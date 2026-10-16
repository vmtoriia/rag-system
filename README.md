# RAG with contextual memory (semester project, B261)

Prototype of a semantic search + Retrieval-Augmented Generation (RAG) system with
**short-term** (conversation) and **long-term** (user profile) memory.
Corpus: Open Food Facts, Czech market. Research question: how do different memory variants
affect anaphora resolution and personalisation?

## Planned experiment
Four memory configurations: (0) none, (1) short-term only, (2) long-term only, (3) both.
The same set of test dialogues is run through each configuration.

## Data pipeline (implemented)
Run in this order from the project root. On Windows use `.venv\Scripts\python.exe` instead of `python`.

| Step | Script | Input -> Output |
|---|---|---|
| 1 | `scripts/01_explore_data.py` | `data/food.parquet` -> `reports/` (schema, countries, fill rates) |
| 2 | `scripts/02_prepare_corpus.py` | `data/food.parquet` -> `data/products_clean.parquet`, `reports/filter_funnel.csv` |
| 3 | `scripts/03_enrich_corpus.py` | `data/products_clean.parquet` -> `data/corpus.parquet`, `reports/corpus_enrichment.txt` |
| 3b | `scripts/02b_language_check.py` | `data/corpus.parquet` -> `reports/language_distribution.csv` |

Details, decisions and licence: see [`docs/DATA.md`](docs/DATA.md).

## Setup
    python -m venv .venv                      (Windows: py -m venv .venv)
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    # download food.parquet into data/ (see docs/DATA.md)

## Layout
    scripts/   data preparation scripts
    reports/   numbers produced by the scripts (used in the written report)
    docs/      data description
    data/      large files (not in git)

Data: Open Food Facts, ODbL (attribution required, see docs/DATA.md).