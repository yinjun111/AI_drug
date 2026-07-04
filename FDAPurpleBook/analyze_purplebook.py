
import csv, os, glob
from datetime import datetime
from collections import defaultdict

data_dir = r'E:\Work\AI_Drug\purplebook_csvs'
all_new = {}
files = sorted(glob.glob(os.path.join(data_dir, '*.csv')))

for f in files:
    fname = os.path.basename(f)
    with open(f, encoding='utf-8-sig', errors='replace') as fh:
        lines = fh.readlines()
    if fname == '2020_february.csv':
        continue
    hdr_idx = None
    for i, line in enumerate(lines):
        s = line.strip().lstrip(',').strip()
        if s.startswith('N/R/U'):
            hdr_idx = i
            break
    if hdr_idx is None:
        continue
    reader = csv.DictReader(lines[hdr_idx:])
    for row in reader:
        nru = row.get('N/R/U','').strip()
        if nru != 'N':
            continue
        bla = row.get('BLA Number','').strip()
        prod = row.get('Product Number','').strip()
        supp = row.get('Supplement Number','').strip()
        key = (bla, prod, supp)
        if key not in all_new:
            all_new[key] = row

DATE_FMTS = ['%d-%b-%y','%d-%b-%Y','%m/%d/%Y','%Y-%m-%d','%m/%d/%y','%B %d, %Y']
def parse_yr(s):
    s = s.strip()
    for fmt in DATE_FMTS:
        try: return datetime.strptime(s, fmt).year
        except: pass
    return None

def parse_dt(s):
    s = s.strip()
    for fmt in DATE_FMTS:
        try: return datetime.strptime(s, fmt)
        except: pass
    return None

approved = []
still_bad = []
for key, row in all_new.items():
    ds = row.get('Approval Date','').strip()
    yr = parse_yr(ds)
    dt = parse_dt(ds)
    if yr is None:
        still_bad.append(ds)
    elif 2020 <= yr <= 2026:
        approved.append({'year': yr, 'approval_date': ds, '_dt': dt, **row})

print(f'Total unique N records: {len(all_new)}')
print(f'Still unparseable: {len(still_bad)} -- samples: {list(set(still_bad))[:5]}')
print(f'=== Approved 2020-2026: {len(approved)} ===')
print()

def tbl(d, title, top=None):
    items = sorted(d.items(), key=lambda x: -x[1])
    if top:
        items = items[:top]
    print(f'--- {title} ---')
    for k, v in items:
        print(f'  {str(v):>4}  {k}')
    print()

by_year = defaultdict(int)
for r in approved: by_year[r['year']] += 1
tbl(by_year, 'Approvals by Year')

by_type = defaultdict(int)
for r in approved: by_type[r.get('BLA Type','').strip() or 'Unknown'] += 1
tbl(by_type, 'By BLA Type')

by_center = defaultdict(int)
for r in approved: by_center[r.get('Center','').strip() or 'Unknown'] += 1
tbl(by_center, 'By FDA Center (CBER vs CDER)')

by_sub = defaultdict(int)
for r in approved: by_sub[r.get('Submission Type','').strip() or 'Unknown'] += 1
tbl(by_sub, 'By Submission Type')

by_route = defaultdict(int)
for r in approved: by_route[r.get('Route of Administration','').strip() or 'Unknown'] += 1
tbl(by_route, 'By Route of Administration', top=15)

by_form = defaultdict(int)
for r in approved: by_form[r.get('Dosage Form','').strip() or 'Unknown'] += 1
tbl(by_form, 'By Dosage Form', top=12)

by_app = defaultdict(int)
for r in approved: by_app[r.get('Applicant','').strip()] += 1
tbl(by_app, 'Top 25 Applicants', top=25)

biosim = [r for r in approved if '351(k)' in r.get('BLA Type','')]
ref_counts = defaultdict(int)
for r in biosim:
    ref = r.get('Ref. Product Proper Name','').strip()
    if ref and ref not in ('N/A', '-', ''):
        ref_counts[ref] += 1
print(f'--- Biosimilars/Interchangeables 351(k): {len(biosim)} total ---')
tbl(ref_counts, 'Top Reference Products (biosimilar targets)', top=15)

orphan = [r for r in approved if r.get('Orphan Exclusivity Exp. Date','').strip() not in ('','N/A','-')]
print(f'--- Products with Orphan Exclusivity: {len(orphan)} ---')
by_year_orphan = defaultdict(int)
for r in orphan: by_year_orphan[r['year']] += 1
for y in sorted(by_year_orphan.keys()): print(f'  {y}: {by_year_orphan[y]}')
print()

print('--- Type Breakdown by Year ---')
print(f'  {"Year":>4}  {"351(a)":>7}  {"Biosimilar":>10}  {"Interchgbl":>10}  {"Other":>6}')
for y in sorted(by_year.keys()):
    yr_rows = [r for r in approved if r['year'] == y]
    a = sum(1 for r in yr_rows if r.get('BLA Type','') == '351(a)')
    b = sum(1 for r in yr_rows if 'Biosimilar' in r.get('BLA Type',''))
    ic = sum(1 for r in yr_rows if 'Interchangeable' in r.get('BLA Type',''))
    o = len(yr_rows) - a - b - ic
    print(f'  {y:>4}  {a:>7}  {b:>10}  {ic:>10}  {o:>6}')
print()

originals = [r for r in approved if r.get('Submission Type','').strip() in ('Original','Original Application')]
print(f'--- Original (new) BLA approvals 2020-2026: {len(originals)} ---')
by_yr_orig = defaultdict(int)
for r in originals: by_yr_orig[r['year']] += 1
for y in sorted(by_yr_orig.keys()): print(f'  {y}: {by_yr_orig[y]}')
print()

print('Sample original approvals (most recent):')
recent = sorted([r for r in originals if r['_dt']], key=lambda r: r['_dt'], reverse=True)[:15]
for r in recent:
    prop = r.get('Proprietary Name','')[:30]
    proper = r.get('Proper Name','')[:50]
    bla_t = r.get('BLA Type','')
    print(f'  {r["approval_date"]:20s}  {prop:30s}  {bla_t:20s}  {proper}')
