"""
Step 4 — Filter merged+classified+patent data to CHRONIC and LONG-TERM drugs.
Output: orangebook_chronic_drugs.csv
"""

import csv

IN  = "orangebook_with_patents.csv"
OUT = "orangebook_chronic_drugs.csv"

KEEP_DURATION = {"CHRONIC", "LONG-TERM"}

rows_out = []
with open(IN, encoding="utf-8") as fh:
    reader = csv.DictReader(fh)
    for row in reader:
        if row["Duration_Class"] in KEEP_DURATION:
            rows_out.append(row)

# Sort by disease category, then by generic competitor count desc
rows_out.sort(key=lambda r: (
    r["Disease_Category"],
    -int(r["Generic_Competitor_Count"]),
))

# Output columns in logical order
OUT_COLS = [
    "Ingredient",
    "Trade_Name(s)",
    "Disease_Category",
    "Duration_Class",
    "DF_Route(s)",
    "Earliest_Approval",
    "Latest_Approval",
    "NDA_Count",
    "ANDA_Count",
    "Generic_Competitor_Count",
    "Patent_Count",
    "Latest_Patent_Expiry",
    "Patent_Expiry_Year",
    "Has_Blocking_Exclusivity",
    "Exclusivity_Codes",
    "Latest_Exclusivity_Date",
    "Applicant(s)",
]

with open(OUT, "w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=OUT_COLS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows_out)

# ── Summary ──────────────────────────────────────────────────────────────────
from collections import Counter
dur_cts = Counter(r["Duration_Class"] for r in rows_out)
cat_cts = Counter(r["Disease_Category"] for r in rows_out)

print(f"Total chronic/long-term ingredients: {len(rows_out)}")
print(f"  CHRONIC:   {dur_cts['CHRONIC']}")
print(f"  LONG-TERM: {dur_cts['LONG-TERM']}")
print("\nDisease category breakdown:")
for cat, n in cat_cts.most_common():
    print(f"  {cat:<30} {n:>5}")
print(f"\nOutput → {OUT}")
