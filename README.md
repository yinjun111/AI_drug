# FDA Chronic-Use Drug Dashboards

Two interactive dashboards analyzing FDA-approved drugs used for **chronic / long-term
indications**, built by merging the FDA's Purple Book (biologics) and Orange Book
(small-molecule drugs) into a single unified dataset.

- **`index.html`** — password-protected landing page linking to both dashboards.
- **`combined_chronic_use_dashboard.html`** — all 985 chronic-use drugs.
- **`combined_chronic_use_peptide_dashboard.html`** — the peptide/protein-modality subset.

Both are password protected — see [Access control](#access-control).

## Data sources

| Source | What it covers | Unit of analysis |
|---|---|---|
| **[FDA Purple Book](https://purplebooksearch.fda.gov/)** | Licensed biologics (BLA products) — monoclonal antibodies, fusion proteins, enzyme/protein replacement therapies, peptide/protein hormones, vaccines, etc. | 96 unique biologics |
| **[FDA Orange Book](https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files)** | Small-molecule NDA/ANDA drugs (`products.txt` data files) | 889 unique active ingredients |

Both source datasets were built and processed in sibling folders (`../FDAPurpleBook/`,
`../FDAOrangeBook/`) before being merged here. Each drug was:

1. Filtered down to **chronic / long-term use** only (indefinite maintenance therapy,
   e.g. cardiovascular, metabolic, psychiatric, autoimmune, HIV, glaucoma, thyroid —
   as opposed to one-off, acute, or short-course treatments).
2. Annotated with disease indication(s), a normalized **disease category**, **drug
   modality** (biologic subtype for Purple Book, GSRS substance class for Orange
   Book), **drug target gene**, **2024 annual revenue (USD B)**, and typical
   **dose / frequency / duration of use**.
3. Where Orange Book indications listed multiple diseases (`;`-joined), rows were
   expanded so each drug–disease pair is its own row (long format).

## Merge & build pipeline

`build_combined_dashboard.py`:

1. Reads `purplebook_chronic_drugs_indications2.csv` (Purple Book, one row per
   drug–disease pair) and `orangebook_chronic_indications_clean.csv` (Orange Book),
   plus `../FDAOrangeBook/orangebook_substance_classes.csv` for GSRS modality lookup.
2. Unions both into one long-format table with a `Source` column
   (`Purple Book` / `Orange Book`) and writes it to
   **`fda_all_drugs_chronic_indications.csv`** (985 drugs, 1,492 drug–indication pairs,
   263 diseases, 65 disease categories, 267 target genes).
3. Renders `combined_chronic_use_dashboard.html` from that merged CSV — Plotly charts
   plus a sortable/filterable data table, no server required (everything is inlined
   into a single static HTML file).

`build_combined_peptide_dashboard.py` does the same, but reads the pre-filtered
**`fda_all_drugs_chronic_indications_peptide.csv`** subset (53 drugs, 77 pairs) —
peptide/protein-hormone and protein-modality drugs only — and adds two extra charts
specific to that subset (true peptide size by target gene, rare/orphan disease split).

To regenerate either dashboard after editing source data:

```bash
python3 build_combined_dashboard.py          # -> fda_all_drugs_chronic_indications.csv + combined_chronic_use_dashboard.html
python3 build_combined_peptide_dashboard.py   # -> combined_chronic_use_peptide_dashboard.html
```

(Requires `pandas`, `plotly`. See memory note: this environment currently has a
pandas/numexpr vs. NumPy 2.0 incompatibility that can block regeneration — fix that
environment issue first if the build fails.)

## What's in each dashboard

Both dashboards share the same structure, walking from raw counts to drill-down detail:

1. **Combined pipeline** — Sankey diagram: Source → Modality → Disease Category.
2. **Source composition** — Purple Book vs. Orange Book split, and drug modality
   breakdown by source.
3. **Disease categories** — distribution across the ~65 disease categories, and top
   30 target genes split by source.
4. **Drill-down** — Gene × Disease Category cross-tab.
5. **Drug breadth & revenue** — drugs ranked by number of indications treated, and
   top drugs by 2024 annual revenue.
6. **Disease coverage** — diseases ranked by number of approved drugs available.
7. *(Peptide dashboard only)* True peptide size by target gene, and rare/orphan
   disease therapies split by category.
8. A full sortable/filterable table of the underlying merged CSV.

## Access control

`index.html` and both dashboard files include a client-side JS password gate,
stored per-browser-session via `sessionStorage`. This is a casual deterrent for
informal sharing, **not real security** — the password is visible in the page
source to anyone who views it, since these are static files with no backend to
enforce access.
