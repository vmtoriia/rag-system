"""How many products are in which language? (uses the product's main-language code from Open Food Facts)

Run:  python scripts/02b_language_check.py
Writes reports/language_distribution.csv (a table for the report).
"""
import argparse
from pathlib import Path

import duckdb

ap = argparse.ArgumentParser()
ap.add_argument("--inp", default="data/corpus.parquet")
ap.add_argument("--reports", default="reports")
args = ap.parse_args()

Path(args.reports).mkdir(exist_ok=True)
df = duckdb.sql(f"""
    SELECT lang, count(*) AS products,
           round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS percent
    FROM read_parquet('{args.inp}')
    GROUP BY lang ORDER BY products DESC
""").df()
df.to_csv(Path(args.reports) / "language_distribution.csv", index=False)
print(df.head(10).to_string(index=False))
print(f"\n({len(df)} distinct language codes in total; full table in reports/language_distribution.csv)")