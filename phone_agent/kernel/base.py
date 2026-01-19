#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
Kernel抽象基类

定义所有Kernel的统一接口，确保：
1. 接口一致性
2. 可替换性
3. 类型安全
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from phone_agent.model import ModelConfig
from phone_agent.kernel.protocols import ExecutionCallback
from phone_agent.kernel.callback import StepCallback


class BaseKernel(ABC):
    """
    Kernel抽象基类
    
    所有Kernel实现都应继承此类，确保接口统一。
    
    设计原则:
    - 无状态: Kernel应该是可复用的，不依赖外部状态
    - 可测试: 通过依赖注入，便于单元测试
    - 可替换: 所有Kernel遵循相同接口，可以无缝切换
    
    Example:
        >>> class MyKernel(BaseKernel):
        ...     def run(self, goal: str) -> Dict[str, Any]:
        ...         # 实现执行逻辑
        ...         return {"success": True}
        ...     
        ...     def reset(self):
        ...         # 重置内部状态
        ...         pass
    """
    
    def __init__(
        self,
        model_config: ModelConfig,
        step_callback: Optional[StepCallback] = None,
        execution_callback: Optional[ExecutionCallback] = None
    ):
        """
        初始化Kernel
        
        Args:
            model_config: 模型配置
            step_callback: 步骤回调（可选）
            execution_callback: 执行回调（可选，用于Phase 1特性）
        """
        self.model_config = model_config
        self.step_callback = step_callback
        self.execution_callback = execution_callback
    
    @abstractmethod
    def run(self, goal: str) -> Dict[str, Any]:
        """
        执行任务
        
        Args:
            goal: 任务目标（自然语言）
        
        Returns:
            执行结果字典，至少包含:
            - success (bool): 是否成功
            - steps (int): 执行步骤数
            - message (str): 结果描述
            
            可选字段:
            - total_tokens (int): 总token消耗
            - prompt_tokens (int): 输入token
            - completion_tokens (int): 输出token
            - cost_estimate (float): 成本估算
            - mode (str): 执行模式
        
        Example:
            >>> kernel = MyKernel(model_config)
            >>> result = kernel.run("打开设置")
            >>> print(result)
            {'success': True, 'steps': 5, 'message': '任务完成'}
        """
        pass
    
    @abstractmethod
    def reset(self):
        """
        重置Kernel状态
        
        清理上下文、计数器等内部状态，为下一次执行做准备。
        """
        pass
    
    def set_execution_callback(self, callback: ExecutionCallback):
        """
        设置执行回调（Phase 1特性）
        
        Args:
            callback: 执行回调对象
        """
        self.execution_callback = callback
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息（可选实现）
        
        Returns:
            统计信息字典，可能包含:
            - total_runs (int): 总执行次数
            - success_rate (float): 成功率
            - avg_steps (float): 平均步骤数
            - avg_tokens (float): 平均token消耗
        """
        return {}


__all__ = ["BaseKernel"]
