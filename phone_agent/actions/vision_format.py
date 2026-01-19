#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
Vision Kernel 格式转换工具（已废弃）

⚠️ [DEPRECATED] 此模块将在 v2.1.0 移除 ⚠️

Phase 4-5 重构后，新架构不再需要此模块：
- 新：模型直接输出 JSON → ResponseParser → parse_action
- 旧：模型输出 do() → parse_vision_action → convert_to_standard_action

迁移指南：
- 新代码：直接使用 `from phone_agent.actions import parse_action`
- 旧测试：暂时保留兼容，但会记录 DeprecationWarning

详见：PHASE45_REFACTOR_COMPLETE_READY_FOR_SERVER.md
"""

import ast
import re
import warnings
from typing import Any

# ==================== 废弃声明 ====================
# 此模块将在 v2.1.0 移除
# 警告在函数调用时触发，避免导入时污染日志
# ================================================


def parse_vision_action(response: str) -> dict[str, Any]:
    """
    从 Vision Kernel 响应中解析动作（已废弃）
    
    [DEPRECATED] 此函数将在 v2.1.0 移除
    
    原因：
    - Phase 4-5 重构后，模型直接输出 JSON dict
    - 不再需要 do() 字符串格式
    - ResponseParser 已接管格式识别
    
    迁移：
    - 旧代码: parse_vision_action("do(action='tap', ...)")
    - 新代码: parse_action({"action": "tap", ...})
    
    支持格式：
    - do(action="tap", element=[500, 500])
    - do(action="done", message="任务完成")
    - finish(message="...") [已废弃，仅作容错处理]
    
    Args:
        response: 来自模型的原始响应字符串
    
    Returns:
        解析后的动作字典，包含 _metadata 字段
        
    Raises:
        ValueError: 当响应无法解析时
    """
    # 发出废弃警告
    warnings.warn(
        "parse_vision_action() 已废弃，将在 v2.1.0 移除。"
        "请更新提示词使用 JSON 格式，并直接调用 parse_action(dict)。",
        DeprecationWarning,
        stacklevel=2
    )
    response = response.strip()
    
    try:
        # 方法1: AST解析(最安全)
        tree = ast.parse(response, mode='eval')
        
        if not isinstance(tree.body, ast.Call):
            raise ValueError("响应必须是函数调用")
        
        func_name = tree.body.func.id if isinstance(tree.body.func, ast.Name) else None
        
        if func_name not in ['do', 'finish']:
            raise ValueError(f"未知函数: {func_name}")
        
        # 安全提取参数
        args = {}
        for keyword in tree.body.keywords:
            arg_name = keyword.arg
            try:
                arg_value = ast.literal_eval(keyword.value)
            except (ValueError, SyntaxError):
                if isinstance(keyword.value, ast.Constant):
                    arg_value = keyword.value.value
                elif isinstance(keyword.value, ast.List):
                    arg_value = [ast.literal_eval(el) for el in keyword.value.elts]
                else:
                    raise ValueError(f"无法解析参数: {arg_name}")
            
            args[arg_name] = arg_value
        
        args["_metadata"] = func_name
        return args
        
    except Exception as e:
        # 降级到正则表达式解析
        try:
            return _parse_with_regex(response)
        except Exception as fallback_error:
            raise ValueError(f"解析动作失败. AST错误: {e}, 正则错误: {fallback_error}")


def _parse_with_regex(response: str) -> dict[str, Any]:
    """正则表达式降级解析器"""
    func_match = re.match(r'^(do|finish)\((.*)\)$', response, re.DOTALL)
    if not func_match:
        raise ValueError(f"无效的动作格式: {response}")
    
    func_name = func_match.group(1)
    args_str = func_match.group(2)
    args = {}
    
    if func_name == "finish":
        message_match = re.search(r'message\s*=\s*["\'](.+?)["\']', args_str)
        if message_match:
            args["message"] = message_match.group(1)
    else:
        # action="Launch"
        action_match = re.search(r'action\s*=\s*["\'](\w+)["\']', args_str)
        if action_match:
            args["action"] = action_match.group(1)
        
        # app/text/message
        for field in ["app", "text", "message"]:
            match = re.search(rf'{field}\s*=\s*["\'](.+?)["\']', args_str)
            if match:
                args[field] = match.group(1)
        
        # element/start/end=[x,y]
        for field in ["element", "start", "end"]:
            match = re.search(rf'{field}\s*=\s*\[(\d+)\s*,\s*(\d+)\]', args_str)
            if match:
                args[field] = [int(match.group(1)), int(match.group(2))]
    
    args["_metadata"] = func_name
    return args


def convert_to_standard_action(action: dict) -> 'Action':
    """
    将 Vision Kernel 动作字典转换为标准 Action 对象（已废弃）
    
    [DEPRECATED] 此函数将在 v2.1.0 移除
    
    原因：
    - Phase 4 重构后，ResponseParser 直接返回标准 dict
    - vision_agent.py 直接调用 parse_action(dict)
    - 不再需要 element/finish 等映射（提示词已修正）
    
    迁移：
    - 旧代码: convert_to_standard_action({"action": "tap", "element": [x, y]})
    - 新代码: parse_action({"action": "tap", "coordinates": [x, y]})
    
    职责：
    1. 处理 Vision Kernel 特殊字段映射
       - "element" → "coordinates"  
       - 动作名首字母大写 → 小写
    2. 调用通用解析器创建 Action 对象
    
    Args:
        action: Vision Kernel 解析后的动作字典
        
    Returns:
        标准 Action 对象
    """
    # 发出废弃警告
    warnings.warn(
        "convert_to_standard_action() 已废弃，将在 v2.1.0 移除。"
        "请直接调用 parse_action(dict)。",
        DeprecationWarning,
        stacklevel=2
    )
    from phone_agent.actions.parse import parse_action
    
    # 复制字典，避免修改原始数据
    normalized = action.copy()
    
    # 0. 容错处理：finish() 已废弃，自动转换为 done 动作
    if normalized.get("_metadata") == "finish":
        normalized["action"] = "done"
        # finish 的 message 参数对应 done 的 message 参数（无需映射）
    
    # 1. 字段名映射：Vision Kernel 使用 "element"，标准格式是 "coordinates"
    if "element" in normalized:
        normalized["coordinates"] = normalized.pop("element")
    
    # 2. 动作名映射：Vision Kernel 首字母大写，标准格式小写
    if "action" in normalized:
        action_name = normalized["action"]
        # 特殊处理带空格的动作名
        action_name = action_name.replace(" ", "_")  # "Double Tap" → "Double_Tap"
        normalized["action"] = action_name.lower()   # "Double_Tap" → "double_tap"
        
        # 容错：finish → done（已废弃，仅作容错）
        if normalized["action"] == "finish":
            normalized["action"] = "done"
    
    # 3. 参数名映射：Vision Kernel 使用 "app"，标准格式也是 "app"（无需映射）
    # 4. 参数名映射：根据动作类型处理 message 字段
    #    - done 动作：保持 message（DoneAction 使用 message）
    #    - 其他动作：message → reason（如 TapAction 等使用 reason）
    if "message" in normalized and normalized.get("action") != "done":
        if "reason" not in normalized:
            normalized["reason"] = normalized.pop("message")
    
    # 5. Scroll 特殊处理：Vision 使用 x,y,direction,distance，标准使用 coordinates,value
    if normalized.get("action") == "scroll":
        if "x" in normalized and "y" in normalized:
            normalized["coordinates"] = [normalized.pop("x"), normalized.pop("y")]
        if "direction" in normalized and "distance" in normalized:
            direction = normalized.pop("direction")
            distance = normalized.pop("distance")
            normalized["value"] = distance if direction in ["up", "right"] else -distance
    
    # 6. Key_Event 特殊处理：移除 KEYCODE_ 前缀
    if normalized.get("action") == "key_event":
        key = normalized.get("key", "")
        if key.startswith("KEYCODE_"):
            normalized["key"] = key[8:].lower()
    
    # 7. 调用通用解析器
    return parse_action(normalized)


# 辅助函数（兼容性）
def do(**kwargs) -> dict[str, Any]:
    """
    创建'do'动作的辅助函数（已废弃）
    
    [DEPRECATED] 此函数将在 v2.1.0 移除
    仅用于测试和向后兼容，新代码请直接使用 dict
    """
    warnings.warn(
        "do() 辅助函数已废弃，将在 v2.1.0 移除。请直接使用 dict。",
        DeprecationWarning,
        stacklevel=2
    )
    kwargs["_metadata"] = "do"
    return kwargs


def finish(**kwargs) -> dict[str, Any]:
    """
    创建'finish'动作的辅助函数（已废弃）
    
    [DEPRECATED] 此函数将在 v2.1.0 移除
    - finish 动作已废弃，请使用 done
    - 仅用于测试和向后兼容
    """
    warnings.warn(
        "finish() 动作已废弃，将在 v2.1.0 移除。请使用 done 动作。",
        DeprecationWarning,
        stacklevel=2
    )
    kwargs["_metadata"] = "finish"
    return kwargs
