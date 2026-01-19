#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
Base class for Vision Language Model providers
"""

from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass


@dataclass
class VLMResponse:
    """Standardized response from VLM providers"""
    thinking: str  # Model's reasoning process
    action: str    # Action command to execute
    raw_output: str  # Original model output
    model: str     # Model name used
    usage: dict[str, Any] | None = None  # Token usage info


class BaseVLMProvider(ABC):
    """
    Abstract base class for Vision Language Model providers.
    All VLM providers must implement this interface.
    """
    
    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: str | None = None,
        **kwargs: Any
    ):
        """
        Initialize the VLM provider.
        
        Args:
            api_key: API key for authentication
            model_name: Name/identifier of the model
            base_url: Optional custom API endpoint
            **kwargs: Additional provider-specific parameters
        """
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url
        self.extra_params = kwargs
        
    @abstractmethod
    def generate(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs: Any
    ) -> VLMResponse:
        """
        Generate a response from the VLM.
        
        Args:
            messages: List of message dictionaries (system, user, assistant)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional generation parameters
            
        Returns:
            VLMResponse: Standardized response object
        """
        pass
    
    @abstractmethod
    def parse_response(self, raw_output: str) -> tuple[str, str]:
        """
        Parse the raw model output into thinking and action.
        
        Args:
            raw_output: Raw text output from the model
            
        Returns:
            tuple[str, str]: (thinking, action)
        """
        pass
    
    @abstractmethod
    def create_message(
        self,
        role: str,
        content: str | list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Create a message in the provider's expected format.
        
        Args:
            role: Message role (system/user/assistant)
            content: Message content (text or multimodal)
            
        Returns:
            dict: Message in provider's format
        """
        pass
    
    @abstractmethod
    def supports_vision(self) -> bool:
        """
        Check if the model supports vision inputs.
        
        Returns:
            bool: True if vision is supported
        """
        pass
    
    def get_model_info(self) -> dict[str, Any]:
        """
        Get information about the model.
        
        Returns:
            dict: Model metadata
        """
        return {
            "provider": self.__class__.__name__,
            "model": self.model_name,
            "base_url": self.base_url,
            "supports_vision": self.supports_vision(),
        }

