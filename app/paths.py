"""Path resolution that survives PyInstaller's one-file bundling.

In a frozen build ``__file__`` points inside a temporary extraction directory
that is deleted on exit, so config files and output folders must be resolved
against the executable's own directory instead.
"""

from __future__ import annotations

import sys
from pathlib import Path


def app_dir() -> Path:
    """Directory the user actually keeps the app in."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resolve(value: str) -> Path:
    """Turn a config value into an absolute path, relative to :func:`app_dir`."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else app_dir() / path
