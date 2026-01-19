#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
请求超时监控中间件
监控和记录所有API请求的耗时，识别慢请求
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TimeoutMonitorMiddleware(BaseHTTPMiddleware):
    """
    请求超时监控中间件
    
    功能：
    1. 记录每个请求的耗时
    2. 识别慢请求（超过阈值）
    3. 统计各端点的平均响应时间
    4. 提供诊断报告
    """
    
    def __init__(self, app, slow_request_threshold: float = 5.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold  # 慢请求阈值（秒）
        
        # 统计数据
        self.request_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'max_time': 0.0,
            'min_time': float('inf'),
            'slow_count': 0,
            'timeout_count': 0,
            'last_slow_requests': []  # 最近的慢请求记录
        })
        
        # 实时请求追踪（用于识别超时）
        self.active_requests = {}
        
        logger.info(f"⏱️ 超时监控中间件已启动，慢请求阈值: {slow_request_threshold}秒")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        # 生成请求ID
        request_id = f"{int(time.time() * 1000)}-{id(request)}"
        request_start = time.time()
        
        # 构建路径标识（不包含查询参数）
        path = request.url.path
        method = request.method
        endpoint = f"{method} {path}"
        
        # 记录请求开始
        self.active_requests[request_id] = {
            'endpoint': endpoint,
            'start_time': request_start,
            'path': path,
            'method': method
        }
        
        try:
            # 执行请求
            response = await call_next(request)
            
            # 计算耗时
            request_time = time.time() - request_start
            
            # 更新统计
            self._update_stats(endpoint, request_time, success=True)
            
            # 记录慢请求
            if request_time > self.slow_request_threshold:
                self._log_slow_request(endpoint, request_time, request_id)
            
            # 添加响应头（方便前端调试）
            response.headers["X-Request-Time"] = f"{request_time:.3f}s"
            response.headers["X-Request-ID"] = request_id
            
            # 日志记录
            log_level = logging.WARNING if request_time > self.slow_request_threshold else logging.DEBUG
            logger.log(
                log_level,
 f"{' SLOW' if request_time > self.slow_request_threshold else ''} "                 f"{endpoint} - {request_time:.3f}s"
            )
            
            return response
            
        except Exception as e:
            # 记录异常
            request_time = time.time() - request_start
            self._update_stats(endpoint, request_time, success=False)
            
            logger.error(
 f" {endpoint} - {request_time:.3f}s - ERROR: {str(e)}"             )
            raise
            
        finally:
            # 清理活跃请求记录
            self.active_requests.pop(request_id, None)
    
    def _update_stats(self, endpoint: str, request_time: float, success: bool = True):
        """更新统计数据"""
        stats = self.request_stats[endpoint]
        
        stats['count'] += 1
        stats['total_time'] += request_time
        stats['max_time'] = max(stats['max_time'], request_time)
        stats['min_time'] = min(stats['min_time'], request_time)
        
        if request_time > self.slow_request_threshold:
            stats['slow_count'] += 1
        
        if not success:
            stats['timeout_count'] += 1
    
    def _log_slow_request(self, endpoint: str, request_time: float, request_id: str):
        """记录慢请求"""
        stats = self.request_stats[endpoint]
        
        # 记录最近的慢请求（最多保留10条）
        slow_record = {
            'time': datetime.now().isoformat(),
            'duration': request_time,
            'request_id': request_id
        }
        
        stats['last_slow_requests'].append(slow_record)
        if len(stats['last_slow_requests']) > 10:
            stats['last_slow_requests'].pop(0)
        
        logger.warning(
 f" 慢请求告警: {endpoint} 耗时 {request_time:.2f}秒 "             f"(阈值: {self.slow_request_threshold}秒)"
        )
    
    def get_stats(self) -> dict:
        """获取统计报告"""
        report = {}
        
        for endpoint, stats in self.request_stats.items():
            if stats['count'] > 0:
                avg_time = stats['total_time'] / stats['count']
                slow_rate = (stats['slow_count'] / stats['count']) * 100
                
                report[endpoint] = {
                    'total_requests': stats['count'],
                    'average_time': round(avg_time, 3),
                    'max_time': round(stats['max_time'], 3),
                    'min_time': round(stats['min_time'], 3),
                    'slow_requests': stats['slow_count'],
                    'slow_rate': round(slow_rate, 2),
                    'timeout_count': stats['timeout_count'],
                    'last_slow_requests': stats['last_slow_requests'][-5:]  # 最近5条
                }
        
        # 按平均耗时排序
        sorted_report = dict(
            sorted(report.items(), key=lambda x: x[1]['average_time'], reverse=True)
        )
        
        return {
            'endpoints': sorted_report,
            'active_requests': len(self.active_requests),
            'slow_threshold': self.slow_request_threshold
        }
    
    def get_slow_endpoints(self, min_slow_rate: float = 10.0) -> list:
        """
        获取慢端点列表
        
        Args:
            min_slow_rate: 最小慢请求比例（百分比）
        """
        slow_endpoints = []
        
        for endpoint, stats in self.request_stats.items():
            if stats['count'] == 0:
                continue
                
            slow_rate = (stats['slow_count'] / stats['count']) * 100
            avg_time = stats['total_time'] / stats['count']
            
            if slow_rate >= min_slow_rate or avg_time > self.slow_request_threshold:
                slow_endpoints.append({
                    'endpoint': endpoint,
                    'average_time': round(avg_time, 3),
                    'slow_rate': round(slow_rate, 2),
                    'total_requests': stats['count'],
                    'slow_requests': stats['slow_count']
                })
        
        # 按慢请求比例排序
        return sorted(slow_endpoints, key=lambda x: x['slow_rate'], reverse=True)


# 全局实例
_timeout_monitor = None


def get_timeout_monitor() -> TimeoutMonitorMiddleware:
    """获取超时监控实例"""
    return _timeout_monitor


def set_timeout_monitor(monitor: TimeoutMonitorMiddleware):
    """设置超时监控实例"""
    global _timeout_monitor
    _timeout_monitor = monitor

