"""
build_speaker_references.py — builds a reference voiceprint per named host,
using 5 manually-labeled episodes as training data.
"""

import json
import numpy as np
from pathlib import Path
from pydub import AudioSegment
from resemblyzer import VoiceEncoder, preprocess_wav

CLIPS_PER_SPEAKER_PER_EPISODE = 4
MIN_CLIP_SECONDS = 2.0
CONFIDENCE_THRESHOLD = 0.85

encoder = VoiceEncoder()


def find_clip_windows(words, min_seconds=MIN_CLIP_SECONDS, confidence_threshold=CONFIDENCE_THRESHOLD):
    """Scan a speaker's words for continuous high-confidence runs at least
    min_seconds long -- these are the safest slices to use as reference audio."""
    windows = []
    run_start = None
    run_start_time = None
    prev_end_time = None

    for w in words:
        if w.get("speaker_confidence", 0) >= confidence_threshold:
            if run_start is None:
                run_start = w
                run_start_time = w["start"]
        else:
            if run_start is not None and prev_end_time - run_start_time >= min_seconds:
                windows.append((run_start_time, prev_end_time))
            run_start = None
        prev_end_time = w["end"]

    if run_start is not None and prev_end_time - run_start_time >= min_seconds:
        windows.append((run_start_time, prev_end_time))

    return windows


def extract_clip_embedding(audio_path, start, end):
    audio = AudioSegment.from_mp3(audio_path)
    clip = audio[start * 1000: end * 1000]
    clip_path = "/tmp/_ref_clip.wav"
    clip.export(clip_path, format="wav")
    wav = preprocess_wav(clip_path)
    return encoder.embed_utterance(wav)


def build_references():
    with open("episodes.json") as f:
        episodes = json.load(f)

    labeled = [e for e in episodes if e["status"] == "done"]
    host_embeddings = {}

    for ep in labeled:
        video_id = ep["video_id"]
        transcript_path = f"../data/transcripts/{video_id}.json"
        audio_path = f"../data/audio/{video_id}.mp3"

        if not Path(transcript_path).exists():
            continue

        with open(transcript_path) as f:
            data = json.load(f)

        speaker_map = data.get("speaker_map", {})
        if not speaker_map:
            continue

        words_by_speaker = {}
        for u in data["utterances"]:
            words_by_speaker.setdefault(u["speaker"], []).extend(u.get("words", []))

        for speaker_id, words in words_by_speaker.items():
            name = speaker_map.get(str(speaker_id))
            if not name or name.startswith("guest:"):
                continue

            windows = find_clip_windows(words)[:CLIPS_PER_SPEAKER_PER_EPISODE]
            for start, end in windows:
                try:
                    embedding = extract_clip_embedding(audio_path, start, end)
                    host_embeddings.setdefault(name, []).append(embedding)
                except Exception as e:
                    print(f"  skipped clip {video_id} {start}-{end}: {e}")

    references = {
        name: np.mean(embeddings, axis=0).tolist()
        for name, embeddings in host_embeddings.items()
    }

    with open("speaker_references.json", "w") as f:
        json.dump(references, f)

    for name, embeddings in host_embeddings.items():
        print(f"{name}: built reference from {len(embeddings)} clips")


if __name__ == "__main__":
    build_references()