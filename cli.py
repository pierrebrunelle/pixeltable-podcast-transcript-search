"""Command-line front end for the transcript archive.

    python cli.py search "how do I see the gap in Saturn's rings"   # top segments + mm:ss offsets
    python cli.py transcript nsh-112                                # one episode, segment by segment
    python cli.py episodes                                          # what is in the archive
    PODCAST_CATALOG=pxt://<org>:<db> python cli.py search "idempotent backfill"
"""

from __future__ import annotations

import argparse
import os

import pixeltable as pxt

CATALOG = os.environ.get('PODCAST_CATALOG', 'podcasts')


def search(question: str, k: int) -> None:
    seg = pxt.get_table(f'{CATALOG}/segments')
    sim = seg.text.similarity(string=question, idx='transcript_embed')
    rows = (
        seg.order_by(sim, asc=False)
        .limit(k)
        .select(seg.show_name, seg.title, seg.at, seg.preview, score=sim)
        .collect()
    )
    for r in rows:
        print(f"{r['score']:.3f}  {r['show_name']} — {r['title']} @ {r['at']}\n       {r['preview']}")


def transcript(episode_id: str) -> None:
    seg = pxt.get_table(f'{CATALOG}/segments')
    q = seg.where(seg.episode_id == episode_id).order_by(seg.segment_start)
    for r in q.select(seg.at, seg.wpm, seg.text).collect():
        print(f"[{r['at']}] ({r['wpm']} wpm) {r['text']}")


def episodes() -> None:
    ep = pxt.get_table(f'{CATALOG}/episodes')
    seg = pxt.get_table(f'{CATALOG}/segments')
    counts = {r['episode_id']: r['n'] for r in seg.group_by(seg.episode_id).select(seg.episode_id, n=pxt.functions.count(seg.pos)).collect()}
    for r in ep.order_by(ep.published).select(ep.episode_id, ep.show_name, ep.title, ep.published, secs=ep.audio_meta.streams[0].duration_seconds).collect():
        print(f"{r['episode_id']:9s} {r['published']}  {r['show_name']}: {r['title']}  ({r["secs"] or 0:.0f} s, {counts.get(r["episode_id"], 0)} segments)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('search', help='semantic search over transcripts')
    s.add_argument('question')
    s.add_argument('-k', type=int, default=3)
    t = sub.add_parser('transcript', help='print one episode transcript')
    t.add_argument('episode_id')
    sub.add_parser('episodes', help='list episodes')
    a = ap.parse_args()
    if a.cmd == 'search':
        search(a.question, a.k)
    elif a.cmd == 'transcript':
        transcript(a.episode_id)
    else:
        episodes()


if __name__ == '__main__':
    main()
