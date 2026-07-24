"""
Merge ClinicalTrials.gov trial-level data with web/news-researched company
pipeline data into one master CSV for the Stem Cell Therapy Landscape
dashboard.

Sources:
  - clinicaltrials_stem_cell_enriched.csv: full census (11,517 studies) of
    ClinicalTrials.gov studies mentioning "stem cell", enriched with a
    Core_Stem_Cell_Product flag (regex on title/intervention — filters out
    incidental mentions e.g. eligibility criteria referencing prior HSCT),
    Disease_Area bucket, Cell_Type, and Stage (derived from Phase/status).
    ClinicalTrials.gov has no "Preclinical" stage by definition (only
    registered trials) and only 2 rows carry OverallStatus=APPROVED_FOR_MARKETING.
  - company_news_stem_cell.csv: EN + CN web/news research on stem cell
    companies -- covers preclinical pipelines and globally-approved products
    (Japan/Korea/EU/China) that a US-centric clinicaltrials.gov pull misses.

Output: stem_cell_master.csv, one row per record, unified schema:
  Source, Record_ID, Company_Sponsor, Sponsor_Class, Country, Product_Name,
  Target_Disease, Disease_Area, Cell_Type, Stage, Status, Start_Date,
  Source_URL, Notes
"""
import csv
import re
import sys

sys.path.insert(0, "/Work1/Zijiang/StemCell")
from enrich_clinicaltrials import classify_disease_area

CT_CSV = "/Work1/Zijiang/StemCell/clinicaltrials_stem_cell_enriched.csv"
NEWS_CSV = "/Work1/Zijiang/StemCell/company_news_stem_cell.csv"
OUT_CSV = "/Work1/Zijiang/StemCell/stem_cell_master.csv"

FIELDS = ["Source", "Record_ID", "Company_Sponsor", "Sponsor_Class", "Country",
          "Product_Name", "Target_Disease", "Disease_Area", "Cell_Type", "Gene_Target",
          "Stage", "Status", "Start_Date", "Source_URL", "Notes"]

STAGE_PATTERNS = [
    # "IND approved/accepted/cleared" means the trial application was cleared
    # to start -- NOT the same as the product being approved for marketing --
    # so this must be checked before the generic approv|marketed rule below.
    (re.compile(r"\binds?\b.{0,15}\b(approv|accept|clear)|"
                r"\b(approv|accept|clear)\w*.{0,15}\binds?\b", re.I), "IND-Enabling / Early Clinical"),
    (re.compile(r"approv|marketed", re.I), "Approved"),
    (re.compile(r"early phase\s*1", re.I), "Early Phase 1"),
    (re.compile(r"phase\s*1\s*/\s*2\s*/\s*3", re.I), "Phase 1/2/3"),
    (re.compile(r"phase\s*2\s*/\s*3", re.I), "Phase 2/3"),
    (re.compile(r"phase\s*1\s*/\s*2\b|phase\s*1-2", re.I), "Phase 1/2"),
    (re.compile(r"phase\s*3", re.I), "Phase 3"),
    (re.compile(r"phase\s*2", re.I), "Phase 2"),
    (re.compile(r"phase\s*1\b", re.I), "Phase 1"),
    (re.compile(r"preclinical", re.I), "Preclinical"),
    (re.compile(r"\bind\b|clinical", re.I), "IND-Enabling / Early Clinical"),
]


def norm_stage(s):
    text = (s or "").strip()
    for rx, label in STAGE_PATTERNS:
        if rx.search(text):
            return label
    return "Unknown"


def main():
    out_rows = []

    with open(CT_CSV, newline="") as f:
        for r in csv.DictReader(f):
            if r["Core_Stem_Cell_Product"] != "Yes":
                continue
            out_rows.append({
                "Source": "ClinicalTrials.gov",
                "Record_ID": r["NCT_ID"],
                "Company_Sponsor": r["Sponsor"],
                "Sponsor_Class": r["Sponsor_Class"],
                "Country": r["Countries"],
                "Product_Name": r["Intervention_Name"],
                "Target_Disease": r["Condition"],
                "Disease_Area": r["Disease_Area"],
                "Cell_Type": r["Cell_Type"],
                "Gene_Target": r["Gene_Target"],
                "Stage": r["Stage"],
                "Status": r["Overall_Status"],
                "Start_Date": r["Start_Date"],
                "Source_URL": r["URL"],
                "Notes": r["Title"],
            })

    n_ct = len(out_rows)

    try:
        with open(NEWS_CSV, newline="", encoding="utf-8-sig") as f:
            news_rows = list(csv.DictReader(f))
    except FileNotFoundError:
        news_rows = []

    for r in news_rows:
        country_norm = "; ".join(x.strip() for x in r.get("Country", "").split("/") if x.strip())
        out_rows.append({
            "Source": "Web/News Research",
            "Record_ID": "",
            "Company_Sponsor": r.get("Company", ""),
            "Sponsor_Class": "INDUSTRY",
            "Country": country_norm,
            "Product_Name": r.get("Product_Name", ""),
            "Target_Disease": r.get("Target_Disease", ""),
            "Disease_Area": classify_disease_area(r.get("Target_Disease", "")),
            "Cell_Type": r.get("Cell_Type", ""),
            "Gene_Target": r.get("Gene_Target", ""),
            "Stage": norm_stage(r.get("Stage", "")),
            "Status": "",
            "Start_Date": r.get("Source_Date", ""),
            "Source_URL": r.get("Source_URL", ""),
            "Notes": r.get("Notes", ""),
        })

    n_news = len(out_rows) - n_ct

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"wrote {len(out_rows)} rows -> {OUT_CSV}  (clinicaltrials.gov: {n_ct}, news: {n_news})")


if __name__ == "__main__":
    main()
