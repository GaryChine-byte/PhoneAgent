#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
模型配置辅助工具

根据环境变量自动生成模型配置，支持多平台切换
"""

import os
import logging
from typing import Dict, Any, Optional
from server.config import Config

logger = logging.getLogger(__name__)


# 平台默认配置
PROVIDER_DEFAULTS = {
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "default_model": "autoglm-phone"  # 官方推荐，针对手机优化
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o"
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-2.0-flash"  # 稳定版，推荐使用
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-vl-plus"  # 视觉理解模型
    }
}


def get_model_config_from_env(kernel_mode: Optional[str] = None) -> Dict[str, Any]:
    """
    从环境变量获取模型配置
    
    Args:
        kernel_mode: 内核模式（xml, vision, planning, auto）
                    如果提供，会使用智能模型选择器
    
    Returns:
        模型配置字典 {base_url, api_key, model_name}
    
    Example:
        # 使用默认提供商（智谱AI）
        config = get_model_config_from_env("vision")
        # 返回: {
        #     "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        #     "api_key": "your_zhipu_key",
        #     "model_name": "autoglm-phone"
        # }
        
        # 切换到 OpenAI（设置环境变量 MODEL_PROVIDER=openai）
        config = get_model_config_from_env("vision")
        # 返回: {
        #     "base_url": "https://api.openai.com/v1",
        #     "api_key": "sk-proj-xxxxx",
        #     "model_name": "gpt-4o"
        # }
    """
    provider = Config.MODEL_PROVIDER.lower()
    
    # 1. 确定 base_url
    if Config.CUSTOM_BASE_URL:
        base_url = Config.CUSTOM_BASE_URL
        logger.info(f"使用自定义 base_url: {base_url}")
    elif provider in PROVIDER_DEFAULTS:
        base_url = PROVIDER_DEFAULTS[provider]["base_url"]
        logger.info(f"使用 {provider} 默认 base_url: {base_url}")
    else:
        # 未知提供商，回退到智谱AI
        logger.warning(f"未知提供商 '{provider}'，回退到智谱AI")
        provider = "zhipu"
        base_url = PROVIDER_DEFAULTS["zhipu"]["base_url"]
    
    # 2. 确定 API Key
    if Config.CUSTOM_API_KEY:
        api_key = Config.CUSTOM_API_KEY
        logger.info("使用自定义 API Key")
    elif provider == "zhipu":
        api_key = Config.ZHIPU_API_KEY
        if not api_key:
            logger.warning("ZHIPU_API_KEY 未设置！")
            api_key = "EMPTY"
    elif provider == "local":
        api_key = "EMPTY"  # 本地模型不需要 API Key
        logger.info("本地模型，API Key = EMPTY")
    else:
        logger.warning(f"使用 {provider} 但未设置 CUSTOM_API_KEY")
        api_key = "EMPTY"
    
    # 3. 确定模型名称
    # 优先级: CUSTOM_MODEL_NAME > 内核特定环境变量 > 智能选择器
    if Config.CUSTOM_MODEL_NAME:
        model_name = Config.CUSTOM_MODEL_NAME
        logger.info(f"使用自定义模型: {model_name} (所有内核)")
    elif kernel_mode:
 # 使用智能模型选择器（支持 XML_KERNEL_MODEL 等环境变量）         from phone_agent.model.selector import select_model_for_kernel
        model_name = select_model_for_kernel(kernel_mode)
        logger.info(f"智能选择模型: {kernel_mode} → {model_name}")
    else:
        # 使用提供商默认模型（fallback）
        model_name = PROVIDER_DEFAULTS.get(provider, {}).get("default_model", "autoglm-phone")
        logger.info(f"使用 {provider} 默认模型: {model_name}")
    
    config = {
        "base_url": base_url,
        "api_key": api_key,
        "model_name": model_name
    }
    
    logger.debug(f"生成模型配置: provider={provider}, model={model_name}")
    
    return config


def get_model_provider() -> str:
    """
    获取当前模型提供商
    
    Returns:
        提供商名称 (zhipu, openai, qwen, moonshot, local)
    """
    return Config.MODEL_PROVIDER.lower()


def is_using_custom_provider() -> bool:
    """
    是否使用非默认（智谱AI）提供商
    
    Returns:
        True 如果使用自定义提供商或自定义配置
    """
    return (
        Config.MODEL_PROVIDER.lower() != "zhipu" or
        Config.CUSTOM_BASE_URL is not None or
        Config.CUSTOM_API_KEY is not None or
        Config.CUSTOM_MODEL_NAME is not None
    )


# 快速示例用法
if __name__ == "__main__":
    import sys
    
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("模型配置测试")
    print("=" * 60)
    
    # 测试不同内核
    for kernel in ["xml", "vision", "planning", "auto"]:
        print(f"\n{kernel.upper()} 内核:")
        config = get_model_config_from_env(kernel)
        print(f"  base_url: {config['base_url']}")
        print(f"  model_name: {config['model_name']}")
        print(f"  api_key: {'***' + config['api_key'][-8:] if len(config['api_key']) > 8 else '(未配置)'}")
    
    print(f"\n当前提供商: {get_model_provider()}")
    print(f"使用自定义配置: {is_using_custom_provider()}")
    print("=" * 60)

