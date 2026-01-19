#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
设备初始化模块

在设备首次连接或重新连接时执行初始化任务：
- 推送 yadb 工具
- 设置屏幕常亮（可选）
- 其他初始化操作
"""

import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)


async def initialize_device(
    device_id: str,
    adb_host: str = "localhost",
    adb_port: int = None,
    check_yadb: bool = True,
    **kwargs
) -> bool:
    """
    初始化设备（异步）
    
    [WARN] 注意: yadb 应该由 Android app (PhoneAgent Remote) 预装
    此函数只负责检查 yadb 是否可用，不尝试推送安装
    
    Args:
        device_id: 设备 ID (如 device_6100)
        adb_host: ADB 服务器地址（FRP 隧道）
        adb_port: ADB 服务器端口（FRP 端口）
        check_yadb: 是否检查 yadb 工具（不推送，只检查）
        **kwargs: 其他初始化选项
    
    Returns:
        True if initialization successful, False otherwise
    """
    logger.info(f" Initializing device {device_id}...")
    
    success = True
    
    # 1. 检查 yadb 工具（不推送安装）
    if check_yadb:
        yadb_success = await _init_yadb(device_id, adb_host, adb_port)
        if yadb_success:
            logger.info(f"  [OK] yadb ready on {device_id}")
        else:
            logger.info(f"  ℹ️  yadb not found on {device_id} (will be installed by Android app)")
            # [OK] 不标记为失败，因为 yadb 会由 Android app 预装
            # success = False  # 注释掉，不影响初始化结果
    
    # 2. 其他初始化任务（未来扩展）
    # - 设置屏幕常亮
    # - 禁用自动锁屏
    # - 设置系统语言
    
    if success:
        logger.info(f"[OK] Device {device_id} initialized successfully")
    else:
        logger.warning(f"[WARN]  Device {device_id} initialization completed with warnings")
    
    return success


async def _init_yadb(device_id: str, adb_host: str, adb_port: int) -> bool:
    """
    检查 yadb 是否可用（在线程中执行以避免阻塞）
    
    [WARN] 注意: yadb 应该由 Android app (PhoneAgent Remote) 预装
    服务器端只负责检查 yadb 是否存在，不尝试推送安装
    
    Args:
        device_id: 设备 ID
        adb_host: ADB 服务器地址
        adb_port: ADB 服务器端口
    
    Returns:
        True if yadb is ready, False otherwise
    """
    try:
        from phone_agent.adb import yadb
        
        # 在线程中执行（避免阻塞事件循环）
        # [OK] 只检查，不尝试安装（skip_install=True）
        result = await asyncio.to_thread(
            yadb.ensure_yadb_ready,
            device_id=device_id,
            adb_host=adb_host,
            adb_port=adb_port,
            skip_install=True  # 不尝试推送安装，避免超时
        )
        
        return result
        
    except ImportError:
        logger.error("yadb module not available")
        return False
    except Exception as e:
        logger.error(f"Failed to check yadb: {e}")
        return False


def initialize_device_sync(
    device_id: str,
    adb_host: str = "localhost",
    adb_port: int = None,
    check_yadb: bool = True,
    **kwargs
) -> bool:
    """
    初始化设备（同步版本，用于非异步环境）
    
    [WARN] 注意: yadb 应该由 Android app (PhoneAgent Remote) 预装
    此函数只负责检查 yadb 是否可用，不尝试推送安装
    
    Args:
        device_id: 设备 ID
        adb_host: ADB 服务器地址
        adb_port: ADB 服务器端口
        check_yadb: 是否检查 yadb 工具（不推送，只检查）
        **kwargs: 其他初始化选项
    
    Returns:
        True if initialization successful, False otherwise
    """
    logger.info(f" Initializing device {device_id} (sync mode)...")
    
    success = True
    
    # 1. 检查 yadb 工具（不推送安装）
    if check_yadb:
        try:
            from phone_agent.adb import yadb
            
            # [OK] 只检查，不尝试安装（skip_install=True）
            yadb_success = yadb.ensure_yadb_ready(
                device_id=device_id,
                adb_host=adb_host,
                adb_port=adb_port,
                skip_install=True  # 不尝试推送安装，避免超时
            )
            
            if yadb_success:
                logger.info(f"  [OK] yadb ready on {device_id}")
            else:
                logger.info(f"  ℹ️  yadb not found on {device_id} (will be installed by Android app)")
                # [OK] 不标记为失败，因为 yadb 会由 Android app 预装
                # success = False  # 注释掉，不影响初始化结果
                
        except ImportError:
            logger.error("yadb module not available")
            success = False
        except Exception as e:
            logger.error(f"Failed to check yadb: {e}")
            success = False
    
    if success:
        logger.info(f"[OK] Device {device_id} initialized successfully")
    else:
        logger.warning(f"[WARN]  Device {device_id} initialization completed with warnings")
    
    return success

