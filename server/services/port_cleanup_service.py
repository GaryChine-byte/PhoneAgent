#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
端口清理服务 - 自动清理僵尸端口和进程

功能：
1. 定期检查端口占用情况
2. 识别僵尸进程（FRP 客户端已断开但端口仍被占用）
3. 强制清理无效的端口占用
4. 同步更新 PortManager 和 DeviceScanner
"""

import asyncio
import logging
import subprocess
import re
from typing import Dict, List, Set, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PortCleanupService:
    """端口清理服务"""
    
    def __init__(
        self,
        port_range_start: int = 6100,
        port_range_end: int = 6299,
        cleanup_interval: int = 300,  # 5 分钟清理一次
        zombie_timeout: int = 600  # 10 分钟无活动视为僵尸
    ):
        self.port_range_start = port_range_start
        self.port_range_end = port_range_end
        self.cleanup_interval = cleanup_interval
        self.zombie_timeout = zombie_timeout
        
        self.is_running = False
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # 端口最后活动时间 {port: datetime}
        self.port_last_active: Dict[int, datetime] = {}
        
        logger.info(f"[PortCleanup] 初始化完成，端口范围: {port_range_start}-{port_range_end}")
    
    async def get_listening_ports(self) -> Dict[int, Dict]:
        """
        获取所有监听的端口及其进程信息
        
        Returns:
            {port: {"pid": pid, "program": program_name}}
        """
        ports = {}
        
        try:
            # 使用 ss 命令（比 netstat 更快）
            result = subprocess.run(
                ["ss", "-tlnp"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # 解析输出
            for line in result.stdout.split('\n'):
                # 查找端口范围内的监听端口
                for port in range(self.port_range_start, self.port_range_end + 1):
                    if f":{port}" in line and "LISTEN" in line:
                        # 提取进程信息
                        pid_match = re.search(r'pid=(\d+)', line)
                        program_match = re.search(r'users:\(\("([^"]+)"', line)
                        
                        ports[port] = {
                            "pid": int(pid_match.group(1)) if pid_match else None,
                            "program": program_match.group(1) if program_match else "unknown"
                        }
                        break
        
        except subprocess.TimeoutExpired:
            logger.warning("[PortCleanup] ss 命令超时")
        except FileNotFoundError:
            # ss 命令不存在，尝试 netstat
            try:
                result = subprocess.run(
                    ["netstat", "-tlnp"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                for line in result.stdout.split('\n'):
                    for port in range(self.port_range_start, self.port_range_end + 1):
                        if f":{port}" in line and "LISTEN" in line:
                            # 提取进程信息
                            parts = line.split()
                            if len(parts) >= 7:
                                pid_program = parts[6]
                                if '/' in pid_program:
                                    pid_str, program = pid_program.split('/', 1)
                                    try:
                                        ports[port] = {
                                            "pid": int(pid_str),
                                            "program": program
                                        }
                                    except ValueError:
                                        pass
                            break
            
            except Exception as e:
                logger.error(f"[PortCleanup] netstat 命令失败: {e}")
        
        except Exception as e:
            logger.error(f"[PortCleanup] 获取端口信息失败: {e}")
        
        return ports
    
    async def get_active_devices(self) -> Set[int]:
        """
        获取活跃设备的端口列表
        
        从 WebSocket 和 DeviceScanner 获取
        """
        active_ports = set()
        
        # 1. 从 WebSocket DeviceManager 获取
        try:
            from server.websocket.server import get_device_manager
            device_manager = get_device_manager()
            
            for device_id, device_info in device_manager.devices.items():
                if device_info.frp_port:
                    # 检查设备是否真的在线
                    if device_id in device_manager.connections:
                        active_ports.add(device_info.frp_port)
                        self.port_last_active[device_info.frp_port] = datetime.now()
        
        except Exception as e:
            logger.debug(f"[PortCleanup] 无法从 WebSocket 获取设备: {e}")
        
        # 2. 从 DeviceScanner 获取
        try:
            from server.services.device_scanner import get_device_scanner
            scanner = get_device_scanner()
            
            online_devices = scanner.get_online_devices()
            for device_id, device in online_devices.items():
                if device.is_online and device.frp_port:
                    active_ports.add(device.frp_port)
                    self.port_last_active[device.frp_port] = datetime.now()
        
        except Exception as e:
            logger.debug(f"[PortCleanup] 无法从 DeviceScanner 获取设备: {e}")
        
        return active_ports
    
    async def identify_zombie_ports(self) -> List[int]:
        """
        识别僵尸端口
        
        僵尸端口的特征：
        1. 端口被占用（有进程监听）
        2. 但没有活跃的设备连接
        3. 超过 zombie_timeout 时间无活动
        """
        zombie_ports = []
        
        # 获取所有监听的端口
        listening_ports = await self.get_listening_ports()
        
        # 获取活跃设备的端口
        active_ports = await self.get_active_devices()
        
        # 识别僵尸端口
        now = datetime.now()
        for port, info in listening_ports.items():
            # 端口被占用但不在活跃列表中
            if port not in active_ports:
                # 检查最后活动时间
                last_active = self.port_last_active.get(port)
                
                if last_active is None:
                    # 第一次发现，记录时间
                    self.port_last_active[port] = now
                elif (now - last_active).total_seconds() > self.zombie_timeout:
                    # 超时，标记为僵尸
                    zombie_ports.append(port)
                    logger.warning(
                        f"[PortCleanup] 发现僵尸端口: {port} "
                        f"(PID: {info['pid']}, 程序: {info['program']}, "
                        f"无活动时间: {int((now - last_active).total_seconds())}秒)"
                    )
        
        return zombie_ports
    
    async def kill_process_by_port(self, port: int) -> bool:
        """
        通过端口号杀死占用进程
        
        Args:
            port: 端口号
            
        Returns:
            是否成功
        """
        try:
            # 1. 查找占用端口的进程
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True,
                timeout=3
            )
            
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                
                for pid in pids:
                    try:
                        pid = int(pid.strip())
                        logger.info(f"[PortCleanup] 杀死进程 PID={pid} (端口 {port})")
                        
                        # 先尝试 SIGTERM（优雅退出）
                        subprocess.run(["kill", str(pid)], timeout=2)
                        await asyncio.sleep(1)
                        
                        # 检查进程是否还在
                        check = subprocess.run(
                            ["kill", "-0", str(pid)],
                            capture_output=True,
                            timeout=1
                        )
                        
                        if check.returncode == 0:
                            # 进程还在，使用 SIGKILL（强制杀死）
                            logger.warning(f"[PortCleanup] 强制杀死进程 PID={pid}")
                            subprocess.run(["kill", "-9", str(pid)], timeout=2)
                    
                    except ValueError:
                        continue
                    except Exception as e:
                        logger.error(f"[PortCleanup] 杀死进程失败 PID={pid}: {e}")
                
                return True
        
        except FileNotFoundError:
            # lsof 不存在，尝试 fuser
            try:
                result = subprocess.run(
                    ["fuser", "-k", f"{port}/tcp"],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                logger.info(f"[PortCleanup] 使用 fuser 清理端口 {port}")
                return True
            
            except Exception as e:
                logger.error(f"[PortCleanup] fuser 命令失败: {e}")
        
        except Exception as e:
            logger.error(f"[PortCleanup] 清理端口 {port} 失败: {e}")
        
        return False
    
    async def cleanup_zombie_ports(self):
        """清理僵尸端口"""
        zombie_ports = await self.identify_zombie_ports()
        
        if not zombie_ports:
            logger.debug("[PortCleanup] 没有发现僵尸端口")
            return
        
        logger.info(f"[PortCleanup] 发现 {len(zombie_ports)} 个僵尸端口，开始清理...")
        
        cleaned_count = 0
        for port in zombie_ports:
            if await self.kill_process_by_port(port):
                cleaned_count += 1
                
                # 从记录中删除
                if port in self.port_last_active:
                    del self.port_last_active[port]
                
                # 通知 PortManager 释放端口
                try:
                    from server.services.port_manager import get_port_manager
                    port_manager = get_port_manager()
                    await port_manager.release_port(port=port)
                except Exception as e:
                    logger.debug(f"[PortCleanup] 释放端口 {port} 失败: {e}")
        
        logger.info(f"[PortCleanup] 清理完成: 成功清理 {cleaned_count}/{len(zombie_ports)} 个僵尸端口")
    
    async def cleanup_loop(self):
        """清理循环"""
        logger.info(f"[PortCleanup] 开始自动清理（间隔 {self.cleanup_interval} 秒）...")
        
        while self.is_running:
            try:
                await self.cleanup_zombie_ports()
                await asyncio.sleep(self.cleanup_interval)
            
            except Exception as e:
                logger.error(f"[PortCleanup] 清理出错: {e}", exc_info=True)
                await asyncio.sleep(self.cleanup_interval)
    
    async def start(self):
        """启动清理服务"""
        if self.is_running:
            logger.warning("[PortCleanup] 清理服务已在运行")
            return
        
        self.is_running = True
        self.cleanup_task = asyncio.create_task(self.cleanup_loop())
        logger.info("[PortCleanup] 清理服务已启动")
    
    async def stop(self):
        """停止清理服务"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("[PortCleanup] 清理服务已停止")
    
    async def force_cleanup_all(self):
        """强制清理所有端口（危险操作，仅用于紧急情况）"""
        logger.warning("[PortCleanup] 执行强制清理所有端口...")
        
        listening_ports = await self.get_listening_ports()
        
        for port in listening_ports:
            logger.info(f"[PortCleanup] 强制清理端口 {port}")
            await self.kill_process_by_port(port)
        
        logger.info("[PortCleanup] 强制清理完成")


# 全局单例
_port_cleanup_service: Optional[PortCleanupService] = None


def get_port_cleanup_service() -> PortCleanupService:
    """获取端口清理服务单例"""
    global _port_cleanup_service
    if _port_cleanup_service is None:
        _port_cleanup_service = PortCleanupService()
    return _port_cleanup_service
