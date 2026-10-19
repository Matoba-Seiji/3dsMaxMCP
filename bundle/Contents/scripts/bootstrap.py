"""Load the installed Max MCP package into 3ds Max's Python interpreter."""

import os
import sys


contents_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
package_root = os.path.join(contents_dir, "python")
package_root_text = os.path.abspath(package_root)
if package_root_text not in sys.path:
    sys.path.insert(0, package_root_text)
