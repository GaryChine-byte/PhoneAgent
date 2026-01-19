#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
控制器模块 - 跨平台控制接口

提供统一的控制器接口,支持 Windows 和 macOS 平台。
"""

import platform
from controllers.base_controller import BaseController

def get_controller() -> BaseController:
    """
    根据操作系统返回对应的控制器
    
    Returns:
        BaseController: Windows 或 Mac 控制器实例
        
    Raises:
        NotImplementedError: 当操作系统不支持时
    """
    os_type = platform.system()
    
    if os_type == "Windows":
        from controllers.windows_controller import WindowsController
        return WindowsController()
    elif os_type == "Darwin":
        from controllers.mac_controller import MacController
        return MacController()
    else:
        raise NotImplementedError(f"不支持的操作系统: {os_type}")

__all__ = ["BaseController", "get_controller"]
