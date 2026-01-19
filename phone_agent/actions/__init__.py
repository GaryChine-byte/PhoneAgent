#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
Actions package - 统一的动作系统

架构（Phase 4-5 重构后）:
1. 标准动作模型（standard_actions.py）- Pydantic模型定义
2. 动作解析器（parse.py）- dict → Action 转换
3. 动作执行器（action_executor.py）- 统一的ADB执行层

两个内核统一流程：
- XML Kernel: JSON → parse_action() → ActionExecutor → ADB
- Vision Kernel: XML+JSON → ResponseParser → parse_action() → ActionExecutor → ADB

废弃模块（v2.1.0 移除）：
- handler.py: ActionHandler（已被 ActionExecutor 替代）
- vision_format.py: do() 解析器（已被 ResponseParser 替代）
"""

# [DEPRECATED] 保留 ActionHandler 导入（向后兼容，v2.1.0 移除）
# 新代码请使用 ActionExecutor
from phone_agent.actions.handler import ActionHandler

# [OK] 标准动作模型
from phone_agent.actions.standard_actions import (
    # 动作模型
    TapAction,
    InputTextAction,
    SwipeAction,
    LaunchAppAction,
    LongPressAction,
    DoubleTapAction,
    PressKeyAction,
    DragAction,
    ScrollAction,
    KeyEventAction,
    AnswerAction,
    AskUserAction,
    DoneAction,
    RecordImportantContentAction,
    GenerateOrUpdateTodosAction,
    WaitAction,
    # 响应模型
    AgentResponse,
    # 类型
    Action,
    ACTION_MODELS,
    # 工具函数
    parse_action,
    parse_agent_response,
    validate_action_sequence,
)

# [OK] 动作执行器
from phone_agent.actions.action_executor import ActionExecutor

__all__ = [
    # [DEPRECATED] 兼容：ActionHandler（v2.1.0 移除，请使用 ActionExecutor）
    "ActionHandler",
    # [核心] 动作执行器（推荐使用）
    "ActionExecutor",
    # [OK] 标准：动作模型
    "TapAction",
    "InputTextAction",
    "SwipeAction",
    "LaunchAppAction",
    "LongPressAction",
    "DoubleTapAction",
    "PressKeyAction",
    "DragAction",
    "ScrollAction",
    "KeyEventAction",
    "AnswerAction",
    "AskUserAction",
    "DoneAction",
    "RecordImportantContentAction",
    "GenerateOrUpdateTodosAction",
    "WaitAction",
    # 响应模型
    "AgentResponse",
    # 类型
    "Action",
    "ACTION_MODELS",
    # 工具函数
    "parse_action",
    "parse_agent_response",
    "validate_action_sequence",
]

