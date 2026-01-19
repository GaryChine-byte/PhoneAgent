#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
FRP 管理器 - 管理 FRP 客户端进程

负责 FRP 客户端的启动、停止和配置管理,实现内网穿透功能。
"""

import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class FrpManager:
    """FRP 客户端管理器"""
    
    def __init__(self, server_addr: str, server_port: int, token: str,
                 local_port: int, remote_port: int):
        self.server_addr = server_addr
        self.server_port = server_port
        self.token = token
        self.local_port = local_port
        self.remote_port = remote_port
        
        self.process: Optional[subprocess.Popen] = None
        self.config_file = "frpc.ini"
    
    def start(self):
        """启动 FRP 客户端"""
        try:
            # 1. 先停止旧的进程（避免冲突）
            self.stop()
            
            # 2. 生成配置文件
            self._generate_config()
            
            # 3. 获取 FRP 可执行文件路径
            frpc_path = self._get_frpc_path()
            
            # 4. 启动进程
            self.process = subprocess.Popen(
                [frpc_path, "-c", self.config_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            logger.info(f"FRP Client 启动成功 (PID: {self.process.pid})")
            logger.info(f"服务器: {self.server_addr}:{self.server_port}")
            logger.info(f"隧道: localhost:{self.local_port} -> {self.remote_port}")
        
        except Exception as e:
            logger.error(f"启动 FRP 失败: {e}", exc_info=True)
            raise
    
    def stop(self):
        """停止 FRP 客户端"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info("FRP Client 已停止")
            except subprocess.TimeoutExpired:
                self.process.kill()
                logger.warning("FRP Client 强制终止")
            except Exception as e:
                logger.error(f"停止 FRP 失败: {e}")
    
    def is_running(self) -> bool:
        """检查 FRP 是否运行中"""
        return self.process is not None and self.process.poll() is None
    
    def _generate_config(self):
        """生成 FRP 配置文件"""
        import socket
        
        # 使用主机名作为唯一标识，避免多客户端冲突
        hostname = socket.gethostname().replace('.', '_').replace('-', '_')
        proxy_name = f"pc_control_{hostname}_{self.remote_port}"
        
        config_content = f"""[common]
server_addr = {self.server_addr}
server_port = {self.server_port}
token = {self.token}
log_level = info

[{proxy_name}]
type = tcp
local_ip = 127.0.0.1
local_port = {self.local_port}
remote_port = {self.remote_port}
"""
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            f.write(config_content.strip())
        
        logger.info(f"FRP 配置文件已生成: {self.config_file} (代理名: {proxy_name})")
    
    def _get_frpc_path(self) -> str:
        """获取 FRP 客户端路径"""
        os_type = platform.system()
        bin_dir = Path(__file__).parent / "bin"
        
        if os_type == "Windows":
            frpc_path = bin_dir / "frpc.exe"
        elif os_type == "Darwin":
            frpc_path = bin_dir / "frpc_darwin"
        else:  # Linux
            frpc_path = bin_dir / "frpc_linux"
        
        if not frpc_path.exists():
            raise FileNotFoundError(
                f"FRP 客户端未找到: {frpc_path}\n"
                f"请从 https://github.com/fatedier/frp/releases 下载对应版本"
            )
        
        # Mac/Linux 需要添加执行权限
        if os_type != "Windows":
            os.chmod(frpc_path, 0o755)
        
        return str(frpc_path)
