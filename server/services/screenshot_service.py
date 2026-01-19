#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
截图服务

负责截图的保存、管理和查询
最小改动集成到现有系统
"""

import os
import json
import hashlib
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from PIL import Image
import base64
from io import BytesIO

from server.models.screenshot import StepScreenshot, TaskScreenshotSummary

logger = logging.getLogger(__name__)


class ScreenshotService:
    """
    截图服务 - 统一管理截图
    
    职责：
    1. 保存和管理截图
    2. 生成缩略图
    3. 提供查询接口
    4. 支持导出
    """
    
    def __init__(self, base_dir: str = "data/screenshots"):
        self.base_dir = Path(base_dir)
        self.tasks_dir = self.base_dir / "tasks"
        self.devices_dir = self.base_dir / "devices"
        self.cache_dir = self.base_dir / "cache"
        
        # 创建目录
        for d in [self.tasks_dir, self.devices_dir, self.cache_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    async def save_step_screenshot(
        self,
        task_id: str,
        device_id: str,
        step_number: int,
        screenshot_base64: str,
        action: dict,
        thinking: str,
        observation: str,
        success: bool,
        kernel_mode: str,
        tokens_used: Optional[dict] = None
    ) -> StepScreenshot:
        """
        保存单步截图
        
 性能优化：         1. 异步并行压缩（4级同时处理）
        2. 优先使用yadb截图
        3. 恢复原有的compress_screenshot_async
        
        性能：~100ms（vs 旧版~400ms）
        """
        try:
            # 创建任务目录
            task_dir = self.tasks_dir / task_id
            steps_dir = task_dir / "steps"
            steps_dir.mkdir(parents=True, exist_ok=True)
            
            # 解码截图
            screenshot_data = base64.b64decode(screenshot_base64)
            
            # 1. 保存原始截图（PNG）
            original_filename = f"step_{step_number:03d}_original.png"
            original_path = steps_dir / original_filename
            with open(original_path, "wb") as f:
                f.write(screenshot_data)
            
            # 2. 异步并行压缩（使用原有的优化函数）
            from server.utils.image_utils import compress_screenshot_async
            
            # 并行生成所有级别（ai, medium, small）
            compressed_result = await compress_screenshot_async(
                str(original_path),
                str(steps_dir),
                for_ai=True  # 生成ai/medium/small三个级别
            )
            
            # 3. 映射路径（容错处理：如果压缩失败，使用原图）
            ai_path = Path(compressed_result.get("ai") or str(original_path))
            medium_path = Path(compressed_result.get("medium") or str(original_path))
            small_path = Path(compressed_result.get("small") or str(original_path))
            
            # 补充thumbnail级别（如果需要更小的）
            thumb_filename = f"step_{step_number:03d}_thumb.jpg"
            thumb_path = steps_dir / thumb_filename
            if not thumb_path.exists():
                # 快速生成thumbnail（从small缩小）
                await asyncio.to_thread(
                    self._create_thumbnail_from_jpg,
                    str(small_path),
                    str(thumb_path),
                    width=320
                )
            
            # 计算文件hash和大小
            file_hash = hashlib.sha256(screenshot_data).hexdigest()
            file_size = len(screenshot_data)
            
            # 构建相对路径
            rel_original = str(original_path.relative_to(self.base_dir))
            rel_ai = str(ai_path.relative_to(self.base_dir)) if ai_path.exists() else None
            rel_medium = str(medium_path.relative_to(self.base_dir)) if medium_path.exists() else None
            rel_small = str(small_path.relative_to(self.base_dir)) if small_path.exists() else None
            rel_thumb = str(thumb_path.relative_to(self.base_dir)) if thumb_path.exists() else None
            
            # 扩展元数据：包含所有级别路径
            metadata = StepScreenshot(
                task_id=task_id,
                device_id=device_id,
                step_number=step_number,
                timestamp=datetime.now(),
                original_path=rel_original,
                thumbnail_path=rel_thumb or rel_small,  # fallback
                action=action,
                thinking=thinking,
                observation=observation,
                success=success,
                tokens_used=tokens_used,
                kernel_mode=kernel_mode,
                file_hash=file_hash,
                file_size=file_size
            )
            
            # 保存步骤元数据（包含所有路径）
            meta_filename = f"step_{step_number:03d}.json"
            meta_path = steps_dir / meta_filename
            
            # 扩展保存信息
            meta_dict = metadata.dict()
            meta_dict["all_levels"] = {
                "original": rel_original,
                "ai": rel_ai,
                "medium": rel_medium,
                "small": rel_small,
                "thumbnail": rel_thumb
            }
            
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta_dict, f, ensure_ascii=False, indent=2, default=str)
            
            # 创建/更新设备索引
            self._update_device_index(device_id, task_id)
            
            logger.info(f"Async compression completed for task {task_id} step {step_number}")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to save screenshot: {e}", exc_info=True)
            raise
    
    def _create_thumbnail_from_jpg(self, input_jpg: str, output_jpg: str, width: int = 320):
        """从已压缩的JPG快速生成thumbnail"""
        try:
            from PIL import Image
            img = Image.open(input_jpg)
            ratio = width / img.width
            height = int(img.height * ratio)
            img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
            img_resized.save(output_jpg, "JPEG", quality=70, optimize=True)
        except Exception as e:
            logger.error(f"Failed to create thumbnail from jpg: {e}")
    
    def init_task(
        self,
        task_id: str,
        device_id: str,
        instruction: str,
        model_config: Optional[dict] = None
    ):
        """
        初始化任务（创建任务信息文件）
        
        在task创建时调用
        """
        try:
            task_dir = self.tasks_dir / task_id
            task_dir.mkdir(parents=True, exist_ok=True)
            
            task_info = {
                "task_id": task_id,
                "device_id": device_id,
                "instruction": instruction,
                "model_config": model_config or {},
                "created_at": datetime.now().isoformat(),
                "status": "pending"
            }
            
            info_path = task_dir / "task_info.json"
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump(task_info, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Initialized task {task_id}")
        except Exception as e:
            logger.error(f"Failed to init task: {e}")
    
    def complete_task(
        self,
        task_id: str,
        status: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
        total_tokens: int = 0,
        total_prompt_tokens: int = 0,
        total_completion_tokens: int = 0
    ):
        """
        任务完成时生成摘要
        
        在task完成时调用
        """
        try:
            task_dir = self.tasks_dir / task_id
            if not task_dir.exists():
                logger.warning(f"Task directory not found: {task_id}")
                return
            
            # 读取task_info
            info_path = task_dir / "task_info.json"
            if not info_path.exists():
                logger.warning(f"Task info not found: {task_id}")
                return
                
            with open(info_path, "r", encoding="utf-8") as f:
                task_info = json.load(f)
            
            # 统计截图
            steps_dir = task_dir / "steps"
            total_steps = len(list(steps_dir.glob("step_*.json"))) if steps_dir.exists() else 0
            
            # 计算总大小
            total_size = sum(
                f.stat().st_size 
                for f in steps_dir.rglob("*") 
                if f.is_file()
            ) if steps_dir.exists() else 0
            
            # 创建摘要
            summary = TaskScreenshotSummary(
                task_id=task_id,
                device_id=task_info["device_id"],
                instruction=task_info["instruction"],
                created_at=datetime.fromisoformat(task_info["created_at"]),
                completed_at=datetime.now(),
                status=status,
                total_steps=total_steps,
                success=(status == "completed"),
                total_tokens=total_tokens,
                total_prompt_tokens=total_prompt_tokens,
                total_completion_tokens=total_completion_tokens,
                result=result,
                error=error,
                screenshots_dir=f"tasks/{task_id}/steps",
                total_size=total_size
            )
            
            # 保存摘要
            summary_path = task_dir / "summary.json"
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary.dict(), f, ensure_ascii=False, indent=2, default=str)
            
                logger.info(f"Task {task_id} completed, summary saved")
        except Exception as e:
            logger.error(f"Failed to complete task: {e}", exc_info=True)
    
    def get_task_screenshots(self, task_id: str) -> Optional[List[StepScreenshot]]:
        """获取任务的所有截图"""
        steps_dir = self.tasks_dir / task_id / "steps"
        if not steps_dir.exists():
            return None
        
        screenshots = []
        for meta_file in sorted(steps_dir.glob("step_*.json")):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    screenshots.append(StepScreenshot(**json.load(f)))
            except Exception as e:
                logger.error(f"Failed to load screenshot metadata: {e}")
        
        return screenshots
    
    def get_task_summary(self, task_id: str) -> Optional[TaskScreenshotSummary]:
        """获取任务摘要"""
        summary_path = self.tasks_dir / task_id / "summary.json"
        if not summary_path.exists():
            return None
        
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                return TaskScreenshotSummary(**json.load(f))
        except Exception as e:
            logger.error(f"Failed to load task summary: {e}")
            return None
    
    def get_device_tasks(self, device_id: str) -> List[str]:
        """获取设备的所有任务ID"""
        device_dir = self.devices_dir / device_id
        if not device_dir.exists():
            return []
        
        task_ids = []
        for item in device_dir.iterdir():
            if item.is_symlink():
                task_ids.append(item.name)
            elif item.suffix == '.txt':  # Windows fallback
                task_ids.append(item.stem)
        
        return task_ids
    
    def export_task(self, task_id: str, output_path: str) -> str:
        """
        导出任务为压缩包
        
        用于传递给其他agent/平台
        """
        import tarfile
        
        task_dir = self.tasks_dir / task_id
        if not task_dir.exists():
            raise ValueError(f"任务 {task_id} 不存在")
        
        with tarfile.open(output_path, "w:gz") as tar:
            tar.add(task_dir, arcname=task_id)
        
            logger.info(f"Exported task {task_id} to {output_path}")
            return output_path
    
    def _create_thumbnail(self, image_data: bytes, output_path: Path, width: int = 320):
        """生成缩略图"""
        try:
            img = Image.open(BytesIO(image_data))
            
            # 计算高度保持比例
            ratio = width / img.width
            height = int(img.height * ratio)
            
            # 调整大小
            img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
            
            # 保存为JPEG
            img_resized.convert("RGB").save(output_path, "JPEG", quality=85, optimize=True)
        except Exception as e:
            logger.error(f"Failed to create thumbnail: {e}")
    
    def _update_device_index(self, device_id: str, task_id: str):
        """更新设备索引（创建软链接或文本文件）"""
        try:
            device_dir = self.devices_dir / device_id
            device_dir.mkdir(parents=True, exist_ok=True)
            
            link_path = device_dir / task_id
            target_path = Path("../../tasks") / task_id
            
            # 如果链接不存在则创建
            if not link_path.exists():
                try:
                    link_path.symlink_to(target_path)
                except (OSError, NotImplementedError):
                    # Windows上可能需要管理员权限，fallback到文本文件
                    with open(link_path.with_suffix('.txt'), 'w') as f:
                        f.write(str(target_path))
        except Exception as e:
            logger.error(f"Failed to update device index: {e}")


# 全局单例
_screenshot_service: Optional[ScreenshotService] = None


def get_screenshot_service() -> ScreenshotService:
    """获取全局截图服务实例"""
    global _screenshot_service
    if _screenshot_service is None:
        _screenshot_service = ScreenshotService()
    return _screenshot_service
