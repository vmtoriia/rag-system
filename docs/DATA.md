# Data

## Source
- Open Food Facts, product database export in Parquet format, file `food.parquet`
  (Hugging Face dataset `openfoodfacts/product-database`).
- Downloaded on: **16 October 2026**
- Dataset revision (commit hash on Hugging Face, "Files and versions" tab): **7ea8b8ebefd42cf457a1fcdf45b6d57853568855**
- Raw file: about 8 GB, 4,813,990 products, 111 columns. Not stored in this repository.
- SHA-256 of `food.parquet`: `C74C716AE028A2DCC1520101CC5DDDEFA79652261052499B1C396427544F463C`

## Licence and attribution
Contains information from Open Food Facts (https://world.openfoodfacts.org), made available under the
Open Database License (ODbL). Individual contents are under the Database Contents License (DbCL).
Product images are not used.

## Subset selection (script `02_prepare_corpus.py`)
Country: Czechia (`en:czech-republic`), 21,066 products. Quality filters are applied cumulatively
(full table: `reports/filter_funnel.csv`):

| Step | Remaining | Removed |
|---|---:|---:|
| Country subset | 21,066 | - |
| Valid barcode (8-14 digits) | 21,053 | 13 |
| Not marked obsolete | 21,053 | 0 |
| Has product name | 19,247 | 1,806 |
| Has ingredients text (at least 10 characters) | 6,848 | 12,399 |
| Has category tags | 6,482 | 366 |
| Has at least 3 of 8 nutrients | 6,039 | 443 |

Ingredients text is the main bottleneck: only 33.8% of Czech products have it. Products without it cannot
be used for content-based retrieval, so they are removed.

## Cleaning and enrichment (script `03_enrich_corpus.py`)
- HTML fragments removed from 1,047 ingredient texts.
- Allergen tags normalised to the 14 EU allergens (`allergens_eu`, `traces_eu`). 371 products had
  non-standard tags (for example `cs:pšeničná`, `en:apple`); these are kept separately in `allergens_other`.
  The tag `en:none` (247 products) means "no allergens declared".
- 151 non-food products (dietary supplements) excluded: 6,039 -> **5,888 products** in `data/corpus.parquet`.
- `doc_text`: one text per product (name, brand, categories, ingredients cut at 800 characters, allergens,
  nutrition per 100 g). This is the text that gets embedded. Mean length 523 characters, maximum 1,283.

## Known limitations of the data
- Crowd-sourced. An empty allergen field does not prove that a product contains no allergens.
- Allergen coverage in the raw Czech data is 19.7%; it is 60.8% in the final corpus only because the corpus
  keeps products that have an ingredients text.
- Mixed languages (product language code, `reports/language_distribution.csv`): Czech 60.8%, English 15.2%,
  German 10.6%, French 4.4%, other languages about 9%. Category and allergen tags are language-neutral
  English tags; names and ingredients are in the language of the product entry.
- The subset leans plant-based: 2,779 of the 6,039 products (46%) are in the category
  `en:plant-based-foods-and-beverages`.

## Data model
One row per product in `data/corpus.parquet`; the same fields are loaded into the database.

| Column | Type | Meaning |
|---|---|---|
| `ean` | text | Barcode (8-14 digits), unique identifier of the product |
| `name`, `brands` | text | Product name and brand(s) |
| `categories_tags` | list of text | Open Food Facts category tags, e.g. `en:plant-based-beverages` |
| `lang` | text | Main language of the product entry (`cs`, `en`, `de`, ...) |
| `url` | text | Link to the source record: `https://world.openfoodfacts.org/product/<ean>` |
| `energy_kcal_100g`, `fat_100g`, `saturated_fat_100g`, `carbohydrates_100g`, `sugars_100g`, `fiber_100g`, `proteins_100g`, `salt_100g` | number | Nutrition per 100 g; empty when unknown |
| `ingredients_text` | text | Ingredients without HTML |
| `allergens_eu` | list of text | Declared allergens, limited to the 14 EU allergens (Regulation (EU) No 1169/2011, Annex II) |
| `traces_eu` | list of text | "May contain" allergens, limited to the same 14 |
| `allergens_other` | list of text | Non-standard allergen tags, kept for analysis only |
| `allergens_declared_none` | true/false | The product is explicitly marked as having no allergens (`en:none`) |
| `doc_text` | text | One readable text per product, used for embeddings and shown to the language model |

## Allergen status model
For a requested allergen, every product gets exactly one status. The rules are applied in this order:

| Status | Rule | Meaning for the user |
|---|---|---|
| `DECLARED` | the allergen is in `allergens_eu` | Contains the allergen |
| `TRACES` | the allergen is in `traces_eu` | May contain traces |
| `NOT_DECLARED` | the product has some allergen information (other allergens, traces, or `en:none`), but not this allergen | Not listed on the product; not a guarantee |
| `UNKNOWN` | the product has no allergen information at all | Missing data; never treated as allergen-free |

`DECLARED` and `TRACES` are checked first, because the data contains contradictions: 37 of the 247 products
marked `en:none` still list milk as an allergen or a trace. Which statuses a user's request excludes is set by
an explicit policy in the request, so that filtering is deterministic.

Nutrition limits (for example, at most 5 g of sugars per 100 g) follow the same principle: a product whose
value is missing cannot be confirmed to meet the limit and is excluded.
