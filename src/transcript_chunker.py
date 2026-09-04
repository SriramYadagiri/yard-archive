"""
transcript_chunker.py — turns a raw {video_id}.json transcript (Deepgram
utterances) into CHRONOLOGICAL conversation chunks tagged with chapter,
so embeddings capture back-and-forth banter and topic context.
"""

import json
import sys

MAX_WORDS = 110
PAUSE_SECONDS = 1.5


def words_to_text(words):
    return " ".join(w.get("punctuated_word", w["word"]) for w in words)


def avg_speaker_confidence(words):
    scores = [w["speaker_confidence"] for w in words if "speaker_confidence" in w]
    return round(sum(scores) / len(scores), 3) if scores else None


def split_long_utterance(words, max_words=MAX_WORDS, overlap=15):
    pieces = []
    i = 0
    n = len(words)
    while i < n:
        piece = words[i:i + max_words]
        pieces.append(piece)
        if i + max_words >= n:
            break
        i += max_words - overlap
    return pieces


def find_chapter(chapters, timestamp):
    """Return the title of the chapter containing this timestamp, or None
    if the episode has no chapters / timestamp falls outside all of them."""
    for chapter in chapters:
        if chapter["start"] <= timestamp < chapter["end"]:
            return chapter["title"]
    return None


def build_chunk_record(video_id, chunk_index, segments, chapters, published_ts=0):
    all_words = [w for _, words in segments for w in words]
    speakers = sorted({str(speaker) for speaker, _ in segments}, key=int)
    start = all_words[0]["start"]

    text_lines = [f"Speaker {speaker}: {words_to_text(words)}" for speaker, words in segments]
    chapter = find_chapter(chapters, start)

    text = "\n".join(text_lines)
    if chapter:
        text = f"[{chapter}]\n{text}"

    return {
        "chunk_id": f"{video_id}_{chunk_index:04d}",
        "video_id": video_id,
        "speakers": speakers,
        "chapter": chapter,
        "speaker_confidence": avg_speaker_confidence(all_words),
        "start": start,
        "end": all_words[-1]["end"],
        "text": text,
        "published_ts": published_ts,
    }


def chunk_transcript(video_id):
    with open(f"../data/transcripts/{video_id}.json") as f:
        data = json.load(f)

    utterances = data["utterances"]
    chapters = data.get("chapters") or []
    published_ts = data.get("published_ts") or 0

    chunks = []
    chunk_index = 0
    current_segments = []
    current_word_count = 0
    prev_end_time = None

    def flush_current():
        nonlocal current_segments, current_word_count, chunk_index
        if current_segments:
            chunks.append(build_chunk_record(video_id, chunk_index, current_segments, chapters, published_ts))
            chunk_index += 1
            current_segments = []
            current_word_count = 0

    for u in utterances:
        words = u.get("words", [])
        if not words:
            continue

        pause = (u["start"] - prev_end_time) if prev_end_time is not None else 0
        prev_end_time = u["end"]

        if len(words) > MAX_WORDS:
            flush_current()
            for piece in split_long_utterance(words):
                chunks.append(build_chunk_record(video_id, chunk_index, [(u["speaker"], piece)], chapters))
                chunk_index += 1
            continue

        would_exceed = current_word_count + len(words) > MAX_WORDS
        if current_segments and (pause >= PAUSE_SECONDS or would_exceed):
            flush_current()

        current_segments.append((u["speaker"], words))
        current_word_count += len(words)

    flush_current()

    output = {
        "video_id": video_id,
        "title": data.get("title"),
        "chunks": chunks,
    }

    with open(f"../data/transcripts/{video_id}_chunks.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"{video_id}: {len(utterances)} utterances -> {len(chunks)} conversation chunks")


if __name__ == "__main__":
    video_id = sys.argv[1]
    chunk_transcript(video_id)