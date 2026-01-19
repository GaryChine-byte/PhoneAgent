#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
数据库初始化脚本

创建包含手机和PC的完整数据库。
"""

import logging
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_database(db_path: str = "data/agent.db"):
    """
    创建新数据库
    
    Args:
        db_path: 数据库文件路径
    """
    # 确保目录存在
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 如果数据库已存在，备份
    if db_file.exists():
        backup_path = db_file.parent / f"agent_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        logger.info(f"备份现有数据库到: {backup_path}")
        import shutil
        shutil.copy2(db_file, backup_path)
    
    # 创建数据库引擎
    engine = create_engine(f"sqlite:///{db_path}")
    
    with engine.connect() as conn:
        logger.info("开始创建数据库表...")
        
        # ==================== 手机任务表 ====================
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id VARCHAR(36) PRIMARY KEY,
                instruction TEXT NOT NULL,
                device_id VARCHAR(50),
                status VARCHAR(20) DEFAULT 'pending',
                created_at DATETIME,
                started_at DATETIME,
                completed_at DATETIME,
                result TEXT,
                error TEXT,
                steps_count INTEGER DEFAULT 0,
                steps_detail TEXT,
                total_tokens INTEGER DEFAULT 0,
                total_prompt_tokens INTEGER DEFAULT 0,
                total_completion_tokens INTEGER DEFAULT 0,
                model_config TEXT,
                important_content TEXT,
                todos TEXT
            )
        """))
        logger.info("✅ 表 tasks (手机任务) 创建成功")
        
        # ==================== 手机设备表 ====================
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id VARCHAR(50) PRIMARY KEY,
                device_name VARCHAR(100) NOT NULL,
                frp_port INTEGER,
                adb_address VARCHAR(50),
                model VARCHAR(50),
                android_version VARCHAR(20),
                screen_resolution VARCHAR(20),
                battery INTEGER,
                status VARCHAR(20) DEFAULT 'offline',
                frp_connected BOOLEAN DEFAULT 0,
                ws_connected BOOLEAN DEFAULT 0,
                registered_at DATETIME,
                last_active DATETIME,
                total_tasks INTEGER DEFAULT 0,
                success_tasks INTEGER DEFAULT 0,
                failed_tasks INTEGER DEFAULT 0,
                current_task_id VARCHAR(36),
                is_busy BOOLEAN DEFAULT 0,
                last_error TEXT,
                uptime_seconds INTEGER DEFAULT 0
            )
        """))
        logger.info("✅ 表 devices (手机设备) 创建成功")
        
        # ==================== PC 任务表 ====================
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pc_tasks (
                task_id VARCHAR(36) PRIMARY KEY,
                instruction TEXT NOT NULL,
                device_id VARCHAR(50),
                status VARCHAR(20) DEFAULT 'pending',
                created_at DATETIME,
                started_at DATETIME,
                completed_at DATETIME,
                result TEXT,
                error TEXT,
                steps_count INTEGER DEFAULT 0,
                steps_detail TEXT,
                total_tokens INTEGER DEFAULT 0,
                total_prompt_tokens INTEGER DEFAULT 0,
                total_completion_tokens INTEGER DEFAULT 0,
                model_config TEXT
            )
        """))
        logger.info("✅ 表 pc_tasks (PC任务) 创建成功")
        
        # ==================== PC 设备表 ====================
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pc_devices (
                device_id VARCHAR(50) PRIMARY KEY,
                device_name VARCHAR(100) NOT NULL,
                frp_port INTEGER,
                os_system VARCHAR(20),
                os_release VARCHAR(50),
                os_machine VARCHAR(50),
                status VARCHAR(20) DEFAULT 'offline',
                frp_connected BOOLEAN DEFAULT 0,
                ws_connected BOOLEAN DEFAULT 0,
                registered_at DATETIME,
                last_active DATETIME,
                total_tasks INTEGER DEFAULT 0,
                success_tasks INTEGER DEFAULT 0,
                failed_tasks INTEGER DEFAULT 0,
                current_task_id VARCHAR(36),
                is_busy BOOLEAN DEFAULT 0,
                last_error TEXT
            )
        """))
        logger.info("✅ 表 pc_devices (PC设备) 创建成功")
        
        # ==================== 模型调用统计表 ====================
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS model_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id VARCHAR(36) NOT NULL,
                provider VARCHAR(50),
                model_name VARCHAR(100),
                kernel_mode VARCHAR(20),
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                latency_ms INTEGER,
                cost_usd REAL DEFAULT 0.0,
                called_at DATETIME,
                success BOOLEAN DEFAULT 1,
                error_message TEXT
            )
        """))
        logger.info("✅ 表 model_calls (模型调用统计) 创建成功")
        
        # ==================== 创建索引 ====================
        logger.info("创建索引...")
        
        # 手机任务索引
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_task_status ON tasks(status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_task_device ON tasks(device_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_task_created ON tasks(created_at DESC)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_task_status_created ON tasks(status, created_at DESC)"))
        
        # 手机设备索引
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_device_status ON devices(status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_device_active ON devices(last_active DESC)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_device_busy ON devices(is_busy)"))
        
        # PC 任务索引
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pc_task_status ON pc_tasks(status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pc_task_device ON pc_tasks(device_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pc_task_created ON pc_tasks(created_at DESC)"))
        
        # PC 设备索引
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pc_device_status ON pc_devices(status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pc_device_active ON pc_devices(last_active DESC)"))
        
        # 模型调用索引
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_model_call_task ON model_calls(task_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_model_call_time ON model_calls(called_at DESC)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_model_call_provider ON model_calls(provider, model_name)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_model_call_kernel ON model_calls(kernel_mode)"))
        
        logger.info("✅ 索引创建成功")
        
        # ==================== 启用 WAL 模式 ====================
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA synchronous=NORMAL"))
        conn.execute(text("PRAGMA cache_size=-64000"))
        conn.execute(text("PRAGMA temp_store=MEMORY"))
        conn.execute(text("PRAGMA mmap_size=268435456"))
        
        logger.info("✅ WAL 模式已启用")
        
        conn.commit()
    
    logger.info(f"✅ 数据库创建成功: {db_path}")
    logger.info("\n数据库表:")
    logger.info("  - tasks (手机任务)")
    logger.info("  - devices (手机设备)")
    logger.info("  - pc_tasks (PC任务)")
    logger.info("  - pc_devices (PC设备)")
    logger.info("  - model_calls (模型调用统计)")


def verify_database(db_path: str = "data/agent.db"):
    """
    验证数据库
    
    Args:
        db_path: 数据库文件路径
    """
    engine = create_engine(f"sqlite:///{db_path}")
    
    with engine.connect() as conn:
        # 获取所有表
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ))
        tables = [row[0] for row in result]
        
        logger.info("\n数据库验证:")
        logger.info(f"找到 {len(tables)} 个表:")
        for table in tables:
            # 获取表的行数
            count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = count_result.fetchone()[0]
            logger.info(f"  ✅ {table} ({count} 行)")


if __name__ == "__main__":
    """直接运行此脚本创建数据库"""
    import sys
    
    # 设置 UTF-8 编码
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    db_path = "data/agent.db"
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    print("=" * 60)
    print("PhoneAgent-Enterprise 数据库初始化")
    print("=" * 60)
    print(f"\n数据库路径: {db_path}")
    print("\n警告: 如果数据库已存在，将自动备份")
    
    response = input("\n是否继续? (y/n): ")
    
    if response.lower() == 'y':
        create_database(db_path)
        verify_database(db_path)
        print("\n数据库初始化完成!")
    else:
        print("\n操作已取消")
