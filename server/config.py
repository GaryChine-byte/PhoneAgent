#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
配置管理模块

支持从 .env 文件或环境变量加载配置
"""

import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# 尝试加载 .env 文件
try:
    from dotenv import load_dotenv
    
    # 查找 .env 文件
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    env_path = project_root / ".env"
    
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"已加载配置文件: {env_path}")
    else:
        logger.info(f"未找到 .env 文件: {env_path}")
        logger.info(f"使用系统环境变量或创建 .env 文件")
except ImportError:
    logger.warning("未安装 python-dotenv，仅使用系统环境变量")
    logger.info("安装方法: pip install python-dotenv")


class Config:
    """
    全局配置类
    
    配置优先级:
    1. 环境变量
    2. .env 文件
    3. 默认值
    """
    
    # ============================================
    # CORS 配置
    # ============================================
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    
    # ============================================
    # AI 模型配置
    # ============================================
    
    # 智谱AI (默认)
    ZHIPU_API_KEY: str = os.getenv("ZHIPU_API_KEY", "")
    
    # 模型提供商配置（支持多平台）
    # 支持: zhipu, openai, gemini, qwen
    MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "zhipu")
    
    # 自定义 base_url（覆盖默认值）
    # 如果不设置，会根据 MODEL_PROVIDER 自动选择
    CUSTOM_BASE_URL: Optional[str] = os.getenv("CUSTOM_BASE_URL")
    
    # 自定义 API Key（用于非智谱AI的平台）
    # 优先级: CUSTOM_API_KEY > ZHIPU_API_KEY
    CUSTOM_API_KEY: Optional[str] = os.getenv("CUSTOM_API_KEY")
    
    # 自定义默认模型名称
    # 如果不设置，会使用智能模型选择器
    CUSTOM_MODEL_NAME: Optional[str] = os.getenv("CUSTOM_MODEL_NAME")
    
    # ============================================
    # 语音识别配置（独立于模型API）
    # ============================================
    
    # 智谱AI语音识别API Key（可选，与ZHIPU_API_KEY可不同）
    # 如果未设置，则使用ZHIPU_API_KEY
    ZHIPU_SPEECH_API_KEY: str = os.getenv("ZHIPU_SPEECH_API_KEY", "")
    
    # Fish Audio API Key（暂未开放，预留）
    # FISHAUDIO_API_KEY: str = os.getenv("FISHAUDIO_API_KEY", "")
    
    # 模型配置参数（通用）
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "3000"))  # 调整为3000（推荐值）
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))
    
    # 任务执行配置
    MAX_TASK_STEPS: int = int(os.getenv("MAX_TASK_STEPS", "100"))  # 默认最大执行步数
    
    # ============================================
    # 服务器配置
    # ============================================
    
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    FRP_PORT: int = int(os.getenv("FRP_PORT", "7000"))
    WEBSOCKET_PORT: int = int(os.getenv("WEBSOCKET_PORT", "9999"))
    
    # ============================================
    # 设备配置
    # ============================================
    
    MAX_DEVICES: int = int(os.getenv("MAX_DEVICES", "100"))  # 支持100台设备
    HEALTH_CHECK_INTERVAL: int = int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))
    
    
    # ============================================
    # 日志配置
    # ============================================
    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/phoneagent.log")
    
    # ============================================
    # 高级配置
    # ============================================
    
    YADB_PATH: Optional[str] = os.getenv("YADB_PATH")
    ADB_TIMEOUT: int = int(os.getenv("ADB_TIMEOUT", "30"))
    SCREENSHOT_TIMEOUT: int = int(os.getenv("SCREENSHOT_TIMEOUT", "30"))
    TASK_TIMEOUT: int = int(os.getenv("TASK_TIMEOUT", "300"))
    
    @classmethod
    def validate(cls, verbose: bool = True, logger: Optional[logging.Logger] = None) -> bool:
        """
        验证配置
        
        Args:
            verbose: 是否打印详细信息（使用print，向后兼容）
            logger: 日志记录器（推荐使用），如果提供则优先使用
        
        Returns:
            是否验证通过
        """
        errors = []
        warnings = []
        
        # 检查 API Key（根据提供商检查）
        if cls.MODEL_PROVIDER == "zhipu" and not cls.ZHIPU_API_KEY and not cls.CUSTOM_API_KEY:
            errors.append("ZHIPU_API_KEY 或 CUSTOM_API_KEY 未设置")
        elif cls.MODEL_PROVIDER != "zhipu" and cls.MODEL_PROVIDER != "local" and not cls.CUSTOM_API_KEY:
            warnings.append(f"使用 {cls.MODEL_PROVIDER} 但未设置 CUSTOM_API_KEY")
        
        # 检查其他配置
        if cls.MAX_DEVICES < 1:
            errors.append(f"MAX_DEVICES 必须 >= 1 (当前: {cls.MAX_DEVICES})")
        
        if cls.MAX_TOKENS < 512:
            warnings.append(f"MAX_TOKENS 过小 (当前: {cls.MAX_TOKENS}，建议 >= 1024)")
        
        # 打印结果（优先使用logger，否则使用print向后兼容）
        if logger:
            if not errors and not warnings:
                logger.info("配置验证通过")
                logger.info(f"最大设备数: {cls.MAX_DEVICES}")
                logger.info("模型会根据任务自动选择（智能选择器）")
            else:
                if errors:
                    logger.error("配置验证失败:")
                    for error in errors:
                        logger.error(f"• {error}")
                
                if warnings:
                    logger.warning("配置警告:")
                    for warning in warnings:
                        logger.warning(f"• {warning}")
        elif verbose:
            if not errors and not warnings:
                print("配置验证通过")
                print(f"最大设备数: {cls.MAX_DEVICES}")
                print(f"模型会根据任务自动选择（智能选择器）")
            else:
                if errors:
                    print("配置验证失败:")
                    for error in errors:
                        print(f"• {error}")
                
                if warnings:
                    print("配置警告:")
                    for warning in warnings:
                        print(f"• {warning}")
        
        return len(errors) == 0
    
    @classmethod
    def print_config(cls, logger: Optional[logging.Logger] = None):
        """
        打印当前配置（隐藏敏感信息）
        
        Args:
            logger: 日志记录器（推荐使用），如果提供则使用logger，否则使用print
        """
        def mask_key(key: str) -> str:
            """隐藏 API Key"""
            if not key:
                return "未设置"
            return f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
        
        lines = [
            "\n" + "="*60,
            "  当前配置",
            "="*60,
            "",
            "【AI 模型】",
            "  提供商: zhipu",
            "  模型: 智能选择（根据任务内核自动匹配）",
            f"  Zhipu API Key: {mask_key(cls.ZHIPU_API_KEY)}",
            f"  Max Tokens: {cls.MAX_TOKENS}",
            f"  Temperature: {cls.TEMPERATURE}",
            "",
            "【服务器】",
            f"  监听地址: {cls.SERVER_HOST}",
            f"  FRP 端口: {cls.FRP_PORT}",
            f"  WebSocket 端口: {cls.WEBSOCKET_PORT}",
            "",
            "【设备】",
            f"  最大设备数: {cls.MAX_DEVICES}",
            f"  健康检查间隔: {cls.HEALTH_CHECK_INTERVAL}s",
            "",
            "【高级】",
            f"  yadb 路径: {cls.YADB_PATH or '未配置'}",
            f"  ADB 超时: {cls.ADB_TIMEOUT}s",
            f"  截图超时: {cls.SCREENSHOT_TIMEOUT}s",
            f"  任务超时: {cls.TASK_TIMEOUT}s",
            "",
            "="*60 + "\n"
        ]
        
        if logger:
            for line in lines:
                if line:
                    logger.info(line)
        else:
            for line in lines:
                print(line)


# 全局配置实例
config = Config()


if __name__ == "__main__":
    # 测试配置
    print("PhoneAgent 配置管理\n")
    
    # 打印当前配置
    config.print_config()
    
    # 验证配置
    if config.validate():
        print("\n配置验证通过！")
        print("\n提示: 模型会根据任务内核自动选择（XML/Vision/Planning）")
        print("详见: phone_agent.model.selector.select_model_for_kernel()")
    else:
        print("\n请先配置 API Key！")
    print("方法 1: 设置环境变量")
    print("  export ZHIPU_API_KEY='your_key'")
    print("\n方法 2: 创建 .env 文件")
    print("  cp env.example .env")
    print("  # 然后编辑 .env 文件填入 API Key")

