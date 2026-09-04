"""
process_manual_episode.py — for an episode whose audio you already
downloaded manually, this fills in the missing pieces (metadata, chapters,
published date) and runs it through the rest of the pipeline
(transcribe -> chunk -> embed), then marks it done in episodes.json.

Usage:
    python process_manual_episode.py <youtube_url> <path_to_existing_mp3>

Example:
    python process_manual_episode.py https://www.youtube.com/watch?v=abc123 \
        ~/Downloads/some_episode.mp3
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
import yt_dlp

from pipeline import transcribe_episode
from transcript_chunker import chunk_transcript
from embed import embed_episode

EPISODES_FILE = "episodes.json"


def process_manual_episode():
    video_id = "yUrX-tM0bB4"
    url = "https://www.youtube.com/watch?v=yUrX-tM0bB4"

    metadata = {
        "video_id": video_id,
        "title": "Jschlatt Is A Bad Influence | The Yard",
        "duration": 5190,
        "url": url,
        "chapters": [
            {
            "start": 0,
            "end": 30,
            "title": "intro"
            },
            {
            "start": 30,
            "end": 90,
            "title": "ludwig shows what he's like before recording"
            },
            {
            "start": 90,
            "end": 373,
            "title": "we're putting aiden in a zoo"
            },
            {
            "start": 373,
            "end": 408,
            "title": "slime's australian accent"
            },
            {
            "start": 408,
            "end": 463,
            "title": "joshman needs a smaller pillow"
            },
            {
            "start": 463,
            "end": 600,
            "title": "the boys figure out what a panopticon is"
            },
            {
            "start": 600,
            "end": 648,
            "title": "offbrand strays"
            },
            {
            "start": 648,
            "end": 728,
            "title": "ludwig has beef with his editors"
            },
            {
            "start": 728,
            "end": 839,
            "title": "radstads catches pigeons"
            },
            {
            "start": 839,
            "end": 855,
            "title": "prezoh"
            },
            {
            "start": 855,
            "end": 871,
            "title": "friendly fire"
            },
            {
            "start": 871,
            "end": 990,
            "title": "ludwig needs to apologise to shake"
            },
            {
            "start": 990,
            "end": 1018,
            "title": "learning quickbooks whilst high"
            },
            {
            "start": 1018,
            "end": 1125,
            "title": "jerma makes everyone laugh at the table"
            },
            {
            "start": 1125,
            "end": 1218,
            "title": "jschlatt becomes the dad at the table"
            },
            {
            "start": 1218,
            "end": 1520,
            "title": "ludwig forgets to invite nick"
            },
            {
            "start": 1520,
            "end": 1730,
            "title": "who is daddy?"
            },
            {
            "start": 1730,
            "end": 1800,
            "title": "ludwig walked in on his japanese teacher..."
            },
            {
            "start": 1800,
            "end": 1879,
            "title": "ludwig's teacher found out about his youtube channel"
            },
            {
            "start": 1879,
            "end": 2059,
            "title": "the boys have a hypothetical"
            },
            {
            "start": 2059,
            "end": 2116,
            "title": "vomiting during a battle rap"
            },
            {
            "start": 2116,
            "end": 2198,
            "title": "ludwig got insulted and now he's embarrassed"
            },
            {
            "start": 2198,
            "end": 2250,
            "title": "i fucked up"
            },
            {
            "start": 2250,
            "end": 2400,
            "title": "unpaid intern"
            },
            {
            "start": 2400,
            "end": 2472,
            "title": "shake still watches ludwigs content"
            },
            {
            "start": 2472,
            "end": 2545,
            "title": "slime messages ludwig after the show..."
            },
            {
            "start": 2545,
            "end": 2682,
            "title": "slime thinks he's 100"
            },
            {
            "start": 2682,
            "end": 2804,
            "title": "Factor!"
            },
            {
            "start": 2804,
            "end": 2876,
            "title": "IJBOL"
            },
            {
            "start": 2876,
            "end": 3270,
            "title": "aiden gets lectured on the basketball court"
            },
            {
            "start": 3270,
            "end": 3394,
            "title": "the new meta to stop ludwig"
            },
            {
            "start": 3394,
            "end": 3445,
            "title": "QT finds the basketball boring"
            },
            {
            "start": 3445,
            "end": 3620,
            "title": "slime is a hobby lobby"
            },
            {
            "start": 3620,
            "end": 3805,
            "title": "TEKKEN 8"
            },
            {
            "start": 3805,
            "end": 3820,
            "title": "peter is excited for the new bezerk manga"
            },
            {
            "start": 3820,
            "end": 3905,
            "title": "slime's insane league squad"
            },
            {
            "start": 3905,
            "end": 4090,
            "title": "ludwig got etoiles a $1,000 gift box"
            },
            {
            "start": 4090,
            "end": 4235,
            "title": "the goon commander"
            },
            {
            "start": 4235,
            "end": 4262,
            "title": "nick misses soonsay"
            },
            {
            "start": 4262,
            "end": 4425,
            "title": "slime calls soonsay"
            },
            {
            "start": 4425,
            "end": 4560,
            "title": "ludwig went to get a massage"
            },
            {
            "start": 4560,
            "end": 4684,
            "title": "boner"
            },
            {
            "start": 4684,
            "end": 4825,
            "title": "ousted"
            },
            {
            "start": 4825,
            "end": 4935,
            "title": "the fast food video"
            },
            {
            "start": 4935,
            "end": 4975,
            "title": "stanz killed it at unpaid intern"
            },
            {
            "start": 4975,
            "end": 5010,
            "title": "slime was gonna be on unpaid intern"
            },
            {
            "start": 5010,
            "end": 5145,
            "title": "the challenged in the show"
            },
            {
            "start": 5145,
            "end": 5190,
            "title": "thanks for watching"
            }
        ],
        "published_ts": 1709186400,
        "published_date": "2024-02-29",
    }
    with open(f"../data/transcripts/{video_id}_meta.json", "w") as f:
        json.dump(metadata, f, indent=2)
    print("Wrote metadata")

    # From here it's the normal pipeline.
    transcribe_episode(video_id)
    print("Transcribed")

    chunk_transcript(video_id)
    print("Chunked")

    embed_episode(video_id)
    print("Embedded")

    # Add/update this episode's entry in episodes.json so it shows up as
    # done, and future backlog runs (pipeline_all.py) don't try to
    # re-download or re-process it.
    if Path(EPISODES_FILE).exists():
        with open(EPISODES_FILE) as f:
            episodes = json.load(f)
    else:
        episodes = []

    existing = next((e for e in episodes if e.get("url") == url or e.get("video_id") == video_id), None)
    if existing:
        existing["video_id"] = video_id
        existing["status"] = "done"
        existing.pop("error", None)
    else:
        episodes.append({"video_id": video_id, "url": url, "status": "done"})

    with open(EPISODES_FILE, "w") as f:
        json.dump(episodes, f, indent=2)

    print(f"\nDone: {video_id} is fully processed and marked 'done' in {EPISODES_FILE}")


if __name__ == "__main__":
    process_manual_episode()