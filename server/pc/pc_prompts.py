#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0
#
# PC Agent Prompts - 参考 MobileAgent PC-Agent 的 prompt 设计
# https://github.com/X-PLUG/MobileAgent/tree/main/PC-Agent
# MIT License, Copyright (c) 2022 mPLUG

"""
PC Agent 的 Prompt 模板

参考 MobileAgent PC-Agent 的设计，实现：
1. Action Prompt - 决策下一步操作
2. Reflection Prompt - 反思操作结果
3. Planning Prompt - 规划任务进度
"""

from typing import List, Dict, Optional


def get_action_prompt(
    instruction: str,
    perception_infos: List[Dict],
    width: int,
    height: int,
    thought_history: List[str],
    summary_history: List[str],
    action_history: List[str],
    reflection_history: List[str],
    last_summary: str,
    last_action: str,
    reflection_thought: str,
    error_flag: bool,
    completed_content: str,
    memory: str = "",
    add_info: str = "",
    ctrl_key: str = "ctrl",
    search_key: List[str] = None
) -> str:
    """
    生成 AI 决策的 Prompt
    
    构建包含任务指令、感知信息、历史操作等上下文的完整 Prompt，
    用于引导 AI 模型决策下一步操作。
    
    Args:
        instruction: 用户任务指令
        perception_infos: 感知信息列表，包含坐标和文本
        width: 屏幕宽度（像素）
        height: 屏幕高度（像素）
        thought_history: 历史思考记录
        summary_history: 历史操作摘要
        action_history: 历史动作记录
        reflection_history: 历史反思记录
        last_summary: 上次操作摘要
        last_action: 上次执行的动作
        reflection_thought: 反思内容
        error_flag: 上次操作是否出错
        completed_content: 已完成内容
        memory: 记忆内容（可选）
        add_info: 附加信息（可选）
        ctrl_key: 控制键名称，默认 "ctrl"（macOS 为 "command"）
        search_key: 搜索快捷键，默认 ["win", "s"]（macOS 为 ["command", "space"]）
    
    Returns:
        完整的 Prompt 字符串，用于发送给 AI 模型
    
    Note:
        - 参考 MobileAgent 的 get_action_prompt 设计
        - 坐标系统使用归一化格式 [0, 1000]
        - 支持跨平台（Windows/macOS）
    """
    prompt = "### Background ###\n"
    prompt += f"This image is a computer screenshot where interactive elements are marked with numbers. "
    prompt += f"Its width is {width} pixels and its height is {height} pixels. "
    prompt += f"The user's instruction is: {instruction}.\n\n"
    
    if add_info:
        prompt += add_info + "\n\n"
    
    # 感知信息
    if perception_infos and len(perception_infos) > 0:
        prompt += "### Screenshot information ###\n"
        prompt += "In order to help you better perceive the content in this screenshot, we extract some information of the current screenshot. "
        prompt += "This information consists of two parts: coordinates; content. "
        prompt += "The format of the coordinates is [x, y], x is the pixel from left to right and y is the pixel from top to bottom; "
        prompt += "the content is a text or 'icon' respectively. "
        prompt += "The information is as follow:\n"
        
        for info in perception_infos:
            if info['text'] != "" and info['text'] != "icon: None" and info['coordinates'] != (0, 0):
                prompt += f"{info['coordinates']}; {info['text']}\n"
        prompt += "\n"
    
    # 历史操作
    if len(action_history) > 0:
        prompt += "### History operations ###\n"
        prompt += "Before arriving at the current screenshot, you have completed the following operations:\n"
        for i in range(len(action_history)):
            if len(reflection_history) > 0:
                prompt += f"Step-{i+1}: [Operation: {summary_history[i].split(' to ')[0].strip()}; Action: {action_history[i]}; Reflection: {reflection_history[i]}]\n"
            else:
                prompt += f"Step-{i+1}: [Operation: {summary_history[i].split(' to ')[0].strip()}; Action: {action_history[i]}]\n"
        prompt += "\n"
    
    # 进度
    if completed_content != "":
        prompt += "### Progress ###\n"
        prompt += "After completing the history operations, you have the following thoughts about the progress of user's instruction completion:\n"
        prompt += "Completed contents:\n" + completed_content + "\n\n"
    
    # 记忆
    if memory != "":
        prompt += "### Memory ###\n"
        prompt += "During the operations, you record the following contents on the screenshot for use in subsequent operations:\n"
        prompt += "Memory:\n" + memory + "\n"
    
    # 上次操作错误
    if error_flag:
        prompt += "### Last operation ###\n"
        prompt += f"You previously wanted to perform the operation \"{last_summary}\" on this page and executed the Action \"{last_action}\". "
        prompt += "But you find that this operation does not meet your expectation. You need to reflect and revise your operation this time.\n\n"
    
    # 任务要求
    prompt += "### Task requirements ###\n"
    prompt += "In order to meet the user's requirements, you need to select one of the following operations to operate on the current screen:\n\n"
    
    # 归一化坐标系统说明 (与手机 Agent 保持一致: 0-1000)
    prompt += "### Coordinate System ###\n"
    prompt += "This system uses **normalized coordinates** in the range [0, 1000] (same as mobile agent):\n"
    prompt += "- (0, 0) = Top-left corner\n"
    prompt += "- (1000, 1000) = Bottom-right corner\n"
    prompt += "- (500, 500) = Screen center\n"
    prompt += "- Example: To click center, use Tap (500, 500)\n\n"
    
    if perception_infos and len(perception_infos) > 0:
        prompt += "Note: The coordinates in the ### Screenshot information ### section are **already normalized [0-1000]**. When you output Tap/Type/Replace/Append actions, use the same normalized format.\n"
    else:
        prompt += "Note: Since no extracted information is provided, you need to directly analyze the screenshot and output normalized coordinates [0-1000].\n"
    
    # 可用操作
    prompt += "You must choose one of the actions below:\n"
    prompt += "Tap (x, y): Tap the position (x, y) in current page. This can be used to select an item.\n"
    prompt += "TapIdx (index): Tap the element by its mark number. For example, 'TapIdx (5)' will tap the element marked as '5'. This is more reliable than using coordinates.\n"
    prompt += "Double Tap (x, y): Double tap the position (x, y) in the current page. This can be used to open a file.\n"
    prompt += "Double TapIdx (index): Double tap the element by its mark number.\n"
    
    # 根据平台动态生成快捷键示例
    if search_key is None:
        search_key = ["win", "s"]
    
    prompt += f"Shortcut (key1, key2): Use keyboard shortcuts. For example, {ctrl_key}+s to save, {ctrl_key}+a to select all, {ctrl_key}+c to copy, {ctrl_key}+v to paste, {ctrl_key}+n to create new file, {ctrl_key}+t to create new tab.\n"
    prompt += "Press (key name): Press a key. For example, 'backspace' to delete, 'enter' to confirm, 'up'/'down'/'left'/'right' to scroll.\n"
    prompt += "Type (x, y), (text): Tap the normalized position (x, y), type the \"text\" and press enter. Example: 'Type (500, 500), (hello)' types at screen center.\n"
    prompt += "Replace (x, y), (text): Replace the content at normalized position (x, y) with \"text\". Example: 'Replace (500, 300), (new text)'.\n"
    prompt += "Append (x, y), (text): Append text after the content at normalized position (x, y). Example: 'Append (500, 300), (more text)'.\n"
    prompt += "Open App (app name): Open an application by name. For example, 'Open App (notepad)' or 'Open App (chrome)'. **IMPORTANT**: This action will automatically open search, type the app name, and press Enter for you. You do NOT need to do anything else after using this action - just wait for the next screenshot to verify the app launched.\n"
    prompt += "Tell (answer): Tell me the answer to the query.\n"
    prompt += "finish(message=\"xxx\"): Use this action when you have accurately and completely finished the task. The message should describe what was accomplished. "
    prompt += "Examples of when to use finish:\n"
    prompt += "  - Instruction: 'Open Notepad' → finish(message=\"Notepad has been opened successfully\")\n"
    prompt += "  - Instruction: 'Open Notepad and type hello' → finish(message=\"Opened Notepad and typed 'hello'\")\n"
    prompt += "  - Instruction: 'Search for X in browser' → finish(message=\"Search results for X are displayed\")\n"
    prompt += "**IMPORTANT**: Only use finish when you can verify the final result is visible on the current screenshot. Do NOT finish just because you performed some operations.\n\n"
    
    # 输出格式
    prompt += "### Output format ###\n"
    prompt += "You should output in the following json format:\n"
    prompt += '{"Thought": "This is your thinking about how to proceed the next operation, please output the thoughts about the history operations explicitly.", '
    prompt += '"Action": "Tap () or TapIdx () or Double Tap () or Double TapIdx () or Shortcut () or Press() or Type () or Replace () or Append () or Open App () or Tell () or finish(message=\\"xxx\\"). Only one action can be output at one time.", '
    prompt += '"Summary": "This is a one sentence summary of this operation."}\n'
    prompt += "The output must contain the following fields: Thought (your reasoning about the next operation), Action (the specific action to take), and Summary (a one-sentence summary of the operation).\n"
    prompt += "**CRITICAL**: Ensure your JSON is properly formatted:\n"
    prompt += '- Use escaped quotes inside strings: \\"text\\" NOT "text"\n'
    prompt += '- Use apostrophes for contractions: don\'t, can\'t, Nuki\'s (NOT don"t, can"t, Nuki"s)\n'
    prompt += '- Add commas between all fields\n'
    prompt += "**Examples**:\n"
    prompt += '- Regular action: {"Thought": "Need to click the button", "Action": "Tap (500, 300)", "Summary": "Click the submit button"}\n'
    prompt += '- Task completion: {"Thought": "The task is complete, Notepad is open with text typed.", "Action": "finish(message=\\"Opened Notepad and typed hello\\")", "Summary": "Task completed successfully"}\n'
    prompt += '- With apostrophes: {"Thought": "I need to search for Nuki\'s materials. Don\'t forget to check all pages.", "Action": "Open App (chrome)", "Summary": "Open browser to search"}\n\n'
    prompt += "\n### Important Notes ###\n"
    prompt += "- **Prefer TapIdx over Tap**: When you see marked elements (mark number: 1, 2, 3...), use 'TapIdx (number)' instead of 'Tap (x, y)' for better reliability.\n"
    prompt += "- **Open App is a complete action**: When you use 'Open App (app name)', the system will automatically search, type, and press Enter. You do NOT need to click anything or press any keys afterward. Just observe the next screenshot to confirm the app opened.\n"
    prompt += "- **After Open App**: If you see the app opened successfully in the next screenshot, proceed with your actual task (like typing text). Do NOT try to click buttons in the search results.\n"
    prompt += "- **Use normalized coordinates [0-1000]**: For large UI areas (like Notepad's text editor), analyze the screenshot and use normalized coordinates. For example, center of screen = (500, 500), top-center = (500, 100).\n"
    prompt += "- **Always use specific numbers**: When using Type/Replace/Append, provide actual normalized coordinates like 'Type (500, 500), (text)', NOT placeholders like 'Type ((x, y), (text))'.\n"
    prompt += "- **When to use finish**: Use finish(message=\"xxx\") ONLY when you can see the final result on the current screenshot. For example:\n"
    prompt += "  [CORRECT] Instruction 'Open Notepad' → See Notepad window → Use finish(message=\"Notepad opened successfully\")\n"
    prompt += "  [CORRECT] Instruction 'Type hello in Notepad' → See 'hello' in Notepad → Use finish(message=\"Typed hello in Notepad\")\n"
    prompt += "  [WRONG] Instruction 'Open Notepad' → Just clicked Open App → Do NOT use finish yet (wait for next screenshot)\n"
    prompt += "- **JSON format is critical**: Always output valid JSON with commas between fields. When using finish, escape quotes: finish(message=\\\"xxx\\\"). Double-check your JSON before outputting.\n"
    
    # 根据平台生成搜索快捷键说明
    search_key_str = "+".join(search_key) if isinstance(search_key, list) else search_key
    if ctrl_key == "command":
        prompt += f"- On macOS: Open App uses {search_key_str} to open Spotlight search.\n"
    else:
        prompt += f"- On Windows: Open App uses {search_key_str} to open search.\n"
    
    prompt += "- Common app names: notepad, chrome, calculator, word, excel, outlook, etc.\n"
    prompt += "- The system will automatically handle Chinese app names and text input.\n\n"
    
    return prompt


def get_reflect_prompt(
    instruction: str,
    perception_infos_before: List[Dict],
    perception_infos_after: List[Dict],
    width: int,
    height: int,
    summary: str,
    action: str,
    add_info: str = ""
) -> str:
    """
    生成反思 prompt
    
    参考 MobileAgent 的 get_reflect_prompt
    """
    prompt = f"These images are two computer screenshots before and after an operation. "
    prompt += f"Their widths are {width} pixels and their heights are {height} pixels.\n\n"
    
    prompt += "In order to help you better perceive the content in this screenshot, we extract some information on the current screenshot. "
    prompt += "The information consists of two parts, consisting of format: coordinates; content. "
    prompt += "The format of the coordinates is [x, y], x is the pixel from left to right and y is the pixel from top to bottom; "
    prompt += "the content is a text or an icon description respectively\n\n"
    
    # 操作前
    if perception_infos_before and len(perception_infos_before) > 0:
        prompt += "### Before the current operation ###\n"
        prompt += "Screenshot information:\n"
        for info in perception_infos_before:
            if info['text'] != "" and info['text'] != "icon: None" and info['coordinates'] != (0, 0):
                prompt += f"{info['coordinates']}; {info['text']}\n"
        prompt += "\n\n"
    
    # 操作后
    if perception_infos_after and len(perception_infos_after) > 0:
        prompt += "### After the current operation ###\n"
        prompt += "Screenshot information:\n"
        for info in perception_infos_after:
            if info['text'] != "" and info['text'] != "icon: None" and info['coordinates'] != (0, 0):
                prompt += f"{info['coordinates']}; {info['text']}\n"
        prompt += "\n\n"
    
    # 当前操作
    prompt += "### Current operation ###\n"
    prompt += f"The user's instruction is: {instruction}."
    if add_info != "":
        prompt += f" You also need to note the following requirements: {add_info}."
    prompt += " In the process of completing the requirements of instruction, an operation is performed on the computer. Below are the details of this operation:\n"
    prompt += "Operation thought: " + summary.split(" to ")[0].strip() + "\n"
    prompt += "Operation action: " + action + "\n\n"
    
    # 响应要求
    prompt += "### Response requirements ###\n"
    prompt += "Now you need to output the following content based on the screenshots before and after the current operation:\n"
    prompt += "1. Whether the result of the \"Operation action\" meets your expectation of \"Operation thought\"?\n"
    prompt += "2. IMPORTANT: By carefully examining the screenshot after the operation, verify if the actual goal described in the user's instruction is achieved.\n"
    prompt += "Choose one of the following:\n"
    prompt += "A: The result of the \"Operation action\" meets my expectation of \"Operation thought\" AND the actual goal in the instruction is achieved based on the current screenshot.\n"
    prompt += "B: The \"Operation action\" results in a wrong page and I need to do something to correct this.\n"
    prompt += "C: The \"Operation action\" produces no changes.\n"
    prompt += "D: The \"Operation action\" seems to complete, but the actual goal in the instruction is NOT achieved based on the current screenshot (e.g., clicked wrong position, wrong item selected).\n\n"
    
    # 输出格式
    prompt += "### Output format ###\n"
    prompt += "Your output format is:\n"
    prompt += "### Thought ###\nYour thought about the question. Please explicitly verify if the goal in the instruction is achieved by checking the screenshot.\n"
    prompt += "### Answer ###\nA or B or C or D"
    
    return prompt


def get_planning_prompt(
    instruction: str,
    thought_history: List[str],
    summary_history: List[str],
    action_history: List[str],
    completed_content: str,
    add_info: str,
    reflection_history: List[str],
    perception_infos: List[Dict],
    width: int,
    height: int
) -> str:
    """
    生成规划 prompt
    
    参考 MobileAgent 的 get_process_prompt
    """
    prompt = "### Background ###\n"
    prompt += f"There is an user's instruction which is: {instruction}. You are a computer operating assistant and are operating the user's computer.\n\n"
    
    # 当前屏幕信息
    if perception_infos is not None and width is not None and height is not None:
        prompt += "### Current screenshot information ###\n"
        prompt += f"The current screen width is {width} pixels and height is {height} pixels.\n"
        prompt += "The following is the information extracted from the current screenshot (format: coordinates; content):\n"
        for info in perception_infos:
            if info['text'] != "" and info['text'] != "icon: None" and info['coordinates'] != (0, 0):
                prompt += f"{info['coordinates']}; {info['text']}\n"
        prompt += "\n"
    
    # 提示信息
    if add_info != "":
        prompt += "### Hint ###\n"
        prompt += "There are hints to help you complete the user's instructions. The hints are as follow:\n"
        prompt += add_info + "\n\n"
    
    # 历史操作
    if len(thought_history) > 1:
        prompt += "### History operations ###\n"
        prompt += "To complete the requirements of user's instruction, you have performed a series of operations. These operations are as follow:\n"
        for i in range(len(summary_history)):
            operation = summary_history[i].split(" to ")[0].strip()
            if len(reflection_history) > 0:
                prompt += f"Step-{i+1}: [Operation thought: {operation}; Operation action: {action_history[i]}; Operation reflection: {reflection_history[i]}]\n"
            else:
                prompt += f"Step-{i+1}: [Operation thought: {operation}; Operation action: {action_history[i]}]\n"
        prompt += "\n"
        
        prompt += "### Progress thinking ###\n"
        prompt += "After completing the history operations, you have the following thoughts about the progress of user's instruction completion:\n"
        prompt += "Completed contents:\n" + completed_content + "\n\n"
        
        prompt += "### Response requirements ###\n"
        prompt += "Now you need to update the \"Completed contents\" by comparing the user's instruction with the current screenshot.\n"
        prompt += "IMPORTANT: You must verify if the actual goal is achieved by checking the current screenshot information, not just assuming based on operation history.\n"
        prompt += "For example, if the instruction is to 'open Notepad', you need to verify if Notepad is actually open on the screen, not just because you clicked something.\n\n"
        
        prompt += "### Output format ###\n"
        prompt += "Your output format is:\n"
        prompt += "### Completed contents ###\nUpdated Completed contents. Don't output the purpose of any operation. Just summarize the contents that have been actually completed AND VERIFIED on the current screenshot."
    
    else:
        prompt += "### Current operation ###\n"
        prompt += "To complete the requirements of user's instruction, you have performed an operation. Your operation thought and action of this operation are as follows:\n"
        prompt += f"Operation thought: {thought_history[-1]}\n"
        operation = summary_history[-1].split(" to ")[0].strip()
        if len(reflection_history) > 0:
            prompt += f"Operation action: {operation}\nOperation reflection: {reflection_history[-1]}\n\n"
        else:
            prompt += f"Operation action: {operation}\n\n"
        
        prompt += "### Response requirements ###\n"
        prompt += "Now you need to combine all of the above to generate the \"Completed contents\".\n"
        prompt += "IMPORTANT: You must verify if the actual goal is achieved by checking the current screenshot information, not just assuming based on operation.\n"
        prompt += "Completed contents is a general summary of the current contents that have been completed. You need to first focus on the requirements of user's instruction, and then summarize the contents that have been completed.\n\n"
        
        prompt += "### Output format ###\n"
        prompt += "Your output format is:\n"
        prompt += "### Completed contents ###\nGenerated Completed contents. Don't output the purpose of any operation. Just summarize the contents that have been actually completed AND VERIFIED on the current screenshot.\n"
        prompt += "(Please use English to output)"
    
    return prompt
