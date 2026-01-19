#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
截图数据模型

定义截图系统的数据结构
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class StepScreenshot(BaseModel):
    """单步截图信息"""
    task_id: str
    device_id: str
    step_number: int
    timestamp: datetime
    
    # 文件路径（相对于data/screenshots/）
    original_path: str
    thumbnail_path: Optional[str] = None
    
    # 动作信息
    action: Dict[str, Any]          # 执行的动作（JSON）
    thinking: Optional[str] = None  # 推理过程
    observation: str                # 执行结果
    success: bool
    
    # Token信息
    tokens_used: Optional[Dict[str, int]] = None
    
    # 内核信息
    kernel_mode: str                # xml/vision/auto
    
    # 文件信息（用于跨平台传递）
    file_hash: Optional[str] = None  # SHA256
    file_size: int = 0               # 字节


class TaskScreenshotSummary(BaseModel):
    """任务截图摘要"""
    task_id: str
    device_id: str
    instruction: str
    
    # 时间信息
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 状态信息
    status: str                     # pending/running/completed/failed/cancelled
    total_steps: int
    success: bool
    
    # Token统计
    total_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    
    # 结果
    result: Optional[str] = None
    error: Optional[str] = None
    
    # 文件信息
    screenshots_dir: str            # 相对路径
    total_size: int = 0             # 总大小（字节）
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
