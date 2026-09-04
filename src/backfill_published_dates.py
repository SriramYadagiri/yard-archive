"""
backfill_published_date.py — short one-off script that adds published_ts
and published_date to any already-processed episode missing them.

Uses yt_dlp.extract_info(url, download=False) -- metadata only, no
re-download of audio, no re-transcription. Safe to re-run: skips any
episode that already has published_ts set.
"""

import json
from pathlib import Path
from datetime import datetime
import yt_dlp

EPISODES_FILE = "episodes.json"


def backfill():
    with open(EPISODES_FILE) as f:
        episodes = json.load(f)

    done = [e for e in episodes if e["status"] == "done"]
    patched, skipped, failed = 0, 0, 0

    for ep in done:
        video_id = ep["video_id"]
        transcript_path = Path(f"../data/transcripts/{video_id}.json")
        meta_path = Path(f"../data/transcripts/{video_id}_meta.json")

        if not transcript_path.exists():
            continue

        with open(transcript_path) as f:
            transcript_data = json.load(f)

        if transcript_data.get("published_ts"):
            skipped += 1
            continue

        try:
            with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
                info = ydl.extract_info(ep["url"], download=False)

            upload_date_str = info.get("upload_date")
            if upload_date_str:
                dt = datetime.strptime(upload_date_str, "%Y%m%d")
                published_ts = int(dt.timestamp())
                published_date = dt.strftime("%Y-%m-%d")
            else:
                published_ts, published_date = None, None

            transcript_data["published_ts"] = published_ts
            transcript_data["published_date"] = published_date
            with open(transcript_path, "w") as f:
                json.dump(transcript_data, f, indent=2)

            if meta_path.exists():
                with open(meta_path) as f:
                    meta_data = json.load(f)
                meta_data["published_ts"] = published_ts
                meta_data["published_date"] = published_date
                with open(meta_path, "w") as f:
                    json.dump(meta_data, f, indent=2)

            print(f"  {video_id}: published {published_date}")
            patched += 1

        except Exception as e:
            print(f"  -> FAILED for {video_id}: {e}")
            failed += 1

    print(f"\nPatched {patched}, skipped {skipped} (already had it), failed {failed}.")


if __name__ == "__main__":
    backfill()