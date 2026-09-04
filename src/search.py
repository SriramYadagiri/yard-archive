"""
search.py — natural language search over embedded podcast chunks.
"""

import json
import os
import re
import sys
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import chromadb

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
TOP_K = 5

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
chroma_client = chromadb.PersistentClient(path="../data/chroma")
collection = chroma_client.get_or_create_collection("yard_transcripts")

_episode_cache = {}


def _load_episode_data(video_id):
    if video_id not in _episode_cache:
        try:
            with open(f"../data/transcripts/{video_id}.json") as f:
                _episode_cache[video_id] = json.load(f)
        except FileNotFoundError:
            _episode_cache[video_id] = {}
    return _episode_cache[video_id]


def resolve_speaker(video_id, speaker_id):
    speaker_map = _load_episode_data(video_id).get("speaker_map", {})
    return speaker_map.get(str(speaker_id), f"Speaker {speaker_id}")


def resolve_title(video_id):
    return _load_episode_data(video_id).get("title", video_id)


def resolve_published_date(video_id):
    return _load_episode_data(video_id).get("published_date")


def resolve_chunk_text(video_id, text):
    def replace(match):
        speaker_id = match.group(1)
        return f"{resolve_speaker(video_id, speaker_id)}:"

    return re.sub(r"Speaker (\d+):", replace, text)


def embed_query(query):
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[query],
    )
    return response.data[0].embedding


def _date_to_ts(date_str):
    return int(datetime.strptime(date_str, "%Y-%m-%d").timestamp())


def _build_date_where(date_from, date_to):
    conditions = []
    if date_from:
        conditions.append({"published_ts": {"$gte": _date_to_ts(date_from)}})
    if date_to:
        conditions.append({"published_ts": {"$lte": _date_to_ts(date_to)}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def search(query, top_k=TOP_K, date_from=None, date_to=None):
    query_vector = embed_query(query)
    where = _build_date_where(date_from, date_to)

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        where=where,
    )

    hits = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        video_id = meta["video_id"]
        raw_speaker_ids = json.loads(meta["speakers"])
        raw_text = results["documents"][0][i]

        hits.append({
            "chunk_id": results["ids"][0][i],
            "text": resolve_chunk_text(video_id, raw_text),
            "video_id": video_id,
            "title": resolve_title(video_id),
            "chapter": meta.get("chapter") or None,
            "published_date": resolve_published_date(video_id),
            "published_ts": meta.get("published_ts", 0),
            "speakers": [resolve_speaker(video_id, sid) for sid in raw_speaker_ids],
            "speaker_confidence": meta.get("speaker_confidence", 0.0),
            "start": meta["start"],
            "end": meta["end"],
            "distance": results["distances"][0][i],
        })
    return hits


def print_results(hits):
    for hit in hits:
        start_seconds = int(hit["start"])
        link = f"https://www.youtube.com/watch?v={hit['video_id']}&t={start_seconds}s"
        header = hit["title"]
        if hit["chapter"]:
            header += f" — {hit['chapter']}"
        if hit["published_date"]:
            header += f" ({hit['published_date']})"
        print(f"\n{header}")
        print(f"{', '.join(hit['speakers'])} (conf={hit['speaker_confidence']:.2f}) | "
              f"{hit['start']:.1f}s-{hit['end']:.1f}s | distance={hit['distance']:.3f}")
        print(f"  {hit['text']}")
        print(f"  {link}")


if __name__ == "__main__":
    query = " ".join(sys.argv[1:])
    if not query:
        result = collection.get(limit=1, include=["metadatas"])
        print(result["metadatas"][0])
        print("Usage: python search.py <your natural language query>")
        sys.exit(1)

    hits = search(query)
    print_results(hits)