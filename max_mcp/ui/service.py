"""Actions used by the 3ds Max top-level MCP menu."""

from max_mcp.connector import max_server_listener as listener
from max_mcp.connector.protocol import HOST, PORT


def start():
    return listener.start_mcp_server()


def stop():
    return listener.stop_mcp_server()


def restart():
    return listener.restart_mcp_server()


def status():
    running = listener.is_running()
    message = "3dsMaxMCP: %s (%s:%s)" % (
        "运行中" if running else "未运行", HOST, PORT
    )
    print(message)
    try:
        from pymxs import runtime as rt
        rt.messageBox(message, title="3dsMaxMCP")
    except Exception:
        pass
    return running
