#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
统一日志配置模块

功能：
1. 配置全局日志系统
2. 同时输出到控制台和文件
3. 按日期轮转日志文件
4. 支持不同模块的日志级别
5. 美化的日志格式
"""

import os
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """带颜色的控制台日志格式化器"""
    
    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # 添加颜色
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        
        return super().format(record)


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    log_file: str = "phoneagent.log",
    enable_console: bool = True,
    enable_file: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 10
):
    """
    配置全局日志系统
    
    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: 日志目录
        log_file: 日志文件名
        enable_console: 是否输出到控制台
        enable_file: 是否输出到文件
        max_bytes: 单个日志文件最大大小（字节）
        backup_count: 保留的历史日志文件数量
    """
    # 确保日志目录存在
    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(parents=True, exist_ok=True)
    
    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除现有的处理器
    root_logger.handlers.clear()
    
    # 日志格式
    # 控制台格式（简洁）
    console_format = "%(asctime)s - %(name)-25s - %(levelname)-8s - %(message)s"
    console_date_format = "%H:%M:%S"
    
    # 文件格式（详细）
    file_format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    file_date_format = "%Y-%m-%d %H:%M:%S"
    
    # 1. 控制台处理器（带颜色）
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_formatter = ColoredFormatter(
            console_format,
            datefmt=console_date_format
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # 2. 文件处理器（轮转）
    if enable_file:
        log_file_path = log_dir_path / log_file
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
        file_formatter = logging.Formatter(
            file_format,
            datefmt=file_date_format
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # 3. 错误日志单独文件
    if enable_file:
        error_log_path = log_dir_path / "error.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)  # 只记录ERROR及以上
        error_formatter = logging.Formatter(
            file_format,
            datefmt=file_date_format
        )
        error_handler.setFormatter(error_formatter)
        root_logger.addHandler(error_handler)
    
    # 配置特定模块的日志级别
    # 降低一些第三方库的日志级别，避免噪音
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)
    
    # 记录日志系统初始化信息
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info(" 日志系统已初始化")
    logger.info(f"   日志级别: {log_level}")
    logger.info(f"   日志目录: {log_dir_path.absolute()}")
    if enable_file:
        logger.info(f"   主日志文件: {log_file}")
        logger.info(f"   错误日志文件: error.log")
    logger.info(f"   文件轮转: {max_bytes / 1024 / 1024:.0f}MB, 保留{backup_count}个")
    logger.info("=" * 60)


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称（通常是模块名）
    
    Returns:
        logging.Logger 实例
    """
    return logging.getLogger(name)


# 请求日志中间件辅助函数
def log_request(method: str, path: str, status_code: int, duration: float, error: Optional[str] = None):
    """
    记录API请求日志
    
    Args:
        method: HTTP方法
        path: 请求路径
        status_code: 状态码
        duration: 耗时（秒）
        error: 错误信息（如果有）
    """
    logger = logging.getLogger("api.request")
    
    # 根据状态码选择日志级别
    if status_code >= 500:
        level = logging.ERROR
    elif status_code >= 400:
        level = logging.WARNING
    else:
        level = logging.INFO
    
    # 格式化耗时
    duration_ms = duration * 1000
    
    # 记录日志
    if error:
        logger.log(level, f"{method} {path} - {status_code} - {duration_ms:.0f}ms - ERROR: {error}")
    else:
        logger.log(level, f"{method} {path} - {status_code} - {duration_ms:.0f}ms")


def log_exception(logger: logging.Logger, message: str, exc_info=True):
    """
    记录异常日志（带堆栈跟踪）
    
    Args:
        logger: 日志记录器
        message: 错误描述
        exc_info: 是否包含异常堆栈信息
    """
    logger.error(message, exc_info=exc_info)


# 示例：按模块配置不同的日志级别
def configure_module_loggers():
    """
    配置各模块的日志级别（可选）
    """
    # 核心业务逻辑 - INFO
    logging.getLogger("server.api").setLevel(logging.INFO)
    logging.getLogger("server.services").setLevel(logging.INFO)
    
    # 设备管理 - INFO
    logging.getLogger("server.services.device_scanner").setLevel(logging.INFO)
    logging.getLogger("server.services.device_pool").setLevel(logging.INFO)
    
    # Agent执行 - DEBUG（更详细）
    logging.getLogger("server.services.agent_service").setLevel(logging.DEBUG)
    
    # ADB操作 - INFO
    logging.getLogger("phone_agent.adb").setLevel(logging.INFO)
    
    # 中间件 - INFO
    logging.getLogger("server.middleware").setLevel(logging.INFO)


if __name__ == "__main__":
    # 测试日志系统
    setup_logging(log_level="DEBUG")
    
    logger = get_logger(__name__)
    
    logger.debug("这是DEBUG级别日志")
    logger.info("这是INFO级别日志")
    logger.warning("这是WARNING级别日志")
    logger.error("这是ERROR级别日志")
    
    # 测试异常日志
    try:
        raise ValueError("这是一个测试异常")
    except Exception as e:
        log_exception(logger, "捕获到测试异常")
    
    # 测试请求日志
    log_request("GET", "/api/v1/tasks", 200, 0.123)
    log_request("POST", "/api/v1/tasks", 500, 1.456, "Internal Server Error")
    
    print("\n日志文件已生成在 logs/ 目录")

