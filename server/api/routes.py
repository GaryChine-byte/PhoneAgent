#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
API Routes - RESTful API 路由定义

包含：
- 设备管理 API
- 任务管理 API
- 语音识别 API
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from server.services import get_agent_service, get_device_pool
from server.services.device_pool import DeviceStatus
from server.services.agent_service import TaskStatus
from server.api.schemas.task import CreateTaskRequest, TaskResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# 导入子路由
from server.api.speech_api import router as speech_router  # 新：统一的语音API
from server.api.anti_detection_config import router as anti_detection_router
from server.api.shortcuts import router as shortcuts_router
from server.api.prompt_cards import router as prompt_cards_router
from server.api.scrcpy import router as scrcpy_router  # H.264 实时预览
from server.api.planning import router as planning_router  # 智能规划模式
from server.api.model_stats import router as model_stats_router # 新增: 模型统计
from server.api.pc_tasks import router as pc_tasks_router  # PC 任务管理
# 注册子路由（带标签分类）
# 按照功能模块分类，方便API文档查看和维护
router.include_router(speech_router, prefix="/speech", tags=["🎤 语音服务"])
router.include_router(scrcpy_router, prefix="", tags=["📺 实时预览"])
router.include_router(planning_router, prefix="", tags=["智能规划"])
router.include_router(shortcuts_router, prefix="", tags=["快捷指令"])
router.include_router(prompt_cards_router, prefix="", tags=["提示词管理"])
router.include_router(model_stats_router, prefix="", tags=["模型统计"])  # 新增
router.include_router(pc_tasks_router, prefix="/pc", tags=["🖥️ PC 任务管理"])  # 新增
# 注意：应用配置API已迁移到 app_config_routes.py (在 app.py 中注册)
router.include_router(anti_detection_router, prefix="", tags=["🛡️ 防风控配置"])


# ============================================
# 端口管理 API
# ============================================

@router.get("/ports/status", summary="查询所有端口分配状态", tags=["🔌 端口管理"])
async def get_port_allocations():
    """获取所有端口的分配状态"""
    from server.services.port_manager import get_port_manager
    
    port_manager = get_port_manager()
    allocations = await port_manager.list_allocations()
    
    return {
        "allocations": allocations,
        "count": len(allocations)
    }


@router.get("/ports/{port}/status", summary="查询指定端口状态", tags=["🔌 端口管理"])
async def get_port_status(port: int):
    """查询指定端口是否被占用"""
    from server.services.port_manager import get_port_manager
    
    port_manager = get_port_manager()
    status = await port_manager.get_port_status(port)
    
    if status:
        return {
            "port": port,
            "occupied": True,
            "device_id": status['device_id'],
            "device_name": status['device_name'],
            "allocated_at": status['allocated_at'].isoformat()
        }
    else:
        return {
            "port": port,
            "occupied": False
        }


@router.get("/ports/available", summary="查找可用端口", tags=["🔌 端口管理"])
async def find_available_port(start: int = 6100, end: int = 6199):
    """查找可用端口"""
    from server.services.port_manager import get_port_manager
    
    port_manager = get_port_manager()
    available_port = await port_manager.find_available_port(start, end)
    
    if available_port:
        return {
            "available": True,
            "port": available_port
        }
    else:
        return {
            "available": False,
            "message": "No available ports in range"
        }


@router.post("/ports/cleanup", summary="清理所有 ADB 连接和端口", tags=["🔌 端口管理"])
async def cleanup_all_ports():
    """
    手动触发清理所有 ADB 连接和端口分配
    
    用于解决端口残留问题
    """
    from server.services.port_manager import get_port_manager
    
    port_manager = get_port_manager()
    await port_manager.cleanup_all_adb_connections()
    
    return {
        "success": True,
        "message": "所有 ADB 连接已清理，端口分配已重置"
    }


@router.delete("/ports/{port}/release", summary="释放指定端口", tags=["🔌 端口管理"])
async def release_port(port: int):
    """
    手动释放指定端口
    
    Args:
        port: 端口号
    """
    from server.services.port_manager import get_port_manager
    import subprocess
    
    port_manager = get_port_manager()
    
    # 先断开 ADB 连接
    adb_address = f"localhost:{port}"
    try:
        subprocess.run(
            ["adb", "disconnect", adb_address],
            capture_output=True,
            timeout=2
        )
    except:
        pass
    
    # 释放端口
    success = await port_manager.release_port(port=port)
    
    if success:
        return {
            "success": True,
            "port": port,
            "message": f"端口 {port} 已释放"
        }
    else:
        return {
            "success": False,
            "port": port,
            "message": f"端口 {port} 未被占用或释放失败"
        }


# 导入设备扫描器
from server.services.device_scanner import get_device_scanner


# ============================================
# Pydantic Models (请求/响应模型)
# ============================================
# 注意：CreateTaskRequest 和 TaskResponse 已从 server.api.schemas.task 导入


class DeviceResponse(BaseModel):
    """设备响应"""
    device_id: str
    device_name: str
    frp_port: int
    adb_address: str
    status: str
    frp_connected: bool
    ws_connected: bool
    current_task: Optional[str]
    model: str
    android_version: str
    screen_resolution: str
    battery: int
    total_tasks: int
    success_tasks: int
    failed_tasks: int
    success_rate: float
    registered_at: str
    last_active: str


class StatsResponse(BaseModel):
    """统计信息响应"""
    device_stats: Dict[str, Any]
    task_stats: Dict[str, Any]


# ============================================
# 设备管理 API
# ============================================


async def get_websocket_device_status():
    """
    从WebSocket服务器查询设备连接状态（异步版本）
    
    服务器内部通信：API服务器 → WebSocket服务器
    - 假设：API服务器和WebSocket服务器在同一台机器上
    - 使用：127.0.0.1 直接连接（服务器内部通信，不需要配置）
    
    注意：这与客户端配置不同
    - 客户端（手机/Android App/PC Agent）：用户配置服务器地址，客户端拼接URL
    - 服务器端（本函数）：服务器内部通信，直接使用 127.0.0.1
    
    返回两种映射：
    - ws_by_id: device_id -> ws_connected（主要匹配方式，格式：device_{frp_port}）
    - ws_by_port: frp_port -> ws_connected（备用匹配方式）
    """
    # 服务器内部通信：直接使用 127.0.0.1（与 AI 手机架构一致）
    # API 服务器和 WebSocket 服务器必须部署在同一台机器上
    websocket_url = "http://127.0.0.1:9999/devices"
    websocket_urls = [websocket_url]
    
    errors = []
    for url in websocket_urls:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=1.0) as client:  # 降低超时到1秒
                response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                # 返回设备状态映射
                ws_status = {
                    "by_id": {},    # device_id -> ws_connected
                    "by_port": {}   # frp_port -> ws_connected
                }
                for device in data.get("devices", []):
                    device_id = device.get("device_id")
                    frp_port = device.get("frp_port")
                    ws_connected = device.get("ws_connected", False)
                    
                    # 按 device_id 映射（主要方式）
                    if device_id:
                        ws_status["by_id"][device_id] = ws_connected
                    
                    # 按 frp_port 映射（备用方式）
                    if frp_port:
                        ws_status["by_port"][frp_port] = ws_connected
                
                logger.info(f"从WebSocket服务器({url})获取到设备状态: {ws_status}")
                return ws_status
            else:
                errors.append(f"{url}: HTTP {response.status_code}")
        except Exception as e:
            errors.append(f"{url}: {type(e).__name__}: {e}")
    
    logger.error(f"所有WebSocket服务器地址都无法连接: {errors}")
    return {"by_id": {}, "by_port": {}}

@router.get("/devices/scanned", tags=["设备管理"])
async def list_scanned_devices():
    """
    获取所有设备列表（优化版 - 合并扫描设备和 WebSocket 设备）
    
    包括：
    1. DeviceScanner 扫描到的手机设备（通过 FRP + ADB）
    2. WebSocket 直接连接的 PC 设备（不需要 FRP）
    """
    scanner = get_device_scanner()
    
    # 1. 获取 DeviceScanner 扫描到的设备（主要是手机）
    online_devices = scanner.get_online_devices()
    
    # 2. 从 WebSocket 服务器查询所有设备状态
    ws_device_status = await get_websocket_device_status()
    
    # 3. 从 WebSocket 服务器获取完整设备列表（包括 PC 设备）
    ws_devices_dict = {}
    try:
        import httpx
        websocket_url = f"http://127.0.0.1:9999/devices"
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(websocket_url)
            if response.status_code == 200:
                data = response.json()
                for device in data.get("devices", []):
                    device_id = device.get("device_id")
                    if device_id:
                        ws_devices_dict[device_id] = device
    except Exception as e:
        logger.debug(f"无法从 WebSocket 获取设备列表: {e}")
    
    devices = []
    
    # 4. 处理 DeviceScanner 扫描到的设备（手机）
    for device_id, device in online_devices.items():
        # 查询WebSocket连接状态（优先按device_id匹配，其次按frp_port匹配）
        ws_connected = (
            ws_device_status["by_id"].get(device_id, False) or  # 按device_id匹配（device_{frp_port}格式）
            ws_device_status["by_port"].get(device.frp_port, False)  # 按frp_port匹配（备用）
        )
        
        # 只包含成功获取的字段，None值不返回
        device_data = {
            "device_id": device.device_id,
            "device_name": device.device_name,  # 使用设备名称
            "device_type": device.device_type,  # ✅ 使用 DeviceScanner 存储的设备类型
            "status": "online" if device.is_online else "offline",
            "frp_port": device.frp_port,
            "adb_address": device.adb_address,
            # 连接状态
            "frp_connected": True,  # 能扫描到说明FRP已连接
            "ws_connected": ws_connected,  # 从WebSocket管理器查询实际连接状态
            # 任务统计（V2暂不支持）
            "current_task": None,
            "total_tasks": 0,
            "success_tasks": 0,
            "failed_tasks": 0,
            "success_rate": 0.0,
            # 时间字段（兼容V1命名）
            "registered_at": device.discovered_at.isoformat(),
            "last_active": device.last_seen.isoformat(),
            "discovered_at": device.discovered_at.isoformat(),
            "last_seen": device.last_seen.isoformat(),
            "method": "port_scanning"  # 标识这是扫描发现的
        }
        
        # 只添加成功获取的字段（不为None）
        if device.model:
            device_data["model"] = device.model
        if device.android_version:
            device_data["android_version"] = device.android_version
        if device.screen_resolution:
            device_data["screen_resolution"] = device.screen_resolution
        if device.battery is not None:
            device_data["battery"] = device.battery
        if device.memory_total:
            device_data["memory_total"] = device.memory_total
        if device.memory_available:
            device_data["memory_available"] = device.memory_available
        if device.storage_total:
            device_data["storage_total"] = device.storage_total
        if device.storage_available:
            device_data["storage_available"] = device.storage_available
        
        devices.append(device_data)
    
    # 5. 添加 WebSocket 中的 PC 设备（不在 DeviceScanner 中的设备）
    for device_id, ws_device in ws_devices_dict.items():
        # 跳过已经在 DeviceScanner 中的设备
        if device_id in online_devices:
            continue
        
        # 只添加 PC 设备（或者端口 >= 6200 的设备）
        device_type = ws_device.get("device_type")
        frp_port = ws_device.get("frp_port", 0)
        
        if device_type == "pc" or frp_port >= 6200:
            device_data = {
                "device_id": device_id,
                "device_name": ws_device.get("device_name", device_id),
                "device_type": device_type or "pc",
                "status": ws_device.get("status", "offline"),
                "frp_port": frp_port,
                "adb_address": None,  # PC 设备没有 ADB
                # 连接状态
                "frp_connected": ws_device.get("frp_connected", False),
                "ws_connected": ws_device.get("ws_connected", False),
                # 任务统计
                "current_task": None,
                "total_tasks": 0,
                "success_tasks": 0,
                "failed_tasks": 0,
                "success_rate": 0.0,
                # 时间字段
                "registered_at": ws_device.get("connected_at"),
                "last_active": ws_device.get("last_heartbeat"),
                "method": "websocket"  # 标识这是 WebSocket 直连的设备
            }
            
            # 添加 PC 特有字段
            if ws_device.get("os_info"):
                device_data["os_info"] = ws_device.get("os_info")
            if ws_device.get("model"):
                device_data["model"] = ws_device.get("model")
            
            devices.append(device_data)
            logger.debug(f"添加 WebSocket PC 设备: {device_id}")
    
    return {
        "devices": devices,
        "count": len(devices),
        "method": "hybrid_scanning"  # 混合模式：扫描 + WebSocket
    }


# 废弃接口已删除: GET /devices -> 请使用 GET /devices/scanned


@router.get("/devices/{device_id}", tags=[" 设备管理"])
async def get_device(device_id: str):
    """获取设备详情（从V2扫描器）"""
    from server.services.device_scanner import get_device_scanner
    
    scanner = get_device_scanner()
    scanned_devices = scanner.get_scanned_devices()
    
    if device_id not in scanned_devices:
        raise HTTPException(404, f"Device not found: {device_id}")
    
    device = scanned_devices[device_id]
    
    # 返回完整设备信息
    return {
        "device_id": device.device_id,
        "device_name": device.device_name,  # 使用device_name而不是device_id
        "status": "online" if device.is_online else "offline",
        "frp_port": device.frp_port,
        "adb_address": device.adb_address,
        "model": device.model,
        "android_version": device.android_version,
        "screen_resolution": device.screen_resolution,
        "battery": device.battery,
        "memory_total": device.memory_total,
        "memory_available": device.memory_available,
        "storage_total": device.storage_total,
        "storage_available": device.storage_available,
        "frp_connected": True,
        "ws_connected": False,
        "discovered_at": device.discovered_at.isoformat(),
        "last_seen": device.last_seen.isoformat(),
        "method": "port_scanning"
    }


class RenameDeviceRequest(BaseModel):
    """设备重命名请求"""
    device_name: str = Field(..., min_length=1, max_length=50, description="新设备名称")


@router.patch("/devices/{device_id}/name", summary="重命名设备", tags=[" 设备管理"])
async def rename_device(device_id: str, request: RenameDeviceRequest):
    """
    更新设备名称
    
    用户可以为设备设置自定义名称，便于识别
    """
    from server.services.device_scanner import get_device_scanner
    
    device_scanner = get_device_scanner()
    success = await device_scanner.update_device_name(device_id, request.device_name)
    
    if not success:
        raise HTTPException(404, f"Device not found: {device_id}")
    
    return {
        "message": "Device renamed successfully",
        "device_id": device_id,
        "new_name": request.device_name
    }


# ============================================
# 任务管理 API
# ============================================

@router.post("/tasks", response_model=TaskResponse, tags=[" 任务管理"])
async def create_task(request: CreateTaskRequest):
    """
    创建任务
    
    支持两种模式：
    1. 指定设备ID（device_id）
    2. 自动分配（从设备池选择可用设备）
    """
    agent_service = get_agent_service()
    
    # 导入配置（在使用前导入）
    from server.config import Config
    config = Config()
    
    # 构建模型配置
    # 支持混合内核：auto（XML优先，失败切换Vision）、xml（纯XML）、vision（纯Vision）
    # 如果用户未明确指定模型，让智能选择器决定
    should_use_selector = (
        request.ai_model == "autoglm-phone"  # 默认值
    )
    
    model_config = {
        "provider": request.ai_provider,
        "max_steps": request.max_steps or config.MAX_TASK_STEPS,  # 使用环境变量默认值
        "kernel_mode": request.kernel_mode or "auto",  # 默认使用auto模式（XML优先，失败切换Vision）
    }
    
    # 只有用户明确指定非默认模型时，才传递 model_name
    if not should_use_selector:
        model_config["model_name"] = request.ai_model
    # 否则让智能选择器在 agent_service._run_agent 中决定（会选择glm-4.6v-flash）
    
    # 使用用户提供的API Key，如果没有则从环境变量加载
    if request.ai_api_key:
        model_config["api_key"] = request.ai_api_key
    else:
        # 从 .env 文件自动加载 API Key
        if config.ZHIPU_API_KEY:
            model_config["api_key"] = config.ZHIPU_API_KEY
        else:
            raise HTTPException(400, "未配置API Key，请在.env中设置ZHIPU_API_KEY或在创建任务时提供")
    
    # 处理提示词卡片：拼接到指令中
    enhanced_instruction = request.instruction
    if request.prompt_card_ids and len(request.prompt_card_ids) > 0:
        from server.api.prompt_cards import load_prompt_cards
        all_cards = load_prompt_cards()
        selected_cards = [card for card in all_cards if card.id in request.prompt_card_ids]
        
        if selected_cards:
            prompt_cards_content = "\n\n===== 任务优化提示词 =====\n"
            for card in selected_cards:
                prompt_cards_content += f"\n【{card.title}】\n{card.content}\n"
            prompt_cards_content += "\n===== 提示词结束 =====\n"
            enhanced_instruction = f"{request.instruction}{prompt_cards_content}"
            
            # 详细日志：让用户可以验证卡片是否生效
            logger.info(f"✅ 已应用 {len(selected_cards)} 个提示词卡片到手机任务")
            for card in selected_cards:
                logger.info(f"  📋 [{card.id}] {card.title}: {card.description}")
            logger.info(f"📝 原始指令长度: {len(request.instruction)} 字符")
            logger.info(f"📝 增强后指令长度: {len(enhanced_instruction)} 字符 (+{len(enhanced_instruction) - len(request.instruction)})")
            logger.debug(f"📝 增强后的完整指令:\n{enhanced_instruction}")
    
    # 创建任务
    task_id = await agent_service.create_task(
        instruction=enhanced_instruction,  # 使用增强后的指令
        model_config=model_config,
        device_id=request.device_id
    )
    
    # 执行任务
    device_pool = get_device_pool()
    success = await agent_service.execute_task(task_id, device_pool)
    
    if not success:
        raise HTTPException(400, "Failed to start task execution")
    
    # 获取任务信息
    task = agent_service.get_task(task_id)
    if not task:
        raise HTTPException(500, "Task created but not found")
    
    # 确保 result 是字符串（如果是 dict 则序列化）
    result_str = task.result
    if isinstance(task.result, dict):
        result_str = json.dumps(task.result, ensure_ascii=False)
    
    return TaskResponse(
        task_id=task.task_id,
        instruction=task.instruction,
        device_id=task.device_id,
        status=task.status.value,
        created_at=task.created_at.isoformat(),
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        duration=task.duration,
        result=result_str,
        error=task.error,
        steps=task.steps  # 修复：返回完整步骤列表
    )


@router.get("/tasks", response_model=List[TaskResponse], tags=[" 任务管理"])
async def list_tasks(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    获取任务列表（优化版 - 使用异步查询）
    
    Args:
        status: 筛选状态 (pending, running, completed, failed, cancelled)
        limit: 返回数量
        offset: 偏移量
    """
    agent_service = get_agent_service()
    
    # 筛选状态
    filter_status = None
    if status:
        try:
            filter_status = TaskStatus(status)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")
    
    # 使用异步版本避免阻塞
    tasks = await agent_service.list_tasks_async(
        status=filter_status,
        limit=limit,
        offset=offset
    )
    
    return [
        TaskResponse(
            task_id=t.task_id,
            instruction=t.instruction,
            device_id=t.device_id,
            status=t.status.value,
            created_at=t.created_at.isoformat(),
            started_at=t.started_at.isoformat() if t.started_at else None,
            completed_at=t.completed_at.isoformat() if t.completed_at else None,
            duration=t.duration,
            result=t.result,
            error=t.error,
            steps=t.steps,  # 修复：返回完整步骤列表
            total_tokens=t.total_tokens,
            total_prompt_tokens=t.total_prompt_tokens,
            total_completion_tokens=t.total_completion_tokens
        )
        for t in tasks
    ]


@router.get("/tasks/{task_id}", response_model=TaskResponse, tags=[" 任务管理"])
async def get_task(task_id: str):
    """获取任务详情（优化版 - 使用异步查询）"""
    agent_service = get_agent_service()
    # 使用异步版本避免阻塞
    task = await agent_service.get_task_async(task_id)
    
    if not task:
        raise HTTPException(404, f"Task not found: {task_id}")
    
    # 确保 result 是字符串（如果是 dict 则序列化）
    result_str = task.result
    if isinstance(task.result, dict):
        result_str = json.dumps(task.result, ensure_ascii=False)
    
    return TaskResponse(
        task_id=task.task_id,
        instruction=task.instruction,
        device_id=task.device_id,
        status=task.status.value,
        created_at=task.created_at.isoformat(),
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        duration=task.duration,
        result=result_str,
        error=task.error,
        steps=task.steps,  # 修复：返回完整步骤列表而不是步骤数量
        total_tokens=task.total_tokens,
        total_prompt_tokens=task.total_prompt_tokens,
        total_completion_tokens=task.total_completion_tokens
    )


@router.get("/tasks/{task_id}/steps", tags=[" 任务管理"])
async def get_task_steps(task_id: str):
    """获取任务的详细步骤信息"""
    agent_service = get_agent_service()
    task = agent_service.get_task(task_id)
    
    if not task:
        raise HTTPException(404, f"Task not found: {task_id}")
    
    return {
        "task_id": task.task_id,
        "instruction": task.instruction,
        "status": task.status.value,
        "current_step": task.current_step,
        "total_steps": len(task.steps),
        "steps": task.steps,  # 返回完整的步骤列表（包含token和耗时）
        "total_tokens": task.total_tokens,
        "total_prompt_tokens": task.total_prompt_tokens,
        "total_completion_tokens": task.total_completion_tokens
    }


@router.post("/tasks/{task_id}/cancel", tags=[" 任务管理"])
async def cancel_task(task_id: str):
    """取消正在执行的任务"""
    agent_service = get_agent_service()
    success = await agent_service.cancel_task(task_id)
    
    if not success:
        raise HTTPException(400, f"Failed to cancel task: {task_id}")
    
    return {"message": "Task cancelled", "task_id": task_id}


class SubmitAnswerRequest(BaseModel):
    """提交用户答案请求"""
    answer: str = Field(..., description="用户的回答")


@router.post("/tasks/{task_id}/answer", tags=[" 任务管理"])
async def submit_user_answer(task_id: str, request: SubmitAnswerRequest):
    """
    提交用户对 Ask User 的回答
    
    当任务状态为 WAITING_FOR_USER 时，用户可以通过此接口提交答案。
    答案会被保存到任务中，并唤醒等待的 Agent 继续执行。
    
    Args:
        task_id: 任务ID
        request: 包含用户答案的请求体
    
    Returns:
        提交结果和任务状态
    """
    agent_service = get_agent_service()
    
    # 使用异步版本获取任务
    task = await agent_service.get_task_async(task_id)
    
    if not task:
        raise HTTPException(404, f"Task not found: {task_id}")
    
    # 检查任务状态
    if task.status != TaskStatus.WAITING_FOR_USER:
        raise HTTPException(
            400, 
            f"Task is not waiting for user input (current status: {task.status.value})"
        )
    
    # 检查是否有待回答的问题
    if not task.pending_question:
        raise HTTPException(400, "No pending question found for this task")
    
    # 保存用户答案
    task.user_answer = request.answer
    task.status = TaskStatus.RUNNING  # 恢复运行状态
    
    # 持久化到数据库
    await agent_service._persist_task_to_db(task)
    
    # 唤醒等待的 Agent
    # 通过设置事件标志，让Agent的等待循环退出
    await agent_service.wake_up_waiting_task(task_id, request.answer)
    
    # 广播任务状态变化（通知前端）
    if agent_service._websocket_broadcast_callback:
        try:
            await agent_service._websocket_broadcast_callback({
                "type": "task_status_change",
                "data": {
                    "task_id": task_id,
                    "status": "running",
                    "message": f"User answered: {request.answer[:50]}..."
                }
            })
        except Exception as e:
            logger.error(f"Failed to broadcast answer submission: {e}")
    
    logger.info(f"用户提交了任务 {task_id} 的回答: {request.answer[:50]}...")
    
    return {
        "success": True,
        "task_id": task_id,
        "answer": request.answer,
        "status": "running",
        "message": "Answer submitted successfully, task will continue"
    }


@router.delete("/tasks/{task_id}", tags=[" 任务管理"])
async def delete_task(task_id: str):
    """删除任务记录（仅能删除已完成/失败的任务）"""
    from server.database import get_db
    from server.database.crud import delete_task as db_delete_task, get_task as db_get_task
    
    db = next(get_db())
    
    # 检查任务是否存在
    db_task = db_get_task(db, task_id)
    if not db_task:
        raise HTTPException(404, f"Task not found: {task_id}")
    
    # 只能删除已完成或失败的任务
    if db_task.status not in ["completed", "failed", "cancelled"]:
        raise HTTPException(400, f"Cannot delete running task. Please cancel it first.")
    
    # 删除任务
    success = db_delete_task(db, task_id)
    
    if not success:
        raise HTTPException(500, f"Failed to delete task: {task_id}")
    
    return {"message": "Task deleted", "task_id": task_id}


@router.post("/tasks/delete-batch", tags=[" 任务管理"])
async def delete_tasks_batch(request: dict):
    """批量删除任务记录"""
    from server.database import get_db
    from server.database.crud import delete_tasks_batch as db_delete_tasks_batch
    
    task_ids = request.get("task_ids", [])
    if not task_ids:
        raise HTTPException(400, "task_ids is required")
    
    db = next(get_db())
    count = db_delete_tasks_batch(db, task_ids)
    
    return {"message": f"Deleted {count} tasks", "count": count}


# ============================================
# 统计信息 API
# ============================================

@router.get("/stats", response_model=StatsResponse, tags=[" 统计信息"])
async def get_stats():
    """获取整体统计信息"""
    device_pool = get_device_pool()
    agent_service = get_agent_service()
    
    return StatsResponse(
        device_stats=device_pool.get_stats(),
        task_stats=agent_service.get_stats()
    )


# ============================================
# 语音识别 API - 已迁移到 speech_api.py
# ============================================
# 
# 语音相关接口已迁移到专门的 speech_api.py 文件中：
# - POST /api/v1/speech/stt  - 语音转文字
# - POST /api/v1/speech/tts  - 文字转语音
# - GET  /api/v1/speech/health - 健康检查
#


# ============================================
# ============================================
# WebSocket 实时通信已移除
# ============================================
# 
# 项目已移除 WebSocket 实时推送功能，改为使用轮询机制。
# 前端通过定期调用 GET /api/v1/tasks/{task_id} 获取任务状态。
#

# ============================================
# 语音API已迁移到 speech_api.py
# ============================================
# 
# 语音相关接口已迁移到专门的 speech_api.py 文件中：
# - POST /api/v1/speech/stt  - 语音转文字
# - POST /api/v1/speech/tts  - 文字转语音
# - GET  /api/v1/speech/health - 健康检查
#


# ============================================
# 截图管理 API
# ============================================

@router.get("/screenshots/{task_id}/{filename}", tags=["🖼️ 截图管理"])
async def get_screenshot(task_id: str, filename: str):
    """
    获取任务步骤截图（旧格式兼容）
    
    Args:
        task_id: 任务ID
        filename: 文件名（如 step_001_small.jpg）
    """
    import os
    
    # 构建文件路径
    screenshot_path = os.path.join("data", "screenshots", task_id, filename)
    
    # 检查文件是否存在
    if not os.path.exists(screenshot_path):
        raise HTTPException(
            status_code=404,
            detail="截图文件不存在"
        )
    
    # 返回文件
    return FileResponse(
        path=screenshot_path,
        media_type="image/jpeg",
        filename=filename
    )


@router.get("/screenshots/tasks/{task_id}/steps/{filename}", tags=["🖼️ 截图管理"])
async def get_screenshot_new_format(task_id: str, filename: str):
    """
    获取任务步骤截图（新格式）
    
    路径格式: /api/v1/screenshots/tasks/{task_id}/steps/{filename}
    
    Args:
        task_id: 任务ID
        filename: 文件名（如 step_001_medium.jpg）
    """
    import os
    from pathlib import Path
    
    # 构建文件路径 - 新格式
    screenshot_path = Path("data") / "screenshots" / "tasks" / task_id / "steps" / filename
    
    # 检查文件是否存在
    if not screenshot_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"截图文件不存在: {screenshot_path}"
        )
    
    # 返回文件
    return FileResponse(
        path=str(screenshot_path),
        media_type="image/jpeg",
        filename=filename
    )


@router.get("/devices/{device_id}/screenshot", tags=["🖼️ 截图管理"])
async def get_device_screenshot(device_id: str, size: str = "medium"):
    """
    获取设备实时截图
    
    Args:
        device_id: 设备ID (如 device_6100)
        size: 尺寸级别 (ai/medium/small/thumbnail)
    """
    import asyncio
    import os
    import base64
    import tempfile
    from phone_agent.adb import get_screenshot
    from server.utils.image_utils import compress_screenshot
    
    try:
        # 将 device_id 转换为 ADB 地址 (device_6100 -> localhost:6100)
        from server.utils import device_id_to_adb_address
        adb_address = device_id_to_adb_address(device_id)
        
        # 获取截图
        screenshot = await asyncio.to_thread(get_screenshot, adb_address)
        
        if not screenshot or not screenshot.base64_data:
            raise HTTPException(
                status_code=500,
                detail="无法获取设备截图"
            )
        
        # 保存临时截图
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(base64.b64decode(screenshot.base64_data))
            tmp_path = tmp.name
            tmp.flush()  # 确保数据写入磁盘
            os.fsync(tmp.fileno())  # 强制同步到磁盘
        
        # 验证文件是否可读
        if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
            raise HTTPException(
                status_code=500,
                detail="截图文件保存失败"
            )
        
        # 压缩截图
        compressed_dir = os.path.dirname(tmp_path)
        compressed_paths = await asyncio.to_thread(
            compress_screenshot,
            tmp_path,
            compressed_dir,
            for_ai=(size == "ai")
        )
        
        # 获取指定尺寸的截图
        target_path = compressed_paths.get(size) or compressed_paths.get("medium")
        
        if not target_path or not os.path.exists(target_path):
            raise HTTPException(
                status_code=500,
                detail="截图压缩失败"
            )
        
        # 读取文件内容直接返回（避免FileResponse异步删除问题）
        with open(target_path, "rb") as f:
            image_data = f.read()
        
        # 清理临时文件
        try:
            os.unlink(tmp_path)
            for path in compressed_paths.values():
                if path and os.path.exists(path):
                    os.unlink(path)
        except:
            pass
        
        # 返回图片数据
        from fastapi.responses import Response
        return Response(
            content=image_data,
            media_type="image/jpeg",
            headers={
                "Content-Disposition": f'inline; filename="{device_id}_screenshot_{size}.jpg"'
            }
        )
                
    except Exception as e:
        logger.error(f"获取设备截图错误: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取设备截图失败: {str(e)}"
        )


# ============================================
# 日志管理 API
# ============================================

@router.get("/logs", tags=[" 日志管理"])
async def get_logs(
    level: Optional[str] = Query(None, description="日志级别过滤: DEBUG, INFO, WARNING, ERROR"),
    limit: int = Query(100, ge=1, le=1000, description="返回条数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    search: Optional[str] = Query(None, description="搜索关键词")
):
    """
    获取应用日志（优化版 - 限制文件大小和使用流式读取）
    
    返回格式化的日志列表，支持过滤和搜索
    """
    import os
    import json
    from datetime import datetime, timedelta
    
    logs = []
    log_dir = "logs"
    
    # 如果日志目录不存在，返回空列表
    if not os.path.exists(log_dir):
        return {
            "logs": [],
            "total": 0,
            "offset": offset,
            "limit": limit
        }
    
    # 优化：只读取最近1个日志文件，限制文件大小
    log_files = sorted(
        [f for f in os.listdir(log_dir) if f.endswith('.log')],
        key=lambda x: os.path.getmtime(os.path.join(log_dir, x)),
        reverse=True
    )[:1]  # 只读最近1个文件（从3个减少到1个）
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB 限制
    
    for log_file in log_files:
        try:
            file_path = os.path.join(log_dir, log_file)
            
            # 优化：检查文件大小，跳过过大的文件
            if os.path.getsize(file_path) > MAX_FILE_SIZE:
                logger.warning(f"日志文件 {log_file} 过大，跳过")
                continue
            
            # 优化：只读取文件最后的部分（倒序读取）
            with open(file_path, 'r', encoding='utf-8') as f:
                # 读取最后 5000 行
                lines = f.readlines()[-5000:]
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 尝试解析JSON格式的日志
                    try:
                        log_entry = json.loads(line)
                    except:
                        # 如果不是JSON，解析文本格式
                        # 格式: timestamp - name - level - [file:line] - message
                        parts = line.split(' - ')
                        if len(parts) >= 5:
                            log_entry = {
                                "timestamp": parts[0],
                                "name": parts[1],
                                "level": parts[2].strip(),
                                "message": ' - '.join(parts[4:])  # 消息可能包含 ' - '
                            }
                        elif len(parts) >= 3:
                            # 简化格式: timestamp - name - level - message
                            log_entry = {
                                "timestamp": parts[0],
                                "name": parts[1] if len(parts) > 1 else "",
                                "level": parts[2].strip() if len(parts) > 2 else "INFO",
                                "message": ' - '.join(parts[3:]) if len(parts) > 3 else line
                            }
                        else:
                            log_entry = {
                                "timestamp": datetime.now().isoformat(),
                                "level": "INFO",
                                "message": line
                            }
                    
                    # 过滤日志级别
                    if level and log_entry.get("level") != level.upper():
                        continue
                    
                    # 搜索关键词
                    if search and search.lower() not in log_entry.get("message", "").lower():
                        continue
                    
                    logs.append(log_entry)
        except Exception as e:
            logger.error(f"读取日志文件失败 {log_file}: {e}")
    
    # 按时间倒序排序
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # 分页
    total = len(logs)
    logs = logs[offset:offset + limit]
    
    return {
        "logs": logs,
        "total": total,
        "offset": offset,
        "limit": limit
    }


@router.get("/logs/task/{task_id}", tags=[" 日志管理"])
async def get_task_logs(task_id: str):
    """
    获取特定任务的工程化日志（JSONL格式）
    
    返回该任务的所有步骤日志和元数据
    """
    from phone_agent.logging import TaskLogger
    
    task_logger = TaskLogger(log_dir="logs")
    
    try:
        logs = task_logger.read_logs(task_id)
        
        return {
            "logs": logs,
            "task_id": task_id,
            "total": len(logs)
        }
    except Exception as e:
        logger.error(f"读取任务日志失败: {e}")
        raise HTTPException(500, f"读取日志失败: {str(e)}")


@router.delete("/logs", tags=[" 日志管理"])
async def clear_logs():
    """清空所有日志文件"""
    import os
    import shutil
    
    log_dir = "logs"
    
    if not os.path.exists(log_dir):
        return {"message": "No logs to clear"}
    
    try:
        # 备份日志
        backup_dir = f"logs_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copytree(log_dir, backup_dir)
        
        # 清空日志目录
        for file in os.listdir(log_dir):
            file_path = os.path.join(log_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        return {
            "message": "Logs cleared successfully",
            "backup_location": backup_dir
        }
    except Exception as e:
        logger.error(f"清空日志失败: {e}")
        raise HTTPException(500, f"清空日志失败: {str(e)}")

