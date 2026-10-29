# -*- coding: utf-8 -*-
"""Actions used by the 3ds Max top-level MCP menu."""

from max_mcp.connector import max_server_listener as listener
from max_mcp.connector import protocol


def _resolve_port(port=None):
    return protocol.PORT if port is None else int(port)


def start(port=None):
    """Start the in-Max listener. port=None uses MAXMCP_PORT or 50012."""
    return listener.start_mcp_server(port=_resolve_port(port))


def stop():
    return listener.stop_mcp_server()


def restart(port=None):
    return listener.restart_mcp_server(port=_resolve_port(port))


def status():
    running = listener.is_running()
    host = getattr(listener, "HOST", protocol.HOST)
    port = getattr(listener, "PORT", protocol.PORT)
    message = "3dsMaxMCP: %s (%s:%s)" % (
        "运行中" if running else "未运行", host, port
    )
    print(message)
    try:
        from pymxs import runtime as rt
        rt.messageBox(message, title="3dsMaxMCP")
    except Exception:
        pass
    return running
