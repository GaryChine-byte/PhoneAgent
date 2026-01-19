#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0
#
# This file incorporates ideas from android-use project (Apache 2.0)
# Repository: https://github.com/languse-ai/android-use

"""
XML解析模块 V3 - 基于android-use的改进版本

核心改进:
1. 使用IOU(Intersection over Union)过滤重叠容器
2. 智能的父子节点关系处理
3. 更准确的交互元素识别
4. 支持长按操作(long-clickable)
5. 更好的文本聚合(收集子节点文本)

参考项目: android-use (languse-ai)
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class BoundingBox:
    """边界框"""
    x1: int
    y1: int
    x2: int
    y2: int
    
    @property
    def center(self) -> Tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)
    
    @property
    def area(self) -> int:
        return (self.x2 - self.x1) * (self.y2 - self.y1)
    
    def to_list(self) -> List[int]:
        return [self.x1, self.y1, self.x2, self.y2]


@dataclass
class DOMNode:
    """DOM节点 - 参考android-use的设计"""
    # 基本属性
    text: str = ""
    content_desc: str = ""
    resource_id: str = ""
    class_name: str = ""
    package: str = ""
    
    # 交互属性
    clickable: bool = False
    long_clickable: bool = False
    focusable: bool = False
    enabled: bool = True
    
    # 位置信息
    bounding_box: Optional[BoundingBox] = None
    
    # 树结构
    parent: Optional['DOMNode'] = None
    children: List['DOMNode'] = field(default_factory=list)
    
    # 索引(用于高亮)
    highlight_index: Optional[int] = None
    
    @property
    def is_interactive(self) -> bool:
        """是否是可交互节点"""
        return self.enabled and (self.clickable or self.long_clickable or self.focusable)
    
    @property
    def display_text(self) -> str:
        """显示文本 - 优先text,回退到content_desc"""
        return self.text or self.content_desc
    
    @property
    def has_parent_interactive(self) -> bool:
        """是否有可交互的父节点"""
        node = self.parent
        while node:
            if node.is_interactive:
                return True
            node = node.parent
        return False
    
    def get_all_text_recursive(self, max_depth: int = 3) -> str:
        """
        递归收集当前节点及子节点的所有文本
        用于给可交互元素提供更丰富的上下文
        """
        if max_depth <= 0:
            return self.display_text
        
        texts = []
        if self.display_text:
            texts.append(self.display_text)
        
        for child in self.children:
            # 如果子节点也是可交互的,就不收集它的文本(避免重复)
            if not child.is_interactive:
                child_text = child.get_all_text_recursive(max_depth - 1)
                if child_text:
                    texts.append(child_text)
        
        return " ".join(texts).strip()


def calculate_iou(box1: BoundingBox, box2: BoundingBox) -> Tuple[float, float, float]:
    """
    计算两个边界框的IOU(Intersection over Union)
    
    返回:
        (iou1, iou2, iou): 
        - iou1: 交集占box1的比例
        - iou2: 交集占box2的比例  
        - iou: 标准IOU(交集/并集)
    """
    # 计算交集
    x1 = max(box1.x1, box2.x1)
    y1 = max(box1.y1, box2.y1)
    x2 = min(box1.x2, box2.x2)
    y2 = min(box1.y2, box2.y2)
    
    if x2 < x1 or y2 < y1:
        return 0.0, 0.0, 0.0
    
    intersection = (x2 - x1) * (y2 - y1)
    area1 = box1.area
    area2 = box2.area
    union = area1 + area2 - intersection
    
    iou1 = intersection / area1 if area1 > 0 else 0
    iou2 = intersection / area2 if area2 > 0 else 0
    iou = intersection / union if union > 0 else 0
    
    return iou1, iou2, iou


def parse_bounds(bounds_str: str) -> Optional[BoundingBox]:
    """解析bounds字符串: "[x1,y1][x2,y2]" """
    try:
        bounds_clean = bounds_str.replace("][", ",").strip("[]")
        x1, y1, x2, y2 = map(int, bounds_clean.split(","))
        
        # 过滤无效bounds
        if x1 >= x2 or y1 >= y2:
            return None
        
        return BoundingBox(x1, y1, x2, y2)
    except (ValueError, AttributeError):
        return None


def parse_xml_to_tree(xml_content: str) -> Optional[DOMNode]:
    """
    解析XML为DOM树
    
    Args:
        xml_content: XML字符串
    
    Returns:
        根节点,如果解析失败返回None
    """
    try:
        root_element = ET.fromstring(xml_content)
    except ET.ParseError as e:
        logger.error(f"XML解析失败: {e}")
        return None
    
    def parse_node_recursive(element: ET.Element, parent: Optional[DOMNode]) -> DOMNode:
        """递归解析节点"""
        attrs = element.attrib
        
        # 提取属性
        node = DOMNode(
            text=attrs.get('text', '').strip(),
            content_desc=attrs.get('content-desc', '').strip(),
            resource_id=attrs.get('resource-id', ''),
            class_name=attrs.get('class', ''),
            package=attrs.get('package', ''),
            clickable=attrs.get('clickable', 'false') == 'true',
            long_clickable=attrs.get('long-clickable', 'false') == 'true',
            focusable=attrs.get('focusable', 'false') == 'true',
            enabled=attrs.get('enabled', 'true') == 'true',
            bounding_box=parse_bounds(attrs.get('bounds', '')),
            parent=parent
        )
        
        # 递归解析子节点
        for child_element in element:
            if child_element.tag == 'node':
                child_node = parse_node_recursive(child_element, node)
                node.children.append(child_node)
        
        return node
    
    return parse_node_recursive(root_element, None)


def collect_interactive_nodes(root: DOMNode) -> List[DOMNode]:
    """
    收集所有可交互节点和独立文本节点
    
    规则:
    1. 可交互节点(clickable/long_clickable/focusable)
    2. 有文本但没有可交互父节点的文本节点
    """
    nodes = []
    
    def traverse(node: DOMNode):
        # 可交互节点
        if node.is_interactive and node.bounding_box:
            nodes.append(node)
        # 独立文本节点(没有可交互父节点)
        elif node.display_text and not node.has_parent_interactive and node.bounding_box:
            nodes.append(node)
        
        for child in node.children:
            traverse(child)
    
    traverse(root)
    return nodes


def filter_container_nodes(nodes: List[DOMNode]) -> List[DOMNode]:
    """
    过滤掉包含多个其他节点的容器节点
    
    参考android-use的逻辑:
    - 如果一个节点包含2个以上其他节点,且自身没有文本,则过滤掉
    - 使用IOU判断包含关系: iou2 > 0.9 且 iou1 < 0.5
    """
    nodes_to_exclude: Set[int] = set()
    
    for i, container in enumerate(nodes):
        if not container.bounding_box:
            continue
        
        contained_count = 0
        for j, inner in enumerate(nodes):
            if i == j or not inner.bounding_box:
                continue
            
            iou1, iou2, _ = calculate_iou(container.bounding_box, inner.bounding_box)
            
            # inner几乎完全在container内,但container不在inner内
            if iou2 > 0.9 and iou1 < 0.5:
                contained_count += 1
        
        # 包含2个以上节点,且自身没有文本
        if contained_count > 2 and not container.display_text:
            nodes_to_exclude.add(i)
    
    return [node for i, node in enumerate(nodes) if i not in nodes_to_exclude]


def remove_overlapping_nodes(nodes: List[DOMNode]) -> List[DOMNode]:
    """
    去除高度重叠的节点
    
    参考android-use:
    - 按位置排序(从上到下,从左到右)
    - 如果两个节点IOU > 0.7,保留第一个
    """
    # 按位置排序
    sorted_nodes = sorted(nodes, key=lambda n: (
        n.bounding_box.center[1] if n.bounding_box else 0,
        n.bounding_box.center[0] if n.bounding_box else 0
    ))
    
    result = []
    for node1 in sorted_nodes:
        if not node1.bounding_box:
            continue
        
        is_duplicate = False
        for node2 in result:
            if not node2.bounding_box:
                continue
            
            _, _, iou = calculate_iou(node1.bounding_box, node2.bounding_box)
            if iou > 0.7:
                is_duplicate = True
                break
        
        if not is_duplicate:
            result.append(node1)
    
    return result


def assign_highlight_indices(nodes: List[DOMNode]) -> Dict[int, DOMNode]:
    """
    为节点分配高亮索引
    
    返回: {index: node} 映射
    """
    # 按位置排序(从上到下,从左到右)
    sorted_nodes = sorted(nodes, key=lambda n: (
        n.bounding_box.center[1] if n.bounding_box else 0,
        n.bounding_box.center[0] if n.bounding_box else 0
    ))
    
    selector_map = {}
    for idx, node in enumerate(sorted_nodes, start=1):
        node.highlight_index = idx
        selector_map[idx] = node
    
    return selector_map


def parse_ui_xml_v3(xml_content: str) -> Tuple[Optional[DOMNode], Dict[int, DOMNode]]:
    """
    解析UI XML (V3版本 - 基于android-use)
    
    Args:
        xml_content: XML字符串
    
    Returns:
        (root_node, selector_map): 根节点和索引映射
    """
    # 1. 解析为树
    root = parse_xml_to_tree(xml_content)
    if not root:
        return None, {}
    
    # 2. 收集可交互节点
    interactive_nodes = collect_interactive_nodes(root)
    logger.debug(f"收集到 {len(interactive_nodes)} 个可交互节点")
    
    # 3. 过滤容器节点
    filtered_nodes = filter_container_nodes(interactive_nodes)
    logger.debug(f"过滤容器后剩余 {len(filtered_nodes)} 个节点")
    
    # 4. 去除重叠节点
    unique_nodes = remove_overlapping_nodes(filtered_nodes)
    logger.debug(f"去重后剩余 {len(unique_nodes)} 个节点")
    
    # 5. 分配索引
    selector_map = assign_highlight_indices(unique_nodes)
    
    return root, selector_map


def format_selector_map_for_llm(selector_map: Dict[int, DOMNode]) -> str:
    """
    格式化selector_map为LLM可读的文本
    
    格式: [index](text)
    """
    lines = []
    for index, node in selector_map.items():
        # 收集节点及其子节点的所有文本
        text = node.get_all_text_recursive()
        if not text:
            # 如果没有文本,使用类型作为标识
            text = node.class_name.split('.')[-1] if node.class_name else "Element"
        
        lines.append(f"[{index}]({text})")
    
    return '\n'.join(lines)


# 向后兼容的UIElement类
@dataclass
class UIElement:
    """UI元素数据类 - 向后兼容"""
    resource_id: str
    text: str
    element_type: str
    bounds: str
    center: Tuple[int, int]
    clickable: bool
    focusable: bool
    enabled: bool
    long_clickable: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "id": self.resource_id,
            "text": self.text,
            "type": self.element_type,
            "bounds": self.bounds,
            "center": list(self.center),
            "clickable": self.clickable,
            "focusable": self.focusable,
            "enabled": self.enabled,
            "long_clickable": self.long_clickable,
            "action": "tap" if self.clickable else ("long_press" if self.long_clickable else ("input" if self.focusable else "read"))
        }


def convert_selector_map_to_elements(selector_map: Dict[int, DOMNode]) -> List[UIElement]:
    """将selector_map转换为UIElement列表(向后兼容)"""
    elements = []
    for node in selector_map.values():
        if not node.bounding_box:
            continue
        
        elements.append(UIElement(
            resource_id=node.resource_id.split('/')[-1] if '/' in node.resource_id else node.resource_id,
            text=node.display_text,
            element_type=node.class_name.split('.')[-1] if node.class_name else "Unknown",
            bounds=f"[{node.bounding_box.x1},{node.bounding_box.y1}][{node.bounding_box.x2},{node.bounding_box.y2}]",
            center=node.bounding_box.center,
            clickable=node.clickable,
            focusable=node.focusable,
            enabled=node.enabled,
            long_clickable=node.long_clickable
        ))
    
    return elements


__all__ = [
    "DOMNode",
    "BoundingBox",
    "UIElement",
    "parse_ui_xml_v3",
    "format_selector_map_for_llm",
    "convert_selector_map_to_elements",
    "calculate_iou"
]

__version__ = "3.0.0"

