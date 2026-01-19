#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
提示词卡片管理 API

提供提示词卡片的CRUD操作，支持动态调优AI效果
"""

import json
import os
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()

# 数据存储路径
DATA_DIR = "data"
PROMPT_CARDS_FILE = os.path.join(DATA_DIR, "prompt_cards.json")

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)


# ============================================
# 数据模型
# ============================================

class PromptCard(BaseModel):
    """提示词卡片数据模型"""
    id: int
    title: str = Field(..., description="提示词标题", max_length=50)
    description: str = Field(..., description="提示词描述", max_length=200)
    content: str = Field(..., description="提示词内容", max_length=2000)
    category: str = Field(default="通用", description="分类")
    is_system: bool = Field(default=False, description="是否为系统内置")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class CreatePromptCardRequest(BaseModel):
    """创建提示词卡片请求"""
    title: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=2000)
    category: str = Field(default="通用")


class UpdatePromptCardRequest(BaseModel):
    """更新提示词卡片请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1, max_length=2000)
    category: Optional[str] = None


class PromptCardsResponse(BaseModel):
    """提示词卡片列表响应"""
    cards: List[PromptCard]
    total: int


# ============================================
# 数据持久化
# ============================================

def load_prompt_cards() -> List[PromptCard]:
    """加载提示词卡片"""
    if not os.path.exists(PROMPT_CARDS_FILE):
        # 初始化系统提示词卡片
        default_cards = get_default_prompt_cards()
        save_prompt_cards(default_cards)
        return default_cards
    
    try:
        with open(PROMPT_CARDS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [PromptCard(**card) for card in data]
    except Exception as e:
        logger.warning(f"Failed to load prompt cards from {PROMPT_CARDS_FILE}: {e}")
        return []


def save_prompt_cards(cards: List[PromptCard]):
    """保存提示词卡片"""
    try:
        with open(PROMPT_CARDS_FILE, 'w', encoding='utf-8') as f:
            json.dump([card.model_dump() for card in cards], f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save prompt cards to {PROMPT_CARDS_FILE}: {e}", exc_info=True)
        raise


def get_default_prompt_cards() -> List[PromptCard]:
    """获取默认系统提示词卡片"""
    return [
        PromptCard(
            id=1,
            title="精确操作",
            description="要求AI更加精确地识别和点击目标元素",
            content="请特别注意：1) 仔细识别界面中的所有元素位置；2) 点击前确认目标元素的精确坐标；3) 避免点击到相邻元素；4) 如果元素较小，尽量点击中心位置。",
            category="操作优化",
            is_system=True
        ),
        PromptCard(
            id=2,
            title="慢速执行",
            description="让AI在操作间增加更多等待时间",
            content="执行任务时请：1) 每次操作后等待2-3秒；2) 页面跳转后等待加载完成；3) 输入文字后等待界面响应；4) 不要着急完成任务，稳定性优先。",
            category="速度控制",
            is_system=True
        ),
        PromptCard(
            id=3,
            title="微信专用",
            description="针对微信App的操作优化",
            content="微信操作提示：1) 注意区分聊天列表和联系人列表；2) 发送消息前确认已选中正确的聊天对象；3) 朋友圈操作要等待图片加载完成；4) 群聊中注意@功能的使用。",
            category="应用适配",
            is_system=True
        ),
        PromptCard(
            id=4,
            title="购物助手",
            description="电商类App的操作优化",
            content="购物操作提示：1) 加入购物车前仔细核对商品信息（规格、数量、价格）；2) 提交订单前检查收货地址；3) 支付前再次确认金额；4) 注意优惠券的使用。",
            category="应用适配",
            is_system=True
        ),
        PromptCard(
            id=5,
            title="防误操作",
            description="避免点击到危险按钮",
            content="安全提示：1) 避免点击「删除」「清空」等危险操作；2) 不要随意授权敏感权限；3) 遇到支付确认时要特别谨慎；4) 不确定的操作请先询问用户。",
            category="安全提示",
            is_system=True
        ),
        PromptCard(
            id=6,
            title="文字输入优化",
            description="提升文字输入的准确性",
            content="输入文字时：1) 输入后检查是否有输入法联想词干扰；2) 长文本分段输入，每段后检查；3) 特殊符号和emoji要谨慎使用；4) 输入完成后确认点击发送按钮。",
            category="输入优化",
            is_system=True
        ),
        PromptCard(
            id=7,
            title="多步任务规划",
            description="复杂任务的分步执行",
            content="复杂任务执行：1) 先理解完整任务目标；2) 分解为多个小步骤；3) 每步执行后确认状态；4) 遇到异常立即停止并报告；5) 完成后总结执行结果。",
            category="任务规划",
            is_system=True
        ),
        PromptCard(
            id=8,
            title="界面变化适应",
            description="应对动态界面和弹窗",
            content="界面变化应对：1) 执行前先观察当前界面状态；2) 注意可能出现的弹窗、广告；3) 遇到意外弹窗先关闭再继续；4) 界面布局变化时重新识别元素位置。",
            category="适应性",
            is_system=True
        )
    ]


def get_next_id(cards: List[PromptCard]) -> int:
    """获取下一个ID"""
    if not cards:
        return 1
    return max(card.id for card in cards) + 1


# ============================================
# API 路由
# ============================================

@router.get("/prompt-cards", response_model=PromptCardsResponse, summary="获取所有提示词卡片")
async def get_prompt_cards(category: Optional[str] = None):
    """
    获取所有提示词卡片
    
    - **category**: 可选，按分类筛选
    """
    cards = load_prompt_cards()
    
    if category:
        cards = [card for card in cards if card.category == category]
    
    return PromptCardsResponse(cards=cards, total=len(cards))


@router.get("/prompt-cards/categories", summary="获取所有分类")
async def get_categories():
    """获取所有提示词卡片的分类列表"""
    cards = load_prompt_cards()
    categories = list(set(card.category for card in cards))
    return {"categories": sorted(categories)}


@router.get("/prompt-cards/{card_id}", response_model=PromptCard, summary="获取单个提示词卡片")
async def get_prompt_card(card_id: int):
    """根据ID获取提示词卡片"""
    cards = load_prompt_cards()
    card = next((c for c in cards if c.id == card_id), None)
    
    if not card:
        raise HTTPException(404, f"Prompt card {card_id} not found")
    
    return card


@router.post("/prompt-cards", response_model=PromptCard, summary="创建提示词卡片")
async def create_prompt_card(request: CreatePromptCardRequest):
    """创建新的提示词卡片"""
    cards = load_prompt_cards()
    
    new_card = PromptCard(
        id=get_next_id(cards),
        title=request.title,
        description=request.description,
        content=request.content,
        category=request.category,
        is_system=False
    )
    
    cards.append(new_card)
    save_prompt_cards(cards)
    
    return new_card


@router.put("/prompt-cards/{card_id}", response_model=PromptCard, summary="更新提示词卡片")
async def update_prompt_card(card_id: int, request: UpdatePromptCardRequest):
    """更新提示词卡片（系统卡片也可以编辑）"""
    cards = load_prompt_cards()
    card = next((c for c in cards if c.id == card_id), None)
    
    if not card:
        raise HTTPException(404, f"Prompt card {card_id} not found")
    
    # 更新字段
    if request.title is not None:
        card.title = request.title
    if request.description is not None:
        card.description = request.description
    if request.content is not None:
        card.content = request.content
    if request.category is not None:
        card.category = request.category
    
    card.updated_at = datetime.now().isoformat()
    
    # 保存
    save_prompt_cards(cards)
    
    return card


@router.delete("/prompt-cards/{card_id}", summary="删除提示词卡片")
async def delete_prompt_card(card_id: int):
    """删除提示词卡片（系统卡片不能删除）"""
    cards = load_prompt_cards()
    card = next((c for c in cards if c.id == card_id), None)
    
    if not card:
        raise HTTPException(404, f"Prompt card {card_id} not found")
    
    if card.is_system:
        raise HTTPException(400, "Cannot delete system prompt card")
    
    cards = [c for c in cards if c.id != card_id]
    save_prompt_cards(cards)
    
    return {"message": "Prompt card deleted successfully", "id": card_id}


@router.post("/prompt-cards/reset", summary="重置为默认提示词卡片")
async def reset_prompt_cards():
    """重置为默认的系统提示词卡片（保留自定义卡片）"""
    cards = load_prompt_cards()
    
    # 保留自定义卡片
    custom_cards = [card for card in cards if not card.is_system]
    
    # 重新加载默认系统卡片
    system_cards = get_default_prompt_cards()
    
    # 合并
    all_cards = system_cards + custom_cards
    save_prompt_cards(all_cards)
    
    return {"message": "Prompt cards reset successfully", "total": len(all_cards)}

