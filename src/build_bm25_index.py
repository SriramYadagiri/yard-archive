"""
build_bm25_index.py — builds a BM25 keyword index over every processed
episode's chunks, for hybrid (keyword + vector) search.

Rebuild this any time your corpus changes (new episodes chunked or
re-chunked) -- same habit as re-running embed_all.py. Unlike ChromaDB,
this index isn't incrementally updatable; it's rebuilt from scratch each
time, which is fine at this corpus size (a few seconds even for the full
backlog).
"""

import json
import pickle
import re
from pathlib import Path
from rank_bm25 import BM25Okapi

EPISODES_FILE = "episodes.json"
INDEX_FILE = "bm25_index.pkl"


def tokenize(text):
    return re.findall(r"[a-z0-9']+", text.lower())


def build_index():
    with open(EPISODES_FILE) as f:
        episodes = json.load(f)

    done = [e for e in episodes if e["status"] == "done"]

    chunks = []
    for ep in done:
        video_id = ep["video_id"]
        chunks_path = Path(f"../data/transcripts/{video_id}_chunks.json")
        if not chunks_path.exists():
            continue
        with open(chunks_path) as f:
            data = json.load(f)
        chunks.extend(data["chunks"])

    tokenized_corpus = [tokenize(c["text"]) for c in chunks]
    index = BM25Okapi(tokenized_corpus)

    with open(INDEX_FILE, "wb") as f:
        pickle.dump({"chunks": chunks, "index": index}, f)

    print(f"Indexed {len(chunks)} chunks from {len(done)} episodes.")


if __name__ == "__main__":
    build_index()