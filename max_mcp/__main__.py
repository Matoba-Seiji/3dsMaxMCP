#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""3ds Max MCP Server 命令行入口。

支持通过以下方式运行：
    python -m max_mcp
    python -m max_mcp --port 50013
    uvx max-mcp

--port 用于在同一台机器上连接不同的 3ds Max 实例；未指定时读取
MAXMCP_PORT 环境变量，再回退到默认端口 50012。
"""

import argparse

from .server import main


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m max_mcp",
        description="3ds Max MCP stdio server",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="in-Max listener TCP port (default: MAXMCP_PORT env or 50012)",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="in-Max listener host (default: 127.0.0.1)",
    )
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()
    main(port=args.port, host=args.host)
