#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
Base Response Parser Interface

Defines the contract for all model response parsers.
"""

from abc import ABC, abstractmethod
from typing import Tuple


class BaseResponseParser(ABC):
    """
    Abstract base class for model response parsers.
    
    Each model provider may have different output formats:
    - AutoGLM: <think>...</think><answer>...</answer>
    - OpenAI: JSON format
    - Claude: Structured text
    - Custom models: Custom formats
    
    This abstraction allows adding new models without modifying core code.
    """
    
    @abstractmethod
    def parse(self, raw_content: str) -> Tuple[str, str]:
        """
        Parse model response into thinking and action.
        
        Args:
            raw_content: Raw response string from the model
        
        Returns:
            Tuple of (thinking, action_string)
            - thinking: The AI's reasoning process
            - action_string: The action to execute (e.g., "do(action='Tap', ...)")
        
        Raises:
            ValueError: If the response cannot be parsed
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Parser name (for registration)."""
        pass
    
    @property
    def supports_streaming(self) -> bool:
        """Whether this parser supports streaming responses."""
        return False

