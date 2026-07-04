"""
Update orangebook_chronic_indications_clean.csv:
  replace the 'Disease / Indication' column with real FDA-label-derived
  indications from orangebook_drug_disease_indications.csv.

Keeps a backup (.bak) and preserves the old MoA-derived value for any drug
where no label indication was found.
"""

import csv, shutil
from pathlib import Path

DETAIL = "orangebook_drug_disease_indications.csv"
CLEAN  = "orangebook_chronic_indications_clean.csv"

# ── Load label-derived indications ────────────────────────────────────────────
label_ind = {}
with open(DETAIL, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        label_ind[r["Drug"]] = {
            "parsed": r["Indications_Parsed"].strip(),
            "source": r["Source"],
        }

# ── Back up the clean file ────────────────────────────────────────────────────
shutil.copy(CLEAN, CLEAN + ".bak")

rows = list(csv.DictReader(open(CLEAN, encoding="utf-8")))
fields = list(rows[0].keys())

n_updated = n_kept = n_missing = 0
for r in rows:
    li = label_ind.get(r["Drug"])
    if li and li["parsed"]:
        r["Disease / Indication"] = li["parsed"]
        n_updated += 1
    elif li and li["source"] == "openFDA label":
        # label found but no dictionary match — keep MoA fallback
        n_kept += 1
    else:
        n_missing += 1

with open(CLEAN, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

print(f"Backup:              {CLEAN}.bak")
print(f"Rows updated (label): {n_updated}")
print(f"Rows kept (MoA):      {n_kept + n_missing}")
print(f"  (label w/o dict match: {n_kept}, no label: {n_missing})")
print(f"Updated -> {CLEAN}")
