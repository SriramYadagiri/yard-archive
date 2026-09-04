"""
pipeline_all.py — runs the full pipeline (download -> transcribe -> chunk
-> embed -> auto-label speakers) per episode, so scaling through the
remaining backlog is one command instead of four manual steps.
"""

import json
from pathlib import Path

from pipeline import download_episode, transcribe_episode
from transcript_chunker import chunk_transcript
from embed import embed_episode
from embed_all import load_embedded_ids, save_embedded_ids

EPISODES_FILE = "episodes.json"
REFERENCES_FILE = "speaker_references.json"


def load_episodes():
    with open(EPISODES_FILE) as f:
        return json.load(f)


def save_episodes(episodes):
    with open(EPISODES_FILE, "w") as f:
        json.dump(episodes, f, indent=2)


def maybe_auto_label(video_id):
    if not Path(REFERENCES_FILE).exists():
        return

    transcript_path = Path(f"../data/transcripts/{video_id}.json")
    with open(transcript_path) as f:
        data = json.load(f)

    if data.get("speaker_map"):
        return  # already labeled -- don't overwrite

    from auto_label_speakers import auto_label
    try:
        auto_label(video_id)
    except Exception as e:
        print(f"  -> auto-labeling FAILED for {video_id}: {e}")


def run(limit=None):
    episodes = load_episodes()
    embedded_ids = load_embedded_ids()

    pending = [e for e in episodes if e["status"] == "pending" or e["status"] == "failed"]
    already_done = [e for e in episodes if e["status"] == "done"]

    if limit:
        pending = pending[:limit]

    print(f"Processing {len(pending)} pending episode(s); "
          f"{len(already_done)} already downloaded/transcribed.\n")

    for ep in pending:
        url = ep["url"]
        print(f"Processing: {url}")

        try:
            video_id = download_episode(url)
            ep["video_id"] = video_id
            transcribe_episode(video_id)
            ep["status"] = "done"
            print(f"  -> downloaded + transcribed ({video_id})")
        except Exception as e:
            ep["status"] = "failed"
            ep["error"] = str(e)
            print(f"  -> FAILED at download/transcribe: {e}")
            save_episodes(episodes)
            continue

        save_episodes(episodes)

        video_id = ep["video_id"]
        chunks_path = Path(f"../data/transcripts/{video_id}_chunks.json")

        try:
            if not chunks_path.exists():
                chunk_transcript(video_id)
                print(f"  -> chunked")
            else:
                print(f"  -> already chunked, skipping")

            if video_id not in embedded_ids:
                embed_episode(video_id)
                embedded_ids.add(video_id)
                save_embedded_ids(embedded_ids)
                print(f"  -> embedded")
            else:
                print(f"  -> already embedded, skipping")

            maybe_auto_label(video_id)
            print(f"  -> speaker labeling checked")

        except Exception as e:
            print(f"  -> FAILED during chunk/embed/label: {e}")

    print("\nDone with this batch.")


if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run(limit=limit)