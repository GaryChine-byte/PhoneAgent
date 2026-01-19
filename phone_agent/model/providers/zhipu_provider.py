#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
智谱AI视觉语言模型Provider
支持: GLM-4V, GLM-4V-Flash, GLM-4.1V-Thinking-Flash
"""

import re
import json
from typing import Any
from openai import OpenAI

from phone_agent.model.providers.base import BaseVLMProvider, VLMResponse


class ZhipuAIProvider(BaseVLMProvider):
    """智谱AI模型Provider"""
    
    DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "glm-4v-flash",
        base_url: str | None = None,
        **kwargs: Any
    ):
        base_url = base_url or self.DEFAULT_BASE_URL
        super().__init__(api_key, model_name, base_url, **kwargs)
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
    
    def generate(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs: Any
    ) -> VLMResponse:
        """使用智谱AI API生成响应"""
        
        # 准备请求参数
        request_params = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        # 添加额外参数(过滤None和0.0值)
        for key, value in self.extra_params.items():
            if value is not None and value != 0.0:
                request_params[key] = value
        
        # 用kwargs覆盖参数
        request_params.update(kwargs)
        
        # 调用API
        response = self.client.chat.completions.create(**request_params)
        
        # 提取内容
        raw_output = response.choices[0].message.content or ""
        
        # 解析思考和动作
        thinking, action = self.parse_response(raw_output)
        
        # 准备使用信息
        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        
        return VLMResponse(
            thinking=thinking,
            action=action,
            raw_output=raw_output,
            model=self.model_name,
            usage=usage,
        )
    
    def parse_response(self, raw_output: str) -> tuple[str, str]:
        """
        解析智谱AI模型响应
        
        支持GLM模型特有的多种输出格式:
        - AutoGLM: <think>...</think><answer>...</answer>
        - JSON: {"think": "...", "action": "..."}
        - Thinking模式: {think>...}</think><|begin_of_box|>...<|end_of_box|>
        - 多行: {think}...{action}do(...)
        """
        
        # 格式1: AutoGLM标准格式
        if "<answer>" in raw_output:
            parts = raw_output.split("<answer>", 1)
            thinking = parts[0].replace("<think>", "").replace("</think>", "").strip()
            action_part = parts[1].replace("</answer>", "").strip()
            action_match = re.search(r'((?:do|finish)\([^()]*(?:\([^()]*\)[^()]*)*\))', action_part)
            action = action_match.group(1).strip() if action_match else action_part
            return thinking, action
        
        # Format 2: JSON format
        try:
            data = json.loads(raw_output.strip())
            if isinstance(data, dict) and "think" in data and "action" in data:
                action_str = str(data["action"])
                action_match = re.search(r'((?:do|finish)\([^()]*(?:\([^()]*\)[^()]*)*\))', action_str)
                action = action_match.group(1).strip() if action_match else action_str
                return str(data["think"]), action
        except json.JSONDecodeError:
            pass
        
        # Format 3: GLM-4.1V-Thinking multi-line format {think}...{action}...
        think_action_match = re.search(
            r'\{think[>]?(.*?)\}\s*(?:\{action\})?\s*((?:do|finish)\([^()]*(?:\([^()]*\)[^()]*)*\))',
            raw_output,
            re.DOTALL
        )
        if think_action_match:
            thinking = think_action_match.group(1).strip()
            action = think_action_match.group(2).strip()
            return thinking, action
        
        # Format 4: GLM-4.1V-Thinking box format
        box_match = re.search(r'<\|begin_of_box\|\>(.*?)<\|end_of_box\|\>', raw_output, re.DOTALL)
        if box_match:
            action_box_content = box_match.group(1).strip()
            action_match = re.search(r'((?:do|finish)\([^()]*(?:\([^()]*\)[^()]*)*\))', action_box_content)
            action = action_match.group(1).strip() if action_match else action_box_content
            
            # Extract thinking
            think_match = re.search(r'\{think[>]?(.*?)\}', raw_output, re.DOTALL)
            thinking = think_match.group(1).strip() if think_match else ""
            return thinking, action
        
        # Format 5: Extract do(...) or finish(...) from anywhere
        action_match = re.search(r'((?:do|finish)\([^()]*(?:\([^()]*\)[^()]*)*\))', raw_output, re.DOTALL)
        if action_match:
            action = action_match.group(1).strip()
            thinking_match = re.search(r'(.*?)\s*' + re.escape(action), raw_output, re.DOTALL)
            thinking = thinking_match.group(1).strip() if thinking_match else ""
            # Clean up thinking
            thinking = re.sub(
                r'\{think[>]?\}?|\{\/think\}?|\</think\>|\{action\}|\<\|begin_of_box\|\>|\<\|end_of_box\|\>',
                '',
                thinking
            ).strip()
            return thinking, action
        
        # Default: treat entire output as action
        return "", raw_output
    
    def create_message(
        self,
        role: str,
        content: str | list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Create Zhipu AI-format message"""
        return {
            "role": role,
            "content": content,
        }
    
    def supports_vision(self) -> bool:
        """Check if model supports vision"""
        vision_keywords = ["4v", "vision", "multimodal"]
        return any(keyword in self.model_name.lower() for keyword in vision_keywords)

