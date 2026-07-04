#!/usr/bin/env python3
import json
import csv
from pathlib import Path
from map_drug_diseases import extract_diseases_from_text

CACHE = Path('fda_indications_cache.json')
OUT = Path('purplebook_drug_diseases_from_cache.csv')

if not CACHE.exists():
    raise SystemExit(f"Cache file not found: {CACHE}")

with CACHE.open('r', encoding='utf-8') as f:
    cache = json.load(f)

rows = []
for key, entry in cache.items():
    drug_name = entry.get('drug_name') or entry.get('queried_name') or key
    data = entry.get('data') or {}
    results = data.get('results') or []
    if not results:
        # no results or error
        rows.append({'Drug Name': drug_name, 'Disease': '', 'Source Key': key})
        continue
    any_disease = False
    for record in results:
        ind_list = record.get('indications_and_usage') or []
        if isinstance(ind_list, str):
            ind_list = [ind_list]
        for ind_text in ind_list:
            diseases = extract_diseases_from_text(ind_text)
            if diseases:
                any_disease = True
                for d in diseases:
                    rows.append({'Drug Name': drug_name, 'Disease': d, 'Source Key': key})
    if not any_disease:
        # write a blank disease row
        rows.append({'Drug Name': drug_name, 'Disease': '', 'Source Key': key})

with OUT.open('w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['Drug Name','Disease','Source Key'])
    writer.writeheader()
    writer.writerows(rows)

print(f'Wrote {len(rows)} rows to {OUT}')
