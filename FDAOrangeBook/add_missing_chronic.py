"""
Enrich chronic drugs that are in orangebook_chronic_drugs.csv but missing from
orangebook_chronic_indications_clean.csv (e.g. peptides previously misclassified
as OTHER, like tirzepatide), and append their rows.

Reuses the openFDA fetch + DISEASE_DICT parser and the granular category mapper.
"""
import csv, re

# Reuse label fetch + parser (fetch_indication, parse_indications, strip_salt)
exec(open("fetch_label_indications.py").read().split("# ── Main loop")[0])
# Reuse granular category mapper
_cat_src = open("update_disease_category.py").read().split("# ── Apply")[0]
exec(_cat_src)

CLEAN   = "orangebook_chronic_indications_clean.csv"
CHRONIC = "orangebook_chronic_drugs.csv"
CLASSIFIED = "orangebook_classified.csv"
PRODUCTS = "data/EOBZIP_2026_05/products.txt"
TARGETS  = "orangebook_drug_targets.csv"

# Known 2024 global revenue (USD B) for the added drugs (blank if not established)
REV = {
    "TIRZEPATIDE": "16.4",     # Mounjaro 11.5 + Zepbound 4.9 (Eli Lilly FY2024)
    "EXENATIDE SYNTHETIC": "", # legacy GLP-1, largely discontinued
}

# ── Load helpers ──────────────────────────────────────────────────────────────
coarse = {r["Ingredient"]: r["Disease_Category"] for r in csv.DictReader(open(CLASSIFIED))}
dur    = {r["Ingredient"]: r["Duration_Class"]   for r in csv.DictReader(open(CLASSIFIED))}
targets = {r["Ingredient"]: r["Gene_Symbol(s)"]  for r in csv.DictReader(open(TARGETS))}

# Dose/route from RLD products (fallback: any active row)
dose_route = {}
for r in csv.DictReader(open(PRODUCTS, encoding="utf-8", errors="replace"), delimiter="~"):
    if r.get("Type") == "DISCN":
        continue
    ing = r["Ingredient"].strip()
    if r.get("RLD", "").upper() == "YES" or ing not in dose_route:
        dose_route[ing] = (r["Strength"].strip(), r["DF;Route"].strip())

def clean_dose(strength, route):
    s = re.sub(r"\*\*.*?\*\*", "", strength).strip()
    s = re.sub(r"\bMG\b", "mg", s); s = re.sub(r"\bML\b", "mL", s)
    s = s.split(" (")[0][:40]
    r = ""
    if "SUBCUTANEOUS" in route: r = "SC"
    elif "INTRAVENOUS" in route: r = "IV"
    elif "INTRATHECAL" in route: r = "intrathecal"
    elif "ORAL" in route: r = "oral"
    return f"{s} {r}".strip()

def infer_freq(route):
    if "SUBCUTANEOUS" in route: return "Weekly or as directed"
    if "INTRATHECAL" in route:  return "Continuous infusion"
    if "ORAL" in route:         return "Once or twice daily"
    return "As directed"

DUR_LABEL = {"CHRONIC": "Indefinite (lifelong maintenance)",
             "LONG-TERM": "Long-term (until progression / disease control)"}

# ── Find missing drugs ────────────────────────────────────────────────────────
clean_rows = list(csv.DictReader(open(CLEAN)))
have = {r["Drug"].upper() for r in clean_rows}
fields = list(clean_rows[0].keys())

chronic = list(csv.DictReader(open(CHRONIC)))
missing = [r for r in chronic if r["Ingredient"].upper() not in have]
print(f"Adding {len(missing)} drugs to clean file")

new_rows = []
for r in missing:
    ing   = r["Ingredient"]
    brand = ""
    for b in r["Trade_Name(s)"].split(" | "):
        b = b.strip()
        if b and "(" not in b and len(b) < 26:
            brand = b; break
    if not brand and r["Trade_Name(s)"]:
        brand = r["Trade_Name(s)"].split(" | ")[0].strip()

    # Indication from openFDA label
    _, raw = fetch_indication(ing, brand)
    phrases = parse_indications(raw) if raw else []
    indication = "; ".join(phrases) if phrases else ""

    # Category (granular) from coarse + indication
    cat = granular_category(coarse.get(ing, "Other"), indication, ing)

    strength, route = dose_route.get(ing, ("", ""))
    row = {
        "Drug": ing.title().replace(" Hydrochloride", " Hydrochloride"),
        "Brand": brand,
        "Disease / Indication": indication or f"{coarse.get(ing,'Chronic')} condition",
        "Category": cat,
        "Target": targets.get(ing, ""),
        "Revenue ($B)": REV.get(ing.upper(), ""),
        "Dose": clean_dose(strength, route),
        "Frequency": infer_freq(route),
        "Duration": DUR_LABEL.get(dur.get(ing, ""), "Indefinite (lifelong maintenance)"),
    }
    new_rows.append(row)
    print(f"  {ing:30s} -> {cat:26s} | {indication[:45]}")

# ── Append + write back (sorted by Drug) ──────────────────────────────────────
import json
try:
    with open("openfda_label_cache.json", "w") as f:
        f.write(json.dumps(cache))
except Exception:
    pass

all_rows = clean_rows + new_rows
all_rows.sort(key=lambda r: r["Drug"].lower())
with open(CLEAN, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader(); w.writerows(all_rows)

print(f"\nClean file now {len(all_rows)} rows -> {CLEAN}")
