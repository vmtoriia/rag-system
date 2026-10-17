"""Build a web page for browsing the corpus.

Run:   python tools/view_corpus.py
Open:  data/corpus_view.html   (double-click; works offline)

This is a helper for looking at the data, not a pipeline step: it only reads data/corpus.parquet.
The page layout lives in tools/view_corpus.html. This script reads the products, puts them into
that page as JSON, and saves the result to data/ (which is not committed to git).
"""
import json
from pathlib import Path

import duckdb

CORPUS = Path("data/corpus.parquet")
TEMPLATE = Path(__file__).with_name("view_corpus.html")
OUTPUT = Path("data/corpus_view.html")


def strip_prefix(tags: list[str] | None) -> list[str]:
    """Turn tags like 'en:milk' or 'cs:tekutá-náhrada-stravy' into 'milk', 'tekutá-náhrada-stravy'."""
    return [tag.split(":", 1)[-1] for tag in tags or []]


def load_products() -> list[dict]:
    """Read the columns the page shows. Numbers are rounded to one decimal place.

    The nutrient columns are stored as FLOAT (32-bit), which keeps 7.6 as 7.599999904...;
    converting to DOUBLE before rounding gives a clean 7.6.
    """
    query = duckdb.sql(f"""
        SELECT ean, name, brands, lang, url,
               categories_tags, allergens_eu, traces_eu, allergens_declared_none,
               round(energy_kcal_100g::DOUBLE, 1) AS kcal,
               round(sugars_100g::DOUBLE, 1)      AS sugars,
               round(proteins_100g::DOUBLE, 1)    AS protein,
               ingredients_text, doc_text
        FROM read_parquet('{CORPUS.as_posix()}')
        ORDER BY name
    """)
    products = [dict(zip(query.columns, row)) for row in query.fetchall()]

    for p in products:
        p["categories"] = strip_prefix(p.pop("categories_tags"))
        p["allergens"] = strip_prefix(p.pop("allergens_eu"))
        p["traces"] = strip_prefix(p.pop("traces_eu"))
        p["no_allergens"] = p.pop("allergens_declared_none")
    return products


def main() -> None:
    products = load_products()

    # "</" is written as "<\/" so that a product text can never close the page's <script> tag.
    data = json.dumps(products, ensure_ascii=False).replace("</", "<\\/")
    template = TEMPLATE.read_text(encoding="utf-8")
    if "__PRODUCTS__" not in template:
        raise SystemExit(f"{TEMPLATE} is empty or is not the page template. Copy view_corpus.html into tools/ again.")
    page = template.replace("__PRODUCTS__", data)

    OUTPUT.write_text(page, encoding="utf-8")
    print(f"Saved {OUTPUT} with {len(products):,} products. Open it in your browser.")


if __name__ == "__main__":
    main()
