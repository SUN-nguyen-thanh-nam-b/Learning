"""Load settings from config.ini."""

from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path

from .paths import app_dir

CONFIG_NAME = "config.ini"


@dataclass(frozen=True)
class Config:
    username: str
    sign_api_key: str
    exe_path: str
    bluetooth_name: str
    darkness: str
    extra_args: str
    width_px: int
    avatar_scale: float
    max_per_minute: int
    queue_max: int
    dedupe: bool
    show_username: bool
    retries: int
    save_dir: str


_DEFAULTS: dict[str, dict[str, str]] = {
    "tiktok": {"username": "", "sign_api_key": ""},
    "printer": {
        "exe_path": "TiMini-Print-Command-Line-Windows-x86_64.exe",
        "bluetooth_name": "",
        "darkness": "",
        "extra_args": "",
    },
    "print": {
        "width_px": "384",
        "avatar_scale": "1.0",
        "max_per_minute": "6",
        "queue_max": "20",
        "dedupe": "true",
        "show_username": "true",
        "retries": "2",
    },
    "app": {"save_dir": "prints"},
}


def default_path() -> Path:
    return app_dir() / CONFIG_NAME


def load(path: Path | None = None) -> Config:
    """Read the ini file, falling back to defaults for anything absent."""
    path = path or default_path()
    parser = configparser.ConfigParser()
    parser.read_dict(_DEFAULTS)
    if path.exists():
        parser.read(path, encoding="utf-8")

    return Config(
        username=parser.get("tiktok", "username").strip().lstrip("@"),
        sign_api_key=parser.get("tiktok", "sign_api_key").strip(),
        exe_path=parser.get("printer", "exe_path").strip(),
        bluetooth_name=parser.get("printer", "bluetooth_name").strip(),
        darkness=parser.get("printer", "darkness").strip(),
        extra_args=parser.get("printer", "extra_args").strip(),
        width_px=parser.getint("print", "width_px"),
        avatar_scale=parser.getfloat("print", "avatar_scale"),
        max_per_minute=parser.getint("print", "max_per_minute"),
        queue_max=parser.getint("print", "queue_max"),
        dedupe=parser.getboolean("print", "dedupe"),
        show_username=parser.getboolean("print", "show_username"),
        retries=parser.getint("print", "retries"),
        save_dir=parser.get("app", "save_dir").strip(),
    )
