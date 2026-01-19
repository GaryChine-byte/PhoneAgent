#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
PC Agent - 服务端 PC 设备控制主逻辑

实现 PC 设备的 AI 自主操作能力,包括感知-决策-执行循环。

架构设计参考:
- MobileAgent PC-Agent (https://github.com/X-PLUG/MobileAgent)
  MIT License, Copyright (c) 2022 mPLUG
  
本模块为独立实现,集成到 PhoneAgent-Enterprise 服务端。
"""

import asyncio
import base64
import copy
import json
import logging
import re
from typing import Dict, List, Optional

from .pc_controller import PCController
from .pc_perception import PCPerception, denormalize_coordinates  # 导入反归一化函数
from .pc_actions import PCAction
from .pc_prompts import get_action_prompt, get_reflect_prompt, get_planning_prompt

logger = logging.getLogger(__name__)


class PCAgent:
    """
    PC Agent 主逻辑 (服务端)
    
    负责 PC 设备的智能控制,实现感知-决策-执行循环。
    独立实现,不依赖抽象基类。
    
    Attributes:
        device_id (str): 设备 ID
        frp_port (int): FRP 端口
        controller (PCController): PC 控制器
        perception (PCPerception): 感知模块
        model_client: VLM 模型客户端
        max_steps (int): 最大执行步骤数
    
    Note:
        这是服务端代码,客户端只负责执行基础操作
    """
    
    def __init__(
        self,
        device_id: str,
        frp_port: int,
        model_client=None,
        config: Optional[Dict] = None
    ):
        """
        初始化 PC Agent
        
        Args:
            device_id: 设备 ID
            frp_port: FRP 端口
            model_client: VLM 模型客户端（可选，不提供则自动创建）
            config: 配置字典 (包含 max_steps 等)
        """
        self.device_id = device_id
        self.frp_port = frp_port
        self.config = config or {}
        
        # 自动初始化模型客户端（与 PhoneAgent 保持一致）
        if model_client is None:
            from phone_agent.model import ModelClient, ModelConfig
            from server.utils.model_config_helper import get_model_config_from_env
            
            # 从环境变量获取配置
            env_config = get_model_config_from_env("vision")  # PC Agent 使用 vision 模式
            model_config = ModelConfig(
                base_url=env_config["base_url"],
                api_key=env_config["api_key"],
                model_name=env_config["model_name"]
            )
            self.model_client = ModelClient(model_config)
            logger.info(f"PC Agent 自动初始化模型客户端: {env_config['model_name']}")
        else:
            self.model_client = model_client
        
        # PC 控制器和感知模块
        self.controller = PCController(device_id, frp_port)
        self.perception = PCPerception(self.controller)
        self.max_steps = self.config.get("max_steps", 30)
        
        # 平台信息（默认值，会在 run 时更新）
        self.os_type = "Windows"
        self.ratio = 1.0
        self.ctrl_key = "ctrl"
        self.search_key = ["win", "s"]  # 默认 Windows
        
        # 归一化坐标系统 (与手机 Agent 保持一致: 0-1000)
        # 注意：这里只是默认值，实际值会在每次 run() 时从 perception 动态获取
        self.last_screen_width = 1920  # 默认值（会动态更新）
        self.last_screen_height = 1080  # 默认值（会动态更新）
        self.coordinate_system = "normalized"  # 默认使用归一化坐标 [0, 1000]
        
        # 历史记录（参考 MobileAgent）
        self.action_history: List[Dict] = []
        self.thought_history: List[str] = []
        self.summary_history: List[str] = []
        self.action_text_history: List[str] = []
        self.reflection_history: List[str] = []
        
        # 任务状态
        self.completed_content = ""
        self.memory = ""
        self.error_flag = False
        
        # 配置
        self.enable_reflection = self.config.get("enable_reflection", True)
        self.enable_planning = self.config.get("enable_planning", True)
        self.add_info = self.config.get("add_info", "")
        
        logger.info(f"PC Agent 初始化完成: {device_id}")
    
    async def run(self, instruction: str, callback=None) -> Dict:
        """
        执行任务 (感知-决策-执行循环)
        
        参考 MobileAgent PC-Agent 的完整流程
        
        Args:
            instruction: 用户指令
            callback: 回调对象 (PCCallback)
            
        Returns:
            执行结果字典:
            {
                "success": bool,
                "steps": int,
                "message": str,
                "history": List[Dict]
            }
        """
        logger.info(f"开始执行任务: {instruction}")
        
        # 获取平台信息（参考 MobileAgent PC-Agent）
        try:
            await self.controller.update_platform_info()
            # 同步平台信息到 self
            self.os_type = self.controller.platform_info.get("os", "Windows")
            self.ratio = self.controller.ratio
            self.ctrl_key = self.controller.ctrl_key
            self.search_key = self.controller.search_key
            logger.info(f"平台信息: os={self.os_type}, ratio={self.ratio}, ctrl_key={self.ctrl_key}, search_key={self.search_key}")
        except Exception as e:
            logger.warning(f"获取平台信息失败，使用默认值: {e}")
        
        # 重置历史记录
        self.action_history = []
        self.thought_history = []
        self.summary_history = []
        self.action_text_history = []
        self.reflection_history = []
        self.completed_content = ""
        self.error_flag = False
        
        try:
            for step in range(1, self.max_steps + 1):
                logger.info(f"=" * 60)
                logger.info(f"步骤 {step}/{self.max_steps}")
                logger.info(f"=" * 60)
                
                # 回调: 步骤开始
                if callback:
                    callback.on_step_start(step)
                
                # ============ 1. 感知 ============
                logger.info("1. 感知屏幕状态...")
                perception_before = await self.perception.perceive()
                
                # 动态更新屏幕尺寸（用于归一化坐标反归一化）
                screen_size = perception_before.get("screen_size", {})
                self.last_screen_width = screen_size.get("width", 1920)
                self.last_screen_height = screen_size.get("height", 1080)
                self.coordinate_system = perception_before.get("coordinate_system", "normalized")
                
                logger.debug(f"屏幕尺寸: {self.last_screen_width}x{self.last_screen_height}, 坐标系统: {self.coordinate_system}")
                
                # 提取 perception_infos 用于后续 TapIdx 操作
                perception_infos = perception_before.get("perception_infos", [])
                
                # ============ 2. 决策 ============
                logger.info("2. AI 决策中...")
                action_output = await self._decide_with_history(
                    instruction=instruction,
                    perception=perception_before,
                    step=step
                )
                
                # 解析决策结果
                thought = action_output.get("thought", "")
                summary = action_output.get("summary", "")
                action_text = action_output.get("action_text", "")
                action_dict = action_output.get("action", {})
                
                logger.info(f"思考: {thought[:100]}...")
                logger.info(f"摘要: {summary}")
                logger.info(f"动作: {action_text}")
                
                # ============ 3. 检查是否完成 ============
                # 与手机 Agent 保持一致: 检查 _metadata == "finish" 或 action_type == "finish"
                is_finish = (
                    action_dict.get("_metadata") == "finish" or 
                    action_dict.get("action_type") == "finish" or 
                    "finish" in action_text.lower() or
                    "Stop" in action_text  # 向后兼容
                )
                
                if is_finish:
                    # 检查是否是错误导致的提前结束
                    is_error = action_dict.get("_error", False)
                    message = action_dict.get("message", "任务完成")
                    
                    if is_error:
                        logger.error(f"[FAIL] 任务失败: {message}")
                        success = False
                        observation = f"任务失败: {message}"
                    else:
                        logger.info(f"[SUCCESS] 任务完成: {message}")
                        success = True
                        observation = "任务完成"
                    
                    # 回调: 步骤结束
                    if callback:
                        callback.on_step_end(
                            step=step,
                            success=success,
                            thinking=thought,
                            action=action_dict,
                            observation=observation,
                            reflection="A" if success else "D",  # 错误时反思为 D
                            planning=self.completed_content
                        )
                        await callback.save_screenshot(step)
                    
                    return {
                        "success": success,
                        "steps": step,
                        "message": message,
                        "history": self.action_history
                    }
                
                # ============ 4. 执行 ============
                logger.info("3. 执行操作...")
                # 传递 perception_infos 用于 TapIdx
                result = await self._execute(action_dict, perception_infos)
                logger.info(f"执行结果: {result.get('message', 'OK')}")
                
                # 执行后续动作（如果有）
                next_actions = action_dict.get("_next_actions", [])
                next_actions_desc = []
                if next_actions:
                    app_name = action_dict.get("_app_name", "")
                    if app_name:
                        logger.info(f"执行 Open App ({app_name}) 的完整流程...")
                    else:
                        logger.info(f"执行 {len(next_actions)} 个后续动作...")
                    
                    for i, next_action in enumerate(next_actions, 1):
                        action_type = next_action.get("action_type")
                        params = next_action.get("params", {})
                        
                        if action_type == "wait":
                            wait_seconds = params["seconds"]
                            logger.info(f"等待 {wait_seconds} 秒...")
                            await asyncio.sleep(wait_seconds)
                        else:
                            # 详细记录即将执行的动作
                            if action_type == "type":
                                logger.info(f"即将输入: '{params.get('text', '')}'")
                            elif action_type == "key":
                                logger.info(f"即将按键: '{params.get('keys', '')}'")
                            elif action_type == "click":
                                logger.info(f"即将点击: ({params.get('x', 0)}, {params.get('y', 0)})")
                            
                            next_result = await self._execute(next_action, perception_infos)
                            
                            # 记录执行结果
                            if action_type == "type":
                                next_actions_desc.append(f"输入 '{params.get('text', '')}'")
                            elif action_type == "key":
                                next_actions_desc.append(f"按键 '{params.get('keys', '')}'")
                            elif action_type == "click":
                                next_actions_desc.append(f"点击 ({params.get('x', 0)}, {params.get('y', 0)})")
                            
                            success = next_result.get('success', False)
                            message = next_result.get('message', 'OK')
                            logger.info(f"后续动作 {i}/{len(next_actions)} 完成: {message} (success={success})")
                
                # ============ 5. 等待操作生效 ============
                await asyncio.sleep(2)  # 参考 MobileAgent，等待2秒
                
                # ============ 6. 反思 (可选) ============
                reflection_result = ""
                if self.enable_reflection:
                    logger.info("4. 反思操作结果...")
                    perception_after = await self.perception.perceive()
                    
                    reflection_result = await self._reflect(
                        instruction=instruction,
                        perception_before=perception_before,
                        perception_after=perception_after,
                        summary=summary,
                        action_text=action_text
                    )
                    
                    logger.info(f"反思结果: {reflection_result}")
                    
                    # 判断是否需要纠错
                    if "D" in reflection_result or "wrong" in reflection_result.lower():
                        self.error_flag = True
                        logger.warning("[WARN] 操作未达到预期，下一步将尝试纠正")
                    elif "B" in reflection_result:
                        self.error_flag = True
                        logger.warning("[WARN] 操作导致错误页面")
                    else:
                        self.error_flag = False
                
                # ============ 7. 规划 (可选) ============
                if self.enable_planning:
                    logger.info("5. 规划任务进度...")
                    perception_current = await self.perception.perceive()
                    
                    planning_result = await self._plan(
                        instruction=instruction,
                        perception=perception_current
                    )
                    
                    self.completed_content = planning_result
                    logger.info(f"已完成内容: {self.completed_content[:100]}...")
                
                # ============ 8. 更新历史 ============
                self.thought_history.append(thought)
                self.summary_history.append(summary)
                self.action_text_history.append(action_text)
                self.reflection_history.append(reflection_result)
                
                step_record = {
                    "step": step,
                    "thought": thought,
                    "summary": summary,
                    "action_text": action_text,
                    "action": action_dict,
                    "result": result,
                    "reflection": reflection_result,
                    "planning": self.completed_content,
                    "perception": perception_before
                }
                self.action_history.append(step_record)
                
                # 回调: 步骤结束
                if callback:
                    # 构建完整的 observation
                    observation = result.get("message", "")
                    if next_actions_desc:
                        app_name = action_dict.get("_app_name", "")
                        if app_name:
                            observation = f"Open App ({app_name}): 已完成搜索、输入、回车，应用应该已启动"
                        else:
                            observation += " + " + ", ".join(next_actions_desc)
                    
                    callback.on_step_end(
                        step=step,
                        success=result.get("success", False),
                        thinking=thought,
                        action=action_dict,
                        observation=observation,
                        reflection=reflection_result,
                        planning=self.completed_content
                    )
                    await callback.save_screenshot(step)
            
            # 达到最大步骤数
            logger.warning(f"达到最大步骤数 {self.max_steps}")
            return {
                "success": False,
                "steps": self.max_steps,
                "message": "达到最大步骤数,任务未完成",
                "history": self.action_history
            }
        
        except Exception as e:
            logger.error(f"任务执行失败: {e}", exc_info=True)
            return {
                "success": False,
                "steps": len(self.action_history),
                "message": f"执行错误: {str(e)}",
                "history": self.action_history
            }
        
        finally:
            # 关闭控制器
            await self.controller.close()
    
    async def _decide_with_history(
        self,
        instruction: str,
        perception: Dict,
        step: int
    ) -> Dict:
        """
        决策（带历史记录）- 使用 MobileAgent 风格的 prompt
        
        Returns:
            {
                "thought": str,
                "summary": str,
                "action_text": str,
                "action": Dict
            }
        """
        if self.model_client is None:
            return {
                "thought": "",
                "summary": "未配置模型",
                "action_text": "Stop",
                "action": {"action_type": "finish", "params": {}, "message": "未配置模型"}
            }
        
        try:
            # 1. 构建 prompt（使用 MobileAgent 风格）
            from phone_agent.model.client import MessageBuilder
            
            # 准备感知信息
            perception_infos = perception.get("perception_infos", [])
            width = perception.get("screen_size", {}).get("width", 1920)
            height = perception.get("screen_size", {}).get("height", 1080)
            
            # 生成 action prompt
            prompt_text = get_action_prompt(
                instruction=instruction,
                perception_infos=perception_infos,
                width=width,
                height=height,
                thought_history=self.thought_history,
                summary_history=self.summary_history,
                action_history=self.action_text_history,
                reflection_history=self.reflection_history,
                last_summary=self.summary_history[-1] if self.summary_history else "",
                last_action=self.action_text_history[-1] if self.action_text_history else "",
                reflection_thought=self.reflection_history[-1] if self.reflection_history else "",
                error_flag=self.error_flag,
                completed_content=self.completed_content,
                memory=self.memory,
                add_info=self.add_info,
                ctrl_key=self.ctrl_key,
                search_key=self.search_key
            )
            
            # 2. 构建消息
            messages = []
            if step == 1:
                messages.append(MessageBuilder.create_system_message(
                    "You are a helpful AI PC operating assistant. You need to help me operate the PC to complete the user's instruction."
                ))
            
            messages.append(MessageBuilder.create_user_message(
                text=prompt_text,
                image_base64=perception.get("screenshot_base64")
            ))
            
            # 3. 调用模型 (使用 request_json 强制 JSON 输出)
            response = await asyncio.to_thread(self.model_client.request_json, messages)
            output_text = response.raw_content if hasattr(response, 'raw_content') else str(response)
            
            # 记录完整的 AI 输出用于调试
            logger.info(f"AI 完整输出 (前500字符): {output_text[:500]}")
            
            # 4. 解析 JSON 输出
            try:
                # 提取 JSON
                json_match = re.search(r'\{.*?"Thought".*?"Action".*?"Summary".*?\}', output_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    
                    # 记录原始 JSON 用于调试
                    logger.info(f"提取的 JSON (前500字符): {json_str[:500]}")
                    
                    # 预处理：修复常见的 JSON 格式问题
                    # 1. 修复所有格中的未转义引号 (如 Nuki"s -> Nuki's)
                    json_str = re.sub(r'([a-zA-Z])"s\s', r"\1's ", json_str)
                    json_str = re.sub(r'([a-zA-Z])"s([,\.\!\}])', r"\1's\2", json_str)
                    
                    # 2. 修复其他常见的未转义引号（在句子中间的引号）
                    # 例如：don"t -> don't, can"t -> can't, it"s -> it's
                    json_str = re.sub(r"([a-zA-Z])\"([a-z])", r"\1'\2", json_str)
                    
                    # 尝试解析
                    try:
                        output_json = json.loads(json_str)
                    except json.JSONDecodeError as e1:
                        # 如果仍然失败，检查是否是单引号 JSON
                        logger.debug(f"直接解析失败: {e1}, 尝试修复...")
                        
                        if "{'Thought'" in json_str or "'Thought'" in json_str:
                            # 单引号 JSON，转换为双引号
                            json_str = json_str.replace("'", '"')
                            logger.debug("检测到单引号 JSON，已转换为双引号")
                        
                        try:
                            output_json = json.loads(json_str)
                        except json.JSONDecodeError as e2:
                            # 最后手段：用正则直接提取字段
                            logger.debug(f"修复后仍解析失败: {e2}, 使用正则提取...")
                            
                            # 使用非贪婪匹配提取三个字段的值
                            thought = ""
                            action = "Stop"
                            summary = ""
                            
                            thought_match = re.search(r'"Thought"\s*:\s*"(.*?)"(?=\s*,)', json_str, re.DOTALL)
                            if thought_match:
                                thought = thought_match.group(1)
                            
                            action_match = re.search(r'"Action"\s*:\s*"(.*?)"(?=\s*,)', json_str, re.DOTALL)
                            if action_match:
                                action = action_match.group(1)
                            
                            summary_match = re.search(r'"Summary"\s*:\s*"(.*?)"(?=\s*[,}])', json_str, re.DOTALL)
                            if summary_match:
                                summary = summary_match.group(1)
                            
                            if thought or action != "Stop" or summary:
                                output_json = {
                                    "Thought": thought,
                                    "Action": action,
                                    "Summary": summary
                                }
                                logger.info("使用正则提取成功")
                            else:
                                raise json.JSONDecodeError("All parsing methods failed", json_str, 0)
                    
                    thought = output_json.get("Thought", "")
                    action_text = output_json.get("Action", "Stop")
                    summary = output_json.get("Summary", "")
                    
                    # 解析动作
                    action_dict = self._parse_mobile_agent_action(action_text)
                    
                    return {
                        "thought": thought,
                        "summary": summary,
                        "action_text": action_text,
                        "action": action_dict
                    }
                else:
                    logger.warning(f"无法解析 JSON: {output_text[:200]}")
                    # 添加完整输出到日志
                    logger.debug(f"完整输出: {output_text}")
                    
                    # 智能检测: 如果输出包含完成相关关键词，视为成功完成
                    completion_keywords = ["完成", "成功", "finish", "success", "done", "completed"]
                    is_likely_complete = any(kw in output_text.lower() for kw in completion_keywords)
                    
                    if is_likely_complete:
                        logger.info("[SUCCESS] 检测到任务可能已完成（基于关键词），标记为成功")
                        return {
                            "thought": output_text[:100],
                            "summary": "任务完成（智能检测）",
                            "action_text": "Stop",
                            "action": {"action_type": "finish", "params": {}, "message": "任务完成（JSON解析失败，但检测到完成关键词）", "_error": False}
                        }
                    else:
                        return {
                            "thought": output_text[:100],
                            "summary": "解析失败",
                            "action_text": "Stop",
                            "action": {"action_type": "finish", "params": {}, "message": "解析失败", "_error": True}
                        }
            except Exception as e:
                logger.error(f"解析决策输出失败: {e}")
                # 添加完整输出到日志
                logger.debug(f"导致解析失败的输出: {output_text}")
                
                # 智能检测: 如果输出包含完成相关关键词，视为成功完成
                completion_keywords = ["完成", "成功", "finish", "success", "done", "completed"]
                is_likely_complete = any(kw in output_text.lower() for kw in completion_keywords)
                
                if is_likely_complete:
                    logger.info("[SUCCESS] 检测到任务可能已完成（基于关键词），标记为成功")
                    return {
                        "thought": output_text[:100],
                        "summary": "任务完成（智能检测）",
                        "action_text": "Stop",
                        "action": {"action_type": "finish", "params": {}, "message": f"任务完成（JSON解析失败: {str(e)}，但检测到完成关键词）", "_error": False}
                    }
                else:
                    return {
                        "thought": output_text[:100],
                        "summary": "解析错误",
                        "action_text": "Stop",
                        "action": {"action_type": "finish", "params": {}, "message": f"解析错误: {str(e)}", "_error": True}
                    }
        
        except Exception as e:
            logger.error(f"决策失败: {e}", exc_info=True)
            return {
                "thought": "",
                "summary": "决策失败",
                "action_text": "Stop",
                "action": {"action_type": "finish", "params": {}, "message": f"决策错误: {str(e)}"}
            }
    
    def _parse_mobile_agent_action(self, action_text: str) -> Dict:
        """
        解析 MobileAgent 风格的动作字符串
        
        将 AI 输出的动作文本解析为标准化的动作字典，支持多种动作类型。
        
        Args:
            action_text: AI 输出的动作文本，如 "Tap (500, 500)" 或 "finish(message=\"完成\")"
        
        Returns:
            动作字典，包含以下字段:
            - action_type: 动作类型 (str)
            - params: 动作参数 (dict)
            - message: 附加消息 (str, 可选)
            - _metadata: 元数据标记 (str, 可选)
        
        支持的动作格式:
            - Tap (x, y): 单击
            - Double Tap (x, y): 双击
            - TapIdx (index): 按索引点击
            - Shortcut (key1, key2): 快捷键
            - Press (key): 按键
            - Type (x, y), (text): 输入文本
            - Replace (x, y), (text): 替换文本
            - Append (x, y), (text): 追加文本
            - Open App (app name): 打开应用
            - Tell (answer): 回答问题
            - finish(message="xxx"): 完成任务 (与手机 Agent 一致)
            - Stop: 完成任务 (向后兼容)
        
        Note:
            - 坐标使用归一化格式 [0, 1000]
            - finish 动作会设置 _metadata="finish" 标记
        """
        action_text = action_text.strip()
        
        # finish(message="xxx") - 优先匹配（与手机 Agent 一致）
        if "finish" in action_text.lower():
            # 提取 message
            match = re.search(r'finish\s*\(\s*message\s*=\s*["\']([^"\']*)["\']', action_text, re.IGNORECASE)
            if match:
                message = match.group(1)
                logger.info(f"[SUCCESS] 任务完成: {message}")
                return {"action_type": "finish", "params": {}, "message": message, "_metadata": "finish"}
            else:
                # 没有 message 参数，使用默认
                logger.info("[SUCCESS] 任务完成（无详细信息）")
                return {"action_type": "finish", "params": {}, "message": "任务完成", "_metadata": "finish"}
        
        # Stop - 向后兼容
        if "Stop" in action_text:
            logger.info("[SUCCESS] 任务完成（Stop 动作，建议改用 finish）")
            return {"action_type": "finish", "params": {}, "message": "任务完成", "_metadata": "finish"}
        
        # Open App (app name) - 统一使用系统搜索（Win+S / Command+Space）
        if "Open App" in action_text:
            match = re.search(r'Open\s+App\s*\(([^)]+)\)', action_text, re.IGNORECASE)
            if match:
                app_name = match.group(1).strip().strip('"').strip("'")
                
                # 统一使用系统搜索（更通用）
                search_key_str = "+".join(self.search_key) if isinstance(self.search_key, list) else self.search_key
                logger.info(f"使用系统搜索启动: {app_name} (快捷键: {search_key_str})")
                
                return {
                    "action_type": "key",
                    "params": {"keys": search_key_str},  # Win+S (Windows) 或 Command+Space (macOS)
                    "_next_actions": [
                        {"action_type": "wait", "params": {"seconds": 3}},        # 增加到 3 秒，等待搜索窗口完全打开
                        {"action_type": "type", "params": {"text": app_name}},    # 输入应用名称
                        {"action_type": "wait", "params": {"seconds": 2.5}},      # 增加到 2.5 秒，确保输入完成并获得焦点
                        {"action_type": "key", "params": {"keys": "enter"}},      # 第一次 Enter
                        {"action_type": "wait", "params": {"seconds": 0.5}},      # 新增：短暂延迟
                        {"action_type": "key", "params": {"keys": "enter"}},      # 新增：双保险，再按一次 Enter
                        {"action_type": "wait", "params": {"seconds": 4}}         # 增加到 4 秒，等待应用完全启动
                    ], 
                    "_app_name": app_name
                }
        
        # TapIdx (index) - 使用标注序号点击
        if "TapIdx" in action_text and "Double" not in action_text:
            match = re.search(r'TapIdx\s*\((\d+)\)', action_text, re.IGNORECASE)
            if match:
                idx = int(match.group(1)) - 1  # 转换为 0-based index
                return {
                    "action_type": "click_idx",
                    "params": {"index": idx, "clicks": 1},
                    "_requires_perception": True
                }
        
        # Tap (x, y) - 支持归一化坐标
        if "Tap" in action_text and "Double" not in action_text:
            match = re.search(r'Tap\s*\((\d+),\s*(\d+)\)', action_text)
            if match:
                norm_x, norm_y = int(match.group(1)), int(match.group(2))
                
                # 反归一化坐标 (参考手机 Agent)
                if self.coordinate_system == "normalized" and norm_x <= 1000 and norm_y <= 1000:
                    x, y = denormalize_coordinates(
                        norm_x, norm_y,
                        self.last_screen_width,
                        self.last_screen_height
                    )
                    logger.debug(f"Tap: 归一化坐标 ({norm_x}, {norm_y}) → 像素坐标 ({x}, {y})")
                else:
                    # 像素坐标（兼容旧格式）
                    x, y = norm_x, norm_y
                    logger.debug(f"Tap: 使用像素坐标 ({x}, {y})")
                
                return {
                    "action_type": "click",
                    "params": {"x": x, "y": y, "button": "left", "clicks": 1}
                }
        
        # Double TapIdx (index)
        if "Double TapIdx" in action_text:
            match = re.search(r'Double\s+TapIdx\s*\((\d+)\)', action_text, re.IGNORECASE)
            if match:
                idx = int(match.group(1)) - 1
                return {
                    "action_type": "click_idx",
                    "params": {"index": idx, "clicks": 2},
                    "_requires_perception": True
                }
        
        # Double Tap (x, y) - 支持归一化坐标
        if "Double Tap" in action_text:
            match = re.search(r'Double\s+Tap\s*\((\d+),\s*(\d+)\)', action_text)
            if match:
                norm_x, norm_y = int(match.group(1)), int(match.group(2))
                
                # 反归一化坐标
                if self.coordinate_system == "normalized" and norm_x <= 1000 and norm_y <= 1000:
                    x, y = denormalize_coordinates(
                        norm_x, norm_y,
                        self.last_screen_width,
                        self.last_screen_height
                    )
                    logger.debug(f"Double Tap: 归一化坐标 ({norm_x}, {norm_y}) → 像素坐标 ({x}, {y})")
                else:
                    x, y = norm_x, norm_y
                
                return {
                    "action_type": "click",
                    "params": {"x": x, "y": y, "button": "left", "clicks": 2}
                }
        
        # Shortcut (key1, key2)
        if "Shortcut" in action_text:
            match = re.search(r'Shortcut\s*\(([^,]+),\s*([^)]+)\)', action_text)
            if match:
                key1 = match.group(1).strip().lower()
                key2 = match.group(2).strip().lower()
                # 转换 command 为平台特定的控制键
                if key1 == "command" or key1 == "cmd":
                    key1 = self.ctrl_key
                return {
                    "action_type": "key",
                    "params": {"keys": f"{key1}+{key2}"},
                    "_next_actions": [
                        {"action_type": "wait", "params": {"seconds": 0.5}}  # 组合键后延迟
                    ]
                }
        
        # Press (key)
        if "Press" in action_text:
            match = re.search(r'Press\s*\(([^)]+)\)', action_text)
            if match:
                key = match.group(1).strip().lower()
                # 判断关键按键，增加延迟
                is_critical = key in ["enter", "return", "esc", "escape", "tab"]
                delay = 0.5 if is_critical else 0.3
                
                return {
                    "action_type": "key",
                    "params": {"keys": key},
                    "_next_actions": [
                        {"action_type": "wait", "params": {"seconds": delay}}  # 按键后延迟
                    ]
                }
        
        # Type (x, y), (text) - 支持归一化坐标
        if "Type" in action_text:
            match = re.search(r'Type\s*\((\d+),\s*(\d+)\),\s*\(([^)]+)\)', action_text)
            if match:
                norm_x, norm_y = int(match.group(1)), int(match.group(2))
                text = match.group(3).strip().strip('"').strip("'")
                text_len = len(text)
                input_delay = 1.5 if text_len > 10 else 0.8
                
                # 反归一化坐标
                if self.coordinate_system == "normalized" and norm_x <= 1000 and norm_y <= 1000:
                    x, y = denormalize_coordinates(
                        norm_x, norm_y,
                        self.last_screen_width,
                        self.last_screen_height
                    )
                    logger.debug(f"Type: 归一化坐标 ({norm_x}, {norm_y}) → 像素坐标 ({x}, {y})")
                else:
                    x, y = norm_x, norm_y
                
                return {
                    "action_type": "click",
                    "params": {"x": x, "y": y, "button": "left", "clicks": 1},
                    "_next_actions": [
                        {"action_type": "wait", "params": {"seconds": 0.5}},      # 等待焦点
                        {"action_type": "type", "params": {"text": text}},
                        {"action_type": "wait", "params": {"seconds": input_delay}},  # 输入后延迟
                        {"action_type": "key", "params": {"keys": "enter"}},
                        {"action_type": "wait", "params": {"seconds": 0.5}},      # Enter 后延迟
                        {"action_type": "key", "params": {"keys": "enter"}},      # 双保险
                        {"action_type": "wait", "params": {"seconds": 1}}         # 提交完成
                    ]
                }
        
        # Replace (x, y), (text) - 支持归一化坐标
        if "Replace" in action_text:
            match = re.search(r'Replace\s*\((\d+),\s*(\d+)\),\s*\(([^)]+)\)', action_text)
            if match:
                norm_x, norm_y = int(match.group(1)), int(match.group(2))
                text = match.group(3).strip().strip('"').strip("'")
                text_len = len(text)
                input_delay = 1.5 if text_len > 10 else 0.8
                
                # 反归一化坐标
                if self.coordinate_system == "normalized" and norm_x <= 1000 and norm_y <= 1000:
                    x, y = denormalize_coordinates(
                        norm_x, norm_y,
                        self.last_screen_width,
                        self.last_screen_height
                    )
                    logger.debug(f"Replace: 归一化坐标 ({norm_x}, {norm_y}) → 像素坐标 ({x}, {y})")
                else:
                    x, y = norm_x, norm_y
                
                return {
                    "action_type": "click",
                    "params": {"x": x, "y": y, "button": "left", "clicks": 2},
                    "_next_actions": [
                        {"action_type": "wait", "params": {"seconds": 0.8}},      # 等待选中
                        {"action_type": "type", "params": {"text": text}},
                        {"action_type": "wait", "params": {"seconds": input_delay}},  # 输入后延迟
                        {"action_type": "key", "params": {"keys": "enter"}},
                        {"action_type": "wait", "params": {"seconds": 0.5}},      # Enter 后延迟
                        {"action_type": "key", "params": {"keys": "enter"}},      # 双保险
                        {"action_type": "wait", "params": {"seconds": 1}}         # 提交完成
                    ]
                }
        
        # Append (x, y), (text) - 支持归一化坐标
        if "Append" in action_text:
            match = re.search(r'Append\s*\((\d+),\s*(\d+)\),\s*\(([^)]+)\)', action_text)
            if match:
                norm_x, norm_y = int(match.group(1)), int(match.group(2))
                text = match.group(3).strip().strip('"').strip("'")
                text_len = len(text)
                input_delay = 1.5 if text_len > 10 else 0.8
                select_all_key = f"{self.ctrl_key}+a"
                
                # 反归一化坐标
                if self.coordinate_system == "normalized" and norm_x <= 1000 and norm_y <= 1000:
                    x, y = denormalize_coordinates(
                        norm_x, norm_y,
                        self.last_screen_width,
                        self.last_screen_height
                    )
                    logger.debug(f"Append: 归一化坐标 ({norm_x}, {norm_y}) → 像素坐标 ({x}, {y})")
                else:
                    x, y = norm_x, norm_y
                
                return {
                    "action_type": "click",
                    "params": {"x": x, "y": y, "button": "left", "clicks": 1},
                    "_next_actions": [
                        {"action_type": "wait", "params": {"seconds": 0.5}},      # 等待焦点
                        {"action_type": "key", "params": {"keys": select_all_key}},
                        {"action_type": "wait", "params": {"seconds": 0.3}},      # Ctrl+A 后延迟
                        {"action_type": "key", "params": {"keys": "down"}},
                        {"action_type": "wait", "params": {"seconds": 0.3}},      # Down 后延迟
                        {"action_type": "type", "params": {"text": text}},
                        {"action_type": "wait", "params": {"seconds": input_delay}},  # 输入后延迟
                        {"action_type": "key", "params": {"keys": "enter"}},
                        {"action_type": "wait", "params": {"seconds": 0.5}},      # Enter 后延迟
                        {"action_type": "key", "params": {"keys": "enter"}},      # 双保险
                        {"action_type": "wait", "params": {"seconds": 1}}         # 提交完成
                    ]
                }
        
        # Tell (answer)
        if "Tell" in action_text:
            match = re.search(r'Tell\s*\(([^)]+)\)', action_text)
            if match:
                answer = match.group(1).strip()
                return {"action_type": "finish", "params": {}, "message": f"回答: {answer}"}
        
        # 默认
        logger.warning(f"无法解析动作: {action_text}")
        return {"action_type": "finish", "params": {}, "message": f"无法解析动作: {action_text}"}
    
    async def _reflect(
        self,
        instruction: str,
        perception_before: Dict,
        perception_after: Dict,
        summary: str,
        action_text: str
    ) -> str:
        """
        反思操作结果
        
        Returns:
            反思结果: "A" | "B" | "C" | "D"
        """
        if self.model_client is None:
            return "A"  # 默认成功
        
        try:
            from phone_agent.model.client import MessageBuilder
            
            # 准备感知信息
            perception_infos_before = perception_before.get("perception_infos", [])
            perception_infos_after = perception_after.get("perception_infos", [])
            width = perception_after.get("screen_size", {}).get("width", 1920)
            height = perception_after.get("screen_size", {}).get("height", 1080)
            
            # 生成 reflect prompt
            prompt_text = get_reflect_prompt(
                instruction=instruction,
                perception_infos_before=perception_infos_before,
                perception_infos_after=perception_infos_after,
                width=width,
                height=height,
                summary=summary,
                action=action_text,
                add_info=self.add_info
            )
            
            # 构建消息（只使用操作后的截图，避免多图片格式问题）
            messages = [
                MessageBuilder.create_system_message(
                    "You are a helpful AI PC operating assistant."
                ),
                MessageBuilder.create_user_message(
                    text=prompt_text,
                    image_base64=perception_after.get("screenshot_base64")
                )
            ]
            
            # 调用模型 (反思不需要 JSON，使用 request)
            response = await asyncio.to_thread(self.model_client.request, messages)
            output_text = response.content if hasattr(response, 'content') else str(response)
            
            # 解析答案
            if "### Answer ###" in output_text:
                answer = output_text.split("### Answer ###")[-1].strip()
                # 提取 A/B/C/D
                for letter in ["A", "B", "C", "D"]:
                    if letter in answer[:10]:
                        return letter
            
            # 默认成功
            return "A"
        
        except Exception as e:
            logger.error(f"反思失败: {e}", exc_info=True)
            return "A"
    
    async def _plan(
        self,
        instruction: str,
        perception: Dict
    ) -> str:
        """
        规划任务进度
        
        Returns:
            已完成内容描述
        """
        if self.model_client is None:
            return ""
        
        try:
            from phone_agent.model.client import MessageBuilder
            
            # 准备感知信息
            perception_infos = perception.get("perception_infos", [])
            width = perception.get("screen_size", {}).get("width", 1920)
            height = perception.get("screen_size", {}).get("height", 1080)
            
            # 生成 planning prompt
            prompt_text = get_planning_prompt(
                instruction=instruction,
                thought_history=self.thought_history if self.thought_history else [""],
                summary_history=self.summary_history if self.summary_history else [""],
                action_history=self.action_text_history,
                completed_content=self.completed_content,
                add_info=self.add_info,
                reflection_history=self.reflection_history,
                perception_infos=perception_infos,
                width=width,
                height=height
            )
            
            # 构建消息
            messages = [
                MessageBuilder.create_system_message(
                    "You are a helpful AI PC operating assistant."
                ),
                MessageBuilder.create_user_message(
                    text=prompt_text,
                    image_base64=perception.get("screenshot_base64")
                )
            ]
            
            # 调用模型 (规划不需要 JSON，使用 request)
            response = await asyncio.to_thread(self.model_client.request, messages)
            output_text = response.content if hasattr(response, 'content') else str(response)
            
            # 解析已完成内容
            if "### Completed contents ###" in output_text:
                completed = output_text.split("### Completed contents ###")[-1].strip()
                return completed[:500]  # 限制长度
            
            return ""
        
        except Exception as e:
            logger.error(f"规划失败: {e}", exc_info=True)
            return ""
    
    async def _execute(self, action: Dict, perception_infos: List[Dict] = None) -> Dict:
        """
        执行操作 (调用客户端 HTTP API)
        
        Args:
            action: 动作字典
            perception_infos: 感知信息列表（用于 click_idx）
            
        Returns:
            执行结果
        """
        action_type = action.get("action_type")
        params = action.get("params", {})
        
        try:
            if action_type == "click_idx":
                # 使用索引点击（参考 MobileAgent TapIdx）
                idx = params.get("index", 0)
                clicks = params.get("clicks", 1)
                
                if not perception_infos or idx >= len(perception_infos):
                    return {"success": False, "message": f"索引 {idx+1} 超出范围"}
                
                # 从 perception_infos 获取坐标
                coordinates = perception_infos[idx].get("coordinates", [0, 0])
                x, y = int(coordinates[0]), int(coordinates[1])
                
                logger.info(f"TapIdx ({idx+1}) -> 坐标 ({x}, {y})")
                return await self.controller.click(x, y, clicks=clicks)
            
            elif action_type == "click":
                return await self.controller.click(
                    params["x"],
                    params["y"]
                )
            
            elif action_type == "type":
                return await self.controller.type_text(
                    params["text"]
                )
            
            elif action_type == "key":
                keys_str = params.get("keys", "")
                # 解析组合键 (如 "ctrl+c" -> key="c", modifiers=["ctrl"])
                if "+" in keys_str:
                    parts = keys_str.split("+")
                    modifiers = parts[:-1]
                    key = parts[-1]
                else:
                    key = keys_str
                    modifiers = []
                
                return await self.controller.press_key(key, modifiers)
            
            elif action_type == "scroll":
                return await self.controller.scroll(
                    params["clicks"]
                )
            
            elif action_type == "move":
                return await self.controller.move_mouse(
                    params["x"],
                    params["y"]
                )
            
            else:
                return {
                    "success": False,
                    "message": f"未知操作: {action_type}"
                }
        
        except Exception as e:
            logger.error(f"执行失败: {e}", exc_info=True)
            return {"success": False, "message": str(e)}
    
    async def take_screenshot(self) -> bytes:
        """
        截图
        
        Returns:
            截图字节数据 (PNG 格式)
        """
        return await self.controller.take_screenshot()
