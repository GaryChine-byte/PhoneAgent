#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""
Model Response Parser Factory

Inspired by GELab-Zero's parser_factory.py design.
Provides a pluggable architecture for parsing different model output formats.
"""

from .factory import ParserFactory, register_parser
from .base_parser import BaseResponseParser
from .autoglm_parser import AutoGLMParser

# Auto-register built-in parsers
register_parser("autoglm-phone", AutoGLMParser)
register_parser("glm-4v", AutoGLMParser)
register_parser("glm-4.1v-thinking-flash", AutoGLMParser)
register_parser("default", AutoGLMParser)

__all__ = [
    "ParserFactory",
    "register_parser",
    "BaseResponseParser",
    "AutoGLMParser",
]

