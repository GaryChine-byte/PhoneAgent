#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
执行回调协议

定义Kernel执行过程中的回调接口，用于：
1. 记录重要内容（Phase 1）
2. 更新TODO列表（Phase 1）
3. 类型安全和IDE提示

注意：StepCallback 已移至 phone_agent.kernel.callback 模块
"""

from typing import Protocol, Optional, Dict, Any


class ExecutionCallback(Protocol):
    """
    执行回调协议（类型提示）
    
    用于Kernel与Service层通信，支持Phase 1高级特性。
    实现此协议的类可以接收Kernel执行过程中的通知。
    
    Example:
        >>> class MyCallback:
        ...     def on_record_content(self, content: str, category: str = None, reason: str = None):
        ...         print(f"记录: {content}")
        ...     
        ...     def on_update_todos(self, todos: str, reason: str = None):
        ...         print(f"TODO: {todos}")
        >>> 
        >>> callback: ExecutionCallback = MyCallback()
    """
    
    def on_record_content(
        self,
        content: str,
        category: str = None,
        reason: str = None
    ) -> None:
        """
        记录重要内容回调
        
        Args:
            content: 要记录的内容
            category: 内容分类（如：price, contact, url等）
            reason: 记录原因（可选）
        """
        ...
    
    def on_update_todos(
        self,
        todos: str,
        reason: str = None
    ) -> None:
        """
        更新TODO列表回调
        
        Args:
            todos: Markdown格式的TODO列表
            reason: 更新原因（可选）
        """
        ...


__all__ = [
    "ExecutionCallback",
]
