# Food RAG: answering questions about food composition and allergens

Semester project B261, Czech Technical University in Prague, Faculty of Electrical Engineering.
Topic: *Prototyp systému RAG pro analýzu složení potravin a alergenů s využitím databáze Open Food Facts*.
Supervisor: Ing. Ondřej Kuželka, Ph.D.

A prototype that answers questions about food composition, allergens and nutrition using
Retrieval-Augmented Generation (RAG) over a subset of the Open Food Facts database. It combines semantic
search with deterministic filters on structured data, cites the products every answer is based on, and keeps
declared allergens, possible traces and missing information apart.

## Stack
Java 21, Spring Boot, Spring AI, PostgreSQL with pgvector, Ollama (local models), Docker Compose.
Data preparation and indexing in Python with DuckDB.

## Status

| Part | Status |
|---|---|
| Data selection, cleaning and data model ([`docs/DATA.md`](docs/DATA.md)) | Done: 5,888 Czech products |
| Architecture ([`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)) | Designed |
| Database (PostgreSQL + pgvector, `docker-compose.yml`) | Set up |
| Indexing: products and `bge-m3` vectors in the database (`scripts/04_index_products.py`) | Done |
| Backend: REST API, vector and hybrid search, filters, grounded answers, logging | Planned |
| Evaluation: 15+ test queries, precision@k, latency, vector vs hybrid | Planned |

## Data pipeline
Run in this order from the project root. On Windows use `.venv\Scripts\python.exe` instead of `python`.

| Step | Script | Reads | Writes |
|---|---|---|---|
| 1 | `scripts/01_explore_data.py` | `data/food.parquet` | `reports/schema.txt`, `countries.csv`, `fill_rates.csv` |
| 2 | `scripts/02_prepare_corpus.py` | `data/food.parquet` | `data/products_clean.parquet`, `reports/filter_funnel.csv`, `corpus_summary.txt` |
| 3 | `scripts/03_enrich_corpus.py` | `data/products_clean.parquet` | `data/corpus.parquet`, `reports/corpus_enrichment.txt` |
| 3b | `scripts/03b_language_check.py` | `data/corpus.parquet` | `reports/language_distribution.csv` |
| 4 | `scripts/04_index_products.py` | `data/corpus.parquet`, Ollama `bge-m3` | table `products` in PostgreSQL, `reports/index_summary.txt` |

Step 1 only measures the raw data. Step 2 selects Czech products and applies quality filters.
Step 3 cleans the text and allergen tags and builds `doc_text`, the text that will be embedded.
Step 3b counts languages. Step 4 embeds every product and stores it in the database (needs Docker and Ollama running).

## Tools
| Tool | What it does |
|---|---|
| `tools/view_corpus.py` | Builds `data/corpus_view.html`, a page to search the corpus and try allergen filters |
| `tools/embedding_demo.py` | Embeds a few texts with the Ollama model `bge-m3` and prints their cosine similarities |

## Setup
    python -m venv .venv                      (Windows: py -m venv .venv)
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    # download food.parquet into data/ (see docs/DATA.md), then run the data pipeline
    docker compose up -d                      (starts PostgreSQL with pgvector on port 15432)
    # install Ollama (https://ollama.com), then:
    ollama pull bge-m3                        (embedding model)
    ollama pull qwen2.5:3b                    (chat model, used by the backend)
    .venv\Scripts\python.exe scripts\04_index_products.py

## Layout
    scripts/   data pipeline, numbered in the order they run
    tools/     helpers for looking at the data
    reports/   numbers produced by the scripts (used in the written report)
    docs/      data description (DATA.md) and architecture (ARCHITECTURE.md)
    data/      large files (not in git)

Data: Open Food Facts, ODbL (attribution required, see docs/DATA.md).
