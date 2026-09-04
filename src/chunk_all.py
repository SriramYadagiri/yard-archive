"""
chunk_all.py — runs chunk_transcript() over every episode marked "done"
in episodes.json, skipping any episode that's already been chunked.

Skip check: if ../data/transcripts/{video_id}_chunks.json already exists,
that episode is skipped -- chunking is deterministic given the same
transcript + same chunking logic, so there's no reason to redo work
that's already on disk. Delete the _chunks.json file manually if you
ever want to force a re-chunk (e.g. after changing MAX_WORDS).
"""

import json
from pathlib import Path
from transcript_chunker import chunk_transcript

EPISODES_FILE = "episodes.json"


def run():
    with open(EPISODES_FILE) as f:
        episodes = json.load(f)

    done = [e for e in episodes if e["status"] == "done"]

    skipped = 0
    processed = 0

    for ep in done:
        video_id = ep["video_id"]
        chunks_path = Path(f"../data/transcripts/{video_id}_chunks.json")

        if chunks_path.exists():
            skipped += 1
            continue

        try:
            chunk_transcript(video_id)
            processed += 1
        except Exception as e:
            print(f"  -> FAILED to chunk {video_id}: {e}")

    print(f"\nChunked {processed} new episode(s), skipped {skipped} already-chunked episode(s).")


if __name__ == "__main__":
    run()