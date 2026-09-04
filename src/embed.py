"""
embed.py — embeds chunked transcript text with OpenAI's embedding API
and stores the vectors + metadata in a local ChromaDB collection.
"""

import json
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI
import chromadb

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
chroma_client = chromadb.PersistentClient(path="../data/chroma")
collection = chroma_client.get_or_create_collection("yard_transcripts")


def embed_texts(texts):
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


def store_chunks(chunks, vectors):
    """published_ts is stored as a plain int so ChromaDB's `where` clause
    can do numeric range filtering ($gte/$lte) for date-range search."""
    collection.upsert(
        ids=[c["chunk_id"] for c in chunks],
        embeddings=vectors,
        documents=[c["text"] for c in chunks],
        metadatas=[
            {
                "video_id": c["video_id"],
                "speakers": json.dumps(c["speakers"]),
                "chapter": c.get("chapter") or "",
                "published_ts": c.get("published_ts") or 0,
                "speaker_confidence": c.get("speaker_confidence") or 0.0,
                "start": c["start"],
                "end": c["end"],
            }
            for c in chunks
        ],
    )


def embed_episode(video_id):
    with open(f"../data/transcripts/{video_id}_chunks.json") as f:
        data = json.load(f)

    chunks = data["chunks"]
    total_embedded = 0

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        texts = [c["text"] for c in batch]
        vectors = embed_texts(texts)
        store_chunks(batch, vectors)
        total_embedded += len(batch)

    print(f"{video_id}: embedded {total_embedded} chunks")


if __name__ == "__main__":
    video_id = sys.argv[1]
    embed_episode(video_id)