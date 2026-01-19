#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
应用配置管理 API
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field

from phone_agent.config.app_manager import get_app_manager, AppConfig

router = APIRouter()


class AppConfigRequest(BaseModel):
    """应用配置请求（匹配前端字段）"""
    display_name: str = Field(..., description="中文显示名", example="微信")
    display_name_en: Optional[str] = Field(None, description="英文显示名", example="WeChat")
    aliases: Optional[str] = Field(None, description="别名（逗号分隔）", example="weixin,WX,微信")
    package_name: str = Field(..., description="Android应用包名", example="com.tencent.mm")
    category: str = Field(default="其他", description="分类", example="社交")
    description: Optional[str] = Field(None, description="应用描述", example="微信聊天应用")
    enabled: bool = Field(default=True, description="是否启用")


class AppConfigResponse(BaseModel):
    """应用配置响应"""
    package_name: str
    display_name: str
    display_name_en: Optional[str] = None
    aliases: List[str] = []
    description: Optional[str] = None
    enabled: bool = True
    category: str = "其他"
    icon: Optional[str] = None
    version: Optional[str] = None
    last_updated: Optional[str] = None


class SyncRequest(BaseModel):
    """同步请求"""
    device_id: Optional[str] = Field(None, description="设备ID（可选，不指定则使用第一个在线设备）")
    auto_enable: bool = Field(False, description="是否自动启用所有应用")
    merge_mode: str = Field("add_new", description="合并模式: add_new | update_all | replace")


@router.get("/apps", tags=["应用管理"], response_model=dict)
async def list_apps(
    enabled_only: bool = False,
    category: Optional[str] = None
):
    """
    获取应用列表
    
    Args:
        enabled_only: 只返回启用的应用
        category: 按分类筛选
    """
    manager = get_app_manager()
    apps = manager.get_all_apps(enabled_only=enabled_only)
    
    # 按分类筛选
    if category and category != "全部":
        apps = [app for app in apps if app.category == category]
    
    # 转换为前端格式
    apps_data = []
    for app in apps:
        apps_data.append({
            "package_name": app.package_name,
            "display_name": app.display_name,
            "display_name_en": app.display_name_en,
            "aliases": app.aliases,
            "description": app.description,
            "enabled": app.enabled,
            "category": app.category,
            "icon": app.icon,
            "version": app.version,
            "last_updated": app.last_updated
        })
    
    # 获取统计信息
    stats = manager.get_stats()
    
    return {
        "apps": apps_data,
        "total": len(apps_data),
        "stats": stats
    }


@router.get("/apps/{package_name}", tags=["应用管理"])
async def get_app(package_name: str):
    """获取应用详情"""
    manager = get_app_manager()
    app = manager.get_app(package_name)
    
    if not app:
        raise HTTPException(404, f"应用不存在: {package_name}")
    
    return {
        "package_name": app.package_name,
        "display_name": app.display_name,
        "display_name_en": app.display_name_en,
        "aliases": app.aliases,
        "description": app.description,
        "enabled": app.enabled,
        "category": app.category,
        "icon": app.icon,
        "version": app.version,
        "last_updated": app.last_updated
    }


@router.post("/apps", tags=["应用管理"])
async def create_or_update_app(app_data: AppConfigRequest):
    """
    创建或更新应用配置
    
    前端字段映射:
    - display_name: 中文显示名（必需）
    - display_name_en: 英文显示名（可选）
    - aliases: 别名字符串，逗号分隔（可选）
    - package_name: 包名（必需，不可修改）
    - category: 分类
    - description: 描述
    - enabled: 是否启用
    """
    manager = get_app_manager()
    
    # 处理别名：从逗号分隔字符串转为列表
    aliases_list = []
    if app_data.aliases:
        aliases_list = [a.strip() for a in app_data.aliases.split(',') if a.strip()]
    
    app = AppConfig(
        package_name=app_data.package_name,
        display_name=app_data.display_name,
        display_name_en=app_data.display_name_en,
        aliases=aliases_list,
        description=app_data.description,
        enabled=app_data.enabled,
        category=app_data.category
    )
    
    success = manager.add_or_update_app(app)
    
    if not success:
        raise HTTPException(500, "保存配置失败")
    
    return {
        "message": "保存成功",
        "app": {
            "package_name": app.package_name,
            "display_name": app.display_name,
            "display_name_en": app.display_name_en,
            "aliases": app.aliases,
            "description": app.description,
            "enabled": app.enabled,
            "category": app.category
        }
    }


@router.patch("/apps/{package_name}/toggle", tags=["应用管理"])
async def toggle_app(
    package_name: str,
    enabled: bool = Body(..., embed=True)
):
    """
    启用/禁用应用
    
    请求体: {"enabled": true}
    """
    manager = get_app_manager()
    
    success = manager.set_app_enabled(package_name, enabled)
    
    if not success:
        raise HTTPException(404, f"应用不存在: {package_name}")
    
    status = "启用" if enabled else "禁用"
    return {
        "message": f"应用已{status}",
        "package_name": package_name,
        "enabled": enabled
    }


@router.delete("/apps/{package_name}", tags=["应用管理"])
async def delete_app(package_name: str):
    """删除应用配置"""
    manager = get_app_manager()
    
    success = manager.remove_app(package_name)
    
    if not success:
        raise HTTPException(404, f"应用不存在: {package_name}")
    
    return {"message": "删除成功", "package_name": package_name}


# ========================================
# 已弃用的扫描功能（保留API以保持向后兼容）
# ========================================
# 原因：扫描出的包名为英文，用户体验差
# 替代方案：使用200+预置应用 + 手动添加
# ========================================

# 应用扫描缓存（设备ID -> (应用列表, 过期时间)） _app_scan_cache = {}
_cache_ttl_seconds = 300  # 5分钟缓存

@router.post("/apps/scan", tags=["应用管理"], deprecated=True)
async def scan_device_apps(device_id: Optional[str] = None):
    """
    已弃用：扫描设备上的应用（优化版 - 添加缓存）
    
    不建议使用原因：
    - 扫描出的包名为英文，用户体验差
    - 建议使用200+预置应用 + 手动添加
    
    仅扫描，不保存到配置
    """
    import time
    
    # 检查缓存
    cache_key = device_id or "default"
    now = time.time()
    
    if cache_key in _app_scan_cache:
        cached_apps, expire_time = _app_scan_cache[cache_key]
        if now < expire_time:
            logger.info(f"Using cached app list for {cache_key}")
            return {
                "apps": cached_apps,
                "total": len(cached_apps),
                "message": f"扫描到 {len(cached_apps)} 个应用（缓存）",
                "cached": True
            }
    
    # 缓存未命中，执行扫描
    manager = get_app_manager()
    apps = manager.scan_device_apps(device_id)
    
    if not apps:
        raise HTTPException(500, "扫描失败或设备无应用")
    
    # 更新缓存
    _app_scan_cache[cache_key] = (apps, now + _cache_ttl_seconds)
    
    return {
        "apps": apps,
        "total": len(apps),
        "message": f"扫描到 {len(apps)} 个应用",
        "cached": False
    }


@router.post("/apps/sync", tags=["应用管理"], deprecated=True)
async def sync_device_apps(request: SyncRequest):
    """
    已弃用：从设备同步应用到配置文件（异步优化版本）
    
    不建议使用原因：
    - 扫描出的包名为英文，用户体验差
    - 建议使用200+预置应用 + 手动添加
    - 前端"扫描设备应用"按钮已移除
    
    建议在设备连接后调用，自动扫描并更新应用列表
    
    Args:
        device_id: 设备ID（可选）
        auto_enable: 是否自动启用所有应用（默认false，新应用默认禁用）
        merge_mode: 合并模式
            - add_new: 只添加新应用，保留现有配置（推荐）
            - update_all: 更新所有应用
            - replace: 完全替换配置文件
    """
    import asyncio
    manager = get_app_manager()
    
    # 异步执行同步操作，避免阻塞事件循环
    sync_result = await asyncio.to_thread(
        manager.sync_from_device,
        device_id=request.device_id,
        auto_enable=request.auto_enable,
        merge_mode=request.merge_mode
    )
    
    new_apps = sync_result.get("new_apps", 0)
    removed_apps = sync_result.get("removed_apps", 0)
    kept_apps = sync_result.get("kept_apps", 0)
    
    if new_apps == 0 and removed_apps == 0:
        return {
            "message": "没有新应用需要同步",
            "new_apps": 0,
            "removed_apps": 0,
            "kept_apps": kept_apps,
            "tip": "所有应用已是最新"
        }
    
    stats = manager.get_stats()
    
    tip = None
    if not request.auto_enable and new_apps > 0:
        tip = f"新增了 {new_apps} 个应用（默认禁用），请到应用管理页面启用需要的应用"
    return {
        "message": f"同步成功，新增 {new_apps} 个，删除 {removed_apps} 个，保留 {kept_apps} 个",
        "new_apps": new_apps,
        "removed_apps": removed_apps,
        "kept_apps": kept_apps,
        "stats": stats,
        "tip": tip
    }


@router.get("/apps/categories", tags=["应用管理"])
async def get_categories():
    """获取所有分类"""
    manager = get_app_manager()
    stats = manager.get_stats()
    
    categories = [
        {"name": "全部", "count": stats["total"]},
        {"name": "社交", "count": stats["categories"].get("社交", 0)},
        {"name": "购物", "count": stats["categories"].get("购物", 0)},
        {"name": "金融", "count": stats["categories"].get("金融", 0)},
        {"name": "娱乐", "count": stats["categories"].get("娱乐", 0)},
        {"name": "系统", "count": stats["categories"].get("系统", 0)},
        {"name": "游戏", "count": stats["categories"].get("游戏", 0)},
        {"name": "拍照", "count": stats["categories"].get("拍照", 0)},
        {"name": "工具", "count": stats["categories"].get("工具", 0)},
        {"name": "其他", "count": stats["categories"].get("其他", 0)},
    ]
    
    return {"categories": categories}


@router.get("/apps/stats", tags=["应用管理"])
async def get_stats():
    """获取应用统计信息"""
    manager = get_app_manager()
    stats = manager.get_stats()
    
    return stats


@router.post("/apps/search", tags=["应用管理"])
async def search_app(name: str = Body(..., embed=True)):
    """
    搜索应用
    
    支持包名、中文名、英文名、别名搜索
    
    请求体: {"name": "微信"}
    """
    manager = get_app_manager()
    app = manager.find_app(name)
    
    if not app:
        raise HTTPException(404, f"未找到应用: {name}")
    
    return {
        "package_name": app.package_name,
        "display_name": app.display_name,
        "display_name_en": app.display_name_en,
        "aliases": app.aliases,
        "description": app.description,
        "enabled": app.enabled,
        "category": app.category
    }


@router.post("/apps/batch-toggle", tags=["应用管理"])
async def batch_toggle_apps(
    package_names: List[str] = Body(..., embed=True),
    enabled: bool = Body(..., embed=True)
):
    """
    批量启用/禁用应用
    
    请求体: {
        "package_names": ["com.tencent.mm", "com.taobao.taobao"],
        "enabled": true
    }
    """
    manager = get_app_manager()
    
    success_count = 0
    failed = []
    
    for package_name in package_names:
        if manager.set_app_enabled(package_name, enabled):
            success_count += 1
        else:
            failed.append(package_name)
    
    status = "启用" if enabled else "禁用"
    
    return {
        "message": f"批量{status}完成",
        "success_count": success_count,
        "failed_count": len(failed),
        "failed": failed
    }


