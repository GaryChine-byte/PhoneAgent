#!/usr/bin/env python3
# Original: Copyright (c) 2024 ZAI Organization (Apache-2.0)
# Modified: Copyright (C) 2025 PhoneAgent Contributors (AGPL-3.0)
# Based on: https://github.com/zai-org/Open-AutoGLM

"""
Phone Agent - An AI-powered phone automation framework.

This package provides tools for automating Android phone interactions
using AI models for visual understanding and decision making.

Core Components:
- PhoneAgent: Main agent class for task execution
- ModelConfig: AI model configuration
- AgentConfig: Agent behavior configuration
- ADBDevice: Android device control
"""

__version__ = "1.0.0"

# Core exports
from phone_agent.kernel.vision_agent import PhoneAgent, AgentConfig
from phone_agent.model import ModelConfig, ModelClient

__all__ = [
    "PhoneAgent",
    "AgentConfig",
    "ModelConfig",
    "ModelClient",
    "__version__",
]
