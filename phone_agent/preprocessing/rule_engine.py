#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
规则引擎执行器

直接执行简单的系统指令，无需LLM。

Phase 1: 支持 launch/home/back/screenshot
"""

from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class RuleEngineExecutor:
    """规则引擎执行器"""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
    
    def execute(self, action: Dict) -> Tuple[bool, str]:
        """
        执行直接动作
        
        Args:
            action: {"type": "launch", "app": "微信"}
        
        Returns:
            (是否成功, 结果消息)
        """
        action_type = action.get("type")
        
        try:
            if action_type == "launch":
                return self._execute_launch(action)
            
            elif action_type == "home":
                return self._execute_home()
            
            elif action_type == "back":
                return self._execute_back()
            
            elif action_type == "screenshot":
                return self._execute_screenshot()
            
            else:
                return False, f"未知的动作类型: {action_type}"
        
        except Exception as e:
            logger.error(f"规则引擎执行失败: {e}")
            return False, str(e)
    
    def _execute_launch(self, action: Dict) -> Tuple[bool, str]:
        """执行启动应用"""
        from phone_agent.adb.device import launch_app
        
        app_name = action.get("app")
        if not app_name:
            return False, "缺少应用名称"
        
        logger.info(f" 规则引擎: 启动应用 {app_name}")
        success = launch_app(app_name, self.device_id)
        
        if success:
            return True, f"应用 {app_name} 已启动"
        else:
            return False, f"应用 {app_name} 启动失败"
    
    def _execute_home(self) -> Tuple[bool, str]:
        """执行返回桌面"""
        from phone_agent.adb.device import press_key
        
        logger.info(f"🏠 规则引擎: 返回桌面")
        success = press_key("KEYCODE_HOME", self.device_id)
        
        if success:
            return True, "已返回桌面"
        else:
            return False, "返回桌面失败"
    
    def _execute_back(self) -> Tuple[bool, str]:
        """执行返回上级"""
        from phone_agent.adb.device import press_key
        
        logger.info(f"<-  规则引擎: 返回上级")
        success = press_key("KEYCODE_BACK", self.device_id)
        
        if success:
            return True, "已返回上级"
        else:
            return False, "返回上级失败"
    
    def _execute_screenshot(self) -> Tuple[bool, str]:
        """执行截图"""
        from phone_agent.adb.device import run_adb_command
        
        logger.info(f"📸 规则引擎: 截图")
        result = run_adb_command(
            ["shell", "screencap", "-p", "/sdcard/screenshot.png"],
            device_id=self.device_id
        )
        
        if result.returncode == 0:
            return True, "截图已保存到 /sdcard/screenshot.png"
        else:
            return False, "截图失败"

