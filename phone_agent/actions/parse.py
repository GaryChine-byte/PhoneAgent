#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
通用动作解析器

将标准JSON字典转换为Action对象
支持XML Kernel和所有直接输出JSON的场景

职责：
- 解析标准JSON格式 {"action": "tap", "coordinates": [x, y], ...}
- 创建对应的Action对象
- 类型验证和参数检查

注意：
- 坐标使用归一化格式 (0-1000)
- 动作名不区分大小写
"""

from typing import Any
from phone_agent.actions.standard_actions import (
    Action,
    TapAction,
    InputTextAction,
    SwipeAction,
    LaunchAppAction,
    LongPressAction,
    DoubleTapAction,
    PressKeyAction,
    WaitAction,
    DragAction,
    ScrollAction,
    KeyEventAction,
    AnswerAction,
    AskUserAction,
    DoneAction,
    RecordImportantContentAction,
    GenerateOrUpdateTodosAction,
    ReadClipboardAction,
    WriteClipboardAction,
)


def parse_action(action_dict: dict[str, Any]) -> Action:
    """
    解析标准JSON格式的动作
    
    Args:
        action_dict: 动作字典，必须包含 "action" 字段
            示例: {"action": "tap", "coordinates": [500, 500], "reason": "点击按钮"}
    
    Returns:
        对应的 Action 对象
        
    Raises:
        ValueError: 当动作类型未知或参数无效时
    
    示例:
        >>> action = parse_action({"action": "tap", "coordinates": [500, 500]})
        >>> isinstance(action, TapAction)
        True
    """
    action_name = action_dict.get("action", "").lower()
    
    # ============================================
    # 基础动作 (10种)
    # ============================================
    
    if action_name == "tap":
        return TapAction(
            coordinates=action_dict.get("coordinates"),
            index=action_dict.get("index"),
            reason=action_dict.get("reason", "")
        )
    
    elif action_name in ["type", "input_text"]:
        return InputTextAction(
            text=action_dict.get("text", ""),
            index=action_dict.get("index"),
            reason=action_dict.get("reason", "")
        )
    
    elif action_name == "swipe":
        return SwipeAction(
            start=action_dict.get("start"),
            end=action_dict.get("end"),
            direction=action_dict.get("direction"),
            duration=action_dict.get("duration", 300),
            reason=action_dict.get("reason", "")
        )
    
    elif action_name in ["launch", "launch_app"]:
        return LaunchAppAction(
            app_name=action_dict.get("app", action_dict.get("app_name", "")),
            reason=action_dict.get("reason", "")
        )
    
    elif action_name in ["long_press", "longpress"]:
        return LongPressAction(
            coordinates=action_dict.get("coordinates"),
            index=action_dict.get("index"),
            duration=action_dict.get("duration", 3000),
            reason=action_dict.get("reason", "")
        )
    
    elif action_name in ["double_tap", "doubletap"]:
        return DoubleTapAction(
            coordinates=action_dict.get("coordinates"),
            index=action_dict.get("index"),
            reason=action_dict.get("reason", "")
        )
    
    elif action_name == "back":
        return PressKeyAction(
            key="back",
            reason=action_dict.get("reason", "")
        )
    
    elif action_name == "home":
        return PressKeyAction(
            key="home",
            reason=action_dict.get("reason", "")
        )
    
    elif action_name == "wait":
        # 支持两种格式：seconds (float) 或 duration (string)
        duration_value = action_dict.get("duration", action_dict.get("seconds", 1.0))
        if isinstance(duration_value, str):
            try:
                seconds = float(duration_value.split()[0])
            except:
                seconds = 1.0
        else:
            seconds = float(duration_value)
        
        return WaitAction(
            seconds=seconds,
            reason=action_dict.get("reason", "")
        )
    
    elif action_name == "done":
        return DoneAction(
            message=action_dict.get("message", action_dict.get("reason", "任务完成")),
            success=action_dict.get("success", True),
            data=action_dict.get("data")
        )
    
    # ============================================
    # 高级动作 (7种)
    # ============================================
    
    elif action_name == "drag":
        return DragAction(
            start=action_dict.get("start"),
            end=action_dict.get("end"),
            start_index=action_dict.get("start_index"),
            end_index=action_dict.get("end_index"),
            duration=action_dict.get("duration", 500),
            reason=action_dict.get("reason", "")
        )
    
    elif action_name == "scroll":
        return ScrollAction(
            coordinates=action_dict.get("coordinates"),
            value=action_dict.get("value", 0),
            reason=action_dict.get("reason", "")
        )
    
    elif action_name in ["key_event", "keyevent"]:
        return KeyEventAction(
            key=action_dict.get("key", "KEYCODE_ENTER"),
            reason=action_dict.get("reason", "")
        )
    
    elif action_name == "answer":
        return AnswerAction(
            answer=action_dict.get("answer", ""),
            success=action_dict.get("success", True),
            data=action_dict.get("data"),
            reason=action_dict.get("reason", "")
        )
    
    elif action_name in ["ask_user", "askuser"]:
        return AskUserAction(
            question=action_dict.get("question", ""),
            options=action_dict.get("options"),
            reason=action_dict.get("reason", "")
        )
    
    elif action_name in ["record_important_content", "record"]:
        return RecordImportantContentAction(
            content=action_dict.get("content", ""),
            category=action_dict.get("category", ""),
            reason=action_dict.get("reason", "")
        )
    
    elif action_name in ["generate_or_update_todos", "todos"]:
        return GenerateOrUpdateTodosAction(
            todos=action_dict.get("todos", ""),
            reason=action_dict.get("reason", "")
        )
    
    elif action_name == "read_clipboard":
        return ReadClipboardAction(
            reason=action_dict.get("reason", "")
        )
    
    elif action_name == "write_clipboard":
        return WriteClipboardAction(
            text=action_dict.get("text", ""),
            reason=action_dict.get("reason", "")
        )
    
    else:
        raise ValueError(f"Unknown action: {action_name}")


__all__ = ["parse_action"]
