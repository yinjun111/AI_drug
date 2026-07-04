"""
Annotate all unique Orange Book active ingredients with FDA GSRS substanceClass
using ToolUniverse FDAGSRS_search_substances.

Strategy per ingredient:
  1. Query the full name; look for case-insensitive exact match.
  2. If no exact match, strip salt/form suffix and re-query.
  3. For combination products (semicolon-delimited), query each component
     and return the unique set of classes found.
  4. Cache every API result to JSON so the run is resumable.

Output: orangebook_substance_classes.csv
"""

import csv, json, re, time, os, sys
from pathlib import Path
from tooluniverse import ToolUniverse

# ── Paths ────────────────────────────────────────────────────────────────────
IN_CSV     = "orangebook_merged_by_ingredient.csv"
OUT_CSV    = "orangebook_substance_classes.csv"
CACHE_FILE = "gsrs_cache.json"

# ── Init ToolUniverse (load only the one tool needed) ────────────────────────
print("Loading ToolUniverse …", flush=True)
tu = ToolUniverse()
tu.load_tools(include_tools=["FDAGSRS_search_substances"])
print("Ready.\n", flush=True)

# ── Load cache ───────────────────────────────────────────────────────────────
cache: dict = {}
if Path(CACHE_FILE).exists():
    with open(CACHE_FILE) as fh:
        cache = json.load(fh)
    print(f"Loaded {len(cache)} cached queries from {CACHE_FILE}", flush=True)

def save_cache():
    with open(CACHE_FILE, "w") as fh:
        json.dump(cache, fh)

# ── Salt-stripping regex (same as classify_chronic.py) ───────────────────────
_SALT_RE = re.compile(
    r"\s+(hydrochloride|hcl|maleate|fumarate|tartrate|succinate|besylate|mesylate"
    r"|tosylate|sulfate|sodium|potassium|calcium|magnesium|zinc|acetate|citrate"
    r"|phosphate|stearate|bromide|iodide|chloride|nitrate|oxalate|gluconate"
    r"|glucuronate|benzoate|diacetate|dipropionate|propionate|valerate|butyrate"
    r"|laurate|palmitate|oleate|decanoate|cypionate|enanthate|pamoate|lactate"
    r"|dimesylate|saccharate|bitartrate|monohydrate|dihydrate|anhydrous"
    r"|monosodium|disodium|trisodium|bicalcium|hemicalcium|hydrate|solvate"
    r"|hydroiodide|hydrobromide|bisulfate|olamine|meglumine|piperazine"
    r"|dihydrochloride|trihydrochloride|monohydrochloride"
    r"|medoxomil|hyclate|acetonide|furoate|pivalate|cilexetil|mofetil|axetil"
    r"|f-18|f 18|tc-99m|n-13"
    r")\b.*$",
    re.IGNORECASE,
)

def strip_salt(name: str) -> str:
    return _SALT_RE.sub("", name.strip()).strip()

# ── API wrapper with cache ───────────────────────────────────────────────────
RATE_DELAY = 0.25   # seconds between requests

def query_gsrs(query: str, limit: int = 5) -> list:
    """Return list of result dicts from GSRS, using cache."""
    key = query.lower().strip()
    if key in cache:
        return cache[key]

    try:
        result = tu.run_one_function(
            {"name": "FDAGSRS_search_substances",
             "arguments": {"query": query, "limit": limit}},
            use_cache=False,
        )
        data = result.get("data", []) if isinstance(result, dict) else []
    except Exception as e:
        data = []   # network / parse error → treat as not found

    cache[key] = data
    time.sleep(RATE_DELAY)
    return data

# ── Match logic ──────────────────────────────────────────────────────────────
UNKNOWN = "unknown"

def best_match(results: list, query_name: str) -> dict | None:
    """
    Pick the best result:
      - Prefer exact name match (case-insensitive).
      - Prefer 'approved' status over others.
      - Fall back to first result.
    Returns the matched record or None.
    """
    if not results:
        return None
    q = query_name.lower().strip()
    # exact name match
    for r in results:
        if r.get("name", "").lower().strip() == q:
            return r
    # approved status first
    approved = [r for r in results if r.get("status") == "approved"]
    return (approved or results)[0]

def classify_ingredient(ingredient: str):
    """
    Returns dict with keys:
      matched_name, unii, substance_class, gsrs_status,
      query_used, match_type, all_classes (for combos)
    """
    parts = [p.strip() for p in ingredient.split(";")]
    is_combo = len(parts) > 1

    records = []   # (part_name, matched_record | None, match_type)

    for part in parts:
        # 1. try full part name
        res1 = query_gsrs(part)
        rec  = best_match(res1, part)
        mtype = "exact_full"

        # 2. if no match, try salt-stripped
        if rec is None:
            stripped = strip_salt(part)
            if stripped and stripped.lower() != part.lower():
                res2 = query_gsrs(stripped)
                rec  = best_match(res2, stripped)
                mtype = "salt_stripped"

        # 3. if still no match, use first result from full query regardless
        if rec is None and res1:
            rec   = res1[0]
            mtype = "first_result"

        if rec is None:
            mtype = "not_found"

        records.append((part, rec, mtype))

    if not is_combo:
        part, rec, mtype = records[0]
        if rec:
            return {
                "Matched_GSRS_Name":  rec.get("name", ""),
                "UNII":               rec.get("unii", ""),
                "Substance_Class":    rec.get("substanceClass", UNKNOWN),
                "GSRS_Status":        rec.get("status", ""),
                "Query_Used":         part,
                "Match_Type":         mtype,
                "All_Classes":        rec.get("substanceClass", UNKNOWN),
                "Formula":            rec.get("formula", ""),
                "SMILES":             rec.get("smiles", ""),
            }
        else:
            return {
                "Matched_GSRS_Name":  "",
                "UNII":               "",
                "Substance_Class":    UNKNOWN,
                "GSRS_Status":        "",
                "Query_Used":         part,
                "Match_Type":         "not_found",
                "All_Classes":        UNKNOWN,
                "Formula":            "",
                "SMILES":             "",
            }
    else:
        # combination: collect classes from all matched components
        classes = []
        names, uniis, statuses, qtypes = [], [], [], []
        for part, rec, mtype in records:
            if rec:
                classes.append(rec.get("substanceClass", UNKNOWN))
                names.append(rec.get("name", ""))
                uniis.append(rec.get("unii", ""))
                statuses.append(rec.get("status", ""))
                qtypes.append(mtype)
            else:
                classes.append(UNKNOWN)
                qtypes.append("not_found")

        unique_classes = list(dict.fromkeys(classes))   # preserve order, dedupe
        # primary class = most informative (protein/nucleic acid > chemical > unknown)
        priority = {"protein": 0, "nucleic acid": 1, "polymer": 2,
                    "structurally diverse": 3, "mixture": 4, "chemical": 5, UNKNOWN: 99}
        primary = sorted(unique_classes, key=lambda c: priority.get(c, 10))[0]

        return {
            "Matched_GSRS_Name":  " | ".join(names),
            "UNII":               " | ".join(uniis),
            "Substance_Class":    primary,
            "GSRS_Status":        " | ".join(statuses),
            "Query_Used":         ingredient,
            "Match_Type":         "combination(" + ",".join(qtypes) + ")",
            "All_Classes":        " | ".join(unique_classes),
            "Formula":            "",
            "SMILES":             "",
        }

# ── Load ingredients ──────────────────────────────────────────────────────────
ingredients = []
with open(IN_CSV, encoding="utf-8") as fh:
    for row in csv.DictReader(fh):
        ingredients.append(row["Ingredient"])

print(f"Total ingredients to annotate: {len(ingredients)}", flush=True)

# ── Load already-completed rows ───────────────────────────────────────────────
done: dict = {}
if Path(OUT_CSV).exists():
    with open(OUT_CSV, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            done[row["Ingredient"]] = row
    print(f"Resuming: {len(done)} already annotated", flush=True)

# ── Run annotations ───────────────────────────────────────────────────────────
OUT_COLS = [
    "Ingredient", "Matched_GSRS_Name", "UNII", "Substance_Class",
    "GSRS_Status", "Query_Used", "Match_Type", "All_Classes",
    "Formula", "SMILES",
]

# Open output in append mode if resuming, write mode if fresh
mode = "a" if done else "w"
out_fh = open(OUT_CSV, mode, newline="", encoding="utf-8")
writer = csv.DictWriter(out_fh, fieldnames=OUT_COLS, extrasaction="ignore")
if not done:
    writer.writeheader()

n_done     = len(done)
n_total    = len(ingredients)
save_every = 50   # save cache every N requests

try:
    for i, ing in enumerate(ingredients):
        if ing in done:
            continue   # skip already done

        ann = classify_ingredient(ing)
        row = {"Ingredient": ing, **ann}
        writer.writerow(row)
        out_fh.flush()
        done[ing] = row
        n_done += 1

        # Progress
        pct = 100 * n_done / n_total
        sc  = ann["Substance_Class"]
        print(f"[{n_done:>4}/{n_total}  {pct:5.1f}%]  {sc:<22}  {ing[:55]}", flush=True)

        # Periodic cache save
        if n_done % save_every == 0:
            save_cache()

except KeyboardInterrupt:
    print("\nInterrupted — saving cache …", flush=True)
finally:
    out_fh.close()
    save_cache()
    print(f"\nDone. {n_done}/{n_total} annotated → {OUT_CSV}")

# ── Summary ───────────────────────────────────────────────────────────────────
from collections import Counter
if done:
    counts = Counter(r["Substance_Class"] for r in done.values())
    print("\nSubstance class breakdown:")
    for cls, n in counts.most_common():
        pct = 100 * n / len(done)
        print(f"  {cls:<30}  {n:>5}  ({pct:.1f}%)")
