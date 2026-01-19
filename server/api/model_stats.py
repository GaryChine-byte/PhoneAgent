#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
模型调用统计 API

提供模型使用情况、成本分析、性能统计等数据

性能优化:
- 异步数据库操作（asyncio.to_thread）
- 内存缓存（60秒TTL）
- 并发控制（信号量）
"""

from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta
import logging
import asyncio
from functools import lru_cache
import time

from server.database import crud, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/model-calls", tags=["Model Statistics"])

# 性能优化配置
CACHE_TTL = 60  # 缓存时间（秒）
MAX_CONCURRENT_QUERIES = 10  # 最大并发查询数

# 并发控制信号量
_query_semaphore = asyncio.Semaphore(MAX_CONCURRENT_QUERIES)

# 简单的内存缓存（带TTL）
_cache = {}
_cache_timestamps = {}


def _get_cache_key(endpoint: str, **kwargs) -> str:
    """生成缓存键"""
    params = "&".join(f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None)
    return f"{endpoint}?{params}"


def _get_cached(key: str):
    """获取缓存（如果未过期）"""
    if key in _cache:
        timestamp = _cache_timestamps.get(key, 0)
        if time.time() - timestamp < CACHE_TTL:
            logger.debug(f"Cache hit: {key}")
            return _cache[key]
        else:
            # 缓存过期，清理
            _cache.pop(key, None)
            _cache_timestamps.pop(key, None)
    return None


def _set_cache(key: str, value):
    """设置缓存"""
    _cache[key] = value
    _cache_timestamps[key] = time.time()
    logger.debug(f"💾 Cache set: {key}")


@router.get("/stats")
async def get_model_stats(
    days: int = Query(7, description="统计天数", ge=1, le=90),
    provider: Optional[str] = Query(None, description="提供商筛选"),
    kernel_mode: Optional[str] = Query(None, description="内核模式筛选")
):
    """
    获取模型调用统计（带缓存和并发控制）
    
    Args:
        days: 统计最近N天的数据（1-90天）
        provider: 按提供商筛选（可选）
        kernel_mode: 按内核模式筛选（可选）
    
    Returns:
        统计数据字典
    
    性能优化:
    - 60秒缓存
    - 异步数据库查询
    - 并发控制
    """
    # 检查缓存
    cache_key = _get_cache_key("stats", days=days, provider=provider, kernel_mode=kernel_mode)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    
    # 并发控制
    async with _query_semaphore:
        # 双重检查缓存（防止并发时重复查询）
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached
        
        # 异步执行数据库查询
        def _query():
            db = next(get_db())
            try:
                start_date = datetime.utcnow() - timedelta(days=days)
                return crud.get_model_call_stats(
                    db,
                    start_date=start_date,
                    provider=provider,
                    kernel_mode=kernel_mode
                )
            finally:
                db.close()
        
        try:
            stats = await asyncio.to_thread(_query)
            
            # 缓存结果
            _set_cache(cache_key, stats)
            
            logger.info(f"Model stats requested: {days} days, {stats['total_calls']} calls")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get model stats: {e}")
            raise


@router.get("/task/{task_id}")
async def get_task_model_calls(task_id: str):
    """
    获取任务的所有模型调用记录（异步优化）
    
    Args:
        task_id: 任务ID
    
    Returns:
        模型调用记录列表
    """
    # 并发控制
    async with _query_semaphore:
        # 异步执行数据库查询
        def _query():
            db = next(get_db())
            try:
                calls = crud.get_model_calls_by_task(db, task_id)
                
                # 转换为字典格式
                result = []
                for call in calls:
                    result.append({
                        "id": call.id,
                        "task_id": call.task_id,
                        "provider": call.provider,
                        "model_name": call.model_name,
                        "kernel_mode": call.kernel_mode,
                        "prompt_tokens": call.prompt_tokens,
                        "completion_tokens": call.completion_tokens,
                        "total_tokens": call.total_tokens,
                        "latency_ms": call.latency_ms,
                        "cost_usd": call.cost_usd,
                        "success": call.success,
                        "error_message": call.error_message,
                        "called_at": call.called_at.isoformat() if call.called_at else None
                    })
                return result
            finally:
                db.close()
        
        try:
            result = await asyncio.to_thread(_query)
            logger.info(f"Task model calls: {task_id}, {len(result)} calls")
            return result
        except Exception as e:
            logger.error(f"Failed to get task model calls: {e}")
            raise


@router.get("/history")
async def get_model_call_history(
    limit: int = Query(50, description="返回数量", ge=1, le=500),
    offset: int = Query(0, description="偏移量", ge=0)
):
    """
    获取模型调用历史记录（异步优化 + 缓存）
    
    Args:
        limit: 返回数量（1-500）
        offset: 偏移量
    
    Returns:
        历史记录列表
    """
    # 检查缓存（仅缓存第一页）
    cache_key = _get_cache_key("history", limit=limit, offset=offset)
    if offset == 0:  # 只缓存第一页
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached
    
    # 并发控制
    async with _query_semaphore:
        # 异步执行数据库查询
        def _query():
            from server.database.models import DBModelCall
            db = next(get_db())
            try:
                calls = db.query(DBModelCall).order_by(
                    DBModelCall.called_at.desc()
                ).offset(offset).limit(limit).all()
                
                result = []
                for call in calls:
                    result.append({
                        "id": call.id,
                        "task_id": call.task_id,
                        "provider": call.provider,
                        "model_name": call.model_name,
                        "kernel_mode": call.kernel_mode,
                        "total_tokens": call.total_tokens,
                        "latency_ms": call.latency_ms,
                        "cost_usd": call.cost_usd,
                        "success": call.success,
                        "called_at": call.called_at.isoformat() if call.called_at else None
                    })
                return result
            finally:
                db.close()
        
        try:
            result = await asyncio.to_thread(_query)
            
            # 缓存第一页结果
            if offset == 0:
                _set_cache(cache_key, result)
            
                logger.info(f"Model call history: {len(result)} records")
                return result
        except Exception as e:
            logger.error(f"Failed to get model call history: {e}")
            raise

