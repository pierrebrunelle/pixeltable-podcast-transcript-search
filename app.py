"""Searchable podcast and meeting transcript archive built with Pixeltable.

Episodes go in as audio files plus cover art. Pixeltable splits each episode into
~30 s segments (audio_splitter, cuts snapped to silence), transcribes every segment
with the OpenAI Whisper API, and keeps an embedding index over the transcript text,
so a question like "how do I see the Cassini division" returns the episode and the
mm:ss offset where it is discussed. Cover art is cut into tiles (tile_iterator) and a
faded copy is kept for the archive page.

Layout: UDFs live in udfs.py; this file holds table models and @pxt.query functions.
No HTTP router: drive it with `python seed.py` and `python cli.py search "<question>"`.

    pxt schema update app.py podcasts
    python seed.py
    python cli.py search "why does sourdough taste sour"
"""

from __future__ import annotations

import pixeltable as pxt
import pixeltable.functions as pxtf
from pixeltable.functions import openai

from udfs import mmss, set_opacity, snippet, word_count, words_per_minute

TRANSCRIBE_MODEL = 'whisper-1'
EMBED_MODEL = 'text-embedding-3-small'

TableModel = pxt.model_base()


class Episodes(TableModel, name='episodes', has_default_idxs=False):
    """One podcast episode or meeting recording."""

    episode_id = pxt.Column(type=pxt.String, primary_key=True)
    show_name: pxt.String
    title: pxt.String
    published: pxt.Date
    audio: pxt.Audio
    cover: pxt.Image

    audio_meta = pxtf.audio.get_metadata(audio)
    cover_thumb = pxtf.image.thumbnail(cover, size=(160, 160))
    cover_faded = set_opacity(cover, 0.5)

    __indexes__ = [pxt.BtreeIndex(show_name)]


class Segments(
    TableModel,
    name='segments',
    base=Episodes,
    iterator=pxtf.audio.audio_splitter(
        Episodes.audio, duration=30.0, overlap=1.0, min_segment_duration=4.0, min_silence_len=0.3
    ),
):
    """Component view: one row per ~30 s audio segment, transcribed with Whisper."""

    transcript = openai.transcriptions(audio_segment, model=TRANSCRIBE_MODEL)  # type: ignore[name-defined]  # noqa: F821
    text = transcript.text.astype(pxt.String)
    words = word_count(text)
    at = mmss(segment_start)  # type: ignore[name-defined]  # noqa: F821
    wpm = words_per_minute(words, segment_start, segment_end)  # type: ignore[name-defined]  # noqa: F821
    preview = snippet(text)

    __indexes__ = [
        pxt.EmbeddingIndex(text, string_embed=openai.embeddings.using(model=EMBED_MODEL), name='transcript_embed')
    ]


class CoverTiles(
    TableModel,
    name='cover_tiles',
    base=Episodes,
    iterator=pxtf.image.tile_iterator(Episodes.cover, tile_size=(256, 256), overlap=(32, 32)),
):
    """Component view: overlapping 256 px tiles of each cover (for detail checks and thumbnails)."""

    detail = pxtf.image.entropy(tile)  # type: ignore[name-defined]  # noqa: F821


@pxt.query
def search_transcripts(question: str, k: int = 5):
    """Top-k transcript segments closest in meaning to the question, with the mm:ss offset."""
    sim = Segments.text.similarity(string=question, idx='transcript_embed')
    return (
        Segments.order_by(sim, asc=False)
        .limit(k)
        .select(Segments.show_name, Segments.title, Segments.at, Segments.text, score=sim)
    )


@pxt.query
def episode_transcript(episode_id: str):
    """Full transcript of one episode, segment by segment."""
    return (
        Segments.where(Segments.episode_id == episode_id)
        .order_by(Segments.segment_start)
        .select(Segments.at, Segments.text, Segments.words)
    )


@pxt.query
def show_episodes(show_name: str):
    """Episodes of one show (show index)."""
    return Episodes.where(Episodes.show_name == show_name).order_by(Episodes.published).select(
        Episodes.episode_id, Episodes.title, Episodes.published
    )
