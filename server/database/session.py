#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
数据库会话管理
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from pathlib import Path
import logging

from server.database.models import Base

logger = logging.getLogger(__name__)

# 数据库文件路径
DATABASE_PATH = Path("data/agent.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# 全局引擎和会话工厂
engine = None
SessionLocal = None


def init_database():
    """初始化数据库"""
    global engine, SessionLocal
    
    # 如果已经初始化，直接返回
    if engine is not None and SessionLocal is not None:
        logger.debug("Database already initialized, skipping...")
        return
    
    # 确保目录存在
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # 优化: 启用WAL模式和性能优化
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={
            "check_same_thread": False,  # SQLite需要这个参数
            "timeout": 30,  # 锁超时30秒（支持高并发）
        },
        pool_size=20,  # 连接池大小
        max_overflow=10,  # 最大溢出连接
        pool_pre_ping=True,  # 连接前检查
        pool_recycle=3600,  # 1小时回收连接
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    # 优化: 启用WAL模式和性能PRAGMA
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL;"))  # WAL模式（并发读写）
        conn.execute(text("PRAGMA synchronous=NORMAL;"))  # 平衡性能和安全
        conn.execute(text("PRAGMA cache_size=-64000;"))  # 64MB缓存
        conn.execute(text("PRAGMA temp_store=MEMORY;"))  # 临时表在内存
        conn.execute(text("PRAGMA mmap_size=268435456;"))  # 256MB内存映射
        conn.commit()
    
        logger.info(f" Database initialized (WAL mode): {DATABASE_PATH.absolute()}")     
 # 创建性能优化索引     _create_indexes(engine)


def _create_indexes(engine):
    """创建性能优化索引"""
    indexes = [
        # 任务表索引
        ("idx_task_status", "CREATE INDEX IF NOT EXISTS idx_task_status ON tasks(status);"),
        ("idx_task_device", "CREATE INDEX IF NOT EXISTS idx_task_device ON tasks(device_id);"),
        ("idx_task_created", "CREATE INDEX IF NOT EXISTS idx_task_created ON tasks(created_at DESC);"),
        ("idx_task_status_created", "CREATE INDEX IF NOT EXISTS idx_task_status_created ON tasks(status, created_at DESC);"),
        
        # 设备表索引
        ("idx_device_status", "CREATE INDEX IF NOT EXISTS idx_device_status ON devices(status);"),
        ("idx_device_active", "CREATE INDEX IF NOT EXISTS idx_device_active ON devices(last_active DESC);"),
        ("idx_device_busy", "CREATE INDEX IF NOT EXISTS idx_device_busy ON devices(is_busy);"),
        
        # 模型调用统计表索引
        ("idx_model_call_task", "CREATE INDEX IF NOT EXISTS idx_model_call_task ON model_calls(task_id);"),
        ("idx_model_call_time", "CREATE INDEX IF NOT EXISTS idx_model_call_time ON model_calls(called_at DESC);"),
        ("idx_model_call_provider", "CREATE INDEX IF NOT EXISTS idx_model_call_provider ON model_calls(provider, model_name);"),
        ("idx_model_call_kernel", "CREATE INDEX IF NOT EXISTS idx_model_call_kernel ON model_calls(kernel_mode);"),
    ]
    
    created_count = 0
    failed_count = 0
    
    with engine.connect() as conn:
        for index_name, sql in indexes:
            try:
                conn.execute(text(sql))
                created_count += 1
            except Exception as e:
                # 如果是列不存在的错误，记录警告而不是错误
                if "no such column" in str(e):
                    logger.warning(f"Index {index_name} skipped: column not found (database schema may be outdated)")
                else:
                    logger.error(f"Failed to create index {index_name}: {e}")
                    failed_count += 1
        
        conn.commit()
    
    if failed_count == 0:
        logger.info(f"Database indexes created ({created_count}/{len(indexes)})")
    else:
        logger.warning(f"Database indexes partially created ({created_count}/{len(indexes)}, {failed_count} failed)") 
def get_db() -> Session:
    """
    获取数据库会话（用于依赖注入）
    
    使用方法:
        db = next(get_db())
        try:
            # 数据库操作
            pass
        finally:
            db.close()
    """
    if SessionLocal is None:
        init_database()
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """
    直接获取数据库会话（同步方式）
    
    使用方法:
        with get_db_session() as db:
            # 数据库操作
            pass
    """
    if SessionLocal is None:
        init_database()
    
    return SessionLocal()

