#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
PC Agent 服务 - PC 任务管理

职责:
1. PC 任务管理 (创建、执行、取消、查询)
2. Agent 调度和执行
3. 状态跟踪和回调通知
4. 与 WebSocket 设备池对接
5. 截图保存和日志记录

复用:
- ScreenshotService (截图)
- TaskLogger (日志)
- ModelCallTracker (模型统计)
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional

from server.pc import PCAgent, PCCallback, PCTask, PCTaskStatus
from server.services.screenshot_service import ScreenshotService
from phone_agent.logging import TaskLogger

logger = logging.getLogger(__name__)


class PCAgentService:
    """
    PC Agent 服务
    
    管理 PC Agent 任务的生命周期,复用现有的通用服务。
    
    Attributes:
        tasks (Dict[str, PCTask]): 任务字典
        _running_task_handles (Dict): 运行中的 asyncio 任务
        screenshot_service (ScreenshotService): 截图服务
        model_client: VLM 模型客户端
    """
    
    def __init__(self):
        """初始化 PC Agent 服务"""
        self.tasks: Dict[str, PCTask] = {}
        self._running_task_handles: Dict[str, asyncio.Task] = {}
        
        # 复用通用服务
        self.screenshot_service = ScreenshotService()
        
        # 模型客户端 (需要外部设置)
        self.model_client = None
        
        logger.info("PC Agent 服务已初始化")
    
    async def create_task(
        self,
        instruction: str,
        device_id: str,
        kernel_mode: str = "vision",
        max_steps: int = 30,
        **kwargs
    ) -> str:
        """
        创建 PC 任务
        
        Args:
            instruction: 用户指令
            device_id: 设备 ID
            kernel_mode: Kernel 模式 (默认 vision)
            max_steps: 最大步骤数
            **kwargs: 其他配置
            
        Returns:
            任务 ID
        """
        task = PCTask(
            task_id=str(uuid.uuid4()),
            instruction=instruction,
            device_id=device_id,
            config={
                "kernel_mode": kernel_mode,
                "max_steps": max_steps,
                **kwargs
            }
        )
        
        self.tasks[task.task_id] = task
        
        logger.info(f"PC 任务已创建: {task.task_id}")
        return task.task_id
    
    async def execute_task(
        self,
        task_id: str,
        websocket_server=None
    ) -> bool:
        """
        执行 PC 任务
        
        Args:
            task_id: 任务 ID
            websocket_server: WebSocket 服务器 (用于获取 FRP 端口)
            
        Returns:
            是否成功启动
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return False
        
        # 获取设备的 FRP 端口
        frp_port = await self._get_frp_port(task.device_id, websocket_server)
        if not frp_port:
            logger.error(f"无法获取设备 FRP 端口: {task.device_id}")
            task.status = PCTaskStatus.FAILED
            task.error = "设备未连接或 FRP 未就绪"
            return False
        
        # 异步执行任务
        asyncio_task = asyncio.create_task(
            self._run_agent(task, frp_port)
        )
        self._running_task_handles[task_id] = asyncio_task
        
        logger.info(f"PC 任务已启动: {task_id}")
        return True
    
    async def _run_agent(self, task: PCTask, frp_port: int):
        """
        运行 Agent (内部方法)
        
        Args:
            task: PC 任务对象
            frp_port: FRP 端口
        """
        from datetime import datetime, timezone
        
        try:
            task.status = PCTaskStatus.RUNNING
            task.started_at = datetime.now(timezone.utc)
            
            # 创建 PC Agent
            agent = PCAgent(
                device_id=task.device_id,
                frp_port=frp_port,
                model_client=self.model_client,
                config=task.config
            )
            task.agent = agent
            
            # 创建回调（日志目录与手机版本保持一致）
            callback = PCCallback(
                task=task,
                screenshot_service=self.screenshot_service,
                task_logger=TaskLogger(log_dir="logs")
            )
            
            # 执行任务
            result = await agent.run(task.instruction, callback)
            
            # 更新状态
            task.status = PCTaskStatus.COMPLETED if result["success"] else PCTaskStatus.FAILED
            task.result = result.get("message")
            task.completed_at = datetime.now(timezone.utc)
            
            # 持久化到数据库
            await self._persist_task(task)
            
            logger.info(f"PC 任务完成: {task.task_id}, 状态: {task.status.value}")
        
        except Exception as e:
            logger.error(f"PC 任务执行失败: {e}", exc_info=True)
            task.status = PCTaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now(timezone.utc)
            
            # 持久化错误状态
            await self._persist_task(task)
        
        finally:
            # 清理
            if task.task_id in self._running_task_handles:
                del self._running_task_handles[task.task_id]
    
    async def _get_frp_port(
        self,
        device_id: str,
        websocket_server=None
    ) -> Optional[int]:
        """
        获取设备的 FRP 端口
        
        通过 HTTP API 从 WebSocket 服务器查询（与 AI 手机架构一致）
        
        Args:
            device_id: 设备 ID
            websocket_server: 已废弃，保留参数兼容性
            
        Returns:
            FRP 端口或 None
        """
        try:
            import httpx
            # 通过 HTTP API 查询设备信息（与 AI 手机架构一致）
            websocket_url = f"http://127.0.0.1:9999/devices/{device_id}"
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(websocket_url)
                
                if response.status_code == 200:
                    device_info = response.json()
                    frp_port = device_info.get("frp_port")
                    
                    if not frp_port:
                        logger.warning(f"设备 {device_id} 未配置 FRP 端口")
                        return None
                    
                    logger.info(f"从 WebSocket 服务器获取到设备 {device_id} 的 FRP 端口: {frp_port}")
                    return frp_port
                elif response.status_code == 404:
                    logger.warning(f"设备不存在: {device_id}")
                    return None
                else:
                    logger.error(f"查询设备失败: HTTP {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"无法从 WebSocket 服务器获取设备信息: {e}")
            return None
    
    async def _persist_task(self, task: PCTask):
        """
        持久化任务到数据库 (使用独立的 PC 表)
        
        Args:
            task: PC 任务对象
        """
        try:
            import json
            from server.database.session import get_db
            from server.database import pc_crud
            
            db = next(get_db())
            
            try:
                # 检查任务是否已存在
                existing_task = pc_crud.get_pc_task(db, task.task_id)
                
                if existing_task:
                    # 更新任务
                    pc_crud.update_pc_task(
                        db=db,
                        task_id=task.task_id,
                        status=task.status.value,
                        steps_count=len(task.steps),
                        steps_detail=json.dumps(task.steps, ensure_ascii=False),
                        result=task.result,
                        error=task.error,
                        started_at=task.started_at,
                        completed_at=task.completed_at,
                        total_tokens=task.total_tokens,
                        total_prompt_tokens=task.total_prompt_tokens,
                        total_completion_tokens=task.total_completion_tokens
                    )
                else:
                    # 创建任务
                    pc_crud.create_pc_task(
                        db=db,
                        task_id=task.task_id,
                        instruction=task.instruction,
                        device_id=task.device_id,
                        status=task.status.value,
                        created_at=task.created_at,
                        started_at=task.started_at,
                        completed_at=task.completed_at,
                        result=task.result,
                        error=task.error,
                        steps_count=len(task.steps),
                        steps_detail=json.dumps(task.steps, ensure_ascii=False),
                        total_tokens=task.total_tokens,
                        total_prompt_tokens=task.total_prompt_tokens,
                        total_completion_tokens=task.total_completion_tokens,
                        model_config=json.dumps(task.config, ensure_ascii=False)
                    )
                
                logger.info(f"PC 任务已持久化: {task.task_id}")
            
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"持久化任务失败: {e}", exc_info=True)
    
    def get_task(self, task_id: str) -> Optional[PCTask]:
        """
        获取任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            PC 任务对象或 None
        """
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[PCTask]:
        """
        获取所有任务
        
        Returns:
            任务列表
        """
        return list(self.tasks.values())
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            是否成功取消
        """
        from datetime import datetime, timezone
        
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"任务不存在: {task_id}")
            return False
        
        if task.status != PCTaskStatus.RUNNING:
            logger.warning(f"任务不在运行状态: {task_id}")
            return False
        
        # 取消 asyncio 任务
        if task_id in self._running_task_handles:
            self._running_task_handles[task_id].cancel()
            del self._running_task_handles[task_id]
        
        task.status = PCTaskStatus.CANCELLED
        task.completed_at = datetime.now(timezone.utc)
        
        # 持久化
        await self._persist_task(task)
        
        logger.info(f"PC 任务已取消: {task_id}")
        return True
    
    def set_model_client(self, model_client):
        """
        设置模型客户端
        
        Args:
            model_client: VLM 模型客户端
        """
        self.model_client = model_client
        logger.info("模型客户端已设置")


# 全局单例
_pc_agent_service: Optional[PCAgentService] = None


def get_pc_agent_service() -> PCAgentService:
    """
    获取 PC Agent 服务单例
    
    Returns:
        PCAgentService 实例
    """
    global _pc_agent_service
    if _pc_agent_service is None:
        _pc_agent_service = PCAgentService()
    return _pc_agent_service
