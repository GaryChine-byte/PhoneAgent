#!/usr/bin/env python3
# Copyright (C) 2025 PhoneAgent Contributors
# Licensed under AGPL-3.0

"""PhoneAgent API Module"""

from .app import create_app
from .routes import router

__all__ = ["create_app", "router"]

