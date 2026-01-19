#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
Mac 控制器 - 使用 pyautogui + PyObjC

基于 macOS Accessibility API 实现的控制器,支持:
- 鼠标键盘操作 (pyautogui)
- 可访问性树获取 (PyObjC)
- 中文输入支持 (剪贴板)
- 自动 ctrl -> command 转换
"""

import logging
import re
from io import BytesIO
from typing import List, Optional, Tuple

try:
    import pyautogui
    import pyperclip
    from PIL import Image
    from AppKit import NSWorkspace
    from ApplicationServices import (
        AXUIElementCopyAttributeNames,
        AXUIElementCopyAttributeValue,
        AXUIElementCreateSystemWide,
        AXIsProcessTrusted,
    )
except ImportError as e:
    raise ImportError(
        f"Mac 控制器依赖缺失: {e}\n"
        "请安装: pip install pyautogui pyperclip pillow pyobjc-framework-Cocoa pyobjc-framework-Quartz"
    )

from controllers.base_controller import BaseController

logger = logging.getLogger(__name__)


class MacController(BaseController):
    """Mac 平台控制器"""
    
    def __init__(self):
        super().__init__()
        # pyautogui 配置
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0  # ⚠️ 设置为 0，所有延迟由服务端控制（避免阻塞 HTTP 响应）
        
        # 检查 Accessibility 权限
        if not self._check_accessibility():
            logger.warning("⚠️  Accessibility 权限未授予")
            logger.warning("   请在 系统偏好设置 > 安全性与隐私 > 隐私 > 辅助功能 中授权")
        
        logger.info("Mac Controller 初始化成功")
    
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
        - 中文使用剪贴板 (Command+V)
        - 英文直接输入
        """
        try:
            # 处理中文: 使用剪贴板
            if self.contains_chinese(text):
                pyperclip.copy(text)
                pyautogui.hotkey('command', 'v')  # Mac 使用 command
                logger.debug(f"输入中文文本 (剪贴板): {len(text)} 字符")
            else:
                pyautogui.write(text, interval=0.01)
                logger.debug(f"输入英文文本: {len(text)} 字符")
            return True
        except Exception as e:
            logger.error(f"输入文本失败: {e}")
            return False
    
    def press_key(self, key: str, modifiers: Optional[List[str]] = None) -> bool:
        """
        按键操作 (Mac 使用 command 而不是 ctrl)
        
        ⚠️ 不使用 interval 参数，避免阻塞 HTTP 响应
        所有延迟由服务端通过 wait 动作统一控制
        """
        try:
            if modifiers:
                # 自动转换 ctrl -> command
                mac_modifiers = ['command' if m == 'ctrl' else m for m in modifiers]
                # ⚠️ 不使用 interval，快速执行
                pyautogui.hotkey(*mac_modifiers, key)
                logger.debug(f"按键组合: {'+'.join(mac_modifiers + [key])}")
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
        """截图"""
        try:
            screenshot = pyautogui.screenshot()
            
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
        """获取可访问性树 (Mac AX API)"""
        try:
            system_wide = AXUIElementCreateSystemWide()
            workspace = NSWorkspace.sharedWorkspace()
            
            elements = []
            
            # 获取前台应用的 AX 元素
            error, ax_app = AXUIElementCopyAttributeValue(
                system_wide, 
                "AXFocusedApplication", 
                None
            )
            
            if error == 0 and ax_app:
                self._traverse_ax_tree(ax_app, elements, depth=0)
            
            logger.debug(f"获取可访问性树: {len(elements)} 个元素")
            return elements
        
        except Exception as e:
            logger.error(f"获取可访问性树失败: {e}")
            return []
    
    def _traverse_ax_tree(self, element, elements: List[dict], depth: int = 0):
        """递归遍历 AX 树"""
        if depth > 10:
            return
        
        try:
            # 获取角色
            error, role = AXUIElementCopyAttributeValue(element, "AXRole", None)
            if error != 0 or not role:
                return
            
            # 排除冗余角色
            exclude_roles = ["AXGroup", "AXLayoutArea", "AXLayoutItem", "AXUnknown"]
            if str(role) in exclude_roles:
                return
            
            # 获取位置和大小
            error1, position = AXUIElementCopyAttributeValue(element, "AXPosition", None)
            error2, size = AXUIElementCopyAttributeValue(element, "AXSize", None)
            
            if error1 == 0 and error2 == 0 and position and size:
                # 解析坐标 (Mac 返回特殊格式)
                pos_str = str(position)
                size_str = str(size)
                
                try:
                    x = float(pos_str.split("x:")[1].split()[0])
                    y = float(pos_str.split("y:")[1].split()[0])
                    w = float(size_str.split("w:")[1].split()[0])
                    h = float(size_str.split("h:")[1].split()[0])
                    
                    # 获取文本
                    error, title = AXUIElementCopyAttributeValue(element, "AXTitle", None)
                    error, value = AXUIElementCopyAttributeValue(element, "AXValue", None)
                    
                    elements.append({
                        "role": str(role),
                        "title": str(title) if title else "",
                        "text": str(value) if value else "",
                        "position": [int(x), int(y)],
                        "size": [int(w), int(h)]
                    })
                except (IndexError, ValueError):
                    pass
            
            # 递归子元素
            error, children = AXUIElementCopyAttributeValue(element, "AXChildren", None)
            if error == 0 and children:
                for child in children:
                    self._traverse_ax_tree(child, elements, depth + 1)
        
        except Exception:
            pass
    
    def get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕尺寸"""
        try:
            size = pyautogui.size()
            return (size.width, size.height)
        except Exception as e:
            logger.error(f"获取屏幕尺寸失败: {e}")
            return (1920, 1080)  # 默认值
    
    def get_platform_info(self) -> dict:
        """获取 macOS 平台信息"""
        return {
            "os_type": "Darwin",  # macOS 的 platform.system() 返回 "Darwin"
            "ratio": 2.0,  # macOS Retina 屏幕通常是 2.0
            "ctrl_key": "command",  # macOS 使用 command 键
            "search_key": ["command", "space"]  # macOS Spotlight 快捷键
        }
    
    def _check_accessibility(self) -> bool:
        """检查 Accessibility 权限"""
        try:
            return AXIsProcessTrusted()
        except Exception:
            return False
    
    @staticmethod
    def _contains_chinese(text: str) -> bool:
        """检测是否包含中文"""
        return bool(re.search(r'[\u4e00-\u9fff]+', text))
