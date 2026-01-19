#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""Server utilities module."""

from .image_utils import compress_screenshot
import re
import logging

logger = logging.getLogger(__name__)


class DeviceIDConverter:
    """
    设备ID转换器 - 统一管理device_id和adb_address之间的转换
    
    支持的格式：
    - device_6100 <-> localhost:6100
    - device_6100 <-> 192.168.1.100:6100 (远程设备)
    - localhost:6100 -> device_6100
    """
    
    # 缓存转换结果，避免重复计算
    _cache = {}
    
    @classmethod
    def to_adb_address(cls, device_id: str, default_host: str = "localhost") -> str:
        """
        将 device_id 转换为 ADB 地址
        
        Args:
            device_id: 设备ID (如 device_6100) 或已经是 ADB 地址
            default_host: 默认主机地址，用于 device_6100 格式
        
        Returns:
            ADB 地址 (如 localhost:6100)
        
        Examples:
            >>> DeviceIDConverter.to_adb_address("device_6100")
            'localhost:6100'
            >>> DeviceIDConverter.to_adb_address("localhost:6100")
            'localhost:6100'
            >>> DeviceIDConverter.to_adb_address("192.168.1.100:5555")
            '192.168.1.100:5555'
        """
        if not device_id:
            raise ValueError("device_id cannot be empty")
        
        # 检查缓存
        cache_key = f"to_adb:{device_id}:{default_host}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]
        
        result = device_id
        
        # 如果已经是 host:port 格式，直接返回
        if ":" in device_id and not device_id.startswith("device_"):
            result = device_id
        # 如果是 device_XXXX 格式，转换为 host:port
        elif device_id.startswith("device_"):
            try:
                port = int(device_id.replace("device_", ""))
                result = f"{default_host}:{port}"
            except ValueError as e:
                logger.warning(f"Invalid device_id format: {device_id}, error: {e}")
                result = device_id
        
        # 缓存结果
        cls._cache[cache_key] = result
        return result
    
    @classmethod
    def to_device_id(cls, adb_address: str) -> str:
        """
        将 ADB 地址转换为 device_id
        
        Args:
            adb_address: ADB 地址 (如 localhost:6100)
        
        Returns:
            device_id (如 device_6100)
        
        Examples:
            >>> DeviceIDConverter.to_device_id("localhost:6100")
            'device_6100'
            >>> DeviceIDConverter.to_device_id("192.168.1.100:6100")
            'device_6100'
            >>> DeviceIDConverter.to_device_id("device_6100")
            'device_6100'
        """
        if not adb_address:
            raise ValueError("adb_address cannot be empty")
        
        # 检查缓存
        cache_key = f"to_device:{adb_address}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]
        
        result = adb_address
        
        # 如果已经是 device_XXXX 格式，直接返回
        if adb_address.startswith("device_"):
            result = adb_address
        # 如果是 host:port 格式，提取端口转换为 device_XXXX
        elif ":" in adb_address:
            try:
                port = int(adb_address.split(":")[-1])
                result = f"device_{port}"
            except ValueError as e:
                logger.warning(f"Invalid adb_address format: {adb_address}, error: {e}")
                result = adb_address
        
        # 缓存结果
        cls._cache[cache_key] = result
        return result
    
    @classmethod
    def extract_port(cls, identifier: str) -> int:
        """
        从设备标识中提取端口号
        
        Args:
            identifier: device_6100 或 localhost:6100
        
        Returns:
            端口号 (如 6100)
        
        Raises:
            ValueError: 无法提取端口号
        """
        if identifier.startswith("device_"):
            return int(identifier.replace("device_", ""))
        elif ":" in identifier:
            return int(identifier.split(":")[-1])
        else:
            raise ValueError(f"Cannot extract port from: {identifier}")
    
    @classmethod
    def clear_cache(cls):
        """清空转换缓存"""
        cls._cache.clear()
        logger.info("DeviceIDConverter cache cleared")


# 向后兼容的函数别名
def device_id_to_adb_address(device_id: str) -> str:
    """
    将 device_id 转换为 ADB 地址 (向后兼容)
    
    推荐使用: DeviceIDConverter.to_adb_address()
    """
    return DeviceIDConverter.to_adb_address(device_id)


def adb_address_to_device_id(adb_address: str) -> str:
    """
    将 ADB 地址转换为 device_id
    
    推荐使用: DeviceIDConverter.to_device_id()
    """
    return DeviceIDConverter.to_device_id(adb_address)


__all__ = [
    "compress_screenshot", 
    "device_id_to_adb_address", 
    "adb_address_to_device_id",
    "DeviceIDConverter"
]

