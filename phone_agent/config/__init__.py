#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
Phone Agent 配置模块

导出内容:
  - APP_PACKAGES: 静态应用包名映射字典（兜底）
  - SYSTEM_PROMPT: 系统提示词
  - get_app_manager: 获取应用配置管理器（推荐使用）

使用建议:
  旧代码（静态查询）:
    from phone_agent.config import APP_PACKAGES
    package = APP_PACKAGES.get("微信")
  
  新代码（动态配置）:
    from phone_agent.config import get_app_manager
    manager = get_app_manager()
    app = manager.find_app("微信")  # 支持中文/英文/别名
    if app and app.enabled:
        package = app.package_name
"""

from phone_agent.config.apps import APP_PACKAGES
from phone_agent.config.prompts import SYSTEM_PROMPT
from phone_agent.config.app_manager import get_app_manager

__all__ = [
    "APP_PACKAGES",      # 静态字典（向后兼容）
    "SYSTEM_PROMPT",     # 系统提示词
    "get_app_manager",   # 动态配置管理器（推荐）
]
