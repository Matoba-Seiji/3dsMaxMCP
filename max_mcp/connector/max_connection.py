#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Date      2026/1/4 11:02
# Usage     : 3ds Max Socket 通信层
# Version   : 2.0
# Comment   : 适配 3ds Max 的 Socket 通信协议，直接发送 Python 代码执行


# Import built-in modules
import socket
import json
from enum import Enum

from max_mcp.connector.protocol import (
    HOST, PORT, connect_to_max, read_frame, write_frame,
)

# Import third-party modules

# Import local modules
from max_mcp.log import LogManager, log_file

logger = LogManager.get_logger('3dsMaxMCPServer', __file__, log_file)

# ============================================================
# 通信协议说明
# ============================================================
# 客户端（MCP Server）与 3ds Max 内的 Socket Server 通过 TCP 通信。
#
# 连接后先验证服务端身份，再发送客户端身份标记。
# 随后的请求格式为:
#   [4字节 大端序 uint32: 消息体长度] + [UTF-8编码的Python脚本]
#
# 接收协议:
#   [4字节 大端序 uint32: 消息体长度] + [UTF-8编码的JSON结果字符串]
#
# 3ds Max 端需要运行一个配套的 Socket Server 脚本来接收并执行命令。
# 参见 max_server_listener.py
# ============================================================

SOCKET_TIMEOUT = 130  # Includes the listener execution timeout.


def _update_script_to_capture_stdout(python_script: str) -> str:
    """将脚本包裹在 stdout 捕获上下文中，便于收集打印输出。"""
    spaced_python_script = '    ' + python_script.replace('\n', '\n    ')
    return f"""
import io
import contextlib
_mcp_io_buf = io.StringIO()
with contextlib.redirect_stdout(_mcp_io_buf):
{spaced_python_script}
_mcp_max_results = _mcp_io_buf.getvalue()
"""


class ScriptReturn(Enum):
    """脚本返回值类型枚举"""
    STDOUT = "stdout"   # 捕获 stdout 输出作为结果
    JSON = "json"       # 将结果解析为 JSON
    NONE = "none"       # 不关心返回值


class MaxConnection(object):
    """3ds Max Socket 通信连接器。

    通过 TCP Socket 连接到 3ds Max 内运行的 Python Socket Server，
    发送 Python 脚本并接收执行结果。

    3ds Max 端需要预先运行 max_server_listener.py 监听脚本。

    Attributes:
        _host: 连接地址，默认 127.0.0.1
        _port: 连接端口，默认 50012
    """

    def __init__(self, host: str = HOST, port: int = PORT):
        super(MaxConnection, self).__init__()
        self._host = host
        self._port = port

    def _send_python_command(self, python_script: str) -> str:
        """通过 Socket 将 Python 脚本发送给 3ds Max，并读取返回结果。

        使用带长度头的协议确保数据完整传输：
        1. 建立 TCP 连接
        2. 校验 3dsMaxMCP 身份标记
        3. 发送 [长度头 + Python脚本]，接收执行结果
        4. 关闭连接

        Args:
            python_script: 要在 3ds Max 中执行的 Python 脚本

        Returns:
            3ds Max 返回的结果字符串

        Raises:
            ConnectionRefusedError: 无法连接到 3ds Max（可能未启动监听）
            ConnectionError: 通信过程中连接断开
            socket.timeout: 等待响应超时
        """
        client = None
        try:
            # The Max listener identifies itself before we send executable code.
            # A Maya process occupying the port receives no Python payload.
            client = connect_to_max(self._host, self._port)
            client.settimeout(SOCKET_TIMEOUT)
            logger.debug(f"已连接到 3ds Max ({self._host}:{self._port})")

            write_frame(client, python_script)
            logger.debug(f"已发送脚本，长度: {len(python_script)} 字符")

            result = read_frame(client)
            logger.debug(f"收到结果，长度: {len(result)} 字符")

            return result

        except ConnectionRefusedError:
            error_msg = (
                f"无法连接到 3ds Max ({self._host}:{self._port})。"
                f"请确保 3ds Max 已启动，且 max_server_listener.py 监听脚本正在运行。"
            )
            logger.error(error_msg)
            raise ConnectionRefusedError(error_msg)

        except socket.timeout:
            if client is None:
                error_msg = (f"{self._host}:{self._port} 未返回 3dsMaxMCP 身份标记；"
                             "端口可能属于其他程序，Python 脚本未发送。")
            else:
                error_msg = f"等待 3ds Max 执行结果超时（{SOCKET_TIMEOUT}秒）。"
            logger.error(error_msg)
            raise TimeoutError(error_msg)

        except Exception as e:
            logger.error(f"与 3ds Max 通信出错: {e}")
            raise

        finally:
            if client is not None:
                client.close()

    def run_python_script(self, python_script: str, *, returns: ScriptReturn = ScriptReturn.JSON):
        """执行 Python 脚本并按指定返回类型处理结果。

        根据 returns 参数决定如何处理脚本和返回值：
        - JSON: 在脚本中初始化 _mcp_max_results 变量，将结果解析为 JSON
        - STDOUT: 包裹 stdout 捕获逻辑，返回打印输出
        - NONE: 直接执行，不处理返回值

        Args:
            python_script: 要执行的 Python 脚本
            returns: 返回值类型，默认为 JSON

        Returns:
            根据 returns 类型返回:
            - JSON: 解析后的 Python 对象（dict/list等）
            - STDOUT: stdout 输出字符串
            - NONE: 原始结果字符串
        """
        if returns == ScriptReturn.STDOUT:
            python_script = _update_script_to_capture_stdout(python_script)
        elif returns == ScriptReturn.JSON:
            python_script = "_mcp_max_results = None\n" + python_script

        result = self._send_python_command(python_script)
        logger.debug(f"send_python_command result: {result[:500] if result else result}")

        # 清理结果字符串中的多余字符
        if result:
            result = result.strip()

        # 按返回类型解析结果
        if returns != ScriptReturn.NONE and result:
            try:
                result = json.loads(result)
            except (json.JSONDecodeError, TypeError):
                # 无法解析为 JSON，按原样返回
                logger.debug(f"结果无法解析为 JSON，按原样返回: {result[:200] if result else result}")

        return result
