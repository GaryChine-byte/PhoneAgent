#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
Scrcpy 管理器 - NAL 单元传输版
适配 FRP 内网穿透架构的实时预览方案

核心特性：
- 直接启动 scrcpy-server（而不是 scrcpy 命令）
- 通过 TCP socket 读取原始 H.264 流
- 按 NAL 单元边界传输（低延迟）
- 支持 FRP 端口映射环境
"""
import subprocess
import asyncio
import logging
import os
import socket
import threading
import queue
from typing import Optional, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class ScrcpySession:
    """
    Scrcpy 会话 - H.264 NAL 单元传输版
    
    核心改进：
    1. 移除 ffmpeg MJPEG 转码（降低延迟）
    2. 直接读取 scrcpy 的 H.264 输出
    3. 按 NAL 单元边界切分（确保前端解码器兼容）
    4. 缓存 SPS/PPS/IDR 初始化数据（新连接可立即播放）
    """
    
    def __init__(self, device_id: str):
        """
        初始化
        
        Args:
            device_id: 设备标识（FRP 模式下是 localhost:61XX 或 device_6100）
        """
        self.device_id = device_id
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        
        # TCP socket 连接（用于读取 H.264 流）
        self.tcp_socket: Optional[socket.socket] = None
        self.scrcpy_port = 27183  # 默认端口（会根据设备动态分配）
        
        # NAL 单元读取缓冲区（核心改进）
        self._nal_buffer = bytearray()
        self._read_thread: Optional[threading.Thread] = None
        self._nal_queue = queue.Queue(maxsize=60)  # NAL 单元队列（约2秒缓冲）
        
        # 缓存初始化数据（SPS + PPS + IDR）
        self.cached_sps: Optional[bytes] = None
        self.cached_pps: Optional[bytes] = None
        self.cached_idr: Optional[bytes] = None
        self._init_ready = threading.Event()
        
    def start(self, bitrate: int = 4_000_000, max_size: int = 1280, framerate: int = 30):
        """
        启动 Scrcpy 会话（使用 scrcpy-server + TCP socket）
        
        核心流程：
        1. 在 Android 设备上启动 scrcpy-server
        2. 设置 ADB 端口转发
        3. 通过 TCP socket 读取原始 H.264 NAL 单元流
        """
        if self.is_running:
            logger.warning(f"Session for {self.device_id} is already running")
            return
        
        try:
            logger.info(f" Starting scrcpy H.264 stream for device: {self.device_id}")
            # 转换 device_id 格式（device_6100 → localhost:6100）
            adb_address = self._get_adb_address()
            logger.info(f" ADB address: {adb_address}")
            # 步骤 1: 清理已有的 scrcpy server
            self._cleanup_existing_server(adb_address)
            
            # 步骤 2: 设置 ADB 端口转发（使用动态端口避免冲突）
            import random
            self.scrcpy_port = random.randint(27183, 27283)  # 随机端口
            self._setup_port_forward(adb_address)
            
            # 步骤 3: 启动 scrcpy server
            self._start_scrcpy_server(adb_address, bitrate, max_size, framerate)
            
            # 步骤 4: 连接 TCP socket
            self._connect_tcp_socket()
            
            self.is_running = True
            logger.info(f" Scrcpy H.264 stream started on port {self.scrcpy_port}")
            logger.info(f" Config: {max_size}p, {bitrate}bps, {framerate}fps")
            
            # 步骤 5: 启动 NAL 单元读取线程
            self._read_thread = threading.Thread(
                target=self._read_nal_units_from_socket,
                daemon=True
            )
            self._read_thread.start()
            
        except Exception as e:
            logger.error(f" Failed to start scrcpy: {e}", exc_info=True)
            self.stop()
            raise
    
    def _get_adb_address(self) -> str:
        """获取 ADB 地址"""
        # device_6100 → localhost:6100
        if self.device_id.startswith("device_"):
            port = self.device_id.replace("device_", "")
            return f"localhost:{port}"
        # 已经是 localhost:6100 格式
        return self.device_id
    
    def _cleanup_existing_server(self, adb_address: str):
        """清理已有的 scrcpy server 进程"""
        try:
            # 杀死已有的 scrcpy server
            cmd = ['adb', '-s', adb_address, 'shell', 'pkill', '-9', '-f', 'app_process.*scrcpy']
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
            logger.debug(f"✓ Cleaned up existing scrcpy server for {adb_address}")
        except:
            pass  # 忽略错误（可能没有正在运行的 server）
    
    def _setup_port_forward(self, adb_address: str):
        """设置 ADB 端口转发"""
        try:
            # 移除旧的端口转发
            cmd_remove = ['adb', '-s', adb_address, 'forward', '--remove', f'tcp:{self.scrcpy_port}']
            subprocess.run(cmd_remove, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
        except:
            pass
        
        # 设置新的端口转发
        cmd = ['adb', '-s', adb_address, 'forward', f'tcp:{self.scrcpy_port}', 'localabstract:scrcpy']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to setup port forward: {result.stderr}")
        
        logger.debug(f"✓ Port forward: {self.scrcpy_port} → localabstract:scrcpy")
    
    def _start_scrcpy_server(self, adb_address: str, bitrate: int, max_size: int, framerate: int):
        """启动 scrcpy server"""
        # 构建 scrcpy server 启动命令
        server_cmd = [
            'adb', '-s', adb_address, 'shell',
            'CLASSPATH=/data/local/tmp/scrcpy-server',
            'app_process', '/', 'com.genymobile.scrcpy.Server',
            '3.3.3',  # scrcpy 版本（需要与设备上的 scrcpy-server 版本匹配）
            f'max_size={max_size}',
            f'video_bit_rate={bitrate}',
            f'max_fps={framerate}',
            'tunnel_forward=true',  # 使用 ADB tunnel
            'audio=false',
            'control=false',
            'cleanup=false',
            'video_codec_options=i-frame-interval=1',  # 每秒一个 IDR 帧
        ]
        
        logger.info(f"📹 Starting scrcpy server: {' '.join(server_cmd)}")
        
        # 启动进程（后台运行）
        self.process = subprocess.Popen(
            server_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # 启动错误日志监控
        stderr_thread = threading.Thread(
            target=self._monitor_stderr,
            daemon=True
        )
        stderr_thread.start()
        
        # 等待 server 启动
        import time
        time.sleep(2)
        
        # 检查进程是否还在运行
        if self.process.poll() is not None:
            # 进程已退出
            stdout, stderr = self.process.communicate()
            error_msg = stderr.decode('utf-8', errors='ignore') if stderr else ''
            raise RuntimeError(f"Scrcpy server exited immediately: {error_msg}")
        
        logger.debug("✓ Scrcpy server started")
    
    def _connect_tcp_socket(self):
        """连接到 scrcpy TCP socket"""
        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.settimeout(5)
            
            # 增加 socket 缓冲区大小（高分辨率视频需要）
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 512 * 1024)  # 512KB
            
            # 连接到 scrcpy server
            self.tcp_socket.connect(('localhost', self.scrcpy_port))
            logger.debug(f"✓ Connected to TCP socket: localhost:{self.scrcpy_port}")
            
            # 读取并丢弃 scrcpy 的 meta 信息（64 字节）
            # scrcpy 协议：前 64 字节是设备信息（设备名称、分辨率等）
            meta_data = self.tcp_socket.recv(64)
            logger.debug(f"✓ Received meta data: {len(meta_data)} bytes")
            
        except Exception as e:
            raise RuntimeError(f"Failed to connect TCP socket: {e}")
    
    def _monitor_stderr(self):
        """监控 scrcpy 错误输出"""
        try:
            for line in iter(self.process.stderr.readline, b''):
                if line:
                    decoded = line.decode('utf-8', errors='ignore').strip()
                    if decoded and 'IClipboard' not in decoded:
                        logger.debug(f"[scrcpy] {decoded}")
        except Exception as e:
            logger.error(f"Error monitoring stderr: {e}")
    
    def _read_nal_units_from_socket(self):
        """
        从 TCP socket 读取 NAL 单元线程
        
        核心逻辑：
        1. 从 TCP socket 读取原始 H.264 数据
        2. 查找 NAL start codes (0x00 0x00 0x00 0x01)
        3. 按 start code 切分为完整 NAL 单元
        4. 缓存 SPS/PPS/IDR（用于新连接初始化）
        5. 放入队列供 WebSocket 发送
        """
        nal_count = 0
        try:
            logger.info(f"📹 NAL unit reader started for {self.device_id}")
            
            while self.is_running and self.tcp_socket:
                # 1. 从 TCP socket 读取数据块
                try:
                    chunk = self.tcp_socket.recv(16384)  # 16KB chunks
                    if not chunk:
                        logger.warning(f" No more data from scrcpy socket for {self.device_id}")
                        break
                except socket.timeout:
                    # Socket 超时，继续等待
                    continue
                except OSError as e:
                    # 处理文件描述符错误（例如连接关闭）
                    if e.errno == 9:  # Bad file descriptor
                        logger.warning(f" Socket closed for {self.device_id}")
                    else:
                        logger.error(f" Socket OS error: {e}")
                    break
                except Exception as e:
                    logger.error(f" Socket read error: {e}")
                    break
                
                # 2. 追加到缓冲区
                self._nal_buffer.extend(chunk)
                
                # 3. 提取完整 NAL 单元
                while True:
                    nal_unit = self._extract_nal_unit()
                    if not nal_unit:
                        break  # 需要更多数据
                    
                    # 4. 缓存 SPS/PPS/IDR
                    self._cache_parameter_sets(nal_unit)
                    
                    # 5. 放入队列
                    try:
                        self._nal_queue.put(nal_unit, block=False)
                        nal_count += 1
                        if nal_count % 100 == 0:
                            logger.debug(f" Processed {nal_count} NAL units")
                    except queue.Full:
                        # 队列满，丢弃旧帧
                        try:
                            self._nal_queue.get_nowait()
                            self._nal_queue.put(nal_unit, block=False)
                        except:
                            pass
        
        except Exception as e:
            logger.error(f" Error reading NAL units: {e}", exc_info=True)
        finally:
            logger.info(f"🛑 NAL reader stopped for {self.device_id}, total: {nal_count} NAL units")
    
    def _extract_nal_unit(self) -> Optional[bytes]:
        """
        从缓冲区提取一个完整 NAL 单元
        
        NAL start code 格式：
        - 0x00 0x00 0x00 0x01 (4字节)
        - 0x00 0x00 0x01 (3字节)
        
        返回：
            完整 NAL 单元（包含 start code），或 None（需要更多数据）
        """
        buffer = bytes(self._nal_buffer)
        
        # 查找所有 start codes
        start_positions = []
        i = 0
        while i < len(buffer) - 3:
            if buffer[i:i+4] == b'\x00\x00\x00\x01':
                start_positions.append(i)
                i += 4
            elif buffer[i:i+3] == b'\x00\x00\x01':
                start_positions.append(i)
                i += 3
            else:
                i += 1
        
        # 需要至少 2 个 start code 才能提取完整 NAL
        if len(start_positions) < 2:
            return None
        
        # 提取第一个 NAL 单元
        nal_unit = buffer[start_positions[0]:start_positions[1]]
        
        # 从缓冲区移除已提取的数据
        self._nal_buffer = bytearray(buffer[start_positions[1]:])
        
        return nal_unit
    
    def _cache_parameter_sets(self, nal_unit: bytes):
        """
        缓存 SPS/PPS/IDR 参数集
        
        NAL 类型（第5字节的低5位）：
        - 7: SPS (Sequence Parameter Set)
        - 8: PPS (Picture Parameter Set)
        - 5: IDR (Instantaneous Decoding Refresh)
        """
        if len(nal_unit) < 5:
            return
        
        # 跳过 start code，读取 NAL 类型
        start_code_len = 4 if nal_unit[:4] == b'\x00\x00\x00\x01' else 3
        nal_type = nal_unit[start_code_len] & 0x1F
        
        # 缓存 SPS（只缓存第一个）
        if nal_type == 7 and not self.cached_sps:
            self.cached_sps = nal_unit
            logger.info(f"✓ Cached SPS: {len(nal_unit)} bytes")
        
        # 缓存 PPS（只缓存第一个）
        elif nal_type == 8 and not self.cached_pps:
            self.cached_pps = nal_unit
            logger.info(f"✓ Cached PPS: {len(nal_unit)} bytes")
        
        # 缓存 IDR（更新为最新的）
        elif nal_type == 5:
            if self.cached_sps and self.cached_pps:
                if not self.cached_idr:
                    logger.info(f"✓ Cached first IDR: {len(nal_unit)} bytes")
                self.cached_idr = nal_unit
                # 标记初始化数据就绪
                if not self._init_ready.is_set():
                    self._init_ready.set()
                    logger.info(" Init data ready (SPS + PPS + IDR)")
    
    def get_init_data(self) -> Optional[bytes]:
        """
        获取初始化数据（SPS + PPS + IDR）
        
        新连接必须先接收这些数据才能开始解码
        """
        if self.cached_sps and self.cached_pps and self.cached_idr:
            return self.cached_sps + self.cached_pps + self.cached_idr
        return None
    
    def wait_for_init_data(self, timeout: float = 10.0) -> bool:
        """等待初始化数据就绪"""
        return self._init_ready.wait(timeout)
    
    def get_nal_unit(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        获取一个 NAL 单元（用于 WebSocket 发送）
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            NAL 单元数据，或 None（超时/队列空）
        """
        try:
            return self._nal_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def stop(self):
        """停止 Scrcpy 会话"""
        self.is_running = False
        
        # 关闭 TCP socket
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except:
                pass
            finally:
                self.tcp_socket = None
        
        # 终止进程
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                logger.error(f"Error stopping scrcpy: {e}")
            finally:
                self.process = None
        
        # 清理端口转发
        try:
            adb_address = self._get_adb_address()
            cmd = ['adb', '-s', adb_address, 'forward', '--remove', f'tcp:{self.scrcpy_port}']
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
        except:
            pass
        
        # 等待读取线程结束
        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=2)
        
        logger.info(f"Scrcpy session stopped for {self.device_id}")


class ScrcpyManager:
    """Scrcpy 管理器（全局单例）"""
    
    def __init__(self):
        self.sessions: Dict[str, ScrcpySession] = {}
        self._lock = threading.Lock()
    
    def start_session(self, device_id: str, **kwargs) -> ScrcpySession:
        """为设备启动 Scrcpy 会话"""
        with self._lock:
            # 如果已有会话，先停止
            if device_id in self.sessions:
                logger.info(f"Stopping existing session for {device_id}")
                self.stop_session(device_id)
            
            session = ScrcpySession(device_id)
            session.start(**kwargs)
            self.sessions[device_id] = session
            return session
    
    def stop_session(self, device_id: str):
        """停止设备的 Scrcpy 会话"""
        with self._lock:
            if device_id in self.sessions:
                self.sessions[device_id].stop()
                del self.sessions[device_id]
    
    def get_session(self, device_id: str) -> Optional[ScrcpySession]:
        """获取设备的 Scrcpy 会话"""
        return self.sessions.get(device_id)
    
    def stop_all(self):
        """停止所有会话"""
        with self._lock:
            for session in list(self.sessions.values()):
                session.stop()
            self.sessions.clear()


# 全局单例
_scrcpy_manager = None

def get_scrcpy_manager() -> ScrcpyManager:
    """获取全局 Scrcpy 管理器"""
    global _scrcpy_manager
    if _scrcpy_manager is None:
        _scrcpy_manager = ScrcpyManager()
    return _scrcpy_manager

