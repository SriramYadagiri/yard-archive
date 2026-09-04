"""
rerank.py — takes the top-N hybrid (vector + BM25) search hits and asks
an LLM to judge each candidate on structured signals, then does scoring,
sorting, and per-episode diversity filtering in Python.
"""

import json
import os
import re
import sys
from dotenv import load_dotenv
from openai import OpenAI

from hybrid_search import hybrid_search

load_dotenv()

CHAT_MODEL = "gpt-4o-mini"
CANDIDATE_K = 30
MAX_PER_EPISODE = 2
MIN_SCORE = 15

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def build_prompt(query, hits):
    candidates = []
    for i, hit in enumerate(hits):
        candidates.append({
            "index": i,
            "episode": hit["title"],
            "chapter": hit["chapter"],
            "speakers": hit["speakers"],
            "speaker_confidence": hit["speaker_confidence"],
            "text": hit["text"],
        })

    return f"""You are judging podcast transcript excerpts for a search query.

Query: "{query}"

Candidates:
{json.dumps(candidates, indent=2)}

Each candidate's text may include multiple speakers' lines in order, and
may be tagged with a chapter title in brackets if the episode has chapters.
Treat the chapter title as supporting context only -- base answers_query
and complete_moment on what the actual dialogue says, not on whether the
chapter title sounds topically related.

For EVERY candidate, judge these signals honestly:
- answers_query: how directly this excerpt addresses the query (0-10)
- person_match: if the query names/implies a specific person, how clearly
  that person is a speaker here (0-10; use 10 if the query names no one)
- complete_moment: whether this captures a full moment/exchange rather
  than a cut-off fragment (0-10)

Be skeptical of person_match when speaker_confidence is low, since the
speaker attribution itself may be wrong in that case.

Respond with ONLY a JSON array, one object per candidate, in this exact
shape (no prose, no markdown fences):
[
  {{"index": 0, "answers_query": 8, "person_match": 10, "complete_moment": 7}},
  ...
]"""


def remove_chapter_brackets(text):
    return re.sub(r'\[.*?\]', '', text, count=1).strip()


def score_candidate(judgment):
    return (
        judgment["answers_query"] * 2
        + judgment["person_match"] * 1.25
        + judgment["complete_moment"] * 0.75
    )


def rerank(query, min_score=MIN_SCORE, max_per_episode=MAX_PER_EPISODE, date_from=None, date_to=None):
    hits = hybrid_search(query, top_k=CANDIDATE_K, date_from=date_from, date_to=date_to)

    if not hits:
        return []

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": build_prompt(query, hits)}],
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        judgments = json.loads(raw)
    except json.JSONDecodeError:
        print(f"Warning: could not parse rerank response, falling back to raw order.\nRaw: {raw}")
        return hits[:5]

    scored = []
    for j in judgments:
        idx = j["index"]
        if 0 <= idx < len(hits):
            scored.append((score_candidate(j), hits[idx]))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    per_episode_count = {}
    final = []
    for score, hit in scored:
        if score < min_score:
            break
        count = per_episode_count.get(hit["video_id"], 0)
        if count >= max_per_episode:
            continue
        hit["relevance_score"] = round(score, 1)
        hit["text"] = remove_chapter_brackets(hit["text"])
        final.append(hit)
        per_episode_count[hit["video_id"]] = count + 1

    return final


if __name__ == "__main__":
    query = " ".join(sys.argv[1:])
    if not query:
        print("Usage: python rerank.py <your natural language query>")
        sys.exit(1)

    from search import print_results
    reranked = rerank(query)
    print(f"\n{len(reranked)} result(s) above the relevance threshold.")
    print_results(reranked)