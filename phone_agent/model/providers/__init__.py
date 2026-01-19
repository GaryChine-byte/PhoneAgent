#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
Multi-modal Vision Language Model Providers
Support for Zhipu AI VLM models
"""

from phone_agent.model.providers.base import BaseVLMProvider
from phone_agent.model.providers.zhipu_provider import ZhipuAIProvider
from phone_agent.model.providers.registry import ModelRegistry, register_provider

__all__ = [
    "BaseVLMProvider",
    "ZhipuAIProvider",
    "ModelRegistry",
    "register_provider",
]

