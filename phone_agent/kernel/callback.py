#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
统一的步骤回调接口

用于所有Agent（Vision、XML、Hybrid）的进度通知

架构说明：
- StepCallback: 同步回调接口，供Agent层使用
- AsyncStepCallback: 异步回调适配器，供AgentService层使用
- 这样保持Agent层纯同步，Service层异步包装
"""

from typing import Protocol, Optional, Dict, Any, List, Tuple


class StepCallback(Protocol):
    """
    步骤回调接口（协议类）- 同步版本
    
    所有Agent都应该支持这个回调接口，以便Service层能够记录任务进度
    
    注意：这是同步接口，Agent在执行过程中直接调用，不涉及asyncio
    """
    
    def on_step_start(self, step: int, action: str) -> None:
        """
        步骤开始时的回调
        
        Args:
            step: 步骤编号（从1开始）
            action: 动作描述
        """
        ...
    
    def on_step_complete(
        self,
        step: int,
        success: bool,
        thinking: str = "",
        observation: str = "",
        screenshot_path: Optional[str] = None
    ) -> None:
        """
        步骤完成时的回调
        
        Args:
            step: 步骤编号
            success: 是否成功
            thinking: AI的思考过程
            observation: 执行观察结果
            screenshot_path: 截图路径（可选）
        """
        ...
    
    def on_error(self, error: str) -> None:
        """
        发生错误时的回调
        
        Args:
            error: 错误信息
        """
        ...


class NoOpCallback:
    """
    空回调实现（用于测试或不需要回调的场景）
    """
    
    def on_step_start(self, step: int, action: str) -> None:
        pass
    
    def on_step_complete(
        self,
        step: int,
        success: bool,
        thinking: str = "",
        observation: str = "",
        screenshot_path: Optional[str] = None
    ) -> None:
        pass
    
    def on_error(self, error: str) -> None:
        pass


class AsyncStepCallback:
    """
    异步回调适配器（实时广播版本）
    
    用于在AgentService层将同步callback转换为异步broadcast：
    1. Agent调用同步方法时，通过线程安全方式调用同步回调
    2. 保持架构一致性：
       - Agent层：纯同步，无需关心asyncio
       - Service层：同步回调直接执行（已经在 AgentCallback 中处理异步）
    
    注意：AgentCallback 的方法是同步的，内部已经处理了异步广播
    """
    
    def __init__(self, sync_callback, loop=None):
        """
        Args:
            sync_callback: 同步回调对象（如AgentCallback，方法是 def 而不是 async def）
            loop: asyncio事件循环（可选，用于兼容性，实际不使用）
        """
        self._sync_callback = sync_callback
        self._loop = loop
    
    def on_step_start(self, step: int, action: str) -> None:
        """同步接口，直接调用同步回调"""
        # AgentCallback.on_step_start 是同步方法，直接调用即可
        # 它内部会处理异步广播（通过 asyncio.run_coroutine_threadsafe）
        self._sync_callback.on_step_start(step, action)
    
    def on_step_complete(
        self,
        step: int,
        success: bool,
        thinking: str = "",
        observation: str = "",
        screenshot_path: Optional[str] = None
    ) -> None:
        """同步接口，直接调用同步回调"""
        # AgentCallback.on_step_complete 是同步方法，直接调用即可
        # [WARN] 注意：AgentCallback 不接受 screenshot_path 参数，因为截图由 AgentService 统一管理
        self._sync_callback.on_step_complete(step, success, thinking, observation)
    
    def on_error(self, error: str) -> None:
        """同步接口，直接调用同步回调"""
        # AgentCallback.on_error 是同步方法，直接调用即可
        self._sync_callback.on_error(error)
    
    async def flush(self):
        """兼容性方法：实时版本不需要flush，但保留接口"""
        pass
    
    def has_pending(self) -> bool:
        """兼容性方法：实时版本没有待处理事件，总是返回False"""
        return False

