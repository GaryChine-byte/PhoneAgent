#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
设备健康检查和自动恢复模块

解决问题：
1. 设备连接丢失（device not found）
2. 设备离线（device offline）
3. ADB服务异常

提供功能：
1. 设备连接状态检查
2. 自动重连
3. 连接健康监控
"""

import logging
import subprocess
import time
from typing import Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class DeviceHealth:
    """设备健康状态"""
    is_connected: bool
    is_responsive: bool
    error_message: Optional[str] = None
    last_check: Optional[datetime] = None


class DeviceHealthChecker:
    """设备健康检查器"""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self._last_health: Optional[DeviceHealth] = None
        self._check_interval = 60  # 秒 - 增加到60秒，减少频繁检查
        
    def check_device_connected(self) -> Tuple[bool, str]:
        """
        检查设备是否连接
        
        Returns:
            (is_connected, message)
        """
        try:
            cmd = ["adb", "devices"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                return False, f"ADB command failed: {result.stderr}"
            
            # 解析输出
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:  # 跳过标题行
                if not line.strip():
                    continue
                    
                parts = line.split()
                if len(parts) >= 2:
                    device = parts[0]
                    status = parts[1]
                    
                    if device == self.device_id:
                        if status == "device":
                            return True, "Connected"
                        elif status == "offline":
                            return False, "Device offline"
                        elif status == "unauthorized":
                            return False, "Device unauthorized (check USB debugging)"
                        else:
                            return False, f"Device status: {status}"
            
            return False, f"Device '{self.device_id}' not found in device list"
            
        except subprocess.TimeoutExpired:
            return False, "ADB devices command timeout"
        except Exception as e:
            return False, f"Check failed: {e}"
    
    def check_device_responsive(self, timeout: float = 3.0) -> Tuple[bool, str]:
        """
        检查设备是否响应
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            (is_responsive, message)
        """
        try:
            cmd = ["adb", "-s", self.device_id, "shell", "echo", "ping"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            
            if result.returncode == 0 and "ping" in result.stdout:
                return True, "Responsive"
            else:
                return False, f"No response (returncode={result.returncode})"
                
        except subprocess.TimeoutExpired:
            return False, f"Response timeout after {timeout}s"
        except Exception as e:
            return False, f"Check failed: {e}"
    
    def get_health(self, force_check: bool = False) -> DeviceHealth:
        """
        获取设备健康状态
        
        Args:
            force_check: 强制检查（忽略缓存）
        
        Returns:
            DeviceHealth对象
        """
        # 检查缓存
        if not force_check and self._last_health:
            if self._last_health.last_check:
                elapsed = (datetime.now() - self._last_health.last_check).total_seconds()
                if elapsed < self._check_interval:
                    return self._last_health
        
        # 执行检查
        is_connected, conn_msg = self.check_device_connected()
        
        if not is_connected:
            health = DeviceHealth(
                is_connected=False,
                is_responsive=False,
                error_message=conn_msg,
                last_check=datetime.now()
            )
        else:
            is_responsive, resp_msg = self.check_device_responsive()
            health = DeviceHealth(
                is_connected=True,
                is_responsive=is_responsive,
                error_message=None if is_responsive else resp_msg,
                last_check=datetime.now()
            )
        
        self._last_health = health
        return health
    
    def try_reconnect(self, max_attempts: int = 3) -> Tuple[bool, str]:
        """
        尝试重新连接设备
        
        Args:
            max_attempts: 最大尝试次数
        
        Returns:
            (success, message)
        """
        logger.info(f"[UPDATE] 尝试重新连接设备: {self.device_id}")
        
        # 如果是网络ADB，尝试重新连接
        if ":" in self.device_id:
            for attempt in range(1, max_attempts + 1):
                logger.info(f"   尝试 {attempt}/{max_attempts}...")
                
                try:
                    # 先断开
                    disconnect_cmd = ["adb", "disconnect", self.device_id]
                    subprocess.run(disconnect_cmd, capture_output=True, timeout=5)
                    time.sleep(1)
                    
                    # 再连接
                    connect_cmd = ["adb", "connect", self.device_id]
                    result = subprocess.run(connect_cmd, capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        output = result.stdout.lower()
                        if "connected" in output or "already connected" in output:
                            # 验证连接
                            time.sleep(2)
                            is_connected, msg = self.check_device_connected()
                            if is_connected:
                                logger.info(f"[OK] 重新连接成功!")
                                return True, "Reconnected successfully"
                            else:
                                logger.warning(f"   连接命令成功但设备未出现: {msg}")
                        else:
                            logger.warning(f"   连接失败: {result.stdout}")
                    
                    time.sleep(2)
                    
                except Exception as e:
                    logger.warning(f"   重连异常: {e}")
                    
            return False, f"Failed to reconnect after {max_attempts} attempts"
        
        else:
            # USB设备，尝试重启ADB
            logger.info("   USB设备，尝试重启ADB服务...")
            try:
                # 重启ADB
                subprocess.run(["adb", "kill-server"], capture_output=True, timeout=5)
                time.sleep(2)
                subprocess.run(["adb", "start-server"], capture_output=True, timeout=10)
                time.sleep(3)
                
                # 验证连接
                is_connected, msg = self.check_device_connected()
                if is_connected:
                    logger.info(f"[OK] ADB重启成功，设备已连接")
                    return True, "ADB restarted, device reconnected"
                else:
                    return False, f"ADB restarted but device not found: {msg}"
                    
            except Exception as e:
                return False, f"Failed to restart ADB: {e}"


def check_and_recover_device(device_id: str, auto_reconnect: bool = True) -> Tuple[bool, str]:
    """
    检查设备健康状态并自动恢复
    
    这是一个便捷函数，用于在执行命令前检查设备状态
    
    Args:
        device_id: 设备ID
        auto_reconnect: 是否自动尝试重连
    
    Returns:
        (is_healthy, message)
    
    Example:
        >>> is_ok, msg = check_and_recover_device("localhost:6104")
        >>> if not is_ok:
        >>>     raise RuntimeError(f"Device not ready: {msg}")
    """
    checker = DeviceHealthChecker(device_id)
    
    # 检查健康状态
    health = checker.get_health(force_check=True)
    
    if health.is_connected and health.is_responsive:
        return True, "Device healthy"
    
    # 设备有问题
    error_msg = health.error_message or "Unknown error"
    logger.warning(f"[WARN] 设备异常: {error_msg}")
    
    # 尝试恢复
    if auto_reconnect:
        success, reconnect_msg = checker.try_reconnect()
        if success:
            # 再次检查
            health = checker.get_health(force_check=True)
            if health.is_connected and health.is_responsive:
                return True, "Device recovered"
            else:
                return False, f"Reconnected but still unhealthy: {health.error_message}"
        else:
            return False, f"Device unhealthy and reconnect failed: {reconnect_msg}"
    
    return False, f"Device unhealthy: {error_msg}"


def validate_device_before_command(device_id: Optional[str]) -> None:
    """
    在执行命令前验证设备状态
    
    如果设备不健康，会尝试恢复，失败则抛出异常
    
    Args:
        device_id: 设备ID
    
    Raises:
        RuntimeError: 如果设备不可用
    
    Example:
        >>> validate_device_before_command("localhost:6104")
        >>> # 如果设备不可用，会抛出异常
    """
    if not device_id:
        # 没有指定设备ID，使用默认设备
        return
    
    is_healthy, msg = check_and_recover_device(device_id, auto_reconnect=True)
    
    if not is_healthy:
        raise RuntimeError(f"Device '{device_id}' is not available: {msg}")


# 全局配置：是否启用设备健康检查
# [WARN] 默认禁用，因为频繁检查可能导致连接不稳定
# 只在明确需要时启用（通过环境变量 PHONEAGENT_ENABLE_DEVICE_HEALTH_CHECK=true）
import os
ENABLE_DEVICE_HEALTH_CHECK = os.getenv("PHONEAGENT_ENABLE_DEVICE_HEALTH_CHECK", "false").lower() == "true"

logger.info(f"Device Health Check: {'ENABLED' if ENABLE_DEVICE_HEALTH_CHECK else 'DISABLED'}")
