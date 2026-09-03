"""Serialised, rate-limited print pipeline."""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import avatar_renderer
from .printer_client import PrinterClient, PrinterError

log = logging.getLogger(__name__)

_SHUTDOWN = object()


@dataclass(frozen=True)
class PrintJob:
    user_id: str
    handle: str
    avatar_url: str
    # Second caption line naming the gift, e.g. "Rose x5".
    detail: str = ""


class PrintWorker:
    """Consumes :class:`PrintJob` items on one background thread.

    BLE allows a single connection to the printer, so jobs must print strictly
    one at a time. Bursts are absorbed by the queue and shed once it is full,
    which keeps a viral moment from backing up the websocket or burning
    through a whole roll of paper.
    """

    def __init__(
        self,
        printer: PrinterClient,
        save_dir: Path,
        width_px: int = 384,
        max_per_minute: int = 6,
        queue_max: int = 20,
        dedupe: bool = True,
        show_username: bool = True,
        retries: int = 2,
        retry_delay: float = 5.0,
    ) -> None:
        self._printer = printer
        self._save_dir = save_dir
        self._width_px = width_px
        self._max_per_minute = max_per_minute
        self._dedupe = dedupe
        self._show_username = show_username
        self._retries = max(retries, 0)
        self._retry_delay = retry_delay

        self._queue: queue.Queue = queue.Queue(maxsize=queue_max)
        self._seen: set[str] = set()
        self._recent_prints: deque[float] = deque()
        self._thread = threading.Thread(
            target=self._loop, name="print-worker", daemon=True
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._queue.put(_SHUTDOWN)
        self._thread.join(timeout=timeout)

    def submit(self, job: PrintJob) -> None:
        """Queue a print job. Safe to call from the asyncio event loop."""
        if self._dedupe and job.user_id in self._seen:
            log.info("skip @%s (already printed this session)", job.handle)
            return
        if not job.avatar_url:
            log.warning("skip @%s (no avatar URL in event)", job.handle)
            return

        try:
            self._queue.put_nowait(job)
        except queue.Full:
            log.warning("queue full, dropped @%s", job.handle)
            return

        self._seen.add(job.user_id)
        log.info("queued @%s -- %s (%d waiting)",
                 job.handle, job.detail or "gift", self._queue.qsize())

    def _throttle(self) -> None:
        """Block until printing another job stays under the per-minute cap."""
        if self._max_per_minute <= 0:
            return
        now = time.monotonic()
        while self._recent_prints and now - self._recent_prints[0] >= 60.0:
            self._recent_prints.popleft()
        if len(self._recent_prints) >= self._max_per_minute:
            wait = 60.0 - (now - self._recent_prints[0])
            log.info("rate limit reached, waiting %.0fs", wait)
            time.sleep(max(wait, 0.0))

    def _print_with_retries(self, job: PrintJob, image: Path) -> bool:
        """Print, retrying a few times before giving up on this gift.

        The printer sleeps after a few idle minutes and stops advertising over
        BLE, which makes discovery fail. Gift events never repeat, so a single
        failed attempt would lose that person's slip for good.
        """
        attempts = self._retries + 1
        for attempt in range(1, attempts + 1):
            try:
                self._printer.print_image(image)
                return True
            except PrinterError as exc:
                if attempt == attempts:
                    # Nothing came out; drop the dedupe entry so a later event
                    # from the same person still has a chance.
                    self._seen.discard(job.user_id)
                    log.error(
                        "gave up on @%s after %d attempt(s): %s",
                        job.handle, attempts, exc,
                    )
                    return False
                log.warning(
                    "print attempt %d/%d for @%s failed (%s); retrying in %.0fs",
                    attempt, attempts, job.handle, exc, self._retry_delay,
                )
                time.sleep(self._retry_delay)
        return False

    def _loop(self) -> None:
        while True:
            job = self._queue.get()
            if job is _SHUTDOWN:
                return
            try:
                self._handle(job)
            except Exception:  # keep the worker alive across any single failure
                log.exception("failed to print @%s", job.handle)

    def _handle(self, job: PrintJob) -> None:
        self._throttle()

        captions = []
        if self._show_username:
            captions.append(f"@{job.handle}")
        if job.detail:
            captions.append(job.detail)

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_path = self._save_dir / f"{stamp}-{job.handle}.png"
        image = avatar_renderer.render(
            avatar_renderer.download(job.avatar_url),
            out_path,
            width_px=self._width_px,
            caption_lines=captions,
        )

        started = time.monotonic()
        if not self._print_with_retries(job, image):
            return

        self._recent_prints.append(time.monotonic())
        log.info(
            "printed @%s in %.1fs -> %s",
            job.handle,
            time.monotonic() - started,
            image.name,
        )
