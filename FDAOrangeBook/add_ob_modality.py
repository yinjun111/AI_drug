"""
Add a 'Drug Modality' column to orangebook_chronic_indications_clean.csv,
sourced from the FDA GSRS substance class (orangebook_substance_classes.csv):
chemical / protein / nucleicAcid / polymer / mixture / structurallyDiverse /
concept / specifiedSubstanceG1 / unknown.
Inserted right after the 'Category' column.
"""
import csv, shutil

CLEAN = "orangebook_chronic_indications_clean.csv"
GSRS  = "orangebook_substance_classes.csv"

substance = {}
with open(GSRS, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        substance[r["Ingredient"].upper()] = r.get("Substance_Class", "chemical") or "chemical"

rows = list(csv.DictReader(open(CLEAN, encoding="utf-8")))
fields = list(rows[0].keys())
new_fields = []
for f in fields:
    new_fields.append(f)
    if f == "Category":
        new_fields.append("Drug Modality")
if "Drug Modality" not in new_fields:
    new_fields.append("Drug Modality")

from collections import Counter
for r in rows:
    r["Drug Modality"] = substance.get(r["Drug"].upper(), "chemical")

shutil.copy(CLEAN, CLEAN + ".modbak")
with open(CLEAN, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=new_fields)
    w.writeheader(); w.writerows(rows)

counts = Counter(r["Drug Modality"] for r in rows)
print(f"Backup: {CLEAN}.modbak")
print(f"Rows: {len(rows)}  | 'Drug Modality' inserted after 'Category'")
print("Modality distribution (drug-rows):")
for m, n in counts.most_common():
    print(f"  {n:>4}  {m}")
print(f"Updated -> {CLEAN}")
