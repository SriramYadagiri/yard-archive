"""
auto_label_speakers.py — automatically suggests a speaker_map for a new
(unlabeled) episode by comparing each diarized speaker id's voice against
your reference voiceprints.
"""

import json
import sys
import numpy as np
from resemblyzer import VoiceEncoder

from build_speaker_references import find_clip_windows, extract_clip_embedding

MATCH_THRESHOLD = 0.75  # cosine similarity below this = treat as unidentified/guest

encoder = VoiceEncoder()


def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def auto_label(video_id):
    with open("speaker_references.json") as f:
        references = json.load(f)

    transcript_path = f"../data/transcripts/{video_id}.json"
    audio_path = f"../data/audio/{video_id}.mp3"

    with open(transcript_path) as f:
        data = json.load(f)

    words_by_speaker = {}
    for u in data["utterances"]:
        words_by_speaker.setdefault(u["speaker"], []).extend(u.get("words", []))

    suggested_map = {}
    review_notes = {}

    for speaker_id, words in words_by_speaker.items():
        windows = find_clip_windows(words)[:3]
        if not windows:
            suggested_map[str(speaker_id)] = "unidentified"
            review_notes[str(speaker_id)] = "no high-confidence clip found -- needs manual review"
            continue

        embeddings = []
        for start, end in windows:
            try:
                embeddings.append(extract_clip_embedding(audio_path, start, end))
            except Exception:
                continue

        if not embeddings:
            suggested_map[str(speaker_id)] = "unidentified"
            review_notes[str(speaker_id)] = "clip extraction failed -- needs manual review"
            continue

        speaker_embedding = np.mean(embeddings, axis=0)
        scores = {name: cosine_similarity(speaker_embedding, ref) for name, ref in references.items()}
        best_name = max(scores, key=scores.get)
        best_score = scores[best_name]

        if best_score >= MATCH_THRESHOLD:
            suggested_map[str(speaker_id)] = best_name
            review_notes[str(speaker_id)] = f"matched {best_name} (similarity={best_score:.2f})"
        else:
            suggested_map[str(speaker_id)] = "unidentified"
            review_notes[str(speaker_id)] = f"best guess {best_name} but low similarity ({best_score:.2f}) -- likely a guest, please review"

    data["speaker_map"] = suggested_map
    data["speaker_map_review_notes"] = review_notes

    with open(transcript_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n{video_id} suggested speaker_map:")
    for speaker_id, name in suggested_map.items():
        print(f"  Speaker {speaker_id} -> {name}   ({review_notes[speaker_id]})")


if __name__ == "__main__":
    auto_label(sys.argv[1])