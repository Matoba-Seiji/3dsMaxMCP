#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""3ds Max MCP Server 核心服务模块。

提供 MCP Server 的完整实现，包括：
- 工具注册与发现
- 脚本生成与发送至 3ds Max
- MCP 协议通信
"""

# Import built-in modules
import os
import json
import asyncio
import traceback
from pprint import pformat
from itertools import chain

# Import third-party modules
import mcp.server.stdio
from typing import Sequence, List, Any, Dict
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from mcp.server.fastmcp.utilities.types import Image
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import pydantic_core

# Import local modules
from max_mcp.connector.max_connection import MaxConnection
from max_mcp.python2_compat import (
    transpile_python2_source, transpile_user_python2_source,
)
from max_mcp.OperationManager import OperationsManager
from max_mcp.log import LogManager, log_file

logger = LogManager.get_logger('3dsMaxMCPServer', __file__, log_file)

__version__ = "0.2.0"  # 注意：修改版本号时需同步更新 pyproject.toml 和 __init__.py

_operation_manager = None


class OperationFactory:
    """操作工厂"""

    @classmethod
    def get_operation_manager(cls, engine: str):
        """获取操作管理器"""
        tool_directory = os.path.abspath(
            os.path.join(os.path.dirname(__file__), f"{engine}_tools").replace("\\", "/")
        )
        manager = OperationsManager(tool_directory)
        manager.find_tools()
        return manager


async def run(server: Server, server_name: str):
    """启动 MCP Server 并在 stdio 通道上提供服务。"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=server_name,
                server_version=__version__,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                ),
            )
        )


def convert_to_content(result: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """将结果统一转换为 MCP 需要的内容对象列表。"""
    if result is None:
        return []

    if isinstance(result, TextContent | ImageContent | EmbeddedResource):
        return [result]

    if isinstance(result, Image):
        return [result.to_image_content()]

    if isinstance(result, list | tuple):
        return list(chain.from_iterable(convert_to_content(item) for item in result))

    if not isinstance(result, str):
        try:
            result = json.dumps(pydantic_core.to_jsonable_python(result))
        except Exception:
            result = str(result)
    return [TextContent(type="text", text=result)]


def wrap_script_in_scoped_function(python_script: str, max_tool_name: str, args: List[str]) -> str:
    """将脚本包装为带有异常捕获与 JSON 结果处理的作用域函数。"""
    spaced_python_script = '    ' + python_script.replace('\n', '\n    ')
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../")).replace("\\", "/")
    return f"""
def _add_root_dir_to_env():
    import sys
    import os
    if "{root_dir}" not in sys.path:
        sys.path.append("{root_dir}")
def _mcp_max_scope({','.join(args)}):
    import json
    import traceback
    from pprint import pprint
    _add_root_dir_to_env()
    try:
        _mcp_text_type = unicode
        _mcp_byte_type = str
        _mcp_string_types = (str, unicode)
    except NameError:
        _mcp_text_type = str
        _mcp_byte_type = bytes
        _mcp_string_types = (str,)

    def _mcp_decode_bytes(value):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return value.decode("mbcs")
            except (LookupError, UnicodeDecodeError):
                return value.decode("utf-8", "replace")

    def _mcp_to_text(value):
        if isinstance(value, _mcp_text_type):
            return value
        if isinstance(value, _mcp_byte_type):
            return _mcp_decode_bytes(value)
        return value

    def _mcp_text(value):
        value = _mcp_to_text(value)
        try:
            return _mcp_text_type(value)
        except UnicodeDecodeError:
            raw_value = value if isinstance(value, _mcp_byte_type) else str(value)
            return _mcp_decode_bytes(raw_value)

    def _mcp_fstring(template, *values):
        template = _mcp_to_text(template)
        values = tuple(_mcp_to_text(value) for value in values)
        return template.format(*values)

    def _mcp_ascii(value):
        return _mcp_text(value).encode("ascii", "backslashreplace").decode("ascii")
{spaced_python_script}
    try:
        results = {max_tool_name}({','.join([a + '=' + a for a in args])})
    except Exception as e:
        # print exception to the 3ds Max console
        traceback.print_exc()
        results = dict([('success', False), ('message', 'Error: 3ds Max tool failed with the follow message: ' + str(e))])

    if results and not isinstance(results, _mcp_string_types):
        try:
            results = json.dumps(results)
        except Exception as e:
            print("3dsMaxMCP: Error attempting to return results from tool {max_tool_name} as JSON")
            pprint(results)
            # unable to parse results as JSON, just return it
            return str(results)
    return results
"""


def _serialize_python_argument(value, target_python_major=None):
    """Serialize JSON-like MCP arguments as safe Python source literals."""
    if target_python_major != 2:
        return repr(value)
    if value is None or isinstance(value, (bool, int, float)):
        return repr(value)
    if isinstance(value, str):
        return "u" + json.dumps(value, ensure_ascii=True)
    if isinstance(value, list):
        return "[" + ", ".join(
            _serialize_python_argument(item, 2) for item in value
        ) + "]"
    if isinstance(value, tuple):
        items = [_serialize_python_argument(item, 2) for item in value]
        suffix = "," if len(items) == 1 else ""
        return "(" + ", ".join(items) + suffix + ")"
    if isinstance(value, dict):
        pairs = [
            "%s: %s" % (
                _serialize_python_argument(key, 2),
                _serialize_python_argument(item, 2),
            )
            for key, item in value.items()
        ]
        return "{" + ", ".join(pairs) + "}"
    return repr(value)


def load_max_tool_source(
    max_tool_name: str,
    filename: str,
    args: Dict[str, List[str]] = None,
    *,
    target_python_major: int = None,
    log: bool = False,
) -> str:
    """Read a tool and generate a Max-side script for its Python version."""
    with open(filename, "r", encoding="utf-8") as f:
        script = f.read()
    args = dict(args or {})
    if target_python_major == 2:
        script = transpile_python2_source(script, filename)
        if max_tool_name == "execute_python_script":
            user_script = args.get("script")
            if isinstance(user_script, str):
                args["script"] = transpile_user_python2_source(user_script)

    results = wrap_script_in_scoped_function(script, max_tool_name, args.keys())
    results += "\n_mcp_max_results = _mcp_max_scope("
    params = []
    for key, value in args.items():
        params.append(
            "%s=%s" % (
                key,
                _serialize_python_argument(value, target_python_major),
            )
        )
    results += ", ".join(params)
    results += ")\n\n"

    if log:
        logger.debug(results)
    return results


def main():
    """MCP Server 入口函数，供 uvx / 命令行 / python -m max_mcp 调用。"""
    server_name = "3dsMaxMCP"
    _operation_manager = OperationFactory.get_operation_manager("max")
    server = Server(server_name)

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """响应客户端的工具列表请求。"""
        logger.info("Requesting a list of tools.")
        return _operation_manager.get_tools()

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        """处理 MCP 客户端调用工具的请求并返回结果。"""

        logger.info(f"Calling tool {name} with arguments: {pformat(arguments)}")

        path = _operation_manager.get_file_path(name)
        if not path:
            error_msg = f"Tool {name} not found."
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        try:
            max_conn = MaxConnection()
            python_major = max_conn.get_python_major_version()
            python_script = load_max_tool_source(
                name, path, arguments, target_python_major=python_major
            )
            results = max_conn.run_python_script(python_script)
            converted_results = convert_to_content(results)
        except Exception as e:
            error_msg = f"Error: tool {name} failed to run. Path{path} Reason {e}\n traceback:{traceback.format_exc()}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        if converted_results:
            return converted_results
        return {"success": True}

    asyncio.run(run(server, server_name))


if __name__ == '__main__':
    main()
