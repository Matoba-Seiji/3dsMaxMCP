#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""3ds Max 内部 Socket Server 监听脚本 (主线程执行版)。

此脚本需要在 3ds Max 内部运行（通过 MAXScript 的 python.ExecuteFile 或
Scripting > Run Script 菜单加载）。

启动后会在后台监听 TCP 端口（默认 50012），接收来自 MCP Server 的 Python 脚本。
脚本通过队列调度到 3ds Max **主线程**执行（保证 pymxs 可用），执行完成后将结果返回。

架构:
    后台线程 (Socket Server)          主线程 (QTimer 轮询)
    ┌─────────────────────┐         ┌─────────────────────┐
    │ 接收客户端脚本       │  ──→   │ 从 _task_queue 取任务│
    │ 放入 _task_queue     │         │ exec() 执行脚本     │
    │ 等待 _result_event   │  ←──   │ 结果放入 _result_queue│
    │ 取出结果并回复客户端  │         │                     │
    └─────────────────────┘         └─────────────────────┘

通信协议:
    请求: [4字节大端序uint32: 消息体长度] + [UTF-8编码的Python脚本]
    响应: [4字节大端序uint32: 消息体长度] + [UTF-8编码的结果字符串]

用法:
    方式1 - 在 3ds Max 的 MAXScript Listener 中执行:
        python.ExecuteFile @"E:\\DCC_MCP\\3dsmax_mcp\\core\\connector\\max_server_listener.py"

    方式2 - 在 3ds Max 菜单中:
        Scripting > Run Script > 选择此文件

停止:
    在 3ds Max Python 控制台中执行:
        stop_mcp_server()
"""

import socket
import threading
import traceback
import json
import queue

from max_mcp.connector.protocol import (
    CLIENT_HELLO, HANDSHAKE_TIMEOUT, HOST as DEFAULT_HOST,
    PORT as DEFAULT_PORT, SERVER_HELLO, read_frame, recv_exact, write_frame,
)

# ============================================================
# 配置
# ============================================================
HOST = DEFAULT_HOST
PORT = DEFAULT_PORT
TIMER_INTERVAL_MS = 50  # 主线程轮询间隔(毫秒)
TASK_TIMEOUT = 120       # 等待主线程执行结果的超时时间(秒)

# ============================================================
# 全局变量
# ============================================================
_server_running = False
_server_thread = None
_server_socket = None

# 任务队列: 后台线程 -> 主线程
# 元素格式: (script: str, result_event: threading.Event, result_holder: list)
_task_queue = queue.Queue()

# 主线程轮询定时器
_timer = None

# 全局执行上下文：跨请求保持变量状态
_exec_globals = {}


# ============================================================
# 通信协议
# ============================================================
# ============================================================
# 视口刷新
# ============================================================
def _force_refresh_viewport():
    """强制刷新 3ds Max 视口和界面。

    工具脚本执行完毕后调用，确保视口和 UI 能及时更新，
    不需要用户手动点击 Max 窗口才刷新。
    """
    try:
        from pymxs import runtime as rt

        # 1. 强制完整重绘视口（最彻底的刷新方式）
        rt.forceCompleteRedraw()

    except Exception:
        # 刷新失败不影响工具执行结果，静默忽略
        pass

    try:
        # 2. 处理 Qt 事件队列，确保 UI 控件也刷新
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            from PySide2.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.processEvents()
    except Exception:
        pass


# ============================================================
# 脚本执行 (在主线程中调用)
# ============================================================
def _execute_python(script: str) -> str:
    """在 3ds Max 主线程的 Python 环境中执行脚本并返回结果。

    脚本中如果设置了 _mcp_max_results 变量，则以该变量值作为返回结果。
    否则返回空字符串。

    Args:
        script: 要执行的 Python 脚本

    Returns:
        执行结果的字符串
    """
    global _exec_globals

    try:
        # 清除上次结果
        _exec_globals.pop('_mcp_max_results', None)

        exec(script, _exec_globals)

        # 强制刷新 3ds Max 视口和界面
        _force_refresh_viewport()

        result = _exec_globals.get('_mcp_max_results', None)

        if result is None:
            return ''
        elif isinstance(result, str):
            return result
        else:
            try:
                return json.dumps(result, ensure_ascii=False)
            except (TypeError, ValueError):
                return str(result)

    except Exception as e:
        traceback.print_exc()
        error_result = {
            'success': False,
            'message': f'3ds Max 执行脚本出错: {str(e)}',
            'traceback': traceback.format_exc()
        }
        return json.dumps(error_result, ensure_ascii=False)


# ============================================================
# 主线程定时器回调
# ============================================================
def _main_thread_poll():
    """主线程定时器回调函数。

    从 _task_queue 中取出待执行的脚本，在主线程中执行，
    将结果放入 result_holder 并通知后台线程。
    """
    try:
        while not _task_queue.empty():
            try:
                script, result_event, result_holder = _task_queue.get_nowait()
            except queue.Empty:
                break

            print(f"[3dsMaxMCP] 主线程正在执行脚本 ({len(script)} 字符)...")

            # 在主线程中执行脚本 (pymxs 可用)
            result = _execute_python(script)

            # 将结果传回后台线程
            result_holder.append(result)
            result_event.set()

            print(f"[3dsMaxMCP] 主线程执行完成，结果 ({len(result)} 字符)")
    except Exception as e:
        print(f"[3dsMaxMCP] 主线程轮询出错: {e}")
        traceback.print_exc()


def _start_main_thread_timer():
    """启动主线程轮询定时器。

    使用 3ds Max 的 QTimer 来在主线程上定时轮询任务队列。
    """
    global _timer

    try:
        from pymxs import runtime as rt

        # 使用 Qt 的 QTimer 实现主线程定时回调
        try:
            from PySide6.QtCore import QTimer
        except ImportError:
            from PySide2.QtCore import QTimer

        _timer = QTimer()
        _timer.setInterval(TIMER_INTERVAL_MS)
        _timer.timeout.connect(_main_thread_poll)
        _timer.start()

        print(f"[3dsMaxMCP] 主线程定时器已启动 (间隔 {TIMER_INTERVAL_MS}ms)")
        return True

    except Exception as e:
        print(f"[3dsMaxMCP] 警告: 无法导入 PySide2/pymxs ({e})")
        print("[3dsMaxMCP] 不会在非 3ds Max 进程执行脚本")
        return False


def _stop_main_thread_timer():
    """停止主线程轮询定时器。"""
    global _timer

    if _timer is not None:
        try:
            _timer.stop()
            _timer.deleteLater()
        except Exception:
            pass
        _timer = None
        print("[3dsMaxMCP] 主线程定时器已停止")


# ============================================================
# 后台线程: Socket Server
# ============================================================
_use_main_thread = False  # 是否使用主线程执行


def _handle_client(conn: socket.socket, addr: tuple):
    """处理单个客户端连接。

    如果主线程定时器可用，将脚本投递到队列等待主线程执行；
    否则直接在当前线程执行（pymxs 不可用）。

    Args:
        conn: 客户端 Socket
        addr: 客户端地址
    """
    try:
        print(f"[3dsMaxMCP] 客户端已连接: {addr}")

        # Send identity before accepting executable code. Maya's listener does
        # not send this greeting, so our client cannot send scripts to Maya.
        conn.settimeout(HANDSHAKE_TIMEOUT)
        conn.sendall(SERVER_HELLO)
        if recv_exact(conn, len(CLIENT_HELLO)) != CLIENT_HELLO:
            print(f"[3dsMaxMCP] 已拒绝非 3dsMaxMCP 客户端: {addr}")
            return
        conn.settimeout(TASK_TIMEOUT + 10)
        script = read_frame(conn)
        if not script:
            print(f"[3dsMaxMCP] 收到空脚本，跳过")
            write_frame(conn, '')
            return

        print(f"[3dsMaxMCP] 收到脚本 ({len(script)} 字符)")

        result_event = threading.Event()
        result_holder = []
        _task_queue.put((script, result_event, result_holder))
        print("[3dsMaxMCP] 已投递到主线程队列，等待执行...")
        if result_event.wait(timeout=TASK_TIMEOUT):
            result = result_holder[0] if result_holder else ''
        else:
            result = json.dumps({
                'success': False,
                'message': f'主线程执行超时 ({TASK_TIMEOUT}秒)'
            }, ensure_ascii=False)
            print("[3dsMaxMCP] 警告: 主线程执行超时!")

        # 发送结果
        write_frame(conn, result)
        print(f"[3dsMaxMCP] 结果已发送 ({len(result)} 字符)")

    except ConnectionError as e:
        print(f"[3dsMaxMCP] 连接错误: {e}")
    except Exception as e:
        print(f"[3dsMaxMCP] 处理请求出错: {e}")
        traceback.print_exc()
        try:
            error_msg = json.dumps({
                'success': False,
                'message': f'服务端处理出错: {str(e)}'
            }, ensure_ascii=False)
            write_frame(conn, error_msg)
        except Exception:
            pass
    finally:
        conn.close()


def _server_loop(server_socket):
    """服务器主循环，监听并处理客户端连接。"""
    global _server_running, _server_socket

    try:
        while _server_running:
            try:
                conn, addr = server_socket.accept()
                # 在独立线程中处理客户端连接
                # 脚本执行会被投递到主线程队列
                client_thread = threading.Thread(
                    target=_handle_client,
                    args=(conn, addr),
                    daemon=True
                )
                client_thread.start()
            except socket.timeout:
                continue
            except OSError:
                break

    except Exception as e:
        print(f"[3dsMaxMCP] 服务器错误: {e}")
        traceback.print_exc()
    finally:
        server_socket.close()
        if _server_socket is server_socket:
            _server_socket = None
            _server_running = False
        print("[3dsMaxMCP] Socket Server 已停止")


# ============================================================
# 公共 API
# ============================================================
def is_running():
    """Report this listener's state, rather than merely probing the port."""
    return bool(_server_running and _server_socket and _server_thread and
                _server_thread.is_alive())


def start_mcp_server(host: str = HOST, port: int = PORT):
    """启动 MCP Socket Server。

    1. 启动主线程 QTimer 定时器用于轮询任务队列
    2. 在后台线程中启动 Socket Server

    Args:
        host: 监听地址，默认 127.0.0.1
        port: 监听端口，默认 50012
    """
    global _server_running, _server_thread, _server_socket, _use_main_thread, HOST, PORT

    if is_running():
        print("[3dsMaxMCP] 服务器已在运行中")
        return True
    if _server_running:
        stop_mcp_server()

    HOST = host
    PORT = port

    # Never execute Max scripts from a foreign DCC or a worker thread.
    _use_main_thread = _start_main_thread_timer()
    if not _use_main_thread:
        return False

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        server_socket.bind((host, port))
        server_socket.listen(5)
        server_socket.settimeout(0.5)
        _server_socket = server_socket
        _server_running = True
        _server_thread = threading.Thread(target=_server_loop,
                                          args=(server_socket,), daemon=True)
        _server_thread.start()
        print(f"[3dsMaxMCP] 已启动，监听 {host}:{port}")
        return True
    except Exception as e:
        server_socket.close()
        _server_socket = None
        _server_running = False
        _stop_main_thread_timer()
        print(f"[3dsMaxMCP] 启动失败：无法监听 {host}:{port} ({e})")
        return False


def stop_mcp_server():
    """停止 MCP Socket Server。"""
    global _server_running, _server_thread, _server_socket, _use_main_thread

    if not _server_running:
        print("[3dsMaxMCP] 服务器未在运行")
        return True

    _server_running = False
    _use_main_thread = False

    # 停止主线程定时器
    _stop_main_thread_timer()

    # 关闭 Socket
    if _server_socket:
        try:
            _server_socket.close()
        except Exception:
            pass
        _server_socket = None

    if _server_thread:
        _server_thread.join(timeout=5)
        _server_thread = None

    # 清空任务队列
    while not _task_queue.empty():
        try:
            _, event, _ = _task_queue.get_nowait()
            event.set()  # 唤醒等待中的线程
        except queue.Empty:
            break

    print("[3dsMaxMCP] 服务器已停止")
    return True


def restart_mcp_server(host: str = HOST, port: int = PORT):
    """重启 MCP Socket Server。

    Args:
        host: 监听地址
        port: 监听端口
    """
    stop_mcp_server()
    return start_mcp_server(host, port)


# ============================================================
# 自动启动
# ============================================================
if __name__ == '__main__':
    start_mcp_server()
