#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Manual startup entry point used by startup_mcp_listener.ms."""

import os
import sys


repository_root = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, os.pardir)
)
if repository_root not in sys.path:
    sys.path.insert(0, repository_root)

from max_mcp.ui import service

service.start()
