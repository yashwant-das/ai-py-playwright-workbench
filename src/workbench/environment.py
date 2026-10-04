"""Checks for the external tools the workbench depends on."""

import shutil


def node_available() -> bool:
    """True when Node.js is on the PATH (needed for the ts-morph AST repair)."""
    return shutil.which("node") is not None
