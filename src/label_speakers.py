"""
label_speakers.py — prints sample lines per speaker id for one episode,
to make it fast to fill in that episode's speaker_map by hand.

Samples are filtered to high speaker_confidence words only, since
low-confidence attributions are the ones most likely to be misdiarized
(usually clustered at speaker-turn boundaries / crosstalk). This should
give a cleaner, more trustworthy picture of who each speaker id actually
is, versus raw utterance sampling which inherits diarization's mistakes.

Each sample includes a timestamp so you can jump to the audio/video and
confirm by ear if a line still looks wrong.

Usage: python label_speakers.py <video_id>
Then manually edit ../data/transcripts/{video_id}.json's "speaker_map"
field, e.g.: {"0": "Ludwig", "1": "Slime", "2": "guest:some_name"}
"""

import json
import sys
from collections import defaultdict

SAMPLES_PER_SPEAKER = 6
CONFIDENCE_THRESHOLD = 0.8


def label_speakers(video_id):
    with open(f"../data/transcripts/{video_id}.json") as f:
        data = json.load(f)

    by_speaker = defaultdict(list)
    skipped_low_confidence = 0

    for u in data["utterances"]:
        # use word-level confidence rather than the whole utterance, since
        # a single utterance can straddle a genuine speaker change
        words = u.get("words", [])
        high_conf_words = [w for w in words if w.get("speaker_confidence", 0) >= CONFIDENCE_THRESHOLD]

        if not high_conf_words:
            skipped_low_confidence += 1
            continue

        if len(by_speaker[u["speaker"]]) < SAMPLES_PER_SPEAKER:
            snippet = " ".join(w.get("punctuated_word", w["word"]) for w in high_conf_words)
            avg_conf = sum(w["speaker_confidence"] for w in high_conf_words) / len(high_conf_words)
            by_speaker[u["speaker"]].append({
                "text": snippet,
                "start": u["start"],
                "confidence": round(avg_conf, 3),
            })

    for speaker_id in sorted(by_speaker):
        print(f"\n--- Speaker {speaker_id} ---")
        for sample in by_speaker[speaker_id]:
            print(f"  [{sample['start']:.1f}s, conf={sample['confidence']:.2f}] \"{sample['text']}\"")

    if skipped_low_confidence:
        print(f"\n({skipped_low_confidence} utterances skipped -- all words below {CONFIDENCE_THRESHOLD} confidence)")

    print(f"\nEdit ../data/transcripts/{video_id}.json -> \"speaker_map\" with your labels.")
    print("Example: {\"0\": \"Ludwig\", \"1\": \"Slime\", \"2\": \"guest:jane_doe\"}")
    print("Tip: if a speaker id's samples still sound like more than one person,")
    print("jump to the printed timestamps in the actual video to confirm by ear --")
    print("that id may be merging two people due to diarization error.")


if __name__ == "__main__":
    label_speakers(sys.argv[1])