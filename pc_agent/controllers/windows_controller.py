#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
Windows 控制器 - 使用 pyautogui + pywinauto

基于 Windows UIA (UI Automation) 实现的控制器,支持:
- 鼠标键盘操作 (pyautogui)
- 可访问性树获取 (pywinauto)
- 中文输入支持 (剪贴板)
"""

import logging
import re
import time
from io import BytesIO
from typing import List, Optional, Tuple

try:
    import pyautogui
    import pyperclip
    from PIL import Image
    from pywinauto import Desktop
    import win32gui
except ImportError as e:
    raise ImportError(
        f"Windows 控制器依赖缺失: {e}\n"
        "请安装: pip install pyautogui pyperclip pillow pywinauto pywin32"
    )

from controllers.base_controller import BaseController

logger = logging.getLogger(__name__)


class WindowsController(BaseController):
    """Windows 平台控制器"""
    
    def __init__(self):
        super().__init__()
        # pyautogui 配置
        pyautogui.FAILSAFE = False  # 禁用安全模式
        pyautogui.PAUSE = 0         # ⚠️ 设置为 0，所有延迟由服务端控制（避免阻塞 HTTP 响应）
        
        logger.info("Windows Controller 初始化成功")
    
    def click(self, x: int, y: int, button: str = 'left', clicks: int = 1) -> bool:
        """点击指定坐标"""
        try:
            pyautogui.click(x, y, clicks=clicks, button=button)
            logger.debug(f"点击: ({x}, {y}), 按钮={button}, 次数={clicks}")
            return True
        except Exception as e:
            logger.error(f"点击失败: {e}")
            return False
    
    def type_text(self, text: str) -> bool:
        """
        输入文本 (支持中文)
        
        参考 MobileAgent PC-Agent 实现:
        - 中文使用剪贴板 (Ctrl+V)
        - 英文直接输入
        
        ⚠️ 不使用 interval 参数，避免阻塞 HTTP 响应
        """
        try:
            # 处理中文: 使用剪贴板
            if self.contains_chinese(text):
                pyperclip.copy(text)
                pyautogui.hotkey('ctrl', 'v')
                logger.debug(f"输入中文文本 (剪贴板): {len(text)} 字符")
            else:
                pyautogui.write(text)  # ⚠️ 移除 interval，快速输入
                logger.debug(f"输入英文文本: {len(text)} 字符")
            return True
        except Exception as e:
            logger.error(f"输入文本失败: {e}")
            return False
    
    def press_key(self, key: str, modifiers: Optional[List[str]] = None) -> bool:
        """
        按键操作
        
        ⚠️ 不使用 interval 参数，避免阻塞 HTTP 响应
        所有延迟由服务端通过 wait 动作统一控制
        """
        try:
            if modifiers:
                # ⚠️ 不使用 interval，快速执行
                pyautogui.hotkey(*modifiers, key)
                logger.debug(f"按键组合: {'+'.join(modifiers + [key])}")
            else:
                pyautogui.press(key)
                logger.debug(f"按键: {key}")
            return True
        except Exception as e:
            logger.error(f"按键失败: {e}")
            return False
    
    def move_mouse(self, x: int, y: int) -> bool:
        """移动鼠标"""
        try:
            pyautogui.moveTo(x, y)
            logger.debug(f"移动鼠标到: ({x}, {y})")
            return True
        except Exception as e:
            logger.error(f"移动鼠标失败: {e}")
            return False
    
    def scroll(self, clicks: int) -> bool:
        """滚动"""
        try:
            pyautogui.scroll(clicks)
            logger.debug(f"滚动: {clicks}")
            return True
        except Exception as e:
            logger.error(f"滚动失败: {e}")
            return False
    
    def take_screenshot(self) -> bytes:
        """
        截图 (使用多种备选方案)
        
        Windows 截图可能失败的原因:
        1. 远程桌面会话
        2. 屏幕锁定
        3. DPI 缩放问题
        4. 权限不足
        """
        try:
            # 方案 1: 使用 pyautogui (最快)
            try:
                screenshot = pyautogui.screenshot()
            except OSError as e:
                logger.warning(f"pyautogui 截图失败 ({e}), 尝试备选方案...")
                
                # 方案 2: 直接使用 PIL ImageGrab (避免多屏问题)
                from PIL import ImageGrab
                try:
                    screenshot = ImageGrab.grab(all_screens=False)  # 只截主屏幕
                except Exception as e2:
                    logger.warning(f"PIL ImageGrab 单屏截图失败 ({e2}), 尝试 mss...")
                    
                    # 方案 3: 使用 mss (最兼容，但需要额外依赖)
                    try:
                        import mss
                        with mss.mss() as sct:
                            monitor = sct.monitors[1]  # 主显示器
                            sct_img = sct.grab(monitor)
                            from PIL import Image
                            screenshot = Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')
                    except ImportError:
                        logger.error("mss 库未安装，无法截图。请运行: pip install mss")
                        raise RuntimeError("所有截图方案均失败，请检查权限或安装 mss 库")
                    except Exception as e3:
                        logger.error(f"mss 截图也失败: {e3}")
                        raise RuntimeError("所有截图方案均失败")
            
            # 转换为字节
            buffer = BytesIO()
            screenshot.save(buffer, format='PNG')
            screenshot_bytes = buffer.getvalue()
            
            logger.debug(f"截图成功: {len(screenshot_bytes)} 字节")
            return screenshot_bytes
        
        except Exception as e:
            logger.error(f"截图失败: {e}")
            raise
    
    def get_accessibility_tree(self) -> List[dict]:
        """获取可访问性树 (Windows UIA)"""
        try:
            desktop = Desktop(backend="uia")
            foreground_hwnd = win32gui.GetForegroundWindow()
            tree = desktop.window(handle=foreground_hwnd)
            
            elements = []
            exclude_roles = ["Pane", "Group", "Unknown"]
            
            def traverse(element, depth=0):
                """递归遍历元素树"""
                if depth > 10:  # 限制深度
                    return
                
                try:
                    role = element.element_info.control_type
                    if role in exclude_roles:
                        return
                    
                    rect = element.rectangle()
                    text = element.window_text()
                    title = element.element_info.name
                    
                    # 只保留有效元素
                    if rect.width() > 0 and rect.height() > 0:
                        elements.append({
                            "role": role,
                            "text": text,
                            "title": title,
                            "position": [rect.left, rect.top],
                            "size": [rect.width(), rect.height()]
                        })
                    
                    # 递归遍历子元素
                    for child in element.children():
                        traverse(child, depth + 1)
                
                except Exception:
                    pass
            
            traverse(tree)
            logger.debug(f"获取可访问性树: {len(elements)} 个元素")
            return elements
        
        except Exception as e:
            logger.error(f"获取可访问性树失败: {e}")
            return []
    
    def get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕尺寸"""
        try:
            size = pyautogui.size()
            return (size.width, size.height)
        except Exception as e:
            logger.error(f"获取屏幕尺寸失败: {e}")
            return (1920, 1080)  # 默认值
    
    def get_platform_info(self) -> dict:
        """获取 Windows 平台信息"""
        return {
            "os_type": "Windows",
            "ratio": 1.0,  # Windows 通常不需要坐标缩放
            "ctrl_key": "ctrl",
            "search_key": ["win", "s"]  # Windows 搜索快捷键
        }
    
    @staticmethod
    def _contains_chinese(text: str) -> bool:
        """检测是否包含中文"""
        return bool(re.search(r'[\u4e00-\u9fff]+', text))
