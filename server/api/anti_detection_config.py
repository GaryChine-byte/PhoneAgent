#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
防风控配置API
提供防风控配置的增删改查接口
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import os

logger = logging.getLogger(__name__)
router = APIRouter()

CONFIG_FILE = "data/anti_detection_config.json"


class AntiDetectionConfig(BaseModel):
    """防风控配置模型"""
    enabled: bool = True
    level: str = "medium"  # low/medium/high
    
    # 功能开关
    enable_time_random: bool = True
    enable_position_random: bool = True
    enable_bezier_swipe: bool = True
    enable_typing_simulation: bool = True
    enable_exploration: bool = True
    
    # 时间配置
    delay_levels: Dict[str, Dict[str, float]] = {
        "low": {"min": 0.3, "max": 1.0},
        "medium": {"min": 0.5, "max": 3.0},
        "high": {"min": 1.0, "max": 5.0}
    }
    
    # 坐标随机化配置
    position_offset_percentage: float = 0.2
    
    # 贝塞尔曲线配置
    bezier_steps: int = 20
    bezier_control_randomness: int = 100
    
    # 输入配置
    typing_delay: Dict[str, float] = {"min": 0.1, "max": 0.3}
    typo_probability: float = 0.05
    pause_every_n_chars: int = 10
    
    # 探索配置
    exploration_probability: float = 0.3


def load_config() -> AntiDetectionConfig:
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return AntiDetectionConfig(**data)
        except Exception as e:
            logger.warning(f"Failed to load anti-detection config from {CONFIG_FILE}: {e}")
    
    # 返回默认配置
    return AntiDetectionConfig()


def save_config(config: AntiDetectionConfig):
    """保存配置"""
    os.makedirs("data", exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config.model_dump(), f, ensure_ascii=False, indent=2)
    
    # 更新phone_agent的全局配置
    try:
        from phone_agent.adb.anti_detection import get_anti_detection
        ad = get_anti_detection()
        ad.update_config(config.model_dump())
    except Exception as e:
        logger.warning(f"Failed to update phone_agent anti-detection config: {e}")


@router.get("/anti-detection/config", response_model=AntiDetectionConfig)
async def get_config():
    """
    获取防风控配置
    
    返回当前的防风控配置，包括所有功能开关和参数
    """
    return load_config()


@router.put("/anti-detection/config", response_model=AntiDetectionConfig)
async def update_config(config: AntiDetectionConfig):
    """
    更新防风控配置
    
    更新防风控配置，立即生效
    """
    try:
        save_config(config)
        return config
    except Exception as e:
        raise HTTPException(500, f"Failed to save config: {str(e)}")


@router.post("/anti-detection/reset")
async def reset_config():
    """
    重置为默认配置
    
    将防风控配置重置为系统默认值
    """
    try:
        default_config = AntiDetectionConfig()
        save_config(default_config)
        return {"message": "Config reset to default", "config": default_config}
    except Exception as e:
        raise HTTPException(500, f"Failed to reset config: {str(e)}")


@router.post("/anti-detection/enable")
async def enable_anti_detection():
    """启用防风控"""
    config = load_config()
    config.enabled = True
    save_config(config)
    return {"message": "Anti-detection enabled", "enabled": True}


@router.post("/anti-detection/disable")
async def disable_anti_detection():
    """禁用防风控"""
    config = load_config()
    config.enabled = False
    save_config(config)
    return {"message": "Anti-detection disabled", "enabled": False}


@router.put("/anti-detection/level")
async def set_level(level: str):
    """
    设置防护等级
    
    Args:
        level: low/medium/high
    """
    if level not in ["low", "medium", "high"]:
        raise HTTPException(400, "Level must be 'low', 'medium', or 'high'")
    
    config = load_config()
    config.level = level
    save_config(config)
    return {"message": f"Level set to {level}", "level": level}


@router.get("/anti-detection/features")
async def get_features():
    """
    获取所有防风控功能及其状态
    
    返回所有可配置的防风控功能列表
    """
    config = load_config()
    return {
        "features": [
            {
                "id": "time_random",
                "name": "时间随机化",
                "description": "为操作添加随机延迟，模拟人类思考时间",
                "enabled": config.enable_time_random,
                "impact": "高"
            },
            {
                "id": "position_random",
                "name": "坐标随机化",
                "description": "点击坐标随机偏移±20%，避免每次点击同一像素",
                "enabled": config.enable_position_random,
                "impact": "高"
            },
            {
                "id": "bezier_swipe",
                "name": "贝塞尔曲线滑动",
                "description": "使用贝塞尔曲线生成自然的滑动轨迹",
                "enabled": config.enable_bezier_swipe,
                "impact": "中"
            },
            {
                "id": "typing_simulation",
                "name": "输入速度模拟",
                "description": "逐字输入，每个字符100-300ms延迟，偶尔打错字",
                "enabled": config.enable_typing_simulation,
                "impact": "中"
            },
            {
                "id": "exploration",
                "name": "探索行为模拟",
                "description": "30%概率先探索（误点、滑动）再执行目标操作",
                "enabled": config.enable_exploration,
                "impact": "低"
            }
        ],
        "level": config.level,
        "enabled": config.enabled
    }


@router.put("/anti-detection/feature/{feature_id}")
async def toggle_feature(feature_id: str, enabled: bool):
    """
    切换单个功能开关
    
    Args:
        feature_id: 功能ID
        enabled: 是否启用
    """
    config = load_config()
    feature_key = f"enable_{feature_id}"
    
    if not hasattr(config, feature_key):
        raise HTTPException(404, f"Feature '{feature_id}' not found")
    
    setattr(config, feature_key, enabled)
    save_config(config)
    
    return {
        "message": f"Feature '{feature_id}' {'enabled' if enabled else 'disabled'}",
        "feature_id": feature_id,
        "enabled": enabled
    }

