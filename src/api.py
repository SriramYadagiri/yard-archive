"""
api.py — thin FastAPI wrapper around rerank.rerank(), hardened for
public deployment: locked-down CORS, per-IP rate limiting, and basic
input validation, since every request costs real OpenAI API money.
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from rerank import rerank

# Comma-separated list of allowed frontend origins, set via an env var on
# the host (e.g. "https://your-app.vercel.app"). Defaults to localhost for
# local dev so you don't have to set this while developing.
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

MAX_QUERY_LENGTH = 300

limiter = Limiter(key_func=get_remote_address)

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["POST"],
    allow_headers=["*"],
)

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
BM25_INDEX_FILE = Path(
    os.getenv("BM25_INDEX_FILE", Path(__file__).resolve().parent / "bm25_index.pkl")
)


@app.get("/health")
def health():
    required_paths = [
        DATA_DIR / "chroma",
        DATA_DIR / "transcripts",
        BM25_INDEX_FILE,
    ]
    ready = all(path.exists() for path in required_paths)
    return {"status": "ok" if ready else "starting", "data_ready": ready}


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=MAX_QUERY_LENGTH)
    date_from: Optional[str] = None  # "YYYY-MM-DD"
    date_to: Optional[str] = None    # "YYYY-MM-DD"


@app.post("/search")
@limiter.limit("10/minute")
def search_endpoint(request: Request, req: SearchRequest):
    results = rerank(req.query, date_from=req.date_from, date_to=req.date_to)
    return {"results": results}


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception):
    # Don't leak internal error details (stack traces, file paths) to
    # public callers -- log server-side, return a generic message.
    print(f"Unhandled error: {exc}")
    return JSONResponse(status_code=500, content={"error": "Something went wrong."})
