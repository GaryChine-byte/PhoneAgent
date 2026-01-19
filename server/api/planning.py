#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
规划模式 API - 智能任务规划与执行

提供智能规划模式的API端点，支持：
1. 生成任务计划（不执行）
2. 执行已生成的计划
3. 直接生成并执行（推荐）
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.services import get_agent_service
from server.services.agent_service import TaskStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/planning", tags=[" 智能规划"]) 

class ModelConfig(BaseModel):
    """模型配置"""
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    execution_mode: Optional[str] = "planning"
    kernel_mode: Optional[str] = Field(
        default="auto",
        description="执行内核模式: xml(快速), vision(兜底), auto(自动)"
    )


class GeneratePlanRequest(BaseModel):
    """生成计划请求"""
    instruction: str = Field(..., description="任务指令")
    device_id: Optional[str] = Field(None, description="设备ID")
    # model_settings 完全可选，不设置时由后端环境变量控制
    model_settings: Optional[ModelConfig] = Field(None, alias="model_config", description="模型配置（可选，留空使用环境变量）")
    prompt_cards: Optional[List[str]] = Field(default=[], description="提示词卡片名称列表")
    
    model_config = {"populate_by_name": True}  # 允许使用别名和字段名


class ExecutePlanRequest(BaseModel):
    """执行计划请求"""
    plan: Dict[str, Any] = Field(..., description="任务计划")
    device_id: str = Field(..., description="设备ID")
    use_smart_positioning: bool = Field(
        default=True,
        description="是否使用XML智能定位（提升准确率）"
    )


class ExecuteDirectRequest(BaseModel):
    """直接执行请求（生成+执行）"""
    instruction: str = Field(..., description="任务指令")
    device_id: Optional[str] = Field(None, description="设备ID")
    # model_settings 完全可选，不设置时由后端环境变量控制
    model_settings: Optional[Dict[str, Any]] = Field(None, alias="model_config", description="模型配置（可选，留空使用环境变量）")
    prompt_cards: Optional[List[str]] = Field(default=[], description="提示词卡片名称列表")
    use_smart_positioning: bool = Field(
        default=True,
        description="是否使用XML智能定位（提升准确率）"
    )
    
    model_config = {"populate_by_name": True}  # 允许使用别名和字段名


@router.post("/generate")
async def generate_plan(request: GeneratePlanRequest):
    """
    生成任务计划（不立即执行）
    
    规划模式会让AI预先分析任务，生成完整的执行计划，
    用户可以预览和调整后再执行
    """
    try:
        logger.info(f"Generating plan for: {request.instruction}")
        
        # 构建模型配置
        from phone_agent.model import ModelConfig as PhoneAgentModelConfig
        from phone_agent.planning import PlanningAgent
        from server.config import Config
        
        # 加载配置
        config = Config()
        
        # 如果提供了 model_settings，将其转换为 dict
        if request.model_settings:
            model_config_dict = request.model_settings.model_dump(exclude_none=True)
        else:
            model_config_dict = {}
        
        # 优先使用用户指定配置，否则从环境变量获取
        if model_config_dict:
            # 用户指定了配置
            model_name = model_config_dict.get("model_name")
            base_url = model_config_dict.get("base_url")
            api_key = model_config_dict.get("api_key")
            
            # 如果缺少任何配置，从环境变量补全
            if not model_name or not base_url or not api_key:
                from server.utils.model_config_helper import get_model_config_from_env
                env_config = get_model_config_from_env("planning")
                
                model_name = model_name or env_config["model_name"]
                base_url = base_url or env_config["base_url"]
                api_key = api_key or env_config["api_key"]
                
                logger.info(f"部分配置来自环境变量")
            else:
                logger.info(f"使用用户指定配置")
        else:
            # 完全使用环境变量配置
            from server.utils.model_config_helper import get_model_config_from_env
            env_config = get_model_config_from_env("planning")
            
            model_name = env_config["model_name"]
            base_url = env_config["base_url"]
            api_key = env_config["api_key"]
            
        logger.info(f"使用环境变量配置 (MODEL_PROVIDER={config.MODEL_PROVIDER})")
        
        model_config = PhoneAgentModelConfig(
            base_url=base_url,
            api_key=api_key,
            model_name=model_name,
        )
        
        # 详细日志
        logger.info(f"规划模式配置:")
        logger.info(f"   base_url: {base_url}")
        logger.info(f"   model_name: {model_name}")
        logger.info(f"   api_key: {'***' + api_key[-8:] if len(api_key) > 8 else '(未配置)'}")
        
        # 创建规划agent
        planner = PlanningAgent(
            model_config=model_config,
            device_id=request.device_id,
        )
        
        # 生成计划（异步执行，避免阻塞）
        import asyncio
        plan = await asyncio.to_thread(
            planner.generate_plan,
            request.instruction,
            include_screenshot=True
        )
        
        # 验证计划
        is_valid, error_msg = planner.validate_plan(plan)
        if not is_valid:
            raise ValueError(f"Generated plan is invalid: {error_msg}")
        
        logger.info(f"Successfully generated plan with {len(plan.steps)} steps")
        
        return {
            "success": True,
            "plan": plan.to_dict(),
            "message": "计划生成成功"
        }
        
    except Exception as e:
        logger.error(f"Failed to generate plan: {e}", exc_info=True)
        raise HTTPException(500, f"计划生成失败: {str(e)}")


@router.post("/execute")
async def execute_plan(request: ExecutePlanRequest):
    """
    执行已生成的计划
    
    接收预先生成的计划并执行，通过AgentService创建和执行任务
    """
    try:
        logger.info(f"Executing plan with {len(request.plan.get('steps', []))} steps")
        
        # 重建计划对象
        from phone_agent.planning import TaskPlan
        plan = TaskPlan.from_dict(request.plan)
        
        # 通过 AgentService 创建任务
        agent_service = get_agent_service()
        task_id = await agent_service.create_task(
            instruction=plan.instruction,
            device_id=request.device_id,
            model_config=None  # 规划模式已经有计划，不需要模型配置
        )
        
        # 将计划数据附加到任务
        task = agent_service.get_task(task_id)
        if task:
            task.kernel_mode = "planning"  # 标记为规划模式
            # 直接执行任务（在后台）
            from server.services import get_device_pool
            device_pool = get_device_pool()
            
            # 启动异步任务执行（规划模式需要特殊处理）
            async def execute_planning_task():
                try:
                    # 步骤回调：记录到任务
                    def step_callback(step_num: int, step_data: dict, success: bool, message: str):
                        """规划模式步骤回调"""
                        step_info = {
                            "step": step_num,
                            "thinking": f"执行步骤 {step_num}: {step_data.get('target_description', '')}",
                            "action": step_data.get("action_type", ""),
                            "observation": message,
                            "status": "completed" if success else "failed",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "screenshot": None  # 规划模式暂不支持截图
                        }
                        task.steps.append(step_info)
                        task.current_step = step_num
                        
                        # WebSocket推送
                        if agent_service._websocket_broadcast_callback:
                            try:
                                asyncio.run_coroutine_threadsafe(
                                    agent_service._websocket_broadcast_callback({
                                        "type": "task_step_update",
                                        "data": {
                                            "task_id": task_id,
                                            "step": step_num,
                                            "thinking": step_info["thinking"],
                                            "action": step_info["action"],
                                            "observation": message,
                                            "screenshot": None,
                                            "success": success,
                                            "status": step_info["status"],
                                            "timestamp": step_info["timestamp"]
                                        }
                                    }),
                                    asyncio.get_event_loop()
                                )
                            except Exception as e:
                                logger.error(f"Failed to broadcast step: {e}")
                    
                    # 执行计划
                    from phone_agent.planning.executor import PlanExecutor
                    executor = PlanExecutor(
                        device_id=request.device_id,
                        use_xml_positioning=request.use_smart_positioning,
                        step_callback=step_callback
                    )
                    
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now(timezone.utc)
                    await agent_service._persist_task_to_db(task)
                    
                    # 执行计划
                    result = await asyncio.to_thread(executor.execute_plan, plan)
                    
                    # 更新任务状态
                    task.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
                    task.completed_at = datetime.now(timezone.utc)
                    task.result = f"计划执行{'成功' if result.success else '失败'}: {result.completed_steps}/{result.total_steps} 步完成"
                    if not result.success:
                        task.error = result.error_message
                    
                    # 持久化最终状态
                    await agent_service._persist_task_to_db(task)
                    await agent_service._cleanup_completed_task(task_id)
                    
                except Exception as e:
                    logger.error(f"Planning task execution failed: {e}", exc_info=True)
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    task.completed_at = datetime.now(timezone.utc)
                    await agent_service._persist_task_to_db(task)
                    await agent_service._cleanup_completed_task(task_id)
            
            # 在后台执行
            asyncio.create_task(execute_planning_task())
            
            logger.info(f"Plan execution started with task_id: {task_id}")
            
            return {
                "success": True,
                "task_id": task_id,
                "message": "计划执行已开始，可通过task_id查看实时进度"
            }
        else:
            raise HTTPException(500, "Failed to create task")
        
    except Exception as e:
        logger.error(f"Failed to execute plan: {e}", exc_info=True)
        raise HTTPException(500, f"计划执行失败: {str(e)}")


@router.post("/execute-direct")
async def execute_direct(request: ExecuteDirectRequest):
    """
    直接生成并执行（推荐方式）
    
    一步完成：生成计划 + 立即执行，创建任务记录并返回task_id
    这是最快的方式，适合不需要预览的场景
    """
    try:
        logger.info(f"Direct execution: {request.instruction}")
        
        # 导入所需类
        from phone_agent.model import ModelConfig as PhoneAgentModelConfig
        from phone_agent.planning import PlanningAgent
        from server.config import Config
        
        # 加载配置
        config = Config()
        
        # 构建模型配置
        # 如果提供了 model_settings，将其转换为 dict
        if request.model_settings:
            model_config_dict = request.model_settings if isinstance(request.model_settings, dict) else {}
        else:
            model_config_dict = {}
        
        # 优先使用用户指定配置，否则从环境变量获取
        if model_config_dict:
            # 用户指定了配置
            model_name = model_config_dict.get("model_name")
            base_url = model_config_dict.get("base_url")
            api_key = model_config_dict.get("api_key")
            
            # 如果缺少任何配置，从环境变量补全
            if not model_name or not base_url or not api_key:
                from server.utils.model_config_helper import get_model_config_from_env
                env_config = get_model_config_from_env("planning")
                
                model_name = model_name or env_config["model_name"]
                base_url = base_url or env_config["base_url"]
                api_key = api_key or env_config["api_key"]
                
                logger.info(f"部分配置来自环境变量")
            else:
                logger.info(f"使用用户指定配置")
        else:
            # 完全使用环境变量配置
            from server.utils.model_config_helper import get_model_config_from_env
            env_config = get_model_config_from_env("planning")
            
            model_name = env_config["model_name"]
            base_url = env_config["base_url"]
            api_key = env_config["api_key"]
            
        logger.info(f"使用环境变量配置 (MODEL_PROVIDER={config.MODEL_PROVIDER})")
        
        model_config = PhoneAgentModelConfig(
            base_url=base_url,
            api_key=api_key,
            model_name=model_name,
        )
        
        # 详细日志
        logger.info(f"规划模式配置:")
        logger.info(f"   base_url: {base_url}")
        logger.info(f"   model_name: {model_name}")
        logger.info(f"   api_key: {'***' + api_key[-8:] if len(api_key) > 8 else '(未配置)'}")
        
        # 拼接提示词卡片
        enhanced_instruction = request.instruction
        if request.prompt_cards and len(request.prompt_cards) > 0:
            from server.api.prompt_cards import load_prompt_cards
            all_cards = load_prompt_cards()
            
            # 根据名称查找卡片
            selected_cards = []
            for card_name in request.prompt_cards:
                for card in all_cards:
                    if card.name == card_name or card.title == card_name:
                        selected_cards.append(card)
                        break
            
            if selected_cards:
                prompt_cards_content = "\n\n===== 任务优化提示词 =====\n"
                for card in selected_cards:
                    prompt_cards_content += f"\n【{card.title}】\n{card.content}\n"
                prompt_cards_content += "\n===== 提示词结束 =====\n"
                enhanced_instruction = f"{request.instruction}{prompt_cards_content}"
        
        # 生成计划
        planner = PlanningAgent(
            model_config=model_config,
            device_id=request.device_id,
        )
        
        plan = planner.generate_plan(enhanced_instruction, include_screenshot=True)
        
        # 验证计划
        is_valid, error_msg = planner.validate_plan(plan)
        if not is_valid:
            raise ValueError(f"Generated plan is invalid: {error_msg}")
        
        logger.info(f"Generated plan with {len(plan.steps)} steps, executing...")
        
        # 通过 AgentService 创建任务
        agent_service = get_agent_service()
        task_id = await agent_service.create_task(
            instruction=plan.instruction,
            device_id=request.device_id,
            model_config=None
        )
        
        # 将计划数据附加到任务并执行
        task = agent_service.get_task(task_id)
        if task:
            task.kernel_mode = "planning"
            
            # 启动异步任务执行
            async def execute_planning_task():
                try:
                    # 步骤回调：记录到任务
                    def step_callback(step_num: int, step_data: dict, success: bool, message: str):
                        """规划模式步骤回调"""
                        step_info = {
                            "step": step_num,
                            "thinking": f"执行步骤 {step_num}: {step_data.get('target_description', '')}",
                            "action": step_data.get("action_type", ""),
                            "observation": message,
                            "status": "completed" if success else "failed",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "screenshot": None
                        }
                        task.steps.append(step_info)
                        task.current_step = step_num
                        
                        # WebSocket推送
                        if agent_service._websocket_broadcast_callback:
                            try:
                                asyncio.run_coroutine_threadsafe(
                                    agent_service._websocket_broadcast_callback({
                                        "type": "task_step_update",
                                        "data": {
                                            "task_id": task_id,
                                            "step": step_num,
                                            "thinking": step_info["thinking"],
                                            "action": step_info["action"],
                                            "observation": message,
                                            "screenshot": None,
                                            "success": success,
                                            "status": step_info["status"],
                                            "timestamp": step_info["timestamp"]
                                        }
                                    }),
                                    asyncio.get_event_loop()
                                )
                            except Exception as e:
                                logger.error(f"Failed to broadcast step: {e}")
                    
                    from phone_agent.planning.executor import PlanExecutor
                    executor = PlanExecutor(
                        device_id=request.device_id,
                        use_xml_positioning=request.use_smart_positioning,
                        step_callback=step_callback
                    )
                    
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now(timezone.utc)
                    await agent_service._persist_task_to_db(task)
                    
                    # 执行计划
                    result = await asyncio.to_thread(executor.execute_plan, plan)
                    
                    # 更新任务状态
                    task.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
                    task.completed_at = datetime.now(timezone.utc)
                    task.result = f"计划执行{'成功' if result.success else '失败'}: {result.completed_steps}/{result.total_steps} 步完成"
                    if not result.success:
                        task.error = result.error_message
                    
                    # 持久化最终状态
                    await agent_service._persist_task_to_db(task)
                    await agent_service._cleanup_completed_task(task_id)
                    
                except Exception as e:
                    logger.error(f"Planning task execution failed: {e}", exc_info=True)
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    task.completed_at = datetime.now(timezone.utc)
                    await agent_service._persist_task_to_db(task)
                    await agent_service._cleanup_completed_task(task_id)
            
            asyncio.create_task(execute_planning_task())
            
            logger.info(f"Direct execution started with task_id: {task_id}")
            
            return {
                "success": True,
                "task_id": task_id,
                "message": "规划模式任务已开始执行，可通过task_id查看实时进度"
            }
        else:
            raise HTTPException(500, "Failed to create task")
        
    except Exception as e:
        logger.error(f"Failed to execute direct: {e}", exc_info=True)
        raise HTTPException(500, f"任务执行失败: {str(e)}")


@router.get("/prompt-cards")
async def list_prompt_cards():
    """
    列出可用的提示词卡片
    
    返回所有启用的提示词卡片
    """
    try:
        from server.api.prompt_cards import load_prompt_cards
        cards = load_prompt_cards()
        
        # 只返回启用的卡片
        enabled_cards = [card for card in cards if card.enabled]
        
        return {
            "success": True,
            "cards": [
                {
                    "id": card.id,
                    "name": card.name,
                    "title": card.title,
                    "category": card.category,
                    "tags": card.tags
                }
                for card in enabled_cards
            ],
            "count": len(enabled_cards)
        }
        
    except Exception as e:
        logger.error(f"Failed to list prompt cards: {e}", exc_info=True)
        raise HTTPException(500, f"获取提示词卡片失败: {str(e)}")

