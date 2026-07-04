"""
Fetch FDA-approved indications from openFDA drug labels for each chronic
Orange Book ingredient, parse into disease phrases, and:
  1. write orangebook_drug_disease_indications.csv   (separate detail file)
  2. update orangebook_chronic_indications_clean.csv  (real indications in place)

openFDA: 1,000 requests/day without an API key (240/min). Cached + resumable.
"""

import csv, json, re, time, sys
from pathlib import Path
import requests

CLEAN_CSV = "orangebook_chronic_indications_clean.csv"
OUT_DETAIL = "orangebook_drug_disease_indications.csv"
CACHE = Path("openfda_label_cache.json")

API = "https://api.fda.gov/drug/label.json"
DELAY = 0.30          # ~200/min, under the 240/min ceiling
DAILY_BUDGET = 960    # stay under the 1,000/day no-key limit

# ── Salt / form suffixes to strip for name matching ──────────────────────────
_SALT_RE = re.compile(
    r"\s+(hydrochloride|hcl|maleate|fumarate|tartrate|succinate|besylate|mesylate"
    r"|tosylate|sulfate|sodium|potassium|calcium|magnesium|zinc|acetate|citrate"
    r"|phosphate|bromide|chloride|nitrate|oxalate|gluconate|bitartrate|dimesylate"
    r"|hydrobromide|monohydrate|dihydrate|medoxomil|hyclate|furoate|cilexetil"
    r"|mofetil|olamine|xinafoate|dipropionate|propionate|valerate|pamoate"
    r"|disoproxil|alafenamide|hemifumarate|d-tartrate|s-malate|malate)\b.*$",
    re.IGNORECASE,
)

def strip_salt(name: str) -> str:
    return _SALT_RE.sub("", name.strip()).strip()

# ── Load cache ───────────────────────────────────────────────────────────────
cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
print(f"Cache: {len(cache)} entries loaded", flush=True)

req_count = 0

def api_search(field: str, value: str):
    """One openFDA query; returns indications_and_usage text or None."""
    global req_count
    if req_count >= DAILY_BUDGET:
        raise RuntimeError("daily-budget-reached")
    params = {"search": f'{field}:"{value}"', "limit": 1}
    try:
        r = requests.get(API, params=params, timeout=15)
        req_count += 1
        time.sleep(DELAY)
        if r.status_code == 429:
            raise RuntimeError("rate-limited-429")
        if r.status_code != 200:
            return None
        results = r.json().get("results", [])
        if not results:
            return None
        txt = results[0].get("indications_and_usage", [""])
        return txt[0] if txt else None
    except RuntimeError:
        raise
    except Exception:
        return None

def fetch_indication(drug: str, brand: str):
    """Return (matched_query, raw_text) for a drug, using multiple strategies."""
    key = drug.lower()
    if key in cache:
        c = cache[key]
        return c.get("matched", ""), c.get("raw", "")

    is_combo = ";" in drug
    components = [strip_salt(p) for p in drug.split(";")]
    components = [c for c in components if c]

    queries = []
    # Combo: brand first (combo product's own label), then components
    if is_combo:
        if brand:
            queries.append(("openfda.brand_name", brand.split("/")[0].split(",")[0].strip()))
        queries.append(("openfda.generic_name", " and ".join(components)))
        for comp in components:
            queries.append(("openfda.generic_name", comp))
    else:
        base = components[0] if components else strip_salt(drug)
        queries.append(("openfda.generic_name", base))
        queries.append(("openfda.substance_name", base))
        if brand:
            queries.append(("openfda.brand_name", brand.split("/")[0].split(",")[0].strip()))

    matched, raw = "", ""
    for field, value in queries:
        if not value:
            continue
        txt = api_search(field, value)
        if txt:
            matched, raw = f"{field}={value}", txt
            break

    cache[key] = {"matched": matched, "raw": raw}
    return matched, raw

# ── Parse label text into disease phrases ────────────────────────────────────
def clean_text(t: str) -> str:
    t = re.sub(r"^\s*\d+(\.\d+)?\s*INDICATIONS?\s+AND\s+USAGE\s*", "", t, flags=re.I)
    t = re.sub(r"\[see[^\]]*\]", "", t, flags=re.I)      # cross-references
    t = re.sub(r"\(\s*\d+(\.\d+)?\s*\)", "", t)            # section refs like (1.2)
    t = re.sub(r"\s+", " ", t).strip()
    return t

# ── Disease dictionary — (regex, canonical name). Ordered specific → general
#    so "non-small cell lung cancer" wins over "lung cancer", etc.
DISEASE_DICT = [
    # Oncology (specific first)
    (r"non[- ]small cell lung (cancer|carcinoma)|nsclc",  "Non-small cell lung cancer"),
    (r"small cell lung (cancer|carcinoma)",               "Small cell lung cancer"),
    (r"chronic myeloid leukemia|chronic myelogenous leukemia|\bcml\b", "Chronic myeloid leukemia"),
    (r"chronic lymphocytic leukemia|\bcll\b",             "Chronic lymphocytic leukemia"),
    (r"acute myeloid leukemia|\baml\b",                   "Acute myeloid leukemia"),
    (r"acute lymphoblastic leukemia|acute lymphocytic leukemia", "Acute lymphoblastic leukemia"),
    (r"multiple myeloma",                                 "Multiple myeloma"),
    (r"myelodysplastic",                                  "Myelodysplastic syndromes"),
    (r"myelofibrosis",                                    "Myelofibrosis"),
    (r"(hodgkin|non[- ]hodgkin).{0,15}lymphoma|mantle cell lymphoma|follicular lymphoma|\blymphoma\b", "Lymphoma"),
    (r"breast (cancer|carcinoma)",                        "Breast cancer"),
    (r"prostate (cancer|carcinoma)",                      "Prostate cancer"),
    (r"colorectal (cancer|carcinoma)|colon cancer",       "Colorectal cancer"),
    (r"ovarian (cancer|carcinoma)",                       "Ovarian cancer"),
    (r"pancreatic (cancer|carcinoma)",                    "Pancreatic cancer"),
    (r"renal cell (cancer|carcinoma)|\brcc\b",            "Renal cell carcinoma"),
    (r"thyroid (cancer|carcinoma)",                       "Thyroid cancer"),
    (r"hepatocellular (cancer|carcinoma)|\bhcc\b",        "Hepatocellular carcinoma"),
    (r"gastric (cancer|carcinoma)|stomach cancer",        "Gastric cancer"),
    (r"bladder (cancer|carcinoma)|urothelial",            "Bladder / urothelial cancer"),
    (r"melanoma",                                         "Melanoma"),
    (r"glioblastoma|glioma",                              "Glioblastoma"),
    (r"cervical cancer",                                  "Cervical cancer"),
    (r"head and neck (cancer|carcinoma)",                 "Head & neck cancer"),
    (r"basal cell carcinoma",                             "Basal cell carcinoma"),

    # Metabolic / endocrine (specific first)
    (r"type 2 diabetes|type ii diabetes|non[- ]insulin[- ]dependent diabetes", "Type 2 diabetes"),
    (r"type 1 diabetes|type i diabetes|insulin[- ]dependent diabetes",         "Type 1 diabetes"),
    (r"diabetes mellitus|diabetic",                       "Diabetes mellitus"),
    (r"familial hypercholesterolemia",                    "Familial hypercholesterolemia"),
    (r"hypercholesterolemia|hyperlipidemia|dyslipidemia|elevated (ldl|cholesterol|triglyceride)", "Dyslipidemia / hypercholesterolemia"),
    (r"hypertriglyceridemia",                             "Hypertriglyceridemia"),
    (r"\bobesity\b|chronic weight management|weight (loss|reduction)|overweight", "Obesity / weight management"),
    (r"hypothyroidism",                                   "Hypothyroidism"),
    (r"hyperthyroidism",                                  "Hyperthyroidism"),
    (r"osteoporosis",                                     "Osteoporosis"),
    (r"\bgout\b|gouty",                                   "Gout"),
    (r"hyperuricemia",                                    "Hyperuricemia"),
    (r"hyperkalemia",                                     "Hyperkalemia"),
    (r"hyperphosphatemia",                                "Hyperphosphatemia"),
    (r"hypogonadism|testosterone deficiency",             "Hypogonadism"),
    (r"growth hormone deficiency|growth failure|short stature", "Growth hormone deficiency"),
    (r"cushing",                                          "Cushing's syndrome"),
    (r"acromegaly",                                       "Acromegaly"),
    (r"vitamin d deficiency|hypocalcemia|secondary hyperparathyroidism", "Mineral / vitamin D disorder"),
    (r"anemia",                                           "Anemia"),

    # Cardiovascular
    (r"heart failure|\bhfref\b|\bhfpef\b",                "Heart failure"),
    (r"atrial fibrillation|\bafib\b",                     "Atrial fibrillation"),
    (r"hypertension|high blood pressure|blood pressure",  "Hypertension"),
    (r"pulmonary arterial hypertension|\bpah\b",          "Pulmonary arterial hypertension"),
    (r"\bangina\b",                                       "Angina"),
    (r"myocardial infarction",                            "Myocardial infarction (risk reduction)"),
    (r"\bstroke\b",                                       "Stroke (risk reduction)"),
    (r"deep vein thrombosis|\bdvt\b|venous thrombosis",   "DVT / venous thrombosis"),
    (r"pulmonary embolism",                               "Pulmonary embolism"),
    (r"venous thromboembolism|\bvte\b|thromboembolic",    "Venous thromboembolism"),
    (r"coronary artery disease|coronary heart disease",   "Coronary artery disease"),
    (r"arrhythmia|ventricular (fibrillation|tachycardia)|supraventricular", "Cardiac arrhythmia"),

    # Psychiatric
    (r"schizophrenia|schizoaffective",                    "Schizophrenia"),
    (r"bipolar",                                          "Bipolar disorder"),
    (r"major depressive disorder|\bmdd\b|depression",     "Major depressive disorder"),
    (r"generalized anxiety|\bgad\b|anxiety",              "Anxiety disorder"),
    (r"attention deficit|\badhd\b",                       "ADHD"),
    (r"obsessive[- ]compulsive|\bocd\b",                  "Obsessive-compulsive disorder"),
    (r"panic disorder",                                   "Panic disorder"),
    (r"post[- ]?traumatic stress|\bptsd\b",               "PTSD"),
    (r"insomnia",                                         "Insomnia"),
    (r"narcolepsy|excessive (daytime )?sleepiness",       "Narcolepsy / EDS"),
    (r"tardive dyskinesia",                               "Tardive dyskinesia"),
    (r"opioid (use disorder|dependence|addiction)",       "Opioid use disorder"),
    (r"alcohol (use disorder|dependence)",                "Alcohol use disorder"),
    (r"smoking cessation|nicotine dependence",            "Smoking cessation"),

    # Neurology
    (r"\bepilepsy\b|seizure|partial[- ]onset|convulsi",   "Epilepsy / seizures"),
    (r"parkinson",                                        "Parkinson's disease"),
    (r"alzheimer|dementia",                               "Alzheimer's disease / dementia"),
    (r"multiple sclerosis|relapsing.{0,20}multiple",     "Multiple sclerosis"),
    (r"migraine",                                         "Migraine"),
    (r"neuropathic pain|diabetic neuropathy|postherpetic neuralgia|fibromyalgia", "Neuropathic pain / fibromyalgia"),
    (r"restless legs",                                    "Restless legs syndrome"),
    (r"myasthenia gravis",                                "Myasthenia gravis"),
    (r"amyotrophic lateral sclerosis|\bals\b",            "ALS"),
    (r"huntington",                                       "Huntington's disease"),
    (r"spasticity",                                       "Spasticity"),
    (r"overactive bladder|urinary (incontinence|urgency|frequency)", "Overactive bladder"),

    # Respiratory
    (r"\basthma\b",                                       "Asthma"),
    (r"chronic obstructive pulmonary|\bcopd\b|emphysema|chronic bronchitis", "COPD"),
    (r"allergic rhinitis|hay fever|nasal congestion",     "Allergic rhinitis"),
    (r"cystic fibrosis",                                  "Cystic fibrosis"),
    (r"(idiopathic )?pulmonary fibrosis",                 "Pulmonary fibrosis"),
    (r"bronchospasm|bronchoconstriction",                 "Bronchospasm"),

    # GI
    (r"gastroesophageal reflux|\bgerd\b|erosive esophagitis|heartburn", "GERD"),
    (r"peptic ulcer|duodenal ulcer|gastric ulcer",        "Peptic ulcer disease"),
    (r"crohn",                                            "Crohn's disease"),
    (r"ulcerative colitis",                               "Ulcerative colitis"),
    (r"irritable bowel|\bibs\b",                          "Irritable bowel syndrome"),
    (r"chronic (idiopathic )?constipation|opioid[- ]induced constipation", "Chronic constipation"),
    (r"short bowel syndrome",                             "Short bowel syndrome"),
    (r"primary biliary (cholangitis|cirrhosis)",          "Primary biliary cholangitis"),
    (r"exocrine pancreatic insufficiency",                "Exocrine pancreatic insufficiency"),
    (r"nausea|vomiting|emesis",                           "Nausea / vomiting"),

    # Autoimmune / rheum / derm
    (r"rheumatoid arthritis",                             "Rheumatoid arthritis"),
    (r"psoriatic arthritis",                              "Psoriatic arthritis"),
    (r"plaque psoriasis|\bpsoriasis\b",                   "Psoriasis"),
    (r"ankylosing spondylitis|axial spondyloarthritis",   "Ankylosing spondylitis"),
    (r"systemic lupus|\bsle\b|lupus",                     "Systemic lupus erythematosus"),
    (r"atopic dermatitis|eczema",                         "Atopic dermatitis"),
    (r"\bacne\b",                                         "Acne"),
    (r"rosacea",                                          "Rosacea"),

    # Infectious
    (r"\bhiv\b|human immunodeficiency",                   "HIV infection"),
    (r"hepatitis b|\bhbv\b",                              "Hepatitis B"),
    (r"hepatitis c|\bhcv\b",                              "Hepatitis C"),
    (r"tuberculosis",                                     "Tuberculosis"),
    (r"cytomegalovirus|\bcmv\b",                          "Cytomegalovirus"),
    (r"influenza",                                        "Influenza"),
    (r"herpes|\bhsv\b",                                   "Herpes"),

    # Ophthalmology
    (r"glaucoma|ocular hypertension|intraocular pressure","Glaucoma / ocular hypertension"),
    (r"macular (degeneration|edema)|\bamd\b",             "Macular degeneration / edema"),
    (r"dry eye",                                          "Dry eye disease"),

    # Pain / urology
    (r"osteoarthritis",                                   "Osteoarthritis"),
    (r"chronic pain|moderate to severe pain|management of pain", "Chronic pain"),
    (r"benign prostatic hyperplasia|\bbph\b|prostatic",   "Benign prostatic hyperplasia"),
    (r"erectile dysfunction",                             "Erectile dysfunction"),
    (r"endometriosis",                                    "Endometriosis"),
    (r"contracepti|pregnancy prevention",                 "Contraception"),
    (r"menopaus|vasomotor|hot flash|hormone (replacement|therapy)", "Menopausal / hormone therapy"),

    # Renal
    (r"chronic kidney disease|\bckd\b|renal impairment|diabetic (kidney|nephropathy)", "Chronic kidney disease"),
]
_DISEASE_COMPILED = [(re.compile(pat, re.I), name) for pat, name in DISEASE_DICT]

_TRIGGER = re.compile(
    r"indicated\s+(?:for(?:\s+the\s+(?:treatment|management|prophylaxis|"
    r"prevention)\s+of|\s+use\s+in)?|to\s+(?:reduce|treat|improve|prevent|"
    r"control|decrease|lower)|in\s+the\s+treatment\s+of|as\s+(?:an?\s+)?)",
    re.I,
)
# Cut markers: indication clause ends at these boilerplate sections
_END = re.compile(
    r"(limitations? of use|dosage and administration|contraindications|"
    r"important (limitations|administration)|lowering blood pressure reduces|"
    r"the effect(iveness)? of .* on)",
    re.I,
)

def parse_indications(raw: str) -> list:
    """Extract canonical disease names from the INDICATION CLAUSE only.

    Scanning the whole section catches diseases mentioned as risk-factors or
    populations; restricting to the clause after the 'indicated for/to' trigger
    (and before 'Limitations of Use') greatly reduces false positives.
    """
    t = clean_text(raw)
    if not t:
        return []

    m = _TRIGGER.search(t)
    clause = t[m.end():] if m else t
    end = _END.search(clause)
    if end:
        clause = clause[:end.start()]
    clause = clause[:400]   # keep the primary indication window

    found = []
    for rx, name in _DISEASE_COMPILED:
        if rx.search(clause) and name not in found:
            found.append(name)
    return found[:6]   # cap at 6 indications per drug

# ── Main loop ────────────────────────────────────────────────────────────────
rows = list(csv.DictReader(open(CLEAN_CSV, encoding="utf-8")))
print(f"Drugs to process: {len(rows)}", flush=True)

detail = []
stopped = False
for i, r in enumerate(rows):
    drug, brand = r["Drug"], r.get("Brand", "")
    try:
        matched, raw = fetch_indication(drug, brand)
    except RuntimeError as e:
        print(f"\n! Stopped early ({e}) after {req_count} requests at drug {i+1}", flush=True)
        stopped = True
        break

    phrases = parse_indications(raw) if raw else []
    detail.append({
        "Drug": drug,
        "Matched_Query": matched,
        "Source": "openFDA label" if raw else "not found",
        "N_Indications": len(phrases),
        "Indications_Parsed": "; ".join(phrases),
        "Label_Indication_Text": clean_text(raw)[:600],
    })

    if (i + 1) % 50 == 0:
        CACHE.write_text(json.dumps(cache))
        hits = sum(1 for d in detail if d["Source"] == "openFDA label")
        print(f"  [{i+1}/{len(rows)}] reqs={req_count} hits={hits}", flush=True)

CACHE.write_text(json.dumps(cache))

# For any rows not processed (stopped early), still emit them from cache/empty
processed = {d["Drug"] for d in detail}
for r in rows:
    if r["Drug"] not in processed:
        key = r["Drug"].lower()
        c = cache.get(key, {})
        raw = c.get("raw", "")
        phrases = parse_indications(raw) if raw else []
        detail.append({
            "Drug": r["Drug"],
            "Matched_Query": c.get("matched", ""),
            "Source": "openFDA label" if raw else "pending",
            "N_Indications": len(phrases),
            "Indications_Parsed": "; ".join(phrases),
            "Label_Indication_Text": clean_text(raw)[:600] if raw else "",
        })

# preserve original order
order = {r["Drug"]: i for i, r in enumerate(rows)}
detail.sort(key=lambda d: order.get(d["Drug"], 9999))

with open(OUT_DETAIL, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["Drug", "Matched_Query", "Source",
                                      "N_Indications", "Indications_Parsed",
                                      "Label_Indication_Text"])
    w.writeheader()
    w.writerows(detail)

n_hits = sum(1 for d in detail if d["Source"] == "openFDA label")
print(f"\nDetail file -> {OUT_DETAIL}")
print(f"  Label indications found: {n_hits}/{len(detail)} "
      f"({100*n_hits/len(detail):.0f}%)")
print(f"  Total openFDA requests used: {req_count}")
if stopped:
    print("  NOTE: stopped at daily budget — re-run tomorrow to finish (cached/resumable)")
