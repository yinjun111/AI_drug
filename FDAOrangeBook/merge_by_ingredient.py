"""
Step 1 — Parse products.txt, filter active rows, aggregate per Ingredient.
Output: orangebook_merged_by_ingredient.csv (~1,889 rows)
"""

import csv
from collections import defaultdict
from datetime import datetime

DATA = "data/EOBZIP_2026_05/products.txt"
OUT  = "orangebook_merged_by_ingredient.csv"

SEP = " | "

records = defaultdict(lambda: {
    "trade_names":   set(),
    "applicants":    set(),
    "appl_nos_N":    set(),   # NDA
    "appl_nos_A":    set(),   # ANDA
    "df_routes":     set(),
    "te_codes":      set(),
    "approval_dates": [],
    "rld_count":     0,
    "anda_count":    0,       # generic-competition proxy
})

def parse_date(s):
    s = s.strip()
    for fmt in ("%b %d, %Y", "%b %y, %Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None

active_rows = 0
with open(DATA, encoding="utf-8", errors="replace") as fh:
    reader = csv.DictReader(fh, delimiter="~")
    for row in reader:
        if row.get("Type", "").strip() == "DISCN":
            continue
        active_rows += 1

        ing = row["Ingredient"].strip()
        if not ing:
            continue

        rec = records[ing]

        def add(field, key):
            v = row.get(key, "").strip()
            if v:
                field.add(v)

        add(rec["trade_names"], "Trade_Name")
        add(rec["applicants"],  "Applicant_Full_Name")
        add(rec["df_routes"],   "DF;Route")
        add(rec["te_codes"],    "TE_Code")

        atype = row.get("Appl_Type", "").strip()
        appl_no = row.get("Appl_No", "").strip()
        if atype == "N" and appl_no:
            rec["appl_nos_N"].add(appl_no)
        elif atype == "A" and appl_no:
            rec["appl_nos_A"].add(appl_no)
            rec["anda_count"] += 1

        if row.get("RLD", "").strip().upper() == "YES":
            rec["rld_count"] += 1

        d = parse_date(row.get("Approval_Date", ""))
        if d:
            rec["approval_dates"].append(d)

OUT_COLS = [
    "Ingredient",
    "Trade_Name(s)",
    "Applicant(s)",
    "NDA_Count",
    "ANDA_Count",
    "NDA_Appl_Nos",
    "ANDA_Appl_Nos",
    "DF_Route(s)",
    "TE_Code(s)",
    "Earliest_Approval",
    "Latest_Approval",
    "RLD_Count",
    "Generic_Competitor_Count",
]

with open(OUT, "w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=OUT_COLS)
    writer.writeheader()
    for ing in sorted(records.keys(), key=str.lower):
        rec = records[ing]
        dates = sorted(rec["approval_dates"])
        earliest = dates[0].strftime("%Y-%m-%d") if dates else ""
        latest   = dates[-1].strftime("%Y-%m-%d") if dates else ""
        writer.writerow({
            "Ingredient":               ing,
            "Trade_Name(s)":            SEP.join(sorted(rec["trade_names"])),
            "Applicant(s)":             SEP.join(sorted(rec["applicants"])),
            "NDA_Count":                len(rec["appl_nos_N"]),
            "ANDA_Count":               len(rec["appl_nos_A"]),
            "NDA_Appl_Nos":             SEP.join(sorted(rec["appl_nos_N"])),
            "ANDA_Appl_Nos":            SEP.join(sorted(rec["appl_nos_A"])),
            "DF_Route(s)":              SEP.join(sorted(rec["df_routes"])),
            "TE_Code(s)":              SEP.join(sorted(rec["te_codes"])),
            "Earliest_Approval":        earliest,
            "Latest_Approval":          latest,
            "RLD_Count":                rec["rld_count"],
            "Generic_Competitor_Count": rec["anda_count"],
        })

print(f"Active product rows processed: {active_rows}")
print(f"Unique ingredients: {len(records)}")
print(f"Output → {OUT}")
