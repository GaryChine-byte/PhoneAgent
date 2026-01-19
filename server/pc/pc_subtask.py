#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0
#
# This file incorporates prompt design from MobileAgent PC-Agent:
# https://github.com/X-PLUG/MobileAgent/tree/main/PC-Agent
# Copyright (c) 2022 mPLUG
# Licensed under the MIT License

"""
子任务分解模块

参考 MobileAgent PC-Agent 的子任务分解机制:
- 复杂任务自动分解为多个子任务
- 支持参数传递（字典格式）
- 每个子任务可独立执行
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def get_subtask_prompt(instruction: str) -> str:
    """
    生成子任务分解 Prompt
    
    参考 MobileAgent PC-Agent prompt_qwen.py
    
    Args:
        instruction: 用户指令
        
    Returns:
        子任务分解 prompt
    """
    func_prompt = '''A multi-modal agent completes a user's instruction by performing a series of actions such as clicking and typing. A user's instruction may consist of multiple subtasks across different applications. I want you to break down this complex instruction into several subtasks, which are of four types:

1. Regular string: For example, "Open dark mode in system settings";
2. String containing dictionary content: The result of the current subtask needs to be passed to other subtasks in a dictionary format, for example, "Check the emails from 'Paul' in Outlook and output the email details in a dict format like {'contact': 'Paul', 'mail_content': 'content of the email'}";
3. Formatted string containing the keys from previous subtasks: Use the information from previous subtasks to complete and independently execute the current subtask, for example, "Send {mail_content} via SMS to 'Joey'". Note: The text in the first "{""}" must be a key from the output of a previous subtask, and there should be no "''";
4. Formatted string containing the keys from previous subtasks and the dictionary content: This requires both information from previous subtasks to complete the current subtask and the result also needs to be passed to other subtasks in a dictionary format, for example, "Search for {question} on Google and output the relevant information in a dict format like {'info': 'related information'}".

For example, the compound instruction "Open Notepad, write 'Hello World', save as 'test.txt', then open Chrome and search for the file location" can be broken down into:
{
"subtask 1": "Open Notepad",
"subtask 2": "Type 'Hello World' in Notepad",
"subtask 3": "Save the file as 'test.txt' and output the file path in dict format {'file_path': 'path to test.txt'}",
"subtask 4": "Open Chrome and search for {file_path}"
}

Notes:
1. Strings or formatted strings containing dictionary content should explain as detailed as possible the meaning of each key in the dict;
2. Each key in a formatted string subtask must have a corresponding dict output in preceding subtasks;
3. Ensure each subtask can be executed independently;
4. Each subtask must specify a clear application (e.g., 'in Notepad', 'in Chrome');
5. Ensure dictionary values do not contain single quote characters.
'''
    
    inst_prompt = '''
User Instruction:
{}
'''

    format_prompt = '''
Please output the split subtasks in the following JSON format:
{
"subtask 1": "<description>",
"subtask 2": "<description>",
...
}
'''
    
    prompt = func_prompt + inst_prompt.format(instruction) + format_prompt
    return prompt


def parse_subtask_dict(subtask_output: str) -> Dict[str, str]:
    """
    解析子任务字典
    
    Args:
        subtask_output: LLM 输出的子任务字符串
        
    Returns:
        子任务字典 {"subtask 1": "...", "subtask 2": "..."}
    """
    import json
    import re
    
    # 提取 JSON 部分
    try:
        # 尝试直接解析
        if subtask_output.strip().startswith('{'):
            return json.loads(subtask_output)
        
        # 提取 ```json ... ``` 或 ``` ... ``` 包裹的内容
        match = re.search(r'```(?:json)?\s*\n(.*?)\n```', subtask_output, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        
        # 提取第一个 { ... }
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', subtask_output, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        
        logger.error(f"无法解析子任务输出: {subtask_output[:200]}")
        return {}
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失败: {e}")
        return {}


def validate_subtask_dict(subtask_dict: Dict[str, str]) -> bool:
    """
    验证子任务字典格式
    
    Args:
        subtask_dict: 子任务字典
        
    Returns:
        是否有效
    """
    if not subtask_dict:
        return False
    
    # 检查键格式: "subtask 1", "subtask 2", ...
    for i in range(1, len(subtask_dict) + 1):
        key = f"subtask {i}"
        if key not in subtask_dict:
            logger.error(f"缺少键: {key}")
            return False
    
    return True


def extract_parameters(subtask_text: str) -> List[str]:
    """
    提取子任务中的参数（格式化字符串中的 {key}）
    
    Args:
        subtask_text: 子任务文本
        
    Returns:
        参数列表 ["param1", "param2"]
    """
    import re
    return re.findall(r'\{(\w+)\}', subtask_text)


def substitute_parameters(subtask_text: str, answer_dict: Dict[str, str]) -> str:
    """
    替换子任务中的参数
    
    Args:
        subtask_text: 子任务文本（如 "Send {email} to John"）
        answer_dict: 参数字典（如 {"email": "hello@example.com"}）
        
    Returns:
        替换后的文本（如 "Send hello@example.com to John"）
    """
    try:
        # Python format 需要转义 { 和 }
        # 将 {'key': 'value'} 转换为 {{'key': 'value'}}
        formatted_text = subtask_text.replace("{'", "{{'").replace("'}", "'}}")
        return formatted_text.format(**answer_dict)
    except KeyError as e:
        logger.error(f"参数替换失败，缺少键: {e}")
        return subtask_text
