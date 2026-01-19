#!/usr/bin/env python3
# Original: Copyright (c) 2024 ZAI Organization (Apache-2.0)
# Modified: Copyright (C) 2025 PhoneAgent Contributors (AGPL-3.0)
# Based on: https://github.com/zai-org/Open-AutoGLM

"""
动作处理器 - 处理AI模型输出（已废弃）

⚠️ [DEPRECATED] 此模块将在 v2.1.0 移除 ⚠️

Phase 4-5 重构后，ActionHandler 已被完全替代：
- 旧：Vision Kernel → ActionHandler → ADB
- 新：Vision Kernel → ResponseParser → parse_action → ActionExecutor

迁移指南：
- 解析：使用 ResponseParser.parse() 或 vision_format.parse_vision_action()
- 执行：使用 ActionExecutor.execute()

详见：PHASE45_REFACTOR_COMPLETE_READY_FOR_SERVER.md
"""

import time
from dataclasses import dataclass
from typing import Any, Callable

from phone_agent.adb import (
    back,
    clear_text,
    detect_and_set_adb_keyboard,
    double_tap,
    home,
    launch_app,
    long_press,
    restore_keyboard,
    swipe,
    tap,
    type_text,
)


@dataclass
class ActionResult:
    """动作执行结果"""

    success: bool
    should_finish: bool
    message: str | None = None
    requires_confirmation: bool = False


class ActionHandler:
    """
    Vision Kernel 格式适配器（已废弃）
    
    [DEPRECATED] 此类将在 v2.1.0 移除
    
    原职责:
    1. 解析 Vision Kernel 格式 (do(action="Tap", element=[x,y]))
    2. 转换为标准 Action 对象（保持归一化坐标）
    3. 委托给 ActionExecutor 执行
    4. 处理特殊动作 (finish, takeover等)
    
    替代方案：
    - 解析：ResponseParser.parse() 或 vision_format.parse_vision_action()
    - 执行：ActionExecutor.execute()
    - Take_over：需手动实现回调逻辑（未来考虑加入 ActionExecutor）

    Args:
        device_id: ADB设备ID(可选),用于多设备场景
        confirmation_callback: 敏感操作确认回调(可选)
            返回True继续执行,返回False取消操作
        takeover_callback: 接管请求回调(可选),用于登录、验证码等场景
    """

    def __init__(
        self,
        device_id: str | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
    ):
        warnings.warn(
            "ActionHandler 已废弃，将在 v2.1.0 移除。"
            "请使用 ResponseParser + ActionExecutor 替代。",
            DeprecationWarning,
            stacklevel=2
        )
        self.device_id = device_id
        self.confirmation_callback = confirmation_callback or self._default_confirmation
        self.takeover_callback = takeover_callback or self._default_takeover
        
        # 核心执行器（延迟初始化，需要屏幕尺寸）
        self._executor = None

    def execute(
        self, action: dict[str, Any], screen_width: int, screen_height: int
    ) -> ActionResult:
        """
        执行AI模型输出的动作
        
        优化: 内部委托给 ActionExecutor 执行

        Args:
            action: 来自模型的动作字典
            screen_width: 当前屏幕宽度(像素)
            screen_height: 当前屏幕高度(像素)

        Returns:
            ActionResult 表示执行是否成功以及是否应该结束
        """
        # 延迟初始化 ActionExecutor（需要屏幕尺寸）
        if self._executor is None:
            from phone_agent.actions import ActionExecutor
            self._executor = ActionExecutor(
                device_id=self.device_id,
                screen_width=screen_width,
                screen_height=screen_height
            )
        
        action_type = action.get("_metadata")

        # 处理特殊动作: finish
        if action_type == "finish":
            return ActionResult(
                success=True, should_finish=True, message=action.get("message")
            )

        if action_type != "do":
            return ActionResult(
                success=False,
                should_finish=True,
                message=f"Unknown action type: {action_type}",
            )

        action_name = action.get("action")
        
        # 处理特殊动作: Take_over (人工接管，需要callback)
        # Note: Take_over 是唯一保留的特殊动作，因为需要 takeover_callback
        # 其他动作(Note/Call_API/Interact)已被标准动作替代(RecordImportantContent/Answer/AskUser)
        if action_name == "Take_over":
            message = action.get("message", "需要用户介入")
            self.takeover_callback(message)
            return ActionResult(True, False, message=message)
        
        # 标准动作: 转换并委托给 ActionExecutor
        try:
            standard_action = self._convert_to_standard_action(action, screen_width, screen_height)
            result = self._executor.execute(standard_action)
            
            # 转换回 ActionResult
            return ActionResult(
                success=result["success"],
                should_finish=False,
                message=result.get("message")
            )
        except Exception as e:
            return ActionResult(
                success=False, should_finish=False, message=f"Action failed: {e}"
            )

    def _convert_to_standard_action(self, action: dict, width: int, height: int):
        """
        将 Vision Kernel 格式转换为标准 Action 对象
        
        注意：保持归一化坐标(0-1000)，由 ActionExecutor 统一转换为像素
        
        支持14种基础动作 + 7种高级动作
        """
        from phone_agent.actions.standard_actions import (
            TapAction, InputTextAction, SwipeAction, LaunchAppAction,
            DoubleTapAction, LongPressAction, WaitAction, PressKeyAction,
            DragAction, ScrollAction, KeyEventAction, AnswerAction,
            AskUserAction, RecordImportantContentAction, GenerateOrUpdateTodosAction
        )
        
        action_name = action.get("action")
        
        # ============================================
        # 基础动作（14种）
        # ============================================
        
        if action_name == "Tap":
            element = action.get("element", [500, 500])  # 归一化坐标 (0-1000)
            return TapAction(coordinates=element, reason=action.get("message", ""))
        
        elif action_name in ["Type", "Type_Name"]:
            text = action.get("text", "")
            return InputTextAction(text=text, reason="")
        
        elif action_name == "Swipe":
            start = action.get("start", [500, 1000])  # 归一化坐标
            end = action.get("end", [500, 500])      # 归一化坐标
            return SwipeAction(
                start=start,
                end=end,
                reason=""
            )
        
        elif action_name == "Launch":
            app_name = action.get("app", "")
            return LaunchAppAction(app_name=app_name, reason="")
        
        elif action_name == "Double Tap":
            element = action.get("element", [500, 500])  # 归一化坐标
            return DoubleTapAction(coordinates=element, reason="")
        
        elif action_name == "Long Press":
            element = action.get("element", [500, 500])  # 归一化坐标
            duration = action.get("duration", 3000)
            return LongPressAction(coordinates=element, duration=duration, reason="")
        
        elif action_name == "Wait":
            duration_str = action.get("duration", "1 second")
            # 解析duration: "x seconds" -> float
            try:
                if isinstance(duration_str, (int, float)):
                    duration = float(duration_str)
                else:
                    duration = float(duration_str.split()[0])
            except:
                duration = 1.0
            return WaitAction(seconds=duration, reason="")
        
        elif action_name == "Back":
            return PressKeyAction(key="back", reason="")
        
        elif action_name == "Home":
            return PressKeyAction(key="home", reason="")
        
        # ============================================
        # 高级动作（7种）
        # ============================================
        
        elif action_name == "Drag":
            start = action.get("start", [500, 1000])  # 归一化坐标
            end = action.get("end", [500, 500])      # 归一化坐标
            duration = action.get("duration", 500)
            return DragAction(
                start=start,
                end=end,
                duration=duration,
                reason=""
            )
        
        elif action_name == "Scroll":
            # Vision提示词: x, y, direction, distance
            # 标准动作库: coordinates, value
            x = action.get("x", 540)  # 归一化坐标
            y = action.get("y", 800)  # 归一化坐标
            direction = action.get("direction", "up")
            distance = action.get("distance", 500)
            
            # 转换direction+distance -> value
            if direction in ["up", "right"]:
                value = distance
            else:
                value = -distance
            
            return ScrollAction(
                coordinates=[x, y],  # 保持归一化
                value=value,
                reason=""
            )
        
        elif action_name == "Key_Event":
            key = action.get("key", "KEYCODE_ENTER")
            # 移除KEYCODE_前缀（如果有）
            if key.startswith("KEYCODE_"):
                key = key[8:].lower()
            return KeyEventAction(key=key, reason="")
        
        elif action_name == "Record_Important_Content":
            content = action.get("content", "")
            category = action.get("category", "")
            return RecordImportantContentAction(
                content=content,
                category=category,
                reason=""
            )
        
        elif action_name == "Generate_Or_Update_TODOs":
            todos = action.get("todos", "")
            return GenerateOrUpdateTodosAction(
                todos=todos,
                reason=""
            )
        
        elif action_name == "Ask_User":
            question = action.get("question", "")
            options = action.get("options", None)
            return AskUserAction(
                question=question,
                options=options,
                reason=""
            )
        
        elif action_name == "Answer":
            answer = action.get("answer", "")
            success = action.get("success", True)
            return AnswerAction(
                answer=answer,
                success=success,
                reason=""
            )
        
        else:
            raise ValueError(f"Unknown action: {action_name}")
    
    # [REMOVED] _convert_relative_to_absolute 已移除
    # 坐标转换统一由 ActionExecutor 处理

    @staticmethod
    def _default_confirmation(message: str) -> bool:
        """默认确认回调(使用控制台输入)"""
        response = input(f"敏感操作: {message}\n确认? (Y/N): ")
        return response.upper() == "Y"

    @staticmethod
    def _default_takeover(message: str) -> None:
        """默认接管回调(使用控制台输入)"""
        input(f"{message}\n完成手动操作后按Enter...")


def parse_action(response: str) -> dict[str, Any]:
    """
    从模型响应中解析动作(使用AST - eval的安全替代方案)

    Args:
        response: 来自模型的原始响应字符串

    Returns:
        解析后的动作字典

    Raises:
        ValueError: 当响应无法解析时

    Note:
        使用AST解析而非eval()以防止代码注入攻击
    """
    import ast
    import re
    
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
            # 使用literal_eval安全地求值
            try:
                arg_value = ast.literal_eval(keyword.value)
            except (ValueError, SyntaxError):
                # 如果literal_eval失败,尝试作为字符串获取值
                if isinstance(keyword.value, ast.Constant):
                    arg_value = keyword.value.value
                elif isinstance(keyword.value, ast.List):
                    # 处理列表字面量,如[x, y]
                    arg_value = [ast.literal_eval(el) for el in keyword.value.elts]
                else:
                    raise ValueError(f"无法解析参数: {arg_name}")
            
            args[arg_name] = arg_value
        
        args["_metadata"] = func_name
        return args
        
    except Exception as e:
        # 降级到正则表达式解析(简单情况)
        try:
            return _parse_action_with_regex(response)
        except Exception as fallback_error:
            raise ValueError(f"解析动作失败. AST错误: {e}, 正则表达式错误: {fallback_error}")


def _parse_action_with_regex(response: str) -> dict[str, Any]:
    """
    基于正则表达式的降级解析器(用于简单动作字符串)
    
    Args:
        response: 来自模型的原始响应字符串
    
    Returns:
        解析后的动作字典
    """
    import re
    
    # 匹配do(...)或finish(...)
    func_match = re.match(r'^(do|finish)\((.*)\)$', response, re.DOTALL)
    if not func_match:
        raise ValueError(f"无效的动作格式: {response}")
    
    func_name = func_match.group(1)
    args_str = func_match.group(2)
    
    # 解析key=value对
    args = {}
    
    # 处理特殊模式
    if func_name == "finish":
        # finish(message="xxx")
        message_match = re.search(r'message\s*=\s*["\'](.+?)["\']', args_str)
        if message_match:
            args["message"] = message_match.group(1)
    else:
        # Parse action, element, etc.
        # action="Launch"
        action_match = re.search(r'action\s*=\s*["\'](\w+)["\']', args_str)
        if action_match:
            args["action"] = action_match.group(1)
        
        # app="xxx"
        app_match = re.search(r'app\s*=\s*["\'](.+?)["\']', args_str)
        if app_match:
            args["app"] = app_match.group(1)
        
        # text="xxx"
        text_match = re.search(r'text\s*=\s*["\'](.+?)["\']', args_str)
        if text_match:
            args["text"] = text_match.group(1)
        
        # element=[x,y]
        element_match = re.search(r'element\s*=\s*\[(\d+)\s*,\s*(\d+)\]', args_str)
        if element_match:
            args["element"] = [int(element_match.group(1)), int(element_match.group(2))]
        
        # start=[x,y]
        start_match = re.search(r'start\s*=\s*\[(\d+)\s*,\s*(\d+)\]', args_str)
        if start_match:
            args["start"] = [int(start_match.group(1)), int(start_match.group(2))]
        
        # end=[x,y]
        end_match = re.search(r'end\s*=\s*\[(\d+)\s*,\s*(\d+)\]', args_str)
        if end_match:
            args["end"] = [int(end_match.group(1)), int(end_match.group(2))]
        
        # message="xxx"
        message_match = re.search(r'message\s*=\s*["\'](.+?)["\']', args_str)
        if message_match:
            args["message"] = message_match.group(1)
        
        # duration="x seconds"
        duration_match = re.search(r'duration\s*=\s*["\'](.+?)["\']', args_str)
        if duration_match:
            args["duration"] = duration_match.group(1)
    
    args["_metadata"] = func_name
    return args


def do(**kwargs) -> dict[str, Any]:
    """创建'do'动作的辅助函数"""
    kwargs["_metadata"] = "do"
    return kwargs


def finish(**kwargs) -> dict[str, Any]:
    """创建'finish'动作的辅助函数（已废弃，仅作容错）"""
    kwargs["_metadata"] = "finish"
    return kwargs
