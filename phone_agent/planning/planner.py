#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""规划代理 - 生成和执行任务计划"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

from phone_agent.adb import get_current_app, get_screenshot
from phone_agent.model import ModelClient, ModelConfig
from phone_agent.model.client import MessageBuilder
from phone_agent.config.prompts import PLANNING_SYSTEM_PROMPT, PLANNING_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


@dataclass
class TaskPlan:
    """任务执行计划"""
    
    instruction: str
    complexity: str  # simple, medium, complex
    task_analysis: str
    overall_strategy: str
    estimated_duration_seconds: int
    steps: list[dict[str, Any]]
    checkpoints: list[dict[str, Any]]
    risk_points: list[str]
    
    def to_dict(self) -> dict[str, Any]:
        """将计划转换为字典"""
        return {
            "instruction": self.instruction,
            "complexity": self.complexity,
            "task_analysis": self.task_analysis,
            "overall_strategy": self.overall_strategy,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "steps": self.steps,
            "checkpoints": self.checkpoints,
            "risk_points": self.risk_points,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskPlan":
        """从字典创建计划"""
        return cls(
            instruction=data["instruction"],
            complexity=data.get("complexity", "medium"),
            task_analysis=data.get("task_analysis", ""),
            overall_strategy=data.get("overall_strategy", ""),
            estimated_duration_seconds=data.get("estimated_duration_seconds", 30),
            steps=data.get("steps", []),
            checkpoints=data.get("checkpoints", []),
            risk_points=data.get("risk_points", []),
        )


class PlanningAgent:
    """
    规划代理 - 在执行前生成完整的任务计划
    
    对于明确定义的任务,这比逐步模式更快更高效。
    """
    
    def __init__(
        self,
        model_config: ModelConfig | None = None,
        device_id: str | None = None,
    ):
        """
        初始化规划代理
        
        Args:
            model_config: AI模型配置
            device_id: 设备ID(可选),用于多设备场景
        """
        self.model_config = model_config or ModelConfig()
        self.device_id = device_id
        self.model_client = ModelClient(self.model_config)
    
    def generate_plan(self, task: str, include_screenshot: bool = True) -> TaskPlan:
        """
        为任务生成完整的执行计划
        
        Args:
            task: 自然语言任务描述
            include_screenshot: 是否在上下文中包含当前屏幕
            
        Returns:
            包含完整计划的TaskPlan对象
            
        Raises:
            ValueError: 当计划生成失败或响应无效时
        """
        logger.info(f"Generating plan for task: {task}")
        
        # 如果需要,获取当前屏幕状态
        screenshot = None
        current_app = "未知"
        screen_width = 1080
        screen_height = 2400
        
        if include_screenshot:
            try:
                screenshot = get_screenshot(self.device_id)
                current_app = get_current_app(self.device_id) or "未知"
                screen_width = screenshot.width
                screen_height = screenshot.height
            except Exception as e:
                logger.warning(f"获取屏幕状态失败: {e}")
        
        # 构建用户提示词
        user_prompt = PLANNING_USER_PROMPT_TEMPLATE.format(
            task=task,
            current_app=current_app,
            screen_width=screen_width,
            screen_height=screen_height,
        )
        
        # 构建消息列表
        messages = [
            MessageBuilder.create_system_message(PLANNING_SYSTEM_PROMPT),
        ]
        
        if screenshot and include_screenshot:
            messages.append(
                MessageBuilder.create_user_message(
                    text=user_prompt,
                    image_base64=screenshot.base64_data
                )
            )
        else:
            messages.append(
                MessageBuilder.create_user_message(text=user_prompt)
            )
        
        # 从模型获取响应(使用request_json强制JSON输出)
        try:
            response = self.model_client.request_json(messages)
            logger.debug(f"模型响应: {response.action[:500]}...")  # 记录前500字符
        except Exception as e:
            logger.error(f"模型请求失败: {e}")
            raise ValueError(f"生成计划失败: {e}")
        
        # 解析JSON响应
        try:
            plan_data = self._parse_json_response(response.action)
        except Exception as e:
            logger.error(f"解析计划失败: {e}")
            logger.error(f"原始响应: {response.action}")
            raise ValueError(f"解析计划失败: {e}")
        
        # [OK] 修复：处理AI返回列表的情况
        if isinstance(plan_data, list):
            # AI返回了步骤列表而不是完整的计划对象
            # 包装成标准格式,并确保每个步骤都有step_id
            logger.warning("AI返回了列表而非计划对象,正在包装")
            steps = plan_data
            # 确保每个步骤都有step_id(只处理字典类型的步骤)
            for i, step in enumerate(steps, 1):
                if isinstance(step, dict) and "step_id" not in step:
                    step["step_id"] = i
                elif not isinstance(step, dict):
                    logger.error(f"步骤 {i} 不是字典类型: {type(step)}, 值: {step}")
                    raise ValueError(f"无效的步骤格式: 步骤 {i} 必须是字典")
            
            plan_data = {
                "instruction": task,
                "complexity": "medium",
                "task_analysis": "AI直接返回了步骤列表",
                "overall_strategy": "按照步骤顺序执行",
                "estimated_duration_seconds": len(steps) * 10,
                "steps": steps,
                "checkpoints": [],
                "risk_points": []
            }
        else:
            # [OK] 修复：即使是标准格式,也要确保步骤有step_id
            if "steps" in plan_data and isinstance(plan_data["steps"], list):
                for i, step in enumerate(plan_data["steps"], 1):
                    if isinstance(step, dict) and "step_id" not in step:
                        step["step_id"] = i
                        logger.warning(f"添加了缺失的step_id={i}到步骤 {i}")
                    elif not isinstance(step, dict):
                        logger.error(f"步骤 {i} 不是字典类型: {type(step)}, 值: {step}")
                        raise ValueError(f"无效的步骤格式: 步骤 {i} 必须是字典")
        
        # 验证并创建计划
        try:
            plan = TaskPlan.from_dict(plan_data)
            logger.info(f"生成了包含 {len(plan.steps)} 个步骤的计划,复杂度: {plan.complexity}")
            return plan
        except Exception as e:
            logger.error(f"创建计划对象失败: {e}")
            logger.error(f"计划数据结构: {type(plan_data)}")
            logger.error(f"计划数据内容: {plan_data}")
            raise ValueError(f"无效的计划结构: {e}")
    
    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """
        从模型响应中解析JSON,处理markdown代码块
        
        Args:
            response: 来自模型的原始响应字符串
            
        Returns:
            解析后的JSON字典
            
        Raises:
            ValueError: 当JSON无法解析时
        """
        import re
        response = response.strip()
        
        # [OK] 检测特殊标签: [notool], [sensitive]
        if response.startswith('[notool]'):
            logger.warning("[WARN] AI返回了[notool] - 任务不需要手机操作")
            raise ValueError(
                "任务不需要手机操作。"
                "此任务可以直接回答而无需手机自动化。"
                "如果想执行手机动作,请使用逐步模式。"
            )
        
        if response.startswith('[sensitive]'):
            logger.error("[SECURITY] AI返回了[sensitive] - 检测到敏感操作")
            raise ValueError(
                "检测到敏感操作(支付、密码、登录、银行应用)。"
                "为安全起见停止。规划模式无法处理敏感操作。"
            )
        
        # 移除markdown代码块(如果存在)
        # 模式1: ```json ... ```
        json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            response = json_match.group(1).strip()
        else:
            # 模式2: ``` ... ```
            json_match = re.search(r'```\s*\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1).strip()
        
        # 清理JSON(移除注释)
        # 移除//注释
        response = re.sub(r'//[^\n]*', '', response)
        # 移除/* */注释
        response = re.sub(r'/\*.*?\*/', '', response, flags=re.DOTALL)
        
        # 尝试解析JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            # 尝试在响应中查找JSON对象
            # 查找第一个{和最后一个}
            start_idx = response.find('{')
            end_idx = response.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx + 1]
                # 清理这个子字符串
                json_str = re.sub(r'//[^\n]*', '', json_str)
                json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            
            # [OK] 容错处理: 如果AI返回了自然语言而不是JSON,尝试从文本中提取关键信息
            logger.warning(f"[WARN] AI返回了非JSON响应,尝试从文本中提取动作")
            
            # 检查是否包含do()调用(Vision模式的格式)
            do_match = re.search(r'do\(action="(\w+)"(?:,\s*(\w+)="([^"]+)")?\)', response)
            if do_match:
                action = do_match.group(1)
                param_name = do_match.group(2)
                param_value = do_match.group(3)
                
                logger.info(f"从文本中提取的动作: {action}, {param_name}={param_value}")
                
                # 构造一个简单的计划
                if action == "Launch" and param_name in ["app", "app_name"]:
                    return {
                        "instruction": f"打开{param_value}",
                        "complexity": "simple",
                        "task_analysis": "单步任务: 启动应用",
                        "overall_strategy": f"启动{param_value}应用",
                        "estimated_duration_seconds": 5,
                        "steps": [
                            {
                                "step_id": 1,
                                "action_type": "LAUNCH",
                                "target_description": f"启动{param_value}",
                                "expected_result": f"{param_value}应用打开",
                                "reasoning": "用户要求打开应用",
                                "parameters": {"app_name": param_value}
                            }
                        ],
                        "checkpoints": [],
                        "risk_points": []
                    }
            
            raise ValueError(f"无法解析JSON: {e}")
    
    def validate_plan(self, plan: TaskPlan) -> tuple[bool, Optional[str]]:
        """
        验证任务计划的正确性
        
        Args:
            plan: 要验证的TaskPlan
            
        Returns:
            元组 (是否有效, 错误消息)
        """
        # 检查必需字段
        if not plan.instruction:
            return False, "计划必须有指令"
        
        if not plan.steps or len(plan.steps) == 0:
            return False, "计划必须至少有一个步骤"
        
        # 验证步骤
        valid_action_types = {
            "LAUNCH", "TAP", "DOUBLE_TAP", "LONG_PRESS", 
            "TYPE", "CLEAR_TEXT", "SWIPE", 
            "BACK", "HOME", "WAIT", "CHECKPOINT"
        }
        
        for i, step in enumerate(plan.steps, 1):
            if "step_id" not in step:
                return False, f"步骤 {i} 缺少step_id"
            
            if "action_type" not in step:
                return False, f"步骤 {i} 缺少action_type"
            
            action_type = step["action_type"]
            if action_type not in valid_action_types:
                return False, f"步骤 {i} 有无效的action_type: {action_type}"
            
            if "parameters" not in step:
                return False, f"步骤 {i} 缺少parameters"
            
            # 验证每种动作类型的参数
            params = step["parameters"]
            if action_type == "LAUNCH" and "app_name" not in params:
                return False, f"步骤 {i} LAUNCH缺少app_name"
            
            if action_type in ("TAP", "DOUBLE_TAP") and ("x" not in params or "y" not in params):
                return False, f"步骤 {i} {action_type}缺少坐标"
            
            if action_type == "LONG_PRESS":
                if "x" not in params or "y" not in params:
                    return False, f"步骤 {i} LONG_PRESS缺少坐标"
                # duration_ms是可选的,有默认值
            
            if action_type == "TYPE" and "text" not in params:
                return False, f"步骤 {i} TYPE缺少text"
            
            # CLEAR_TEXT没有必需参数
            
            if action_type == "SWIPE":
                required = ["start_x", "start_y", "end_x", "end_y"]
                if not all(k in params for k in required):
                    return False, f"步骤 {i} SWIPE缺少坐标"
            
            if action_type == "WAIT" and "seconds" not in params:
                return False, f"步骤 {i} WAIT缺少seconds"
        
        return True, None

