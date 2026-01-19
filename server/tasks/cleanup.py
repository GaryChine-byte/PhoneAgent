#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
后台清理任务模块

负责：
1. 清理过期截图（7天前）
2. 清理过期任务日志
3. 维护系统资源占用在合理范围
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class CleanupService:
    """清理服务"""
    
    def __init__(self):
        self.screenshot_dir = Path("data/screenshots")
        self.log_dir = Path("logs")
        self.screenshot_retention_days = 7  # 截图保留7天
        self.log_retention_days = 30        # 日志保留30天
        
        self._cleanup_task = None
    
    async def start(self):
        """启动定期清理任务"""
        async def cleanup_loop():
            while True:
                try:
                    # 每天凌晨3点执行清理
                    now = datetime.now()
                    next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
                    if next_run < now:
                        next_run += timedelta(days=1)
                    
                    wait_seconds = (next_run - now).total_seconds()
                    logger.info(f"📅 下次清理任务将在 {next_run.strftime('%Y-%m-%d %H:%M')} 执行")
                    
                    await asyncio.sleep(wait_seconds)
                    
                    # 执行清理
                    await self.run_cleanup()
                    
                except Exception as e:
                    logger.error(f"清理任务循环出错: {e}")
                    await asyncio.sleep(3600)  # 出错后1小时后重试
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info(" 清理服务已启动")
        # 启动时立即执行一次清理
        asyncio.create_task(self.run_cleanup())
    
    async def run_cleanup(self):
        """执行清理任务"""
        logger.info("🧹 开始执行清理任务...")
        
        # 清理截图
        screenshot_count = await self.cleanup_screenshots()
        
        # 清理日志
        log_count = await self.cleanup_logs()
        
        logger.info(f" 清理任务完成: 删除 {screenshot_count} 个截图, {log_count} 个日志文件")     
    async def cleanup_screenshots(self) -> int:
        """
        清理过期截图
        
        Returns:
            删除的文件数量
        """
        if not self.screenshot_dir.exists():
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=self.screenshot_retention_days)
        deleted_count = 0
        
        def _sync_cleanup():
            nonlocal deleted_count
            for root, dirs, files in os.walk(self.screenshot_dir):
                for file in files:
                    file_path = Path(root) / file
                    try:
                        # 检查文件修改时间
                        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if mtime < cutoff_date:
                            file_path.unlink()
                            deleted_count += 1
                    except Exception as e:
                        logger.error(f"删除截图失败 {file_path}: {e}")
        
        # 在线程池中执行IO操作
        await asyncio.get_event_loop().run_in_executor(None, _sync_cleanup)
        
        if deleted_count > 0:
            logger.info(f"🗑️ 截图清理: 删除 {deleted_count} 个超过 {self.screenshot_retention_days} 天的文件")
        
        return deleted_count
    
    async def cleanup_logs(self) -> int:
        """
        清理过期日志
        
        Returns:
            删除的文件数量
        """
        if not self.log_dir.exists():
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=self.log_retention_days)
        deleted_count = 0
        
        def _sync_cleanup():
            nonlocal deleted_count
            for root, dirs, files in os.walk(self.log_dir):
                for file in files:
                    # 只清理.log和.jsonl文件
                    if not (file.endswith('.log') or file.endswith('.jsonl')):
                        continue
                    
                    file_path = Path(root) / file
                    try:
                        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if mtime < cutoff_date:
                            file_path.unlink()
                            deleted_count += 1
                    except Exception as e:
                        logger.error(f"删除日志失败 {file_path}: {e}")
        
        await asyncio.get_event_loop().run_in_executor(None, _sync_cleanup)
        
        if deleted_count > 0:
            logger.info(f"🗑️ 日志清理: 删除 {deleted_count} 个超过 {self.log_retention_days} 天的文件")
        
        return deleted_count
    
    def stop(self):
        """停止清理服务"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        logger.info("清理服务已停止")


# 全局实例
_cleanup_service: CleanupService = None


def get_cleanup_service() -> CleanupService:
    """获取清理服务单例"""
    global _cleanup_service
    if _cleanup_service is None:
        _cleanup_service = CleanupService()
    return _cleanup_service


# 便捷启动函数
async def start_cleanup_service():
    """启动清理服务"""
    service = get_cleanup_service()
    await service.start()


if __name__ == "__main__":
    # 测试
    async def test():
        service = CleanupService()
        await service.run_cleanup()
    
    asyncio.run(test())

