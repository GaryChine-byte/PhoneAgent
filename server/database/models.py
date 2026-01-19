#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
SQLAlchemy 数据库模型
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class DBTask(Base):
    """任务表 (手机)"""
    __tablename__ = "tasks"
    
    task_id = Column(String(36), primary_key=True)
    instruction = Column(Text, nullable=False)
    device_id = Column(String(50))
    status = Column(String(20), default="pending")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    result = Column(Text)
    error = Column(Text)
    steps_count = Column(Integer, default=0)  # 步骤总数
    steps_detail = Column(Text)  # JSON string: 存储每一步的详细信息
    
    # Token统计
    total_tokens = Column(Integer, default=0)
    total_prompt_tokens = Column(Integer, default=0)
    total_completion_tokens = Column(Integer, default=0)
    
    model_config = Column(Text)  # JSON string
    
    # Phase 1: 高级特性
    important_content = Column(Text)  # JSON string: 记录的重要内容列表
    todos = Column(Text)  # Markdown格式的TODO列表


class DBDevice(Base):
    """设备表"""
    __tablename__ = "devices"
    
    device_id = Column(String(50), primary_key=True)
    device_name = Column(String(100), nullable=False)
    frp_port = Column(Integer)
    adb_address = Column(String(50))
    
    model = Column(String(50))
    android_version = Column(String(20))
    screen_resolution = Column(String(20))
    battery = Column(Integer)
    
    status = Column(String(20), default="offline")
    frp_connected = Column(Boolean, default=False)
    ws_connected = Column(Boolean, default=False)
    
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime)
    
    total_tasks = Column(Integer, default=0)
    success_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    
    # 新增: 实时状态字段
    current_task_id = Column(String(36))  # 当前执行的任务ID
    is_busy = Column(Boolean, default=False)  # 是否忙碌
    last_error = Column(Text)  # 最后一次错误
    uptime_seconds = Column(Integer, default=0)  # 在线时长（秒）


class DBPCTask(Base):
    """PC 任务表 (独立)"""
    __tablename__ = "pc_tasks"
    
    task_id = Column(String(36), primary_key=True)
    instruction = Column(Text, nullable=False)
    device_id = Column(String(50))
    status = Column(String(20), default="pending")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    result = Column(Text)
    error = Column(Text)
    steps_count = Column(Integer, default=0)
    steps_detail = Column(Text)  # JSON string
    
    # Token统计
    total_tokens = Column(Integer, default=0)
    total_prompt_tokens = Column(Integer, default=0)
    total_completion_tokens = Column(Integer, default=0)
    
    model_config = Column(Text)  # JSON string


class DBPCDevice(Base):
    """PC 设备表 (独立)"""
    __tablename__ = "pc_devices"
    
    device_id = Column(String(50), primary_key=True)
    device_name = Column(String(100), nullable=False)
    frp_port = Column(Integer)
    
    # 系统信息
    os_system = Column(String(20))  # Windows/Darwin
    os_release = Column(String(50))
    os_machine = Column(String(50))
    
    status = Column(String(20), default="offline")
    frp_connected = Column(Boolean, default=False)
    ws_connected = Column(Boolean, default=False)
    
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime)
    
    total_tasks = Column(Integer, default=0)
    success_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    
    current_task_id = Column(String(36))
    is_busy = Column(Boolean, default=False)
    last_error = Column(Text)


class DBModelCall(Base):
    """模型调用统计表"""
    __tablename__ = "model_calls"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(36), nullable=False)  # 关联任务
    
    # 模型信息
    provider = Column(String(50))  # 提供商: openai, zhipu, deepseek等
    model_name = Column(String(100))  # 模型名称
    kernel_mode = Column(String(20))  # 内核模式: xml, vision, auto
    
    # Token统计
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # 性能统计
    latency_ms = Column(Integer)  # 延迟（毫秒）
    cost_usd = Column(Float, default=0.0)  # 成本（美元）
    
    # 时间戳
    called_at = Column(DateTime, default=datetime.utcnow)
    
    # 额外信息
    success = Column(Boolean, default=True)
    error_message = Column(Text)


