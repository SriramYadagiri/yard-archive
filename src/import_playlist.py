"""
import_playlist.py

Usage:
    python import_playlist.py "https://www.youtube.com/playlist?list=..."

Adds any new videos from the playlist to episodes.json.
"""

import json
import os
import sys
import yt_dlp

EPISODES_FILE = "episodes.json"


def load_existing():
    if os.path.exists(EPISODES_FILE):
        with open(EPISODES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save(episodes):
    with open(EPISODES_FILE, "w", encoding="utf-8") as f:
        json.dump(episodes, f, indent=2)


def main():
    if len(sys.argv) != 2:
        print("Usage: python import_playlist.py <playlist_url>")
        return

    playlist_url = sys.argv[1]

    episodes = load_existing()
    existing_ids = {e["video_id"] for e in episodes}

    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)

    added = 0

    for entry in info["entries"]:
        video_id = entry["id"]

        if video_id in existing_ids:
            continue

        episodes.append({
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "status": "pending"
        })

        existing_ids.add(video_id)
        added += 1

    save(episodes)

    print(f"Added {added} new episodes.")
    print(f"Total episodes: {len(episodes)}")


if __name__ == "__main__":
    main()