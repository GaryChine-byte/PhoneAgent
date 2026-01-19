#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
PC 任务 API 路由

提供 PC Agent 任务的 RESTful API 接口。
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.services.pc_agent_service import get_pc_agent_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["PC Tasks"])


class CreatePCTaskRequest(BaseModel):
    """创建 PC 任务请求"""
    instruction: str = Field(..., description="用户指令")
    device_id: str = Field(..., description="设备 ID")
    kernel_mode: str = Field(default="vision", description="Kernel 模式")
    max_steps: int = Field(default=30, description="最大步骤数")
    prompt_card_ids: Optional[List[int]] = Field(default=[], description="提示词卡片ID列表")


class PCTaskResponse(BaseModel):
    """PC 任务响应"""
    task_id: str
    instruction: str
    device_id: str
    device_type: str
    status: str
    steps: list
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_tokens: int
    total_prompt_tokens: int
    total_completion_tokens: int


@router.post("/tasks", response_model=dict)
async def create_pc_task(request: CreatePCTaskRequest):
    """
    创建 PC 任务
    
    Args:
        request: 创建任务请求
        
    Returns:
        任务 ID
        
    Raises:
        HTTPException: 当任务创建或执行失败时
    """
    try:
        pc_service = get_pc_agent_service()
        
        # 处理提示词卡片：拼接到指令中（与手机 Agent 一致）
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
                logger.info(f"✅ 已应用 {len(selected_cards)} 个提示词卡片到 PC 任务")
                for card in selected_cards:
                    logger.info(f"  📋 [{card.id}] {card.title}: {card.description}")
                logger.info(f"📝 原始指令长度: {len(request.instruction)} 字符")
                logger.info(f"📝 增强后指令长度: {len(enhanced_instruction)} 字符 (+{len(enhanced_instruction) - len(request.instruction)})")
        
        # 创建任务（使用增强后的指令）
        task_id = await pc_service.create_task(
            instruction=enhanced_instruction,
            device_id=request.device_id,
            kernel_mode=request.kernel_mode,
            max_steps=request.max_steps
        )
        
        # 立即执行（通过 HTTP API 查询设备信息，与 AI 手机架构一致）
        success = await pc_service.execute_task(task_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="任务执行失败")
        
        return {"task_id": task_id}
    
    except Exception as e:
        logger.error(f"创建 PC 任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=PCTaskResponse)
async def get_pc_task(task_id: str):
    """
    获取 PC 任务详情
    
    Args:
        task_id: 任务 ID
        
    Returns:
        任务详情
        
    Raises:
        HTTPException: 当任务不存在时
    """
    pc_service = get_pc_agent_service()
    task = pc_service.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return task.to_dict()


@router.get("/tasks", response_model=dict)
async def list_pc_tasks(
    limit: int = 100,
    offset: int = 0
):
    """
    列出所有 PC 任务
    
    Args:
        limit: 返回数量限制
        offset: 偏移量
        
    Returns:
        任务列表
    """
    pc_service = get_pc_agent_service()
    all_tasks = pc_service.get_all_tasks()
    
    # 按创建时间倒序排序
    all_tasks.sort(key=lambda t: t.created_at, reverse=True)
    
    # 分页
    tasks = all_tasks[offset:offset + limit]
    
    return {
        "tasks": [task.to_dict() for task in tasks],
        "total": len(all_tasks),
        "limit": limit,
        "offset": offset
    }


@router.post("/tasks/{task_id}/cancel", response_model=dict)
async def cancel_pc_task(task_id: str):
    """
    取消 PC 任务
    
    Args:
        task_id: 任务 ID
        
    Returns:
        操作结果
        
    Raises:
        HTTPException: 当任务不存在或无法取消时
    """
    pc_service = get_pc_agent_service()
    success = await pc_service.cancel_task(task_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="无法取消任务")
    
    return {"success": True, "message": "任务已取消"}


@router.get("/devices", response_model=dict)
async def list_pc_devices():
    """
    列出所有 PC 设备
    
    从 WebSocket 服务器查询已连接的 PC 设备
    
    Returns:
        PC 设备列表
    """
    try:
        import httpx
        import os
        
        # 从环境变量获取 WebSocket 服务器地址
        ws_host = os.getenv("WEBSOCKET_HOST", "127.0.0.1")
        ws_port = os.getenv("WEBSOCKET_PORT", "9999")
        
        # 查询 WebSocket 服务器的设备列表
        websocket_urls = [
            f"http://{ws_host}:{ws_port}/devices",
            "http://127.0.0.1:9999/devices",
            "http://localhost:9999/devices",
        ]
        
        for url in websocket_urls:
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        all_devices = data.get("devices", [])
                        
                        # 过滤 PC 设备
                        pc_devices = [
                            {
                                "device_id": device.get("device_id"),
                                "device_name": device.get("device_name"),
                                "device_type": device.get("device_type", "pc"),
                                "os_info": device.get("os_info"),
                                "status": device.get("status"),
                                "frp_port": device.get("frp_port"),
                                "model": device.get("model"),
                                "last_active": device.get("last_heartbeat"),
                                "ws_connected": device.get("ws_connected", False),
                                "frp_connected": device.get("frp_connected", False),
                            }
                            for device in all_devices
                            if device.get("device_type") == "pc" or device.get("frp_port", 0) >= 6200
                        ]
                        
                        return {
                            "devices": pc_devices,
                            "total": len(pc_devices)
                        }
            except Exception as e:
                logger.debug(f"尝试连接 {url} 失败: {e}")
                continue
        
        # 如果所有尝试都失败，返回空列表
        logger.warning("无法连接到 WebSocket 服务器，返回空设备列表")
        return {
            "devices": [],
            "total": 0
        }
    
    except Exception as e:
        logger.error(f"获取 PC 设备列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
