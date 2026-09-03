"""Turn a TikTok avatar URL into an image the PD-01 can print."""

from __future__ import annotations

import io
from collections.abc import Sequence
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

# Tried in order for the caption. Segoe UI ships with Windows and has the
# widest Unicode coverage; the PIL bitmap font is the last resort.
_CAPTION_FONTS = ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf")

_LINE_GAP = 6
_CAPTION_PADDING = 10


class RenderError(RuntimeError):
    """Raised when the downloaded bytes are not a usable image."""


def _load_font(size: int):
    for name in _CAPTION_FONTS:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _center_square(image: Image.Image) -> Image.Image:
    side = min(image.size)
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    return image.crop((left, top, left + side, top + side))


def download(url: str, timeout: float = 10.0) -> bytes:
    response = httpx.get(url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    return response.content


def render(
    avatar_bytes: bytes,
    out_path: Path,
    width_px: int = 384,
    caption_lines: Sequence[str] = (),
) -> Path:
    """Square-crop the avatar, scale it to the printer's dot width, caption it.

    The image is left greyscale: TiMini-Print rasterises to 1-bit itself and
    applies Atkinson dithering, so pre-thresholding here would only throw
    away tones it needs. autocontrast widens the range it has to work with.
    """
    try:
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise RenderError(
            f"not a readable image ({len(avatar_bytes)} bytes) -- a truncated "
            "download or an error page saved as an image will do this"
        ) from exc
    avatar = _center_square(avatar).resize((width_px, width_px), Image.LANCZOS)
    avatar = ImageOps.autocontrast(avatar.convert("L"))

    lines = [line for line in caption_lines if line]
    font = _load_font(max(16, width_px // 14)) if lines else None
    line_height = (font.size + _LINE_GAP) if font else 0
    caption_height = (len(lines) * line_height + _CAPTION_PADDING) if lines else 0

    canvas = Image.new("L", (width_px, width_px + caption_height), color=255)
    canvas.paste(avatar, (0, 0))

    if font is not None:
        draw = ImageDraw.Draw(canvas)
        y = width_px + _CAPTION_PADDING // 2
        for line in lines:
            box = draw.textbbox((0, 0), line, font=font)
            x = max(0, (width_px - (box[2] - box[0])) // 2)
            draw.text((x, y), line, font=font, fill=0)
            y += line_height

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, format="PNG")
    return out_path
