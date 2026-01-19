#!/usr/bin/env python3
# Original: Copyright (c) 2024 ZAI Organization (Apache-2.0)
# Modified: Copyright (C) 2025 PhoneAgent Contributors (AGPL-3.0)
# Based on: https://github.com/zai-org/Open-AutoGLM

"""使用OpenAI兼容API的AI推理模型客户端"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Union

from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for the AI model."""

    base_url: str = "http://localhost:8000/v1"
    api_key: str = "EMPTY"
    model_name: str = "autoglm-phone-9b"
    max_tokens: int = 3000
    temperature: float = 0.0
    top_p: float = 0.85
    frequency_penalty: float = 0.0  # [CHANGED] 智谱API不支持非0的frequency_penalty
    extra_body: dict[str, Any] = field(
        default_factory=lambda: {"skip_special_tokens": False}
    )


@dataclass
class ModelResponse:
    """Response from the AI model."""

    thinking: str
    action: Union[dict, str]  # [Phase 4] 可以是 dict (优先) 或 str (兼容)
    raw_content: str
    usage: dict[str, Any] | None = None  # Token usage info


class ModelClient:
    """
    Client for interacting with OpenAI-compatible vision-language models.

    Args:
        config: Model configuration.
    """

    def __init__(self, config: ModelConfig | None = None):
        self.config = config or ModelConfig()
        self.client = OpenAI(base_url=self.config.base_url, api_key=self.config.api_key)

    def request(self, messages: list[dict[str, Any]]) -> ModelResponse:
        """
        Send a request to the model.

        Args:
            messages: List of message dictionaries in OpenAI format.

        Returns:
            ModelResponse containing thinking and action.

        Raises:
            ValueError: If the response cannot be parsed.
        """
        # 构建请求参数
        request_params = {
            "messages": messages,
            "model": self.config.model_name,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
        }
        
        # 只有当 frequency_penalty 不为 0 时才添加（兼容智谱等 API）
        if self.config.frequency_penalty != 0.0:
            request_params["frequency_penalty"] = self.config.frequency_penalty
        
        # extra_body: 智谱API不支持，跳过
        # if self.config.extra_body:
        #     request_params["extra_body"] = self.config.extra_body
        
        response = self.client.chat.completions.create(**request_params)

        raw_content = response.choices[0].message.content
        
        # 检查是否因 max_tokens 截断
        finish_reason = response.choices[0].finish_reason
        if finish_reason == "length":
            logger.warning(
                f"模型输出因 max_tokens 限制被截断！"
                f"当前 max_tokens={self.config.max_tokens}，"
                f"建议增加到 4096 或更高"
            )

        # Parse thinking and action from response
        thinking, action = self._parse_response(raw_content)
        
        # Extract token usage (支持标准OpenAI格式和智谱AI扩展格式)
        usage = None
        if hasattr(response, 'usage') and response.usage:
            usage = {
                "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0),
                "completion_tokens": getattr(response.usage, 'completion_tokens', 0),
                "total_tokens": getattr(response.usage, 'total_tokens', 0),
            }
            
            # 智谱AI深度思考模型额外返回字段（如果存在）
            # completion_tokens_details: {"reasoning_tokens": xxx, "accepted_prediction_tokens": xxx, "rejected_prediction_tokens": xxx}
            if hasattr(response.usage, 'completion_tokens_details'):
                details = response.usage.completion_tokens_details
                usage["completion_tokens_details"] = {
                    "reasoning_tokens": getattr(details, 'reasoning_tokens', 0),
                    "accepted_prediction_tokens": getattr(details, 'accepted_prediction_tokens', 0),
                    "rejected_prediction_tokens": getattr(details, 'rejected_prediction_tokens', 0),
                }

        return ModelResponse(thinking=thinking, action=action, raw_content=raw_content, usage=usage)
    
    def request_json(
        self,
        messages: list[dict[str, Any]],
        temperature: float | None = None
    ) -> ModelResponse:
        """
        请求JSON格式响应（用于XML Kernel等场景）
        
        Args:
            messages: 消息列表
            temperature: 温度参数（可选，覆盖配置）
        
        Returns:
            ModelResponse，其中 raw_content 为 JSON 字符串
        
        Raises:
            ValueError: 如果响应无法解析
        
        Example:
            >>> client = ModelClient(config)
            >>> response = client.request_json([
            ...     {"role": "system", "content": "You are a helpful assistant."},
            ...     {"role": "user", "content": "返回JSON: {\"action\": \"tap\", \"x\": 100}"}
            ... ])
            >>> data = json.loads(response.raw_content)
        """
        # 构建请求参数
        request_params = {
            "messages": messages,
            "model": self.config.model_name,
            "max_tokens": self.config.max_tokens,
            "temperature": temperature if temperature is not None else self.config.temperature,
            "top_p": self.config.top_p,
            "response_format": {"type": "json_object"},  # [NEW] 强制JSON输出
        }
        
        # 只有当 frequency_penalty 不为 0 时才添加
        if self.config.frequency_penalty != 0.0:
            request_params["frequency_penalty"] = self.config.frequency_penalty
        
        # 只有当 extra_body 不为空时才添加
        if self.config.extra_body:
            request_params["extra_body"] = self.config.extra_body
        
        response = self.client.chat.completions.create(**request_params)
        
        raw_content = response.choices[0].message.content
        
        # Extract token usage
        usage = None
        if hasattr(response, 'usage') and response.usage:
            usage = {
                "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0),
                "completion_tokens": getattr(response.usage, 'completion_tokens', 0),
                "total_tokens": getattr(response.usage, 'total_tokens', 0),
            }
            
            # 智谱AI深度思考模型额外返回字段
            if hasattr(response.usage, 'completion_tokens_details'):
                details = response.usage.completion_tokens_details
                usage["completion_tokens_details"] = {
                    "reasoning_tokens": getattr(details, 'reasoning_tokens', 0),
                    "accepted_prediction_tokens": getattr(details, 'accepted_prediction_tokens', 0),
                    "rejected_prediction_tokens": getattr(details, 'rejected_prediction_tokens', 0),
                }
        
        # JSON模式下，thinking为空，整个JSON作为action
        return ModelResponse(
            thinking="",
            action=raw_content,
            raw_content=raw_content,
            usage=usage
        )

    def _parse_response(self, content: str) -> tuple[str, Union[dict, str]]:
        """
        Parse the model response into thinking and action parts.
        
        [Phase 4 完成] 职责已简化，委托给 ResponseParser
        
        现在只负责：
        - 调用 ResponseParser 识别格式
        - 返回 (thinking, action_data)
          - action_data 可以是 dict (优先) 或 str (兼容)
        
        支持的模型和格式：
        - Vision Kernel (XML+JSON混合): <thinking>...</thinking><tool_call>{...}</tool_call>
        - autoglm-phone (官方推荐): <think>...</think><answer>...</answer>
        - glm-4.1v-thinking-flash (免费): {think}...{action}... 或 box格式
        - glm-4.1v-thinking-flashx (高并发): 同thinking-flash
        - 通用兜底: JSON格式 或 纯文本提取do(...)
        
        格式优先级：
        1. XML+JSON混合格式（Vision Kernel标准）
        2. AutoGLM 标准格式
        3. JSON 格式（明确、易调试）
        4. GLM-Thinking 多行格式
        5. GLM-Thinking Box格式
        6. 纯文本提取（兜底）

        Args:
            content: Raw response content.

        Returns:
            Tuple of (thinking, action).
        """
        from phone_agent.model.response_parser import ResponseParser
        
        # [Phase 4 完成] 委托给 ResponseParser 处理所有格式识别
        return ResponseParser.parse(content)
        
        # 以下代码已移至 response_parser.py，保留注释供参考
        # 格式1: Vision Kernel XML+JSON混合格式 <thinking>...</thinking><tool_call>{JSON}</tool_call>
        r"""
        if "<thinking>" in content and "<tool_call>" in content:
            try:
                # 提取thinking部分
                thinking_match = re.search(r'<thinking>(.*?)</thinking>', content, re.DOTALL)
                thinking = thinking_match.group(1).strip() if thinking_match else ""
                
                # 提取tool_call中的内容
                tool_call_match = re.search(r'<tool_call>(.*?)</tool_call>', content, re.DOTALL)
                if tool_call_match:
                    tool_call_content = tool_call_match.group(1).strip()
                    
                    # 尝试解析为JSON（标准格式）
                    try:
                        tool_data = json.loads(tool_call_content)
                        # 检查是否是标准的JSON格式（action作为单独字段）
                        if isinstance(tool_data, dict) and "action" in tool_data:
                            action_name = tool_data.get("action", "")
                            
                            # 检查action是否包含参数（错误格式）
                            if "(" in action_name or ")" in action_name:
                                # 错误格式："action": "Type(text='xxx')"
                                logger.warning(f"检测到错误的action格式（参数在action字符串中）: {action_name}")
                                # 尝试解析并转换为标准格式（容错处理）
                                # 暂时返回原始格式，让handler处理
                                return thinking, tool_call_content
                            
                            # 标准格式：将JSON转换为 do() 调用格式（保持向后兼容）
                            # {"action": "tap", "coordinates": [x, y]} -> do(action="tap", coordinates=[x, y])
                            params = {k: v for k, v in tool_data.items() if k != "action"}
                            
                            # 容错处理：如果模型错误输出 finish，自动纠正为 done
                            if action_name.lower() == "finish":
                                action_name = "done"
                            
                            # 构造 do() 格式参数字符串
                            param_parts = [f'action="{action_name}"']
                            for k, v in params.items():
                                if isinstance(v, str):
                                    # 字符串参数需要转义引号
                                    v_escaped = v.replace('"', '\\"')
                                    param_parts.append(f'{k}="{v_escaped}"')
                                elif isinstance(v, list):
                                    param_parts.append(f'{k}={v}')
                                else:
                                    param_parts.append(f'{k}={v}')
                            param_str = ", ".join(param_parts)
                            action_str = f'do({param_str})'
                            
                            return thinking, action_str
                            
                    except json.JSONDecodeError:
                        # 不是JSON，可能是旧的 do() 格式（向后兼容）
                        if tool_call_content.startswith('do('):
                            return thinking, tool_call_content
                        # 其他情况，返回原始内容
                        return thinking, tool_call_content
                        
            except (AttributeError, Exception) as e:
                # 如果解析失败，继续尝试其他格式
                logger.debug(f"XML+JSON格式解析失败: {e}")
                pass
        
        # 格式2: AutoGLM 标准格式 <think>...</think><answer>...</answer>
        if "<answer>" in content:
            parts = content.split("<answer>", 1)
            thinking = parts[0].replace("<think>", "").replace("</think>", "").strip()
            action = parts[1].replace("</answer>", "").strip()
            return thinking, action
        
        # 格式3: JSON 格式 {"think": "...", "action": "..."} (旧Vision格式，保留兼容)
        if content.strip().startswith("{") and '"think"' in content and '"action"' in content:
            try:
                # 尝试解析 JSON
                data = json.loads(content.strip())
                if isinstance(data, dict) and "think" in data and "action" in data:
                    return str(data["think"]), str(data["action"])
            except json.JSONDecodeError:
                # JSON 解析失败，尝试用正则提取（处理嵌套引号问题）
                # 提取 think 字段（在逗号之前）
                think_match = re.search(r'"think"\s*:\s*"([^"]*(?:"[^"]*"[^"]*)*)"', content)
                if not think_match:
                    # 尝试更宽松的匹配
                    think_match = re.search(r'"think"\s*:\s*"(.*?)",\s*"action"', content, re.DOTALL)
                
                # 提取 action 字段（可能包含嵌套引号）
                # 匹配 "action": "do(action="xxx")" 或 "action": "do(...)"
                action_match = re.search(r'"action"\s*:\s*"(do\([^)]+\))"', content)
                
                if think_match and action_match:
                    thinking = think_match.group(1).strip()
                    action = action_match.group(1).strip()
                    return thinking, action
        
        # 格式4: GLM-4.1V-Thinking 格式 {think}...{action}... 
        # 包括换行的情况：{think}...\n{action}...
        if "{think}" in content and "{action}" in content:
            think_match = re.search(r'\{think\}(.*?)\{action\}', content, re.DOTALL)
            if think_match:
                thinking = think_match.group(1).strip()
                # 提取 {action} 后面的 do(...) 指令
                action_section = content.split("{action}")[1]
                # 在 action section 中找 do(...) 或 finish(...)[容错：finish已废弃]
                action_match = re.search(r'((?:do|finish)\([^)]+\))', action_section)
                action = action_match.group(1).strip() if action_match else action_section.split('\n')[0].strip()
                # 移除可能的注释
                action = re.sub(r'//[^\n]*', '', action).strip()
                return thinking, action
        
        # 格式5: GLM-4.1V-Thinking 格式 {think>...}<|begin_of_box|>...<|end_of_box|>
        if "{think>" in content or "{think}" in content:
            # 提取 thinking 部分
            think_match = re.search(r'\{think[>]?(.*?)\}', content, re.DOTALL)
            thinking = think_match.group(1).strip() if think_match else ""
            
            # 提取 action 部分（在 box 标记内或 think 后面）
            box_match = re.search(r'<\|begin_of_box\|\>(.*?)<\|end_of_box\|\>', content, re.DOTALL)
            if box_match:
                action = box_match.group(1).strip()
                # 移除可能的 {action} 前缀
                action = re.sub(r'^\{action\}', '', action).strip()
                # 移除注释（// 开头的行）
                action = re.sub(r'//[^\n]*', '', action).strip()
            else:
                # 如果没有 box 标记，寻找 {action}... 格式
                action_match = re.search(r'\{action\}(.*?)(?:\n//|$)', content, re.DOTALL)
                if action_match:
                    action = action_match.group(1).strip()
                else:
                    # 取 think 后面的内容
                    action_match = re.search(r'\{think[>]?.*?\}(.*)$', content, re.DOTALL)
                    action = action_match.group(1).strip() if action_match else ""
                    # 移除注释
                    action = re.sub(r'//[^\n]*', '', action).strip()
            
            return thinking, action
        
        # 格式6: GLM-4.1V 输出 <think>... 但没有闭合标签和 <answer>
        # 或者输出了 </think> 但没有 <answer> 标签
        # 这种情况下，thinking 太长被截断了，或者模型输出格式不标准
        if "<think>" in content or "</think>" in content:
            # 尝试提取一个合理的 action（可能在最后）
            # 查找 do(...) 或 finish(...)[容错] 模式
            action_pattern = r'((?:do|finish)\([^)]+\))'
            matches = re.findall(action_pattern, content)
            if matches:
                # 取最后一个匹配的 action
                action = matches[-1]
                # thinking 是 action 之前的内容
                idx = content.rfind(action)
                thinking_text = content[:idx].replace("<think>", "").replace("</think>", "").strip()
                # 限制 thinking 长度避免太长
                thinking = thinking_text[-500:] if len(thinking_text) > 500 else thinking_text
                return thinking, action
        
        # 默认：尝试从任何格式中提取 do(...) 指令（finish已废弃，仅作容错）
        # 这是最后的兜底方案，用于处理各种奇怪的输出格式
        
        # 使用正则提取所有 do(...) 或 finish(...)[容错] 模式
        # 支持嵌套括号和引号
        all_matches = []
        
        # 方法1: 找到所有完整的 do(...) 或 finish(...)[容错] 调用
        # 改进的正则：匹配 do( 或 finish( 后面的内容，直到找到匹配的 )
        # 支持引号和嵌套，也支持数组 [x, y]
        for match in re.finditer(r'((?:do|finish)\s*\([^()]*(?:\[[^\]]*\])?[^()]*(?:\([^()]*\)[^()]*)*\))', content):
            all_matches.append(match.group(1))
        
        if all_matches:
            # 取最后一个匹配（通常是最终的action指令）
            action = all_matches[-1].strip()
            # thinking 是 action 之前的内容
            idx = content.rfind(action)
            thinking = content[:idx] if idx > 0 else ""
            # 清理 thinking 中的各种标记
            thinking = re.sub(r'\{think[>]?\}?|\{\/think\}?|\</think\>|\{action\}|\<\|begin_of_box\|\>|\<\|end_of_box\|\>|//[^\n]*|"think"\s*:|"action"\s*:', '', thinking).strip()
            thinking = re.sub(r'^\{+|\}+$|^"+|"+$', '', thinking).strip()
            return thinking, action
        
        # 完全无法解析，返回空thinking和原内容（会导致 parse_action 失败）
        return "", content
        """


class MessageBuilder:
    """Helper class for building conversation messages."""

    @staticmethod
    def create_system_message(content: str) -> dict[str, Any]:
        """Create a system message."""
        return {"role": "system", "content": content}

    @staticmethod
    def create_user_message(
        text: str, image_base64: str | None = None
    ) -> dict[str, Any]:
        """
        Create a user message with optional image.

        Args:
            text: Text content.
            image_base64: Optional base64-encoded image.

        Returns:
            Message dictionary.
        """
        content = []

        if image_base64:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                }
            )

        content.append({"type": "text", "text": text})

        return {"role": "user", "content": content}

    @staticmethod
    def create_assistant_message(content: str) -> dict[str, Any]:
        """Create an assistant message."""
        return {"role": "assistant", "content": content}

    @staticmethod
    def remove_images_from_message(message: dict[str, Any]) -> dict[str, Any]:
        """
        Remove image content from a message to save context space.

        Args:
            message: Message dictionary.

        Returns:
            Message with images removed.
        """
        if isinstance(message.get("content"), list):
            message["content"] = [
                item for item in message["content"] if item.get("type") == "text"
            ]
        return message

    @staticmethod
    def build_screen_info(current_app: str, **extra_info) -> str:
        """
        Build screen info string for the model.

        Args:
            current_app: Current app name.
            **extra_info: Additional info to include.

        Returns:
            JSON string with screen info.
        """
        info = {"current_app": current_app, **extra_info}
        return json.dumps(info, ensure_ascii=False)
