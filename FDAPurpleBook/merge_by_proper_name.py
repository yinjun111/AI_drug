
import csv
import glob
import os
from collections import defaultdict

DATA_DIR = r'E:\Work\AI_Drug\purplebook_csvs'
OUT_FILE  = r'E:\Work\AI_Drug\purplebook_merged_by_proper_name.csv'

# Each proper name maps to a dict of sets for multi-valued fields
records = defaultdict(lambda: {
    'file_names':     set(),
    'applicants':     set(),
    'bla_numbers':    set(),
    'prop_names':     set(),
    'strengths':      set(),
    'dosage_forms':   set(),
    'routes':         set(),
    'approval_dates': set(),
})

files = sorted(glob.glob(os.path.join(DATA_DIR, '*.csv')))

for f in files:
    fname = os.path.basename(f)
    if fname == '2020_february.csv':   # full dump, no N/R/U flags
        continue
    with open(f, encoding='utf-8-sig', errors='replace') as fh:
        lines = fh.readlines()

    hdr_idx = next(
        (i for i, line in enumerate(lines)
         if line.strip().lstrip(',').startswith('N/R/U')),
        None
    )
    if hdr_idx is None:
        continue

    for row in csv.DictReader(lines[hdr_idx:]):
        if row.get('N/R/U', '').strip() != 'N':
            continue

        proper = row.get('Proper Name', '').strip()
        if not proper:
            continue

        rec = records[proper]
        rec['file_names'].add(fname)

        def add(field, key):
            v = row.get(key, '').strip()
            if v and v not in ('N/A', '-'):
                field.add(v)

        add(rec['applicants'],     'Applicant')
        add(rec['bla_numbers'],    'BLA Number')
        add(rec['prop_names'],     'Proprietary Name')
        add(rec['strengths'],      'Strength')
        add(rec['dosage_forms'],   'Dosage Form')
        add(rec['routes'],         'Route of Administration')
        add(rec['approval_dates'], 'Approval Date')


SEP = ' | '

def join(s):
    return SEP.join(sorted(s))

OUT_COLS = [
    'Proper Name',
    'File Name(s)',
    'Applicant(s)',
    'BLA Number(s)',
    'Proprietary Name(s)',
    'Strength (merged)',
    'Dosage Form(s)',
    'Route of Administration',
    'Approval Date(s)',
]

with open(OUT_FILE, 'w', newline='', encoding='utf-8-sig') as out:
    writer = csv.DictWriter(out, fieldnames=OUT_COLS)
    writer.writeheader()
    for proper in sorted(records.keys(), key=str.lower):
        rec = records[proper]
        writer.writerow({
            'Proper Name':              proper,
            'File Name(s)':             join(rec['file_names']),
            'Applicant(s)':             join(rec['applicants']),
            'BLA Number(s)':            join(rec['bla_numbers']),
            'Proprietary Name(s)':      join(rec['prop_names']),
            'Strength (merged)':        join(rec['strengths']),
            'Dosage Form(s)':           join(rec['dosage_forms']),
            'Route of Administration':  join(rec['routes']),
            'Approval Date(s)':         join(rec['approval_dates']),
        })

print(f'Merged {len(records)} unique Proper Names → {OUT_FILE}')
