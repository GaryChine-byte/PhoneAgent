#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
截图API接口

提供截图查询、下载、导出等功能
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import List
from pathlib import Path

from server.services.screenshot_service import get_screenshot_service
from server.models.screenshot import StepScreenshot, TaskScreenshotSummary

router = APIRouter(prefix="/api/screenshots", tags=["screenshots"])


@router.get("/task/{task_id}/summary", response_model=TaskScreenshotSummary)
async def get_task_summary(task_id: str):
    """获取任务截图摘要"""
    service = get_screenshot_service()
    summary = service.get_task_summary(task_id)
    
    if not summary:
        raise HTTPException(status_code=404, detail="任务不存在或未完成")
    
    return summary


@router.get("/task/{task_id}/steps", response_model=List[StepScreenshot])
async def get_task_steps(task_id: str):
    """获取任务的所有步骤截图元数据"""
    service = get_screenshot_service()
    screenshots = service.get_task_screenshots(task_id)
    
    if screenshots is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return screenshots


@router.get("/task/{task_id}/step/{step_number}/image")
async def get_step_image(
    task_id: str, 
    step_number: int,
    thumb: bool = False  # 是否返回缩略图
):
    """
    获取步骤截图文件
    
    Args:
        task_id: 任务ID
        step_number: 步骤编号
        thumb: 是否返回缩略图（默认False返回原图）
    """
    service = get_screenshot_service()
    screenshots = service.get_task_screenshots(task_id)
    
    if not screenshots:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 查找对应步骤
    target_screenshot = None
    for s in screenshots:
        if s.step_number == step_number:
            target_screenshot = s
            break
    
    if not target_screenshot:
        raise HTTPException(status_code=404, detail=f"步骤 {step_number} 不存在")
    
    # 确定文件路径
    file_path = Path("data/screenshots") / (
        target_screenshot.thumbnail_path if thumb 
        else target_screenshot.original_path
    )
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(file_path)


@router.get("/device/{device_id}/tasks")
async def get_device_tasks(device_id: str):
    """
    获取设备的所有任务
    
    Args:
        device_id: 设备ID
    """
    service = get_screenshot_service()
    task_ids = service.get_device_tasks(device_id)
    
    return {
        "device_id": device_id,
        "task_ids": task_ids,
        "count": len(task_ids)
    }


@router.post("/task/{task_id}/export")
async def export_task(task_id: str):
    """
    导出任务为压缩包
    
    用于传递给其他agent/平台分析
    
    Args:
        task_id: 任务ID
    """
    service = get_screenshot_service()
    
    output_path = f"data/screenshots/cache/{task_id}.tar.gz"
    try:
        service.export_task(task_id, output_path)
        return FileResponse(
            output_path,
            filename=f"{task_id}.tar.gz",
            media_type="application/gzip",
            headers={
                "Content-Disposition": f"attachment; filename={task_id}.tar.gz"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.get("/stats")
async def get_statistics():
    """获取截图系统统计信息"""
    tasks_dir = Path("data/screenshots/tasks")
    
    if not tasks_dir.exists():
        return {
            "total_tasks": 0,
            "total_size_mb": 0,
            "storage_path": str(tasks_dir.absolute())
        }
    
    # 统计所有任务
    total_tasks = len(list(tasks_dir.iterdir()))
    
    # 统计总大小
    total_size = sum(
        f.stat().st_size 
        for f in tasks_dir.rglob("*") 
        if f.is_file()
    )
    
    return {
        "total_tasks": total_tasks,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "storage_path": str(tasks_dir.absolute())
    }
