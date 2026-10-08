"""Install the 3ds Max 2023/2025 menu for the current Windows user.

The external Codex/Claude MCP process still runs from this repository. The
installed Autodesk bundle contains only the in-Max bridge and menu actions.
"""

import argparse
import os
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BUNDLE_SOURCE = ROOT / "bundle"
BUNDLE_NAME = "3dsMaxMCP.bundle"


def bundle_destination():
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not set; this installer requires Windows")
    parent = (Path(appdata) / "Autodesk" / "ApplicationPlugins").resolve()
    destination = (parent / BUNDLE_NAME).resolve()
    if destination.parent != parent:
        raise RuntimeError("Bundle path escapes the Autodesk ApplicationPlugins directory")
    return destination


def _is_our_bundle(destination):
    manifest = destination / "PackageContents.xml"
    if not manifest.is_file():
        return False
    try:
        return ET.parse(manifest).getroot().attrib.get("Name") == "3dsMaxMCP"
    except ET.ParseError:
        return False


def install():
    destination = bundle_destination()
    if destination.exists() and not _is_our_bundle(destination):
        raise RuntimeError("Refusing to overwrite an unrelated bundle: %s" % destination)

    for source in BUNDLE_SOURCE.rglob("*"):
        if source.is_file():
            target = destination / source.relative_to(BUNDLE_SOURCE)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    python_root = destination / "Contents" / "python" / "max_mcp"
    for source in (ROOT / "max_mcp").rglob("*.py"):
        target = python_root / source.relative_to(ROOT / "max_mcp")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    if not _is_our_bundle(destination):
        raise RuntimeError("Installed bundle failed manifest validation")
    print("Installed 3dsMaxMCP menu: %s" % destination)
    print("Restart 3ds Max 2023 or 2025 to load the top menu.")
    return destination


def uninstall():
    destination = bundle_destination()
    if not destination.exists():
        print("3dsMaxMCP menu is not installed")
        return
    if not _is_our_bundle(destination):
        raise RuntimeError("Refusing to delete an unrecognized bundle: %s" % destination)
    # The resolved path was checked to be a direct child of ApplicationPlugins.
    shutil.rmtree(destination)
    print("Removed 3dsMaxMCP menu: %s" % destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    try:
        uninstall() if args.uninstall else install()
    except (OSError, RuntimeError) as exc:
        print("Installation failed: %s" % exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
