"""
bm25_search.py — keyword search over the prebuilt BM25 index, returning
hits in the same shape as search.search() so they can be fused via RRF
with vector search results.

The index is loaded once at import time and cached in memory. Rebuild it
with build_bm25_index.py whenever your corpus changes -- this module
does NOT auto-detect staleness, it just loads whatever's on disk.
"""

import pickle
import os
from datetime import datetime
from pathlib import Path

from build_bm25_index import tokenize
from search import resolve_speaker, resolve_title, resolve_chunk_text, resolve_published_date

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
INDEX_FILE = Path(os.getenv("BM25_INDEX_FILE", Path(__file__).resolve().parent / "bm25_index.pkl"))

_index_data = None


def _load_index():
    global _index_data
    if _index_data is None:
        if not Path(INDEX_FILE).exists():
            raise FileNotFoundError(
                f"{INDEX_FILE} not found -- run `python build_bm25_index.py` first."
            )
        with open(INDEX_FILE, "rb") as f:
            _index_data = pickle.load(f)
    return _index_data


def _date_to_ts(date_str):
    return int(datetime.strptime(date_str, "%Y-%m-%d").timestamp())


def bm25_search(query, top_k=40, date_from=None, date_to=None):
    data = _load_index()
    chunks = data["chunks"]
    index = data["index"]

    tokenized_query = tokenize(query)
    scores = index.get_scores(tokenized_query)

    # BM25 has no query-time "where" clause like ChromaDB -- date
    # filtering here is a plain post-filter over the scored list, using
    # each chunk's own published_ts (already present on every chunk
    # since transcript_chunker.py writes it in).
    date_from_ts = _date_to_ts(date_from) if date_from else None
    date_to_ts = _date_to_ts(date_to) if date_to else None

    scored = []
    for chunk, score in zip(chunks, scores):
        if score <= 0:
            continue  # no keyword overlap at all -- not a real candidate
        ts = chunk.get("published_ts") or 0
        if date_from_ts and ts < date_from_ts:
            continue
        if date_to_ts and ts > date_to_ts:
            continue
        scored.append((score, chunk))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    top = scored[:top_k]

    hits = []
    for score, chunk in top:
        video_id = chunk["video_id"]
        hits.append({
            "chunk_id": chunk["chunk_id"],
            "text": resolve_chunk_text(video_id, chunk["text"]),
            "video_id": video_id,
            "title": resolve_title(video_id),
            "chapter": chunk.get("chapter") or None,
            "published_date": resolve_published_date(video_id),
            "published_ts": chunk.get("published_ts") or 0,
            "speakers": [resolve_speaker(video_id, sid) for sid in chunk["speakers"]],
            "speaker_confidence": chunk.get("speaker_confidence") or 0.0,
            "start": chunk["start"],
            "end": chunk["end"],
            "bm25_score": score,
        })
    return hits
