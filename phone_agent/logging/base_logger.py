#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
Base Logger Interface

Inspired by GELab-Zero's base_logger.py design pattern.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseLogger(ABC):
    """
    Abstract base class for all loggers.
    
    This interface ensures consistency across different logging implementations
    (local file, remote server, database, etc.)
    """
    
    @abstractmethod
    def log_step(
        self,
        task_id: str,
        step: int,
        timestamp: str,
        thinking: str,
        action: Dict[str, Any],
        observation: str,
        screenshot_path: str | None = None,
        performance: Dict[str, float] | None = None,
        tokens_used: Dict[str, int] | None = None,
    ) -> None:
        """
        Log a single step execution.
        
        Args:
            task_id: Unique task identifier
            step: Step number (0-indexed)
            timestamp: ISO 8601 timestamp
            thinking: AI's reasoning/thinking process
            action: Action dictionary (parsed)
            observation: Result or observation after action
            screenshot_path: Path to screenshot (if available)
            performance: Performance metrics (inference_time, etc.)
            tokens_used: Token usage statistics
        """
        pass
    
    @abstractmethod
    def log_task_start(
        self,
        task_id: str,
        instruction: str,
        device_id: str,
        model_config: Dict[str, Any],
    ) -> None:
        """Log task initialization."""
        pass
    
    @abstractmethod
    def log_task_complete(
        self,
        task_id: str,
        status: str,  # "success" | "failed" | "cancelled"
        result_message: str,
        total_steps: int,
        total_time: float,
        total_tokens: int,
    ) -> None:
        """Log task completion."""
        pass
    
    @abstractmethod
    def read_logs(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Read all logs for a task.
        
        Args:
            task_id: Task identifier
        
        Returns:
            List of log entries (chronological order)
        """
        pass

