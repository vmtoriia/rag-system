"""Step 2: build the clean corpus (products_clean.parquet) from food.parquet.

Run:
    python scripts/02_prepare_corpus.py --parquet data/food.parquet

What it does:
  1. Keeps only products sold in the chosen country (default: Czechia).
  2. Applies quality filters one by one and records how many products each filter removes
     -> reports/filter_funnel.csv  (use this table in the report to justify the subset)
  3. Flattens the awkward structures of the raw file into simple columns:
       - product_name / ingredients_text: lists of {lang, text}  -> one string
       - nutriments: list of {name, 100g, ...}                    -> a few numeric columns
  4. Writes data/products_clean.parquet (+ a 200-row CSV preview) and
     reports/corpus_summary.txt (categories, nutrient availability, allergen stats).
The raw food.parquet is not needed after this step.
"""
import argparse
from pathlib import Path

import duckdb

# nutrient name in OFF -> column name in our corpus (values are per 100 g)
NUTRIENTS = {
    "energy-kcal": "energy_kcal_100g",
    "fat": "fat_100g",
    "saturated-fat": "saturated_fat_100g",
    "carbohydrates": "carbohydrates_100g",
    "sugars": "sugars_100g",
    "fiber": "fiber_100g",
    "proteins": "proteins_100g",
    "salt": "salt_100g",
}


def pick_text(col: str, lang_pref: str) -> str:
    """SQL: choose the best text from a list of {lang, text} structs.
    Priority: preferred language -> the product's main language -> English -> first non-empty."""
    def first(cond: str) -> str:
        return (f"list_filter({col}, x -> ({cond}) AND x.\"text\" IS NOT NULL "
                f"AND trim(x.\"text\") <> '')[1].\"text\"")
    return (f"COALESCE({first(f'x.lang = ' + repr(lang_pref))}, "
            f"{first('x.lang = lang')}, {first(chr(120) + '.lang = ' + repr('en'))}, "
            f"{first('TRUE')})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", required=True)
    ap.add_argument("--country", default="en:czech-republic")
    ap.add_argument("--lang", default="cs", help="preferred language for names/ingredients")
    ap.add_argument("--min-ingredients-chars", type=int, default=10)
    ap.add_argument("--out-dir", default="data")
    ap.add_argument("--reports", default="reports")
    args = ap.parse_args()

    Path(args.out_dir).mkdir(exist_ok=True)
    Path(args.reports).mkdir(exist_ok=True)
    con = duckdb.connect()
    src = f"read_parquet('{args.parquet}')"

    nutrient_cols = ",\n            ".join(
        f"list_filter(nutriments, x -> x.name = '{k}')[1].\"100g\" AS {v}"
        for k, v in NUTRIENTS.items()
    )

    # Stage 0: country subset, with flattened columns (computed once, filters applied later)
    con.sql(f"""
        CREATE TABLE stage AS
        SELECT
            code,
            {pick_text('product_name', args.lang)}      AS name,
            brands,
            categories_tags,
            {pick_text('ingredients_text', args.lang)}  AS ingredients_text,
            allergens_tags,
            traces_tags,
            lang,
            COALESCE(obsolete, false)                   AS obsolete,
            {nutrient_cols}
        FROM {src}
        WHERE list_contains(countries_tags, '{args.country}')
    """)

    # Quality filters, applied cumulatively; each step is counted for the funnel table.
    steps = [
        ("country subset", "TRUE"),
        ("valid barcode (8-14 digits)", "code IS NOT NULL AND regexp_matches(code, '^[0-9]{8,14}$')"),
        ("not marked obsolete", "NOT obsolete"),
        ("has product name", "name IS NOT NULL AND length(trim(name)) >= 2"),
        (f"has ingredients text (>= {args.min_ingredients_chars} chars)",
         f"ingredients_text IS NOT NULL AND length(trim(ingredients_text)) >= {args.min_ingredients_chars}"),
        ("has category tags", "categories_tags IS NOT NULL AND len(categories_tags) > 0"),
        ("has at least 3 nutrients",
         "(" + " + ".join(f"({v} IS NOT NULL)::INT" for v in NUTRIENTS.values()) + ") >= 3"),
    ]
    funnel, where = [], []
    for label, cond in steps:
        where.append(f"({cond})")
        n = con.sql(f"SELECT count(*) FROM stage WHERE {' AND '.join(where)}").fetchone()[0]
        funnel.append((label, n))
    prev = None
    lines = ["step,remaining,removed"]
    for label, n in funnel:
        lines.append(f'"{label}",{n},{0 if prev is None else prev - n}')
        prev = n
    (Path(args.reports) / "filter_funnel.csv").write_text("\n".join(lines), encoding="utf-8")

    # Final table: dedupe by barcode, add URL and derived fields
    out_pq = Path(args.out_dir) / "products_clean.parquet"
    con.sql(f"""
        COPY (
            SELECT DISTINCT ON (code)
                code AS ean,
                trim(name) AS name,
                nullif(trim(brands), '') AS brands,
                categories_tags,
                trim(ingredients_text) AS ingredients_text,
                COALESCE(allergens_tags, []::VARCHAR[]) AS allergens_tags,
                COALESCE(traces_tags, []::VARCHAR[])    AS traces_tags,
                {', '.join(NUTRIENTS.values())},
                lang,
                'https://world.openfoodfacts.org/product/' || code AS url
            FROM stage
            WHERE {' AND '.join(where)}
            ORDER BY code
        ) TO '{out_pq.as_posix()}' (FORMAT parquet)
    """)
    con.sql(f"CREATE VIEW clean AS SELECT * FROM read_parquet('{out_pq.as_posix()}')")
    con.sql(f"""COPY (SELECT ean, name, brands, array_to_string(categories_tags, ';') AS categories,
                      ingredients_text, array_to_string(allergens_tags, ';') AS allergens,
                      array_to_string(traces_tags, ';') AS traces, sugars_100g, proteins_100g, url
               FROM clean LIMIT 200) TO '{(Path(args.out_dir) / 'products_clean_preview.csv').as_posix()}'
               (HEADER, DELIMITER ',')""")

    # Summary for the report
    total = con.sql("SELECT count(*) FROM clean").fetchone()[0]
    with_all = con.sql("SELECT count(*) FROM clean WHERE len(allergens_tags) > 0").fetchone()[0]
    with_tr = con.sql("SELECT count(*) FROM clean WHERE len(traces_tags) > 0").fetchone()[0]
    cats = con.sql("""SELECT c AS category, count(*) AS n
                      FROM (SELECT unnest(categories_tags) AS c FROM clean)
                      GROUP BY c ORDER BY n DESC LIMIT 25""").df()
    alg = con.sql("""SELECT a AS allergen, count(*) AS n
                     FROM (SELECT unnest(allergens_tags) AS a FROM clean)
                     GROUP BY a ORDER BY n DESC LIMIT 15""").df()
    nut = {v: con.sql(f"SELECT round(avg(({v} IS NOT NULL)::INT), 3) FROM clean").fetchone()[0]
           for v in NUTRIENTS.values()}
    summary = [
        f"Corpus size: {total:,} products ({args.country})",
        f"With at least one declared allergen: {with_all:,} ({with_all / max(total, 1):.1%})",
        f"With at least one trace allergen:    {with_tr:,} ({with_tr / max(total, 1):.1%})",
        "", "Nutrient availability (share of products):",
        *[f"  {k}: {v}" for k, v in nut.items()],
        "", "Top categories:", cats.to_string(index=False),
        "", "Top declared allergens:", alg.to_string(index=False),
    ]
    text = "\n".join(summary)
    (Path(args.reports) / "corpus_summary.txt").write_text(text, encoding="utf-8")
    print("Filter funnel:")
    for label, n in funnel:
        print(f"  {n:>8,}  {label}")
    print("\n" + text)
    print(f"\nWritten: {out_pq}, {Path(args.out_dir) / 'products_clean_preview.csv'}, reports/")


if __name__ == "__main__":
    main()