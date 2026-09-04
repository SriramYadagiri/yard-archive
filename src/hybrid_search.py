"""
hybrid_search.py — combines vector search (search.py) and keyword search
(bm25_search.py) via Reciprocal Rank Fusion (RRF), so exact-term queries
(proper nouns, slang, specific game/brand names) get picked up by BM25
even when the embedding alone might under-rank them, while semantic or
paraphrased queries still work via vector search.

RRF avoids needing to normalize BM25 scores (unbounded, corpus-dependent)
against cosine distances (bounded, different scale) -- it only uses each
hit's RANK within its own list, not its raw score, sidestepping that
normalization problem entirely. RRF_K=60 is the standard constant from
the original RRF paper; it's rarely worth tuning.
"""

from search import search
from bm25_search import bm25_search

RRF_K = 60


def hybrid_search(query, top_k=40, date_from=None, date_to=None, per_method_k=40):
    vector_hits = search(query, top_k=per_method_k, date_from=date_from, date_to=date_to)
    keyword_hits = bm25_search(query, top_k=per_method_k, date_from=date_from, date_to=date_to)

    scores = {}
    hit_lookup = {}

    for rank, hit in enumerate(vector_hits):
        scores[hit["chunk_id"]] = scores.get(hit["chunk_id"], 0) + 1 / (RRF_K + rank + 1)
        hit_lookup[hit["chunk_id"]] = hit

    for rank, hit in enumerate(keyword_hits):
        scores[hit["chunk_id"]] = scores.get(hit["chunk_id"], 0) + 1 / (RRF_K + rank + 1)
        hit_lookup.setdefault(hit["chunk_id"], hit)

    ranked_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    return [hit_lookup[cid] for cid in ranked_ids[:top_k]]