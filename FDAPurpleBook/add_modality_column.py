"""
Add a 'Drug Modality' column to purplebook_chronic_drugs_indications2.csv.

The modality classification (Monoclonal Antibody / Fusion Protein /
Enzyme / Protein Replacement / Peptide / Hormone / Polyclonal Immunoglobulin /
Allergen / Vaccine) already exists as MODALITY_MAP inside the Purple Book
dashboard (chronic_use_dashboard.html). We extract that authoritative map and
join it onto the CSV by 'Drug (Proper Name)'.
"""
import csv, re, json, shutil

CSV_FILE  = "chronic_drugs_indications2.csv"
DASHBOARD = "chronic_use_dashboard.html"

# ── Extract MODALITY_MAP from the dashboard ───────────────────────────────────
html = open(DASHBOARD, encoding="utf-8").read()
m = re.search(r"const MODALITY_MAP\s*=\s*(\{.*?\})\s*;", html, re.DOTALL)
if not m:
    raise SystemExit("MODALITY_MAP not found in dashboard")
MODALITY_MAP = json.loads(m.group(1))
print(f"Loaded MODALITY_MAP: {len(MODALITY_MAP)} drugs")

# ── Read CSV, insert 'Drug Modality' after 'Disease Category' ─────────────────
rows = list(csv.DictReader(open(CSV_FILE, encoding="utf-8-sig")))
fields = list(rows[0].keys())

new_fields = []
for f in fields:
    new_fields.append(f)
    if f == "Disease Category":
        new_fields.append("Drug Modality")
if "Drug Modality" not in new_fields:          # fallback: append at end
    new_fields.append("Drug Modality")

unmapped = set()
for r in rows:
    drug = r["Drug (Proper Name)"].strip()
    mod = MODALITY_MAP.get(drug)
    if mod is None:
        # try case-insensitive match
        for k, v in MODALITY_MAP.items():
            if k.lower() == drug.lower():
                mod = v
                break
    if mod is None:
        mod = "Other"
        unmapped.add(drug)
    r["Drug Modality"] = mod

# ── Back up and write ─────────────────────────────────────────────────────────
shutil.copy(CSV_FILE, CSV_FILE + ".bak")
with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=new_fields)
    w.writeheader()
    w.writerows(rows)

# ── Summary ───────────────────────────────────────────────────────────────────
from collections import Counter
counts = Counter(r["Drug Modality"] for r in rows)
uniq_counts = Counter()
seen = set()
for r in rows:
    d = r["Drug (Proper Name)"]
    if d not in seen:
        seen.add(d); uniq_counts[r["Drug Modality"]] += 1

print(f"\nBackup: {CSV_FILE}.bak")
print(f"Rows: {len(rows)}  |  new column 'Drug Modality' inserted after 'Disease Category'")
print("\nModality distribution (unique drugs):")
for mod, n in uniq_counts.most_common():
    print(f"  {n:>3}  {mod}")
if unmapped:
    print(f"\nUnmapped drugs (-> 'Other'): {sorted(unmapped)}")
print(f"\nUpdated -> {CSV_FILE}")
