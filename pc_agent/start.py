#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
PC Agent 启动脚本

快速启动 PC Agent 客户端的便捷脚本。
"""

import asyncio
import logging
import sys
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('pc_agent.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def check_dependencies():
    """检查依赖是否安装"""
    missing = []
    
    try:
        import yaml
    except ImportError:
        missing.append("pyyaml")
    
    try:
        import aiohttp
    except ImportError:
        missing.append("aiohttp")
    
    try:
        import websockets
    except ImportError:
        missing.append("websockets")
    
    try:
        import pyautogui
    except ImportError:
        missing.append("pyautogui")
    
    if missing:
        logger.error(f"缺少依赖: {', '.join(missing)}")
        logger.error("请运行: pip install -r requirements.txt")
        return False
    
    return True


def check_config():
    """检查配置文件是否存在"""
    config_file = Path("config.yaml")
    if not config_file.exists():
        logger.error("配置文件不存在: config.yaml")
        logger.error("请复制 config.yaml.example 并修改配置")
        logger.error("命令: cp config.yaml.example config.yaml")
        return False
    
    return True


def check_frp_client():
    """检查 FRP 客户端是否存在"""
    import platform
    
    os_type = platform.system()
    bin_dir = Path("bin")
    
    if os_type == "Windows":
        frpc_path = bin_dir / "frpc.exe"
    elif os_type == "Darwin":
        frpc_path = bin_dir / "frpc_darwin"
    else:
        frpc_path = bin_dir / "frpc_linux"
    
    if not frpc_path.exists():
        logger.warning(f"FRP 客户端未找到: {frpc_path}")
        logger.warning("请从 https://github.com/fatedier/frp/releases 下载")
        logger.warning(f"并放置到 {bin_dir} 目录")
        return False
    
    return True


async def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info(" PC Agent 客户端启动")
    logger.info("=" * 60)
    
    # 检查依赖
    logger.info("检查依赖...")
    if not check_dependencies():
        sys.exit(1)
    logger.info("依赖检查通过")
    
    # 检查配置
    logger.info("检查配置...")
    if not check_config():
        sys.exit(1)
    logger.info("配置检查通过")
    
    # 检查 FRP 客户端
    logger.info("检查 FRP 客户端...")
    if not check_frp_client():
        logger.warning("FRP 客户端未找到,将尝试继续运行")
    else:
        logger.info("FRP 客户端检查通过")
    
    # 导入并启动客户端
    try:
        from pc_agent_client import PCAgentClient
        
        logger.info("启动 PC Agent 客户端...")
        client = PCAgentClient("config.yaml")
        await client.start()
    
    except KeyboardInterrupt:
        logger.info("收到停止信号,正在退出...")
    except Exception as e:
        logger.error(f"启动失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序已停止")
