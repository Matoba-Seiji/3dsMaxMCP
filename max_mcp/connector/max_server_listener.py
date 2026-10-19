#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""3ds Max 内部 Socket Server 监听脚本（兼容 Max 2020 Python 2.7）。"""

import json
import socket
import threading
import traceback

try:
    import Queue as queue
except ImportError:
    import queue

from max_mcp.connector.protocol import (
    CLIENT_HELLO, HANDSHAKE_TIMEOUT, HOST as DEFAULT_HOST,
    PORT as DEFAULT_PORT, SERVER_HELLO, ConnectionError as SocketConnectionError,
    read_frame, recv_exact, write_frame,
)

HOST = DEFAULT_HOST
PORT = DEFAULT_PORT
TIMER_INTERVAL_MS = 50
TASK_TIMEOUT = 120

_server_running = False
_server_thread = None
_server_socket = None
_task_queue = queue.Queue()
_timer = None
_exec_globals = {}
_use_main_thread = False

try:
    _TEXT_TYPE = unicode
    _STRING_TYPES = (str, unicode)
    _BYTE_TYPE = str
except NameError:
    _TEXT_TYPE = str
    _STRING_TYPES = (str,)
    _BYTE_TYPE = bytes


def _source_bytes(source):
    if isinstance(source, _TEXT_TYPE):
        source = source.encode("utf-8")
    elif not isinstance(source, _BYTE_TYPE):
        source = _TEXT_TYPE(source).encode("utf-8")
    return b"# -*- coding: utf-8 -*-\n" + source


def _force_refresh_viewport():
    """刷新视口与 Qt 事件队列。"""
    try:
        from pymxs import runtime as rt
        rt.forceCompleteRedraw()
    except Exception:
        pass
    try:
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            from PySide2.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.processEvents()
    except Exception:
        pass


def _execute_python(script):
    """在 Max 主线程中执行代码并返回 JSON 兼容结果。"""
    global _exec_globals
    try:
        _exec_globals.pop("_mcp_max_results", None)
        compiled = compile(_source_bytes(script), "<3dsMaxMCP>", "exec")
        eval(compiled, _exec_globals, _exec_globals)
        _force_refresh_viewport()
        result = _exec_globals.get("_mcp_max_results")
        if result is None:
            return ""
        if isinstance(result, _STRING_TYPES):
            return result
        try:
            return json.dumps(result, ensure_ascii=False)
        except (TypeError, ValueError):
            return _TEXT_TYPE(result)
    except Exception as exc:
        traceback.print_exc()
        error_result = {
            "success": False,
            "message": "3ds Max 执行脚本出错: %s" % exc,
            "traceback": traceback.format_exc(),
        }
        return json.dumps(error_result, ensure_ascii=False)


def _main_thread_poll():
    """将接收线程投递的请求放到 Max 主线程执行。"""
    try:
        while not _task_queue.empty():
            try:
                script, result_event, result_holder = _task_queue.get_nowait()
            except queue.Empty:
                break
            print("[3dsMaxMCP] 主线程正在执行脚本 (%s 字符)..." % len(script))
            result = _execute_python(script)
            result_holder.append(result)
            result_event.set()
            print("[3dsMaxMCP] 主线程执行完成，结果 (%s 字符)" % len(result))
    except Exception as exc:
        print("[3dsMaxMCP] 主线程轮询出错: %s" % exc)
        traceback.print_exc()


def _start_main_thread_timer():
    """在 Max UI 主线程启动 QTimer 轮询队列。"""
    global _timer
    try:
        try:
            from PySide6.QtCore import QTimer
        except ImportError:
            from PySide2.QtCore import QTimer
        _timer = QTimer()
        _timer.setInterval(TIMER_INTERVAL_MS)
        _timer.timeout.connect(_main_thread_poll)
        _timer.start()
        print("[3dsMaxMCP] 主线程定时器已启动 (间隔 %sms)" % TIMER_INTERVAL_MS)
        return True
    except Exception as exc:
        print("[3dsMaxMCP] 警告: 无法导入 PySide2/pymxs (%s)" % exc)
        print("[3dsMaxMCP] 不会在非 3ds Max 进程执行脚本")
        return False


def _stop_main_thread_timer():
    global _timer
    if _timer is not None:
        try:
            _timer.stop()
            _timer.deleteLater()
        except Exception:
            pass
        _timer = None
        print("[3dsMaxMCP] 主线程定时器已停止")


def _handle_client(conn, addr):
    try:
        print("[3dsMaxMCP] 客户端已连接: %s" % (addr,))
        conn.settimeout(HANDSHAKE_TIMEOUT)
        conn.sendall(SERVER_HELLO)
        if recv_exact(conn, len(CLIENT_HELLO)) != CLIENT_HELLO:
            print("[3dsMaxMCP] 已拒绝非 3dsMaxMCP 客户端: %s" % (addr,))
            return
        conn.settimeout(TASK_TIMEOUT + 10)
        script = read_frame(conn)
        if not script:
            print("[3dsMaxMCP] 收到空脚本，跳过")
            write_frame(conn, "")
            return

        print("[3dsMaxMCP] 收到脚本 (%s 字符)" % len(script))
        result_event = threading.Event()
        result_holder = []
        _task_queue.put((script, result_event, result_holder))
        print("[3dsMaxMCP] 已投递到主线程队列，等待执行...")
        if result_event.wait(timeout=TASK_TIMEOUT):
            result = result_holder[0] if result_holder else ""
        else:
            result = json.dumps({
                "success": False,
                "message": "主线程执行超时 (%s秒)" % TASK_TIMEOUT,
            }, ensure_ascii=False)
            print("[3dsMaxMCP] 警告: 主线程执行超时!")
        write_frame(conn, result)
        print("[3dsMaxMCP] 结果已发送 (%s 字符)" % len(result))
    except SocketConnectionError as exc:
        print("[3dsMaxMCP] 连接错误: %s" % exc)
    except Exception as exc:
        print("[3dsMaxMCP] 处理请求出错: %s" % exc)
        traceback.print_exc()
        try:
            write_frame(conn, json.dumps({
                "success": False,
                "message": "服务端处理出错: %s" % exc,
            }, ensure_ascii=False))
        except Exception:
            pass
    finally:
        conn.close()


def _server_loop(server_socket):
    global _server_running, _server_socket
    try:
        while _server_running:
            try:
                conn, addr = server_socket.accept()
                client_thread = threading.Thread(
                    target=_handle_client, args=(conn, addr)
                )
                client_thread.daemon = True
                client_thread.start()
            except socket.timeout:
                continue
            except socket.error:
                break
    except Exception as exc:
        print("[3dsMaxMCP] 服务器错误: %s" % exc)
        traceback.print_exc()
    finally:
        try:
            server_socket.close()
        except Exception:
            pass
        if _server_socket is server_socket:
            _server_socket = None
            _server_running = False
        print("[3dsMaxMCP] Socket Server 已停止")


def is_running():
    if not (_server_running and _server_socket and _server_thread):
        return False
    alive = getattr(_server_thread, "is_alive", None)
    if alive is None:
        alive = _server_thread.isAlive
    return bool(alive())


def start_mcp_server(host=HOST, port=PORT):
    """启动主线程定时器和 TCP Socket Server。"""
    global _server_running, _server_thread, _server_socket
    global _use_main_thread, HOST, PORT
    if is_running():
        print("[3dsMaxMCP] 服务器已在运行中")
        return True
    if _server_running:
        stop_mcp_server()

    HOST = host
    PORT = port
    _use_main_thread = _start_main_thread_timer()
    if not _use_main_thread:
        return False

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            server_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1
            )
        server_socket.bind((host, port))
        server_socket.listen(5)
        server_socket.settimeout(0.5)
        _server_socket = server_socket
        _server_running = True
        _server_thread = threading.Thread(
            target=_server_loop, args=(server_socket,)
        )
        _server_thread.daemon = True
        _server_thread.start()
        print("[3dsMaxMCP] 已启动，监听 %s:%s" % (host, port))
        return True
    except Exception as exc:
        server_socket.close()
        _server_socket = None
        _server_running = False
        _stop_main_thread_timer()
        print("[3dsMaxMCP] 启动失败：无法监听 %s:%s (%s)" % (host, port, exc))
        return False


def stop_mcp_server():
    """停止监听器并清理等待中的任务。"""
    global _server_running, _server_thread, _server_socket, _use_main_thread
    if not _server_running:
        print("[3dsMaxMCP] 服务器未在运行")
        return True

    _server_running = False
    _use_main_thread = False
    _stop_main_thread_timer()
    if _server_socket:
        try:
            _server_socket.close()
        except Exception:
            pass
        _server_socket = None
    if _server_thread:
        _server_thread.join(timeout=5)
        _server_thread = None

    while not _task_queue.empty():
        try:
            unused_script, event, unused_holder = _task_queue.get_nowait()
            event.set()
        except queue.Empty:
            break
    print("[3dsMaxMCP] 服务器已停止")
    return True


def restart_mcp_server(host=HOST, port=PORT):
    stop_mcp_server()
    return start_mcp_server(host, port)


if __name__ == "__main__":
    start_mcp_server()
