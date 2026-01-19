#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
WebSocket Server for Device Communication
设备通信 WebSocket 服务器 - 实时控制和监控通道
"""

import asyncio
import json
import logging
import subprocess
from datetime import datetime, timezone
from typing import Dict, Set, Optional
from dataclasses import dataclass, asdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """
    设备信息
    
    支持 Android 和 PC 设备
    """
    device_id: str
    device_name: str
    device_type: str = "android"  # android 或 pc
    model: str = "unknown"
    android_version: str = "unknown"  # PC 设备为操作系统版本
    screen_resolution: str = "unknown"
    frp_port: int = 0
    connected_at: datetime = None
    last_heartbeat: datetime = None
    status: str = "online"  # online, offline, busy
    battery: int = 100
    network: str = "unknown"
    frp_connected: bool = False
    ws_connected: bool = False  # WebSocket连接状态
    os_info: dict = None  # PC 设备的操作系统信息


class DeviceManager:
    """设备连接管理器"""
    
    def __init__(self):
        # WebSocket 连接: device_id -> WebSocket
        self.connections: Dict[str, WebSocket] = {}
        
        # 设备信息: device_id -> DeviceInfo
        self.devices: Dict[str, DeviceInfo] = {}
        
        # 任务分配: device_id -> Set[task_id]
        self.device_tasks: Dict[str, Set[str]] = {}
        
        self._lock = asyncio.Lock()
    
    async def register_device(self, device_id: str, websocket: WebSocket, info: dict):
        """注册设备并初始化"""
        async with self._lock:
            self.connections[device_id] = websocket
            
            # 检查 FRP 状态
            frp_connected = False
            frp_port = info.get("frp_port", 0)
            if frp_port:
                try:
                    # 检查 FRP 端口是否监听
                    result = subprocess.run(
                        ["netstat", "-tln"],
                        capture_output=True,
                        text=True,
                        timeout=1
                    )
                    if f":{frp_port}" in result.stdout:
                        frp_connected = True
                        logger.info(f"FRP port {frp_port} is listening")
                except Exception as e:
                    logger.warning(f"Failed to check FRP status: {e}")
            
            # 如果设备已存在（重新连接），更新状态而不是创建新对象
            if device_id in self.devices:
                # 设备重连，更新状态
                device = self.devices[device_id]
                device.connected_at = datetime.now(timezone.utc)
                device.last_heartbeat = datetime.now(timezone.utc)
                device.status = "online"  # ← 关键：重连时设置为online
                device.frp_connected = frp_connected
                device.ws_connected = True  # WebSocket已连接
                device.battery = info.get("battery", device.battery)
                device.network = info.get("network", device.network)
                
                # ✅ 修复：重连时也更新 device_type 和 os_info（防止 DeviceScanner 误判）
                if "device_type" in info:
                    device.device_type = info["device_type"]
                if "os_info" in info:
                    device.os_info = info["os_info"]
                if "device_name" in info:
                    device.device_name = info["device_name"]
                
                logger.info(f"Device reconnected: {device_id}, Type: {device.device_type}, status set to online, FRP: {frp_connected}")
                
                # 设备重连时也执行初始化（确保 yadb 等工具就绪）- 仅 Android 设备
                if device.device_type == "android" and frp_connected and frp_port:
                    asyncio.create_task(self._initialize_device_background(device_id, frp_port))
            else:
                # 新设备注册
                device_type = info.get("device_type", "android")
                
                self.devices[device_id] = DeviceInfo(
                    device_id=device_id,
                    device_name=info.get("device_name", device_id),
                    device_type=device_type,
                    model=info.get("model", "unknown"),
                    android_version=info.get("android_version", "unknown"),
                    screen_resolution=info.get("screen_resolution", "unknown"),
                    frp_port=frp_port,
                    connected_at=datetime.now(timezone.utc),
                    last_heartbeat=datetime.now(timezone.utc),
                    status="online",
                    battery=info.get("battery", 100),
                    network=info.get("network", "unknown"),
                    frp_connected=frp_connected,
                    ws_connected=True,
                    os_info=info.get("os_info", None)  # PC 设备的操作系统信息
                )
                logger.info(f"Device registered: {device_id} ({self.devices[device_id].device_name}), Type: {device_type}, FRP: {frp_connected}")
                
                # 新设备注册时执行初始化 (仅 Android 设备需要)
                if device_type == "android" and frp_connected and frp_port:
                    asyncio.create_task(self._initialize_device_background(device_id, frp_port))
            
            # 初始化任务集合
            if device_id not in self.device_tasks:
                self.device_tasks[device_id] = set()
    
    async def _initialize_device_background(self, device_id: str, frp_port: int):
        """
        后台初始化设备（异步任务）
        
        在设备注册后立即执行：
        - 推送 yadb 工具到设备（仅首次注册）
        - 其他初始化操作
        
 优化：避免重复初始化，减少超时等待         """
        try:
            # 检查是否已经初始化过（避免重复初始化）
            if not hasattr(self, '_initialized_devices'):
                self._initialized_devices = set()
            
            # 如果已经初始化过，跳过
            if device_id in self._initialized_devices:
                logger.debug(f"⏭️  Device {device_id} already initialized, skipping...")
                return
            
            from phone_agent.core.device_init import initialize_device
            
            logger.info(f"⏳ Starting background initialization for {device_id}...")
            
            success = await initialize_device(
                device_id=device_id,
                adb_host="localhost",
                adb_port=frp_port,
                check_yadb=True  # 只检查 yadb，不推送安装（由 Android app 预装）
            )
            
            if success:
                logger.info(f"Background initialization completed for {device_id}")
                self._initialized_devices.add(device_id)
            else:
                logger.warning(f"Background initialization had warnings for {device_id}")
                # 即使失败也标记为已尝试，避免重复尝试
                self._initialized_devices.add(device_id)
                
        except Exception as e:
            logger.error(f"Background initialization failed for {device_id}: {e}", exc_info=True)
            # 标记为已尝试，避免重复尝试
            if hasattr(self, '_initialized_devices'):
                self._initialized_devices.add(device_id)
    
    async def unregister_device(self, device_id: str):
        """注销设备并释放资源"""
        async with self._lock:
            # 获取设备的 FRP 端口
            frp_port = None
            if device_id in self.devices:
                frp_port = self.devices[device_id].frp_port
                self.devices[device_id].status = "offline"
                self.devices[device_id].ws_connected = False  # WebSocket已断开
            logger.info(f"Device unregistered: {device_id} (FRP port: {frp_port})")
            
            # 删除 WebSocket 连接
            if device_id in self.connections:
                del self.connections[device_id]
            
            # 清理任务分配
            if device_id in self.device_tasks:
                del self.device_tasks[device_id]
        
        # 释放 ADB 连接和 FRP 端口（在锁外执行，避免阻塞）
        if frp_port:
            await self._cleanup_device_resources(device_id, frp_port)
    
    async def _cleanup_device_resources(self, device_id: str, frp_port: int):
        """清理设备资源：断开 ADB 连接（仅手机设备）"""
        try:
            # 检查设备类型，PC 设备不需要清理 ADB
            device_type = "phone"  # 默认
            if device_id in self.devices:
                device_type = self.devices[device_id].device_type
            
            if device_type == "pc":
                logger.info(f"🧹 Cleaning up resources for {device_id} (PC device, skip ADB cleanup)")
                # PC 设备只需要释放端口
                try:
                    port_manager = get_port_manager()
                    await port_manager.release_port(port=frp_port)
                    logger.info(f"Port {frp_port} released from port manager")
                except Exception as e:
                    logger.debug(f"Failed to release port {frp_port}: {e}")
                logger.info(f"Resource cleanup completed for {device_id}")
                return
            
            # 手机设备：清理 ADB 连接
            adb_address = f"localhost:{frp_port}"
            logger.info(f"🧹 Cleaning up resources for {device_id} (ADB: {adb_address})")
            
            # 1. 断开 ADB 连接
            try:
                result = await asyncio.create_subprocess_exec(
                    "adb", "disconnect", adb_address,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=5)
                
                if result.returncode == 0:
                    logger.info(f"ADB disconnected: {adb_address}")
                else:
                    logger.warning(f"ADB disconnect failed: {stderr.decode()}")
            except asyncio.TimeoutError:
                logger.warning(f"ADB disconnect timeout: {adb_address}")
            except Exception as e:
                logger.warning(f"ADB disconnect error: {e}")
            # 2. 可选：通知端口管理器释放端口（如果有端口管理器）
            try:
                from server.services.port_manager import get_port_manager
                port_manager = get_port_manager()
                # 使用 port 参数释放端口
                await port_manager.release_port(port=frp_port)
                logger.info(f"Port {frp_port} released from port manager")
            except Exception as e:
                logger.debug(f"Port manager not available or release failed: {e}")
            
            logger.info(f"Resource cleanup completed for {device_id}")
        except Exception as e:
            logger.error(f"Failed to cleanup resources for {device_id}: {e}")     
    async def send_command(self, device_id: str, command: dict):
        """向设备发送命令"""
        if device_id not in self.connections:
            logger.warning(f"Device not connected: {device_id}")
            return False
        
        try:
            websocket = self.connections[device_id]
            await websocket.send_json(command)
            logger.info(f"Command sent to {device_id}: {command['type']}")
            return True
        except Exception as e:
            logger.error(f"Failed to send command to {device_id}: {e}")
            return False
    
    async def broadcast(self, message: dict, exclude: Set[str] = None):
        """广播消息"""
        exclude = exclude or set()
        tasks = []
        
        for device_id, websocket in self.connections.items():
            if device_id not in exclude:
                tasks.append(websocket.send_json(message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_device_info(self, device_id: str) -> Optional[DeviceInfo]:
        """获取设备信息"""
        return self.devices.get(device_id)
    
    def list_devices(self, status: Optional[str] = None) -> list:
        """列出设备"""
        devices = list(self.devices.values())
        
        if status:
            devices = [d for d in devices if d.status == status]
        
        return devices
    
    def get_available_device(self) -> Optional[DeviceInfo]:
        """获取可用设备"""
        for device in self.devices.values():
            if device.status == "online" and device.frp_connected:
                # 检查是否空闲（没有任务）
                if len(self.device_tasks.get(device.device_id, set())) == 0:
                    return device
        return None
    
    async def assign_task(self, device_id: str, task_id: str):
        """分配任务"""
        async with self._lock:
            if device_id in self.device_tasks:
                self.device_tasks[device_id].add(task_id)
                self.devices[device_id].status = "busy"
    
    async def complete_task(self, device_id: str, task_id: str):
        """完成任务"""
        async with self._lock:
            if device_id in self.device_tasks:
                self.device_tasks[device_id].discard(task_id)
                
                # 如果没有任务了，标记为在线
                if len(self.device_tasks[device_id]) == 0:
                    self.devices[device_id].status = "online"


# 创建全局设备管理器
device_manager = DeviceManager()


def get_device_manager() -> DeviceManager:
    """获取设备管理器单例（供其他模块使用）"""
    return device_manager


# 创建 FastAPI 应用
app = FastAPI(title="PhoneAgent WebSocket Server", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/device/{frp_port}")
async def device_websocket(websocket: WebSocket, frp_port: int):
    """
    设备 WebSocket 连接端点
    
    使用 frp_port 作为唯一标识，确保与 FRP 扫描器同步
    """
    
    await websocket.accept()
    logger.info(f"WebSocket connection established: frp_port={frp_port}")
    
    try:
        # 等待设备上线消息
        data = await websocket.receive_json()
        
        if data.get("type") != "device_online":
            logger.warning(f"Invalid first message from port {frp_port}: {data}")
            await websocket.close(code=1008, reason="Invalid first message")
            return
        
        # 从 specs 中获取设备信息
        specs = data.get("specs", {})
        # 确保 frp_port 一致
        specs["frp_port"] = frp_port
        # 统一 device_id 格式：device_{frp_port}
        device_id = f"device_{frp_port}"
        specs["device_id"] = device_id
        
        # 注册设备
        await device_manager.register_device(
            device_id=device_id,
            websocket=websocket,
            info=specs
        )
        
        # 发送确认消息
        await websocket.send_json({
            "type": "registered",
            "device_id": device_id,
            "frp_port": frp_port,
            "message": "Device registered successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        logger.info(f"Device registered: {device_id} (port: {frp_port}, name: {specs.get('device_name', 'unknown')}, type: {specs.get('device_type', 'unknown')})")
        
        # 消息循环（支持心跳 + 任务消息）
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            # 处理不同类型的消息
            if message_type == "ping":
                # 心跳请求，响应 pong
                await websocket.send_json({"type": "pong"})
                logger.debug(f"💓 Heartbeat from {device_id}")
            
            elif message_type == "pong":
                # 心跳响应
                logger.debug(f"💓 Heartbeat response from {device_id}")
            
            elif message_type == "task_progress":
                # 转发任务进度（给 API 服务器）
                logger.info(f"Task progress from {device_id} (port: {frp_port}): {data}")
                # TODO: 推送到任务管理系统
            
            elif message_type == "log":
                # 记录设备日志
                logger.info(f"[{device_id}] {data.get('message')}")
            
            elif message_type == "task_complete":
                # 任务完成
                task_id = data.get("task_id")
                await device_manager.complete_task(device_id, task_id)
                logger.info(f"Task {task_id} completed on {device_id} (port: {frp_port})")
            
            else:
                logger.warning(f"Unknown message type from {device_id}: {message_type}")
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {device_id} (port: {frp_port})")
    
    except Exception as e:
        logger.error(f"WebSocket error for {device_id}: {e}")
    
    finally:
        await device_manager.unregister_device(device_id)


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "PhoneAgent WebSocket Server",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "connected_devices": len(device_manager.connections),
        "online_devices": len([d for d in device_manager.devices.values() if d.status == "online"]),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/devices")
async def get_devices():
    """获取WebSocket连接的设备列表（实时状态）"""
    devices = []
    
    for device_id, device_info in device_manager.devices.items():
        # ✅ 核心修复：实时查询 WebSocket 连接状态
        ws_connected = device_id in device_manager.connections
        
        # ✅ 根据设备类型动态计算状态
        if device_info.device_type == "pc":
            # PC 设备：只看 WebSocket 连接
            status = "online" if ws_connected else "offline"
        else:
            # 手机设备：需要双连接（WebSocket + FRP/ADB）
            status = "online" if (ws_connected and device_info.frp_connected) else "offline"
        
        device_data = {
            "device_id": device_info.device_id,
            "device_name": device_info.device_name,
            "device_type": device_info.device_type,
            "model": device_info.model,
            "android_version": device_info.android_version,
            "screen_resolution": device_info.screen_resolution,
            "battery": device_info.battery,
            "network": device_info.network,
            "status": status,  # ✅ 实时计算的状态
            "frp_connected": device_info.frp_connected,
            "ws_connected": ws_connected,  # ✅ 实时查询的连接状态
            "connected_at": device_info.connected_at.isoformat() if device_info.connected_at else None,
            "last_heartbeat": device_info.last_heartbeat.isoformat() if device_info.last_heartbeat else None,
            "frp_port": device_info.frp_port,
            "os_info": device_info.os_info
        }
        devices.append(device_data)
    
    return {
        "devices": devices,
        "count": len(devices),
        "connected_count": len(device_manager.connections)
    }


@app.get("/devices/{device_id}")
async def get_device(device_id: str):
    """获取特定设备的详细信息（实时状态）"""
    if device_id not in device_manager.devices:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device_info = device_manager.devices[device_id]
    
    # ✅ 实时查询 WebSocket 连接状态
    ws_connected = device_id in device_manager.connections
    
    # ✅ 根据设备类型动态计算状态
    if device_info.device_type == "pc":
        status = "online" if ws_connected else "offline"
    else:
        status = "online" if (ws_connected and device_info.frp_connected) else "offline"
    
    return {
        "device_id": device_info.device_id,
        "device_name": device_info.device_name,
        "device_type": device_info.device_type,
        "model": device_info.model,
        "android_version": device_info.android_version,
        "screen_resolution": device_info.screen_resolution,
        "battery": device_info.battery,
        "network": device_info.network,
        "status": status,  # ✅ 实时计算的状态
        "frp_connected": device_info.frp_connected,
        "ws_connected": ws_connected,  # ✅ 实时查询的连接状态
        "os_info": device_info.os_info,
        "connected_at": device_info.connected_at.isoformat() if device_info.connected_at else None,
        "last_heartbeat": device_info.last_heartbeat.isoformat() if device_info.last_heartbeat else None,
        "frp_port": device_info.frp_port,
        "current_tasks": len(device_manager.device_tasks.get(device_id, set()))
    }


@app.post("/devices/{device_id}/command")
async def send_command(device_id: str, command: dict):
    """向设备发送命令"""
    success = await device_manager.send_command(device_id, command)
    if success:
        return {"status": "sent", "device_id": device_id}
    raise HTTPException(status_code=500, detail="Failed to send command")


@app.post("/broadcast")
async def broadcast_message(message: dict):
    """广播消息"""
    await device_manager.broadcast(message)
    return {"status": "broadcasted", "recipients": len(device_manager.connections)}


@app.get("/connections")
async def get_connections():
    """获取当前WebSocket连接状态"""
    connections = {}
    
    for device_id, websocket in device_manager.connections.items():
        connections[device_id] = {
            "connected": True,
            "connection_time": "unknown"  # WebSocket对象没有连接时间信息
        }
    
    return {
        "connections": connections,
        "count": len(connections)
    }


async def auto_connect_devices():
    """
    服务启动时自动连接已知设备
    
    功能：WebSocket 服务器重启后，快速恢复 ADB 连接（仅针对手机设备）
    配合：DeviceScanner 每 10 秒持续扫描，两者互为补充
    
    注意：
    - 此函数在 WebSocket 服务器启动时执行一次，快速恢复连接
    - DeviceScanner 在 API 服务器中运行，持续监控设备状态
    - 设备通过 WebSocket 主动发送 device_online 消息注册
    - ✅ 只对手机设备（6100-6199）尝试 ADB 连接
    - ✅ PC 设备（6200-6299）通过 WebSocket 注册，无需 ADB
    """
    logger.info("📡 WebSocket 服务器启动，尝试恢复 ADB 连接...")     
    # 扫描手机设备端口范围（与 DeviceScanner 保持一致）
    MOBILE_PORT_START = 6100
    MOBILE_PORT_END = 6199
    
    connected_count = 0
    checked_ports = 0
    
    # 快速扫描前 20 个手机设备端口（最常用的范围）
    # 完整扫描由 DeviceScanner 负责（每 10 秒）
    for port in range(MOBILE_PORT_START, min(MOBILE_PORT_START + 20, MOBILE_PORT_END + 1)):
        checked_ports += 1
        try:
            # 检查端口是否有FRP监听
            result = subprocess.run(
                ["netstat", "-tln"],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if f":{port}" in result.stdout and "LISTEN" in result.stdout:
                # 发现手机设备 FRP 端口，尝试 ADB 连接
                device_addr = f"localhost:{port}"
                logger.info(f"  📱 发现手机设备 FRP 端口: {port}")
                
                connect_result = subprocess.run(
                    ["adb", "connect", device_addr],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                output = connect_result.stdout.lower()
                if "connected" in output or "already connected" in output:
                    logger.info(f"✅ 恢复 ADB 连接: {device_addr}")
                    connected_count += 1
                else:
                    logger.debug(f"连接失败: {device_addr}")
        except Exception as e:
            logger.debug(f"端口 {port} 检查失败: {e}")
            continue
    
    logger.info(f"快速扫描完成: 检查了 {checked_ports} 个端口，恢复了 {connected_count} 个 ADB 连接")
    logger.info("DeviceScanner 会在 10 秒内进行完整扫描并更新设备状态")
    if connected_count == 0:
        logger.info("如果有设备在线，它们会通过 WebSocket 主动连接并注册") 
@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    # V2: 不再需要心跳超时检测，WebSocket 使用原生 ping/pong 机制
    logger.info(" WebSocket 服务器启动完成（使用原生 ping/pong 机制，ping_interval=30s）")     
    # 【重要】清理残留的 ADB 连接（WebSocket 服务器重启后）
    try:
        from server.services.port_manager import get_port_manager
        port_manager = get_port_manager()
        await port_manager.cleanup_all_adb_connections()
        logger.info(" ADB connections cleaned up in WebSocket server")
    except Exception as e:
     logger.warning(f" Failed to cleanup ADB connections: {e}")     
    # 快速恢复 ADB 连接（与 DeviceScanner 互补）
    # - auto_connect_devices: 服务器重启时立即恢复（扫描前 20 个端口）
    # - DeviceScanner: 持续监控所有端口（每 10 秒扫描 6100-6199）
    await auto_connect_devices()


if __name__ == "__main__":
    import asyncio
    
    # 启动时自动连接设备
    try:
        asyncio.run(auto_connect_devices())
    except Exception as e:
        logger.error(f"自动连接设备失败: {e}")
    
    # 启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9999,
        log_level="info",
        access_log=True
    )

