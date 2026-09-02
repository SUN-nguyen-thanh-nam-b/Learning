"""Launcher. Kept at the repo root so PyInstaller has a plain script entry."""

import sys

from app.main import main

if __name__ == "__main__":
    sys.exit(main())
