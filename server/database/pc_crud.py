#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
PC 任务数据库操作 (独立)

专门用于 PC 任务的 CRUD 操作,完全独立于手机任务。
"""

import json
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from .models import DBPCTask, DBPCDevice

logger = logging.getLogger(__name__)


# ==================== PC 任务操作 ====================

def create_pc_task(
    db: Session,
    task_id: str,
    instruction: str,
    device_id: str,
    status: str = "pending",
    **kwargs
) -> DBPCTask:
    """
    创建 PC 任务
    
    Args:
        db: 数据库会话
        task_id: 任务 ID
        instruction: 用户指令
        device_id: 设备 ID
        status: 任务状态
        **kwargs: 其他字段
        
    Returns:
        DBPCTask 实例
    """
    task = DBPCTask(
        task_id=task_id,
        instruction=instruction,
        device_id=device_id,
        status=status,
        created_at=kwargs.get("created_at", datetime.utcnow()),
        **{k: v for k, v in kwargs.items() if k != "created_at"}
    )
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    logger.info(f"PC 任务已创建: {task_id}")
    return task


def update_pc_task(
    db: Session,
    task_id: str,
    **kwargs
) -> Optional[DBPCTask]:
    """
    更新 PC 任务
    
    Args:
        db: 数据库会话
        task_id: 任务 ID
        **kwargs: 要更新的字段
        
    Returns:
        更新后的 DBPCTask 实例或 None
    """
    task = db.query(DBPCTask).filter(DBPCTask.task_id == task_id).first()
    
    if not task:
        logger.warning(f"PC 任务不存在: {task_id}")
        return None
    
    for key, value in kwargs.items():
        if hasattr(task, key):
            setattr(task, key, value)
    
    db.commit()
    db.refresh(task)
    
    logger.info(f"PC 任务已更新: {task_id}")
    return task


def get_pc_task(db: Session, task_id: str) -> Optional[DBPCTask]:
    """
    获取 PC 任务
    
    Args:
        db: 数据库会话
        task_id: 任务 ID
        
    Returns:
        DBPCTask 实例或 None
    """
    return db.query(DBPCTask).filter(DBPCTask.task_id == task_id).first()


def list_pc_tasks(
    db: Session,
    device_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[DBPCTask]:
    """
    列出 PC 任务
    
    Args:
        db: 数据库会话
        device_id: 设备 ID (可选)
        status: 任务状态 (可选)
        limit: 返回数量限制
        offset: 偏移量
        
    Returns:
        DBPCTask 列表
    """
    query = db.query(DBPCTask)
    
    if device_id:
        query = query.filter(DBPCTask.device_id == device_id)
    
    if status:
        query = query.filter(DBPCTask.status == status)
    
    query = query.order_by(DBPCTask.created_at.desc())
    query = query.limit(limit).offset(offset)
    
    return query.all()


def delete_pc_task(db: Session, task_id: str) -> bool:
    """
    删除 PC 任务
    
    Args:
        db: 数据库会话
        task_id: 任务 ID
        
    Returns:
        是否成功删除
    """
    task = db.query(DBPCTask).filter(DBPCTask.task_id == task_id).first()
    
    if not task:
        return False
    
    db.delete(task)
    db.commit()
    
    logger.info(f"PC 任务已删除: {task_id}")
    return True


# ==================== PC 设备操作 ====================

def create_or_update_pc_device(
    db: Session,
    device_id: str,
    device_name: str,
    **kwargs
) -> DBPCDevice:
    """
    创建或更新 PC 设备
    
    Args:
        db: 数据库会话
        device_id: 设备 ID
        device_name: 设备名称
        **kwargs: 其他字段
        
    Returns:
        DBPCDevice 实例
    """
    device = db.query(DBPCDevice).filter(DBPCDevice.device_id == device_id).first()
    
    if device:
        # 更新
        device.device_name = device_name
        device.last_active = datetime.utcnow()
        
        for key, value in kwargs.items():
            if hasattr(device, key):
                setattr(device, key, value)
        
        logger.info(f"PC 设备已更新: {device_id}")
    else:
        # 创建
        device = DBPCDevice(
            device_id=device_id,
            device_name=device_name,
            registered_at=datetime.utcnow(),
            last_active=datetime.utcnow(),
            **kwargs
        )
        db.add(device)
        logger.info(f"PC 设备已创建: {device_id}")
    
    db.commit()
    db.refresh(device)
    
    return device


def get_pc_device(db: Session, device_id: str) -> Optional[DBPCDevice]:
    """
    获取 PC 设备
    
    Args:
        db: 数据库会话
        device_id: 设备 ID
        
    Returns:
        DBPCDevice 实例或 None
    """
    return db.query(DBPCDevice).filter(DBPCDevice.device_id == device_id).first()


def list_pc_devices(
    db: Session,
    status: Optional[str] = None,
    limit: int = 100
) -> List[DBPCDevice]:
    """
    列出 PC 设备
    
    Args:
        db: 数据库会话
        status: 设备状态 (可选)
        limit: 返回数量限制
        
    Returns:
        DBPCDevice 列表
    """
    query = db.query(DBPCDevice)
    
    if status:
        query = query.filter(DBPCDevice.status == status)
    
    query = query.order_by(DBPCDevice.last_active.desc())
    query = query.limit(limit)
    
    return query.all()


def update_pc_device_status(
    db: Session,
    device_id: str,
    status: str,
    **kwargs
) -> Optional[DBPCDevice]:
    """
    更新 PC 设备状态
    
    Args:
        db: 数据库会话
        device_id: 设备 ID
        status: 设备状态
        **kwargs: 其他字段
        
    Returns:
        更新后的 DBPCDevice 实例或 None
    """
    device = db.query(DBPCDevice).filter(DBPCDevice.device_id == device_id).first()
    
    if not device:
        return None
    
    device.status = status
    device.last_active = datetime.utcnow()
    
    for key, value in kwargs.items():
        if hasattr(device, key):
            setattr(device, key, value)
    
    db.commit()
    db.refresh(device)
    
    return device
