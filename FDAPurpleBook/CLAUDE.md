# AI_Drug — FDA Purple Book Biologics Analysis

This project analyzes FDA-approved biologics (BLA products) using the **FDA Purple Book**
monthly historical data, tracing a pipeline from raw approval records through to a
disease/target/revenue dashboard for chronic-use biologics. Prior work (visible in file
timestamps) was done mid-May through early-July 2026, primarily in Claude Desktop.

## Data source

- Monthly Purple Book CSV snapshots live in `purplebook_csvs/` (gitignored, 75 files,
  `2020_february.csv` through `2026_april.csv`), downloaded from
  `https://www.accessdata.fda.gov/drugsatfda_docs/PurpleBook/...`. Each row has an
  `N/R/U` flag (New/Revised/Unchanged); pipeline scripts only keep `N` rows to avoid
  double-counting products across monthly snapshots.
- `purplebook-search-january-data-download (1).xlsx` — a supplementary raw export.
- `purplebook_analysis.ipynb` is the original exploratory notebook: downloads/loads the
  monthly CSVs, dedupes, parses approval dates, and produces summary breakdowns
  (approvals by year, BLA type — original/biosimilar/interchangeable, CBER vs CDER,
  top applicants, biosimilar reference-product competition, route/dosage form, orphan
  drug approvals, and a proper-name merge step).

## Pipeline (chronological, by script)

1. **`analyze_purplebook.py`** — standalone summary script over `purplebook_csvs/`:
   dedupes `N` records by (BLA Number, Product Number, Supplement Number), filters to
   2020–2026 approvals, and prints tables (approvals/year, BLA type, FDA center,
   submission type, route, dosage form, top applicants, biosimilar reference products,
   orphan exclusivity, original-BLA approvals).

2. **`merge_by_proper_name.py`** — collapses all monthly records down to one row per
   unique `Proper Name` (generic name), merging applicants, BLA numbers, brand names,
   strengths, dosage forms, routes, and approval dates into pipe-separated lists.
   Output: `purplebook_merged_by_proper_name.csv` (also a variant
   `purplebook_merged_proper_name.csv`, 209 unique proper names — the input used by
   downstream disease-mapping scripts).

3. **`map_drug_diseases.py`** / **`generate_drug_disease_table.py`** — for each unique
   drug (proper name + brand fallback), query FDA label data via the `tooluniverse`
   MCP-style CLI tool (`uvx --from tooluniverse tu run FDA_get_indications_by_drug_name`),
   cache raw responses to `fda_indications_cache.json` / `fda_indications_cache_full.json`
   (gitignored), then regex-parse the "INDICATIONS AND USAGE" label text into individual
   disease phrases and bucket them into 6 categories (oncology, infectious, autoimmune,
   neurology, cardiovascular, metabolic; else "others").
   Outputs: `purplebook_drug_diseases.csv` (208 rows) and
   `purplebook_adalimumab_style_drug_diseases.csv` (651 drug–disease rows, richer
   per-disease parsing).
   - `convert_cache_to_csv.py` re-derives `purplebook_drug_diseases_from_cache.csv`
     directly from the cache JSON without re-querying (reuses `extract_diseases_from_text`
     from `map_drug_diseases.py`).

4. **`chronic_use_classification.csv`** (209 rows) — manual/curated classification of
   each Purple Book biologic into duration buckets: `CHRONIC` (indefinite maintenance),
   `LONG-TERM` (months–years, e.g. oncology until progression), `PERIODIC`, `SHORT`,
   `ONE-TIME` (gene therapy/CAR-T/vaccine). Built/backed by
   **`chronic_use_analysis.py`**, which hardcodes a `CLASSIFICATIONS` dict of drug →
   (category, subcategory, indication, rationale) for ~200+ named biologics.

5. **`build_chronic_table.py`** — hand-curated per-drug-per-indication detail table
   (drug, brand, disease, disease category, dose, frequency, duration) specifically for
   CHRONIC/LONG-TERM biologics, excluding oncology. Feeds `chronic_drugs_indications.csv`.

6. **`add_targets.py`** — adds a `Drug Target (Gene)` column via a hardcoded
   drug→gene-symbol map (TNF inhibitors, IL-17/23 axis, IL-4/13, IL-5/eosinophil axis,
   enzyme-replacement targets, etc.), sourced from ChEMBL/HGNC.

7. **`add_revenue.py`** — adds a 2024 global annual revenue (USD billions) column,
   manually sourced per-company from FY2024 earnings (AbbVie, Sanofi/Regeneron, Roche,
   Novartis, J&J, Takeda, Amgen, AstraZeneca, Eli Lilly, Novo Nordisk, GSK, Biogen/Eisai,
   argenx, etc.).
   → Final merged table: **`chronic_drugs_indications2.csv`** (176 rows; columns: Drug,
   Brand Name(s), Disease/Indication, Disease Category, Drug Target (Gene), Annual
   Revenue 2024 (USD B), Dose, Frequency, Duration of Use). This is the primary
   analysis-ready dataset.

8. **`build_dashboard.py`** — builds the final self-contained interactive HTML
   dashboard (Plotly) from `chronic_use_classification.csv` +
   `chronic_drugs_indications2.csv`, with 8 figures:
   1. Sankey — full pipeline flow (208 biologics → duration bucket → disease category → target → drug)
   2. Donut — duration classification breakdown
   3. Bar — disease category counts (non-oncology chronic/long-term)
   4. Bar — top drug target genes
   5. Sunburst — Disease category → Drug Target → Drug
   6. Scatter — drugs by # indications vs target diversity
   7. Heatmap — Drug Target Gene × Disease Category
   8. Bar — top-selling biologics by 2024 revenue, colored by disease category
   → Output: **`chronic_use_dashboard.html`** (230KB, most recently modified file —
   this is the current deliverable).
   - A separate **`disease_drug_count_dashboard.html`** is a standalone dashboard focused
     on disease-by-drug-count.
   - `generate_drug_disease_table.py`'s docstring calls this "the adalimumab-style"
     table, i.e. modeled on how adalimumab's multiple indications are laid out.

9. **`FDA Biologics — Chronic Use Dashboard.pdf`** — an exported/printed snapshot of the
   dashboard (492KB).

## Related sub-project: `Primus/` (gitignored)

A separate, larger-scope exploration using a drug-target knowledge graph (OptimusKG),
centered on the **TNF** gene:
- `query_gene_drugs.py` / `query_drug_trials.py` — query scripts (gene→drugs,
  drug→clinical trials).
- `TNF_summary_report.txt` — summary: 21 drugs directly targeting TNF (10 approved,
  e.g. thalidomide, pomalidomide, binimetinib — note these are small molecules with
  TNF-modulating activity, not the biologic TNF inhibitors like adalimumab), plus
  54,091 drug–disease pairs across 4,918 TNF-associated diseases in the KG (3,475
  unique approved drugs by disease coverage).
- `adalimumab_clinical_reports.csv` / `adalimumab_clinical_trials.csv` — adalimumab-specific
  clinical trial data pulled as a case study.
- This appears to be earlier/parallel exploratory work, not wired into the main
  `chronic_use_dashboard.html` pipeline above.

## Notes / gotchas

- Several scripts reference Windows paths (`E:\Work\AI_Drug\...`, `/Work/AI_Drug/...`)
  from when this was run in a different environment — current working directory here is
  `/Work1/ZijiangYang/AI_Drug`, so paths would need adjusting to re-run `analyze_purplebook.py`,
  `merge_by_proper_name.py`, or `build_dashboard.py` as-is.
- `.gitignore` excludes `purplebook_csvs/`, `Primus/`, the FDA indication cache JSONs,
  `*.log`, and `*.bak` — so the git history (`d73ff84`, single "Initial commit") only
  tracks scripts, curated CSVs, and dashboard HTML, not raw source data or caches.
- Two near-duplicate disease-mapping pipelines exist (`map_drug_diseases.py` vs
  `generate_drug_disease_table.py`) with nearly identical regex parsing logic — the
  `_full` cache/CSV variants are the more complete second pass.
