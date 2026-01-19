#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
Model Registry and Factory Pattern
Central registry for all VLM providers
"""

from typing import Any, Type
from phone_agent.model.providers.base import BaseVLMProvider


class ModelRegistry:
    """
    Registry for VLM providers.
    Allows dynamic registration and retrieval of model providers.
    """
    
    _providers: dict[str, Type[BaseVLMProvider]] = {}
    _aliases: dict[str, str] = {}
    
    @classmethod
    def register(
        cls,
        name: str,
        provider_class: Type[BaseVLMProvider],
        aliases: list[str] | None = None
    ) -> None:
        """
        Register a VLM provider.
        
        Args:
            name: Unique name for the provider
            provider_class: Provider class (must inherit from BaseVLMProvider)
            aliases: Optional list of alias names
        """
        if not issubclass(provider_class, BaseVLMProvider):
            raise TypeError(
                f"Provider class must inherit from BaseVLMProvider, "
                f"got {provider_class}"
            )
        
        cls._providers[name.lower()] = provider_class
        
        # Register aliases
        if aliases:
            for alias in aliases:
                cls._aliases[alias.lower()] = name.lower()
    
    @classmethod
    def get_provider(
        cls,
        name: str,
        api_key: str,
        model_name: str,
        **kwargs: Any
    ) -> BaseVLMProvider:
        """
        Get a VLM provider instance.
        
        Args:
            name: Provider name or alias
            api_key: API key for authentication
            model_name: Model name/identifier
            **kwargs: Additional provider-specific parameters
            
        Returns:
            BaseVLMProvider: Provider instance
        """
        # Check aliases first
        provider_name = cls._aliases.get(name.lower(), name.lower())
        
        # Get provider class
        provider_class = cls._providers.get(provider_name)
        
        if provider_class is None:
            available = list(cls._providers.keys())
            raise ValueError(
                f"Unknown provider: {name}. "
                f"Available providers: {', '.join(available)}"
            )
        
        # Instantiate and return
        return provider_class(
            api_key=api_key,
            model_name=model_name,
            **kwargs
        )
    
    @classmethod
    def list_providers(cls) -> list[str]:
        """
        List all registered providers.
        
        Returns:
            list[str]: Provider names
        """
        return list(cls._providers.keys())
    
    @classmethod
    def get_provider_aliases(cls, name: str) -> list[str]:
        """
        Get all aliases for a provider.
        
        Args:
            name: Provider name
            
        Returns:
            list[str]: List of aliases
        """
        provider_name = name.lower()
        return [
            alias for alias, provider in cls._aliases.items()
            if provider == provider_name
        ]
    
    @classmethod
    def auto_detect_provider(cls, model_name: str) -> str | None:
        """
        Auto-detect provider based on model name.
        
        Args:
            model_name: Model name
            
        Returns:
            str | None: Detected provider name or None
        """
        model_lower = model_name.lower()
        
        # Detection patterns (只支持智谱AI)
        patterns = {
            "zhipu": ["glm-4", "glm-3", "chatglm", "autoglm"],
        }
        
        for provider, keywords in patterns.items():
            if any(keyword in model_lower for keyword in keywords):
                return provider
        
        return None


def register_provider(
    name: str,
    aliases: list[str] | None = None
):
    """
    Decorator to register a VLM provider.
    
    Usage:
        @register_provider("my_provider", aliases=["mp", "myprovider"])
        class MyProvider(BaseVLMProvider):
            ...
    """
    def decorator(provider_class: Type[BaseVLMProvider]):
        ModelRegistry.register(name, provider_class, aliases)
        return provider_class
    return decorator


# Register built-in providers (只注册智谱AI)
from phone_agent.model.providers.zhipu_provider import ZhipuAIProvider

ModelRegistry.register("zhipu", ZhipuAIProvider, aliases=["glm", "zhipuai", "chatglm"])

