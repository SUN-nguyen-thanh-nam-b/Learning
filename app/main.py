"""Entry point: wire the TikTok listener to the printer."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from . import app_config, avatar_renderer, tiktok_listener
from .avatar_renderer import RenderError
from .paths import resolve
from .print_worker import PrintWorker
from .printer_client import PrinterClient, PrinterError


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )
    # The library logs every chat message at INFO, which drowns out our own.
    logging.getLogger("TikTokLive").setLevel(logging.WARNING)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tiktok-follower-printer",
        description="Print the avatar of everyone who sends a gift on your TikTok LIVE.",
    )
    parser.add_argument("--config", type=Path, help="path to config.ini")
    parser.add_argument(
        "--scan", action="store_true", help="list Bluetooth printers and exit"
    )
    parser.add_argument(
        "--test-print",
        metavar="IMAGE",
        type=Path,
        help="render and print one local image, then exit",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


def _build_printer(config: app_config.Config) -> PrinterClient:
    return PrinterClient(
        exe_path=resolve(config.exe_path),
        bluetooth_name=config.bluetooth_name,
        darkness=config.darkness,
        extra_args=config.extra_args,
    )


def main() -> int:
    args = _parse_args()
    _configure_logging(args.verbose)
    log = logging.getLogger("app")

    config_path = args.config or app_config.default_path()
    if not config_path.exists():
        log.error(
            "config not found at %s -- copy config.example.ini to config.ini "
            "and edit it",
            config_path,
        )
        return 2

    config = app_config.load(config_path)
    printer = _build_printer(config)

    if args.scan:
        try:
            print(printer.scan())
        except PrinterError as exc:
            log.error("%s", exc)
            return 1
        return 0

    if args.test_print:
        if not args.test_print.exists():
            log.error("no such image: %s", args.test_print)
            return 2
        try:
            image = avatar_renderer.render(
                args.test_print.read_bytes(),
                resolve(config.save_dir) / "test-print.png",
                width_px=config.width_px,
                caption_lines=["@test"] if config.show_username else [],
            )
        except RenderError as exc:
            log.error("%s: %s", args.test_print, exc)
            return 2
        try:
            printer.print_image(image)
        except PrinterError as exc:
            log.error("%s", exc)
            return 1
        log.info("test print sent (%s)", image)
        return 0

    if not config.username:
        log.error("set [tiktok] username in %s", config_path)
        return 2

    # TikTokLive reads its Euler Stream credentials from the environment.
    if config.sign_api_key:
        os.environ["SIGN_API_KEY"] = config.sign_api_key

    worker = PrintWorker(
        printer=printer,
        save_dir=resolve(config.save_dir),
        width_px=config.width_px,
        max_per_minute=config.max_per_minute,
        queue_max=config.queue_max,
        dedupe=config.dedupe,
        show_username=config.show_username,
        retries=config.retries,
    )
    worker.start()
    log.info(
        "watching @%s for gifts -- printing to '%s'",
        config.username,
        config.bluetooth_name or "first printer found",
    )

    try:
        tiktok_listener.run_forever(config.username, worker.submit)
    except KeyboardInterrupt:
        log.info("stopping")
    finally:
        worker.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
