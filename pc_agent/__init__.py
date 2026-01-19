#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
PC Agent - 电脑远程控制客户端

通过 FRP + WebSocket 架构实现 PC 端的远程控制,支持 Windows 和 macOS 平台。

主要功能:
- 跨平台控制器 (Windows/Mac)
- FRP 隧道管理
- WebSocket 设备注册
- HTTP 控制服务器

示例用法:
    from pc_agent import PCAgentClient
    
    client = PCAgentClient("config.yaml")
    await client.start()
"""

__version__ = "0.1.0"
__author__ = "PhoneAgent-Enterprise Team"

from pc_agent_client import PCAgentClient

__all__ = ["PCAgentClient"]
