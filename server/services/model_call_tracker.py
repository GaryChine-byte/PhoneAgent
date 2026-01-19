#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
模型调用追踪器

在Agent执行过程中自动记录模型调用统计
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

from server.database import crud, get_db

logger = logging.getLogger(__name__)


class ModelCallTracker:
    """模型调用追踪器"""
    
    @staticmethod
    async def track_call(
        task_id: str,
        model_name: str,
        kernel_mode: str,
        usage: Dict[str, int],
        latency_ms: int,
        provider: str = "zhipu",
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """
        记录模型调用
        
        Args:
            task_id: 任务ID
            model_name: 模型名称
            kernel_mode: 内核模式 (xml/vision/auto)
            usage: Token使用情况 {"prompt_tokens": 100, "completion_tokens": 50}
            latency_ms: 延迟（毫秒）
            provider: 提供商
            success: 是否成功
            error_message: 错误信息（如果失败）
        """
        try:
            import asyncio
            
            def _record():
                db = next(get_db())
                try:
                    # 计算成本（智谱AI定价，可配置）
                    cost_usd = ModelCallTracker._calculate_cost(
                        model_name,
                        usage.get("prompt_tokens", 0),
                        usage.get("completion_tokens", 0)
                    )
                    
                    crud.create_model_call(
                        db,
                        task_id=task_id,
                        provider=provider,
                        model_name=model_name,
                        kernel_mode=kernel_mode,
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                        latency_ms=latency_ms,
                        cost_usd=cost_usd,
                        success=success,
                        error_message=error_message
                    )
                    
                    logger.debug(
                        f"Model call tracked: {model_name} | "
                        f"{usage.get('total_tokens', 0)} tokens | "
                        f"${cost_usd:.4f}"
                    )
                finally:
                    db.close()
            
            # 异步执行，不阻塞主流程
            await asyncio.get_event_loop().run_in_executor(None, _record)
            
        except Exception as e:
            # 记录失败不应影响主流程
            logger.error(f"Failed to track model call: {e}")     
    @staticmethod
    def _calculate_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        计算成本（美元）
        
        智谱AI定价（2025年）:
        - glm-4-flash: 免费
        - glm-4-1.5v-thinking-flash: 免费
        - autoglm-phone: 免费
        
        未来可扩展为付费模型定价
        """
        # 当前所有模型免费
        if "flash" in model_name.lower() or "autoglm" in model_name.lower():
            return 0.0
        
        # 预留付费模型定价（示例）
        pricing = {
            "glm-4-plus": {
                "prompt": 0.05 / 1000,  # $0.05 per 1K tokens
                "completion": 0.05 / 1000
            },
            "glm-4-air": {
                "prompt": 0.001 / 1000,
                "completion": 0.001 / 1000
            }
        }
        
        if model_name in pricing:
            cost = (
                prompt_tokens * pricing[model_name]["prompt"] +
                completion_tokens * pricing[model_name]["completion"]
            )
            return round(cost, 6)
        
        return 0.0


# 便捷函数
async def track_model_call(
    task_id: str,
    model_name: str,
    kernel_mode: str,
    usage: Dict[str, int],
    latency_ms: int,
    **kwargs
):
    """便捷的模型调用追踪函数"""
    await ModelCallTracker.track_call(
        task_id=task_id,
        model_name=model_name,
        kernel_mode=kernel_mode,
        usage=usage,
        latency_ms=latency_ms,
        **kwargs
    )

