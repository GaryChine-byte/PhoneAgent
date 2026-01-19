#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
Kernel Package - Android自动化内核

包含多种内核实现：
- XMLKernelAgent: 基于UI树的快速内核
- HybridAgent: 混合内核（XML + Vision）

统一接口：
- BaseKernel: 抽象基类
- ExecutionCallback: 执行回调协议
- StepCallback: 步骤回调协议
"""

from phone_agent.kernel.vision_agent import PhoneAgent, AgentConfig
from phone_agent.kernel.xml_agent import XMLKernelAgent, XMLKernelConfig
from phone_agent.kernel.hybrid_agent import HybridAgent, HybridConfig, ExecutionMode
from phone_agent.kernel.base import BaseKernel
from phone_agent.kernel.protocols import ExecutionCallback
from phone_agent.kernel.callback import (
    StepCallback,
    NoOpCallback,
    AsyncStepCallback
)

__all__ = [
    # Kernel实现
    "PhoneAgent",           # Vision Kernel
    "AgentConfig",          # Vision Kernel Config
    "XMLKernelAgent",       # XML Kernel
    "XMLKernelConfig",      # XML Kernel Config
    "HybridAgent",          # Hybrid Kernel
    "HybridConfig",         # Hybrid Kernel Config
    "ExecutionMode",        # Execution Mode Enum
    
    # 基类和协议
    "BaseKernel",
    "ExecutionCallback",
    "StepCallback",
    "NoOpCallback",
    "AsyncStepCallback",
]
