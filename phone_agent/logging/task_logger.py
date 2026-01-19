#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
Task Logger - JSONL Format

Implements GELab-Zero's structured logging approach:
- Each step is a JSON line
- Screenshots saved separately
- Performance metrics tracked
- Easy to parse and visualize

File structure:
    logs/
    ├── {task_id}.jsonl           # Step-by-step log
    ├── {task_id}/                # Screenshot directory
    │   ├── step_000.png
    │   ├── step_001.png
    │   └── ...
    └── {task_id}_summary.json    # Task summary
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

from .base_logger import BaseLogger


@dataclass
class StepLog:
    """Data class for a single step log entry."""
    task_id: str
    step: int
    timestamp: str
    thinking: str
    action: Dict[str, Any]
    observation: str
    screenshot_path: str | None = None
    performance: Dict[str, float] | None = None
    tokens_used: Dict[str, int] | None = None
    success: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for JSON serialization)."""
        return asdict(self)


class TaskLogger(BaseLogger):
    """
    Task logger with JSONL format (inspired by GELab-Zero).
    
    Features:
    - Each line is a complete JSON object (easy to stream)
    - Screenshots saved separately (avoid huge log files)
    - Human-readable timestamps
    - Machine-parseable format
    """
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize task logger.
        
        Args:
            log_dir: Base directory for all logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Task metadata cache (for summary generation)
        self._task_metadata: Dict[str, Dict[str, Any]] = {}
    
    def _get_log_path(self, task_id: str) -> Path:
        """Get path to task log file."""
        return self.log_dir / f"{task_id}.jsonl"
    
    def _get_screenshot_dir(self, task_id: str) -> Path:
        """Get screenshot directory for task."""
        screenshot_dir = self.log_dir / task_id
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        return screenshot_dir
    
    def _get_summary_path(self, task_id: str) -> Path:
        """Get path to task summary file."""
        return self.log_dir / f"{task_id}_summary.json"
    
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
        success: bool = True,
    ) -> None:
        """
        Log a single step (appends to JSONL file).
        
        Format:
        {"task_id": "...", "step": 0, "timestamp": "...", ...}
        {"task_id": "...", "step": 1, "timestamp": "...", ...}
        """
        log_entry = StepLog(
            task_id=task_id,
            step=step,
            timestamp=timestamp,
            thinking=thinking,
            action=action,
            observation=observation,
            screenshot_path=screenshot_path,
            performance=performance or {},
            tokens_used=tokens_used or {},
            success=success,
        )
        
        # Append to JSONL file (one line per step)
        log_path = self._get_log_path(task_id)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry.to_dict(), ensure_ascii=False) + "\n")
    
    def log_task_start(
        self,
        task_id: str,
        instruction: str,
        device_id: str,
        model_config: Dict[str, Any],
    ) -> None:
        """Log task initialization."""
        # [SECURITY] 脱敏 model_config，不保存 API Key
        sanitized_model_config = model_config.copy() if model_config else {}
        if "api_key" in sanitized_model_config:
            sanitized_model_config["api_key"] = "********"
        
        self._task_metadata[task_id] = {
            "task_id": task_id,
            "instruction": instruction,
            "device_id": device_id,
            "model_config": sanitized_model_config,  # 使用脱敏后的配置
            "started_at": datetime.now().isoformat(),
            "status": "running",
        }
        
        # Write initial summary
        self._update_summary(task_id)
    
    def log_task_complete(
        self,
        task_id: str,
        status: str,
        result_message: str,
        total_steps: int,
        total_time: float,
        total_tokens: int,
    ) -> None:
        """Log task completion."""
        if task_id in self._task_metadata:
            self._task_metadata[task_id].update({
                "status": status,
                "result_message": result_message,
                "completed_at": datetime.now().isoformat(),
                "total_steps": total_steps,
                "total_time": total_time,
                "total_tokens": total_tokens,
            })
        else:
            # Create minimal metadata if not found
            self._task_metadata[task_id] = {
                "task_id": task_id,
                "status": status,
                "result_message": result_message,
                "completed_at": datetime.now().isoformat(),
                "total_steps": total_steps,
                "total_time": total_time,
                "total_tokens": total_tokens,
            }
        
        # Write final summary
        self._update_summary(task_id)
    
    def _update_summary(self, task_id: str) -> None:
        """Update task summary file."""
        if task_id not in self._task_metadata:
            return
        
        summary_path = self._get_summary_path(task_id)
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(self._task_metadata[task_id], f, ensure_ascii=False, indent=2)
    
    def read_logs(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Read all logs for a task.
        
        Returns:
            List of step logs (chronological order)
        """
        log_path = self._get_log_path(task_id)
        if not log_path.exists():
            return []
        
        logs = []
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
        
        return logs
    
    def read_summary(self, task_id: str) -> Dict[str, Any] | None:
        """Read task summary."""
        summary_path = self._get_summary_path(task_id)
        if not summary_path.exists():
            return None
        
        with open(summary_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def list_tasks(self) -> List[str]:
        """List all task IDs."""
        task_ids = []
        for file in self.log_dir.glob("*.jsonl"):
            task_ids.append(file.stem)
        return sorted(task_ids, reverse=True)  # Newest first

