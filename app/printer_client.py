"""Thin wrapper around the TiMini-Print command-line binary.

TiMini-Print (Apache-2.0, https://github.com/Dejniel/TiMini-Print) already
speaks the PD-01's proprietary v5g BLE protocol, so this app shells out to it
rather than reimplementing the wire format.
"""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path


class PrinterError(RuntimeError):
    """Raised when the printer binary is missing, fails, or hangs."""


class PrinterClient:
    def __init__(
        self,
        exe_path: Path,
        bluetooth_name: str = "",
        darkness: str = "",
        extra_args: str = "",
        timeout: float = 120.0,
        preserve_margins: bool = False,
    ) -> None:
        self._exe = exe_path
        self._bluetooth = bluetooth_name
        self._darkness = darkness
        self._extra = shlex.split(extra_args) if extra_args else []
        self._timeout = timeout
        self._preserve_margins = preserve_margins

    def _base_cmd(self) -> list[str]:
        if not self._exe.exists():
            raise PrinterError(
                f"TiMini-Print CLI not found at {self._exe}. Download it from "
                "https://github.com/Dejniel/TiMini-Print/releases and set "
                "[printer] exe_path in config.ini."
            )
        return [str(self._exe)]

    def scan(self) -> str:
        """List Bluetooth printers the CLI can see."""
        return self._run(self._base_cmd() + ["--scan"])

    def print_image(self, image_path: Path) -> str:
        cmd = self._base_cmd()
        if self._bluetooth:
            cmd += ["--bluetooth", self._bluetooth]
        if self._darkness:
            cmd += ["--darkness", self._darkness]
        if self._preserve_margins:
            # Without this the CLI crops the white padding that makes a
            # scaled-down avatar smaller, then rescales back to full width.
            cmd.append("--no-trim-side-margins")
        cmd += self._extra
        cmd.append(str(image_path))
        return self._run(cmd)

    def _run(self, cmd: list[str]) -> str:
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self._timeout
            )
        except subprocess.TimeoutExpired as exc:
            raise PrinterError(
                f"printer did not respond within {self._timeout:.0f}s"
            ) from exc

        output = f"{proc.stdout or ''}{proc.stderr or ''}".strip()
        if proc.returncode != 0:
            raise PrinterError(f"exit code {proc.returncode}: {output[:400]}")
        return output
