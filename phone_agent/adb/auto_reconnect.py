#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
ADB 设备自动重连模块

用于网络 ADB 连接（localhost:port）的自动重连
解决 Remote App 后台时连接断开的问题
"""

import subprocess
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 连接缓存（避免频繁检查）
_connection_cache = {}
_cache_ttl = 5  # 缓存有效期5秒（从30秒缩短，快速检测连接变化）


def ensure_device_connected(device_id: Optional[str], force_check: bool = False) -> None:
    """
    确保设备已连接，如果未连接则自动重连
    
    Args:
        device_id: 设备ID (例如: "localhost:6104")
        force_check: 是否强制检查（忽略缓存）
    
    Raises:
        RuntimeError: 如果重连失败
    """
    if not device_id or ":" not in device_id:
        return  # USB 设备不需要重连
    
    current_time = time.time()
    
    # 检查缓存
    if not force_check and device_id in _connection_cache:
        last_check_time = _connection_cache[device_id]
        if current_time - last_check_time < _cache_ttl:
            return  # 缓存有效，跳过检查
    
    # 检查设备是否在线
    if _is_device_online(device_id):
        _connection_cache[device_id] = current_time
        return  # 设备在线，无需重连
    
    # 设备不在线，尝试重连
    logger.warning(f"[WARN] 设备 {device_id} 不在线，自动重连中...")
    
    if _reconnect_device(device_id):
        _connection_cache[device_id] = current_time
        logger.info(f"[OK] 设备 {device_id} 重连成功")
    else:
        # 清除缓存
        _connection_cache.pop(device_id, None)
        raise RuntimeError(f"Failed to reconnect device: {device_id}")


def _is_device_online(device_id: str) -> bool:
    """检查设备是否在线"""
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return False
        
        # 解析输出
        lines = result.stdout.strip().split('\n')
        for line in lines[1:]:  # 跳过标题行
            if not line.strip():
                continue
            
            parts = line.split()
            if len(parts) >= 2:
                device = parts[0]
                status = parts[1]
                
                if device == device_id and status == "device":
                    return True
        
        return False
        
    except Exception as e:
        logger.debug(f"检查设备状态失败: {e}")
        return False


def _reconnect_device(device_id: str, max_attempts: int = 2) -> bool:
    """重新连接设备"""
    for attempt in range(1, max_attempts + 1):
        try:
            # 1. 断开旧连接
            subprocess.run(
                ["adb", "disconnect", device_id],
                capture_output=True,
                timeout=5
            )
            time.sleep(0.5)
            
            # 2. 重新连接
            result = subprocess.run(
                ["adb", "connect", device_id],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            output = result.stdout.lower()
            if "connected" in output or "already connected" in output:
                # 等待连接稳定
                time.sleep(1.5)
                
                # 验证连接
                if _is_device_online(device_id):
                    return True
                else:
                    logger.warning(f"连接命令成功但设备未上线 (尝试 {attempt}/{max_attempts})")
            else:
                logger.warning(f"连接失败: {result.stdout} (尝试 {attempt}/{max_attempts})")
            
        except Exception as e:
            logger.warning(f"重连异常: {e} (尝试 {attempt}/{max_attempts})")
        
        if attempt < max_attempts:
            time.sleep(1)  # 重试前等待
    
    return False


def clear_connection_cache():
    """清除连接缓存（用于测试或强制刷新）"""
    _connection_cache.clear()
    logger.debug("连接缓存已清除")
