# RAG with contextual memory (semester project, B261)

Prototype of a semantic search + Retrieval-Augmented Generation (RAG) system with
**short-term** (conversation) and **long-term** (user profile) memory.
Corpus: Open Food Facts, Czech market. Research question: how do different memory variants
affect anaphora resolution and personalisation?

## Planned experiment
Four memory configurations: (0) none, (1) short-term only, (2) long-term only, (3) both.
The same set of test dialogues is run through each configuration.

## Status
- Done: data pipeline (steps 1-3b), corpus of 5,888 products, documented in [`docs/DATA.md`](docs/DATA.md).
- Designed: system architecture (C4 model), see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
- Next: embeddings and vector database, then search without memory (configuration 0).

## Data pipeline
Run in this order from the project root. On Windows use `.venv\Scripts\python.exe` instead of `python`.

| Step | Script | Reads | Writes |
|---|---|---|---|
| 1 | `scripts/01_explore_data.py` | `data/food.parquet` | `reports/schema.txt`, `countries.csv`, `fill_rates.csv` |
| 2 | `scripts/02_prepare_corpus.py` | `data/food.parquet` | `data/products_clean.parquet`, `reports/filter_funnel.csv`, `corpus_summary.txt` |
| 3 | `scripts/03_enrich_corpus.py` | `data/products_clean.parquet` | `data/corpus.parquet`, `reports/corpus_enrichment.txt` |
| 3b | `scripts/03b_language_check.py` | `data/corpus.parquet` | `reports/language_distribution.csv` |

Step 1 only measures the raw data. Step 2 selects Czech products and applies quality filters.
Step 3 cleans the text and allergen tags and builds `doc_text`, the text that will be embedded.
Step 3b counts languages. Details, decisions and licence: see [`docs/DATA.md`](docs/DATA.md).

## Tools
Helpers for looking at the data; they change nothing.

| Tool | What it does |
|---|---|
| `tools/view_corpus.py` | Builds `data/corpus_view.html`, a page to search the corpus and try the allergy filter. |

## Setup
    python -m venv .venv                      (Windows: py -m venv .venv)
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    # download food.parquet into data/ (see docs/DATA.md)

## Layout
    scripts/   data pipeline, numbered in the order they run
    tools/     helpers for looking at the data
    reports/   numbers produced by the scripts (used in the written report)
    docs/      data description (DATA.md) and architecture (ARCHITECTURE.md)
    data/      large files (not in git)

Data: Open Food Facts, ODbL (attribution required, see docs/DATA.md).
