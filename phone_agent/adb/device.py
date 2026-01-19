#!/usr/bin/env python3
# Original: Copyright (c) 2024 ZAI Organization (Apache-2.0)
# Modified: Copyright (C) 2025 PhoneAgent Contributors (AGPL-3.0)
# Based on: https://github.com/zai-org/Open-AutoGLM

"""Android自动化设备控制工具"""

import os
import subprocess
import time
import shlex  # [SECURITY] 用于安全转义命令参数
from typing import List, Optional, Tuple

from phone_agent.config.apps import APP_PACKAGES
from phone_agent.adb.anti_detection import get_anti_detection


def get_current_app(device_id: str | None = None) -> str:
    """
    获取当前焦点应用名称

    Args:
        device_id: ADB设备ID(可选),用于多设备场景

    Returns:
        识别的应用名称,否则返回"系统桌面"
    """
    adb_prefix = _get_adb_prefix(device_id)

    result = subprocess.run(
        adb_prefix + ["shell", "dumpsys", "window"], 
        capture_output=True, 
        text=True,
        timeout=10
    )
    output = result.stdout

    # 解析窗口焦点信息
    for line in output.split("\n"):
        if "mCurrentFocus" in line or "mFocusedApp" in line:
            for app_name, package in APP_PACKAGES.items():
                if package in line:
                    return app_name

    return "系统桌面"


def tap(x: int, y: int, device_id: str | None = None, delay: float = 1.0, use_anti_detection: bool = True) -> None:
    """
    在指定坐标点击

    Args:
        x: X坐标
        y: Y坐标
        device_id: ADB设备ID(可选)
        delay: 点击后延迟秒数(仅use_anti_detection=False时生效)
        use_anti_detection: 是否使用防风控(随机化坐标和延迟)
    
    Raises:
        RuntimeError: 当点击命令失败或设备不可用时
    """
    # [NEW] 自动检查并重连（针对网络ADB）
    from phone_agent.adb.auto_reconnect import ensure_device_connected
    ensure_device_connected(device_id)
    
    # [OK] 设备健康检查（默认禁用，避免频繁检查导致连接不稳定）
    # 如需启用：export PHONEAGENT_ENABLE_DEVICE_HEALTH_CHECK=true
    from phone_agent.adb.device_health import validate_device_before_command, ENABLE_DEVICE_HEALTH_CHECK
    if ENABLE_DEVICE_HEALTH_CHECK and device_id:
        try:
            validate_device_before_command(device_id)
        except RuntimeError as e:
            # 设备检查失败，但不影响命令执行（让后续的错误检查处理）
            logger.warning(f"Device health check failed: {e}")
    
    adb_prefix = _get_adb_prefix(device_id)
    
    # 防风控：随机化点击位置
    if use_anti_detection:
        ad = get_anti_detection()
        x, y = ad.randomize_point(x, y)

    result = subprocess.run(
        adb_prefix + ["shell", "input", "tap", str(x), str(y)], 
        capture_output=True,
        timeout=10
    )
    
    # [OK] 检查命令执行结果
    if result.returncode != 0:
        error_msg = result.stderr.decode('utf-8', errors='ignore') if result.stderr else "Unknown error"
        
        # 特殊错误处理
        if "device" in error_msg.lower() and "not found" in error_msg.lower():
            raise RuntimeError(f"Device '{device_id}' not found. Please check device connection.")
        elif "offline" in error_msg.lower():
            raise RuntimeError(f"Device '{device_id}' is offline. Please reconnect the device.")
        else:
            raise RuntimeError(f"Tap command failed at ({x}, {y}): {error_msg}")
    
    # 防风控：人性化延迟
    if use_anti_detection:
        get_anti_detection().human_delay()
    else:
        time.sleep(delay)


def double_tap(
    x: int, y: int, device_id: str | None = None, delay: float = 1.0
) -> None:
    """
    Double tap at the specified coordinates.

    Args:
        x: X coordinate.
        y: Y coordinate.
        device_id: Optional ADB device ID.
        delay: Delay in seconds after double tap.
    
    Raises:
        RuntimeError: If tap command fails
    """
    # [NEW] 自动检查并重连
    from phone_agent.adb.auto_reconnect import ensure_device_connected
    ensure_device_connected(device_id)
    
    adb_prefix = _get_adb_prefix(device_id)

    result1 = subprocess.run(
        adb_prefix + ["shell", "input", "tap", str(x), str(y)], 
        capture_output=True,
        timeout=10
    )
    if result1.returncode != 0:
        error_msg = result1.stderr.decode('utf-8', errors='ignore') if result1.stderr else "Unknown error"
        raise RuntimeError(f"First tap failed at ({x}, {y}): {error_msg}")
    
    time.sleep(0.1)
    
    result2 = subprocess.run(
        adb_prefix + ["shell", "input", "tap", str(x), str(y)], 
        capture_output=True,
        timeout=10
    )
    if result2.returncode != 0:
        error_msg = result2.stderr.decode('utf-8', errors='ignore') if result2.stderr else "Unknown error"
        raise RuntimeError(f"Second tap failed at ({x}, {y}): {error_msg}")
    
    time.sleep(delay)


def long_press(
    x: int,
    y: int,
    duration_ms: int = 3000,
    device_id: str | None = None,
    delay: float = 1.0,
) -> None:
    """
    Long press at the specified coordinates.

    Args:
        x: X coordinate.
        y: Y coordinate.
        duration_ms: Duration of press in milliseconds.
        device_id: Optional ADB device ID.
        delay: Delay in seconds after long press.
    
    Raises:
        RuntimeError: If long press command fails
    """
    # [NEW] 自动检查并重连
    from phone_agent.adb.auto_reconnect import ensure_device_connected
    ensure_device_connected(device_id)
    
    adb_prefix = _get_adb_prefix(device_id)

    result = subprocess.run(
        adb_prefix
        + ["shell", "input", "swipe", str(x), str(y), str(x), str(y), str(duration_ms)],
        capture_output=True,
        timeout=15
    )
    
    if result.returncode != 0:
        error_msg = result.stderr.decode('utf-8', errors='ignore') if result.stderr else "Unknown error"
        raise RuntimeError(f"Long press failed at ({x}, {y}): {error_msg}")
    
    time.sleep(delay)


def swipe(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration_ms: int | None = None,
    device_id: str | None = None,
    delay: float = 1.0,
    use_anti_detection: bool = True,
) -> None:
    """
    Swipe from start to end coordinates.

    Args:
        start_x: Starting X coordinate.
        start_y: Starting Y coordinate.
        end_x: Ending X coordinate.
        end_y: Ending Y coordinate.
        duration_ms: Duration of swipe in milliseconds (auto-calculated if None).
        device_id: Optional ADB device ID.
        delay: Delay in seconds after swipe (仅use_anti_detection=False时生效).
        use_anti_detection: 是否使用防风控（贝塞尔曲线滑动）
    """
    # [NEW] 自动检查并重连
    from phone_agent.adb.auto_reconnect import ensure_device_connected
    ensure_device_connected(device_id)
    
    adb_prefix = _get_adb_prefix(device_id)
    ad = get_anti_detection()

    # 配置常量：滑动时长范围（毫秒）
    MIN_SWIPE_DURATION_MS = 1000
    MAX_SWIPE_DURATION_MS = 2000
    
    if duration_ms is None:
        # Calculate duration based on distance
        dist_sq = (start_x - end_x) ** 2 + (start_y - end_y) ** 2
        duration_ms = int(dist_sq / 1000)
        duration_ms = max(MIN_SWIPE_DURATION_MS, min(duration_ms, MAX_SWIPE_DURATION_MS))

    # 防风控：使用贝塞尔曲线生成滑动路径
    if use_anti_detection and ad.enabled and ad.config.get("enable_bezier_swipe", True):
        path = ad.generate_swipe_path(start_x, start_y, end_x, end_y)
        
        # 执行贝塞尔曲线滑动（多段）
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]
            seg_duration = duration_ms // len(path)
            
            result = subprocess.run(
                adb_prefix + [
                    "shell", "input", "swipe",
                    str(x1), str(y1), str(x2), str(y2), str(seg_duration)
                ],
                capture_output=True,
                timeout=15
            )
            if result.returncode != 0:
                error_msg = result.stderr.decode('utf-8', errors='ignore') if result.stderr else "Unknown error"
                raise RuntimeError(f"Swipe segment {i} failed: {error_msg}")
    else:
        # 普通直线滑动
        result = subprocess.run(
            adb_prefix
            + [
                "shell",
                "input",
                "swipe",
                str(start_x),
                str(start_y),
                str(end_x),
                str(end_y),
                str(duration_ms),
            ],
            capture_output=True,
            timeout=15
        )
        if result.returncode != 0:
            error_msg = result.stderr.decode('utf-8', errors='ignore') if result.stderr else "Unknown error"
            raise RuntimeError(f"Swipe failed from ({start_x}, {start_y}) to ({end_x}, {end_y}): {error_msg}")

    # 防风控：人性化延迟
    if use_anti_detection:
        ad.human_delay()
    else:
        time.sleep(delay)


def back(device_id: str | None = None, delay: float = 1.0) -> None:
    """
    Press the back button.

    Args:
        device_id: Optional ADB device ID.
        delay: Delay in seconds after pressing back.
    """
    adb_prefix = _get_adb_prefix(device_id)

    subprocess.run(
        adb_prefix + ["shell", "input", "keyevent", "4"], 
        capture_output=True,
        timeout=10
    )
    time.sleep(delay)


def home(device_id: str | None = None, delay: float = 1.0) -> None:
    """
    Press the home button (go to home screen).

    Args:
        device_id: Optional ADB device ID.
        delay: Delay in seconds after pressing home.
    
    Note:
        Uses 'am start' instead of 'input keyevent' to avoid INJECT_EVENTS permission issues.
    """
    adb_prefix = _get_adb_prefix(device_id)

    # Use Activity Manager to go home (more reliable than keyevent)
    subprocess.run(
        adb_prefix + ["shell", "am", "start", "-a", "android.intent.action.MAIN", 
                      "-c", "android.intent.category.HOME"],
        capture_output=True,
        timeout=10
    )
    time.sleep(delay)


def launch_app(app_name: str, device_id: str | None = None, delay: float = 1.0) -> bool:
    """
    Launch an app by name using Activity Manager (AM).
    
    稳定性优化：
    1. 支持中文显示名和英文名
    2. 三级降级策略：AM -> monkey -> 通知用户手动配置
    3. 详细的错误日志和调试信息

    Args:
        app_name: The app name (中文显示名，如"大麦"，优先匹配).
        device_id: Optional ADB device ID.
        delay: Delay in seconds after launching.

    Returns:
        True if app was launched, False if app not found.
    
    Note:
        推荐在 data/app_config.json 中配置应用的中文显示名和包名。
        硬编码的 APP_PACKAGES 作为后备方案。
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # [NEW] 自动检查并重连
    from phone_agent.adb.auto_reconnect import ensure_device_connected
    ensure_device_connected(device_id)
    
    package = None
    source = None
    
    # 策略1: 优先从动态配置文件获取（支持中文、英文、别名）
    try:
        import json
        config_file = "data/app_config.json"
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                app_configs = json.load(f)
                # 查找匹配的app（支持多种名称格式）
                for app in app_configs:
                    # 匹配中文显示名
                    if app.get('display_name') == app_name:
                        package = app.get('package_name')
                        source = f"app_config.json (中文名: {app_name})"
                        break
                    
                    # 匹配英文显示名（不区分大小写）
                    if app.get('display_name_en', '').lower() == app_name.lower():
                        package = app.get('package_name')
                        source = f"app_config.json (英文名: {app_name})"
                        break
                    
                    # 匹配别名（不区分大小写）
                    aliases = app.get('aliases', [])
                    if any(alias.lower() == app_name.lower() for alias in aliases):
                        package = app.get('package_name')
                        source = f"app_config.json (别名: {app_name})"
                        break
    except Exception as e:
        logger.warning(f"Failed to load app config: {e}")
    
    # 策略2: 从硬编码的APP_PACKAGES获取（向后兼容）
    if not package:
        package = APP_PACKAGES.get(app_name)
        if package:
            source = "APP_PACKAGES (hardcoded)"
    
    # 如果仍然找不到包名，返回详细错误
    if not package:
        logger.error(f"[X] 未找到应用 '{app_name}' 的包名")
        logger.info(f"[NOTE] 提示: 请在 data/app_config.json 中添加应用配置:")
        logger.info(f'   {{"display_name": "{app_name}", "package_name": "com.example.app"}}')
        logger.info(f"   或在 phone_agent/config/apps.py 的 APP_PACKAGES 中添加")
        return False

    adb_prefix = _get_adb_prefix(device_id)
    logger.info(f" 正在启动应用: {app_name} ({package}) [来源: {source}]")

    # Method 1: Use Activity Manager (AM) - Most reliable and fast
    try:
        result = subprocess.run(
            adb_prefix + [
                "shell",
                "am",
                "start",
                "-a",
                "android.intent.action.MAIN",
                "-c",
                "android.intent.category.LAUNCHER",
                package
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Check if launch was successful
        if result.returncode == 0 and "Error" not in result.stderr:
            logger.info(f"[OK] 应用启动成功 (AM): {app_name}")
            time.sleep(delay)
            return True
        
        logger.warning(f"[WARN] AM启动失败: {result.stderr.strip()}")
        
    except subprocess.TimeoutExpired:
        logger.warning(f"[WARN] AM启动超时")
    except Exception as e:
        logger.warning(f"[WARN] AM启动异常: {e}")
    
    # Method 2: Fallback to monkey command
    logger.info(f"[UPDATE] 尝试 monkey 命令启动...")
    try:
        result = subprocess.run(
            adb_prefix + [
                "shell",
                "monkey",
                "-p",
                package,
                "-c",
                "android.intent.category.LAUNCHER",
                "1",
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info(f"[OK] 应用启动成功 (monkey): {app_name}")
            time.sleep(delay)
            return True
        
        stderr = result.stderr.strip()
        
        # 特殊错误处理
        if "device" in stderr.lower() and "not found" in stderr.lower():
            logger.error(f"[X] 设备未连接: {stderr}")
            logger.error(f"[NOTE] 请检查设备连接状态: adb devices")
        elif "offline" in stderr.lower():
            logger.error(f"[X] 设备离线: {stderr}")
            logger.error(f"[NOTE] 请重新连接设备或重启ADB")
        else:
            logger.error(f"[X] monkey启动失败: {stderr}")
        
    except subprocess.TimeoutExpired:
        logger.error(f"[X] monkey启动超时")
    except Exception as e:
        logger.error(f"[X] monkey启动异常: {e}")
    
    # Method 3: All methods failed
    logger.error(f"[X] 应用启动失败: {app_name}")
    logger.info(f"[NOTE] 调试建议:")
    logger.info(f"   1. 检查包名是否正确: {package}")
    logger.info(f"   2. 手动测试: adb shell am start -n {package}/.MainActivity")
    logger.info(f"   3. 检查应用是否已安装: adb shell pm list packages | grep {package}")
    return False


def _get_adb_prefix(device_id: str | None) -> list:
    """
    Get ADB command prefix with optional device specifier.
    
    [SECURITY] 安全性：device_id 会被验证，防止命令注入
    """
    if device_id:
        # [SECURITY] 验证 device_id 格式，防止命令注入
        # 合法格式：localhost:6100, 192.168.1.100:5555, emulator-5554, ABCD1234
        if not _is_valid_device_id(device_id):
            raise ValueError(f"Invalid device_id format: {device_id}")
        return ["adb", "-s", device_id]
    return ["adb"]


def _is_valid_device_id(device_id: str) -> bool:
    """
    验证 device_id 格式是否合法
    
    合法格式：
    - localhost:6100
    - 192.168.1.100:5555
    - emulator-5554
    - ABCD1234 (设备序列号)
    
    Args:
        device_id: 设备ID
    
    Returns:
        是否合法
    """
    import re
    
    # 允许的格式
    patterns = [
        r'^localhost:\d{1,5}$',           # localhost:6100
        r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}$',  # IP:Port
        r'^emulator-\d+$',                # emulator-5554
        r'^[A-Za-z0-9_-]+$',              # 设备序列号
        r'^device_\d+$',                  # device_6100 (自定义格式)
    ]
    
    return any(re.match(pattern, device_id) for pattern in patterns)


def run_adb_command(
    command: list[str],
    device_id: str | None = None,
    timeout: int = 30,
    check_error: bool = True
) -> str:
    """
    执行 ADB 命令的统一封装
    
    集成自 Android Action Kernel (MIT License)
    提供统一的 ADB 命令执行接口，简化代码复用。
    
    Args:
        command: ADB 命令参数列表（不包含 'adb' 前缀）
        device_id: 设备ID（可选）
        timeout: 超时时间（秒）
        check_error: 是否检查错误
    
    Returns:
        命令输出（stdout）
    
    Raises:
        RuntimeError: 如果命令执行失败且 check_error=True
    """
    adb_prefix = _get_adb_prefix(device_id)
    
    try:
        result = subprocess.run(
            adb_prefix + command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        # 检查错误
        if check_error and result.stderr and "error" in result.stderr.lower():
            raise RuntimeError(f"ADB Error: {result.stderr.strip()}")
        
        return result.stdout.strip()
        
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"ADB command timeout after {timeout}s: {' '.join(command)}")
    except Exception as e:
        if check_error:
            raise RuntimeError(f"ADB command failed: {e}")
        return ""
