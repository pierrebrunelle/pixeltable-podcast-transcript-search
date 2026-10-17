"""UDFs for the podcast transcript archive (pure Python, no table imports)."""

from __future__ import annotations

import re

import PIL.Image

import pixeltable as pxt


@pxt.udf
def set_opacity(img: PIL.Image.Image, opacity: float) -> PIL.Image.Image:
    """Scale the alpha channel of an image (docs cookbook: adjust image opacity)."""
    img = img.convert('RGBA')
    alpha = img.split()[3].point(lambda p: int(p * opacity))
    img.putalpha(alpha)
    return img


@pxt.udf
def mmss(seconds: float) -> str:
    """Format a segment offset as mm:ss for deep links into an episode."""
    s = int(seconds or 0)
    return f'{s // 60:02d}:{s % 60:02d}'


@pxt.udf
def word_count(text: str) -> int:
    return len(re.findall(r"[\w']+", text or ''))


@pxt.udf
def words_per_minute(words: int, start: float, end: float) -> float:
    """Speaking rate of one segment."""
    dur = max((end or 0.0) - (start or 0.0), 1e-6)
    return round(words * 60.0 / dur, 1)


@pxt.udf
def snippet(text: str, limit: int = 140) -> str:
    """First sentence-ish chunk of a transcript segment for search results."""
    t = ' '.join((text or '').split())
    return t if len(t) <= limit else t[: limit - 1].rsplit(' ', 1)[0] + '…'
