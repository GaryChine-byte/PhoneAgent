#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
响应格式解析器

从 client.py 抽取的格式识别和解析逻辑
职责：识别不同模型的输出格式，提取 thinking 和 action 部分

支持的格式：
1. Vision Kernel (XML+JSON): <thinking>...</thinking><tool_call>{...}</tool_call>
2. AutoGLM: <think>...</think><answer>...</answer>
3. 纯 JSON: {"think": "...", "action": "..."}
4. GLM-Thinking: {think}...{action}...
5. GLM-Thinking Box: {think>...}<|begin_of_box|>...<|end_of_box|>
6. 兜底：正则提取 do(...) 指令
"""

import re
import json
import logging
from typing import Union

logger = logging.getLogger(__name__)


class ResponseParser:
    """响应格式解析器"""
    
    @staticmethod
    def parse(content: str) -> tuple[str, Union[dict, str]]:
        """
        解析模型响应，提取 thinking 和 action
        
        Args:
            content: 模型的原始响应文本
            
        Returns:
            (thinking, action_data)
            - thinking: str - 思考过程文本
            - action_data: dict | str
              - dict: 标准 JSON 格式（优先）
              - str: do() 格式字符串（兼容）
        
        格式优先级：
        1. XML+JSON混合格式（Vision Kernel标准）→ 返回 dict
        2. AutoGLM 标准格式 → 返回 str
        3. JSON 格式 → 返回 dict 或 str
        4. GLM-Thinking 格式 → 返回 str
        5. 纯文本提取（兜底）→ 返回 str
        """
        
        # 格式1: Vision Kernel XML+JSON混合格式
        result = ResponseParser._parse_xml_json_format(content)
        if result:
            return result
        
        # 格式2: AutoGLM 标准格式
        result = ResponseParser._parse_autoglm_format(content)
        if result:
            return result
        
        # 格式3: 纯 JSON 格式
        result = ResponseParser._parse_json_format(content)
        if result:
            return result
        
        # 格式4: GLM-Thinking 格式
        result = ResponseParser._parse_glm_thinking_format(content)
        if result:
            return result
        
        # 格式5: GLM-Thinking Box 格式
        result = ResponseParser._parse_glm_box_format(content)
        if result:
            return result
        
        # 格式6: 兜底 - 正则提取
        result = ResponseParser._parse_fallback(content)
        if result:
            return result
        
        # 完全无法解析
        logger.warning(f"无法解析响应格式: {content[:200]}")
        return "", ""
    
    @staticmethod
    def _parse_xml_json_format(content: str) -> tuple[str, dict] | None:
        """
        解析 Vision Kernel XML+JSON 混合格式
        
        格式1: <thinking>...</thinking><tool_call>{JSON}</tool_call>
        格式2: <thinking>...</thinking>{JSON}  (模型偷懒，省略 tool_call 标签)
        返回: (thinking, action_dict)
        
        容错处理：
        1. </thinking> 缺失：从 <thinking> 到 <tool_call> 之间提取
        2. </tool_call> 缺失：从 <tool_call> 之后提取所有内容
        3. <tool_call> 标签完全缺失：直接提取 </thinking> 之后的 JSON
        4. JSON 不完整：尝试补全右大括号
        """
        if "<thinking>" not in content:
            return None
        
        # 🔥 容错增强：支持没有 <tool_call> 标签的情况
        has_tool_call_tag = "<tool_call>" in content
        
        try:
            # 提取 thinking（容错：</thinking> 可能缺失）
            thinking_match = re.search(r'<thinking>(.*?)</thinking>', content, re.DOTALL)
            if thinking_match:
                thinking = thinking_match.group(1).strip()
            else:
                # 容错：从 <thinking> 到 <tool_call> 或 JSON 之间提取
                thinking_start = content.find('<thinking>') + len('<thinking>')
                if has_tool_call_tag:
                    thinking_end = content.find('<tool_call>')
                else:
                    # 如果没有 tool_call 标签，找第一个 { 的位置
                    thinking_end = content.find('{', thinking_start)
                
                if thinking_start > 0 and thinking_end > thinking_start:
                    thinking = content[thinking_start:thinking_end].strip()
                    logger.debug("容错：</thinking> 标签缺失，提取到分隔符之间的内容")
                else:
                    thinking = ""
            
            # 🔥 新增：处理没有 <tool_call> 标签的情况
            if not has_tool_call_tag:
                # 直接从 </thinking> 之后提取 JSON
                thinking_end_tag = content.find('</thinking>')
                if thinking_end_tag != -1:
                    tool_call_content = content[thinking_end_tag + len('</thinking>'):].strip()
                    logger.info("容错：<tool_call> 标签完全缺失，提取 </thinking> 之后的内容")
                else:
                    # 如果连 </thinking> 都没有，从第一个 { 开始提取
                    json_start = content.find('{')
                    if json_start != -1:
                        tool_call_content = content[json_start:].strip()
                        logger.info("容错：thinking 标签不完整，直接提取 JSON 部分")
                    else:
                        return None
            else:
                # 提取 tool_call 中的 JSON（容错：</tool_call> 可能缺失）
                tool_call_match = re.search(r'<tool_call>(.*?)</tool_call>', content, re.DOTALL)
                
                if not tool_call_match:
                    # 容错：</tool_call> 缺失，尝试提取 <tool_call> 之后的所有内容
                    tool_call_start = content.find('<tool_call>')
                    if tool_call_start != -1:
                        tool_call_content = content[tool_call_start + len('<tool_call>'):].strip()
                        logger.info("容错：</tool_call> 标签缺失，提取 <tool_call> 之后的所有内容")
                    else:
                        return None
                else:
                    tool_call_content = tool_call_match.group(1).strip()
            
            # 解析 JSON（容错：可能不完整）
            try:
                tool_data = json.loads(tool_call_content)
                
                # 验证是否是标准 JSON 格式
                if not isinstance(tool_data, dict) or "action" not in tool_data:
                    return None
                
                action_name = tool_data.get("action", "")
                
                # 检查错误格式：参数在 action 字符串中
                if "(" in action_name or ")" in action_name:
                    logger.warning(f"检测到错误的 action 格式: {action_name}")
                    # 返回原始字符串，让后续处理
                    return thinking, tool_call_content
                
                # 🔥 Phase 4 关键改动：直接返回 dict，不再转换为 do() 格式
                # 容错：finish → done
                if action_name.lower() == "finish":
                    tool_data["action"] = "done"
                
                return thinking, tool_data
                
            except json.JSONDecodeError as e:
                # JSON 解析失败，尝试容错
                logger.info(f"JSON 解析失败: {e}，尝试容错补全")
                
                # 容错 1：可能缺少右大括号
                if tool_call_content.strip().startswith('{') and not tool_call_content.strip().endswith('}'):
                    try:
                        fixed_content = tool_call_content.strip() + '\n}'
                        tool_data = json.loads(fixed_content)
                        logger.info("容错成功：补全了缺失的右大括号")
                        
                        if isinstance(tool_data, dict) and "action" in tool_data:
                            # finish → done
                            if tool_data.get("action", "").lower() == "finish":
                                tool_data["action"] = "done"
                            return thinking, tool_data
                    except json.JSONDecodeError:
                        pass
                
                # 容错 2：可能是旧的 do() 格式
                if tool_call_content.startswith('do('):
                    logger.info("检测到旧的 do() 格式，返回原始字符串")
                    return thinking, tool_call_content
                
                return None
                
        except (AttributeError, Exception) as e:
            logger.debug(f"XML+JSON 格式解析失败: {e}")
            return None
    
    @staticmethod
    def _parse_autoglm_format(content: str) -> tuple[str, str] | None:
        """
        解析 AutoGLM 标准格式
        
        格式: <think>...</think><answer>...</answer>
        返回: (thinking, action_str)
        """
        if "<answer>" not in content:
            return None
        
        parts = content.split("<answer>", 1)
        thinking = parts[0].replace("<think>", "").replace("</think>", "").strip()
        action = parts[1].replace("</answer>", "").strip()
        return thinking, action
    
    @staticmethod
    def _parse_json_format(content: str) -> tuple[str, Union[dict, str]] | None:
        """
        解析纯 JSON 格式
        
        格式: {"think": "...", "action": "..."}
        返回: (thinking, action_str 或 action_dict)
        """
        if not (content.strip().startswith("{") and '"think"' in content and '"action"' in content):
            return None
        
        try:
            data = json.loads(content.strip())
            if isinstance(data, dict) and "think" in data and "action" in data:
                thinking = str(data["think"])
                action = data["action"]
                
                # 如果 action 是 dict，直接返回
                if isinstance(action, dict):
                    return thinking, action
                # 否则返回字符串
                return thinking, str(action)
                
        except json.JSONDecodeError:
            # JSON 解析失败，尝试正则提取
            think_match = re.search(r'"think"\s*:\s*"([^"]*(?:"[^"]*"[^"]*)*)"', content)
            if not think_match:
                think_match = re.search(r'"think"\s*:\s*"(.*?)",\s*"action"', content, re.DOTALL)
            
            action_match = re.search(r'"action"\s*:\s*"(do\([^)]+\))"', content)
            
            if think_match and action_match:
                thinking = think_match.group(1).strip()
                action = action_match.group(1).strip()
                return thinking, action
        
        return None
    
    @staticmethod
    def _parse_glm_thinking_format(content: str) -> tuple[str, str] | None:
        """
        解析 GLM-4.1V-Thinking 格式
        
        格式: {think}...{action}...
        返回: (thinking, action_str)
        """
        if "{think}" not in content or "{action}" not in content:
            return None
        
        think_match = re.search(r'\{think\}(.*?)\{action\}', content, re.DOTALL)
        if not think_match:
            return None
        
        thinking = think_match.group(1).strip()
        
        # 提取 {action} 后面的内容
        action_section = content.split("{action}")[1]
        action_match = re.search(r'((?:do|finish)\([^)]+\))', action_section)
        action = action_match.group(1).strip() if action_match else action_section.split('\n')[0].strip()
        
        # 移除注释
        action = re.sub(r'//[^\n]*', '', action).strip()
        return thinking, action
    
    @staticmethod
    def _parse_glm_box_format(content: str) -> tuple[str, str] | None:
        """
        解析 GLM-4.1V-Thinking Box 格式
        
        格式: {think>...}<|begin_of_box|>...<|end_of_box|>
        返回: (thinking, action_str)
        """
        if "{think>" not in content and "{think}" not in content:
            return None
        
        # 提取 thinking
        think_match = re.search(r'\{think[>]?(.*?)\}', content, re.DOTALL)
        thinking = think_match.group(1).strip() if think_match else ""
        
        # 提取 action（在 box 标记内或 think 后面）
        box_match = re.search(r'<\|begin_of_box\|\>(.*?)<\|end_of_box\|\>', content, re.DOTALL)
        if box_match:
            action = box_match.group(1).strip()
            action = re.sub(r'^\{action\}', '', action).strip()
            action = re.sub(r'//[^\n]*', '', action).strip()
        else:
            # 没有 box 标记，寻找 {action}...
            action_match = re.search(r'\{action\}(.*?)(?:\n//|$)', content, re.DOTALL)
            if action_match:
                action = action_match.group(1).strip()
            else:
                # 取 think 后面的内容
                action_match = re.search(r'\{think[>]?.*?\}(.*)$', content, re.DOTALL)
                action = action_match.group(1).strip() if action_match else ""
                action = re.sub(r'//[^\n]*', '', action).strip()
        
        return thinking, action if action else None
    
    @staticmethod
    def _parse_fallback(content: str) -> tuple[str, str] | None:
        """
        兜底解析：正则提取 do(...) 或 finish(...) 指令
        
        返回: (thinking, action_str)
        """
        # 查找所有 do(...) 或 finish(...) 模式
        all_matches = []
        for match in re.finditer(r'((?:do|finish)\s*\([^()]*(?:\[[^\]]*\])?[^()]*(?:\([^()]*\)[^()]*)*\))', content):
            all_matches.append(match.group(1))
        
        if not all_matches:
            return None
        
        # 取最后一个匹配（通常是最终的 action）
        action = all_matches[-1].strip()
        
        # thinking 是 action 之前的内容
        idx = content.rfind(action)
        thinking = content[:idx] if idx > 0 else ""
        
        # 清理 thinking
        thinking = thinking.replace("<think>", "").replace("</think>", "")
        thinking = thinking.replace("<thinking>", "").replace("</thinking>", "")
        thinking = thinking.strip()
        
        # 限制 thinking 长度
        if len(thinking) > 500:
            thinking = thinking[-500:]
        
        return thinking, action


__all__ = ["ResponseParser"]
