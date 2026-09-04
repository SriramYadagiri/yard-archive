FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/var/data \
    BM25_INDEX_FILE=/var/data/bm25_index.pkl \
    PORT=8000

WORKDIR /app

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY src ./src

EXPOSE 8000

CMD ["sh", "-c", "python src/ensure_data.py && cd src && uvicorn api:app --host 0.0.0.0 --port ${PORT}"]
