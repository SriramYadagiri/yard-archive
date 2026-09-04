import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_SPEAKERS = ["Ludwig", "Nick", "Aiden", "Slime"]
STOP_WORDS = {
    # Articles
    "a", "an", "the",

    # Pronouns
    "i", "me", "my", "mine",
    "you", "your", "yours",
    "he", "him", "his",
    "she", "her", "hers",
    "it", "its",
    "we", "us", "our", "ours",
    "they", "them", "their", "theirs",

    # Demonstratives
    "this", "that", "these", "those",

    # Conjunctions
    "and", "or", "but", "so", "because", "if", "then",

    # Prepositions
    "to", "of", "in", "on", "at", "for", "with",
    "from", "by", "as", "into", "about", "over",
    "after", "before", "through", "between", "during",

    # Auxiliary / common verbs
    "is", "are", "was", "were", "be", "been", "being",
    "am", "do", "does", "did", "doing",
    "have", "has", "had",
    "can", "could", "will", "would",
    "should", "may", "might", "must",

    # Common contractions after normalization
    "im", "ive", "id", "ill",
    "youre", "youve", "youll",
    "were", "weve", "well",
    "theyre", "theyve", "theyll",
    "thats", "theres", "heres",

    # Fillers common in podcasts
    "like", "yeah", "yes", "no",
    "uh", "um", "huh", "ah", "oh",
    "okay", "ok", "right",
    "well", "just", "really",
    "actually", "basically",
    "literally", "kind", "sort",
    "gonna", "wanna", "gotta",

    # Misc
    "not", "dont", "didnt", "cant",
    "couldnt", "wouldnt", "shouldnt",
}

def normalize_speaker_name(value: Optional[object]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        return cleaned.capitalize() if cleaned.lower() in {"ludwig", "nick", "aiden", "slime"} else cleaned
    return str(value)


def resolve_speaker_name(speaker_id: Optional[object], speaker_map: Optional[Dict[str, str]]) -> Optional[str]:
    if speaker_id is None:
        return None
    if isinstance(speaker_id, str):
        speaker_id = speaker_id.strip()
    if speaker_map is None:
        speaker_map = {}

    if speaker_id in speaker_map:
        return normalize_speaker_name(speaker_map[speaker_id])

    if isinstance(speaker_id, int):
        return normalize_speaker_name(speaker_map.get(str(speaker_id)))

    normalized = normalize_speaker_name(speaker_id)
    if normalized in DEFAULT_SPEAKERS:
        return normalized
    return None


def normalize_word(word: Optional[str]) -> Optional[str]:
    if not word:
        return None
    cleaned = re.sub(r"[^a-z0-9]+", "", word.lower())
    if not cleaned:
        return None
    if cleaned in STOP_WORDS:
        return None
    return cleaned


def build_speaker_stats(transcripts: List[Dict], speakers: Optional[List[str]] = None) -> Dict:
    if speakers is None:
        speakers = DEFAULT_SPEAKERS

    speaker_set = set(speakers)
    episode_stats: List[Dict] = []
    episodes_by_id: Dict[str, Dict] = {}
    overall_counters: Dict[str, Counter] = {speaker: Counter() for speaker in speaker_set}
    overall_word_counts: Dict[str, int] = {speaker: 0 for speaker in speaker_set}

    for transcript in transcripts:
        episode_word_counts = {speaker: 0 for speaker in speaker_set}
        episode_top_words: Dict[str, Counter] = {speaker: Counter() for speaker in speaker_set}

        speaker_map = transcript.get("speaker_map", {}) or {}
        for utterance in transcript.get("utterances", []) or []:
            for word_info in utterance.get("words", []) or []:
                speaker_name = resolve_speaker_name(word_info.get("speaker"), speaker_map)
                if speaker_name is None:
                    speaker_name = resolve_speaker_name(utterance.get("channel"), speaker_map)
                if speaker_name not in speaker_set:
                    continue

                raw_word = word_info.get("word") or word_info.get("punctuated_word")
                if raw_word is None:
                    continue

                episode_word_counts[speaker_name] += 1
                overall_word_counts[speaker_name] += 1

                token = normalize_word(raw_word)
                if token is None:
                    continue

                episode_top_words[speaker_name][token] += 1
                overall_counters[speaker_name][token] += 1

        present_speakers = {
            speaker: count
            for speaker, count in episode_word_counts.items()
            if count > 0
        }

        episode_summary = {
            "video_id": transcript.get("video_id"),
            "title": transcript.get("title"),
            "speaker_word_counts": present_speakers,
            "speaker_top_words": {
                speaker: top_words_for_counter(episode_top_words[speaker]) for speaker in present_speakers
            },
        }
        episode_stats.append(episode_summary)

        episode_id = transcript.get("video_id") or transcript.get("id")
        if episode_id is not None:
            episodes_by_id[str(episode_id)] = {
                "name": transcript.get("title"),
                "speaker_word_counts": present_speakers,
            }

    overall_summary = {
        speaker: {
            "word_count": overall_word_counts[speaker],
            "top_words": top_words_for_counter(overall_counters[speaker]),
        }
        for speaker in speaker_set
    }

    return {"episodes": episode_stats, "episodes_by_id": episodes_by_id, "overall": overall_summary}


def top_words_for_counter(counter: Counter, limit: int = 10) -> List[Dict[str, object]]:
    return [
        {"word": word, "count": count}
        for word, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def load_transcripts(data_dir: Path) -> List[Dict]:
    transcripts: List[Dict] = []
    for path in sorted(data_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            transcripts.append(json.load(handle))
    return transcripts


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate word-count stats for selected speakers across podcast episodes")
    parser.add_argument("--transcripts-dir", default="data/transcripts", help="Directory containing transcript JSON files")
    parser.add_argument("--output", default="data/speaker_stats.json", help="Where to save the generated JSON summary")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parents[1]
    transcripts_dir = Path(args.transcripts_dir)
    if not transcripts_dir.is_absolute():
        transcripts_dir = base_dir / transcripts_dir

    transcripts = load_transcripts(transcripts_dir)
    stats = build_speaker_stats(transcripts, speakers=DEFAULT_SPEAKERS)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = base_dir / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")


    with open("stats.json", "w") as f:
        json.dump(stats, f)


    print(json.dumps(stats["overall"], indent=2))
    print(json.dumps(stats["episodes_by_id"], indent=2))


if __name__ == "__main__":
    main()
