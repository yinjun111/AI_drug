"""
Build orangebook_drug_revenue.csv using two public CMS data sources:

1. Medicaid State Drug Utilization Data 2023 (CMS)
   → total_amount_reimbursed, number_of_prescriptions, units_reimbursed per trade name
   → aggregated nationally across all states and quarters

2. NADAC (National Average Drug Acquisition Cost) 2024 (CMS)
   → nadac_per_unit (average acquisition cost per unit for pharmacies)

Mapping: trade name → ingredient via Orange Book merged CSV.
"""

import csv, io, re, requests
from collections import defaultdict
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
OB_MERGED   = "orangebook_merged_by_ingredient.csv"
OB_CLASSIFY = "orangebook_classified.csv"
OB_GSRS     = "orangebook_substance_classes.csv"
OUT_CSV     = "orangebook_drug_revenue.csv"

# ── Step 1: Build trade-name → ingredient reverse map ────────────────────────
print("Building trade-name → ingredient map …")
trade_to_ing: dict[str, str] = {}   # lower-cased trade name → ingredient
ing_meta: dict[str, dict]    = {}   # ingredient → meta (NDA/ANDA counts etc.)

with open(OB_MERGED, encoding="utf-8") as fh:
    for row in csv.DictReader(fh):
        ing = row["Ingredient"]
        ing_meta[ing] = {
            "Trade_Name(s)":            row["Trade_Name(s)"],
            "NDA_Count":                row["NDA_Count"],
            "ANDA_Count":               row["ANDA_Count"],
            "Generic_Competitor_Count": row["Generic_Competitor_Count"],
            "Earliest_Approval":        row["Earliest_Approval"],
            "Latest_Approval":          row["Latest_Approval"],
        }
        for trade in row["Trade_Name(s)"].split(" | "):
            t = trade.strip().upper()
            if t:
                trade_to_ing[t] = ing

# Also index by ingredient name itself (for generic products listed by INN)
for ing in ing_meta:
    trade_to_ing[ing.strip().upper()] = ing
    # First word of multi-component (e.g. "ATORVASTATIN CALCIUM" → "ATORVASTATIN")
    first = ing.split()[0]
    if first not in trade_to_ing:
        trade_to_ing[first.upper()] = ing

print(f"  {len(trade_to_ing):,} trade-name entries mapped to {len(ing_meta):,} ingredients")

# ── Step 2: Load disease/duration classification ──────────────────────────────
classify: dict[str, dict] = {}
with open(OB_CLASSIFY, encoding="utf-8") as fh:
    for row in csv.DictReader(fh):
        classify[row["Ingredient"]] = {
            "Disease_Category": row["Disease_Category"],
            "Duration_Class":   row["Duration_Class"],
        }

# ── Step 3: Load GSRS substance class ────────────────────────────────────────
gsrs: dict[str, dict] = {}
with open(OB_GSRS, encoding="utf-8") as fh:
    for row in csv.DictReader(fh):
        gsrs[row["Ingredient"]] = {
            "Substance_Class": row["Substance_Class"],
            "UNII":            row["UNII"],
        }

# ── Step 4: Stream Medicaid 2023 SDU data and aggregate ──────────────────────
SDUD_LOCAL = "sdud_2023.csv"
print(f"\nReading Medicaid 2023 SDU data from {SDUD_LOCAL} …")

# Accumulate per trade-name
sdud_totals: dict[str, dict] = defaultdict(lambda: {
    "total_reimbursed": 0.0,
    "total_rx":         0,
    "total_units":      0.0,
})

n_rows = 0
n_matched = 0
fh_sdud = open(SDUD_LOCAL, encoding="utf-8", errors="replace")
reader = csv.DictReader(fh_sdud)

for row in reader:
    n_rows += 1
    if n_rows % 500_000 == 0:
        print(f"  … {n_rows:,} rows processed, {n_matched:,} matched", flush=True)

    pname = (row.get("Product Name") or "").strip().upper()
    if not pname:
        continue

    try:
        amt   = float(row.get("Total Amount Reimbursed") or 0)
        rx    = int(float(row.get("Number of Prescriptions") or 0))
        units = float(row.get("Units Reimbursed") or 0)
    except (ValueError, TypeError):
        continue

    sdud_totals[pname]["total_reimbursed"] += amt
    sdud_totals[pname]["total_rx"]         += rx
    sdud_totals[pname]["total_units"]      += units

    if pname in trade_to_ing:
        n_matched += 1

fh_sdud.close()
print(f"  Done. {n_rows:,} rows, {len(sdud_totals):,} unique product names")

# ── Step 5: Read NADAC 2024 for per-unit cost ─────────────────────────────────
NADAC_LOCAL = "nadac_2024.csv"
print(f"\nReading NADAC 2024 from {NADAC_LOCAL} …")

# NADAC: keep the latest (most recent) entry per NDC description
nadac_latest: dict[str, dict] = {}   # upper drug name → {nadac_per_unit, as_of_date}

if Path(NADAC_LOCAL).exists() and Path(NADAC_LOCAL).stat().st_size > 0:
    with open(NADAC_LOCAL, encoding="utf-8", errors="replace") as fh2:
        reader2 = csv.DictReader(fh2)
        for row in reader2:
            # Columns vary — try both naming conventions
            desc = (row.get("NDC Description") or row.get("ndc_description") or "").strip().upper()
            npu  = row.get("NADAC Per Unit") or row.get("nadac_per_unit") or ""
            date = row.get("As of Date") or row.get("effective_date") or ""

            if not desc or not npu:
                continue
            try:
                npu_val = float(str(npu).replace("$", ""))
            except ValueError:
                continue

            # Keep latest date per description
            existing = nadac_latest.get(desc)
            if existing is None or date > existing["as_of_date"]:
                nadac_latest[desc] = {"nadac_per_unit": npu_val, "as_of_date": date}

    print(f"  {len(nadac_latest):,} NDC descriptions in NADAC 2024")
else:
    print(f"  NADAC 2024 not available locally, skipping")

# ── Step 6: Map SDUD product names → ingredients + NADAC ─────────────────────
def match_ingredient(pname: str) -> str | None:
    """Return ingredient for a product name, trying several lookup strategies."""
    # 1. Direct match
    if pname in trade_to_ing:
        return trade_to_ing[pname]
    # 2. Strip trailing dose/strength descriptors (e.g. "OZEMPIC 0." → "OZEMPIC", "JARDIANCE 10MG" → "JARDIANCE")
    base = re.sub(r'[\s\-]+\d.*$', '', pname).strip()   # remove from first digit onward
    base = re.sub(r'\s+(HCL|HBR|SODIUM|POTASSIUM|CALCIUM|SULFATE|ACETATE|MALEATE|TARTRATE|CITRATE|PHOSPHATE|HYDROCHLORIDE|TAB|CAP|INJ|SOLN|SUSP|PEN|KIT|SUS|CF).*$', '', base).strip()
    if base and base in trade_to_ing:
        return trade_to_ing[base]
    # 3. First word only (e.g. "ELIQUIS" from "ELIQUIS 2.5MG")
    first_word = pname.split()[0] if pname.split() else ''
    if len(first_word) >= 5 and first_word in trade_to_ing:
        return trade_to_ing[first_word]
    # 4. First two words
    words = pname.split()
    if len(words) >= 2:
        two = ' '.join(words[:2])
        if two in trade_to_ing:
            return trade_to_ing[two]
    return None

# Aggregate SDUD entries by ingredient
ing_sdud: dict[str, dict] = defaultdict(lambda: {
    "Medicaid_Total_Reimbursed_2023_USD": 0.0,
    "Medicaid_Total_Prescriptions_2023":  0,
    "Medicaid_Total_Units_2023":          0.0,
    "Medicaid_Product_Names":             set(),
})

unmatched_top: list[tuple] = []
for pname, totals in sdud_totals.items():
    ing = match_ingredient(pname)
    if ing:
        ing_sdud[ing]["Medicaid_Total_Reimbursed_2023_USD"] += totals["total_reimbursed"]
        ing_sdud[ing]["Medicaid_Total_Prescriptions_2023"]  += totals["total_rx"]
        ing_sdud[ing]["Medicaid_Total_Units_2023"]          += totals["total_units"]
        ing_sdud[ing]["Medicaid_Product_Names"].add(pname)
    else:
        unmatched_top.append((totals["total_reimbursed"], pname))

# Print top unmatched by spending
unmatched_top.sort(reverse=True)
print(f"\nTop 20 unmatched product names by Medicaid spending:")
for amt, pname in unmatched_top[:20]:
    print(f"  ${amt:>14,.0f}  {pname}")

# Aggregate NADAC per ingredient (average across matching NDC descriptions)
ing_nadac: dict[str, list[float]] = defaultdict(list)
for desc, data in nadac_latest.items():
    ing = match_ingredient(desc)
    if ing:
        ing_nadac[ing].append(data["nadac_per_unit"])

# ── Step 7: Write output CSV ──────────────────────────────────────────────────
OUT_COLS = [
    "Ingredient",
    "Trade_Name(s)",
    "Substance_Class",
    "UNII",
    "Disease_Category",
    "Duration_Class",
    "NDA_Count",
    "ANDA_Count",
    "Generic_Competitor_Count",
    "Earliest_Approval",
    "Medicaid_Total_Reimbursed_2023_USD",
    "Medicaid_Total_Reimbursed_2023_USD_M",   # in millions, rounded
    "Medicaid_Total_Prescriptions_2023",
    "Medicaid_Total_Units_2023",
    "NADAC_Avg_Per_Unit_2024_USD",
    "Medicaid_Matched_Product_Names",
]

rows_out = []
for ing in sorted(ing_meta.keys(), key=str.lower):
    meta   = ing_meta[ing]
    cls    = classify.get(ing, {})
    g      = gsrs.get(ing, {})
    s      = ing_sdud.get(ing, {})
    nadac_vals = ing_nadac.get(ing, [])

    reimbursed = s.get("Medicaid_Total_Reimbursed_2023_USD", 0.0)
    rows_out.append({
        "Ingredient":                          ing,
        "Trade_Name(s)":                       meta["Trade_Name(s)"],
        "Substance_Class":                     g.get("Substance_Class", ""),
        "UNII":                                g.get("UNII", ""),
        "Disease_Category":                    cls.get("Disease_Category", ""),
        "Duration_Class":                      cls.get("Duration_Class", ""),
        "NDA_Count":                           meta["NDA_Count"],
        "ANDA_Count":                          meta["ANDA_Count"],
        "Generic_Competitor_Count":            meta["Generic_Competitor_Count"],
        "Earliest_Approval":                   meta["Earliest_Approval"],
        "Medicaid_Total_Reimbursed_2023_USD":  f"{reimbursed:.2f}" if reimbursed else "",
        "Medicaid_Total_Reimbursed_2023_USD_M":f"{reimbursed/1e6:.2f}" if reimbursed else "",
        "Medicaid_Total_Prescriptions_2023":   s.get("Medicaid_Total_Prescriptions_2023", "") or "",
        "Medicaid_Total_Units_2023":           f"{s.get('Medicaid_Total_Units_2023', 0.0):.0f}" if s.get("Medicaid_Total_Units_2023") else "",
        "NADAC_Avg_Per_Unit_2024_USD":         f"{sum(nadac_vals)/len(nadac_vals):.4f}" if nadac_vals else "",
        "Medicaid_Matched_Product_Names":      " | ".join(sorted(s.get("Medicaid_Product_Names", set()))[:5]),
    })

with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=OUT_COLS)
    writer.writeheader()
    writer.writerows(rows_out)

# ── Summary ───────────────────────────────────────────────────────────────────
matched_n  = sum(1 for r in rows_out if r["Medicaid_Total_Reimbursed_2023_USD"])
total_med  = sum(float(r["Medicaid_Total_Reimbursed_2023_USD"]) for r in rows_out if r["Medicaid_Total_Reimbursed_2023_USD"])

print(f"\n{'='*60}")
print(f"Output → {OUT_CSV}")
print(f"Total ingredients: {len(rows_out):,}")
print(f"With Medicaid spend data: {matched_n:,}")
print(f"Total 2023 Medicaid spend (all matched): ${total_med/1e9:.2f}B")
print(f"\nTop 25 by 2023 Medicaid reimbursement:")
top = sorted(rows_out, key=lambda r: float(r["Medicaid_Total_Reimbursed_2023_USD"] or 0), reverse=True)
for r in top[:25]:
    amt_m = float(r["Medicaid_Total_Reimbursed_2023_USD_M"] or 0)
    print(f"  ${amt_m:>8.0f}M  {r['Disease_Category']:<18}  {r['Ingredient'][:50]}")
