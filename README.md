# Yard Search

A semantic and keyword search engine for moments from [The Yard](https://www.youtube.com/@TheYardPodcast) podcast. Search results include transcript excerpts, speaker attribution, episode metadata, relevance scores, and timestamped YouTube links.

This is an independent fan project and is not affiliated with The Yard.

## How it works

1. Podcast audio is downloaded and transcribed with Deepgram.
2. Transcripts are split into searchable chunks and embedded with OpenAI.
3. Semantic results from ChromaDB and keyword results from BM25 are combined using Reciprocal Rank Fusion.
4. An OpenAI model reranks the strongest candidates for relevance and completeness.
5. A FastAPI service returns the results to the React frontend.

## Tech stack

- React 18 and Vite
- FastAPI and Uvicorn
- ChromaDB for vector search
- `rank-bm25` for keyword search
- OpenAI embeddings and result reranking
- Deepgram transcription

## Repository layout

```text
frontend/                 React search interface
src/api.py                FastAPI HTTP API
src/search.py             ChromaDB vector search
src/bm25_search.py        BM25 keyword search
src/hybrid_search.py      Reciprocal Rank Fusion
src/rerank.py             LLM-based candidate reranking
src/pipeline*.py          Download and transcription pipeline
src/transcript_chunker.py Transcript chunk generation
src/stats_generator.py    Speaker statistics generator
data/speaker_stats.json   Generated aggregate speaker statistics
```

## Prerequisites

- Python 3.11 or newer
- Node.js 18 or newer
- FFmpeg if you plan to download and process new episodes
- An OpenAI API key
- A Deepgram API key if you plan to transcribe new episodes

The search corpus is not stored in Git because it is too large. To run search locally, you need these generated artifacts:

```text
data/chroma/              ChromaDB vector index
data/transcripts/         Transcript and chunk JSON files
src/bm25_index.pkl        BM25 index
```

## Local setup

Clone the repository and install the backend dependencies:

```bash
git clone https://github.com/SriramYadagiri/yard-archive.git
cd yard-archive
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `src/.env`:

```dotenv
OPENAI_API_KEY=your_openai_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key
```

Install the frontend dependencies:

```bash
cd frontend
npm install
```

## Run locally

Start the API from the `src` directory so its relative data paths resolve correctly:

```bash
cd src
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

In a second terminal, start the frontend:

```bash
cd frontend
npm run dev
```

Open <http://localhost:5173>. The frontend sends search requests to `http://localhost:8000/search`.

The API accepts requests in this form:

```json
{
  "query": "Slime talking about airports",
  "date_from": "2021-07-01",
  "date_to": "2026-12-31"
}
```

## Build the search data

The scripts in `src/` use paths relative to that directory. Run pipeline commands from `src` unless a command below says otherwise.

After adding or updating transcript files, generate chunks, embeddings, and the BM25 index:

```bash
cd src
python chunk_all.py
python embed_all.py
python build_bm25_index.py
```

Generate aggregate speaker statistics from the repository root:

```bash
python src/stats_generator.py
```

Generated indexes, transcripts, downloaded audio, environment files, and browser session cookies are intentionally excluded from Git.

## Production build

Build the frontend with:

```bash
cd frontend
npm run build
```

The repository includes a Render Blueprint that creates a static frontend and a FastAPI web service. The API uses a persistent disk because the search corpus is too large for Git and Render's normal filesystem is ephemeral.

First, create a gzip-compressed archive with this layout:

```text
chroma/
transcripts/
bm25_index.pkl
```

From the repository root, the following command creates it from the local search data:

```bash
tar -czf yard-search-data.tar.gz \
  -C data chroma transcripts \
  -C ../src bm25_index.pkl
```

Upload the archive to private object storage and create a download URL. Then create a new Blueprint in Render from this repository and provide these values when prompted:

- `OPENAI_API_KEY`
- `DATA_ARCHIVE_URL` — a private or signed URL for `yard-search-data.tar.gz`
- `ALLOWED_ORIGINS` — the frontend origin, such as `https://yard-search.onrender.com`
- `VITE_API_URL` — the full search endpoint, such as `https://yard-search-api.onrender.com/search`

On its first boot, the API streams the archive directly into `/var/data`. Later deploys reuse the restored corpus on the persistent disk.

## Notes

- Search requests are limited to 10 per minute per IP.
- Query text is limited to 300 characters.
- The frontend stores recent search metadata in local storage and result payloads in per-tab session storage.
