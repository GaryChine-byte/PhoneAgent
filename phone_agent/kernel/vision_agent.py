#!/usr/bin/env python3
# Original: Copyright (c) 2024 ZAI Organization (Apache-2.0)
# Modified: Copyright (C) 2025 PhoneAgent Contributors (AGPL-3.0)
# Based on: https://github.com/zai-org/Open-AutoGLM

"""PhoneAgent主类 - 编排手机自动化"""

import json
import logging
import traceback
from dataclasses import dataclass
from typing import Any, Callable

from phone_agent.actions.vision_format import (
    parse_vision_action,  # [Phase 4] 仅用于兼容 do() 格式，逐步废弃
    # convert_to_standard_action,  # [Phase 4] 已移除，直接使用 parse_action
    do,  # 辅助函数，保留
    finish  # 辅助函数，保留（已废弃）
)
from phone_agent.actions import ActionExecutor
from phone_agent.adb import get_current_app, get_screenshot
from phone_agent.config import SYSTEM_PROMPT
from phone_agent.model import ModelClient, ModelConfig
from phone_agent.model.client import MessageBuilder

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """PhoneAgent配置"""

    max_steps: int = 100
    device_id: str | None = None
    adb_host: str | None = None  # FRP隧道主机
    adb_port: int | None = None  # FRP隧道端口
    system_prompt: str = SYSTEM_PROMPT
    verbose: bool = True


@dataclass
class StepResult:
    """单个代理步骤的结果"""

    success: bool
    finished: bool
    action: dict[str, Any] | None
    thinking: str
    message: str | None = None
    usage: dict[str, Any] | None = None  # AI模型的token使用量


class PhoneAgent:
    """
    AI驱动的Android手机交互自动化代理

    该代理使用视觉语言模型理解屏幕内容并决定动作以完成用户任务。

    Args:
        model_config: AI模型配置
        agent_config: 代理行为配置
        confirmation_callback: 敏感操作确认回调(可选)
        takeover_callback: 接管请求回调(可选)

    Example:
        >>> from phone_agent import PhoneAgent
        >>> from phone_agent.model import ModelConfig
        >>>
        >>> model_config = ModelConfig(base_url="http://localhost:8000/v1")
        >>> agent = PhoneAgent(model_config)
        >>> agent.run("打开微信并给John发消息")
    """

    def __init__(
        self,
        model_config: ModelConfig | None = None,
        agent_config: AgentConfig | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
        step_callback: Any | None = None,  # 新增：步骤回调
    ):
        self.model_config = model_config or ModelConfig()
        self.agent_config = agent_config or AgentConfig()

        self.model_client = ModelClient(self.model_config)
        
        # 回调
        self.confirmation_callback = confirmation_callback
        self.takeover_callback = takeover_callback

        self._context: list[dict[str, Any]] = []
        self._step_count = 0
        
        # Action Executor（延迟初始化）
        self._action_executor = None
        
        # 新增：步骤回调支持
        from phone_agent.kernel.callback import NoOpCallback
        self.step_callback = step_callback or NoOpCallback()

    def run(self, task: str) -> str:
        """
        运行代理以完成任务

        Args:
            task: 任务的自然语言描述

        Returns:
            代理的最终消息
        """
        self._context = []
        self._step_count = 0

        # 第一步,使用用户提示词
        result = self._execute_step(task, is_first=True)

        if result.finished:
            return result.message or "任务完成"

        # 继续执行直到完成或达到最大步数
        while self._step_count < self.agent_config.max_steps:
            result = self._execute_step(is_first=False)

            if result.finished:
                return result.message or "任务完成"

        return "Max steps reached"

    def step(self, task: str | None = None) -> StepResult:
        """
        Execute a single step of the agent.

        Useful for manual control or debugging.

        Args:
            task: Task description (only needed for first step).

        Returns:
            StepResult with step details.
        """
        is_first = len(self._context) == 0

        if is_first and not task:
            raise ValueError("Task is required for the first step")

        return self._execute_step(task, is_first)

    def reset(self) -> None:
        """重置代理状态以开始新任务"""
        self._context = []
        self._step_count = 0
    
    def _normalize_action_for_log(
        self, action: dict[str, Any], screen_width: int, screen_height: int
    ) -> dict[str, Any]:
        """
        规范化动作格式用于日志记录
        
        将 Vision Kernel 的 element 坐标（归一化 0-1000）转换为
        标准的 coordinates 格式（绝对像素），以便与 XML Kernel 的日志格式统一
        
        Args:
            action: 原始动作字典
            screen_width: 屏幕宽度
            screen_height: 屏幕高度
        
        Returns:
            规范化后的动作字典
        """
        normalized = action.copy()
        action_name = action.get("action", "").lower()
        
        # 处理包含 element 字段的动作（Tap, Long Press, Double Tap）
        if "element" in action:
            element = action["element"]
            if isinstance(element, list) and len(element) == 2:
                # 转换为绝对坐标
                x = int(element[0] / 1000 * screen_width) if element[0] <= 1000 else element[0]
                y = int(element[1] / 1000 * screen_height) if element[1] <= 1000 else element[1]
                normalized["coordinates"] = [x, y]
                # 保留原始 element 字段以便调试
                normalized["element_normalized"] = element
        
        # 处理 Swipe 动作
        if "start" in action and "end" in action:
            start = action["start"]
            end = action["end"]
            if isinstance(start, list) and len(start) == 2:
                start_x = int(start[0] / 1000 * screen_width) if start[0] <= 1000 else start[0]
                start_y = int(start[1] / 1000 * screen_height) if start[1] <= 1000 else start[1]
                normalized["start"] = [start_x, start_y]
            if isinstance(end, list) and len(end) == 2:
                end_x = int(end[0] / 1000 * screen_width) if end[0] <= 1000 else end[0]
                end_y = int(end[1] / 1000 * screen_height) if end[1] <= 1000 else end[1]
                normalized["end"] = [end_x, end_y]
        
        # 处理 Scroll 动作（x, y 坐标）
        if "x" in action and "y" in action:
            x = action["x"]
            y = action["y"]
            if x <= 1000:
                normalized["x"] = int(x / 1000 * screen_width)
            if y <= 1000:
                normalized["y"] = int(y / 1000 * screen_height)
        
        return normalized
    
    def _check_context_usage(self) -> None:
        """
        轻量级上下文使用监控
        
        提供任务步数的可见性，帮助识别异常长的任务。
        不会阻止任务执行，仅记录日志。
        """
        current_step = self._step_count
        
        # 基础信息：长任务提醒
        if current_step > 30:
            logger.info(f"长任务检测: 当前步数 {current_step}")
        
        # 估算上下文使用（可选，用于调试）
        if current_step > 50:
            # 粗略估算: 系统提示词(5093) + 每步历史(100) + 保留空间(1500)
            estimated_tokens = 5093 + (current_step - 1) * 100 + 1500
            context_limit = 16384  # glm-4.6v-flash的保守估计
            usage_percent = (estimated_tokens / context_limit) * 100
            
            logger.info(
                f"上下文估算: {estimated_tokens:,} tokens "
                f"({usage_percent:.1f}% / {context_limit:,})"
            )
            
            if usage_percent > 80:
                logger.warning(
                    f"上下文使用较高: {usage_percent:.1f}% "
                    f"(步数: {current_step})"
                )
        
        # 极限情况告警
        if current_step > 80:
            logger.warning(
                f"极长任务: {current_step} 步，可能存在问题 "
                f"(建议检查任务是否卡住)"
            )

    def _execute_step(
        self, user_prompt: str | None = None, is_first: bool = False
    ) -> StepResult:
        """执行代理循环的单个步骤"""
        self._step_count += 1
        
        # [NEW] 轻量级上下文监控
        self._check_context_usage()
        
        # [WARN] 不在这里调用 on_step_start,因为此时还没有 thinking 和 action
        # on_step_start 会在 LLM 响应后、执行动作前调用

        # 捕获当前屏幕状态
        # [FIX] 与 XML Kernel 保持一致：只传递 device_id（已包含完整连接信息）
        # device_id 格式如 "localhost:6100" 本身就包含 host:port
        screenshot = get_screenshot(device_id=self.agent_config.device_id)
        # [OK] 修复: get_current_app 只接受 device_id 参数
        current_app = get_current_app(device_id=self.agent_config.device_id)

        # 构建消息
        if is_first:
            self._context.append(
                MessageBuilder.create_system_message(self.agent_config.system_prompt)
            )

            screen_info = MessageBuilder.build_screen_info(current_app)
            text_content = f"{user_prompt}\n\n{screen_info}"

            self._context.append(
                MessageBuilder.create_user_message(
                    text=text_content, image_base64=screenshot.base64_data
                )
            )
        else:
            screen_info = MessageBuilder.build_screen_info(current_app)
            text_content = f"** Screen Info **\n\n{screen_info}"

            self._context.append(
                MessageBuilder.create_user_message(
                    text=text_content, image_base64=screenshot.base64_data
                )
            )

        # 获取模型响应（使用XML+JSON混合格式）
        try:
            response = self.model_client.request(self._context)
        except Exception as e:
            if self.agent_config.verbose:
                traceback.print_exc()
            return StepResult(
                success=False,
                finished=True,
                action=None,
                thinking="",
                message=f"Model error: {e}",
            )

        # 解析action字符串为动作对象
        # [Phase 4] response.action 现在可以是 dict 或 str
        # - dict: 标准 JSON 格式（优先，来自 ResponseParser）
        # - str: do() 格式字符串（兼容，逐步废弃）
        thinking_text = response.thinking
        action_data = response.action
        
        if not action_data:
            logger.warning(f"模型响应缺少action: {response.raw_content[:200]}")
            return StepResult(
                success=False,
                finished=True,
                action=None,
                thinking=thinking_text,
                message="Model response missing action field",
            )
        
        try:
            # [Phase 4] 优先处理 dict 类型（新架构）
            if isinstance(action_data, dict):
                action_dict = action_data
                
                # 容错：element → coordinates（Phase 5 可移除）
                if "element" in action_dict:
                    logger.warning("⚠️ 检测到废弃的 'element' 参数，请更新提示词使用 'coordinates'")
                    action_dict["coordinates"] = action_dict.pop("element")
                
                # 容错：finish → done（Phase 5 可移除）
                if action_dict.get("action", "").lower() == "finish":
                    logger.warning("⚠️ 检测到废弃的 'finish' 动作，自动转换为 'done'")
                    action_dict["action"] = "done"
                
            # [Phase 4] 降级处理 str 类型（兼容旧格式）
            elif isinstance(action_data, str):
                action_str = action_data.strip()
                
                # 尝试解析为 JSON
                if action_str.startswith("{"):
                    try:
                        action_dict = json.loads(action_str)
                        
                        # 容错映射
                        if "element" in action_dict:
                            action_dict["coordinates"] = action_dict.pop("element")
                        if action_dict.get("action", "").lower() == "finish":
                            action_dict["action"] = "done"
                    except json.JSONDecodeError:
                        # JSON 解析失败，尝试 do() 格式
                        logger.warning("JSON 解析失败，尝试 do() 格式")
                        action_dict = parse_vision_action(action_str)
                else:
                    # do() 格式（逐步废弃）
                    logger.warning("⚠️ 检测到 do() 格式，建议更新提示词使用 JSON")
                    action_dict = parse_vision_action(action_str)
            else:
                raise ValueError(f"不支持的 action 类型: {type(action_data)}")
                
        except (ValueError, json.JSONDecodeError) as e:
            # 解析失败
            if self.agent_config.verbose:
                logger.error(f"Action解析失败: {action_data}, 错误: {e}")
                traceback.print_exc()
            # 创建 done 动作（错误情况）
            action_dict = {"action": "done", "message": f"解析失败: {action_data}"}

        # 处理 done/finish(容错) 动作
        if action_dict.get("_metadata") == "finish" or action_dict.get("action") == "done":
            finished = True
            message = action_dict.get("message", "任务完成")
            
            # 通知步骤完成
            self.step_callback.on_step_complete(
                self._step_count,
                True,
                thinking=thinking_text,
                observation=message
            )
            
            if self.agent_config.verbose:
                logger.info("="*50)
                logger.info(f"任务完成: {message}")
                logger.info("="*50)
            
            return StepResult(
                success=True,
                finished=True,
                action=action_dict,
                thinking=thinking_text,
                usage=None
            )
        
        # 处理 Take_over 动作（特殊，需要回调）
        if action_dict.get("action") == "Take_over":
            message = action_dict.get("message", "需要用户介入")
            if self.takeover_callback:
                self.takeover_callback(message)
            
            self.step_callback.on_step_complete(
                self._step_count,
                True,
                thinking=thinking_text,
                observation=message
            )
            
            return StepResult(
                success=True,
                finished=False,
                action=action_dict,
                thinking=thinking_text,
                usage=None
            )
        
        # [Phase 4] 直接使用 parse_action 转换为标准 Action 对象
        # 不再需要 convert_to_standard_action（vision_format.py）
        try:
            from phone_agent.actions.parse import parse_action
            standard_action = parse_action(action_dict)
        except Exception as e:
            logger.error(f"动作解析失败: {e}")
            traceback.print_exc()
            return StepResult(
                success=False,
                finished=False,
                action=action_dict,
                thinking=thinking_text,
                usage=None
            )
        
        # 规范化坐标格式用于日志
        normalized_action = self._normalize_action_for_log(action_dict, screenshot.width, screenshot.height)
        
        step_info = {
            "thinking": thinking_text,
            "action": normalized_action
        }
        self.step_callback.on_step_start(self._step_count, json.dumps(step_info, ensure_ascii=False))
        
        if self.agent_config.verbose:
            logger.debug("="*50)
            logger.debug("思考过程:")
            logger.debug("-"*50)
            logger.debug(thinking_text)
            logger.debug("-"*50)
            logger.debug("执行动作:")
            logger.debug(json.dumps(action_dict, ensure_ascii=False, indent=2))
            logger.debug("="*50)

        # Remove image from context to save space
        self._context[-1] = MessageBuilder.remove_images_from_message(self._context[-1])

        # 初始化 ActionExecutor
        if self._action_executor is None:
            self._action_executor = ActionExecutor(
                device_id=self.agent_config.device_id,
                screen_width=screenshot.width,
                screen_height=screenshot.height
            )
        
        # 执行动作
        try:
            result_dict = self._action_executor.execute(standard_action)
            success = result_dict.get("success", False)
            message = result_dict.get("message", "")
            
            # 判断是否应该结束
            should_finish = result_dict.get("done", False)
        except Exception as e:
            if self.agent_config.verbose:
                traceback.print_exc()
            success = False
            message = str(e)
            should_finish = False

        # Add assistant response to context (使用XML+JSON混合格式)
        self._context.append(
            MessageBuilder.create_assistant_message(
                f"<thinking>{thinking_text}</thinking><tool_call>{json.dumps(action_dict, ensure_ascii=False)}</tool_call>"
            )
        )

        # 通知步骤完成
        self.step_callback.on_step_complete(
            self._step_count,
            success,
            thinking=thinking_text,
            observation=message
        )

        if should_finish and self.agent_config.verbose:
            logger.info("="*50)
            logger.info(f"任务完成: {message}")
            logger.info("="*50)

        return StepResult(
            success=success,
            finished=should_finish,
            action=action_dict,
            thinking=thinking_text,
            message=message,
            usage=response.usage,  # Pass token usage info
        )

    @property
    def context(self) -> list[dict[str, Any]]:
        """Get the current conversation context."""
        return self._context.copy()

    @property
    def step_count(self) -> int:
        """Get the current step count."""
        return self._step_count
