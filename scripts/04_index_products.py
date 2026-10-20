"""Step 4: index the products: embed every doc_text and store the products in PostgreSQL (pgvector).

Run (the database and Ollama must be running, and the model downloaded: ollama pull bge-m3):
    python scripts/04_index_products.py

What it does:
  1. Reads data/corpus.parquet (made by step 3).
  2. Sends each product's doc_text to the embedding model bge-m3 in Ollama, in batches,
     and gets back a vector of 1024 numbers per product.
  3. Recreates the table `products` (the data model in docs/DATA.md plus the vector)
     and inserts all products. Running the script again replaces the table.
  4. Runs a few test searches and writes reports/index_summary.txt.

The vectors are stored with length 1, so the cosine similarity of two products is simply 1 - cosine distance
(pgvector operator <=>). There is no approximate vector index: with about 6,000 products an exact search
takes milliseconds and gives exact results.
"""
import json
import math
import time
import urllib.error
import urllib.request
from pathlib import Path

import duckdb
import psycopg
from pgvector.psycopg import register_vector

CORPUS = Path("data/corpus.parquet")
REPORT = Path("reports/index_summary.txt")

# Must match docker-compose.yml
DB = dict(host="localhost", port=15432, dbname="rag", user="rag", password="rag")

OLLAMA_URL = "http://localhost:11434/api/embed"
MODEL = "bge-m3"
DIMENSIONS = 1024
BATCH_SIZE = 32

# column name -> SQL type, in the order of docs/DATA.md
COLUMNS = {
    "ean": "text PRIMARY KEY",
    "name": "text NOT NULL",
    "brands": "text",
    "categories_tags": "text[] NOT NULL",
    "lang": "text",
    "url": "text NOT NULL",
    "energy_kcal_100g": "double precision",
    "fat_100g": "double precision",
    "saturated_fat_100g": "double precision",
    "carbohydrates_100g": "double precision",
    "sugars_100g": "double precision",
    "fiber_100g": "double precision",
    "proteins_100g": "double precision",
    "salt_100g": "double precision",
    "ingredients_text": "text NOT NULL",
    "allergens_eu": "text[] NOT NULL",
    "traces_eu": "text[] NOT NULL",
    "allergens_other": "text[] NOT NULL",
    "allergens_declared_none": "boolean NOT NULL",
    "doc_text": "text NOT NULL",
}
LIST_COLUMNS = {"categories_tags", "allergens_eu", "traces_eu", "allergens_other"}

TEST_QUERIES = ["ovesný nápoj", "oat drink", "hořká čokoláda"]


def embed(texts: list[str]) -> list[list[float]]:
    """Get one vector per text from Ollama, scaled to length 1."""
    body = json.dumps({"model": MODEL, "input": texts}).encode("utf-8")
    request = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            vectors = json.loads(response.read().decode("utf-8"))["embeddings"]
    except urllib.error.URLError as e:
        raise SystemExit(f"Cannot get embeddings from Ollama ({e}). Is Ollama running? Is the model "
                         f"downloaded (ollama pull {MODEL})?")
    result = []
    for v in vectors:
        if len(v) != DIMENSIONS:
            raise SystemExit(f"Expected {DIMENSIONS} numbers per vector, got {len(v)}.")
        length = math.sqrt(sum(x * x for x in v))
        result.append([x / length for x in v])
    return result


def connect() -> psycopg.Connection:
    try:
        conn = psycopg.connect(**DB, autocommit=True, connect_timeout=5)
    except psycopg.OperationalError as e:
        raise SystemExit(f"Cannot connect to the database ({e}). Start it with: docker compose up -d")
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)
    return conn


def main() -> None:
    conn = connect()  # fail early, before the slow part

    # 1) Read the corpus. DuckDB returns list columns as Python lists.
    #    Nutrients are stored as 32-bit FLOAT (7.6 becomes 7.5999999); rounding to 3 decimals restores 7.6.
    cols = list(COLUMNS)
    select = ", ".join(f"round({c}::DOUBLE, 3) AS {c}" if COLUMNS[c] == "double precision" else c for c in cols)
    rows = duckdb.sql(f"SELECT {select} FROM read_parquet('{CORPUS.as_posix()}') ORDER BY ean").fetchall()
    rows = [tuple((v or []) if c in LIST_COLUMNS else v for c, v in zip(cols, row)) for row in rows]
    texts = [row[cols.index("doc_text")] for row in rows]
    print(f"Read {len(rows):,} products from {CORPUS}")

    # 2) Embed in batches.
    start = time.perf_counter()
    vectors = []
    for i in range(0, len(texts), BATCH_SIZE):
        vectors += embed(texts[i:i + BATCH_SIZE])
        print(f"\r  embedded {len(vectors):,} / {len(texts):,}", end="", flush=True)
    embed_seconds = time.perf_counter() - start
    print(f"\nEmbedding took {embed_seconds:.0f} s ({len(texts) / embed_seconds:.1f} products per second)")

    # 3) Store. One transaction: either the whole table is replaced, or nothing changes.
    definitions = ",\n    ".join(f"{c} {t}" for c, t in COLUMNS.items())
    placeholders = ", ".join(["%s"] * (len(cols) + 1))
    with conn.transaction():
        conn.execute("DROP TABLE IF EXISTS products")
        conn.execute(f"CREATE TABLE products (\n    {definitions},\n    embedding vector({DIMENSIONS}) NOT NULL\n)")
        conn.execute("CREATE INDEX products_allergens_eu_idx ON products USING gin (allergens_eu)")
        conn.execute("CREATE INDEX products_traces_eu_idx ON products USING gin (traces_eu)")
        with conn.cursor() as cur:
            cur.executemany(
                f"INSERT INTO products ({', '.join(cols)}, embedding) VALUES ({placeholders})",
                [(*row, vector) for row, vector in zip(rows, vectors)],
            )
    stored = conn.execute("SELECT count(*) FROM products").fetchone()[0]
    print(f"Stored {stored:,} products in table 'products'")

    # 4) Test searches: rank all products by similarity (1 - cosine distance).
    lines = [
        f"Embedding model: {MODEL} via Ollama ({DIMENSIONS} numbers per product)",
        f"Products stored: {stored:,}",
        f"Embedding time: {embed_seconds:.0f} s",
        "",
        "Test searches, vector only (similarity: higher = closer in meaning):",
    ]
    for query, query_vector in zip(TEST_QUERIES, embed(TEST_QUERIES)):
        hits = conn.execute(
            "SELECT name, brands, 1 - (embedding <=> %s::vector) AS similarity "
            "FROM products ORDER BY embedding <=> %s::vector LIMIT 3",
            (query_vector, query_vector),
        ).fetchall()
        lines.append(f"\nQuery: {query}")
        lines += [f"  {s:.3f}  {n} ({b or 'no brand'})" for n, b, s in hits]

    text = "\n".join(lines)
    REPORT.write_text(text + "\n", encoding="utf-8")
    print("\n" + text)


if __name__ == "__main__":
    main()
