#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
PC 控制器 - 服务端通过 HTTP API 控制 PC 设备

通过 FRP 隧道调用 PC 客户端的 HTTP API 接口实现远程控制。
"""

import base64
import logging
from typing import Optional

try:
    import httpx
except ImportError:
    raise ImportError("请安装 httpx: pip install httpx")

logger = logging.getLogger(__name__)


class PCController:
    """
    PC 控制器 (服务端)
    
    通过 HTTP API 控制 PC 设备,所有操作通过 FRP 隧道转发。
    
    Attributes:
        device_id (str): 设备 ID
        frp_port (int): FRP 端口
        base_url (str): PC 客户端 API 地址
        client (httpx.AsyncClient): HTTP 客户端
    """
    
    def __init__(self, device_id: str, frp_port: int):
        """
        初始化 PC 控制器
        
        Args:
            device_id: 设备 ID
            frp_port: FRP 端口
        """
        self.device_id = device_id
        self.frp_port = frp_port
        self.base_url = f"http://localhost:{frp_port}"
        # 增加超时时间：connect=5s, read=30s, write=30s, pool=30s
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=30.0)
        )
        
        # 平台信息（从 health_check 获取）
        self.ratio = 1  # 坐标缩放比例
        self.ctrl_key = "ctrl"  # 控制键
        self.search_key = ["win", "s"]  # 搜索快捷键
        self.platform_info = None  # 完整平台信息
        
        logger.info(f"PC 控制器初始化: {device_id}, 端口: {frp_port}")
    
    async def update_platform_info(self):
        """
        更新平台信息（从 health_check 获取）
        
        参考 MobileAgent PC-Agent 的平台检测机制
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            info = response.json()
            
            self.platform_info = info
            self.ratio = info.get("ratio", 1)
            self.ctrl_key = info.get("ctrl_key", "ctrl")
            self.search_key = info.get("search_key", ["win", "s"])
            
            logger.info(f"平台信息已更新: OS={info.get('os')}, ratio={self.ratio}")
        except Exception as e:
            logger.warning(f"获取平台信息失败，使用默认值: {e}")
    
    async def click(self, x: int, y: int, button: str = 'left', clicks: int = 1) -> dict:
        """
        点击操作
        
        参考 MobileAgent PC-Agent:
        - 坐标会根据 ratio 自动缩放
        - macOS Retina: ratio=2, x,y 需要除以 2
        - Windows: ratio=1, 不需要缩放
        
        Args:
            x: X 坐标
            y: Y 坐标
            button: 按钮类型 ('left', 'right', 'middle')
            clicks: 点击次数
            
        Returns:
            操作结果字典
            
        Raises:
            httpx.HTTPError: 当请求失败时
        """
        try:
            # 应用坐标缩放
            scaled_x = int(x // self.ratio)
            scaled_y = int(y // self.ratio)
            
            if self.ratio != 1:
                logger.debug(f"坐标缩放: ({x}, {y}) -> ({scaled_x}, {scaled_y}), ratio={self.ratio}")
            
            response = await self.client.post(
                f"{self.base_url}/api/control/click",
                json={"x": scaled_x, "y": scaled_y, "button": button, "clicks": clicks}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"点击失败: {e}", exc_info=True)
            raise
    
    async def type_text(self, text: str) -> dict:
        """
        输入文本
        
        Args:
            text: 要输入的文本
            
        Returns:
            操作结果字典
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/control/type",
                json={"text": text}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"输入文本失败: {e}", exc_info=True)
            raise
    
    async def press_key(self, key: str, modifiers: Optional[list] = None) -> dict:
        """
        按键操作
        
        Args:
            key: 按键名称
            modifiers: 修饰键列表 (如 ['ctrl', 'shift'])
            
        Returns:
            操作结果字典
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/control/key",
                json={"key": key, "modifiers": modifiers or []}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"按键失败: {e}", exc_info=True)
            raise
    
    async def move_mouse(self, x: int, y: int) -> dict:
        """
        移动鼠标
        
        Args:
            x: X 坐标
            y: Y 坐标
            
        Returns:
            操作结果字典
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/control/move",
                json={"x": x, "y": y}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"移动鼠标失败: {e}", exc_info=True)
            raise
    
    async def scroll(self, clicks: int) -> dict:
        """
        滚动操作
        
        Args:
            clicks: 滚动量 (正数向上,负数向下)
            
        Returns:
            操作结果字典
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/control/scroll",
                json={"clicks": clicks}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"滚动失败: {e}", exc_info=True)
            raise
    
    async def take_screenshot(self) -> bytes:
        """
        截图
        
        Returns:
            PNG 格式的截图字节数据
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/control/screenshot"
            )
            response.raise_for_status()
            data = response.json()
            
            # Base64 解码
            return base64.b64decode(data['image'])
        except Exception as e:
            logger.error(f"截图失败: {e}", exc_info=True)
            raise
    
    async def get_perception_infos(self) -> dict:
        """
        获取感知信息 (OCR + a11y)
        
        Returns:
            包含可访问性树和屏幕信息的字典
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/control/perception"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取感知信息失败: {e}", exc_info=True)
            raise
    
    async def get_screen_size(self) -> tuple:
        """
        获取屏幕尺寸
        
        Returns:
            (width, height) 元组
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/control/screen_size"
            )
            response.raise_for_status()
            data = response.json()
            return (data['width'], data['height'])
        except Exception as e:
            logger.error(f"获取屏幕尺寸失败: {e}", exc_info=True)
            raise
    
    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()
        logger.info(f"PC 控制器已关闭: {self.device_id}")
