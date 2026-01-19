#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
快捷指令管理API
支持预置指令和用户自定义指令
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)
router = APIRouter()

# 配置文件路径
SHORTCUTS_FILE = "data/shortcuts.json"

# 内存缓存（避免每次都读取文件）
_shortcuts_cache = None
_cache_timestamp = 0
CACHE_TTL = 60  # 缓存60秒


class Shortcut(BaseModel):
    """快捷指令"""
    id: str                          # 指令ID
    title: str                       # 指令标题（用于语音识别）
    instruction: str                 # 指令内容
    category: str = "自定义"          # 分类
    is_system: bool = False          # 是否系统预置
    voice_keywords: List[str] = []   # 语音关键词（用于匹配）
    created_at: str                  # 创建时间
    updated_at: str                  # 更新时间
    use_count: int = 0               # 使用次数


class ShortcutCreateRequest(BaseModel):
    """创建快捷指令请求"""
    title: str
    instruction: str
    category: str = "自定义"
    voice_keywords: List[str] = []


class ShortcutUpdateRequest(BaseModel):
    """更新快捷指令请求"""
    title: Optional[str] = None
    instruction: Optional[str] = None
    category: Optional[str] = None
    voice_keywords: Optional[List[str]] = None


class ShortcutsResponse(BaseModel):
    """快捷指令列表响应"""
    shortcuts: List[Shortcut]
    total: int
    system_count: int
    custom_count: int


def load_shortcuts(force_reload: bool = False) -> List[Shortcut]:
    """
    加载快捷指令（带缓存）
    
    Args:
        force_reload: 强制重新加载，忽略缓存
    """
    global _shortcuts_cache, _cache_timestamp
    import time
    
    # 检查缓存
    if not force_reload and _shortcuts_cache is not None:
        if time.time() - _cache_timestamp < CACHE_TTL:
            return _shortcuts_cache
    
    os.makedirs("data", exist_ok=True)
    
    if not os.path.exists(SHORTCUTS_FILE):
        shortcuts = initialize_shortcuts()
    else:
        try:
            with open(SHORTCUTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                shortcuts = [Shortcut(**item) for item in data]
        except Exception as e:
            logger.warning(f"Failed to load shortcuts from {SHORTCUTS_FILE}: {e}")
            shortcuts = initialize_shortcuts()
    
    # 更新缓存
    _shortcuts_cache = shortcuts
    _cache_timestamp = time.time()
    
    return shortcuts


def save_shortcuts(shortcuts: List[Shortcut]):
    """保存快捷指令"""
    global _shortcuts_cache, _cache_timestamp
    import time
    
    os.makedirs("data", exist_ok=True)
    with open(SHORTCUTS_FILE, 'w', encoding='utf-8') as f:
        json.dump([s.model_dump() for s in shortcuts], f, ensure_ascii=False, indent=2)
    
    # 更新缓存
    _shortcuts_cache = shortcuts
    _cache_timestamp = time.time()


def initialize_shortcuts() -> List[Shortcut]:
    """初始化系统预置快捷指令"""
    now = datetime.now().isoformat()
    
    system_shortcuts = [
        Shortcut(
            id="sys_wechat_check",
            title="查看微信消息",
            instruction="打开微信，查看最新的未读消息",
            category="社交",
            is_system=True,
            voice_keywords=["查看微信", "看微信", "微信消息"],
            created_at=now,
            updated_at=now
        ),
        Shortcut(
            id="sys_douyin_browse",
            title="刷抖音",
            instruction="打开抖音，刷5个视频",
            category="娱乐",
            is_system=True,
            voice_keywords=["刷抖音", "看抖音", "抖音"],
            created_at=now,
            updated_at=now
        ),
        Shortcut(
            id="sys_traffic_check",
            title="查询违章",
            instruction="打开交管12123，查询违章情况",
            category="生活",
            is_system=True,
            voice_keywords=["查违章", "查询违章", "违章查询", "交管"],
            created_at=now,
            updated_at=now
        ),
        Shortcut(
            id="sys_alipay_scan",
            title="支付宝扫码",
            instruction="打开支付宝，进入扫一扫",
            category="支付",
            is_system=True,
            voice_keywords=["支付宝扫码", "扫一扫", "支付宝"],
            created_at=now,
            updated_at=now
        ),
        Shortcut(
            id="sys_taobao_cart",
            title="查看购物车",
            instruction="打开淘宝，进入购物车查看",
            category="购物",
            is_system=True,
            voice_keywords=["购物车", "淘宝购物车", "看购物车"],
            created_at=now,
            updated_at=now
        ),
        Shortcut(
            id="sys_map_home",
            title="导航回家",
            instruction="打开高德地图，导航到家",
            category="出行",
            is_system=True,
            voice_keywords=["导航回家", "回家", "回家导航"],
            created_at=now,
            updated_at=now
        ),
        Shortcut(
            id="sys_music_play",
            title="播放音乐",
            instruction="打开网易云音乐，播放我喜欢的音乐",
            category="娱乐",
            is_system=True,
            voice_keywords=["播放音乐", "听歌", "放歌"],
            created_at=now,
            updated_at=now
        ),
        Shortcut(
            id="sys_screenshot",
            title="截图分享",
            instruction="截取当前屏幕，打开微信分享给好友",
            category="工具",
            is_system=True,
            voice_keywords=["截图分享", "截图", "分享截图"],
            created_at=now,
            updated_at=now
        ),
    ]
    
    save_shortcuts(system_shortcuts)
    return system_shortcuts


@router.get("/shortcuts", response_model=ShortcutsResponse)
async def get_shortcuts(category: Optional[str] = None):
    """
    获取快捷指令列表
    
    可按分类筛选
    """
    shortcuts = load_shortcuts()
    
    if category:
        shortcuts = [s for s in shortcuts if s.category == category]
    
    system_count = len([s for s in shortcuts if s.is_system])
    custom_count = len(shortcuts) - system_count
    
    return ShortcutsResponse(
        shortcuts=shortcuts,
        total=len(shortcuts),
        system_count=system_count,
        custom_count=custom_count
    )


@router.get("/shortcuts/{shortcut_id}", response_model=Shortcut)
async def get_shortcut(shortcut_id: str):
    """获取单个快捷指令详情"""
    shortcuts = load_shortcuts()
    
    for shortcut in shortcuts:
        if shortcut.id == shortcut_id:
            return shortcut
    
    raise HTTPException(404, f"Shortcut not found: {shortcut_id}")


@router.post("/shortcuts", response_model=Shortcut)
async def create_shortcut(request: ShortcutCreateRequest):
    """
    创建自定义快捷指令
    """
    import uuid
    
    shortcuts = load_shortcuts()
    now = datetime.now().isoformat()
    
    new_shortcut = Shortcut(
        id=f"custom_{uuid.uuid4().hex[:8]}",
        title=request.title,
        instruction=request.instruction,
        category=request.category,
        is_system=False,
        voice_keywords=request.voice_keywords,
        created_at=now,
        updated_at=now,
        use_count=0
    )
    
    shortcuts.append(new_shortcut)
    save_shortcuts(shortcuts)
    
    return new_shortcut


@router.put("/shortcuts/{shortcut_id}", response_model=Shortcut)
async def update_shortcut(shortcut_id: str, request: ShortcutUpdateRequest):
    """
    更新快捷指令
    
    注意：系统预置指令也可以编辑（V2版本改进）
    """
    shortcuts = load_shortcuts()
    
    for i, shortcut in enumerate(shortcuts):
        if shortcut.id == shortcut_id:
            # V2: 允许编辑系统预设指令
            # 但保持 is_system 标志不变（用于UI显示）
            
            # 更新字段
            if request.title is not None:
                shortcut.title = request.title
            if request.instruction is not None:
                shortcut.instruction = request.instruction
            if request.category is not None:
                shortcut.category = request.category
            if request.voice_keywords is not None:
                shortcut.voice_keywords = request.voice_keywords
            
            shortcut.updated_at = datetime.now().isoformat()
            
            shortcuts[i] = shortcut
            save_shortcuts(shortcuts)
            
            return shortcut
    
    raise HTTPException(404, f"Shortcut not found: {shortcut_id}")


@router.delete("/shortcuts/{shortcut_id}")
async def delete_shortcut(shortcut_id: str):
    """
    删除快捷指令
    
    系统预置指令不可删除
    """
    shortcuts = load_shortcuts()
    
    for i, shortcut in enumerate(shortcuts):
        if shortcut.id == shortcut_id:
            if shortcut.is_system:
                raise HTTPException(400, "Cannot delete system shortcut")
            
            del shortcuts[i]
            save_shortcuts(shortcuts)
            
            return {"message": "Shortcut deleted", "shortcut_id": shortcut_id}
    
    raise HTTPException(404, f"Shortcut not found: {shortcut_id}")


@router.post("/shortcuts/{shortcut_id}/execute")
async def execute_shortcut(shortcut_id: str, device_id: Optional[str] = None):
    """
    执行快捷指令
    
    创建任务并返回task_id
    """
    from server.services import get_agent_service, get_device_pool
    
    shortcuts = load_shortcuts()
    
    # 查找指令
    shortcut = None
    for i, s in enumerate(shortcuts):
        if s.id == shortcut_id:
            shortcut = s
            # 增加使用次数
            shortcuts[i].use_count += 1
            save_shortcuts(shortcuts)
            break
    
    if not shortcut:
        raise HTTPException(404, f"Shortcut not found: {shortcut_id}")
    
    # 创建任务
    agent_service = get_agent_service()
    
    from server.config import Config
    config = Config()
    
    model_config = {
        "api_key": config.ZHIPU_API_KEY,
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "model_name": "autoglm-phone"
    }
    
    task_id = await agent_service.create_task(
        instruction=shortcut.instruction,
        model_config=model_config,
        device_id=device_id
    )
    
    # 执行任务
    device_pool = get_device_pool()
    success = await agent_service.execute_task(task_id, device_pool)
    
    if not success:
        raise HTTPException(400, "Failed to execute shortcut")
    
    return {
        "message": "Shortcut executing",
        "shortcut_id": shortcut_id,
        "task_id": task_id,
        "title": shortcut.title
    }


@router.post("/shortcuts/match")
async def match_shortcut(voice_text: str):
    """
    根据语音文本匹配快捷指令
    
    返回最匹配的快捷指令
    """
    shortcuts = load_shortcuts()
    
    # 简单关键词匹配
    matched_shortcuts = []
    
    for shortcut in shortcuts:
        for keyword in shortcut.voice_keywords:
            if keyword in voice_text:
                matched_shortcuts.append({
                    "shortcut": shortcut,
                    "confidence": len(keyword) / len(voice_text)  # 简单置信度
                })
                break
    
    if not matched_shortcuts:
        return {"matched": False, "message": "未找到匹配的快捷指令"}
    
    # 按置信度排序
    matched_shortcuts.sort(key=lambda x: x["confidence"], reverse=True)
    best_match = matched_shortcuts[0]["shortcut"]
    
    return {
        "matched": True,
        "shortcut": best_match,
        "confidence": matched_shortcuts[0]["confidence"],
        "alternatives": [m["shortcut"] for m in matched_shortcuts[1:3]]  # 返回前2个备选
    }


@router.get("/shortcuts/categories")
async def get_shortcut_categories():
    """获取所有分类及每个分类的快捷指令数量"""
    shortcuts = load_shortcuts()
    
    categories = {}
    for shortcut in shortcuts:
        if shortcut.category not in categories:
            categories[shortcut.category] = 0
        categories[shortcut.category] += 1
    
    return {"categories": categories}

