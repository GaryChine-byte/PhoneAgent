#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
控制服务器 - 提供 HTTP API 接口,接收服务器的控制命令

基于 aiohttp 实现的 HTTP 服务器,提供以下接口:
- /api/control/click - 点击操作
- /api/control/type - 文本输入
- /api/control/key - 按键操作
- /api/control/screenshot - 截图
- /api/control/move - 鼠标移动
- /api/control/scroll - 滚动
- /api/control/perception - 感知信息 (OCR + a11y)
"""

import asyncio
import base64
import logging
from typing import Optional

try:
    from aiohttp import web
except ImportError:
    raise ImportError("请安装 aiohttp: pip install aiohttp")

# 禁用 aiohttp.server 的 BadStatusLine 错误日志（忽略非 HTTP 协议请求）
logging.getLogger('aiohttp.server').setLevel(logging.CRITICAL)
logging.getLogger('aiohttp.access').setLevel(logging.WARNING)

from controllers.base_controller import BaseController

logger = logging.getLogger(__name__)


class ControlServer:
    """HTTP API 控制服务器"""
    
    def __init__(self, port: int, controller: BaseController):
        self.port = port
        self.controller = controller
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        
        # 注册路由
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_post('/api/control/click', self.handle_click)
        self.app.router.add_post('/api/control/type', self.handle_type)
        self.app.router.add_post('/api/control/key', self.handle_key)
        self.app.router.add_post('/api/control/screenshot', self.handle_screenshot)
        self.app.router.add_post('/api/control/move', self.handle_move)
        self.app.router.add_post('/api/control/scroll', self.handle_scroll)
        self.app.router.add_get('/api/control/perception', self.handle_perception)
        self.app.router.add_get('/api/control/screen_size', self.handle_screen_size)
    
    async def start(self):
        """启动服务器"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, 'localhost', self.port)
        await site.start()
        logger.info(f"控制服务器已启动: http://localhost:{self.port}")
    
    async def stop(self):
        """停止服务器"""
        if self.runner:
            await self.runner.cleanup()
            logger.info("控制服务器已停止")
    
    # ==================== API Handlers ====================
    
    async def health_check(self, request):
        """
        健康检查 - 返回设备信息
        
        返回平台信息和坐标比例（参考 MobileAgent）
        """
        import platform
        
        # 从控制器获取平台信息
        platform_info = self.controller.get_platform_info()
        
        return web.json_response({
            "status": "ok",
            "device_type": "pc",
            "os": platform_info["os_type"],
            "os_release": platform.release(),
            "machine": platform.machine(),
            # MobileAgent PC-Agent 兼容参数
            "ratio": platform_info["ratio"],  # 坐标缩放比例 (1=Windows, 2=macOS Retina)
            "ctrl_key": platform_info["ctrl_key"],  # 控制键名称
            "search_key": platform_info["search_key"],  # 搜索快捷键
        })
    
    async def handle_click(self, request):
        """处理点击请求"""
        try:
            data = await request.json()
            x = data['x']
            y = data['y']
            button = data.get('button', 'left')
            clicks = data.get('clicks', 1)
            
            # 执行点击
            success = await asyncio.to_thread(
                self.controller.click, x, y, button, clicks
            )
            
            return web.json_response({
                "success": success,
                "message": f"点击 ({x}, {y})"
            })
        
        except Exception as e:
            logger.error(f"点击错误: {e}", exc_info=True)
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def handle_type(self, request):
        """处理输入请求"""
        try:
            data = await request.json()
            text = data['text']
            
            success = await asyncio.to_thread(
                self.controller.type_text, text
            )
            
            return web.json_response({
                "success": success,
                "message": f"输入 {len(text)} 个字符"
            })
        
        except Exception as e:
            logger.error(f"输入错误: {e}", exc_info=True)
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def handle_key(self, request):
        """处理按键请求"""
        try:
            data = await request.json()
            key = data['key']
            modifiers = data.get('modifiers', [])
            
            success = await asyncio.to_thread(
                self.controller.press_key, key, modifiers
            )
            
            # 构建完整的按键描述
            if modifiers:
                key_desc = "+".join(modifiers + [key])
            else:
                key_desc = key
            
            return web.json_response({
                "success": success,
                "message": f"按键: {key_desc}"
            })
        
        except Exception as e:
            logger.error(f"按键错误: {e}", exc_info=True)
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def handle_screenshot(self, request):
        """处理截图请求"""
        try:
            screenshot_bytes = await asyncio.to_thread(
                self.controller.take_screenshot
            )
            
            # Base64 编码
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            return web.json_response({
                "success": True,
                "image": screenshot_b64,
                "format": "png"
            })
        
        except Exception as e:
            logger.error(f"截图错误: {e}", exc_info=True)
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def handle_move(self, request):
        """处理鼠标移动请求"""
        try:
            data = await request.json()
            x = data['x']
            y = data['y']
            
            success = await asyncio.to_thread(
                self.controller.move_mouse, x, y
            )
            
            return web.json_response({
                "success": success,
                "message": f"移动到 ({x}, {y})"
            })
        
        except Exception as e:
            logger.error(f"移动错误: {e}", exc_info=True)
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def handle_scroll(self, request):
        """处理滚动请求"""
        try:
            data = await request.json()
            clicks = data['clicks']
            
            success = await asyncio.to_thread(
                self.controller.scroll, clicks
            )
            
            return web.json_response({
                "success": success,
                "message": f"滚动 {clicks}"
            })
        
        except Exception as e:
            logger.error(f"滚动错误: {e}", exc_info=True)
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def handle_perception(self, request):
        """处理感知信息请求 (OCR + a11y)"""
        try:
            # 获取当前屏幕截图
            screenshot_bytes = await asyncio.to_thread(
                self.controller.take_screenshot
            )
            
            # 获取可访问性树
            elements = await asyncio.to_thread(
                self.controller.get_accessibility_tree
            )
            
            # 获取屏幕尺寸
            width, height = self.controller.get_screen_size()
            
            return web.json_response({
                "success": True,
                "elements": elements,
                "screenshot_size": len(screenshot_bytes),
                "screen_size": {"width": width, "height": height}
            })
        
        except Exception as e:
            logger.error(f"感知错误: {e}", exc_info=True)
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def handle_screen_size(self, request):
        """获取屏幕尺寸"""
        try:
            width, height = self.controller.get_screen_size()
            
            return web.json_response({
                "success": True,
                "width": width,
                "height": height
            })
        
        except Exception as e:
            logger.error(f"获取屏幕尺寸错误: {e}", exc_info=True)
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
