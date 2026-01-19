#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
UI层级获取 - 智能路由

自动选择最佳方法:
1. uiautomator dump (标准方法)
2. uiautomator dump --nohup (降级，跳过空闲等待)

使用方法:
    from phone_agent.adb.ui_hierarchy import get_ui_hierarchy_robust
    
    elements = get_ui_hierarchy_robust(device_id="localhost:6101")

Note: yadb does NOT support UI layout dump, removed from strategies.
"""

import logging
from typing import List, Optional
from phone_agent.adb.xml_tree import UIElement

logger = logging.getLogger(__name__)

# 全局策略缓存
_device_strategies = {}


def get_ui_hierarchy_robust(
    device_id: Optional[str] = None,
    max_retries: int = 2,
    timeout: int = 15
) -> List[UIElement]:
    """
    鲁棒的UI层级获取（智能降级）
    
    Args:
        device_id: 设备ID
        max_retries: 最大重试次数
        timeout: 单次尝试超时（秒）
    
    Returns:
        UI元素列表
    
    Raises:
        RuntimeError: 所有方法都失败时
    """
    device_key = device_id or "default"
    
    # 如果已知有效策略，优先使用
    if device_key in _device_strategies:
        strategy = _device_strategies[device_key]
        logger.debug(f"使用已知策略: {strategy}")
        try:
            return _execute_strategy(strategy, device_id, timeout)
        except Exception as e:
            logger.warning(f"已知策略失败: {e}，重新尝试")
            del _device_strategies[device_key]
    
    # 尝试不同策略（移除了无效的yadb策略）
    strategies = ["uiautomator", "uiautomator_nohup"]
    last_error = None
    
    for attempt in range(max_retries):
        for strategy in strategies:
            try:
                logger.info(f"[UPDATE] 尝试: {strategy} (第{attempt+1}次)")
                elements = _execute_strategy(strategy, device_id, timeout)
                
                if elements:
                    # 成功！记住这个策略
                    _device_strategies[device_key] = strategy
                    logger.info(f"[OK] {strategy} 成功，找到 {len(elements)} 个元素")
                    return elements
            
            except Exception as e:
                logger.debug(f"{strategy} 失败: {e}")
                last_error = e
                continue
        
        # 重试前等待
        if attempt < max_retries - 1:
            import time
            wait = 2 ** attempt
            logger.info(f"[TODO] 等待{wait}秒后重试...")
            time.sleep(wait)
    
    raise RuntimeError(
        f"所有UI获取方法都失败 (尝试{max_retries}次)。"
        f"最后错误: {last_error}"
    )


def _execute_strategy(
    strategy: str,
    device_id: Optional[str],
    timeout: int
) -> List[UIElement]:
    """执行特定策略"""
    
    if strategy == "uiautomator":
        return _try_uiautomator(device_id, timeout, nohup=False)
    
    elif strategy == "uiautomator_nohup":
        return _try_uiautomator(device_id, timeout, nohup=True)
    
    else:
        raise ValueError(f"未知策略: {strategy}")


# [X] REMOVED: _try_yadb() function
# Reason: yadb does NOT support UI layout dump
# This was a misunderstanding of yadb's capabilities


def _try_uiautomator(
    device_id: Optional[str],
    timeout: int,
    nohup: bool = False
) -> List[UIElement]:
    """尝试使用uiautomator"""
    import os
    import subprocess
    from phone_agent.adb.device import run_adb_command, _get_adb_prefix
    from phone_agent.adb.xml_tree import parse_ui_xml
    
    remote_path = "/sdcard/window_dump.xml"
    local_path = f"temp_ui_dump_{device_id or 'default'}.xml"
    
    try:
        # 构建dump命令
        cmd = ["shell", "uiautomator", "dump"]
        
        if nohup:
            cmd.append("--nohup")  # 跳过空闲等待
            logger.debug("使用 --nohup 参数")
        
        cmd.append(remote_path)
        
        # 执行dump
        result = run_adb_command(cmd, device_id=device_id, timeout=timeout)
        
        if not result or "Error" in result or "ERROR" in result:
            raise RuntimeError(f"Dump失败: {result}")
        
        # 拉取XML
        adb_prefix = _get_adb_prefix(device_id)
        pull_result = subprocess.run(
            adb_prefix + ["pull", remote_path, local_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if pull_result.returncode != 0:
            raise RuntimeError(f"Pull失败: {pull_result.stderr}")
        
        # 解析XML
        if not os.path.exists(local_path):
            raise RuntimeError("XML文件不存在")
        
        with open(local_path, "r", encoding="utf-8") as f:
            xml_content = f.read()
        
        elements = parse_ui_xml(xml_content)
        
        # 清理
        try:
            os.remove(local_path)
        except:
            pass
        
        return elements
    
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Timeout after {timeout}s")


def reset_strategy(device_id: Optional[str] = None):
    """
    重置设备策略（设备重启后调用）
    """
    device_key = device_id or "default"
    if device_key in _device_strategies:
        del _device_strategies[device_key]
        logger.info(f"已重置 {device_key} 的UI获取策略")


def get_current_strategy(device_id: Optional[str] = None) -> Optional[str]:
    """获取当前使用的策略"""
    device_key = device_id or "default"
    return _device_strategies.get(device_key)

