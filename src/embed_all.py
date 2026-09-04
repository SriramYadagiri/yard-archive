"""
embed_all.py — runs embed_episode() over every chunked episode, skipping
any episode that's already been embedded.

Skip check: uses a local marker file (embedded_episodes.json, a simple
list of video_ids) rather than re-checking ChromaDB directly. This matters
because embed_episode() calls the OpenAI API -- re-embedding an
already-embedded episode wouldn't corrupt anything (upsert is idempotent),
but it would cost real API money for zero benefit, so skipping based on
a cheap local marker is worth it over "just let upsert handle it."

Delete an episode's video_id from embedded_episodes.json manually if you
ever want to force a re-embed (e.g. after re-chunking with new logic).
"""

import json
from pathlib import Path
from embed import embed_episode

EPISODES_FILE = "episodes.json"
MARKER_FILE = "embedded_episodes.json"


def load_embedded_ids():
    if Path(MARKER_FILE).exists():
        with open(MARKER_FILE) as f:
            return set(json.load(f))
    return set()


def save_embedded_ids(ids):
    with open(MARKER_FILE, "w") as f:
        json.dump(sorted(ids), f, indent=2)


def run():
    with open(EPISODES_FILE) as f:
        episodes = json.load(f)

    done = [e for e in episodes if e["status"] == "done"]
    embedded_ids = load_embedded_ids()

    skipped = 0
    processed = 0

    for ep in done:
        video_id = ep["video_id"]
        chunks_path = Path(f"../data/transcripts/{video_id}_chunks.json")

        if video_id in embedded_ids:
            skipped += 1
            continue

        if not chunks_path.exists():
            print(f"  -> skipping {video_id}: not chunked yet (run chunk_all.py first)")
            continue

        try:
            embed_episode(video_id)
            embedded_ids.add(video_id)
            save_embedded_ids(embedded_ids)  # persist after every episode
            processed += 1
        except Exception as e:
            print(f"  -> FAILED to embed {video_id}: {e}")

    print(f"\nEmbedded {processed} new episode(s), skipped {skipped} already-embedded episode(s).")


if __name__ == "__main__":
    run()