#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
基础控制器 - 定义跨平台控制接口

定义了所有平台控制器必须实现的抽象接口,包括鼠标、键盘、截图等操作。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
import re


class BaseController(ABC):
    """控制器抽象基类"""
    
    @staticmethod
    def contains_chinese(text: str) -> bool:
        """
        检测文本是否包含中文字符
        
        参考 MobileAgent PC-Agent 实现
        
        Args:
            text: 待检测文本
            
        Returns:
            是否包含中文
        """
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
        return chinese_pattern.search(text) is not None
    
    @abstractmethod
    def click(self, x: int, y: int, button: str = 'left', clicks: int = 1) -> bool:
        """
        点击指定坐标
        
        Args:
            x: X 坐标
            y: Y 坐标
            button: 按钮类型 ('left', 'right', 'middle')
            clicks: 点击次数
            
        Returns:
            是否成功
        """
        pass
    
    @abstractmethod
    def type_text(self, text: str) -> bool:
        """
        输入文本
        
        Args:
            text: 要输入的文本
            
        Returns:
            是否成功
        """
        pass
    
    @abstractmethod
    def press_key(self, key: str, modifiers: Optional[List[str]] = None) -> bool:
        """
        按键
        
        Args:
            key: 按键名称
            modifiers: 修饰键列表 (如 ['ctrl', 'shift'])
            
        Returns:
            是否成功
        """
        pass
    
    @abstractmethod
    def move_mouse(self, x: int, y: int) -> bool:
        """
        移动鼠标
        
        Args:
            x: X 坐标
            y: Y 坐标
            
        Returns:
            是否成功
        """
        pass
    
    @abstractmethod
    def scroll(self, clicks: int) -> bool:
        """
        滚动
        
        Args:
            clicks: 滚动量 (正数向上,负数向下)
            
        Returns:
            是否成功
        """
        pass
    
    @abstractmethod
    def take_screenshot(self) -> bytes:
        """
        截图
        
        Returns:
            PNG 格式的截图字节数据
        """
        pass
    
    @abstractmethod
    def get_accessibility_tree(self) -> List[dict]:
        """
        获取可访问性树
        
        Returns:
            元素列表,每个元素包含:
            - role: 角色类型
            - text: 文本内容
            - title: 标题
            - position: [x, y]
            - size: [width, height]
        """
        pass
    
    @abstractmethod
    def get_screen_size(self) -> Tuple[int, int]:
        """
        获取屏幕尺寸
        
        Returns:
            (width, height)
        """
        pass
    
    @abstractmethod
    def get_platform_info(self) -> dict:
        """
        获取平台信息
        
        Returns:
            包含以下字段的字典:
            - os_type: 操作系统类型 ("Windows", "Darwin" 等)
            - ratio: 坐标缩放比例 (Windows: 1.0, macOS Retina: 2.0)
            - ctrl_key: 控制键名称 ("ctrl", "command")
            - search_key: 搜索快捷键 (["win", "s"] 或 ["command", "space"])
        """
        pass
