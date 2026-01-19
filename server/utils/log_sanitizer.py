#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
日志脱敏工具

用于在日志输出前移除敏感信息，防止API密钥、密码等泄露
"""

import re
from typing import Any, Dict


def sanitize_api_key(api_key: str) -> str:
    """
    脱敏API密钥，只显示前4位和后4位
    
    Args:
        api_key: 原始API密钥
    
    Returns:
        脱敏后的API密钥
    
    Examples:
        >>> sanitize_api_key("sk-1234567890abcdef")
        'sk-1***def'
        >>> sanitize_api_key("short")
        '***'
    """
    if not api_key or len(api_key) < 8:
        return "***"
    
    return f"{api_key[:4]}***{api_key[-3:]}"


def sanitize_dict(data: Dict[str, Any], sensitive_keys: set = None) -> Dict[str, Any]:
    """
    脱敏字典中的敏感字段
    
    Args:
        data: 原始字典
        sensitive_keys: 敏感字段名集合（默认包含常见的密钥字段）
    
    Returns:
        脱敏后的字典（深拷贝）
    
    Examples:
        >>> sanitize_dict({"api_key": "secret123", "name": "test"})
        {'api_key': 'sec***23', 'name': 'test'}
    """
    if sensitive_keys is None:
        sensitive_keys = {
            "api_key", "apikey", "api-key",
            "secret", "secret_key", "secretkey",
            "password", "passwd", "pwd",
            "token", "access_token", "refresh_token",
            "authorization", "auth",
            "private_key", "privatekey"
        }
    
    # 深拷贝并脱敏
    result = {}
    for key, value in data.items():
        key_lower = key.lower().replace("_", "").replace("-", "")
        
        # 检查是否是敏感字段
        is_sensitive = any(
            sensitive_key.replace("_", "").replace("-", "") in key_lower
            for sensitive_key in sensitive_keys
        )
        
        if is_sensitive and isinstance(value, str):
            result[key] = sanitize_api_key(value)
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value, sensitive_keys)
        elif isinstance(value, list):
            result[key] = [
                sanitize_dict(item, sensitive_keys) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    
    return result


def sanitize_url(url: str) -> str:
    """
    脱敏URL中的密钥参数
    
    Args:
        url: 原始URL
    
    Returns:
        脱敏后的URL
    
    Examples:
        >>> sanitize_url("https://api.example.com?api_key=secret123")
        'https://api.example.com?api_key=sec***23'
    """
    # 匹配URL参数中的敏感信息
    patterns = [
        (r'(api_key|apikey|token|secret|password)=([^&\s]+)', r'\1=***'),
        (r'(Authorization:\s*Bearer\s+)([^\s]+)', r'\1***'),
    ]
    
    result = url
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    return result


def sanitize_log_message(message: str) -> str:
    """
    脱敏日志消息中的敏感信息
    
    Args:
        message: 原始日志消息
    
    Returns:
        脱敏后的日志消息
    
    Examples:
        >>> sanitize_log_message("API Key: sk-1234567890")
        'API Key: sk-1***90'
    """
    # 匹配常见的密钥格式
    patterns = [
        # OpenAI/Zhipu API密钥格式: sk-xxx, glm-xxx
        (r'\b(sk-|glm-|api-)([a-zA-Z0-9]{32,})', lambda m: f"{m.group(1)}{sanitize_api_key(m.group(2))}"),
        # JWT Token
        (r'\b(eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)', lambda m: f"{m.group(1)[:20]}***"),
        # 通用密钥格式（至少16位字母数字）
        (r'(["\']?(?:api_key|apikey|secret|password|token)["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_-]{16,})(["\']?)',
         lambda m: f"{m.group(1)}{sanitize_api_key(m.group(2))}{m.group(3)}"),
    ]
    
    result = message
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    return result


# 便捷函数
def safe_log_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    便捷函数：返回可安全记录到日志的字典
    
    Usage:
        logger.info(f"Model config: {safe_log_dict(model_config)}")
    """
    return sanitize_dict(data)


def safe_log_str(message: str) -> str:
    """
    便捷函数：返回可安全记录到日志的字符串
    
    Usage:
        logger.info(safe_log_str(f"Connecting to {url}"))
    """
    return sanitize_log_message(message)


if __name__ == "__main__":
    # 测试
    print("=== 测试 API 密钥脱敏 ===")
    print(sanitize_api_key("sk-1234567890abcdef"))
    print(sanitize_api_key("short"))
    
    print("\n=== 测试字典脱敏 ===")
    config = {
        "api_key": "sk-1234567890abcdef",
        "model_name": "gpt-4",
        "secret": "my_secret_password",
        "nested": {
            "token": "bearer_token_12345"
        }
    }
    print(sanitize_dict(config))
    
    print("\n=== 测试 URL 脱敏 ===")
    url = "https://api.example.com/v1/chat?api_key=secret123&model=gpt-4"
    print(sanitize_url(url))
    
    print("\n=== 测试日志消息脱敏 ===")
    message = "Connecting with API Key: sk-1234567890abcdef to model gpt-4"
    print(sanitize_log_message(message))

