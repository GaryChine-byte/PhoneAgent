#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0
#
# This module uses yadb binary from official repository (LGPL-3.0)
# Repository: https://github.com/ysbing/YADB
# Author: ysbing
#
# YADB is called as an independent tool via subprocess (dynamic linking),
# so PhoneAgent code remains independent and is NOT subject to LGPL copyleft.

"""
YADB utilities for enhanced Android device control.

Key features (official yadb support):
- Chinese text input (no APK required)
- Force screenshot (bypass FLAG_SECURE)
- Clipboard operations
- Long press simulation

Note: yadb does NOT support UI layout dump. Use uiautomator for that.
"""

import subprocess
import hashlib
import logging
import base64
from pathlib import Path
from typing import Optional
from io import BytesIO

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = logging.getLogger(__name__)

# yadb 文件的 MD5 校验值（官方版本）
YADB_MD5 = "29a0cd3b3adea92350dd5a25594593df"

# yadb 在本地的路径
YADB_LOCAL_PATH = Path(__file__).parent.parent / "yadb" / "yadb"

# yadb 在设备上的路径
YADB_DEVICE_PATH = "/data/local/tmp/yadb"


def _check_md5(file_path: Path) -> str:
    """Calculate MD5 hash of a file."""
    if not file_path.exists():
        return ""
    
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def _build_adb_cmd(device_id: str = None, adb_host: str = None, adb_port: int = None) -> list:
    """
    Build ADB command prefix.
    
    Args:
        device_id: Device serial number (can be IP:PORT for network ADB)
        adb_host: ADB server host (deprecated, use device_id with IP:PORT instead)
        adb_port: ADB server port (deprecated, use device_id with IP:PORT instead)
    
    Returns:
        ADB command prefix list
    
    Note:
        For FRP tunneling, use device_id="localhost:6104" instead of adb_host/adb_port.
        The -H and -P flags are for ADB server, not for device connection.
    
    TODO: [重构] 统一 device_id 格式，移除 adb_host/adb_port 参数
        - 当前存在两种 ID 格式混用：
          1. 友好 ID: "device_6100" (前端/WebSocket 用)
          2. ADB 地址: "localhost:6100" (ADB 命令用)
        - 应该使用 server.utils.DeviceIDConverter 统一转换
        - 参考: DEVICE_ID_CHAOS_ANALYSIS.md
    """
    cmd = ["adb"]
    
    # 🔥 临时修复：智能判断 device_id 是否是有效的 ADB 地址
    # 有效的 ADB 地址包含 ':'（如 localhost:6100）或是直连设备序列号
    # 无效的 ID 如 "device_6100" 应该回退到 adb_host:adb_port
    # TODO: 长期应该在调用方统一使用 DeviceIDConverter
    
    if device_id and ':' in device_id:
        # 完整的网络地址（FRP 模式）
        cmd.extend(["-s", device_id])
        logger.debug(f"Using network device address: {device_id}")
    elif adb_host and adb_port:
        # 从 adb_host:adb_port 构建地址
        device_address = f"{adb_host}:{adb_port}"
        cmd.extend(["-s", device_address])
        logger.debug(f"Building device address from host/port: {device_address}")
    elif device_id:
        # 可能是直连设备的序列号（不包含 ':'）
        # 或者是错误的友好 ID（如 "device_6100"）
        cmd.extend(["-s", device_id])
        if not device_id.startswith(('emulator-', '192.168.', '10.', '172.')):
            # 不像是有效的设备 ID，记录警告
            logger.warning(f"device_id '{device_id}' may not be a valid ADB address. Expected format: 'localhost:PORT' or device serial.")
    
    return cmd


# 全局缓存（减少重复检查）
_yadb_check_cache: dict[str, bool] = {}
_cache_expiry: dict[str, float] = {}
CACHE_TTL = 60  # 1分钟缓存（从5分钟缩短，更快检测设备状态变化）


def is_yadb_installed(device_id: str = None, adb_host: str = None, adb_port: int = None, use_cache: bool = True) -> bool:
    """
    Check if yadb is installed on the device.

    Args:
        device_id: Device serial number
        adb_host: ADB server host (for FRP tunneling)
        adb_port: ADB server port (for FRP tunneling)
        use_cache: 是否使用缓存（默认True，可提升性能）

    Returns:
        True if yadb is installed, False otherwise.
    """
    import time
    
    # 生成缓存key
    cache_key = device_id or f"{adb_host}:{adb_port}"
    
    # 检查缓存
    if use_cache and cache_key in _yadb_check_cache:
        if time.time() < _cache_expiry.get(cache_key, 0):
            logger.debug(f"[CACHE] yadb检测结果: {_yadb_check_cache[cache_key]}")
            return _yadb_check_cache[cache_key]
    
    cmd = _build_adb_cmd(device_id, adb_host, adb_port)
    
    try:
        # 简化检测：只检查文件是否存在且可执行
        # Remote App保证yadb正确性，无需检查MD5
        # [FIX] yadb 是 DEX 文件，不是 ELF 可执行文件
        # 应该检查文件是否存在（-f），而不是是否可执行（-x）
        result = subprocess.run(
            cmd + ["shell", "test", "-f", YADB_DEVICE_PATH, "&&", "echo", "OK"],
            capture_output=True,
            text=True,
            timeout=5  # 缩短超时
        )
        
        installed = "OK" in result.stdout
        
        # 更新缓存
        if use_cache:
            _yadb_check_cache[cache_key] = installed
            _cache_expiry[cache_key] = time.time() + CACHE_TTL
            logger.debug(f"[CACHE] yadb检测结果已缓存: {installed}")
        
        return installed
        
    except Exception as e:
        logger.debug(f"yadb check failed: {e}")
        return False


def install_yadb(device_id: str = None, adb_host: str = None, adb_port: int = None) -> bool:
    """
    Install yadb binary to the device (fallback method).
    
    [WARN] **Note**: yadb should be pre-installed by the Android app from assets.
    This method is a fallback for manual installation or troubleshooting.
    
    The Android app (PhoneAgent Remote) automatically installs yadb from
    assets/yadb/yadb to /data/local/tmp/yadb during startup.
    
    Args:
        device_id: Device serial number
        adb_host: ADB server host (for FRP tunneling)
        adb_port: ADB server port (for FRP tunneling)

    Returns:
        True if installation successful, False otherwise.
    """
    cmd = _build_adb_cmd(device_id, adb_host, adb_port)
    
    try:
        logger.warning("[WARN] yadb not found - it should be pre-installed by Android app")
        logger.info("Attempting fallback installation via adb push...")
        
        # 尝试使用 adb push 推送本地文件（如果存在）
        if YADB_LOCAL_PATH.exists():
            try:
                # 推送本地 yadb 文件
                push_cmd = cmd + ["push", str(YADB_LOCAL_PATH), YADB_DEVICE_PATH]
                result = subprocess.run(push_cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    # [FIX] yadb 是 DEX 文件，设置读权限即可（不需要可执行权限）
                    # DEX 文件通过 app_process 运行，不需要 +x 权限
                    chmod_cmd = cmd + ["shell", f"chmod 644 {YADB_DEVICE_PATH}"]
                    subprocess.run(chmod_cmd, capture_output=True, timeout=10)
                    
                    # 验证
                    if is_yadb_installed(device_id, adb_host, adb_port):
                        logger.info(f"[OK] yadb successfully installed via adb push")
                        return True
                    else:
                        logger.warning("adb push succeeded but verification failed")
                else:
                    logger.debug(f"adb push failed: {result.stderr}")
            except Exception as e:
                logger.debug(f"adb push error: {e}")
        else:
            logger.warning(f"Local yadb file not found: {YADB_LOCAL_PATH}")
        
        logger.error("Failed to install yadb via fallback method")
        logger.info("Troubleshooting:")
        logger.info("  1. Ensure Android app (PhoneAgent Remote) is running")
        logger.info("  2. Check if yadb exists: adb shell ls -l /data/local/tmp/yadb")
        logger.info("  3. Manual install: adb push yadb /data/local/tmp/yadb && adb shell chmod 755 /data/local/tmp/yadb")
        return False
            
    except Exception as e:
        logger.error(f"yadb installation error: {e}")
        return False


def ensure_yadb_ready(device_id: str = None, adb_host: str = None, adb_port: int = None, skip_install: bool = True) -> bool:
    """
    Ensure yadb is installed and ready to use.
    
    [IMPORTANT] yadb应该由Android Remote App预安装。
    此函数默认只检查，不尝试安装（skip_install=True）。
    
    Args:
        device_id: Device serial number
        adb_host: ADB server host (for FRP tunneling)
        adb_port: ADB server port (for FRP tunneling)
        skip_install: 默认True，只检查不安装（推荐）

    Returns:
        True if yadb is ready, False otherwise.
    """
    # 检查是否已安装（使用缓存）
    if is_yadb_installed(device_id, adb_host, adb_port, use_cache=True):
        logger.debug(f"✅ yadb ready")
        return True
    
    # 默认不尝试安装（Remote App负责安装）
    if skip_install:
        logger.warning(f"⚠️ yadb not found on device")
        logger.info(f"💡 Ensure Android Remote App is running and yadb is installed")
        logger.info(f"💡 Test yadb: adb -s {device_id or 'DEVICE'} shell 'test -x /data/local/tmp/yadb && echo OK'")
        return False
    
    # 仅在明确要求时才尝试fallback安装
    logger.warning(f"⚠️ yadb not found, attempting fallback installation...")
    logger.info(f"💡 This should rarely happen if Remote App is running")
    return install_yadb(device_id, adb_host, adb_port)


def type_text(text: str, device_id: str = None, adb_host: str = None, adb_port: int = None) -> bool:
    """
    Type text into the currently focused input field using yadb.

    Args:
        text: The text to type (supports Chinese, Emoji, etc.)
        device_id: Device serial number
        adb_host: ADB server host (for FRP tunneling)
        adb_port: ADB server port (for FRP tunneling)

    Returns:
        True if successful, False otherwise.
    
    Example:
        >>> type_text("你好，世界！", device_id="device_6100")
        True
    """
    # 确保 yadb 已安装
    if not ensure_yadb_ready(device_id, adb_host, adb_port):
        logger.error("yadb not ready")
        return False
    
    cmd = _build_adb_cmd(device_id, adb_host, adb_port)
    
    # 预处理文本：空格需要转义
    processed_text = text.replace(" ", "\\ ")
    
    # 构建 yadb 命令
    cmd.extend([
        "shell",
        "app_process",
        "-Djava.class.path=/data/local/tmp/yadb",
        "/data/local/tmp",
        "com.ysbing.yadb.Main",
        "-keyboard",
        processed_text,
    ])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            logger.debug(f"Typed text via yadb: {text[:50]}...")
            return True
        else:
            logger.error(f"yadb type_text failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("yadb type_text timeout")
        return False
    except Exception as e:
        logger.error(f"yadb type_text error: {e}")
        return False


def force_screenshot(
    device_id: str = None, 
    adb_host: str = None, 
    adb_port: int = None,
    return_pil: bool = False,
    max_retries: int = 1  # 新增：最大重试次数（默认1次，即不重试）
) -> Optional[bytes | tuple]:
    """
    Capture screenshot using yadb (bypasses FLAG_SECURE).
    
    [WARN] **Key Feature**: This method can screenshot sensitive apps 
    (banking, payment, etc.) that normally block screenshots.
    
    Args:
        device_id: Device serial number
        adb_host: ADB server host (for FRP tunneling)
        adb_port: ADB server port (for FRP tunneling)
        return_pil: If True, returns (image_bytes, PIL.Image), else just bytes
        max_retries: Maximum number of retries (default: 1, no retry)
    
    Returns:
        PNG image bytes if successful, None if failed.
        If return_pil=True: (bytes, PIL.Image) tuple
    
    Example:
        >>> # Standard usage
        >>> png_data = force_screenshot(device_id="device_6100")
        >>> with open("screenshot.png", "wb") as f:
        ...     f.write(png_data)
        
        >>> # With retry
        >>> png_data = force_screenshot(device_id="device_6100", max_retries=3)
        
        >>> # Get both bytes and PIL Image
        >>> png_data, img = force_screenshot(device_id="device_6100", return_pil=True)
        >>> print(f"Size: {img.width}x{img.height}")
    """
    # 重试逻辑
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            logger.warning(f"yadb screenshot retry {attempt}/{max_retries}")
            # 重试前强制检查连接
            from phone_agent.adb.auto_reconnect import ensure_device_connected, clear_connection_cache
            clear_connection_cache()
            try:
                ensure_device_connected(device_id, force_check=True)
            except Exception as e:
                logger.error(f"Connection check failed on retry {attempt}: {e}")
                if attempt < max_retries:
                    import time
                    time.sleep(2)  # 等待2秒后重试
                    continue
                else:
                    return None
        
        result = _force_screenshot_single_attempt(
            device_id, adb_host, adb_port, return_pil
        )
        
        if result is not None:
            if attempt > 1:
                logger.info(f"✅ yadb screenshot succeeded on retry {attempt}")
            return result
        
        # 失败后清除缓存
        if attempt < max_retries:
            from phone_agent.adb.auto_reconnect import clear_connection_cache
            clear_connection_cache()
            # 清除 yadb 缓存
            cache_key = device_id or f"{adb_host}:{adb_port}"
            _yadb_check_cache.pop(cache_key, None)
            _cache_expiry.pop(cache_key, None)
            
            import time
            time.sleep(2)  # 等待2秒后重试
    
    logger.error(f"❌ yadb screenshot failed after {max_retries} attempts")
    return None


def _force_screenshot_single_attempt(
    device_id: str = None,
    adb_host: str = None,
    adb_port: int = None,
    return_pil: bool = False
) -> Optional[bytes | tuple]:
    """
    Single attempt of force screenshot (internal function).
    """
    if not ensure_yadb_ready(device_id, adb_host, adb_port):
        logger.error("yadb not ready for screenshot")
        return None
    
    cmd = _build_adb_cmd(device_id, adb_host, adb_port)
    
    # 🔥 使用唯一文件名避免并发冲突
    # 当多个截图请求同时执行时，固定文件名会导致文件被覆盖
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    screenshot_path = f"/data/local/tmp/yadb_screenshot_{unique_id}.png"
    logger.debug(f"Using unique screenshot path: {screenshot_path}")
    
    # 步骤 1: 运行 yadb 截图命令(会将截图保存到设备上)
    screenshot_cmd = cmd + [
        "shell",
        "app_process",
        "-Djava.class.path=/data/local/tmp/yadb",
        "/data/local/tmp",
        "com.ysbing.yadb.Main",
        "-screenshot",
    ]
    
    try:
        import time
        logger.debug("Executing yadb force screenshot...")
        start_time = time.time()
        
        # [OK] 减少超时时间，避免长时间卡住（从60秒降到30秒）
        # [OK] 添加更详细的错误信息
        try:
            result = subprocess.run(screenshot_cmd, capture_output=True, timeout=30)
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            logger.error(f"yadb screenshot timeout after {elapsed:.2f}s (limit: 30s)")
            logger.error("Possible causes: 1) Device not responding 2) yadb process stuck 3) Network issue")
            return None
        
        elapsed = time.time() - start_time
        logger.debug(f"yadb command completed in {elapsed:.2f}s")
        
        if result.returncode != 0:
            logger.error(f"yadb screenshot command failed (returncode={result.returncode})")
            # 解码输出用于日志（可能失败，但不影响主流程）
            try:
                stderr = result.stderr.decode('utf-8', errors='ignore')
                stdout = result.stdout.decode('utf-8', errors='ignore')
                logger.error(f"stderr: {stderr}")
                logger.error(f"stdout: {stdout}")
            except:
                pass
            return None
        
        # 检查输出（yadb 可能输出不同的成功信息）
        try:
            output = result.stdout.decode('utf-8', errors='ignore')
            output_lower = output.lower()
            if "success" not in output_lower and "screenshot" in output_lower:
                # yadb 可能只输出 "screenshot" 而没有 "success"
                logger.debug(f"yadb output: {output}")
            elif "success" not in output_lower:
                logger.warning(f"yadb screenshot may have failed, output: {output}")
                # 不直接返回，尝试读取文件看是否生成了
        except:
            # 解码失败，跳过输出检查，直接尝试读取文件
            logger.debug("Could not decode yadb output, checking file directly")
        
        logger.debug(f"yadb screenshot command completed, checking file: {screenshot_path}")
        
        # 步骤 2: 先检查文件是否存在
        check_cmd = cmd + ["shell", f"ls -l {screenshot_path}"]
        try:
            check_result = subprocess.run(check_cmd, capture_output=True, timeout=5, text=True)
        except subprocess.TimeoutExpired:
            logger.error(f"文件检查超时 (ls {screenshot_path})")
            logger.error("设备可能响应缓慢或连接不稳定")
            return None
        
        if check_result.returncode != 0 or "No such file" in check_result.stdout:
            logger.error(f"Screenshot file not found on device: {screenshot_path}")
            logger.debug(f"ls output: {check_result.stdout}")
            return None
        
        logger.debug(f"Screenshot file exists: {check_result.stdout.strip()}")
        
        # 步骤 3: 使用 adb exec-out cat 读取截图文件(避免换行符转换)
        # exec-out 比 shell 更适合传输二进制数据
        read_cmd = cmd + ["exec-out", f"cat {screenshot_path}"]
        try:
            result = subprocess.run(read_cmd, capture_output=True, timeout=10)
        except subprocess.TimeoutExpired:
            logger.error(f"读取截图文件超时 (cat {screenshot_path})")
            logger.error("可能原因：1) 文件过大 2) 网络延迟 3) 设备存储响应慢")
            # 尝试清理
            try:
                cleanup_cmd = cmd + ["shell", f"rm {screenshot_path}"]
                subprocess.run(cleanup_cmd, capture_output=True, timeout=3)
            except:
                pass
            return None
        
        if result.returncode != 0:
            logger.error(f"Failed to read screenshot file (returncode={result.returncode})")
            if result.stderr:
                logger.debug(f"stderr: {result.stderr.decode('utf-8', errors='ignore')}")
            return None
        
        png_data = result.stdout
        
        # 验证 PNG 数据
        if not png_data or len(png_data) < 100:
            logger.error(f"Screenshot data too small: {len(png_data)} bytes")
            # 尝试显示前100字节（可能是错误消息）
            if png_data:
                logger.debug(f"Data preview: {png_data[:100]}")
            return None
        
        if not png_data.startswith(b'\x89PNG'):
            logger.error(f"Invalid PNG data (magic number check failed)")
            logger.debug(f"Data starts with: {png_data[:20]}")
            return None
        
        logger.info(f"[OK] Force screenshot captured: {len(png_data)} bytes")
        
        # 步骤 4: 清理设备上的临时文件
        cleanup_cmd = cmd + ["shell", f"rm {screenshot_path}"]
        try:
            subprocess.run(cleanup_cmd, capture_output=True, timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning(f"清理临时文件超时，文件 {screenshot_path} 可能残留在设备上")
            # 清理失败不影响截图返回
        except Exception as e:
            logger.debug(f"清理临时文件失败: {e}")
            # 清理失败不影响截图返回
        
        # 如果需要返回 PIL Image
        if return_pil and PIL_AVAILABLE:
            try:
                img = Image.open(BytesIO(png_data))
                return (png_data, img)
            except Exception as e:
                logger.warning(f"Failed to create PIL Image: {e}, returning bytes only")
                return png_data
        
        return png_data
        
    except subprocess.TimeoutExpired:
        # [OK] 这个异常已经在上面处理了，这里是兜底
        logger.error("yadb screenshot timeout (outer catch)")
        return None
    except Exception as e:
        logger.error(f"yadb screenshot error: {e}", exc_info=True)
        return None


def force_screenshot_base64(
    device_id: str = None, 
    adb_host: str = None, 
    adb_port: int = None,
    include_dimensions: bool = False,
    max_retries: int = 1  # 新增：最大重试次数
) -> Optional[str | dict]:
    """
    Capture screenshot using yadb and return base64 encoded data.
    
    This is a convenience wrapper around force_screenshot() that returns
    base64 data ready for API responses or AI vision models.
    
    Args:
        device_id: Device serial number
        adb_host: ADB server host (for FRP tunneling)
        adb_port: ADB server port (for FRP tunneling)
        include_dimensions: If True, returns dict with base64 + width/height
        max_retries: Maximum number of retries (default: 1, no retry)
    
    Returns:
        Base64 string if include_dimensions=False
        Dict with {base64_data, width, height} if include_dimensions=True
        None if screenshot failed
    
    Example:
        >>> # Simple usage
        >>> b64 = force_screenshot_base64(device_id="device_6100")
        >>> print(f"data:image/png;base64,{b64}")
        
        >>> # With retry
        >>> b64 = force_screenshot_base64(device_id="device_6100", max_retries=3)
        
        >>> # With dimensions
        >>> data = force_screenshot_base64(device_id="device_6100", include_dimensions=True)
        >>> print(f"Size: {data['width']}x{data['height']}")
    """
    result = force_screenshot(
        device_id, adb_host, adb_port, 
        return_pil=PIL_AVAILABLE and include_dimensions,
        max_retries=max_retries
    )
    
    if result is None:
        return None
    
    # 处理返回值
    if isinstance(result, tuple):
        png_data, img = result
        base64_data = base64.b64encode(png_data).decode('utf-8')
        
        if include_dimensions:
            return {
                "base64_data": base64_data,
                "width": img.width,
                "height": img.height,
                "is_sensitive": False  # yadb 绕过了限制
            }
        return base64_data
    else:
        # 只有 bytes
        base64_data = base64.b64encode(result).decode('utf-8')
        
        if include_dimensions:
            if PIL_AVAILABLE:
                try:
                    img = Image.open(BytesIO(result))
                    return {
                        "base64_data": base64_data,
                        "width": img.width,
                        "height": img.height,
                        "is_sensitive": False
                    }
                except Exception as e:
                    logger.warning(f"Failed to get image dimensions: {e}")
                    # 无法获取尺寸，返回默认值
                    return {
                        "base64_data": base64_data,
                        "width": 1080,  # 默认值
                        "height": 2400,  # 默认值
                        "is_sensitive": False
                    }
            else:
                # PIL 不可用，返回默认尺寸
                return {
                    "base64_data": base64_data,
                    "width": 1080,
                    "height": 2400,
                    "is_sensitive": False
                }
        
        return base64_data


def long_press(
    x: int, 
    y: int, 
    duration_ms: int = 2000, 
    device_id: str = None, 
    adb_host: str = None, 
    adb_port: int = None
) -> bool:
    """
    Perform a long press at the specified coordinates using yadb.

    Args:
        x: X coordinate
        y: Y coordinate
        duration_ms: Duration in milliseconds (default: 2000)
        device_id: Device serial number
        adb_host: ADB server host (for FRP tunneling)
        adb_port: ADB server port (for FRP tunneling)

    Returns:
        True if successful, False otherwise.
    """
    if not ensure_yadb_ready(device_id, adb_host, adb_port):
        return False
    
    cmd = _build_adb_cmd(device_id, adb_host, adb_port)
    
    cmd.extend([
        "shell",
        "app_process",
        "-Djava.class.path=/data/local/tmp/yadb",
        "/data/local/tmp",
        "com.ysbing.yadb.Main",
        "-touch",
        str(x),
        str(y),
        str(duration_ms),
    ])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"yadb long_press error: {e}")
        return False


def read_clipboard(device_id: str = None, adb_host: str = None, adb_port: int = None) -> Optional[str]:
    """
    Read clipboard content from device using yadb.

    Args:
        device_id: Device serial number
        adb_host: ADB server host (for FRP tunneling)
        adb_port: ADB server port (for FRP tunneling)

    Returns:
        Clipboard content or None if failed.
    """
    if not ensure_yadb_ready(device_id, adb_host, adb_port):
        return None
    
    cmd = _build_adb_cmd(device_id, adb_host, adb_port)
    
    cmd.extend([
        "shell",
        "app_process",
        "-Djava.class.path=/data/local/tmp/yadb",
        "/data/local/tmp",
        "com.ysbing.yadb.Main",
        "-readClipboard",
    ])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception as e:
        logger.error(f"yadb read_clipboard error: {e}")
        return None


def write_clipboard(
    text: str, 
    device_id: str = None, 
    adb_host: str = None, 
    adb_port: int = None
) -> bool:
    """
    Write text to device clipboard using yadb.

    Args:
        text: Text to write
        device_id: Device serial number
        adb_host: ADB server host (for FRP tunneling)
        adb_port: ADB server port (for FRP tunneling)

    Returns:
        True if successful, False otherwise.
    """
    if not ensure_yadb_ready(device_id, adb_host, adb_port):
        return False
    
    cmd = _build_adb_cmd(device_id, adb_host, adb_port)
    
    cmd.extend([
        "shell",
        "app_process",
        "-Djava.class.path=/data/local/tmp/yadb",
        "/data/local/tmp",
        "com.ysbing.yadb.Main",
        "-writeClipboard",
        text,
    ])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"yadb write_clipboard error: {e}")
        return False


# [X] REMOVED: dump_layout() function
# Reason: Official yadb does NOT support `-layout` parameter
# This function never worked and always failed silently
# Use uiautomator dump instead (see ui_hierarchy.py)

