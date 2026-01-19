#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
PC 控制模块 - 服务端 PC 设备控制

提供 PC 设备的智能控制能力,包括:
- PCAgent: AI 自主操作主逻辑
- PCController: HTTP API 调用封装
- PCPerception: 感知模块
- PCAction: 动作定义
- PCCallback: 任务回调
- PCTask: 任务模型
"""

from .pc_actions import PCAction
from .pc_agent import PCAgent
from .pc_callback import PCCallback
from .pc_controller import PCController
from .pc_perception import PCPerception
from .pc_task import PCTask, PCTaskStatus

__all__ = [
    "PCAgent",
    "PCController",
    "PCPerception",
    "PCAction",
    "PCCallback",
    "PCTask",
    "PCTaskStatus"
]
