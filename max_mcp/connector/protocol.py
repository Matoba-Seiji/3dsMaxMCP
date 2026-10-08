"""Wire protocol shared by the external MCP server and the in-Max listener.

The greeting is sent before any executable payload. A client connected to a
different DCC therefore cannot send Python code to that process accidentally.
"""

import socket
import struct


HOST = "127.0.0.1"
PORT = 50012
SERVER_HELLO = b"3DSMAXMCP/1\n"
CLIENT_HELLO = b"3DSMAXMCP-CLIENT/1\n"
HANDSHAKE_TIMEOUT = 3.0
MAX_MESSAGE_SIZE = 8 * 1024 * 1024


def recv_exact(connection, length):
    data = bytearray()
    while len(data) < length:
        chunk = connection.recv(length - len(data))
        if not chunk:
            raise ConnectionError("Socket closed before the message was complete")
        data.extend(chunk)
    return bytes(data)


def read_frame(connection):
    length = struct.unpack(">I", recv_exact(connection, 4))[0]
    if length > MAX_MESSAGE_SIZE:
        raise ValueError("MCP message exceeds the maximum allowed size")
    return recv_exact(connection, length).decode("utf-8")


def write_frame(connection, message):
    payload = message.encode("utf-8")
    if len(payload) > MAX_MESSAGE_SIZE:
        raise ValueError("MCP message exceeds the maximum allowed size")
    connection.sendall(struct.pack(">I", len(payload)) + payload)


def connect_to_max(host=HOST, port=PORT, timeout=HANDSHAKE_TIMEOUT):
    """Connect only if the peer identifies itself as this Max listener."""
    connection = socket.create_connection((host, port), timeout=timeout)
    try:
        greeting = recv_exact(connection, len(SERVER_HELLO))
        if greeting != SERVER_HELLO:
            raise ConnectionError(
                "The process listening on %s:%s is not 3dsMaxMCP; "
                "Python was not sent." % (host, port)
            )
        connection.sendall(CLIENT_HELLO)
        return connection
    except Exception:
        connection.close()
        raise
