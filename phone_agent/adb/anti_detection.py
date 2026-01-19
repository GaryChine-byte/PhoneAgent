#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
防风控模块 - Anti-Detection Module
为ADB操作添加人性化延迟和随机化，避免被识别为机器人

支持功能：
1. 时间随机化 - 人性化操作延迟
2. 坐标随机化 - 点击位置偏移
3. 贝塞尔曲线滑动 - 自然的滑动轨迹
4. 输入速度模拟 - 逐字打字
5. 探索行为 - 模拟真人寻找过程
"""

import random
import time
import math
from typing import Tuple, Optional, List, Dict, Any


def bezier_curve(p0: Tuple[float, float], 
                 p1: Tuple[float, float], 
                 p2: Tuple[float, float], 
                 p3: Tuple[float, float], 
                 steps: int = 20) -> List[Tuple[int, int]]:
    """
    生成三次贝塞尔曲线点
    
    Args:
        p0: 起点
        p1: 控制点1
        p2: 控制点2
        p3: 终点
        steps: 曲线分段数
    
    Returns:
        [(x, y), ...] 曲线上的点列表
    """
    points = []
    for i in range(steps + 1):
        t = i / steps
        
        # 三次贝塞尔曲线公式
        x = (1-t)**3 * p0[0] + \
            3 * (1-t)**2 * t * p1[0] + \
            3 * (1-t) * t**2 * p2[0] + \
            t**3 * p3[0]
        
        y = (1-t)**3 * p0[1] + \
            3 * (1-t)**2 * t * p1[1] + \
            3 * (1-t) * t**2 * p2[1] + \
            t**3 * p3[1]
        
        points.append((int(x), int(y)))
    
    return points


class AntiDetection:
    """防风控策略管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化防风控
        
        Args:
            config: 配置字典，包含各项功能的开关和参数
        """
        # 默认配置
        self.config = {
            "enabled": False,  # [OK] 默认关闭（避免影响点击准确性）
            "level": "low",    # [OK] 默认低延迟
            
            # 功能开关
            "enable_time_random": True,       # 时间随机化
            "enable_position_random": False,  # [OK] 默认关闭坐标随机化
            "enable_bezier_swipe": True,      # 贝塞尔曲线滑动
            "enable_typing_simulation": True, # 输入模拟
            "enable_exploration": False,      # [OK] 默认关闭探索行为
            
            # 时间配置
            "delay_levels": {
                "low": {"min": 0.2, "max": 0.5},      # [OK] 极速模式
                "medium": {"min": 0.3, "max": 1.0},   # [OK] 标准模式
                "high": {"min": 0.5, "max": 2.0}      # [OK] 谨慎模式
            },
            
            # 坐标随机化配置
            "position_offset_percentage": 0.02,  # [OK] 降低到±2%（原20%太大）
            
            # 贝塞尔曲线配置
            "bezier_steps": 20,                 # 曲线分段数
            "bezier_control_randomness": 100,   # 控制点随机范围(像素)
            
            # 输入配置
            "typing_delay": {"min": 0.1, "max": 0.3},
            "typo_probability": 0.05,           # 5%打错字概率
            "pause_every_n_chars": 10,          # 每N个字符停顿
            
            # 探索配置
            "exploration_probability": 0.3       # 30%探索概率
        }
        
        # 更新配置
        if config:
            self.config.update(config)
    
    @property
    def enabled(self) -> bool:
        """是否启用防风控"""
        return self.config.get("enabled", True)
    
    @property
    def level(self) -> str:
        """防护等级"""
        return self.config.get("level", "medium")
    
    def update_config(self, config: Dict[str, Any]):
        """
        更新配置
        
        Args:
            config: 新的配置项
        """
        self.config.update(config)
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self.config.copy()
    
    def set_level(self, level: str):
        """设置防护等级"""
        if level in ["low", "medium", "high"]:
            self.config["level"] = level
    
    def enable(self):
        """启用防风控"""
        self.config["enabled"] = True
    
    def disable(self):
        """禁用防风控"""
        self.config["enabled"] = False
    
    def enable_feature(self, feature: str):
        """启用特定功能"""
        key = f"enable_{feature}"
        if key in self.config:
            self.config[key] = True
    
    def disable_feature(self, feature: str):
        """禁用特定功能"""
        key = f"enable_{feature}"
        if key in self.config:
            self.config[key] = False
    
    def human_delay(self, min_override: Optional[float] = None, max_override: Optional[float] = None):
        """
        模拟人类操作延迟
        
        Args:
            min_override: 覆盖最小延迟
            max_override: 覆盖最大延迟
        """
        if not self.enabled or not self.config.get("enable_time_random", True):
            return
        
        delay_config = self.config["delay_levels"].get(self.level, self.config["delay_levels"]["medium"])
        min_sec = min_override if min_override is not None else delay_config["min"]
        max_sec = max_override if max_override is not None else delay_config["max"]
        
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
    
    def reading_delay(self):
        """模拟阅读延迟（查看内容）"""
        if not self.enabled:
            return
        
        delay = random.uniform(2.0, 5.0)
        time.sleep(delay)
    
    def thinking_delay(self):
        """模拟思考延迟（输入前）"""
        if not self.enabled:
            return
        
        delay = random.uniform(0.8, 2.0)
        time.sleep(delay)
    
    def random_offset(self, value: int, percentage: float = 0.2) -> int:
        """
        为坐标添加随机偏移
        
        Args:
            value: 原始值
            percentage: 偏移百分比（0.2 = ±20%）
        
        Returns:
            添加随机偏移后的值
        """
        if not self.enabled:
            return value
        
        offset_range = int(value * percentage)
        offset = random.randint(-offset_range, offset_range)
        return value + offset
    
    def randomize_point(
        self, 
        x: int, 
        y: int, 
        x_range: Optional[Tuple[int, int]] = None,
        y_range: Optional[Tuple[int, int]] = None
    ) -> Tuple[int, int]:
        """
        在指定范围内随机化点击坐标
        
        Args:
            x: 原始x坐标
            y: 原始y坐标
            x_range: X轴允许范围 (min, max)
            y_range: Y轴允许范围 (min, max)
        
        Returns:
            (random_x, random_y)
        """
        if not self.enabled or not self.config.get("enable_position_random", True):
            return x, y
        
        percentage = self.config.get("position_offset_percentage", 0.2)
        
        # 默认±percentage范围
        if x_range:
            random_x = random.randint(x_range[0], x_range[1])
        else:
            random_x = self.random_offset(x, percentage)
        
        if y_range:
            random_y = random.randint(y_range[0], y_range[1])
        else:
            random_y = self.random_offset(y, percentage)
        
        return random_x, random_y
    
    def generate_swipe_path(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int
    ) -> List[Tuple[int, int]]:
        """
        生成贝塞尔曲线滑动轨迹
        
        Args:
            start_x: 起点X
            start_y: 起点Y
            end_x: 终点X
            end_y: 终点Y
        
        Returns:
            [(x, y), ...] 滑动路径点列表
        """
        if not self.enabled or not self.config.get("enable_bezier_swipe", True):
            # 不使用贝塞尔，返回直线
            return [(start_x, start_y), (end_x, end_y)]
        
        # 起点和终点
        p0 = (start_x, start_y)
        p3 = (end_x, end_y)
        
        # 生成两个控制点（在路径中间，带随机偏移）
        randomness = self.config.get("bezier_control_randomness", 100)
        
        # 控制点1（靠近起点）
        p1_x = start_x + (end_x - start_x) / 3 + random.randint(-randomness, randomness)
        p1_y = start_y + (end_y - start_y) / 3 + random.randint(-randomness, randomness)
        p1 = (p1_x, p1_y)
        
        # 控制点2（靠近终点）
        p2_x = start_x + 2 * (end_x - start_x) / 3 + random.randint(-randomness, randomness)
        p2_y = start_y + 2 * (end_y - start_y) / 3 + random.randint(-randomness, randomness)
        p2 = (p2_x, p2_y)
        
        # 生成贝塞尔曲线
        steps = self.config.get("bezier_steps", 20)
        return bezier_curve(p0, p1, p2, p3, steps)
    
    def typing_delay(self) -> float:
        """
        获取打字延迟（每个字符）
        
        Returns:
            延迟秒数
        """
        if not self.enabled or not self.config.get("enable_typing_simulation", True):
            return 0.0
        
        typing_config = self.config.get("typing_delay", {"min": 0.1, "max": 0.3})
        return random.uniform(typing_config["min"], typing_config["max"])
    
    def should_make_typo(self) -> bool:
        """
        是否应该模拟打错字
        
        Returns:
            True表示应该打错字
        """
        if not self.enabled or not self.config.get("enable_typing_simulation", True):
            return False
        
        probability = self.config.get("typo_probability", 0.05)
        return random.random() < probability
    
    def should_explore(self) -> bool:
        """
        是否应该模拟探索行为（误点、滑动）
        
        Returns:
            True表示应该探索
        """
        if not self.enabled or not self.config.get("enable_exploration", True):
            return False
        
        probability = self.config.get("exploration_probability", 0.3)
        return random.random() < probability
    
    def get_pause_interval(self) -> int:
        """获取输入时的停顿间隔（每N个字符）"""
        return self.config.get("pause_every_n_chars", 10)


# 全局实例
_anti_detection = AntiDetection()


def get_anti_detection() -> AntiDetection:
    """获取全局防风控实例"""
    return _anti_detection


def load_config_from_file(file_path: str = "data/anti_detection_config.json") -> Dict[str, Any]:
    """
    从文件加载防风控配置
    
    Args:
        file_path: 配置文件路径
    
    Returns:
        配置字典
    """
    import json
    import os
    
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load anti-detection config from {file_path}: {e}")
    
    return {}


def save_config_to_file(config: Dict[str, Any], file_path: str = "data/anti_detection_config.json"):
    """
    保存防风控配置到文件
    
    Args:
        config: 配置字典
        file_path: 配置文件路径
    """
    import json
    import os
    
    os.makedirs("data", exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def init_from_config_file():
    """从配置文件初始化全局实例"""
    config = load_config_from_file()
    if config:
        _anti_detection.update_config(config)


def human_delay(min_sec: Optional[float] = None, max_sec: Optional[float] = None):
    """快捷函数：人类延迟"""
    _anti_detection.human_delay(min_sec, max_sec)


def reading_delay():
    """快捷函数：阅读延迟"""
    _anti_detection.reading_delay()


def thinking_delay():
    """快捷函数：思考延迟"""
    _anti_detection.thinking_delay()


def randomize_point(
    x: int, 
    y: int, 
    x_range: Optional[Tuple[int, int]] = None,
    y_range: Optional[Tuple[int, int]] = None
) -> Tuple[int, int]:
    """快捷函数：随机化坐标"""
    return _anti_detection.randomize_point(x, y, x_range, y_range)


# 使用示例
if __name__ == "__main__":
    ad = AntiDetection(level="medium")
    
    print("测试人类延迟...")
    start = time.time()
    ad.human_delay()
    print(f"延迟: {time.time() - start:.2f}秒")
    
    print("\n测试坐标随机化...")
    original = (500, 1000)
    for i in range(5):
        randomized = ad.randomize_point(*original)
        print(f"原坐标: {original} -> 随机坐标: {randomized}")
    
    print("\n测试打字延迟...")
    for _ in range(5):
        delay = ad.typing_delay()
        print(f"打字延迟: {delay:.3f}秒")

