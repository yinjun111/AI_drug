# FDA Orange Book — Chronic Drugs Analysis Plan

Goal: mirror the `FDAPurpleBook/` chronic-use pipeline and dashboard, but for the Orange
Book (NDA/ANDA small-molecule drugs), focusing on chronic-use drugs. Not yet executed —
this is the plan to follow when we resume.

## Source data

`data/EOBZIP_2026_05/` (downloaded from
https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files),
three ASCII tilde (`~`)-delimited files, single current snapshot (no monthly N/R/U
history like Purple Book):

- **`products.txt`** (48,381 rows) — columns: `Ingredient`, `DF;Route` (dosage form +
  route, semicolon-joined within the field), `Trade_Name`, `Applicant`, `Strength`,
  `Appl_Type` (`N`=NDA/innovator, `A`=ANDA/generic), `Appl_No`, `Product_No`, `TE_Code`
  (therapeutic equivalence, e.g. `AB`=substitutable, blank=not evaluated/no RLD),
  `Approval_Date`, `RLD` (Yes/No — Reference Listed Drug), `RS` (Yes/No — Reference
  Standard), `Type` (`RX`, `OTC`, `DISCN`=discontinued), `Applicant_Full_Name`.
  - `Appl_Type` counts: A=37,545, N=10,836.
  - `Type` counts: RX=24,660, DISCN=22,945, OTC=776.
  - 2,737 unique `Ingredient` strings total; **1,889 unique active (non-DISCN)
    ingredients** — this is the unit of analysis (vs. 209 biologics in Purple Book).
  - `Ingredient` can be a single active ingredient or a `;`-separated combo
    (2,824 active rows are combination products).

- **`patent.txt`** (21,807 rows) — `Appl_Type`, `Appl_No`, `Product_No`, `Patent_No`,
  `Patent_Expire_Date_Text`, `Drug_Substance_Flag`, `Drug_Product_Flag`,
  `Patent_Use_Code` (e.g. `U-141` — specific use covered, legend published separately),
  `Delist_Flag`, `Submission_Date`. Joins to `products.txt` via `(Appl_No, Product_No)`.

- **`exclusivity.txt`** (2,265 rows) — `Appl_Type`, `Appl_No`, `Product_No`,
  `Exclusivity_Code`, `Exclusivity_Date`. Known codes: NCE (5yr new chemical entity),
  ODE (7yr orphan), PED (6mo pediatric extension), GAIN (5yr antibiotic incentive),
  plus non-blocking 3yr codes D/I/M/NC/NDF/NE/NP/NPP/NR/NS, and others seen in the data
  (e.g. `RTO`) not yet fully confirmed against FDA's legend — needs spot-checking during
  implementation. Joins to `products.txt` the same way as patents.

## Why not reuse the Purple Book scripts as-is

- Purple Book's disease/duration classification came from live FDA label queries via
  `uvx --from tooluniverse tu run FDA_get_indications_by_drug_name` — **`uvx` is not
  installed in this environment.**
- Fallback checked: direct public openFDA REST API (`api.fda.gov/drug/label.json`)
  works, but is capped at **1,000 requests/day without an API key** (40/min). We have
  1,889 unique active ingredients, so a straight per-ingredient query pass can't
  complete in one day. Attempted to self-provision a free instant `api.data.gov` key
  (`POST /signup/`) — the endpoint no longer supports that (405), so no key in hand.
  Did not attempt account signup via the user's email through a browser/JS flow since
  that needs manual verification.
- Purple Book's chronic-duration classification (`chronic_use_analysis.py`) was itself
  a **hand-curated dictionary**, not derived automatically — so the plan below follows
  the same precedent, scaled up with name/suffix pattern rules to cover ~1,889
  ingredients without per-drug manual entry or API calls.

## Planned pipeline (scripts to write in `FDAOrangeBook/`)

1. **`merge_by_ingredient.py`**
   - Parse `products.txt`, filter to active rows (`Type != DISCN`).
   - Aggregate per unique `Ingredient`: trade name(s), applicant(s), `Appl_Type` set
     (N/A counts → brand-vs-generic split), dosage form(s)/route(s), TE codes,
     approval date range, RLD count, count of ANDA rows (generic-competition proxy).
   - Output: `orangebook_merged_by_ingredient.csv` (~1,889 rows). Mirrors
     `FDAPurpleBook/merge_by_proper_name.py`.

2. **`classify_chronic.py`**
   - Rule-based classifier, no external API calls:
     - **Disease category**: regex/keyword rules on the ingredient name plus INN
       stem/suffix patterns (e.g. `-pril`→ACE inhibitor/cardiovascular, `-sartan`→ARB/
       cardiovascular, `-olol`→beta blocker/cardiovascular, `-dipine`→CCB/cardiovascular,
       `-statin`→lipid/metabolic, `-gliptin`/`-gliflozin`/`-glutide`/metformin→metabolic
       (diabetes), `-prazole`/`-tidine`→GI, `-dronate`→bone/metabolic, `-oxetine`/
       `-alopram`/`-apine`/`-idone`→psychiatric, `-triptan`→neurology (but acute, not
       chronic), `-navir`/`-tegravir`/antiretrovirals→infectious (chronic HIV mgmt),
       `-tinib`/`-ciclib`/hormonal oncology agents→oncology, glaucoma agents→
       ophthalmology, immunosuppressants→autoimmune, etc. Categories: cardiovascular,
       metabolic, psychiatric, neurology, respiratory, GI, autoimmune, infectious,
       oncology, ophthalmology, dermatology, pain, other/unclassified.
     - **Duration class**: CHRONIC (indefinite maintenance — most cardiovascular/
       metabolic/psychiatric/autoimmune/HIV/glaucoma/thyroid drugs), LONG-TERM
       (oncology until progression), PERIODIC (e.g. long-term-as-needed NSAIDs,
       migraine prophylaxis), SHORT (acute antibiotics, single-course antivirals,
       analgesics for acute pain), OTHER/UNCLASSIFIED (fallback bucket — expect a
       non-trivial chunk here given 1,889 ingredients; the dashboard should show this
       bucket explicitly rather than force-fit it).
   - Output: adds `Disease_Category`, `Duration_Class` columns (new CSV or in-place
     merge into the CSV from step 1).

3. **`join_patents_exclusivity.py`**
   - Join `patent.txt` and `exclusivity.txt` back to each ingredient via
     `(Appl_No, Product_No)` through `products.txt`.
   - Per ingredient: latest `Patent_Expire_Date_Text` (patent-cliff date), patent count,
     any active exclusivity + codes.
   - This is new relative to Purple Book — Orange Book's unique value-add is
     patent/exclusivity data, so use it for a "generic competition / patent cliff" angle
     instead of Purple Book's revenue angle (no clean public revenue source at this
     ingredient count without heavy manual curation).

4. **Final chronic table**
   - Filter merged+classified+patent data to `Duration_Class` in {CHRONIC, LONG-TERM},
     output `orangebook_chronic_drugs.csv` analogous to
     `FDAPurpleBook/chronic_drugs_indications2.csv` (ingredient, disease category,
     dosage form/route, brand vs. generic counts, # ANDA competitors, latest patent
     expiry, earliest approval date).

5. **`build_orangebook_dashboard.py`**
   - Self-contained Plotly HTML dashboard, same visual style/palette as
     `FDAPurpleBook/build_dashboard.py`, adapted figures:
     1. Sankey — all active ingredients → duration class → disease category
     2. Donut — duration class breakdown
     3. Bar — disease category counts (chronic/long-term only)
     4. Bar — top chronic ingredients by # ANDA generic competitors (competition
        intensity — Orange-Book-specific, no Purple Book equivalent)
     5. Scatter — latest patent expiry year vs. # generic competitors (patent-cliff
        view) for chronic drugs — Orange-Book-specific
     6. Heatmap — disease category × generic-availability (AB-rated vs not)
     7. Bar — chronic drugs by approval decade (market maturity)
   - Output: `orangebook_chronic_dashboard.html`.

## Open questions / to confirm before or during execution

- Exact meaning of some `Exclusivity_Code` values seen in the data but not confirmed
  against FDA's official legend (e.g. `RTO`) — spot check during step 3, don't block on
  it (it's a minor enrichment field, not core to the chronic classification).
- How much of the 1,889-ingredient list ends up "OTHER/UNCLASSIFIED" after rule-based
  classification — if it's large (e.g. >30%), may be worth a second pass adding more
  suffix rules or a small manually-curated top-N list (by generic-competitor count, as
  a proxy for clinical significance) before finalizing the dashboard.
- Whether to fold in `FDAPurpleBook`-style revenue data — deferred for now; no clean
  free source at this scale without heavy manual work, unlike the ~30 blockbuster
  biologics Purple Book covered by hand.

## Task tracker

Tracked as tasks #1–#5 in this session's task list (`TaskList`), currently all
`pending`, ready to pick up as `merge_by_ingredient.py` → `classify_chronic.py` →
`join_patents_exclusivity.py` → final table → `build_orangebook_dashboard.py`.
