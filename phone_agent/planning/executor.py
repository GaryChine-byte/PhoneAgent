#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""任务计划执行器"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from phone_agent.adb import (
    get_current_app, get_screenshot, launch_app, tap, type_text, swipe, back, home,
    double_tap, long_press, clear_text
)
from .planner import TaskPlan

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of plan execution."""
    
    success: bool
    completed_steps: int
    total_steps: int
    failed_step: Optional[int]
    error_message: Optional[str]
    execution_time: float
    fallback_to_step_by_step: bool = False  # [NEW] 是否需要降级
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "completed_steps": self.completed_steps,
            "total_steps": self.total_steps,
            "failed_step": self.failed_step,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "fallback_to_step_by_step": self.fallback_to_step_by_step,
        }


@dataclass
class RetryConfig:
    """[NEW] 重试配置"""
    max_retries: int = 2
    retry_delay: float = 1.0
    enable_fallback: bool = True


@dataclass
class CheckpointConfig:
    """[NEW] 检查点配置 - 平衡性能与成本"""
    # 验证模式
    default_mode: str = "xml"  # xml: 快速验证, vision: 视觉验证, hybrid: 混合
    
    # 混合模式策略
    xml_first: bool = True  # 优先用 XML，失败后用 Vision
    vision_for_critical: bool = True  # 关键检查点强制使用 Vision
    
    # 成本控制
    max_vision_checkpoints: int = 3  # 每个任务最多使用 Vision 验证的次数
    vision_checkpoint_interval: int = 5  # 每隔 N 个检查点使用一次 Vision（抽样验证）


@dataclass
class HumanInterventionRequest:
    """[NEW] 人工介入请求"""
    type: str  # "confirm", "input"
    message: str
    options: Optional[list] = None
    input_type: Optional[str] = "text"
    placeholder: Optional[str] = None
    timeout: int = 60


class PlanExecutor:
    """
    计划执行器 - 委托给 ActionExecutor
    
    职责:
    1. 执行完整任务计划
    2. 步骤编排和重试
    3. Checkpoint验证（XML/Vision混合）
    4. 人机协同（HUMAN_CONFIRM/INPUT）
    5. XML智能定位（element_selector）
    
    [OK] 优化: 动作执行委托给 ActionExecutor
    """
    
    def __init__(
        self,
        device_id: str | None = None,
        step_callback: Callable[[int, dict, bool, str], None] | None = None,
        use_xml_positioning: bool = True,
        human_intervention_callback: Callable[[HumanInterventionRequest], tuple[bool, Any]] | None = None,
        retry_config: Optional[RetryConfig] = None,
        checkpoint_config: Optional[CheckpointConfig] = None,
        model_config: Any = None,  # [NEW] 用于 Vision 验证
    ):
        """
        Initialize plan executor.
        
        Args:
            device_id: Optional device ID for multi-device setups
            step_callback: Optional callback called after each step
                Signature: (step_num, step_data, success, message)
            use_xml_positioning: Whether to use XML-based smart positioning (default: True)
            human_intervention_callback: [NEW] Callback for human intervention requests
                Signature: (request) -> (success, response_data)
            retry_config: [NEW] Retry configuration
            checkpoint_config: [NEW] Checkpoint validation configuration
            model_config: [NEW] Model configuration for Vision validation
        """
        self.device_id = device_id
        self.step_callback = step_callback
        self.use_xml_positioning = use_xml_positioning
        self.human_intervention_callback = human_intervention_callback
        self.retry_config = retry_config or RetryConfig()
        self.checkpoint_config = checkpoint_config or CheckpointConfig()
        self.model_config = model_config
        
        # [OK] 创建核心执行器（延迟初始化，需要屏幕尺寸）
        self._action_executor = None
        self._screen_width = None
        self._screen_height = None
        
        # [NEW] 统计信息
        self._checkpoint_count = 0
        self._vision_checkpoint_count = 0
    
    def _get_action_executor(self):
        """
        获取 ActionExecutor 实例（延迟初始化）
        
        [OK] 新增: 统一的执行器获取方法
        """
        if self._action_executor is None:
            # 获取屏幕尺寸
            if self._screen_width is None or self._screen_height is None:
                from phone_agent.adb import get_screenshot
                screenshot = get_screenshot(device_id=self.device_id)
                self._screen_width = screenshot.width
                self._screen_height = screenshot.height
            
            # 创建执行器
            from phone_agent.actions import ActionExecutor
            self._action_executor = ActionExecutor(
                device_id=self.device_id,
                screen_width=self._screen_width,
                screen_height=self._screen_height
            )
        
        return self._action_executor
    
    def execute_plan(self, plan: TaskPlan) -> ExecutionResult:
        """
        Execute a complete task plan.
        
        Args:
            plan: TaskPlan to execute
            
        Returns:
            ExecutionResult with execution details
        """
        logger.info(f"Executing plan with {len(plan.steps)} steps")
        start_time = time.time()
        
        completed_steps = 0
        failed_step = None
        error_message = None
        
        try:
            for i, step in enumerate(plan.steps, 1):
                logger.info(f"Executing step {i}/{len(plan.steps)}: {step.get('target_description', 'Unknown')}")
                
                # 带重试的步骤执行
                success, message = self._execute_step_with_retry(i, step)
                
                if self.step_callback:
                    self.step_callback(i, step, success, message)
                
                if not success:
                    error_message = message
                    failed_step = i
                    logger.error(f"Step {i} failed: {message}")
                    
                    # 检查此步骤是否有关键检查点
                    is_critical = self._is_critical_step(plan, i)
                    if is_critical:
                        logger.error(f"关键步骤 {i} 失败,中止执行")
                        
                        # 建议降级到逐步执行
                        if self.retry_config.enable_fallback:
                            logger.info("建议降级到逐步执行模式...")
                            return ExecutionResult(
                                success=False,
                                completed_steps=i,
                                total_steps=len(plan.steps),
                                failed_step=i,
                                error_message=error_message,
                                execution_time=time.time() - start_time,
                                fallback_to_step_by_step=True
                            )
                        
                        break
                    else:
                        logger.warning(f"Non-critical step {i} failed, continuing...")
                
                completed_steps = i
                
                # 步骤间短暂延迟以等待UI稳定
                time.sleep(0.5)
        
        except Exception as e:
            logger.error(f"Execution error: {e}", exc_info=True)
            error_message = f"Execution error: {str(e)}"
        
        execution_time = time.time() - start_time
        
        success = (failed_step is None) or (completed_steps == len(plan.steps))
        
        result = ExecutionResult(
            success=success,
            completed_steps=completed_steps,
            total_steps=len(plan.steps),
            failed_step=failed_step,
            error_message=error_message,
            execution_time=execution_time,
        )
        
        logger.info(f"Execution completed: {result.completed_steps}/{result.total_steps} steps in {result.execution_time:.2f}s")
        
        return result
    
    def _execute_step_with_retry(self, step_num: int, step: dict[str, Any]) -> tuple[bool, str]:
        """
        [NEW] Execute a step with retry logic.
        
        Args:
            step_num: Step number
            step: Step dictionary
            
        Returns:
            Tuple of (success, message)
        """
        action_type = step.get("action_type")
        
        # [NEW] 人机协同动作不需要重试
        if action_type in ["HUMAN_CONFIRM", "HUMAN_INPUT"]:
            return self._execute_step(step)
        
        # 其他动作支持重试
        for attempt in range(self.retry_config.max_retries + 1):
            if attempt > 0:
                logger.info(f"重试 {attempt}/{self.retry_config.max_retries}...")
                time.sleep(self.retry_config.retry_delay)
            
            success, message = self._execute_step(step)
            
            if success:
                if attempt > 0:
                    logger.info(f"重试成功")
                return True, message
            
            # 失败了，记录日志
            logger.warning(f"尝试 {attempt + 1} 失败: {message}")
        
        # 所有重试都失败
        return False, f"步骤失败（已重试 {self.retry_config.max_retries} 次）: {message}"
    
    def _execute_step(self, step: dict[str, Any]) -> tuple[bool, str]:
        """
        Execute a single step.
        
        Args:
            step: Step dictionary from plan
            
        Returns:
            Tuple of (success, message)
        """
        action_type = step.get("action_type")
        parameters = step.get("parameters", {})
        
        try:
            if action_type == "LAUNCH":
                return self._execute_launch(parameters)
            elif action_type == "TAP":
                return self._execute_tap(parameters)
            elif action_type == "DOUBLE_TAP":
                return self._execute_double_tap(parameters)
            elif action_type == "LONG_PRESS":
                return self._execute_long_press(parameters)
            elif action_type == "TYPE":
                return self._execute_type(parameters)
            elif action_type == "CLEAR_TEXT":
                return self._execute_clear_text(parameters)
            elif action_type == "SWIPE":
                return self._execute_swipe(parameters)
            elif action_type == "SCROLL":
                return self._execute_scroll(parameters)
            elif action_type == "BACK":
                return self._execute_back(parameters)
            elif action_type == "HOME":
                return self._execute_home(parameters)
            elif action_type == "WAIT":
                return self._execute_wait(parameters)
            elif action_type == "CHECKPOINT":
                return self._execute_checkpoint(parameters)
            elif action_type == "HUMAN_CONFIRM":
                return self._execute_human_confirm(parameters)
            elif action_type == "HUMAN_INPUT":
                return self._execute_human_input(parameters)
            else:
                return False, f"Unknown action type: {action_type}"
        
        except Exception as e:
            logger.error(f"Step execution error: {e}", exc_info=True)
            return False, f"Error: {str(e)}"
    
    def _execute_launch(self, params: dict) -> tuple[bool, str]:
        """Execute LAUNCH action."""
        app_name = params.get("app_name")
        if not app_name:
            return False, "Missing app_name parameter"
        
        try:
            launch_app(app_name, self.device_id)
            # 等待应用启动
            time.sleep(2)
            return True, f"Launched {app_name}"
        except Exception as e:
            return False, f"Failed to launch {app_name}: {e}"
    
    def _execute_tap(self, params: dict) -> tuple[bool, str]:
        """
        Execute TAP action with optional smart positioning.
        
        [OK] 优化: 委托给 ActionExecutor 执行
        
        If element_selector is provided and use_xml_positioning is True,
        attempts to find element via XML tree before falling back to fixed coordinates.
        """
        # 1️⃣ XML智能定位（PlanExecutor独有功能）
        if self.use_xml_positioning and "element_selector" in params:
            x, y, found = self._find_element_by_selector(params["element_selector"])
            if found:
                params["x"] = x
                params["y"] = y
            logger.info(f"[OK] XML智能定位成功: ({x}, {y})")
        
        # 2️⃣ 检查坐标
        x = params.get("x")
        y = params.get("y")
        
        if x is None or y is None:
            return False, "Missing x or y coordinate and no valid selector"
        
        # 3️⃣ 转换为标准Action并委托给ActionExecutor
        try:
            from phone_agent.actions.standard_actions import TapAction
            action = TapAction(
                coordinates=[x, y],
                reason=params.get("reason", "")
            )
            
            executor = self._get_action_executor()
            result = executor.execute(action)
            
            if result["success"]:
                coords = result["coordinates"]
                return True, f"Tapped at ({coords[0]}, {coords[1]})"
            else:
                return False, result.get("message", "Tap failed")
        except Exception as e:
            logger.error(f"Tap execution error: {e}", exc_info=True)
            return False, f"Failed to tap: {e}"
    
    def _execute_double_tap(self, params: dict) -> tuple[bool, str]:
        """
        Execute DOUBLE_TAP action.
        
        [OK] 优化: 委托给 ActionExecutor 执行
        """
        x = params.get("x")
        y = params.get("y")
        
        if x is None or y is None:
            return False, "Missing x or y coordinate"
        
        try:
            from phone_agent.actions.standard_actions import DoubleTapAction
            action = DoubleTapAction(coordinates=[x, y], reason="")
            
            executor = self._get_action_executor()
            result = executor.execute(action)
            
            if result["success"]:
                coords = result["coordinates"]
                return True, f"Double tapped at ({coords[0]}, {coords[1]})"
            else:
                return False, result.get("message", "Double tap failed")
        except Exception as e:
            return False, f"Failed to double tap: {e}"
    
    def _execute_long_press(self, params: dict) -> tuple[bool, str]:
        """
        Execute LONG_PRESS action.
        
        [OK] 优化: 委托给 ActionExecutor 执行
        """
        x = params.get("x")
        y = params.get("y")
        duration_ms = params.get("duration_ms", 3000)
        
        if x is None or y is None:
            return False, "Missing x or y coordinate"
        
        try:
            from phone_agent.actions.standard_actions import LongPressAction
            action = LongPressAction(
                coordinates=[x, y],
                duration=duration_ms,
                reason=""
            )
            
            executor = self._get_action_executor()
            result = executor.execute(action)
            
            if result["success"]:
                coords = result["coordinates"]
                return True, f"Long pressed at ({coords[0]}, {coords[1]}) for {duration_ms}ms"
            else:
                return False, result.get("message", "Long press failed")
        except Exception as e:
            return False, f"Failed to long press: {e}"
    
    def _execute_type(self, params: dict) -> tuple[bool, str]:
        """
        Execute TYPE action with smart input (yadb priority).
        
        [OK] 优化: 委托给 ActionExecutor 执行
        """
        text = params.get("text")
        if not text:
            return False, "Missing text parameter"
        
        try:
            from phone_agent.actions.standard_actions import InputTextAction
            action = InputTextAction(text=text, reason="")
            
            executor = self._get_action_executor()
            result = executor.execute(action)
            
            if result["success"]:
                return True, f"Typed: {text}"
            else:
                return False, result.get("message", "Type failed")
        except Exception as e:
            logger.error(f"Type action error: {e}", exc_info=True)
            return False, f"Failed to type: {e}"
    
    def _execute_clear_text(self, params: dict) -> tuple[bool, str]:
        """Execute CLEAR_TEXT action."""
        try:
            clear_text(self.device_id)
            time.sleep(0.2)
            return True, "Cleared text"
        except Exception as e:
            return False, f"Failed to clear text: {e}"
    
    def _execute_swipe(self, params: dict) -> tuple[bool, str]:
        """
        Execute SWIPE action.
        
        [OK] 优化: 委托给 ActionExecutor 执行
        """
        start_x = params.get("start_x")
        start_y = params.get("start_y")
        end_x = params.get("end_x")
        end_y = params.get("end_y")
        
        if any(v is None for v in [start_x, start_y, end_x, end_y]):
            return False, "Missing swipe coordinates"
        
        try:
            from phone_agent.actions.standard_actions import SwipeAction
            action = SwipeAction(
                start_coordinates=[start_x, start_y],
                end_coordinates=[end_x, end_y],
                reason=""
            )
            
            executor = self._get_action_executor()
            result = executor.execute(action)
            
            if result["success"]:
                return True, f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})"
            else:
                return False, result.get("message", "Swipe failed")
        except Exception as e:
            return False, f"Failed to swipe: {e}"
    
    def _execute_scroll(self, params: dict) -> tuple[bool, str]:
        """
        Execute SCROLL action.
        
        Scroll in specified direction by distance.
        
        Parameters:
            direction: "up" | "down" | "left" | "right"
            distance: scroll distance in pixels (default: 500)
            x, y: scroll center point (optional, default: screen center)
        """
        direction = params.get("direction", "down")
        distance = params.get("distance", 500)
        
        # 默认屏幕中央（假设1440x3200）
        x = params.get("x", 720)
        y = params.get("y", 1600)
        
        try:
            # 根据方向计算终点
            if direction == "up":
                end_x, end_y = x, max(0, y - distance)
            elif direction == "down":
                end_x, end_y = x, min(3200, y + distance)  # 假设屏幕高度
            elif direction == "left":
                end_x, end_y = max(0, x - distance), y
            elif direction == "right":
                end_x, end_y = min(1440, x + distance), y  # 假设屏幕宽度
            else:
                return False, f"Invalid scroll direction: {direction}"
            
            swipe(x, y, end_x, end_y, duration=300, device_id=self.device_id)
            time.sleep(0.5)
            return True, f"Scrolled {direction} by {distance}px from ({x}, {y})"
        except Exception as e:
            logger.error(f"Scroll failed: {e}", exc_info=True)
            return False, f"Failed to scroll: {e}"
    
    def _execute_back(self, params: dict) -> tuple[bool, str]:
        """Execute BACK action."""
        try:
            back(self.device_id)
            time.sleep(0.3)
            return True, "Pressed back button"
        except Exception as e:
            return False, f"Failed to press back: {e}"
    
    def _execute_home(self, params: dict) -> tuple[bool, str]:
        """Execute HOME action."""
        try:
            home(self.device_id)
            time.sleep(0.5)
            return True, "Pressed home button"
        except Exception as e:
            return False, f"Failed to press home: {e}"
    
    def _execute_wait(self, params: dict) -> tuple[bool, str]:
        """Execute WAIT action."""
        seconds = params.get("seconds", 1)
        
        try:
            time.sleep(seconds)
            return True, f"Waited {seconds} seconds"
        except Exception as e:
            return False, f"Failed to wait: {e}"
    
    def _execute_checkpoint(self, params: dict) -> tuple[bool, str]:
        """
        Execute CHECKPOINT action - verify current state.
        
        [NEW] Enhanced with hybrid validation (XML + Vision).
        
        验证策略：
        1. 默认使用 XML 验证（快速、低成本）
        2. 关键检查点使用 Vision 验证（可靠）
        3. XML 失败时降级到 Vision 验证（自动兜底）
        4. 控制 Vision 使用次数（成本管理）
        """
        description = params.get("description", "Checkpoint")
        expected_state = params.get("expected_state", {})
        is_critical = params.get("critical", False)
        validation_mode = params.get("validation_mode", self.checkpoint_config.default_mode)
        
        self._checkpoint_count += 1
        logger.info(f"Checkpoint {self._checkpoint_count}: {description}")
        # 如果没有提供验证条件,只记录日志并成功(旧版行为)
        if not expected_state:
            logger.info(f"无验证条件,检查点通过")
            return True, f"检查点通过: {description}"
        
        # [NEW] 决定验证模式
        use_vision = self._should_use_vision_validation(
            is_critical=is_critical,
            validation_mode=validation_mode
        )
        
        if use_vision:
            return self._validate_with_vision(description, expected_state, is_critical)
        else:
            # 尝试 XML 验证
            xml_success, xml_message = self._validate_with_xml(description, expected_state)
            
            if xml_success:
                return True, xml_message
            
            # XML 失败，决定是否降级到 Vision
            if self.checkpoint_config.xml_first and self._can_use_vision():
                logger.warning(f"XML 验证失败: {xml_message}")
                logger.info(f"降级到 Vision 验证...")
                return self._validate_with_vision(description, expected_state, is_critical)
            
            return False, xml_message
    
    def _should_use_vision_validation(self, is_critical: bool, validation_mode: str) -> bool:
        """
        [NEW] 决定是否使用 Vision 验证
        
        策略：
        1. 明确指定 vision 模式 → 使用 Vision
        2. 关键检查点 + 配置允许 → 使用 Vision
        3. 达到抽样间隔 → 使用 Vision（定期验证）
        4. 超过 Vision 使用次数限制 → 不使用
        """
        # 明确指定
        if validation_mode == "vision":
            if self._can_use_vision():
                return True
            else:
                logger.warning(f"已达到 Vision 验证次数限制，使用 XML 验证")
                return False
        
        if validation_mode == "xml":
            return False
        
        # hybrid 模式决策
        if not self._can_use_vision():
            return False
        
        # 关键检查点
        if is_critical and self.checkpoint_config.vision_for_critical:
            logger.info(f"关键检查点，使用 Vision 验证")
            return True
        
        # 抽样验证（每隔 N 个检查点使用一次 Vision）
        if self._checkpoint_count % self.checkpoint_config.vision_checkpoint_interval == 0:
            logger.info(f"抽样验证（第 {self._checkpoint_count} 个检查点），使用 Vision")
            return True
        
        return False
    
    def _can_use_vision(self) -> bool:
        """[NEW] 检查是否还能使用 Vision 验证"""
        return self._vision_checkpoint_count < self.checkpoint_config.max_vision_checkpoints
    
    def _validate_with_xml(self, description: str, expected_state: dict) -> tuple[bool, str]:
        """
        [NEW] 使用 XML 树验证（快速、低成本）
        
        优势：
        - 速度快（~0.5秒）
        - 成本低（~$0.001）
        - 适合简单验证
        
        局限：
        - 依赖 UI 树可用性
        - 无法验证视觉内容
        """
        logger.info(f"使用 XML 验证（快速模式）")
        
        try:
            from phone_agent.adb import get_current_app
            from phone_agent.adb.ui_hierarchy import get_ui_hierarchy
            
            # 1. Validate current app if specified
            if "current_app" in expected_state:
                expected_app = expected_state["current_app"]
                current_app = get_current_app(self.device_id)
                
                if current_app != expected_app:
                    error_msg = f"应用不匹配: 预期 '{expected_app}', 实际 '{current_app}'"
                    logger.error(f"{error_msg}")
                    return False, error_msg
                
            logger.info(f"  [OK] 应用匹配: {current_app}")
            
            # 2. Validate UI elements if specified
            if "has_text" in expected_state or "not_has_text" in expected_state:
                try:
                    ui_elements = get_ui_hierarchy(self.device_id)
                    
                    if not ui_elements:
                        logger.warning("UI 树为空")
                        return False, "UI 树为空，无法验证"
                    
                    # 检查必需文本
                    if "has_text" in expected_state:
                        required_text = expected_state["has_text"]
                        found = any(required_text in elem.text for elem in ui_elements if elem.text)
                        
                        if not found:
                            error_msg = f"未找到预期文本: '{required_text}'"
                            logger.error(f"{error_msg}")
                            return False, error_msg
                        
                    logger.info(f"  [OK] 找到预期文本: {required_text}")
                    
                    # 检查禁止文本
                    if "not_has_text" in expected_state:
                        forbidden_text = expected_state["not_has_text"]
                        found = any(forbidden_text in elem.text for elem in ui_elements if elem.text)
                        
                        if found:
                            error_msg = f"发现不应存在的文本: '{forbidden_text}'"
                            logger.error(f"{error_msg}")
                            return False, error_msg
                        
                    logger.info(f"未发现禁止文本: {forbidden_text}")
                
                except Exception as e:
                    logger.warning(f"UI 验证失败: {e}")
                    return False, f"UI 验证失败: {str(e)}"
            
            logger.info(f"XML 验证通过")
            return True, f"XML checkpoint passed: {description}"
            
        except Exception as e:
            logger.error(f"XML 验证异常: {e}", exc_info=True)
            return False, f"XML validation error: {str(e)}"
    
    def _validate_with_vision(self, description: str, expected_state: dict, is_critical: bool) -> tuple[bool, str]:
        """
        [NEW] 使用 Vision 验证（可靠、成本较高）
        
        优势：
        - 可靠性高（~95%）
        - 可验证视觉内容
        - 不依赖 UI 树
        
        成本：
        - 速度慢（~2-3秒）
        - 成本高（~$0.05/次）
        """
        self._vision_checkpoint_count += 1
        logger.info(f"使用 Vision 验证（可靠模式，第 {self._vision_checkpoint_count}/{self.checkpoint_config.max_vision_checkpoints} 次）")
        
        # 检查是否有模型配置
        if not self.model_config:
            logger.warning("未配置模型，降级到 XML 验证")
            return self._validate_with_xml(description, expected_state)
        
        try:
            from phone_agent.adb import get_screenshot, get_current_app
            from phone_agent.model import ModelClient
            from phone_agent.model.client import MessageBuilder
            
            # 1. 获取当前截图
            screenshot = get_screenshot(self.device_id)
            if not screenshot:
                logger.error("无法获取截图")
                return False, "无法获取截图"
            
            # 2. 构建验证提示词
            validation_prompt = self._build_vision_validation_prompt(description, expected_state)
            
            # 3. 调用 Vision 模型
            model_client = ModelClient(self.model_config)
            
            messages = [
                MessageBuilder.create_system_message(
                    "你是一个手机界面验证专家。请根据截图验证是否满足给定的条件。"
                    "只回答'是'或'否'，并简要说明原因。"
                ),
                MessageBuilder.create_user_message(
                    text=validation_prompt,
                    image_base64=screenshot.base64_data
                )
            ]
            
            response = model_client.request(messages, temperature=0.1)
            answer = response.content.strip().lower()
            
            logger.info(f"Vision 响应: {response.content[:100]}")
            # 4. 解析结果
            if "是" in answer or "yes" in answer or "满足" in answer or "通过" in answer:
                logger.info(f"Vision 验证通过")
                return True, f"Vision checkpoint passed: {description}"
            else:
                error_msg = f"Vision 验证失败: {response.content}"
                logger.error(f"{error_msg}")
                return False, error_msg
        
        except Exception as e:
            logger.error(f"Vision 验证异常: {e}", exc_info=True)
            
            # Vision 失败，如果是非关键检查点，尝试 XML 兜底
            if not is_critical:
                logger.info(f"Vision 验证失败，尝试 XML 兜底...")
                return self._validate_with_xml(description, expected_state)
            
            return False, f"Vision validation error: {str(e)}"
    
    def _build_vision_validation_prompt(self, description: str, expected_state: dict) -> str:
        """[NEW] 构建 Vision 验证提示词"""
        prompt_parts = [f"检查点描述: {description}\n\n请验证以下条件：\n"]
        
        if "current_app" in expected_state:
            prompt_parts.append(f"- 当前应用是否为 '{expected_state['current_app']}'？\n")
        
        if "has_text" in expected_state:
            prompt_parts.append(f"- 屏幕上是否显示文本 '{expected_state['has_text']}'？\n")
        
        if "not_has_text" in expected_state:
            prompt_parts.append(f"- 屏幕上是否不包含文本 '{expected_state['not_has_text']}'？\n")
        
        if "visual_check" in expected_state:
            prompt_parts.append(f"- {expected_state['visual_check']}\n")
        
        prompt_parts.append("\n所有条件都满足吗？请回答'是'或'否'，并说明原因。")
        
        return "".join(prompt_parts)
    
    def _execute_human_confirm(self, params: dict) -> tuple[bool, str]:
        """
        [NEW] Execute HUMAN_CONFIRM action - request human confirmation.
        
        Args:
            params: Parameters including:
                - message: Confirmation message
                - options: List of options (default: ["确认", "取消"])
                - timeout: Timeout in seconds (default: 60)
        
        Returns:
            Tuple of (success, message)
        """
        message = params.get("message", "请确认是否继续")
        options = params.get("options", ["确认", "取消"])
        timeout = params.get("timeout", 60)
        
        logger.info(f"请求人工确认: {message}")
        logger.info(f"选项: {', '.join(options)}")
        
        if not self.human_intervention_callback:
            logger.warning("未配置人工介入回调，自动通过")
            return True, "人工确认（自动通过）"
        
        try:
            # Create intervention request
            request = HumanInterventionRequest(
                type="confirm",
                message=message,
                options=options,
                timeout=timeout
            )
            
            # Wait for human response
            success, response = self.human_intervention_callback(request)
            
            if not success:
                logger.info(f"用户取消操作")
                return False, "用户取消操作"
            
            selected_option = response.get("selected_option", "确认")
            logger.info(f"用户确认: {selected_option}")
            return True, f"用户确认: {selected_option}"
            
        except Exception as e:
            logger.error(f"人工确认失败: {e}", exc_info=True)
            return False, f"人工确认失败: {str(e)}"
    
    def _execute_human_input(self, params: dict) -> tuple[bool, str]:
        """
        [NEW] Execute HUMAN_INPUT action - request human input.
        
        Args:
            params: Parameters including:
                - prompt: Input prompt message
                - input_type: Input type (text, password, number, captcha)
                - placeholder: Placeholder text
                - timeout: Timeout in seconds (default: 60)
        
        Returns:
            Tuple of (success, message)
        """
        prompt = params.get("prompt", "请输入")
        input_type = params.get("input_type", "text")
        placeholder = params.get("placeholder", "")
        timeout = params.get("timeout", 60)
        
        logger.info(f"请求人工输入: {prompt}")
        logger.info(f"类型: {input_type}")
        
        if not self.human_intervention_callback:
            logger.warning("未配置人工介入回调，跳过输入")
            return False, "未配置人工介入回调"
        
        try:
            # Create intervention request
            request = HumanInterventionRequest(
                type="input",
                message=prompt,
                input_type=input_type,
                placeholder=placeholder,
                timeout=timeout
            )
            
            # Wait for human input
            success, response = self.human_intervention_callback(request)
            
            if not success:
                logger.info(f"用户取消输入")
                return False, "用户取消输入"
            
            user_input = response.get("input_value", "")
            
            if not user_input:
                logger.warning(f"用户输入为空")
                return False, "用户输入为空"
            
            # Type the user input
            logger.info(f"收到用户输入，正在输入到设备...")
            type_text(user_input, self.device_id)
            time.sleep(0.3)
            
            # Mask sensitive input in log
            masked_input = "*" * len(user_input) if input_type in ["password", "captcha"] else user_input
            return True, f"用户输入已完成: {masked_input}"
            
        except Exception as e:
            logger.error(f"人工输入失败: {e}", exc_info=True)
            return False, f"人工输入失败: {str(e)}"
    
    def _is_critical_step(self, plan: TaskPlan, step_num: int) -> bool:
        """Check if a step has a critical checkpoint."""
        for checkpoint in plan.checkpoints:
            if checkpoint.get("step_id") == step_num and checkpoint.get("critical", False):
                return True
        return False
    
    def _find_element_by_selector(self, selector: dict[str, Any]) -> tuple[int, int, bool]:
        """
        Find element using XML-based smart positioning.
        
        Args:
            selector: Element selector with optional fields:
                - text: Element text content
                - content_desc: Content description
                - resource_id: Android resource ID
                - class_name: Android class name
        
        Returns:
            Tuple of (x, y, found) where:
            - x, y: Center coordinates if found
            - found: Whether element was successfully located
        """
        try:
            from phone_agent.adb.xml_tree import get_ui_hierarchy
            
            elements = get_ui_hierarchy(self.device_id)
            
            if not elements:
                logger.warning("No UI elements found, XML tree might be empty")
                return 0, 0, False
            
            # Try to match by各个selector条件
            text_match = selector.get("text")
            content_desc = selector.get("content_desc")
            resource_id = selector.get("resource_id")
            class_name = selector.get("class_name")
            
            for elem in elements:
                # Match by text (支持部分匹配)
                if text_match:
                    if elem.text and text_match.lower() in elem.text.lower():
                        logger.info(f"Found element by text: '{text_match}' at ({elem.center_x}, {elem.center_y})")
                        return elem.center_x, elem.center_y, True
                
                # Match by content description
                if content_desc:
                    if elem.content_desc and content_desc.lower() in elem.content_desc.lower():
                        logger.info(f"Found element by content_desc: '{content_desc}' at ({elem.center_x}, {elem.center_y})")
                        return elem.center_x, elem.center_y, True
                
                # Match by resource ID (精确匹配)
                if resource_id:
                    if elem.resource_id == resource_id:
                        logger.info(f"Found element by resource_id: '{resource_id}' at ({elem.center_x}, {elem.center_y})")
                        return elem.center_x, elem.center_y, True
                
                # Match by class name
                if class_name:
                    if elem.class_name and class_name in elem.class_name:
                        logger.info(f"Found element by class: '{class_name}' at ({elem.center_x}, {elem.center_y})")
                        return elem.center_x, elem.center_y, True
            
            logger.warning(f"No element found matching selector: {selector}")
            return 0, 0, False
            
        except Exception as e:
            logger.error(f"Error during smart positioning: {e}", exc_info=True)
            return 0, 0, False

