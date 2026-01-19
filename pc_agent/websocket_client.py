#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
WebSocket 客户端 - 连接到服务器,注册设备和保持心跳

负责与服务器建立 WebSocket 连接,完成设备注册和心跳保活。
支持自动重连机制。
"""

import asyncio
import json
import logging
import platform
import socket
from typing import Optional

try:
    import websockets
except ImportError:
    raise ImportError("请安装 websockets: pip install websockets")

logger = logging.getLogger(__name__)


class WebSocketClient:
    """WebSocket 客户端"""
    
    def __init__(self, server_url: str, device_id: str, frp_port: int, device_name: str):
        # 拼接完整的 WebSocket URL（包含 frp_port）
        base_url = server_url.rstrip('/')
        self.server_url = f"{base_url}/{frp_port}"
        
        self.device_id = device_id
        self.frp_port = frp_port
        self.device_name = device_name
        
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        
        logger.info(f"WebSocket 客户端初始化: {self.server_url}")
    
    async def connect(self):
        """连接到服务器"""
        self.running = True
        
        while self.running:
            try:
                logger.info(f"正在连接到 {self.server_url}...")
                
                # ✅ 关键修复：使用原生 WebSocket ping，与手机端架构一致
                async with websockets.connect(
                    self.server_url,
                    ping_interval=30,    # 每 30 秒自动发送 ping（与手机端一致）
                    ping_timeout=10,     # 10 秒没有 pong 就断开
                    close_timeout=10
                ) as ws:
                    self.ws = ws
                    logger.info("WebSocket 已连接")
                    
                    # 发送注册消息
                    await self._register()
                    
                    # 保持连接和心跳
                    await self._keep_alive()
            
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket 连接已关闭,正在重连...")
                await asyncio.sleep(5)
            
            except Exception as e:
                logger.error(f"WebSocket 错误: {e}", exc_info=True)
                await asyncio.sleep(5)
    
    async def _register(self):
        """注册设备"""
        try:
            # 获取系统信息
            os_info = {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "processor": platform.processor(),
            }
            
            # 构建符合服务端要求的注册消息
            register_msg = {
                "type": "device_online",  # 服务端期望的类型
                "specs": {  # 服务端期望数据在 specs 字段中
                    "device_id": self.device_id,
                    "frp_port": self.frp_port,
                    "device_name": self.device_name,
                    "device_type": "pc",
                    "os_info": os_info,
                    "model": f"{platform.system()} {platform.release()}",
                    "android_version": platform.release(),  # 对 PC 是系统版本
                    "screen_resolution": "unknown",  # PC 端暂时不提供
                }
            }
            
            await self.ws.send(json.dumps(register_msg))
            logger.info(f"发送注册消息: device_id={self.device_id}, frp_port={self.frp_port}")
            
            # 等待服务端确认
            response = await asyncio.wait_for(self.ws.recv(), timeout=10.0)
            response_data = json.loads(response)
            
            if response_data.get("type") == "registered":
                logger.info(f"设备注册成功: {response_data.get('device_id')}")
            else:
                logger.warning(f"收到意外的响应: {response_data}")
        
        except Exception as e:
            logger.error(f"注册失败: {e}", exc_info=True)
    
    async def _keep_alive(self):
        """保持连接和接收消息"""
        # 注意：心跳由 websockets 库自动处理（ping_interval=30）
        # 这里只负责接收和处理服务器消息
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type", "")
                    
                    if msg_type == "ping":
                        # 响应服务端的 JSON ping（如果有）
                        await self.ws.send(json.dumps({"type": "pong"}))
                        logger.debug("💓 JSON ping 响应")
                    
                    elif msg_type == "pong":
                        # 收到 JSON pong
                        logger.debug("💓 JSON pong 收到")
                    
                    elif msg_type == "registered":
                        logger.info("注册确认")
                    
                    elif msg_type == "command":
                        # 处理服务器命令
                        logger.info(f"收到命令: {data}")
                        # TODO: 处理命令
                    
                    else:
                        logger.debug(f"收到消息: {msg_type}")
                
                except json.JSONDecodeError:
                    logger.warning(f"无法解析消息: {message}")
                except Exception as e:
                    logger.error(f"处理消息错误: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket 连接已关闭")
        except Exception as e:
            logger.error(f"保持连接错误: {e}")
    
    async def disconnect(self):
        """断开连接"""
        self.running = False
        if self.ws:
            await self.ws.close()
            logger.info("WebSocket 已断开")
    
    @staticmethod
    def generate_device_id() -> str:
        """生成设备 ID"""
        hostname = socket.gethostname()
        os_type = platform.system().lower()
        return f"pc_{os_type}_{hostname}"
