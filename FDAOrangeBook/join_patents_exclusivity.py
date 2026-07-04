"""
Step 3 — Join patent.txt and exclusivity.txt back to each ingredient.
Per ingredient: latest patent expiry, patent count, active exclusivity codes.
Input:  orangebook_classified.csv + raw data files
Output: orangebook_with_patents.csv
"""

import csv
from datetime import datetime
from collections import defaultdict

PRODUCTS    = "data/EOBZIP_2026_05/products.txt"
PATENTS     = "data/EOBZIP_2026_05/patent.txt"
EXCLUSIVITY = "data/EOBZIP_2026_05/exclusivity.txt"
CLASSIFIED  = "orangebook_classified.csv"
OUT         = "orangebook_with_patents.csv"

TODAY = datetime(2026, 7, 3)   # reference date for "active" exclusivity check

def parse_date(s):
    s = (s or "").strip()
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%b %Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None

# ── Build (Appl_Type, Appl_No, Product_No) → Ingredient map ─────────────────
prod_key_to_ing = {}  # (type, appl_no, prod_no) → ingredient
with open(PRODUCTS, encoding="utf-8", errors="replace") as fh:
    for row in csv.DictReader(fh, delimiter="~"):
        if row.get("Type", "").strip() == "DISCN":
            continue
        key = (row["Appl_Type"].strip(), row["Appl_No"].strip(), row["Product_No"].strip())
        prod_key_to_ing[key] = row["Ingredient"].strip()

# ── Aggregate patents per ingredient ─────────────────────────────────────────
# Track latest expiry, total count, and deduped patent numbers
ing_patents = defaultdict(lambda: {
    "patent_nos":  set(),
    "latest_exp":  None,
    "n_patents":   0,
})

with open(PATENTS, encoding="utf-8", errors="replace") as fh:
    for row in csv.DictReader(fh, delimiter="~"):
        key = (row["Appl_Type"].strip(), row["Appl_No"].strip(), row["Product_No"].strip())
        ing = prod_key_to_ing.get(key)
        if not ing:
            continue
        pno = row.get("Patent_No", "").strip()
        if pno:
            ing_patents[ing]["patent_nos"].add(pno)
        exp = parse_date(row.get("Patent_Expire_Date_Text", ""))
        if exp:
            cur = ing_patents[ing]["latest_exp"]
            if cur is None or exp > cur:
                ing_patents[ing]["latest_exp"] = exp

# Build final patent fields per ingredient
for ing, d in ing_patents.items():
    d["n_patents"] = len(d["patent_nos"])

# ── Aggregate exclusivity per ingredient ─────────────────────────────────────
# Classify codes into blocking vs. non-blocking
BLOCKING_CODES = {"NCE", "ODE", "PED", "GAIN", "ODE-PED", "NCE-PED"}
ing_excl = defaultdict(lambda: {
    "excl_codes":    [],
    "latest_excl":   None,
    "has_blocking":  False,
})

with open(EXCLUSIVITY, encoding="utf-8", errors="replace") as fh:
    for row in csv.DictReader(fh, delimiter="~"):
        key = (row["Appl_Type"].strip(), row["Appl_No"].strip(), row["Product_No"].strip())
        ing = prod_key_to_ing.get(key)
        if not ing:
            continue
        code = row.get("Exclusivity_Code", "").strip()
        exp  = parse_date(row.get("Exclusivity_Date", ""))
        if code:
            if exp is None or exp >= TODAY:   # still active or undated
                ing_excl[ing]["excl_codes"].append(code)
                if exp:
                    cur = ing_excl[ing]["latest_excl"]
                    if cur is None or exp > cur:
                        ing_excl[ing]["latest_excl"] = exp
                if code in BLOCKING_CODES:
                    ing_excl[ing]["has_blocking"] = True

# ── Merge with classified CSV ─────────────────────────────────────────────────
rows_in = []
with open(CLASSIFIED, encoding="utf-8") as fh:
    reader = csv.DictReader(fh)
    in_fields = reader.fieldnames
    for r in reader:
        rows_in.append(r)

out_fields = in_fields + [
    "Patent_Count",
    "Latest_Patent_Expiry",
    "Patent_Expiry_Year",
    "Exclusivity_Codes",
    "Latest_Exclusivity_Date",
    "Has_Blocking_Exclusivity",
]

with open(OUT, "w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=out_fields)
    writer.writeheader()
    for r in rows_in:
        ing = r["Ingredient"]
        pat = ing_patents.get(ing, {})
        exc = ing_excl.get(ing, {})

        latest_pat = pat.get("latest_exp")
        latest_exc = exc.get("latest_excl")
        excl_codes = sorted(set(exc.get("excl_codes", [])))

        r["Patent_Count"]              = pat.get("n_patents", 0)
        r["Latest_Patent_Expiry"]      = latest_pat.strftime("%Y-%m-%d") if latest_pat else ""
        r["Patent_Expiry_Year"]        = latest_pat.year if latest_pat else ""
        r["Exclusivity_Codes"]         = " | ".join(excl_codes)
        r["Latest_Exclusivity_Date"]   = latest_exc.strftime("%Y-%m-%d") if latest_exc else ""
        r["Has_Blocking_Exclusivity"]  = "Yes" if exc.get("has_blocking") else "No"
        writer.writerow(r)

# ── Summary ──────────────────────────────────────────────────────────────────
n_with_patent = sum(1 for r in rows_in if ing_patents.get(r["Ingredient"], {}).get("n_patents", 0) > 0)
n_with_excl   = sum(1 for r in rows_in if ing_excl.get(r["Ingredient"], {}).get("excl_codes"))
n_blocking    = sum(1 for r in rows_in if ing_excl.get(r["Ingredient"], {}).get("has_blocking"))

print(f"Ingredients with ≥1 patent:              {n_with_patent}")
print(f"Ingredients with active exclusivity:     {n_with_excl}")
print(f"Ingredients with blocking exclusivity:   {n_blocking}")
print(f"Output → {OUT}")
