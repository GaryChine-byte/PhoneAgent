#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
PC 动作定义 - 标准化的操作动作

定义 PC 设备的标准动作格式。
"""

import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PCAction:
    """
    PC 动作
    
    标准化的操作动作格式。
    
    Attributes:
        action_type (str): 动作类型
        params (dict): 动作参数
        thought (str): 思考过程 (可选)
        message (str): 消息 (可选)
    """
    action_type: str
    params: Dict
    thought: Optional[str] = None
    message: Optional[str] = None
    
    @classmethod
    def click(cls, x: int, y: int, button: str = "left") -> "PCAction":
        """创建点击动作"""
        return cls(
            action_type="click",
            params={"x": x, "y": y, "button": button}
        )
    
    @classmethod
    def type_text(cls, text: str) -> "PCAction":
        """创建输入动作"""
        return cls(
            action_type="type",
            params={"text": text}
        )
    
    @classmethod
    def press_key(cls, key: str, modifiers: Optional[List[str]] = None) -> "PCAction":
        """创建按键动作"""
        return cls(
            action_type="key",
            params={"key": key, "modifiers": modifiers or []}
        )
    
    @classmethod
    def scroll(cls, clicks: int) -> "PCAction":
        """创建滚动动作"""
        return cls(
            action_type="scroll",
            params={"clicks": clicks}
        )
    
    @classmethod
    def move_mouse(cls, x: int, y: int) -> "PCAction":
        """创建鼠标移动动作"""
        return cls(
            action_type="move",
            params={"x": x, "y": y}
        )
    
    @classmethod
    def finish(cls, message: str = "任务完成") -> "PCAction":
        """创建完成动作"""
        return cls(
            action_type="finish",
            params={},
            message=message
        )
    
    @classmethod
    def from_model_response(cls, response: str) -> "PCAction":
        """
        从模型响应创建动作
        
        Args:
            response: 模型响应 (JSON 格式)
            
        Returns:
            PCAction 对象
        """
        try:
            data = json.loads(response)
            return cls(
                action_type=data.get("action_type", "finish"),
                params=data.get("params", {}),
                thought=data.get("thought"),
                message=data.get("message")
            )
        except Exception as e:
            logger.error(f"解析模型响应失败: {e}", exc_info=True)
            return cls.finish(f"解析错误: {str(e)}")
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PCAction":
        """
        从字典创建动作
        
        Args:
            data: 动作字典
            
        Returns:
            PCAction 对象
        """
        return cls(
            action_type=data.get("action_type", "finish"),
            params=data.get("params", {}),
            thought=data.get("thought"),
            message=data.get("message")
        )
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "action_type": self.action_type,
            "params": self.params,
            "thought": self.thought,
            "message": self.message
        }
