"""Listen for gift events on a TikTok LIVE room."""

from __future__ import annotations

import logging
import time
from typing import Callable

from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, DisconnectEvent, GiftEvent

from .print_worker import PrintJob

log = logging.getLogger(__name__)

# Ordered largest first so the renderer has the most pixels to downscale from.
_AVATAR_FIELDS = ("avatar_large", "avatar_medium", "avatar_thumb", "avatar_jpg")


def _avatar_url(user) -> str:
    for field in _AVATAR_FIELDS:
        image = getattr(user, field, None)
        urls = getattr(image, "url_list", None) if image is not None else None
        if urls:
            return urls[0]
    return ""


def _to_job(user, detail: str) -> PrintJob | None:
    if user is None:
        return None
    return PrintJob(
        user_id=user.id_str or str(user.id),
        handle=user.display_id or user.nickname or "unknown",
        avatar_url=_avatar_url(user),
        detail=detail,
    )


def _gift_detail(event: GiftEvent) -> str:
    name = (event.gift.name if event.gift is not None else "") or "Gift"
    count = max(event.repeat_count, 1)
    return f"{name} x{count}" if count > 1 else name


def _build_client(username: str, on_job: Callable[[PrintJob], None]):
    client = TikTokLiveClient(unique_id=username)

    @client.on(ConnectEvent)
    async def _on_connect(event) -> None:  # noqa: ANN001
        log.info("connected to @%s's live room", username)

    @client.on(DisconnectEvent)
    async def _on_disconnect(event) -> None:  # noqa: ANN001
        log.warning("disconnected from @%s's live room", username)

    @client.on(GiftEvent)
    async def _on_gift(event) -> None:  # noqa: ANN001
        # TikTok emits one event per tick of a combo gift. Only the closing
        # event has streaking=False and carries the final repeat_count, so
        # printing mid-streak would spit out one slip per rose.
        if event.streaking:
            return
        job = _to_job(event.user, _gift_detail(event))
        if job is None:
            log.warning("gift event carried no user")
            return
        on_job(job)

    return client


def run_forever(
    username: str,
    on_job: Callable[[PrintJob], None],
    reconnect_delay: float = 15.0,
) -> None:
    """Stay connected for the whole stream, reconnecting when it drops.

    ``client.run()`` returns as soon as the room closes -- which happens every
    time the stream ends, the network blips, or TikTok drops the socket -- so a
    long broadcast needs this outer retry loop. A fresh client is built each
    attempt because a disconnected one is not reusable.
    """
    while True:
        client = _build_client(username, on_job)
        try:
            client.run()
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            log.warning("live connection failed: %s", exc)

        log.info(
            "reconnecting in %.0fs (make sure @%s is actually live)",
            reconnect_delay,
            username,
        )
        time.sleep(reconnect_delay)
