#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
PC 任务模型

定义 PC Agent 的任务数据结构,与 PhoneAgent 的 Task 保持一致。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum


class PCTaskStatus(Enum):
    """PC 任务状态"""
    PENDING = "pending"       # 等待执行
    RUNNING = "running"       # 执行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 已取消


@dataclass
class PCTask:
    """
    PC 任务
    
    与 PhoneAgent 的 Task 结构保持一致,便于前端复用组件。
    
    Attributes:
        task_id (str): 任务 ID
        instruction (str): 用户指令
        device_id (str): 设备 ID
        device_type (str): 设备类型 (固定为 "pc")
        status (PCTaskStatus): 任务状态
        steps (List[Dict]): 步骤记录
        result (str): 任务结果
        error (str): 错误信息
        created_at (datetime): 创建时间
        started_at (datetime): 开始时间
        completed_at (datetime): 完成时间
        total_tokens (int): 总 Token 数
        total_prompt_tokens (int): 总 Prompt Token 数
        total_completion_tokens (int): 总 Completion Token 数
        config (Dict): 配置信息
        agent: Agent 实例 (运行时)
    """
    
    task_id: str
    instruction: str
    device_id: str
    device_type: str = "pc"
    
    # 状态
    status: PCTaskStatus = PCTaskStatus.PENDING
    
    # 步骤记录 (与 PhoneAgent 格式一致)
    steps: List[Dict] = field(default_factory=list)
    
    # 结果
    result: Optional[str] = None
    error: Optional[str] = None
    
    # 时间
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Token 统计
    total_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    
    # 配置
    config: Dict = field(default_factory=dict)
    
    # Agent 实例 (运行时)
    agent: Optional[Any] = None
    
    def to_dict(self) -> Dict:
        """
        转换为字典 (API 返回)
        
        Returns:
            任务字典
        """
        return {
            "task_id": self.task_id,
            "instruction": self.instruction,
            "device_id": self.device_id,
            "device_type": self.device_type,
            "status": self.status.value,
            "steps": self.steps,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_tokens": self.total_tokens,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "config": self.config
        }
    
    @property
    def duration(self) -> Optional[float]:
        """
        任务执行时长 (秒)
        
        Returns:
            执行时长或 None
        """
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.now(timezone.utc)
        return (end_time - self.started_at).total_seconds()
    
    @property
    def step_count(self) -> int:
        """
        步骤数量
        
        Returns:
            步骤数量
        """
        return len(self.steps)
    
    @property
    def is_running(self) -> bool:
        """
        是否正在运行
        
        Returns:
            是否正在运行
        """
        return self.status == PCTaskStatus.RUNNING
    
    @property
    def is_finished(self) -> bool:
        """
        是否已结束
        
        Returns:
            是否已结束
        """
        return self.status in (
            PCTaskStatus.COMPLETED,
            PCTaskStatus.FAILED,
            PCTaskStatus.CANCELLED
        )
