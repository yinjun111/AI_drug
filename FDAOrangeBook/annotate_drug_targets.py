"""
Annotate all Orange Book active ingredients with drug targets from ChEMBL.

Strategy (bulk, fast — minimises API calls):
  1. Download ALL ChEMBL mechanism records (≈ 10k rows) in one paginated pass
     → gives molecule_chembl_id → mechanism_of_action, target_chembl_id, action_type
  2. Download ALL approved (max_phase ≥ 3) molecule names in bulk
     → gives pref_name / synonyms → molecule_chembl_id mapping
  3. Download unique target records in batches of 50
     → gives target_chembl_id → gene_symbol(s), target_name, target_type
  4. For each Orange Book ingredient, name-match → ChEMBL ID → mechanism → target genes
  5. For salt-form or combination ingredients, try each component separately

Output: orangebook_drug_targets.csv
"""

import csv, json, re, time, urllib.parse
from collections import defaultdict
from pathlib import Path
import requests

BASE    = "https://www.ebi.ac.uk/chembl/api/data"
CACHE   = Path("chembl_cache.json")
OUT_CSV = "orangebook_drug_targets.csv"
DELAY   = 0.25   # seconds between requests

# ── Shared session ────────────────────────────────────────────────────────────
S = requests.Session()
S.headers.update({"Accept": "application/json", "User-Agent": "OrangeBook-research/1.0"})

def get(url, retries=3):
    for attempt in range(retries):
        try:
            r = S.get(url, timeout=20)
            if r.status_code == 200 and r.content:
                return r.json()
        except Exception:
            pass
        time.sleep(DELAY * (attempt + 1))
    return {}

def paginate(endpoint, params="", page_size=1000):
    """Yield all records from a paginated ChEMBL endpoint."""
    offset = 0
    while True:
        url = f"{BASE}/{endpoint}?{params}&limit={page_size}&offset={offset}"
        data = get(url)
        records_key = endpoint.split(".")[0]   # e.g. "mechanism" → "mechanisms"
        # Try plural form
        rows = data.get(records_key + "s") or data.get(records_key) or []
        if not rows:
            break
        yield from rows
        meta = data.get("page_meta", {})
        total = meta.get("total_count", 0)
        offset += page_size
        if offset >= total:
            break
        time.sleep(DELAY)

# ── Load or build cache ───────────────────────────────────────────────────────
cache = {}
if CACHE.exists():
    cache = json.loads(CACHE.read_text())
    print(f"Loaded cache: {len(cache.get('mechanisms',{}))} mechs, "
          f"{len(cache.get('mol_name_map',{}))} name→ID entries, "
          f"{len(cache.get('targets',{}))} targets")

# ── Step 1: Download all mechanism records ────────────────────────────────────
if "mechanisms" not in cache:
    print("\nDownloading all ChEMBL mechanism records …")
    mech_map = defaultdict(list)   # mol_chembl_id → [mech_dicts]
    n = 0
    for m in paginate("mechanism.json", ""):
        mol_id = m.get("molecule_chembl_id", "")
        if mol_id:
            mech_map[mol_id].append({
                "moa":         m.get("mechanism_of_action", ""),
                "action_type": m.get("action_type", ""),
                "target_id":   m.get("target_chembl_id", ""),
                "target_name": m.get("target_name", ""),
                "direct":      m.get("direct_interaction", 0),
            })
        n += 1
        if n % 1000 == 0:
            print(f"  … {n} mechanism records", flush=True)
    cache["mechanisms"] = dict(mech_map)
    CACHE.write_text(json.dumps(cache))
    print(f"  Done: {n} records, {len(mech_map)} unique molecules")
else:
    mech_map = defaultdict(list, {k: v for k, v in cache["mechanisms"].items()})
    print(f"Using cached mechanisms: {sum(len(v) for v in mech_map.values())} records")

# ── Step 2: Download approved molecule name → ChEMBL ID map ──────────────────
if "mol_name_map" not in cache:
    print("\nDownloading ChEMBL molecule names (max_phase ≥ 3) …")
    name_to_id = {}   # lower-case name → chembl_id
    n = 0
    for m in paginate("molecule.json", "max_phase__gte=3"):
        cid = m.get("molecule_chembl_id", "")
        if not cid:
            continue
        # Index pref_name
        pname = (m.get("pref_name") or "").strip().lower()
        if pname:
            name_to_id[pname] = cid
        # Index synonyms
        for syn in m.get("molecule_synonyms", []) or []:
            s = (syn.get("synonym") or syn.get("molecule_synonym") or "").strip().lower()
            if s and s not in name_to_id:
                name_to_id[s] = cid
        n += 1
        if n % 1000 == 0:
            print(f"  … {n} molecules", flush=True)
    cache["mol_name_map"] = name_to_id
    CACHE.write_text(json.dumps(cache))
    print(f"  Done: {n} molecules, {len(name_to_id)} name entries")
else:
    name_to_id = cache["mol_name_map"]
    print(f"Using cached name map: {len(name_to_id)} entries")

# ── Step 3: Collect unique target IDs and fetch gene symbols ─────────────────
all_target_ids = set(
    m["target_id"] for mechs in mech_map.values()
    for m in mechs if m.get("target_id")
)
print(f"\nUnique target IDs in mechanism data: {len(all_target_ids)}")

target_cache = cache.get("targets", {})
missing_targets = all_target_ids - set(target_cache.keys())

if missing_targets:
    print(f"Fetching {len(missing_targets)} missing target gene records …")
    ids_list = list(missing_targets)
    BATCH = 50
    for i in range(0, len(ids_list), BATCH):
        batch = ids_list[i:i+BATCH]
        ids_str = ",".join(batch)
        data = get(f"{BASE}/target.json?target_chembl_id__in={urllib.parse.quote(ids_str)}&limit={BATCH}")
        for t in data.get("targets", []):
            tid = t.get("target_chembl_id", "")
            if not tid:
                continue
            comps = t.get("target_components", [])
            genes = []
            for c in comps:
                for syn in c.get("target_component_synonyms", []):
                    if syn.get("syn_type") == "GENE_SYMBOL":
                        g = syn.get("component_synonym", "")
                        if g:
                            genes.append(g)
                # Also check gene_symbol field directly
                g2 = c.get("gene_symbol", "")
                if g2 and g2 not in genes:
                    genes.append(g2)
            target_cache[tid] = {
                "gene_symbols": ", ".join(genes),
                "target_name":  t.get("pref_name", ""),
                "target_type":  t.get("target_type", ""),
                "organism":     t.get("organism", ""),
            }
        if (i // BATCH) % 5 == 0:
            print(f"  … {i+len(batch)}/{len(ids_list)} targets", flush=True)
        time.sleep(DELAY)
    cache["targets"] = target_cache
    CACHE.write_text(json.dumps(cache))

print(f"Target gene records: {len(target_cache)}")

# ── Step 4: Helper — name → ChEMBL ID ────────────────────────────────────────
_SALT_RE = re.compile(
    r"\s+(hydrochloride|hcl|maleate|fumarate|tartrate|succinate|besylate|mesylate"
    r"|sulfate|sodium|potassium|calcium|magnesium|acetate|citrate|phosphate|bromide"
    r"|chloride|nitrate|dimesylate|bitartrate|hydrobromide|monohydrate|dihydrate"
    r"|medoxomil|hyclate|acetonide|furoate|cilexetil|mofetil|olamine|tosylate"
    r"|valerate|propionate|dipropionate|diacetate)\b.*$",
    re.IGNORECASE,
)

def strip_salt(name: str) -> str:
    return _SALT_RE.sub("", name.strip()).strip()

def name_to_chembl(ingredient: str) -> str:
    """Return ChEMBL ID for a drug name using multiple strategies."""
    name = ingredient.lower().strip()

    # 1. Direct
    if name in name_to_id:
        return name_to_id[name]

    # 2. Salt-stripped
    stripped = strip_salt(name)
    if stripped and stripped != name and stripped in name_to_id:
        return name_to_id[stripped]

    # 3. First two words (handles "ATORVASTATIN CALCIUM" → "atorvastatin")
    parts = name.split()
    if len(parts) >= 2:
        for n_words in (2, 1):
            candidate = " ".join(parts[:n_words])
            if candidate in name_to_id:
                return name_to_id[candidate]

    return ""

def format_mechs(chembl_id: str) -> dict:
    """Aggregate mechanism/target info for a ChEMBL molecule."""
    mechs = mech_map.get(chembl_id, [])
    if not mechs:
        return {}

    # Prefer direct_interaction=1 entries; fall back to all
    direct = [m for m in mechs if m.get("direct")]
    pool   = direct or mechs

    genes, tnames, moas, atypes, tids = [], [], [], [], []
    for m in pool:
        tid = m.get("target_id", "")
        tinfo = target_cache.get(tid, {})
        gene  = tinfo.get("gene_symbols", "")
        tname = tinfo.get("target_name", "") or m.get("target_name", "")
        moa   = m.get("moa", "")
        atype = m.get("action_type", "")

        if gene and gene not in genes:   genes.append(gene)
        if tname and tname not in tnames: tnames.append(tname)
        if moa and moa not in moas:      moas.append(moa)
        if atype and atype not in atypes: atypes.append(atype)
        if tid and tid not in tids:      tids.append(tid)

    return {
        "ChEMBL_ID":          chembl_id,
        "Gene_Symbol(s)":     " | ".join(genes),
        "Target_Name(s)":     " | ".join(tnames),
        "Mechanism_of_Action":"; ".join(moas),
        "Action_Type(s)":     " | ".join(atypes),
        "Target_ChEMBL_ID(s)":"; ".join(tids),
        "N_Targets":          len(tids),
    }

# ── Step 5: Process each ingredient ──────────────────────────────────────────
ingredients = []
with open("orangebook_merged_by_ingredient.csv", encoding="utf-8") as fh:
    for row in csv.DictReader(fh):
        ingredients.append(row)

# Load classification and GSRS for context columns
classify = {}
with open("orangebook_classified.csv", encoding="utf-8") as fh:
    for row in csv.DictReader(fh):
        classify[row["Ingredient"]] = row

gsrs = {}
with open("orangebook_substance_classes.csv", encoding="utf-8") as fh:
    for row in csv.DictReader(fh):
        gsrs[row["Ingredient"]] = row

print(f"\nAnnotating {len(ingredients)} ingredients …")

OUT_COLS = [
    "Ingredient", "Trade_Name(s)", "Disease_Category", "Duration_Class",
    "Substance_Class", "ChEMBL_ID",
    "Gene_Symbol(s)", "Target_Name(s)", "Mechanism_of_Action",
    "Action_Type(s)", "Target_ChEMBL_ID(s)", "N_Targets",
    "Match_Strategy",
]

rows_out = []
n_matched = 0

for ing_row in ingredients:
    ing = ing_row["Ingredient"]
    cl  = classify.get(ing, {})
    g   = gsrs.get(ing, {})
    trade = ing_row.get("Trade_Name(s)", "")

    result = {
        "Ingredient":       ing,
        "Trade_Name(s)":    trade,
        "Disease_Category": cl.get("Disease_Category", ""),
        "Duration_Class":   cl.get("Duration_Class", ""),
        "Substance_Class":  g.get("Substance_Class", ""),
        "ChEMBL_ID":        "",
        "Gene_Symbol(s)":   "",
        "Target_Name(s)":   "",
        "Mechanism_of_Action": "",
        "Action_Type(s)":   "",
        "Target_ChEMBL_ID(s)": "",
        "N_Targets":        0,
        "Match_Strategy":   "not_found",
    }

    # Handle combination products — try each component
    parts = [p.strip() for p in ing.split(";")]
    all_mechs = []

    for part in parts:
        cid = name_to_chembl(part)
        if not cid:
            continue
        minfo = format_mechs(cid)
        if minfo:
            all_mechs.append((part, cid, minfo))

    if all_mechs:
        n_matched += 1
        if len(all_mechs) == 1:
            part, cid, minfo = all_mechs[0]
            result.update(minfo)
            result["Match_Strategy"] = "direct" if part.lower() == ing.lower() else "component"
        else:
            # Combination: merge all component targets
            all_genes  = []
            all_tnames = []
            all_moas   = []
            all_atypes = []
            all_tids   = []
            all_cids   = []
            for part, cid, minfo in all_mechs:
                all_cids.append(cid)
                for g_str in minfo.get("Gene_Symbol(s)", "").split(" | "):
                    if g_str and g_str not in all_genes: all_genes.append(g_str)
                for t in minfo.get("Target_Name(s)", "").split(" | "):
                    if t and t not in all_tnames: all_tnames.append(t)
                for m in minfo.get("Mechanism_of_Action", "").split("; "):
                    if m and m not in all_moas: all_moas.append(m)
                for a in minfo.get("Action_Type(s)", "").split(" | "):
                    if a and a not in all_atypes: all_atypes.append(a)
                for t in minfo.get("Target_ChEMBL_ID(s)", "").split("; "):
                    if t and t not in all_tids: all_tids.append(t)
            result["ChEMBL_ID"]           = " | ".join(all_cids)
            result["Gene_Symbol(s)"]       = " | ".join(all_genes)
            result["Target_Name(s)"]       = " | ".join(all_tnames)
            result["Mechanism_of_Action"]  = "; ".join(all_moas)
            result["Action_Type(s)"]       = " | ".join(all_atypes)
            result["Target_ChEMBL_ID(s)"] = "; ".join(all_tids)
            result["N_Targets"]            = len(all_tids)
            result["Match_Strategy"]       = "combination"

    rows_out.append(result)

with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=OUT_COLS)
    writer.writeheader()
    writer.writerows(rows_out)

# ── Summary ───────────────────────────────────────────────────────────────────
from collections import Counter
n_with_gene = sum(1 for r in rows_out if r["Gene_Symbol(s)"])
n_with_moa  = sum(1 for r in rows_out if r["Mechanism_of_Action"])
targets_dist = Counter(r["N_Targets"] for r in rows_out)

print(f"\n{'='*60}")
print(f"Output → {OUT_CSV}")
print(f"Total ingredients:              {len(rows_out):>5}")
print(f"With ChEMBL mechanism data:     {n_matched:>5} ({100*n_matched/len(rows_out):.1f}%)")
print(f"With gene symbol(s):            {n_with_gene:>5} ({100*n_with_gene/len(rows_out):.1f}%)")
print(f"With mechanism_of_action text:  {n_with_moa:>5} ({100*n_with_moa/len(rows_out):.1f}%)")

print("\nSample results:")
for r in sorted(rows_out, key=lambda x: -x["N_Targets"])[:10]:
    print(f"  {r['Ingredient'][:35]:<35} genes={r['Gene_Symbol(s)'][:45]}")
