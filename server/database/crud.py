#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
数据库 CRUD 操作
"""

from sqlalchemy.orm import Session
from server.database.models import DBTask, DBDevice, DBModelCall
from typing import List, Optional
from datetime import datetime
import json


# ========== Task CRUD ==========

def create_task(db: Session, task_id: str, instruction: str, **kwargs) -> DBTask:
    """创建任务"""
    db_task = DBTask(
        task_id=task_id,
        instruction=instruction,
        device_id=kwargs.get("device_id"),
        model_config=json.dumps(kwargs.get("model_config", {})) if kwargs.get("model_config") else None,
        created_at=datetime.utcnow()
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_task(db: Session, task_id: str) -> Optional[DBTask]:
    """获取任务"""
    return db.query(DBTask).filter(DBTask.task_id == task_id).first()


def list_tasks(
    db: Session,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[DBTask]:
    """获取任务列表"""
    query = db.query(DBTask)
    if status:
        query = query.filter(DBTask.status == status)
    return query.order_by(DBTask.created_at.desc()).offset(offset).limit(limit).all()


def update_task(db: Session, task_id: str, **updates):
    """更新任务"""
    # 处理 datetime 对象
    for key, value in updates.items():
        if isinstance(value, datetime):
            updates[key] = value
    
    db.query(DBTask).filter(DBTask.task_id == task_id).update(updates)
    db.commit()


def delete_task(db: Session, task_id: str) -> bool:
    """删除单个任务"""
    count = db.query(DBTask).filter(DBTask.task_id == task_id).delete()
    db.commit()
    return count > 0


def delete_tasks_batch(db: Session, task_ids: List[str]) -> int:
    """批量删除任务"""
    count = db.query(DBTask).filter(DBTask.task_id.in_(task_ids)).delete(synchronize_session=False)
    db.commit()
    return count


def delete_old_tasks(db: Session, days: int = 30) -> int:
    """删除旧任务（可选的清理功能）"""
    from datetime import timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    count = db.query(DBTask).filter(DBTask.created_at < cutoff_date).delete()
    db.commit()
    return count


# ========== Device CRUD ==========

def upsert_device(db: Session, device_id: str, **data) -> DBDevice:
    """插入或更新设备"""
    device = db.query(DBDevice).filter(DBDevice.device_id == device_id).first()
    
    if device:
        # 更新现有设备
        for key, value in data.items():
            if hasattr(device, key):
                setattr(device, key, value)
    else:
        # 插入新设备
        device = DBDevice(device_id=device_id, **data)
        db.add(device)
    
    db.commit()
    db.refresh(device)
    return device


def get_device(db: Session, device_id: str) -> Optional[DBDevice]:
    """获取设备"""
    return db.query(DBDevice).filter(DBDevice.device_id == device_id).first()


def list_devices(db: Session, status: Optional[str] = None) -> List[DBDevice]:
    """获取设备列表"""
    query = db.query(DBDevice)
    if status:
        query = query.filter(DBDevice.status == status)
    return query.order_by(DBDevice.registered_at.desc()).all()


def update_device(db: Session, device_id: str, **updates):
    """更新设备"""
    db.query(DBDevice).filter(DBDevice.device_id == device_id).update(updates)
    db.commit()


def update_device_stats(db: Session, device_id: str, success: bool):
    """更新设备统计"""
    device = get_device(db, device_id)
    if device:
        device.total_tasks += 1
        if success:
            device.success_tasks += 1
        else:
            device.failed_tasks += 1
        device.last_active = datetime.utcnow()
        db.commit()


# ========== 模型调用统计 CRUD ==========

def create_model_call(
    db: Session,
    task_id: str,
    provider: str,
    model_name: str,
    kernel_mode: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
    cost_usd: float = 0.0,
    success: bool = True,
    error_message: Optional[str] = None
) -> DBModelCall:
    """记录模型调用"""
    model_call = DBModelCall(
        task_id=task_id,
        provider=provider,
        model_name=model_name,
        kernel_mode=kernel_mode,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        success=success,
        error_message=error_message,
        called_at=datetime.utcnow()
    )
    db.add(model_call)
    db.commit()
    db.refresh(model_call)
    return model_call


def get_model_calls_by_task(db: Session, task_id: str) -> List[DBModelCall]:
    """获取任务的所有模型调用记录"""
    return db.query(DBModelCall).filter(DBModelCall.task_id == task_id).all()


def get_model_call_stats(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    provider: Optional[str] = None,
    kernel_mode: Optional[str] = None
) -> dict:
    """获取模型调用统计"""
    query = db.query(DBModelCall)
    
    if start_date:
        query = query.filter(DBModelCall.called_at >= start_date)
    if end_date:
        query = query.filter(DBModelCall.called_at <= end_date)
    if provider:
        query = query.filter(DBModelCall.provider == provider)
    if kernel_mode:
        query = query.filter(DBModelCall.kernel_mode == kernel_mode)
    
    calls = query.all()
    
    if not calls:
        return {
            "total_calls": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "avg_latency_ms": 0,
            "success_rate": 0.0
        }
    
    total_calls = len(calls)
    total_tokens = sum(c.total_tokens for c in calls)
    total_cost = sum(c.cost_usd for c in calls)
    avg_latency = sum(c.latency_ms for c in calls if c.latency_ms) / total_calls if total_calls > 0 else 0
    success_count = sum(1 for c in calls if c.success)
    
    return {
        "total_calls": total_calls,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "avg_latency_ms": int(avg_latency),
        "success_rate": round(success_count / total_calls * 100, 2) if total_calls > 0 else 0.0,
        "by_provider": _group_by_provider(calls),
        "by_kernel": _group_by_kernel(calls)
    }


def _group_by_provider(calls: List[DBModelCall]) -> dict:
    """按提供商分组统计"""
    from collections import defaultdict
    stats = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost": 0.0})
    
    for call in calls:
        stats[call.provider]["calls"] += 1
        stats[call.provider]["tokens"] += call.total_tokens
        stats[call.provider]["cost"] += call.cost_usd
    
    return dict(stats)


def _group_by_kernel(calls: List[DBModelCall]) -> dict:
    """按内核模式分组统计"""
    from collections import defaultdict
    stats = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost": 0.0})
    
    for call in calls:
        stats[call.kernel_mode]["calls"] += 1
        stats[call.kernel_mode]["tokens"] += call.total_tokens
        stats[call.kernel_mode]["cost"] += call.cost_usd
    
    return dict(stats)


def delete_old_model_calls(db: Session, days: int = 90) -> int:
    """删除旧的模型调用记录"""
    from datetime import timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    count = db.query(DBModelCall).filter(DBModelCall.called_at < cutoff_date).delete()
    db.commit()
    return count
