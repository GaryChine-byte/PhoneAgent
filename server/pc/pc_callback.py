#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
PC Agent 回调 - 任务执行过程中的状态回调

负责:
1. 步骤开始/结束通知
2. 截图保存 (复用 ScreenshotService)
3. 日志记录 (复用 TaskLogger)
"""

import base64
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PCCallback:
    """
    PC Agent 回调
    
    用于任务执行过程中的状态回调,复用现有的通用服务。
    
    Attributes:
        task: PC 任务对象
        screenshot_service: 截图服务
        task_logger: 任务日志记录器 (可选)
    """
    
    def __init__(
        self,
        task,
        screenshot_service,
        task_logger=None
    ):
        """
        初始化回调
        
        Args:
            task: PC 任务对象 (PCTask)
            screenshot_service: ScreenshotService 实例
            task_logger: TaskLogger 实例 (可选)
        """
        self.task = task
        self.screenshot_service = screenshot_service
        self.task_logger = task_logger
    
    def on_step_start(self, step: int):
        """
        步骤开始回调
        
        Args:
            step: 步骤编号
        """
        logger.info(f"[Task {self.task.task_id}] Step {step} started")
        
        # TaskLogger 只在步骤完成时记录，开始时不需要记录
        # 保持此方法为空操作，仅用于日志输出
    
    def on_step_end(
        self,
        step: int,
        success: bool,
        thinking: str,
        action: Dict,
        observation: str,
        reflection: str = "",
        planning: str = ""
    ):
        """
        步骤结束回调
        
        Args:
            step: 步骤编号
            success: 是否成功
            thinking: 思考过程
            action: 执行的动作
            observation: 观察结果
            reflection: 反思结果 (A/B/C/D)
            planning: 规划进度
        """
        # 记录到 task.steps (与 PhoneAgent 保持一致，添加反思和规划字段)
        step_data = {
            "step": step,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "thinking": thinking,
            "action": action,
            "observation": observation,
            "reflection": reflection,  # 新增
            "planning": planning,  # 新增
            "success": success,
            "status": "completed" if success else "failed"
        }
        
        self.task.steps.append(step_data)
        
        logger.info(
            f"[Task {self.task.task_id}] Step {step} "
            f"{'succeeded' if success else 'failed'}: {observation}"
        )
        
        # 日志记录
        if self.task_logger:
            # TaskLogger.log_step 需要完整的参数
            self.task_logger.log_step(
                task_id=self.task.task_id,
                step=step,
                timestamp=step_data["timestamp"],
                thinking=thinking,
                action=action,
                observation=observation,
                screenshot_path=step_data.get("screenshot"),
                performance=None,
                tokens_used=None
            )
    
    async def save_screenshot(self, step: int) -> Optional[Dict]:
        """
        保存截图 (复用 ScreenshotService)
        
        Args:
            step: 步骤编号
            
        Returns:
            截图路径字典或 None:
            {
                "ai": str,
                "medium": str,
                "small": str,
                "thumbnail": str,
                "original": str
            }
        """
        try:
            # 获取截图
            if not self.task.agent:
                logger.warning(f"Task {self.task.task_id}: Agent not available")
                return None
            
            screenshot_bytes = await self.task.agent.take_screenshot()
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode()
            
            # 获取步骤信息
            step_data = None
            if self.task.steps:
                for s in reversed(self.task.steps):
                    if s.get("step") == step:
                        step_data = s
                        break
            
            if not step_data:
                logger.warning(f"Step data not found for step {step}")
                return None
            
            # 保存截图 (复用现有服务)
            result = await self.screenshot_service.save_step_screenshot(
                task_id=self.task.task_id,
                device_id=self.task.device_id,
                step_number=step,
                screenshot_base64=screenshot_base64,
                action=step_data.get("action", {}),
                thinking=step_data.get("thinking", ""),
                observation=step_data.get("observation", ""),
                success=step_data.get("success", False),
                kernel_mode="vision",  # PC 默认使用 vision
                tokens_used=None
            )
            
            if result:
                logger.info(f"Screenshot saved for step {step}")
                return result.model_dump() if hasattr(result, 'model_dump') else result.dict()
            else:
                return None
        
        except Exception as e:
            logger.error(f"保存截图失败: {e}", exc_info=True)
            return None
    
    def on_progress(self, current: int, total: int, message: str = ""):
        """
        进度更新回调 (可选)
        
        Args:
            current: 当前进度
            total: 总进度
            message: 进度消息
        """
        logger.info(f"[Task {self.task.task_id}] Progress: {current}/{total} - {message}")
    
    def on_error(self, error: Exception):
        """
        错误回调 (可选)
        
        Args:
            error: 异常对象
        """
        logger.error(f"[Task {self.task.task_id}] Error: {error}", exc_info=True)
        
        if self.task_logger:
            self.task_logger.log_error(str(error))
