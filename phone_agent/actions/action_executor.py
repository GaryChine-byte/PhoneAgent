#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
标准动作执行器

职责：
1. 连接标准动作模型与ADB封装
2. 处理index和coordinates两种模式
3. 统一错误处理和日志记录
4. 为XML和Vision两个内核提供统一的执行层

设计理念：
- 简单映射：动作 → ADB函数（1:1）
- 类型安全：利用Pydantic验证
- 易扩展：新增动作只需添加一个方法
- 内核无关：XML和Vision都可以使用

[NEW] Phase 1: 支持高级特性回调
- record_important_content: 通过callback记录
- generate_or_update_todos: 通过callback更新
"""

import logging
from typing import Dict, Any, Optional, List

from phone_agent.actions.standard_actions import (
    Action,
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
    ReadClipboardAction,
    WriteClipboardAction,
)
from phone_agent.adb import (
    tap,
    swipe,
    back,
    home,
    launch_app,
    long_press,
    double_tap,
)

# [NEW] 导入Protocol类型
try:
    from phone_agent.kernel.protocols import ExecutionCallback
except ImportError:
    # 向后兼容：如果protocols模块不存在，使用Any
    ExecutionCallback = Any


logger = logging.getLogger(__name__)


class ActionExecutor:
    """
    标准动作执行器
    
    将标准格式的动作对象转换为ADB命令执行
    支持XML Kernel和Vision Kernel
    """
    
    def __init__(
        self,
        device_id: str,
        screen_width: int,
        screen_height: int,
        elements: Optional[List[Any]] = None,
        task: Optional[Any] = None,
        callback: Optional[ExecutionCallback] = None
    ):
        """
        初始化执行器
        
        Args:
            device_id: 设备ID
            screen_width: 屏幕宽度（像素）
            screen_height: 屏幕高度（像素）
            elements: UI元素列表（用于index模式）
            task: Task对象（用于记录important_content和todos）
            callback: 执行回调（ExecutionCallback协议，优先于task）
        """
        self.device_id = device_id
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.elements = elements or []
        self.task = task  # [NEW] Phase 1高级特性
        self.callback: Optional[ExecutionCallback] = callback  # [NEW] Phase 1回调机制（类型安全）
    
    def execute(self, action: Action) -> Dict[str, Any]:
        """
        执行动作
        
        Args:
            action: 动作对象（来自parse_action）
            
        Returns:
            执行结果字典 {"success": bool, "message": str, ...}
        """
        try:
            if isinstance(action, TapAction):
                return self._execute_tap(action)
            elif isinstance(action, InputTextAction):
                return self._execute_input_text(action)
            elif isinstance(action, SwipeAction):
                return self._execute_swipe(action)
            elif isinstance(action, LaunchAppAction):
                return self._execute_launch_app(action)
            elif isinstance(action, LongPressAction):
                return self._execute_long_press(action)
            elif isinstance(action, DoubleTapAction):
                return self._execute_double_tap(action)
            elif isinstance(action, PressKeyAction):
                return self._execute_press_key(action)
            elif isinstance(action, DragAction):
                return self._execute_drag(action)
            elif isinstance(action, ScrollAction):
                return self._execute_scroll(action)
            elif isinstance(action, KeyEventAction):
                return self._execute_key_event(action)
            elif isinstance(action, AnswerAction):
                return self._execute_answer(action)
            elif isinstance(action, AskUserAction):
                return self._execute_ask_user(action)
            elif isinstance(action, RecordImportantContentAction):
                return self._execute_record_content(action)
            elif isinstance(action, GenerateOrUpdateTodosAction):
                return self._execute_update_todos(action)
            elif isinstance(action, WaitAction):
                return self._execute_wait(action)
            elif isinstance(action, ReadClipboardAction):
                return self._execute_read_clipboard(action)
            elif isinstance(action, WriteClipboardAction):
                return self._execute_write_clipboard(action)
            elif isinstance(action, DoneAction):
                return {
                    "done": True,
                    "success": action.success,
                    "message": action.message,
                    "data": action.data
                }
            else:
                return {
                    "success": False,
                    "message": f"Unknown action type: {type(action).__name__}"
                }
        except Exception as e:
            logger.error(f"Action execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Execution error: {str(e)}"
            }
    
    def _execute_tap(self, action: TapAction) -> Dict[str, Any]:
        """
        执行点击动作
        
        支持两种模式：
        1. coordinates: 归一化坐标（0-1000），统一转换为像素
        2. index: 元素索引（从elements列表）
        """
        x, y = None, None
        
        if action.coordinates:
            # Coordinates模式：归一化坐标 (0-1000) → 像素坐标
            x = int(action.coordinates[0] / 1000 * self.screen_width)
            y = int(action.coordinates[1] / 1000 * self.screen_height)
            mode = "coordinates(normalized)"
            logger.debug(f"归一化坐标 {action.coordinates} → 实际像素 ({x}, {y})")
        
        elif action.index is not None:
            # Index模式：从元素列表获取坐标
            if action.index < len(self.elements):
                element = self.elements[action.index]
                # 假设element有bounds属性: [left, top, right, bottom]
                if hasattr(element, 'bounds'):
                    bounds = element.bounds
                    x = (bounds[0] + bounds[2]) // 2
                    y = (bounds[1] + bounds[3]) // 2
                elif hasattr(element, 'center'):
                    x, y = element.center
                else:
                    return {
                        "success": False,
                        "message": f"Element {action.index} has no bounds/center"
                    }
                mode = f"index[{action.index}]"
            else:
                return {
                    "success": False,
                    "message": f"Index {action.index} out of range (max: {len(self.elements)-1})"
                }
        else:
            return {
                "success": False,
                "message": "Tap action must have either coordinates or index"
            }
        
        # [OK] 执行ADB tap（捕获异常）
        try:
            tap(x, y, self.device_id)
            
            logger.info(f"[OK] Tap executed: ({x}, {y}) via {mode}" + 
                       (f" - {action.reason}" if action.reason else ""))
            
            return {
                "success": True,
                "action": "tap",
                "x": x,
                "y": y,
                "mode": mode,
                "reason": action.reason
            }
        except RuntimeError as e:
            # tap命令执行失败
            logger.error(f"[X] Tap failed at ({x}, {y}): {e}")
            return {
                "success": False,
                "action": "tap",
                "x": x,
                "y": y,
                "mode": mode,
                "error": str(e),
                "message": f"Tap command failed: {e}"
            }
        except Exception as e:
            # 其他未预期的错误
            logger.error(f"[X] Tap error at ({x}, {y}): {e}", exc_info=True)
            return {
                "success": False,
                "action": "tap",
                "x": x,
                "y": y,
                "mode": mode,
                "error": str(e),
                "message": f"Unexpected error: {e}"
            }
    
    def _execute_input_text(self, action: InputTextAction) -> Dict[str, Any]:
        """
        执行输入文本动作
        
        优先使用yadb（支持中文），失败时回退ADB Keyboard
        """
        from phone_agent.adb.smart_input import smart_type_text
        
        # TODO: 如果action.index存在，先点击该输入框
        if action.index is not None:
            tap_action = TapAction(index=action.index)
            tap_result = self._execute_tap(tap_action)
            if not tap_result["success"]:
                return {
                    "success": False,
                    "message": f"Failed to focus input field: {tap_result['message']}"
                }
            # 等待输入框聚焦
            import time
            time.sleep(0.5)
        
        # [OK] 执行输入（智能选择yadb或ADB Keyboard）
        try:
            success = smart_type_text(action.text, self.device_id)
            
            if success:
                logger.info(f"[OK] Input executed: '{action.text}'" + 
                           (f" - {action.reason}" if action.reason else ""))
                return {
                    "success": True,
                    "action": "input_text",
                    "text": action.text,
                    "index": action.index,
                    "reason": action.reason
                }
            else:
                logger.warning(f"[X] Input failed: '{action.text}'")
                return {
                    "success": False,
                    "action": "input_text",
                    "text": action.text,
                    "index": action.index,
                    "error": "Input method failed",
                    "message": "Failed to input text"
                }
        except Exception as e:
            logger.error(f"[X] Input error: '{action.text}': {e}", exc_info=True)
            return {
                "success": False,
                "action": "input_text",
                "text": action.text,
                "index": action.index,
                "error": str(e),
                "message": f"Input error: {e}"
            }
    
    def _execute_swipe(self, action: SwipeAction) -> Dict[str, Any]:
        """
        执行滑动动作
        
        支持两种模式：
        1. direction: up/down/left/right
        2. start + end: 归一化坐标（0-1000）→ 像素
        """
        if action.direction:
            # 方向模式：转换为屏幕坐标
            start_x, start_y, end_x, end_y = self._direction_to_coordinates(action.direction)
            mode = f"direction[{action.direction}]"
        
        else:
            # 坐标模式：归一化 (0-1000) → 实际像素
            start_x = int(action.start[0] / 1000 * self.screen_width)
            start_y = int(action.start[1] / 1000 * self.screen_height)
            end_x = int(action.end[0] / 1000 * self.screen_width)
            end_y = int(action.end[1] / 1000 * self.screen_height)
            mode = "coordinates(normalized)"
        
        # [OK] 执行ADB swipe（捕获异常）
        try:
            swipe(
                start_x, start_y, end_x, end_y,
                duration_ms=action.duration,
                device_id=self.device_id
            )
            
            logger.info(f"[OK] Swipe executed: ({start_x},{start_y}) → ({end_x},{end_y}) via {mode}" + 
                       (f" - {action.reason}" if action.reason else ""))
            
            return {
                "success": True,
                "action": "swipe",
                "start": [start_x, start_y],
                "end": [end_x, end_y],
                "mode": mode,
                "reason": action.reason
            }
        except RuntimeError as e:
            logger.error(f"[X] Swipe failed: {e}")
            return {
                "success": False,
                "action": "swipe",
                "start": [start_x, start_y],
                "end": [end_x, end_y],
                "mode": mode,
                "error": str(e),
                "message": f"Swipe command failed: {e}"
            }
        except Exception as e:
            logger.error(f"[X] Swipe error: {e}", exc_info=True)
            return {
                "success": False,
                "action": "swipe",
                "start": [start_x, start_y],
                "end": [end_x, end_y],
                "mode": mode,
                "error": str(e),
                "message": f"Unexpected error: {e}"
            }
    
    def _execute_launch_app(self, action: LaunchAppAction) -> Dict[str, Any]:
        """
        执行启动应用动作
        
        使用Android Activity Manager启动应用
        """
        # [OK] 执行ADB launch_app
        success = launch_app(action.app_name, self.device_id)
        
        if success:
            logger.info(f"[OK] App launched: {action.app_name}" + 
                       (f" - {action.reason}" if action.reason else ""))
        else:
            logger.warning(f"[X] App launch failed: {action.app_name}")
        
        return {
            "success": success,
            "action": "launch_app",
            "app_name": action.app_name,
            "reason": action.reason
        }
    
    def _execute_long_press(self, action: LongPressAction) -> Dict[str, Any]:
        """
        执行长按动作
        
        支持两种模式：
        1. coordinates: 归一化坐标（0-1000）→ 像素
        2. index: 元素索引（从elements列表）
        """
        x, y = None, None
        
        if action.coordinates:
            # Coordinates模式：归一化 (0-1000) → 实际像素
            x = int(action.coordinates[0] / 1000 * self.screen_width)
            y = int(action.coordinates[1] / 1000 * self.screen_height)
            mode = "coordinates(normalized)"
        
        elif action.index is not None:
            # Index模式：从元素列表获取坐标
            if action.index < len(self.elements):
                element = self.elements[action.index]
                if hasattr(element, 'bounds'):
                    bounds = element.bounds
                    x = (bounds[0] + bounds[2]) // 2
                    y = (bounds[1] + bounds[3]) // 2
                elif hasattr(element, 'center'):
                    x, y = element.center
                else:
                    return {
                        "success": False,
                        "message": f"Element {action.index} has no bounds/center"
                    }
                mode = f"index[{action.index}]"
            else:
                return {
                    "success": False,
                    "message": f"Index {action.index} out of range (max: {len(self.elements)-1})"
                }
        else:
            return {
                "success": False,
                "message": "Long press action must have either coordinates or index"
            }
        
        # [OK] 执行ADB long_press
        long_press(x, y, duration=action.duration, device_id=self.device_id)
        
        logger.info(f"[OK] Long press executed: ({x}, {y}) via {mode}, duration={action.duration}ms" + 
                   (f" - {action.reason}" if action.reason else ""))
        
        return {
            "success": True,
            "action": "long_press",
            "coordinates": [x, y],
            "duration": action.duration,
            "reason": action.reason
        }
    
    def _execute_double_tap(self, action: DoubleTapAction) -> Dict[str, Any]:
        """
        执行双击动作
        
        支持两种模式：
        1. coordinates: 归一化坐标（0-1000）→ 像素
        2. index: 元素索引（从elements列表）
        """
        x, y = None, None
        
        if action.coordinates:
            # Coordinates模式：归一化 (0-1000) → 实际像素
            x = int(action.coordinates[0] / 1000 * self.screen_width)
            y = int(action.coordinates[1] / 1000 * self.screen_height)
            mode = "coordinates(normalized)"
        
        elif action.index is not None:
            # Index模式：从元素列表获取坐标
            if action.index < len(self.elements):
                element = self.elements[action.index]
                if hasattr(element, 'bounds'):
                    bounds = element.bounds
                    x = (bounds[0] + bounds[2]) // 2
                    y = (bounds[1] + bounds[3]) // 2
                elif hasattr(element, 'center'):
                    x, y = element.center
                else:
                    return {
                        "success": False,
                        "message": f"Element {action.index} has no bounds/center"
                    }
                mode = f"index[{action.index}]"
            else:
                return {
                    "success": False,
                    "message": f"Index {action.index} out of range (max: {len(self.elements)-1})"
                }
        else:
            return {
                "success": False,
                "message": "Double tap action must have either coordinates or index"
            }
        
        # [OK] 执行ADB double_tap
        double_tap(x, y, device_id=self.device_id)
        
        logger.info(f"[OK] Double tap executed: ({x}, {y}) via {mode}" + 
                   (f" - {action.reason}" if action.reason else ""))
        
        return {
            "success": True,
            "action": "double_tap",
            "coordinates": [x, y],
            "reason": action.reason
        }
    
    def _execute_press_key(self, action: PressKeyAction) -> Dict[str, Any]:
        """
        执行按键动作
        
        支持: back, home, recent
        """
        if action.key == "back":
            back(self.device_id)
        
        elif action.key == "home":
            home(self.device_id)
        
        elif action.key == "recent":
            # Recent apps按键
            from phone_agent.adb.device import run_adb_command
            run_adb_command(
                ["shell", "input", "keyevent", "KEYCODE_APP_SWITCH"],
                self.device_id
            )
        
        else:
            return {
                "success": False,
                "message": f"Unknown key: {action.key}"
            }
        
        logger.info(f"[OK] Key pressed: {action.key}" + 
                   (f" - {action.reason}" if action.reason else ""))
        
        return {
            "success": True,
            "action": "press_key",
            "key": action.key,
            "reason": action.reason
        }
    
    def _execute_wait(self, action: WaitAction) -> Dict[str, Any]:
        """执行等待动作"""
        import time
        time.sleep(action.seconds)
        
        logger.info(f"[OK] Waited: {action.seconds}s" + 
                   (f" - {action.reason}" if action.reason else ""))
        
        return {
            "success": True,
            "action": "wait",
            "seconds": action.seconds,
            "reason": action.reason
        }
    
    def _execute_drag(self, action: DragAction) -> Dict[str, Any]:
        """执行拖拽动作"""
        start_x, start_y, end_x, end_y = None, None, None, None
        
        # 解析起始和结束坐标
        if action.start and action.end:
            # Coordinates模式：归一化 (0-1000) → 像素
            start_x = int(action.start[0] / 1000 * self.screen_width)
            start_y = int(action.start[1] / 1000 * self.screen_height)
            end_x = int(action.end[0] / 1000 * self.screen_width)
            end_y = int(action.end[1] / 1000 * self.screen_height)
            mode = "coordinates(normalized)"
        elif action.start_index is not None and action.end_index is not None:
            # Index模式
            if action.start_index < len(self.elements) and action.end_index < len(self.elements):
                start_elem = self.elements[action.start_index]
                end_elem = self.elements[action.end_index]
                start_x, start_y = self._get_element_center(start_elem)
                end_x, end_y = self._get_element_center(end_elem)
                mode = f"index[{action.start_index}→{action.end_index}]"
            else:
                return {"success": False, "message": "Index out of range"}
        else:
            return {"success": False, "message": "Drag requires start/end coordinates or indices"}
        
        # 执行拖拽（使用swipe实现）
        swipe(start_x, start_y, end_x, end_y, duration=action.duration, device_id=self.device_id)
        logger.info(f"[OK] Drag: ({start_x},{start_y})→({end_x},{end_y}) via {mode}")
        
        return {"success": True, "action": "drag", "start": [start_x, start_y], "end": [end_x, end_y]}
    
    def _execute_scroll(self, action: ScrollAction) -> Dict[str, Any]:
        """执行滚动动作（归一化坐标 → 像素）"""
        x = int(action.coordinates[0] / 1000 * self.screen_width)
        y = int(action.coordinates[1] / 1000 * self.screen_height)
        
        # 滚动转换为swipe：正数向上，负数向下
        offset = int(abs(action.value) * 100)  # 滚动量转像素
        if action.value > 0:  # 向上滚动
            end_y = max(0, y - offset)
            swipe(x, y, x, end_y, duration=300, device_id=self.device_id)
        else:  # 向下滚动
            end_y = min(self.screen_height, y + offset)
            swipe(x, y, x, end_y, duration=300, device_id=self.device_id)
        
        logger.info(f"[OK] Scroll: ({x},{y}) value={action.value}")
        return {"success": True, "action": "scroll", "coordinates": [x, y], "value": action.value}
    
    def _execute_key_event(self, action: KeyEventAction) -> Dict[str, Any]:
        """执行按键事件"""
        from phone_agent.adb import execute_adb_command
        
        # 映射常见按键名到keycode
        key_map = {
            "volume_up": "KEYCODE_VOLUME_UP",
            "volume_down": "KEYCODE_VOLUME_DOWN",
            "power": "KEYCODE_POWER",
            "camera": "KEYCODE_CAMERA",
            "clear": "KEYCODE_CLEAR",
            "menu": "KEYCODE_MENU",
            "search": "KEYCODE_SEARCH",
        }
        
        keycode = key_map.get(action.key, action.key)
        cmd = f"input keyevent {keycode}"
        execute_adb_command(cmd, self.device_id)
        
        logger.info(f"[OK] Key event: {action.key}")
        return {"success": True, "action": "key_event", "key": action.key}
    
    def _execute_answer(self, action: AnswerAction) -> Dict[str, Any]:
        """执行返回答案动作（不执行ADB操作）"""
        logger.info(f"[OK] Answer: {action.answer}")
        return {
            "done": True,
            "success": True,
            "action": "answer",
            "answer": action.answer,
            "data": action.data
        }
    
    def _execute_ask_user(self, action: AskUserAction) -> Dict[str, Any]:
        """执行询问用户动作（暂停任务）"""
        logger.info(f"❓ Ask user: {action.question}")
        return {
            "ask_user": True,
            "question": action.question,
            "options": action.options,
            "reason": action.reason
        }
    
    def _execute_record_content(self, action: RecordImportantContentAction) -> Dict[str, Any]:
        """执行记录重要内容动作"""
        logger.info(f" Record: [{action.category}] {action.content[:50]}...")
        
        # [NEW] 优先使用回调（适用于XML Kernel）
        if self.callback and hasattr(self.callback, 'on_record_content'):
            self.callback.on_record_content(
                content=action.content,
                category=action.category,
                reason=action.reason
            )
        # 回退到直接访问task（适用于其他场景）
        elif self.task:
            from datetime import datetime, timezone
            record = {
                "content": action.content,
                "category": action.category or "general",
                "reason": action.reason,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self.task.important_content.append(record)
            logger.debug(f"[OK] Recorded to task.important_content: {record}")
        else:
            logger.warning("[WARN] No callback or task available for record_content")
        
        return {
            "success": True,
            "action": "record_important_content",
            "content": action.content,
            "category": action.category
        }
    
    def _execute_update_todos(self, action: GenerateOrUpdateTodosAction) -> Dict[str, Any]:
        """执行更新TODO动作"""
        logger.info(f" Update TODOs: {len(action.todos.split(chr(10)))} items")
        
        # [NEW] 优先使用回调
        if self.callback and hasattr(self.callback, 'on_update_todos'):
            self.callback.on_update_todos(
                todos=action.todos,
                reason=action.reason
            )
        # 回退到直接访问task
        elif self.task:
            self.task.todos = action.todos
            logger.debug(f"[OK] Updated task.todos")
        else:
            logger.warning("[WARN] No callback or task available for update_todos")
        
        return {
            "success": True,
            "action": "generate_or_update_todos",
            "todos": action.todos
        }
    
    def _get_element_center(self, element) -> tuple[int, int]:
        """获取元素中心坐标"""
        if hasattr(element, 'bounds'):
            bounds = element.bounds
            return (bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2
        elif hasattr(element, 'center'):
            return element.center
        else:
            raise ValueError("Element has no bounds/center")
    
    def _direction_to_coordinates(self, direction: str) -> tuple[int, int, int, int]:
        """
        将方向转换为屏幕坐标
        
        Args:
            direction: up/down/left/right
            
        Returns:
            (start_x, start_y, end_x, end_y)
        """
        # 使用屏幕中心80%的区域进行滑动
        center_x = self.screen_width // 2
        center_y = self.screen_height // 2
        margin = 0.1  # 10%边距
        
        if direction == "up":
            # 向上滑动：从底部往上
            return (
                center_x,
                int(self.screen_height * (1 - margin)),
                center_x,
                int(self.screen_height * margin)
            )
        
        elif direction == "down":
            # 向下滑动：从顶部往下
            return (
                center_x,
                int(self.screen_height * margin),
                center_x,
                int(self.screen_height * (1 - margin))
            )
        
        elif direction == "left":
            # 向左滑动：从右往左
            return (
                int(self.screen_width * (1 - margin)),
                center_y,
                int(self.screen_width * margin),
                center_y
            )
        
        elif direction == "right":
            # 向右滑动：从左往右
            return (
                int(self.screen_width * margin),
                center_y,
                int(self.screen_width * (1 - margin)),
                center_y
            )
        
        else:
            raise ValueError(f"Unknown direction: {direction}")
    
    def _execute_read_clipboard(self, action: ReadClipboardAction) -> Dict[str, Any]:
        """
        执行读取剪贴板动作
        
        Returns:
            {
                "success": True/False,
                "action": "read_clipboard",
                "content": "剪贴板内容",
                "message": "读取成功/失败信息"
            }
        """
        try:
            from phone_agent.adb.yadb import read_clipboard
            
            logger.info(f"[TARGET] 读取剪贴板: {action.reason}")
            
            # 读取剪贴板
            content = read_clipboard(device_id=self.device_id)
            
            if content is not None:
                # 截断过长的内容用于日志
                preview = content[:100] + "..." if len(content) > 100 else content
                logger.info(f"[OK] 读取剪贴板成功: {preview}")
                
                return {
                    "success": True,
                    "action": "read_clipboard",
                    "content": content,
                    "message": f"剪贴板内容: {preview}"
                }
            else:
                logger.error("[X] 读取剪贴板失败: 剪贴板为空或读取失败")
                return {
                    "success": False,
                    "action": "read_clipboard",
                    "content": "",
                    "error": "剪贴板为空或读取失败"
                }
                
        except Exception as e:
            logger.error(f"[X] 读取剪贴板异常: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "action": "read_clipboard",
                "error": str(e)
            }
    
    def _execute_write_clipboard(self, action: WriteClipboardAction) -> Dict[str, Any]:
        """
        执行写入剪贴板动作
        
        Returns:
            {
                "success": True/False,
                "action": "write_clipboard",
                "message": "写入成功/失败信息"
            }
        """
        try:
            from phone_agent.adb.yadb import write_clipboard
            
            # 截断过长的内容用于日志
            preview = action.text[:100] + "..." if len(action.text) > 100 else action.text
            logger.info(f"[TARGET] 写入剪贴板: {preview} ({action.reason})")
            
            # 写入剪贴板
            success = write_clipboard(action.text, device_id=self.device_id)
            
            if success:
                logger.info(f"[OK] 写入剪贴板成功")
                return {
                    "success": True,
                    "action": "write_clipboard",
                    "message": f"已写入剪贴板: {preview}"
                }
            else:
                logger.error("[X] 写入剪贴板失败")
                return {
                    "success": False,
                    "action": "write_clipboard",
                    "error": "写入剪贴板失败"
                }
                
        except Exception as e:
            logger.error(f"[X] 写入剪贴板异常: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "action": "write_clipboard",
                "error": str(e)
            }


__all__ = ["ActionExecutor"]
