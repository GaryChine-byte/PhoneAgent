#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
Parser Factory - Dynamic Parser Registration

Based on GELab-Zero's parser_factory.py design pattern.
"""

from typing import Dict, Type
from .base_parser import BaseResponseParser


class ParserFactory:
    """
    Factory for managing and retrieving response parsers.
    
    Usage:
        # Register a parser
        ParserFactory.register("gpt-4v", OpenAIParser)
        
        # Get a parser
        parser = ParserFactory.get_parser("gpt-4v")
        thinking, action = parser.parse(response)
    """
    
    _parsers: Dict[str, Type[BaseResponseParser]] = {}
    
    @classmethod
    def register(cls, model_name: str, parser_class: Type[BaseResponseParser]) -> None:
        """
        Register a parser for a specific model.
        
        Args:
            model_name: Model identifier (e.g., "gpt-4v", "autoglm-phone")
            parser_class: Parser class (must inherit from BaseResponseParser)
        """
        if not issubclass(parser_class, BaseResponseParser):
            raise TypeError(f"{parser_class} must inherit from BaseResponseParser")
        
        cls._parsers[model_name] = parser_class
    
    @classmethod
    def get_parser(cls, model_name: str) -> BaseResponseParser:
        """
        Get parser instance for a model.
        
        Args:
            model_name: Model identifier
        
        Returns:
            Parser instance
        
        Raises:
            ValueError: If no parser is registered for the model
        """
        if model_name not in cls._parsers:
            # Fallback to default parser
            if "default" in cls._parsers:
                return cls._parsers["default"]()
            raise ValueError(f"No parser registered for model: {model_name}")
        
        return cls._parsers[model_name]()
    
    @classmethod
    def list_supported_models(cls) -> list[str]:
        """List all registered model names."""
        return list(cls._parsers.keys())
    
    @classmethod
    def is_supported(cls, model_name: str) -> bool:
        """Check if a model is supported."""
        return model_name in cls._parsers


def register_parser(model_name: str, parser_class: Type[BaseResponseParser]) -> None:
    """Convenience function for registering parsers."""
    ParserFactory.register(model_name, parser_class)

