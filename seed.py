"""Insert the demo episodes (three synthetic podcast episodes + a public-domain 1961 speech excerpt).

    pxt schema update app.py podcasts
    python seed.py                                  # local catalog 'podcasts'
    PODCAST_CATALOG=pxt://<org>:<db> python seed.py # same rows into a Pixeltable Cloud database

Cover art is drawn with Pillow on first run (data/covers/*.png), so the repo ships only audio.
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import pixeltable as pxt

HERE = Path(__file__).parent
AUDIO = HERE / 'data' / 'audio'
COVERS = HERE / 'data' / 'covers'
CATALOG = os.environ.get('PODCAST_CATALOG', 'podcasts')

EPISODES = [
    dict(episode_id='pn-041', show_name='Pipeline Notes', title='Backfills without tears',
         published=dt.date(2026, 9, 2), audio='backfills-without-tears.mp3', colors=('#0f4c81', '#7ec8e3')),
    dict(episode_id='nsh-112', show_name='Night Sky Hour', title="Saturn's rings with a small telescope",
         published=dt.date(2026, 9, 9), audio='saturn-small-telescope.mp3', colors=('#14143c', '#c9a227')),
    dict(episode_id='kc-007', show_name='Kitchen Chemistry', title='Why sourdough rises',
         published=dt.date(2026, 9, 16), audio='why-sourdough-rises.mp3', colors=('#7a3e1d', '#f2d0a4')),
    dict(episode_id='arc-1961', show_name='Speech Archive', title='"City upon a hill" (January 9, 1961, excerpt)',
         published=dt.date(1961, 1, 9), audio='archive-jfk-1961-city-upon-a-hill.flac', colors=('#2b2b2b', '#b0b0b0')),
]


def draw_cover(ep: dict, size: int = 768) -> Path:
    """A simple gradient cover with the show name and episode title."""
    COVERS.mkdir(parents=True, exist_ok=True)
    path = COVERS / f"{ep['episode_id']}.png"
    if path.exists():
        return path
    top, bottom = (Image.new('RGB', (1, 1), c).getpixel((0, 0)) for c in ep['colors'])
    img = Image.new('RGB', (size, size))
    d = ImageDraw.Draw(img)
    for y in range(size):
        f = y / (size - 1)
        d.line([(0, y), (size, y)], fill=tuple(int(a + (b - a) * f) for a, b in zip(top, bottom)))
    try:
        big, small = ImageFont.load_default(56), ImageFont.load_default(30)
    except TypeError:  # Pillow < 10.1
        big = small = ImageFont.load_default()
    d.text((48, 64), ep['show_name'], fill='white', font=big)
    d.text((48, size - 120), ep['title'][:44], fill='white', font=small)
    d.ellipse([size - 260, 180, size - 60, 380], outline='white', width=6)
    img.save(path)
    return path


def main() -> None:
    episodes = pxt.get_table(f'{CATALOG}/episodes')
    rows = [
        {k: ep[k] for k in ('episode_id', 'show_name', 'title', 'published')}
        | {'audio': str(AUDIO / ep['audio']), 'cover': str(draw_cover(ep))}
        for ep in EPISODES
    ]
    existing = {r['episode_id'] for r in episodes.select(episodes.episode_id).collect()}
    new = [r for r in rows if r['episode_id'] not in existing]
    if new:
        status = episodes.insert(new, on_error='ignore')
        print(f'inserted {len(new)} episodes ({status.num_rows} rows incl. segments + cover tiles, {status.num_excs} errors)')
    else:
        print('all demo episodes already present')
    seg = pxt.get_table(f'{CATALOG}/segments')
    print(f'segments: {seg.count()} · transcription errors: {seg.where(seg.text == None).count()}')  # noqa: E711


if __name__ == '__main__':
    main()
