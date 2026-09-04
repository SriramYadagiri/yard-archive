"""
backfill_chapters.py — one-off script to add `chapters` to episodes that
were downloaded before chapter extraction existed in pipeline.py.

Uses yt_dlp.extract_info(url, download=False) -- this only fetches
metadata from YouTube, it does NOT re-download audio, so this is fast
and doesn't touch your existing .mp3 files or re-run transcription.
"""

import json
from pathlib import Path
import yt_dlp

EPISODES_FILE = "episodes.json"


def backfill():
    with open(EPISODES_FILE) as f:
        episodes = json.load(f)

    done = [e for e in episodes if e["status"] == "done"]

    patched = 0
    skipped = 0
    failed = 0

    for ep in done:
        video_id = ep["video_id"]
        transcript_path = Path(f"../data/transcripts/{video_id}.json")
        meta_path = Path(f"../data/transcripts/{video_id}_meta.json")

        if not transcript_path.exists():
            print(f"  -> skipping {video_id}: no transcript file found")
            continue

        with open(transcript_path) as f:
            transcript_data = json.load(f)

        if transcript_data.get("chapters"):
            skipped += 1
            continue

        try:
            with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
                info = ydl.extract_info(ep["url"], download=False)

            chapters = [
                {"start": c["start_time"], "end": c["end_time"], "title": c["title"]}
                for c in info.get("chapters") or []
            ]

            transcript_data["chapters"] = chapters
            with open(transcript_path, "w") as f:
                json.dump(transcript_data, f, indent=2)

            if meta_path.exists():
                with open(meta_path) as f:
                    meta_data = json.load(f)
                meta_data["chapters"] = chapters
                with open(meta_path, "w") as f:
                    json.dump(meta_data, f, indent=2)

            print(f"  {video_id}: {len(chapters)} chapters")
            patched += 1

        except Exception as e:
            print(f"  -> FAILED for {video_id}: {e}")
            failed += 1

    print(f"\nPatched {patched}, skipped {skipped} (already had chapters), failed {failed}.")


if __name__ == "__main__":
    backfill()