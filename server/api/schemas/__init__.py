#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
API Schemas - Pydantic 数据模型
用于定义 API 请求和响应的数据结构
"""

from server.api.schemas.task import CreateTaskRequest, TaskResponse
from server.api.schemas.device import DeviceResponse

__all__ = [
    "CreateTaskRequest",
    "TaskResponse",
    "DeviceResponse",
]

