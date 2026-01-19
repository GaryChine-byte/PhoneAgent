#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""Android设备屏幕截图工具"""

import base64
import os
import subprocess
import uuid
import tempfile
import logging
from dataclasses import dataclass
from io import BytesIO
from typing import Tuple

from PIL import Image

# 尝试导入 yadb（强制截图功能）
try:
    from . import yadb
    YADB_AVAILABLE = True
except ImportError:
    YADB_AVAILABLE = False

logger = logging.getLogger(__name__)

# 配置：是否尝试使用 yadb 强制截图
USE_YADB_FORCE_SCREENSHOT = True


@dataclass
class Screenshot:
    """捕获的截图数据"""

    base64_data: str
    width: int
    height: int
    is_sensitive: bool = False
    forced: bool = False  # 新增: 是否使用强制截图


def get_screenshot(
    device_id: str | None = None, 
    timeout: int = 30,
    adb_host: str | None = None,
    adb_port: int | None = None,
    force_yadb: bool = False,
    prefer_yadb: bool = True  # 新增: 优先使用 yadb
) -> Screenshot:
    """
    从连接的Android设备捕获截图

    Args:
        device_id: ADB设备ID(可选),用于多设备场景
        timeout: 截图操作超时秒数
        adb_host: ADB服务器主机(用于FRP隧道)
        adb_port: ADB服务器端口(用于FRP隧道)
        force_yadb: 强制只使用yadb(不回退)
        prefer_yadb: 优先使用yadb但失败时回退到标准方式(默认: True)

    Returns:
        包含base64数据和尺寸的Screenshot对象

    Note:
        **优先级策略 (prefer_yadb=True, 默认):**
        1. 优先尝试 yadb 强制截图(可绕过 FLAG_SECURE)
        2. 如果 yadb 失败,回退到标准截图
        
        **强制模式 (force_yadb=True):**
        - 只使用 yadb,不回退
        
        **标准模式 (prefer_yadb=False):**
        - 先用标准截图,失败时才用 yadb
    """
    # 模式 1: 强制只使用 yadb (不回退)
    if force_yadb and YADB_AVAILABLE and USE_YADB_FORCE_SCREENSHOT:
        logger.info("[SECURITY] Using yadb force screenshot (forced mode, no fallback)")
        return _get_screenshot_yadb(device_id, adb_host, adb_port)
    
    # 模式 2: 优先使用 yadb (推荐，默认)
    if prefer_yadb and YADB_AVAILABLE and USE_YADB_FORCE_SCREENSHOT:
        logger.info("[TARGET] Trying yadb force screenshot first (preferred mode)...")
        yadb_screenshot = _get_screenshot_yadb(device_id, adb_host, adb_port)
        
        # yadb 成功，直接返回
        if yadb_screenshot and not yadb_screenshot.is_sensitive:
            logger.info("[OK] yadb force screenshot succeeded!")
            return yadb_screenshot
        
        # yadb 失败，回退到标准截图
        logger.warning("[WARN] yadb failed, falling back to standard screenshot...")
        return _get_screenshot_standard(device_id, timeout, adb_host, adb_port)
    
    # 模式 3: 标准模式 (先标准，失败时用 yadb)
    logger.info("📸 Using standard screenshot...")
    screenshot = _get_screenshot_standard(device_id, timeout, adb_host, adb_port)
    
    # 如果标准截图失败（敏感屏幕），尝试 yadb 强制截图
    if screenshot.is_sensitive and YADB_AVAILABLE and USE_YADB_FORCE_SCREENSHOT:
        logger.info("🔓 Standard screenshot blocked, trying yadb force screenshot...")
        yadb_screenshot = _get_screenshot_yadb(device_id, adb_host, adb_port)
        
        if yadb_screenshot and not yadb_screenshot.is_sensitive:
            logger.info("[OK] yadb force screenshot succeeded!")
            return yadb_screenshot
        else:
            logger.warning("[X] yadb force screenshot also failed, returning fallback")
    
    return screenshot


def _get_screenshot_standard(
    device_id: str | None = None, 
    timeout: int = 30,
    adb_host: str | None = None,
    adb_port: int | None = None
) -> Screenshot:
    """
    Standard screenshot using adb screencap.
    
    This is the default method, but will fail on apps with FLAG_SECURE.
    """
    adb_prefix = _get_adb_prefix(device_id, adb_host, adb_port)

    try:
        # 使用 exec-out 直接获取截图数据（不需要在手机上写文件）
        # 这种方法更适合远程 FRP 环境
        result = subprocess.run(
            adb_prefix + ["exec-out", "screencap", "-p"],
            capture_output=True,
            timeout=timeout,
        )

        # 检查是否成功
        if result.returncode != 0:
            error_msg = result.stderr.decode('utf-8', errors='ignore')
            logger.warning(f"Standard screenshot failed: {error_msg}")
            
            # 检测是否是敏感页面（FLAG_SECURE）
            is_sensitive = "Status: -1" in error_msg or "FLAG_SECURE" in error_msg
            return _create_fallback_screenshot(is_sensitive=is_sensitive)

        # 直接从 stdout 获取 PNG 数据
        image_data = result.stdout
        
        if not image_data or len(image_data) < 100:
            logger.warning(f"Screenshot data too small: {len(image_data)} bytes")
            # [OK] 修复：数据过小也可能是敏感屏幕
            return _create_fallback_screenshot(is_sensitive=True)

        # 使用 BytesIO 从内存中加载图片
        img = Image.open(BytesIO(image_data))
        width, height = img.size

        # [OK] 新增：检测是否是全黑或几乎全黑的图片（可能是敏感屏幕）
        # 计算平均亮度
        grayscale = img.convert('L')  # 转为灰度
        pixels = list(grayscale.getdata())
        avg_brightness = sum(pixels) / len(pixels)
        
        # 如果平均亮度低于10（几乎全黑），标记为敏感
        if avg_brightness < 10:
            logger.warning(f"Screenshot is almost black (brightness: {avg_brightness:.1f}), marking as sensitive")
            return _create_fallback_screenshot(is_sensitive=True)

        # 直接对原始数据进行 base64 编码
        base64_data = base64.b64encode(image_data).decode("utf-8")

        return Screenshot(
            base64_data=base64_data, 
            width=width, 
            height=height, 
            is_sensitive=False,
            forced=False
        )

    except subprocess.TimeoutExpired:
        logger.error(f"Screenshot timeout after {timeout}s")
        return _create_fallback_screenshot(is_sensitive=True)  # [OK] 超时也标记为敏感
    except Exception as e:
        logger.error(f"Screenshot error: {e}", exc_info=True)
        return _create_fallback_screenshot(is_sensitive=True)  # [OK] 异常也标记为敏感


def _get_screenshot_yadb(
    device_id: str | None = None,
    adb_host: str | None = None,
    adb_port: int | None = None
) -> Screenshot:
    """
    Force screenshot using yadb (bypasses FLAG_SECURE).
    
    This method can capture screenshots even on sensitive apps like banking
    and payment apps that normally block screenshots.
    """
    try:
        # 使用重试机制（最多3次）
        result = yadb.force_screenshot_base64(
            device_id=device_id,
            adb_host=adb_host,
            adb_port=adb_port,
            include_dimensions=True,
            max_retries=3  # 新增：最多重试3次
        )
        
        if result and isinstance(result, dict):
            return Screenshot(
                base64_data=result["base64_data"],
                width=result["width"],
                height=result["height"],
                is_sensitive=False,
                forced=True  # 标记为强制截图
            )
        else:
            logger.error("yadb force screenshot returned invalid data")
            return _create_fallback_screenshot(is_sensitive=True)
            
    except Exception as e:
        logger.error(f"yadb force screenshot error: {e}", exc_info=True)
        return _create_fallback_screenshot(is_sensitive=True)


def _get_adb_prefix(device_id: str | None, adb_host: str | None = None, adb_port: int | None = None) -> list:
    """
    Get ADB command prefix with optional device specifier.
    
    Args:
        device_id: Device serial number (can be IP:PORT for network ADB)
        adb_host: ADB server host (deprecated, use device_id with IP:PORT instead)
        adb_port: ADB server port (deprecated, use device_id with IP:PORT instead)
    
    Returns:
        ADB command prefix list
    
    Note:
        For FRP tunneling, use device_id="localhost:6104" instead of adb_host/adb_port.
        The -H and -P flags are for ADB server, not for device connection.
    """
    cmd = ["adb"]
    
    # 优先使用 device_id
    if device_id:
        cmd.extend(["-s", device_id])
    # 兼容旧参数：将 adb_host:adb_port 转换为 device_id
    elif adb_host and adb_port:
        device_address = f"{adb_host}:{adb_port}"
        cmd.extend(["-s", device_address])
        logger.debug(f"Converting adb_host/adb_port to device_id: {device_address}")
    
    return cmd


def _create_fallback_screenshot(is_sensitive: bool) -> Screenshot:
    """Create a black fallback image when screenshot fails."""
    default_width, default_height = 1080, 2400

    black_img = Image.new("RGB", (default_width, default_height), color="black")
    buffered = BytesIO()
    black_img.save(buffered, format="PNG")
    base64_data = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return Screenshot(
        base64_data=base64_data,
        width=default_width,
        height=default_height,
        is_sensitive=is_sensitive,
    )
