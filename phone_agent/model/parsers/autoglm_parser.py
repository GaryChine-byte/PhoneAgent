#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
AutoGLM Response Parser

Parses AutoGLM's XML-like format:
<think>reasoning process</think>
<answer>action command</answer>
"""

import re
from typing import Tuple
from .base_parser import BaseResponseParser


class AutoGLMParser(BaseResponseParser):
    """
    Parser for AutoGLM (ZhipuAI) response format.
    
    Supported formats:
    1. XML-like tags: <think>...</think><answer>...</answer>
    2. Box format: <|begin_of_box|>...<|end_of_box|>
    3. Multi-line format: {think}...\\n{action}...
    """
    
    @property
    def name(self) -> str:
        return "autoglm"
    
    def parse(self, raw_content: str) -> Tuple[str, str]:
        """
        Parse AutoGLM response.
        
        Args:
            raw_content: Raw response from AutoGLM model
        
        Returns:
            Tuple of (thinking, action)
        """
        # Try Method 1: XML-like tags
        thinking, action = self._parse_xml_tags(raw_content)
        if thinking and action:
            return thinking, action
        
        # Try Method 2: Box format
        thinking, action = self._parse_box_format(raw_content)
        if thinking and action:
            return thinking, action
        
        # Try Method 3: Multi-line format
        thinking, action = self._parse_multiline_format(raw_content)
        if thinking and action:
            return thinking, action
        
        # Fallback: treat entire content as action
        return "", raw_content.strip()
    
    def _parse_xml_tags(self, content: str) -> Tuple[str, str]:
        """Parse <think>...</think><answer>...</answer> format."""
        think_match = re.search(r"<think>(.*?)</think>", content, re.DOTALL)
        answer_match = re.search(r"<answer>(.*?)</answer>", content, re.DOTALL)
        
        if think_match and answer_match:
            thinking = think_match.group(1).strip()
            action = answer_match.group(1).strip()
            return thinking, action
        
        return "", ""
    
    def _parse_box_format(self, content: str) -> Tuple[str, str]:
        """Parse <|begin_of_box|>...<|end_of_box|> format."""
        pattern = r"<\|begin_of_box\|>(.*?)<\|end_of_box\|>"
        boxes = re.findall(pattern, content, re.DOTALL)
        
        if len(boxes) >= 2:
            thinking = boxes[0].strip()
            action = boxes[1].strip()
            return thinking, action
        elif len(boxes) == 1:
            # Only action box found
            return "", boxes[0].strip()
        
        return "", ""
    
    def _parse_multiline_format(self, content: str) -> Tuple[str, str]:
        """
        Parse multi-line format:
        {think}
        reasoning...
        {action}
        do(...)
        """
        lines = content.split("\n")
        thinking_lines = []
        action_lines = []
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line == "{think}":
                current_section = "think"
            elif line == "{action}":
                current_section = "action"
            elif current_section == "think" and line:
                thinking_lines.append(line)
            elif current_section == "action" and line:
                action_lines.append(line)
        
        if thinking_lines and action_lines:
            thinking = "\n".join(thinking_lines)
            action = "\n".join(action_lines)
            return thinking, action
        
        return "", ""

