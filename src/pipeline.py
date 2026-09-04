"""
pipeline.py — reusable download/transcribe functions shared by batch.py
and pipeline_all.py.
"""

import json
import os
from datetime import datetime
from dotenv import load_dotenv
import yt_dlp
from deepgram import DeepgramClient

load_dotenv()
client = DeepgramClient(api_key=os.getenv("DEEPGRAM_API_KEY"))


def download_episode(url):
    options = {
        "format": "bestaudio/best",
        "outtmpl": "../data/audio/%(id)s.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
        }],
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)

    video_id = info["id"]

    chapters = [
        {"start": c["start_time"], "end": c["end_time"], "title": c["title"]}
        for c in info.get("chapters") or []
    ]

    # yt-dlp gives upload_date as "YYYYMMDD" -- convert to both a unix
    # timestamp (for numeric range filtering in ChromaDB, which only
    # supports numeric comparisons in `where` clauses) and an ISO date
    # string (for human-readable display).
    upload_date_str = info.get("upload_date")
    if upload_date_str:
        dt = datetime.strptime(upload_date_str, "%Y%m%d")
        published_ts = int(dt.timestamp())
        published_date = dt.strftime("%Y-%m-%d")
    else:
        published_ts = None
        published_date = "2024-02-29"

    metadata = {
        "video_id": video_id,
        "title": info["title"],
        "duration": info["duration"],
        "url": url,
        "chapters": chapters,
        "published_ts": published_ts,
        "published_date": published_date,
    }
    with open(f"../data/transcripts/{video_id}_meta.json", "w") as f:
        json.dump(metadata, f, indent=2)

    return video_id


def transcribe_episode(video_id):
    with open(f"../data/audio/{video_id}.mp3", "rb") as audio:
        response = client.listen.v1.media.transcribe_file(
            request=audio.read(),
            model="nova-3",
            smart_format=True,
            diarize=True,
            utterances=True,
            request_options={"timeout_in_seconds": 300, "max_retries": 3},
        )

    result = response.model_dump()

    with open(f"../data/transcripts/{video_id}_meta.json") as f:
        meta = json.load(f)

    output = {
        **meta,
        "speaker_map": {},
        "utterances": result["results"]["utterances"],
    }
    with open(f"../data/transcripts/{video_id}.json", "w") as f:
        json.dump(output, f, indent=2)