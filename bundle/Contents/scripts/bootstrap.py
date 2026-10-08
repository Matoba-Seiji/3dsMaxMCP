"""Load the installed Max MCP package into 3ds Max's Python interpreter."""

import pathlib
import sys


package_root = pathlib.Path(__file__).resolve().parents[1] / "python"
package_root_text = str(package_root)
if package_root_text not in sys.path:
    sys.path.insert(0, package_root_text)
