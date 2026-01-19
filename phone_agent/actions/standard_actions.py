"""
统一动作格式定义

基于android-use最佳实践，融合MAI-UI的简洁性
支持XML Kernel（index模式）和Vision Kernel（coordinates模式）

参考：
- android-use: Registry模式 + Pydantic类型安全
- MAI-UI: 简洁的JSON格式
- MobileAgent: 多模态实践经验
"""

from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, validator


class TapAction(BaseModel):
    """
    点击动作 - 统一格式
    
    支持两种模式：
    1. index模式（XML Kernel推荐）: 使用元素索引
    2. coordinates模式（Vision Kernel）: 使用归一化坐标(0-1000)
    """
    index: Optional[int] = Field(None, description="元素索引（XML模式）")
    coordinates: Optional[List[int]] = Field(None, description="归一化坐标 [x, y] (0-1000范围)")
    reason: Optional[str] = Field(None, description="执行原因（可选，便于调试）")
    
    @validator('coordinates')
    def validate_coordinates(cls, v):
        if v is not None and len(v) != 2:
            raise ValueError("coordinates必须是[x, y]格式")
        return v
    
    def model_post_init(self, __context: Any) -> None:
        """验证至少提供index或coordinates之一"""
        if self.index is None and self.coordinates is None:
            raise ValueError("必须提供index或coordinates之一")


class InputTextAction(BaseModel):
    """
    输入文本动作
    """
    text: str = Field(..., description="要输入的文本")
    index: Optional[int] = Field(None, description="目标输入框索引（可选，不填则在当前焦点）")
    clear: bool = Field(True, description="输入前是否清空")
    reason: Optional[str] = None


class SwipeAction(BaseModel):
    """
    滑动动作
    
    支持两种模式：
    1. 方向模式（推荐）: direction参数
    2. 坐标模式（精确控制）: start + end参数
    """
    direction: Optional[Literal["up", "down", "left", "right"]] = Field(None, description="滑动方向")
    start: Optional[List[int]] = Field(None, description="起始坐标 [x, y] (归一化0-1000)")
    end: Optional[List[int]] = Field(None, description="结束坐标 [x, y] (归一化0-1000)")
    duration: int = Field(200, description="滑动时长（毫秒）")
    reason: Optional[str] = None
    
    def model_post_init(self, __context: Any) -> None:
        """验证至少提供direction或start+end"""
        if self.direction is None and (self.start is None or self.end is None):
            raise ValueError("必须提供direction或(start+end)")


class LaunchAppAction(BaseModel):
    """
    启动应用动作
    
    [WARN] 重要：app_name只填应用名称，不要包含任务描述
    """
    app_name: str = Field(..., description="应用名称（只填名字，如'微信'）")
    reason: Optional[str] = None


class LongPressAction(BaseModel):
    """
    长按动作
    
    支持两种模式：
    1. index模式：使用元素索引
    2. coordinates模式：使用归一化坐标(0-1000)
    """
    index: Optional[int] = Field(None, description="元素索引")
    coordinates: Optional[List[int]] = Field(None, description="归一化坐标 [x, y] (0-1000范围)")
    duration: int = Field(1000, description="长按时长（毫秒），默认1000ms")
    reason: Optional[str] = None
    
    @validator('coordinates')
    def validate_coordinates(cls, v):
        if v is not None and len(v) != 2:
            raise ValueError("coordinates必须是[x, y]格式")
        return v
    
    def model_post_init(self, __context: Any) -> None:
        """验证至少提供index或coordinates之一"""
        if self.index is None and self.coordinates is None:
            raise ValueError("必须提供index或coordinates之一")


class DoubleTapAction(BaseModel):
    """
    双击动作
    
    支持两种模式：
    1. index模式：使用元素索引
    2. coordinates模式：使用归一化坐标(0-1000)
    """
    index: Optional[int] = Field(None, description="元素索引")
    coordinates: Optional[List[int]] = Field(None, description="归一化坐标 [x, y] (0-1000范围)")
    reason: Optional[str] = None
    
    @validator('coordinates')
    def validate_coordinates(cls, v):
        if v is not None and len(v) != 2:
            raise ValueError("coordinates必须是[x, y]格式")
        return v
    
    def model_post_init(self, __context: Any) -> None:
        """验证至少提供index或coordinates之一"""
        if self.index is None and self.coordinates is None:
            raise ValueError("必须提供index或coordinates之一")


class PressKeyAction(BaseModel):
    """
    按键动作
    """
    key: Literal["back", "home", "recent"] = Field(..., description="按键名称")
    reason: Optional[str] = None


class DoneAction(BaseModel):
    """
    完成任务动作
    
    [WARN] 关键规则：
    1. done必须是唯一动作（不能与其他动作组合）
    2. 必须包含完整的任务结果信息
    """
    success: bool = Field(True, description="任务是否成功完成")
    message: str = Field(..., description="完成信息或失败原因")
    data: Optional[Dict[str, Any]] = Field(None, description="提取的数据（可选）")


class RecordImportantContentAction(BaseModel):
    """
    记录重要内容动作（长期记忆机制）
    
    保存任务执行过程中的关键信息，供后续步骤使用。
    记录的内容会：1) 加入AI上下文 2) 持久化到数据库 3) 在前端展示
    
    Inspired by android-use (MIT License) - Copyright (c) 2025 languse-ai
    """
    content: str = Field(..., description="要记录的重要内容")
    category: Optional[str] = Field(None, description="内容分类（如price, contact, url等）")
    reason: Optional[str] = Field(None, description="记录原因（可选）")


class GenerateOrUpdateTodosAction(BaseModel):
    """
    生成或更新TODO列表动作（任务规划机制）
    
    用于复杂任务的规划和进度跟踪。支持Markdown格式。
    格式：- [ ] 未完成 / - [x] 已完成 / - [-] 进行中
    
    Inspired by android-use (MIT License) - Copyright (c) 2025 languse-ai
    """
    todos: str = Field(..., description="Markdown格式的TODO列表")
    reason: Optional[str] = Field(None, description="更新原因（可选）")


class DragAction(BaseModel):
    """拖拽动作 - Inspired by android-use (MIT) + MAI-UI (Apache-2.0)"""
    start_index: Optional[int] = Field(None, description="起始元素索引")
    end_index: Optional[int] = Field(None, description="目标元素索引")
    start: Optional[List[int]] = Field(None, description="起始坐标[x,y](0-1000)")
    end: Optional[List[int]] = Field(None, description="结束坐标[x,y](0-1000)")
    duration: int = Field(500, description="拖拽时长(ms)")
    reason: Optional[str] = None


class ScrollAction(BaseModel):
    """滚动动作 - Inspired by MobileAgent (Apache-2.0)"""
    coordinates: List[int] = Field(..., description="滚动位置[x,y](0-1000)")
    value: int = Field(..., description="滚动量(正数向上,负数向下)")
    reason: Optional[str] = None


class KeyEventAction(BaseModel):
    """按键事件 - Inspired by MobileAgent (Apache-2.0)"""
    key: str = Field(..., description="按键名(volume_up,power等)")
    reason: Optional[str] = None


class AnswerAction(BaseModel):
    """返回答案 - Inspired by MobileAgent+MAI-UI (Apache-2.0)"""
    answer: str = Field(..., description="答案内容")
    success: bool = Field(True, description="是否成功找到答案")
    data: Optional[Dict[str, Any]] = Field(None, description="结构化数据")
    reason: Optional[str] = None


class AskUserAction(BaseModel):
    """询问用户 - Inspired by MAI-UI (Apache-2.0)"""
    question: str = Field(..., description="要问用户的问题")
    options: Optional[List[str]] = Field(None, description="可选项列表")
    reason: Optional[str] = None


class WaitAction(BaseModel):
    """
    等待动作
    """
    seconds: float = Field(3.0, ge=0, description="等待秒数")
    reason: Optional[str] = None


class ReadClipboardAction(BaseModel):
    """
    读取设备剪贴板内容
    
    使用场景:
    - 获取用户复制的验证码
    - 读取从其他应用复制的内容
    - 验证复制操作是否成功
    """
    reason: str = Field(..., description="读取剪贴板的原因")


class WriteClipboardAction(BaseModel):
    """
    写入内容到设备剪贴板
    
    使用场景:
    - 准备长文本供用户粘贴
    - 跨应用传递数据
    - 绕过输入法限制
    """
    text: str = Field(..., description="要写入剪贴板的文本")
    reason: str = Field(..., description="写入剪贴板的原因")


# 动作类型映射
ACTION_MODELS = {
    "tap": TapAction,
    "input_text": InputTextAction,
    "swipe": SwipeAction,
    "launch_app": LaunchAppAction,
    "long_press": LongPressAction,
    "double_tap": DoubleTapAction,
    "press_key": PressKeyAction,
    "drag": DragAction,
    "scroll": ScrollAction,
    "key_event": KeyEventAction,
    "answer": AnswerAction,
    "ask_user": AskUserAction,
    "done": DoneAction,
    "record_important_content": RecordImportantContentAction,
    "generate_or_update_todos": GenerateOrUpdateTodosAction,
    "wait": WaitAction,
    "read_clipboard": ReadClipboardAction,
    "write_clipboard": WriteClipboardAction,
}

# 类型别名
Action = Union[
    TapAction,
    InputTextAction,
    SwipeAction,
    LaunchAppAction,
    LongPressAction,
    DoubleTapAction,
    PressKeyAction,
    DragAction,
    ScrollAction,
    KeyEventAction,
    AnswerAction,
    AskUserAction,
    DoneAction,
    RecordImportantContentAction,
    GenerateOrUpdateTodosAction,
    WaitAction,
    ReadClipboardAction,
    WriteClipboardAction,
]


class AgentResponse(BaseModel):
    """
    Agent响应格式（完整）
    """
    think: str = Field(..., description="推理过程")
    evaluation_previous_goal: str = Field(
        ...,
        description="对上一步的评估：Success|Failed|Unknown"
    )
    action: List[Dict[str, Any]] = Field(..., description="动作列表")
    
    @validator('action')
    def validate_action_not_empty(cls, v):
        if len(v) == 0:
            raise ValueError("action列表不能为空")
        return v


def parse_action(action_dict: Dict[str, Any]) -> Action:
    """
    解析动作（支持两种格式）
    
    Args:
        action_dict: 动作字典，支持两种格式：
            1. 标准格式: {"tap": {"index": 33, "reason": "点击"}}
            2. XML Kernel格式: {"action": "tap", "coordinates": [100, 200], "reason": "点击"}
        
    Returns:
        解析后的动作对象
        
    Raises:
        ValueError: 未知动作或参数错误
    
    Example:
        >>> parse_action({"tap": {"index": 33, "reason": "点击搜索"}})
        TapAction(index=33, coordinates=None, reason='点击搜索')
        
        >>> parse_action({"action": "tap", "coordinates": [100, 200], "reason": "点击"})
        TapAction(index=None, coordinates=[100, 200], reason='点击')
    """
    if not isinstance(action_dict, dict):
        raise ValueError(f"Invalid action format: {action_dict}")
    
    # [OK] 检测格式：XML Kernel格式（有"action"字段）
    if "action" in action_dict:
        action_name = action_dict["action"]
        action_params = {k: v for k, v in action_dict.items() if k != "action"}
        
        # 映射动作名（XML Kernel使用小写）
        action_name_map = {
            "tap": "tap",
            "type": "input_text",  # XML: type → 标准: input_text
            "swipe": "swipe",
            "launch": "launch_app",  # XML: launch → 标准: launch_app
            "long_press": "long_press",
            "double_tap": "double_tap",
            "back": "press_key",  # XML: back → 标准: press_key
            "home": "press_key",  # XML: home → 标准: press_key
            "drag": "drag",
            "scroll": "scroll",
            "key_event": "key_event",
            "answer": "answer",
            "ask_user": "ask_user",
            "record_important_content": "record_important_content",
            "generate_or_update_todos": "generate_or_update_todos",
            "wait": "wait",
            "done": "done",
        }
        
        if action_name not in action_name_map:
            raise ValueError(f"Unknown XML Kernel action: {action_name}")
        
        mapped_name = action_name_map[action_name]
        
        # 特殊处理：back/home需要添加key参数
        if action_name in ["back", "home"]:
            action_params["key"] = action_name
        
        # 特殊处理：type的text字段保持不变（InputTextAction使用text）
        # XML: {"action": "type", "text": "hello"} → InputTextAction(text="hello")
        
        # 特殊处理：launch需要重命名app字段
        if action_name == "launch" and "app" in action_params:
            action_params["app_name"] = action_params.pop("app")
        
        # 特殊处理：done需要确保有message字段
        if action_name == "done":
            if "message" not in action_params and "reason" in action_params:
                action_params["message"] = action_params.pop("reason")
            elif "message" not in action_params:
                action_params["message"] = "任务完成"
        
        if mapped_name not in ACTION_MODELS:
            raise ValueError(f"Unknown action: {mapped_name}")
        
        model_class = ACTION_MODELS[mapped_name]
        return model_class(**action_params)
    
    # [OK] 标准格式: {"tap": {...}}
    if len(action_dict) != 1:
        raise ValueError(f"Invalid action format: {action_dict}")
    
    action_name, action_params = list(action_dict.items())[0]
    
    if action_name not in ACTION_MODELS:
        raise ValueError(f"Unknown action: {action_name}")
    
    model_class = ACTION_MODELS[action_name]
    return model_class(**action_params)


def parse_agent_response(response_dict: Dict[str, Any]) -> AgentResponse:
    """
    解析完整的Agent响应
    
    Args:
        response_dict: 响应字典，包含think, evaluation_previous_goal, action
        
    Returns:
        解析后的AgentResponse对象
    """
    return AgentResponse(**response_dict)


def validate_action_sequence(actions: List[Action]) -> bool:
    """
    验证动作序列的合法性
    
    规则：
    1. 如果包含done动作，它必须是唯一的动作
    2. 动作列表不能为空
    
    Args:
        actions: 动作列表
        
    Returns:
        是否合法
        
    Raises:
        ValueError: 违反规则时抛出
    """
    if len(actions) == 0:
        raise ValueError("动作列表不能为空")
    
    has_done = any(isinstance(action, DoneAction) for action in actions)
    
    if has_done and len(actions) > 1:
        raise ValueError("done动作必须是唯一的动作，不能与其他动作组合")
    
    return True


__all__ = [
    # 动作模型
    "TapAction",
    "InputTextAction",
    "SwipeAction",
    "LaunchAppAction",
    "PressKeyAction",
    "DoneAction",
    "RecordImportantContentAction",
    "GenerateOrUpdateTodosAction",
    "WaitAction",
    # 响应模型
    "AgentResponse",
    # 类型
    "Action",
    "ACTION_MODELS",
    # 工具函数
    "parse_action",
    "parse_agent_response",
    "validate_action_sequence",
]
