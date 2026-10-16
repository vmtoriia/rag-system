"""Step 1: explore the Open Food Facts export (food.parquet).

Run:
    python scripts/01_explore_data.py --parquet data/food.parquet

This script only READS the data; it does not filter or change anything.
It answers four questions and writes the answers to reports/:
  1. Which columns and types does the file contain?          -> reports/schema.txt
  2. How many products does each country have?               -> reports/countries.csv
  3. For the chosen country, how complete are the key fields? -> reports/fill_rates.csv
  4. What do real records look like?                         -> reports/sample_records.csv
The numbers are used in the written report to justify the choice of the data subset.
The script does not assume exact column names: columns it cannot find are skipped.
"""
import argparse
from pathlib import Path

import duckdb

# Fields of interest (used only if the file contains them under this name)
KEY_FIELDS = [
    "code", "product_name", "brands", "categories_tags", "ingredients_text",
    "allergens_tags", "traces_tags", "nutriments", "countries_tags", "lang",
]


def fill_expr(col: str, dtype: str) -> str:
    """Return a SQL expression that is 1 if the field is really filled, otherwise 0."""
    q = f'"{col}"'
    d = dtype.upper()
    if d.endswith("[]"):  # list column: filled means non-empty
        return f"CASE WHEN {q} IS NOT NULL AND len({q}) > 0 THEN 1 ELSE 0 END"
    if d == "VARCHAR":
        return f"CASE WHEN {q} IS NOT NULL AND trim({q}) <> '' THEN 1 ELSE 0 END"
    return f"CASE WHEN {q} IS NOT NULL THEN 1 ELSE 0 END"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", required=True)
    ap.add_argument("--country", default="en:czech-republic",
                    help="country tag, e.g. en:czech-republic, en:slovakia, en:germany")
    ap.add_argument("--out", default="reports")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(exist_ok=True)
    con = duckdb.connect()
    src = f"read_parquet('{args.parquet}')"

    # 1) Schema
    schema = con.sql(f"DESCRIBE SELECT * FROM {src}").df()
    types = dict(zip(schema["column_name"], schema["column_type"]))
    (out / "schema.txt").write_text(schema.to_string(index=False), encoding="utf-8")
    total = con.sql(f"SELECT count(*) FROM {src}").fetchone()[0]
    print(f"Columns: {len(types)}, total products: {total:,}")
    print("Key fields found in the file:",
          [c for c in KEY_FIELDS if c in types] or "none - see reports/schema.txt")

    # 2) Products per country
    if "countries_tags" in types:
        countries = con.sql(f"""
            SELECT c AS country, count(*) AS products
            FROM (SELECT unnest(countries_tags) AS c FROM {src})
            GROUP BY c ORDER BY products DESC LIMIT 40
        """).df()
        countries.to_csv(out / "countries.csv", index=False)
        print("\nTop countries by number of products:")
        print(countries.head(15).to_string(index=False))
        where = f"list_contains(countries_tags, '{args.country}')"
    else:
        print("\nColumn countries_tags not found: the country filter is skipped.")
        where = "TRUE"

    # 3) Completeness of key fields for the chosen country
    cols = [c for c in KEY_FIELDS if c in types]
    selects = ", ".join(f"avg({fill_expr(c, types[c])}) AS \"{c}\"" for c in cols)
    n = con.sql(f"SELECT count(*) FROM {src} WHERE {where}").fetchone()[0]
    fr = con.sql(f"SELECT {selects} FROM {src} WHERE {where}").df().T
    fr.columns = ["fill_rate"]
    fr["fill_rate"] = fr["fill_rate"].round(3)
    fr.to_csv(out / "fill_rates.csv")
    print(f"\nProducts with country tag {args.country}: {n:,}")
    print("Share of products with the field filled (1.0 = all products):")
    print(fr.to_string())

    # 4) A few raw records, to see the real structure of the data
    sample = con.sql(f"SELECT * FROM {src} WHERE {where} LIMIT 3").df()
    sample.T.to_csv(out / "sample_records.csv", header=False)
    print("\n3 sample records saved to reports/sample_records.csv")


if __name__ == "__main__":
    main()