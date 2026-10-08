"""Manual startup entry point used by startup_mcp_listener.ms."""

import pathlib
import sys


repository_root = pathlib.Path(__file__).resolve().parents[2]
root_text = str(repository_root)
if root_text not in sys.path:
    sys.path.insert(0, root_text)

from max_mcp.ui import service

service.start()
