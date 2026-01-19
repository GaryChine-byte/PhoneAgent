#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
PC Agent 客户端主程序

在 PC 上运行的代理客户端,通过 FRP 和 WebSocket 连接到服务器。

示例用法:
    from pc_agent import PCAgentClient
    
    client = PCAgentClient("config.yaml")
    await client.start()
"""

import asyncio
import logging
import platform
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    raise ImportError("请安装 pyyaml: pip install pyyaml")

from control_server import ControlServer
from controllers import get_controller
from frp_manager import FrpManager
from websocket_client import WebSocketClient

logger = logging.getLogger(__name__)


class PCAgentClient:
    """
    PC Agent 客户端主类
    
    负责协调各个组件的启动和停止,包括:
    - 控制服务器 (HTTP API)
    - FRP 隧道管理
    - WebSocket 连接
    
    Attributes:
        config (dict): 配置字典
        os_type (str): 操作系统类型
        controller: 平台控制器实例
        control_server: HTTP 控制服务器
        frp_manager: FRP 管理器
        ws_client: WebSocket 客户端
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化 PC Agent 客户端
        
        Args:
            config_path: 配置文件路径
            
        Raises:
            FileNotFoundError: 当配置文件不存在时
            yaml.YAMLError: 当配置文件格式错误时
        """
        # 加载配置
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 检测操作系统
        self.os_type = platform.system()
        logger.info(f"操作系统: {self.os_type}")
        
        # 初始化组件
        self.controller = get_controller()
        self.control_server = ControlServer(
            port=self.config['local_port'],
            controller=self.controller
        )
        self.frp_manager = FrpManager(
            server_addr=self.config['server']['ip'],
            server_port=self.config['server']['frp_port'],
            token=self.config['server']['token'],
            local_port=self.config['local_port'],
            remote_port=self.config['remote_port']
        )
        self.ws_client = WebSocketClient(
            server_url=self.config['server']['websocket_url'],
            device_id=self._get_device_id(),
            frp_port=self.config['remote_port'],
            device_name=self.config['device_name']
        )
    
    def _get_device_id(self) -> str:
        """
        生成设备 ID
        
        Returns:
            设备 ID,格式为 "pc_{系统}_{主机名}"
        """
        return WebSocketClient.generate_device_id()
    
    async def start(self):
        """
        启动客户端
        
        按顺序启动各个组件:
        1. 控制服务器
        2. FRP 隧道
        3. WebSocket 连接
        4. 保持运行
        """
        try:
            # 1. 启动控制服务器
            logger.info("正在启动控制服务器...")
            await self.control_server.start()
            
            # 2. 启动 FRP 隧道
            logger.info("正在启动 FRP 隧道...")
            self.frp_manager.start()
            
            # 等待 FRP 连接成功
            await asyncio.sleep(3)
            
            # 3. 连接 WebSocket
            logger.info("正在连接到 WebSocket...")
            
            # WebSocket 客户端在后台运行
            ws_task = asyncio.create_task(self.ws_client.connect())
            
            # 4. 保持运行
            logger.info("=" * 60)
            logger.info(" PC Agent Client 运行中")
            logger.info(f"   设备 ID: {self._get_device_id()}")
            logger.info(f"   控制端口: {self.config['local_port']}")
            logger.info(f"   FRP 远程端口: {self.config['remote_port']}")
            logger.info("=" * 60)
            
            # 保持主循环
            while True:
                await asyncio.sleep(60)
                # 健康检查
                if not self.frp_manager.is_running():
                    logger.error("FRP 进程已停止,正在重启...")
                    self.frp_manager.start()
                    
        except KeyboardInterrupt:
            logger.info("收到停止信号...")
            await self.stop()
        except Exception as e:
            logger.error(f"运行错误: {e}", exc_info=True)
            await self.stop()
    
    async def stop(self):
        """停止客户端"""
        logger.info("正在停止 PC Agent Client...")
        
        # 关闭 WebSocket
        if self.ws_client:
            await self.ws_client.disconnect()
        
        # 停止 FRP
        if self.frp_manager:
            self.frp_manager.stop()
        
        # 停止控制服务器
        if self.control_server:
            await self.control_server.stop()
        
        logger.info("PC Agent Client 已停止")


async def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 启动客户端
    client = PCAgentClient("config.yaml")
    await client.start()


if __name__ == "__main__":
    asyncio.run(main())
