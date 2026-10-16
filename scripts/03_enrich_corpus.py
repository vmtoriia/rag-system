"""Step 3: clean and enrich the corpus (products_clean.parquet -> corpus.parquet).

Run:
    python scripts/03_enrich_corpus.py

Fixes problems found when inspecting the data:
  1. HTML leftovers in ingredients (e.g. <span class="allergen">mléko</span>) -> stripped.
  2. Messy allergen tags -> normalised to the 14 EU allergens:
       allergens_eu / traces_eu   (clean lists used for filtering by a user profile)
       allergens_other            (non-standard tags such as cs:pšeničná, en:apple; kept for the report)
     The tag 'en:none' means "explicitly no allergens" and becomes an empty list.
  3. Non-food rows (default: dietary supplements) are excluded.
  4. Builds `doc_text`: the single text per product that will be embedded and shown to the LLM.
Writes data/corpus.parquet and reports/corpus_enrichment.txt.
"""
import argparse
from pathlib import Path

import duckdb

EU14 = [
    "en:gluten", "en:crustaceans", "en:eggs", "en:fish", "en:peanuts", "en:soybeans",
    "en:milk", "en:nuts", "en:celery", "en:mustard", "en:sesame-seeds",
    "en:sulphur-dioxide-and-sulphites", "en:lupin", "en:molluscs",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inp", default="data/products_clean.parquet")
    ap.add_argument("--out", default="data/corpus.parquet")
    ap.add_argument("--reports", default="reports")
    ap.add_argument("--exclude-categories", nargs="*", default=["en:dietary-supplements"])
    ap.add_argument("--max-ingredients-chars", type=int, default=800,
                    help="ingredients are cut to this length inside doc_text (embedding models have a token limit)")
    args = ap.parse_args()

    Path(args.reports).mkdir(exist_ok=True)
    con = duckdb.connect()
    eu = "[" + ", ".join(f"'{a}'" for a in EU14) + "]"
    excl = "[" + ", ".join(f"'{c}'" for c in args.exclude_categories) + "]"

    # Step A: text cleanup + allergen normalisation
    con.sql(f"""
        CREATE TABLE a AS
        SELECT
            ean, name, brands, categories_tags, lang, url,
            energy_kcal_100g, fat_100g, saturated_fat_100g, carbohydrates_100g,
            sugars_100g, fiber_100g, proteins_100g, salt_100g,
            trim(regexp_replace(
                replace(replace(replace(replace(
                    regexp_replace(ingredients_text, '<[^>]*>', '', 'g'),
                    '&amp;', '&'), '&nbsp;', ' '), '&quot;', '"'), '&#39;', ''''),
                '\\s+', ' ', 'g'))                                              AS ingredients_text,
            list_sort(list_distinct(list_filter(allergens_tags, x -> list_contains({eu}, x)))) AS allergens_eu,
            list_sort(list_distinct(list_filter(traces_tags,    x -> list_contains({eu}, x)))) AS traces_eu,
            list_sort(list_distinct(list_filter(allergens_tags,
                x -> NOT list_contains({eu}, x) AND x <> 'en:none')))           AS allergens_other,
            list_contains(allergens_tags, 'en:none')                            AS allergens_declared_none
        FROM read_parquet('{args.inp}')
        WHERE NOT list_has_any(categories_tags, {excl})
    """)

    # Step B: readable categories (most specific 6) and the embedding text
    def pretty(col: str) -> str:
        return (f"list_transform({col}, x -> replace(replace(regexp_replace(x, '^[a-z]{{2}}:', ''), "
                f"'-', ' '), 'en:', ''))")

    con.sql(f"""
        COPY (
            SELECT *,
              concat_ws('. ',
                'Product: ' || name,
                CASE WHEN brands IS NOT NULL THEN 'Brand: ' || brands END,
                'Categories: ' || array_to_string(list_slice({pretty('categories_tags')}, -6, -1), ', '),
                'Ingredients: ' || CASE WHEN length(ingredients_text) > {args.max_ingredients_chars}
                                       THEN left(ingredients_text, {args.max_ingredients_chars}) || '...'
                                       ELSE ingredients_text END,
                CASE WHEN len(allergens_eu) > 0
                     THEN 'Contains allergens: ' || array_to_string(list_transform(allergens_eu,
                          x -> replace(replace(x, 'en:', ''), '-', ' ')), ', ') END,
                CASE WHEN len(traces_eu) > 0
                     THEN 'May contain traces of: ' || array_to_string(list_transform(traces_eu,
                          x -> replace(replace(x, 'en:', ''), '-', ' ')), ', ') END,
                CASE WHEN concat_ws('', energy_kcal_100g, fat_100g, sugars_100g, proteins_100g, salt_100g) <> ''
                     THEN 'Per 100 g: ' || concat_ws(', ',
                          CASE WHEN energy_kcal_100g IS NOT NULL THEN 'energy ' || round(energy_kcal_100g)::INT || ' kcal' END,
                          CASE WHEN fat_100g         IS NOT NULL THEN 'fat '      || round(fat_100g, 1)         || ' g' END,
                          CASE WHEN sugars_100g      IS NOT NULL THEN 'sugars '   || round(sugars_100g, 1)      || ' g' END,
                          CASE WHEN proteins_100g    IS NOT NULL THEN 'protein '  || round(proteins_100g, 1)    || ' g' END,
                          CASE WHEN salt_100g        IS NOT NULL THEN 'salt '     || round(salt_100g, 2)        || ' g' END)
                END
              ) AS doc_text
            FROM a
            ORDER BY ean
        ) TO '{Path(args.out).as_posix()}' (FORMAT parquet)
    """)
    con.sql(f"CREATE VIEW c AS SELECT * FROM read_parquet('{Path(args.out).as_posix()}')")

    n_in = con.sql(f"SELECT count(*) FROM read_parquet('{args.inp}')").fetchone()[0]
    n = con.sql("SELECT count(*) FROM c").fetchone()[0]
    html_left = con.sql("SELECT count(*) FROM c WHERE ingredients_text LIKE '%<%>%'").fetchone()[0]
    html_before = con.sql(f"SELECT count(*) FROM read_parquet('{args.inp}') WHERE ingredients_text LIKE '%<%>%'").fetchone()[0]
    other = con.sql("SELECT count(*) FROM c WHERE len(allergens_other) > 0").fetchone()[0]
    none_ = con.sql("SELECT count(*) FROM c WHERE allergens_declared_none").fetchone()[0]
    alg = con.sql("""SELECT replace(a,'en:','') AS allergen, count(*) AS n
                     FROM (SELECT unnest(allergens_eu) AS a FROM c) GROUP BY a ORDER BY n DESC""").df()
    L = con.sql("""SELECT round(avg(length(doc_text))) AS mean_chars, max(length(doc_text)) AS max_chars,
                          quantile_cont(length(doc_text), 0.95) AS p95_chars FROM c""").df()
    ex = con.sql("SELECT doc_text FROM c LIMIT 2").df()["doc_text"].tolist()

    lines = [
        f"Products in:  {n_in:,}", f"Products out: {n:,} (excluded categories: {args.exclude_categories})",
        f"Ingredient texts containing HTML: before {html_before:,}, after {html_left:,}",
        f"Products with non-standard allergen tags (moved to allergens_other): {other:,}",
        f"Products with explicit 'en:none' (no allergens declared): {none_:,}",
        "", "EU-14 allergen counts (declared):", alg.to_string(index=False),
        "", "doc_text length (characters):", L.to_string(index=False),
        "", "Example doc_text:", *[f"- {e}" for e in ex],
    ]
    text = "\n".join(lines)
    (Path(args.reports) / "corpus_enrichment.txt").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()