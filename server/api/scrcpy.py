#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
Scrcpy H.264 WebSocket 路由
基于 NAL 单元传输的低延迟视频流
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
import asyncio
import logging
from typing import Optional

from server.services.scrcpy_manager import get_scrcpy_manager

router = APIRouter(prefix="/scrcpy", tags=["scrcpy"])
logger = logging.getLogger(__name__)


class StartScrcpyRequest(BaseModel):
    """启动 Scrcpy H.264 流请求"""
    bitrate: Optional[int] = 4_000_000  # 4Mbps
    max_size: Optional[int] = 1280  # 1280p
    framerate: Optional[int] = 30


@router.post("/start/{device_id}")
async def start_scrcpy(device_id: str, request: StartScrcpyRequest):
    """
    启动 Scrcpy H.264 会话
    
    Args:
        device_id: 设备标识（FRP 模式下是 localhost:61XX）
    """
    try:
        logger.info(f"Starting H.264 stream for device: {device_id}")
        manager = get_scrcpy_manager()
        session = manager.start_session(
            device_id=device_id,
            bitrate=request.bitrate,
            max_size=request.max_size,
            framerate=request.framerate
        )
        
        # 优化：减少等待时间，改为异步轮询
        if not session.wait_for_init_data(timeout=10.0):  # 10秒超时
            logger.warning(f"Scrcpy初始化数据超时，但会话已启动")
            # 不抛出异常，允许前端自行重试连接
            return {
                "success": True,
                "device_id": device_id,
                "message": "H.264 stream started (init data pending)",
                "warning": "初始化数据尚未就绪，请稍后刷新",
                "config": {
                    "bitrate": request.bitrate,
                    "max_size": request.max_size,
                    "framerate": request.framerate
                }
            }
        
        return {
            "success": True,
            "device_id": device_id,
            "message": "H.264 stream started",
            "config": {
                "bitrate": request.bitrate,
                "max_size": request.max_size,
                "framerate": request.framerate
            }
        }
    
    except Exception as e:
        logger.error(f"Failed to start H.264 stream: {e}", exc_info=True)
        raise HTTPException(500, f"启动失败: {str(e)}")


@router.post("/stop/{device_id}")
async def stop_scrcpy(device_id: str):
    """停止 Scrcpy H.264 会话（优化版 - 异步执行）"""
    try:
        manager = get_scrcpy_manager()
        
        # 优化：异步执行停止操作，不等待完成
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, manager.stop_session, device_id)
        
        # 立即返回，不等待停止完成
        return {
            "success": True,
            "message": f"H.264 stream stopped for {device_id}"
        }
    except Exception as e:
        logger.error(f"Failed to stop H.264 stream: {e}")
        raise HTTPException(500, f"停止失败: {str(e)}")


@router.websocket("/stream/{device_id}")
async def stream_websocket(websocket: WebSocket, device_id: str):
    """
    H.264 视频流 WebSocket 端点
    
    核心流程：
    1. 接受连接
    2. 发送初始化数据（SPS + PPS + IDR）
    3. 持续发送 NAL 单元
    
    每个 WebSocket 消息 = 一个完整 NAL 单元
    """
    await websocket.accept()
    logger.info(f"📺 H.264 WebSocket connected: {device_id}")
    
    manager = get_scrcpy_manager()
    session = manager.get_session(device_id)
    
    # 如果会话不存在，返回错误
    if not session or not session.is_running:
        await websocket.send_json({
            "error": "Session not found or not running",
            "message": f"Please start session for {device_id} first"
        })
        await websocket.close(code=1008, reason="Session not found")
        return
    
    try:
        # 1. 等待初始化数据就绪（增加超时时间）
        if not session.wait_for_init_data(timeout=30.0):  # 从10秒增加到30秒
            await websocket.send_json({
                "error": "Init data timeout",
                "message": "Failed to get SPS/PPS/IDR within 30 seconds"
            })
            await websocket.close()
            return
        
        # 2. 发送初始化数据（SPS + PPS + IDR）
        init_data = session.get_init_data()
        if init_data:
            await websocket.send_bytes(init_data)
            logger.info(f"Sent init data: {len(init_data)} bytes")
        else:
            await websocket.send_json({"error": "Init data not available"})
            await websocket.close()
            return
        
        # 3. 持续发送 NAL 单元
        nal_count = 0
        while session.is_running:
            # 从队列获取 NAL 单元（阻塞式，带超时）
            nal_unit = await asyncio.to_thread(
                session.get_nal_unit,
                timeout=1.0
            )
            
            if nal_unit:
                # 发送 NAL 单元
                await websocket.send_bytes(nal_unit)
                nal_count += 1
                
                # 每 100 个 NAL 单元打印一次日志
                if nal_count % 100 == 0:
                    logger.debug(f"Sent {nal_count} NAL units to {device_id}")
            else:
                # 超时，检查连接状态
                try:
                    await websocket.send_json({"type": "ping"})
                except:
                    # 连接断开
                    break
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {device_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    
    finally:
        try:
            await websocket.close()
        except:
            pass
        logger.info(f"H.264 stream ended for {device_id}")


@router.get("/sessions")
async def list_sessions():
    """列出所有 H.264 会话"""
    manager = get_scrcpy_manager()
    sessions = []
    
    for device_id, session in manager.sessions.items():
        sessions.append({
            "device_id": device_id,
            "is_running": session.is_running,
            "has_init_data": session.get_init_data() is not None
        })
    
    return {
        "success": True,
        "sessions": sessions,
        "count": len(sessions)
    }


# ============================================
# 设备控制 API
# ============================================

class TouchRequest(BaseModel):
    """触摸事件请求"""
    x: int  # X坐标百分比 (0-100)
    y: int  # Y坐标百分比 (0-100)
    action: str = "tap"  # tap/down/move/up


class SwipeRequest(BaseModel):
    """滑动事件请求"""
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    duration: int = 300  # 毫秒


class KeyRequest(BaseModel):
    """按键事件请求"""
    keycode: int
    action: str = "press"  # press/down/up


@router.post("/control/{device_id}/touch")
async def control_touch(device_id: str, request: TouchRequest):
    """
    发送触摸事件（优化版 - 动态获取设备分辨率）
    
    Args:
        device_id: 设备ID
        request: 触摸请求 (x, y 为百分比 0-100)
    """
    try:
        import subprocess
        from server.utils import device_id_to_adb_address
        from server.services.device_scanner import get_device_scanner
        
        # 转换 device_id 为 ADB 地址 (device_6100 -> localhost:6100)
        adb_address = device_id_to_adb_address(device_id)
        
        # 优化：动态获取设备分辨率
        scanner = get_device_scanner()
        scanned_devices = scanner.get_scanned_devices()
        
        width, height = 1080, 2340  # 默认值
        if device_id in scanned_devices:
            device = scanned_devices[device_id]
            if device.screen_resolution:
                try:
                    # 解析分辨率 "1080x2340"
                    parts = device.screen_resolution.split('x')
                    if len(parts) == 2:
                        width = int(parts[0])
                        height = int(parts[1])
                        logger.debug(f"Using device resolution: {width}x{height}")
                except Exception as e:
                    logger.warning(f"Failed to parse resolution: {e}, using default")
        
        # 将百分比转换为实际坐标
        actual_x = int(request.x * width / 100)
        actual_y = int(request.y * height / 100)
        
        logger.info(f"Touch: {request.x}%, {request.y}% -> {actual_x}, {actual_y} (screen: {width}x{height})")
        
        if request.action == "tap":
            cmd = f"adb -s {adb_address} shell input tap {actual_x} {actual_y}"
        elif request.action == "down":
            cmd = f"adb -s {adb_address} shell input touchscreen swipe {actual_x} {actual_y} {actual_x} {actual_y} 1000"
        else:
            raise HTTPException(400, f"Unsupported touch action: {request.action}")
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0:
            raise HTTPException(500, f"ADB command failed: {result.stderr}")
        
        return {
            "success": True,
            "device_id": device_id,
            "action": request.action,
            "coordinates": {"x": actual_x, "y": actual_y}
        }
    
    except subprocess.TimeoutExpired:
        raise HTTPException(500, "Touch command timeout")
    except Exception as e:
        logger.error(f"Failed to send touch event: {e}")
        raise HTTPException(500, f"Touch failed: {str(e)}")


@router.post("/control/{device_id}/swipe")
async def control_swipe(device_id: str, request: SwipeRequest):
    """
    发送滑动事件（优化版 - 动态获取设备分辨率）
    
    Args:
        device_id: 设备ID
        request: 滑动请求
    """
    try:
        import subprocess
        from server.utils import device_id_to_adb_address
        from server.services.device_scanner import get_device_scanner
        
        # 转换 device_id 为 ADB 地址 (device_6100 -> localhost:6100)
        adb_address = device_id_to_adb_address(device_id)
        
        # 优化：动态获取设备分辨率
        scanner = get_device_scanner()
        scanned_devices = scanner.get_scanned_devices()
        
        width, height = 1080, 2340  # 默认值
        if device_id in scanned_devices:
            device = scanned_devices[device_id]
            if device.screen_resolution:
                try:
                    parts = device.screen_resolution.split('x')
                    if len(parts) == 2:
                        width = int(parts[0])
                        height = int(parts[1])
                except Exception as e:
                    logger.warning(f"Failed to parse resolution: {e}, using default")
        
        # 转换百分比坐标
        start_x = int(request.start_x * width / 100)
        start_y = int(request.start_y * height / 100)
        end_x = int(request.end_x * width / 100)
        end_y = int(request.end_y * height / 100)
        
        cmd = f"adb -s {adb_address} shell input swipe {start_x} {start_y} {end_x} {end_y} {request.duration}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            raise HTTPException(500, f"ADB command failed: {result.stderr}")
        
        return {
            "success": True,
            "device_id": device_id,
            "action": "swipe",
            "start": {"x": start_x, "y": start_y},
            "end": {"x": end_x, "y": end_y}
        }
    
    except subprocess.TimeoutExpired:
        raise HTTPException(500, "Swipe command timeout")
    except Exception as e:
        logger.error(f"Failed to send swipe event: {e}")
        raise HTTPException(500, f"Swipe failed: {str(e)}")


@router.post("/control/{device_id}/key")
async def control_key(device_id: str, request: KeyRequest):
    """
    发送按键事件
    
    Args:
        device_id: 设备ID  
        request: 按键请求
    """
    try:
        import subprocess
        from server.utils import device_id_to_adb_address
        
        # 转换 device_id 为 ADB 地址 (device_6100 -> localhost:6100)
        adb_address = device_id_to_adb_address(device_id)
        
        cmd = f"adb -s {adb_address} shell input keyevent {request.keycode}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0:
            raise HTTPException(500, f"ADB command failed: {result.stderr}")
        
        return {
            "success": True,
            "device_id": device_id,
            "keycode": request.keycode,
            "action": request.action
        }
    
    except subprocess.TimeoutExpired:
        raise HTTPException(500, "Key command timeout")
    except Exception as e:
        logger.error(f"Failed to send key event: {e}")
        raise HTTPException(500, f"Key failed: {str(e)}")
