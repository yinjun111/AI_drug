#!/usr/bin/env python3
import csv
import json
import re
import subprocess
import time
from collections import OrderedDict
from pathlib import Path

INPUT_CSV = Path("purplebook_merged_proper_name.csv")
OUTPUT_CSV = Path("purplebook_drug_diseases.csv")
CACHE_FILE = Path("fda_indications_cache.json")

CATEGORY_KEYWORDS = [
    ("oncology", [
        r"cancer", r"carcinoma", r"leukemia", r"lymphoma", r"sarcoma", r"neoplasm", 
        r"malignan", r"melanoma", r"myeloma", r"metastasi", r"blastoma", r"hodgkin", 
        r"non[- ]hodgkin", r"acute lymphoblastic", r"acute myeloid", r"solid tumor",
    ]),
    ("infectious", [
        r"\binfection\b", r"\binfectious\b", r"\bhepatitis\b", r"\bhiv\b", r"\binfluenza\b", r"\bpneumonia\b",
        r"\brespiratory syncytial virus\b", r"\brs?v\b", r"\bcovid\b", r"\bsepsis\b", r"\bbacterial\b",
        r"\bviral\b", r"\bfungal\b", r"\bparasitic\b",
    ]),
    ("autoimmune", [
        r"multiple sclerosis", r"rheumatoid", r"lupus", r"psoriasis", r"scleroderma",
        r"ankylosing spondylitis", r"crohn", r"ulcerative colitis", r"autoimmune",
        r"myasthenia gravis", r"immune thrombocytopenia", r"idiopathic thrombocytopenic purpura",
        r"inflammatory bowel disease", r"uveitis", r"vasculitis", r"hidradenitis suppurativa",
        r"juvenile idiopathic arthritis",
    ]),
    ("neurology", [
        r"alzheimer", r"dementia", r"migraine", r"epilepsy", r"seizure", r"parkinson",
        r"neuropathy", r"stroke", r"spinal muscular atrophy", r"amyotrophic lateral sclerosis",
        r"ataxia", r"headache",
    ]),
    ("cardiovascular", [
        r"heart", r"cardiac", r"myocardial", r"coronary", r"angina", r"hypertension",
        r"blood pressure", r"aortic", r"artery", r"arterial", r"thrombosis", r"thrombo",
        r"heart failure", r"arrhythmia", r"atrial fibrillation", r"ischemic",
    ]),
    ("metabolic", [
        r"diabetes", r"obesity", r"hyperlipid", r"dyslipid", r"metabolic", r"lipid disorder",
        r"cholesterol", r"gout", r"phenylketonuria", r"glycogen storage", r"thyroid",
    ]),
]

SEARCH_NORMALIZATIONS = [
    lambda s: s.strip(),
    lambda s: re.sub(r"\(.*?\)", "", s).strip(),
    lambda s: re.sub(r"[,;].*$", "", s).strip(),
    lambda s: re.sub(r"[^A-Za-z0-9 ]+", " ", s).strip(),
    lambda s: s.replace("-", " ").replace("/", " ").strip(),
]

RESULT_FIELDS = ["Drug Name", "Disease", "Category", "Search Term"]


def load_cache(path):
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {}


def save_cache(path, cache):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(cache, handle, indent=2, ensure_ascii=False)


def run_fda_query(drug_name):
    args = [
        "uvx",
        "--from",
        "tooluniverse",
        "tu",
        "run",
        "FDA_get_indications_by_drug_name",
        json.dumps({"drug_name": drug_name}),
        "--json",
    ]
    proc = subprocess.run(args, capture_output=True, text=True, timeout=45)
    output = proc.stdout.strip()
    if not output:
        return {
            "status": "error",
            "error": {"code": "NO_OUTPUT", "message": proc.stderr.strip()},
            "results": [],
            "meta": {"total": 0, "skip": 0, "limit": 0},
        }
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        data = {
            "status": "error",
            "error": {"code": "JSON_ERROR", "message": output[:1000]},
            "results": [],
            "meta": {"total": 0, "skip": 0, "limit": 0},
        }
    return data


def get_cache_key(name):
    return name.strip().lower()


def query_cached(cache, drug_name):
    key = get_cache_key(drug_name)
    if key in cache:
        return cache[key]
    data = run_fda_query(drug_name)
    cache[key] = {"drug_name": drug_name, "data": data, "queried_name": drug_name}
    save_cache(CACHE_FILE, cache)
    # polite spacing for external service
    time.sleep(0.08)
    return cache[key]


def normalize_search_terms(drug_name):
    seen = set()
    for normalize in SEARCH_NORMALIZATIONS:
        candidate = normalize(drug_name)
        if candidate and candidate not in seen:
            seen.add(candidate)
            yield candidate


def extract_indication_texts(data):
    if not isinstance(data, dict):
        return []
    results = data.get("results") or []
    texts = []
    for record in results:
        fields = record.get("indications_and_usage")
        if fields:
            if isinstance(fields, list):
                texts.extend(fields)
            else:
                texts.append(fields)
    return texts


def clean_text(text):
    text = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
    text = re.sub(r"1 INDICATIONS AND USAGE", "", text, flags=re.I)
    text = text.strip()
    return text


def extract_diseases_from_text(text):
    text = clean_text(text)
    text = text.replace("•", "\n•")
    text = re.sub(r"\(\s*\d+(?:\.\d+)?\s*\)", "", text)
    text = re.sub(
        r"\b(?:Select patients for therapy|Patients should have|Patients should|Treat patients|The recommended dose|Dosage and Administration|Limitations of Use)\b[^\.]*\.",
        "",
        text,
        flags=re.I,
    )

    body = text
    match = re.search(
        r"(?:is indicated for|indicated for|is indicated to|is indicated as|indicated as|indicated in|is indicated in)\s*:\s*(.*)$",
        text,
        flags=re.I | re.DOTALL,
    )
    if match:
        body = match.group(1)

    candidates = re.split(r"\n•|\n-|;|\n|\r|\*", body)
    disease_chunks = set()

    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        candidate = re.sub(r"^•\s*", "", candidate)
        if ":" in candidate:
            candidate = candidate.split(":", 1)[0].strip()
        cleaned = candidate
        cleaned = re.sub(
            r"^\s*(?:is indicated for|indicated for|for the treatment and control of|for the treatment of|for the prophylaxis and treatment of|for the prophylaxis of|for the prevention of|reducing signs and symptoms,?\s*|reducing signs and symptoms of\s*|reducing signs and symptoms, inducing .*? of\s*|reducing signs and symptoms, inducing major clinical response, inhibiting the progression of structural damage, and improving physical function in adult patients with\s*|reducing signs and symptoms, inducing major clinical response, inhibiting the progression of structural damage, and improving physical function in adult patients with\s*|inhibiting the progression of structural damage, and improving physical function in adult patients with\s*|inhibiting the progression of structural damage,?\s*|improving physical function in adult patients with\s*|treatment of\s*|treatment and control of\s*)",
            "",
            cleaned,
            flags=re.I,
        )
        cleaned = re.sub(r"^inhibiting the progression of structural damage(?:,? and improving physical function(?: in adult patients with)?)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"^of\s+", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\bmoderately to severely active\b\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\bmoderately active\b\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\bseverely active\b\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\bactive\b\s*", "", cleaned, flags=re.I)
        if cleaned.lower().startswith("reducing signs") or cleaned.lower().startswith("inducing major clinical response"):
            m = re.search(r"with\s+(.+?)(?:\.|$)", cleaned, flags=re.I)
            if m:
                cleaned = m.group(1).strip()
        cleaned = re.sub(
            r"\b(?:in adult patients|in adults|in pediatric patients|in pediatric patients 2 years of age or older|in pediatric patients 2 years of age|in patients 2 years of age or older|in patients 2 years of age|in patients 12 years of age or older|in patients 6 years of age|in pediatric patients.*|in adults and pediatric patients.*|in patients)\b.*$",
            "",
            cleaned,
            flags=re.I,
        )
        cleaned = re.sub(r"\b(?:who have .*|who previously .*|who are .*|including .*|after .*|following .*|when .*|which .*|that .*?)$", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*\([^\)]*\)", "", cleaned)
        if " with " in cleaned.lower() and not re.search(r"\b(?:arthritis|disease|colitis|psoriasis|uveitis|spondylitis|syndrome|suppurativa|enteritis|panuveitis)\b", cleaned, flags=re.I):
            m2 = re.search(r"with\s+(.+?)(?:\.|$)", cleaned, flags=re.I)
            if m2:
                cleaned = m2.group(1).strip()
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,;:.")
        cleaned = re.sub(r"\.+$", "", cleaned).strip()
        if len(cleaned) < 4:
            continue
        if len(cleaned) > 180:
            cleaned = cleaned[:180].rstrip(" ,;:")
        disease_chunks.add(cleaned)

    normalized = []
    for disease in sorted(disease_chunks, key=lambda x: (len(x), x.lower())):
        disease = re.sub(r"\s+", " ", disease).strip()
        if disease and len(disease) > 3:
            normalized.append(disease)
    return normalized


def categorize_disease(disease_text):
    lower = disease_text.lower()
    for category, patterns in CATEGORY_KEYWORDS:
        for pattern in patterns:
            if re.search(pattern, lower):
                return category
    return "others"


def choose_best_result(results, query_term):
    if not results:
        return None
    # prefer records with either brand_name or generic_name containing the query token or related terms
    query_tokens = {t for t in re.split(r"\W+", query_term.lower()) if t}
    scored = []
    for record in results:
        score = 0
        openfda = record.get("openfda", {}) or {}
        for field in ("brand_name", "generic_name"):
            values = openfda.get(field)
            if not values:
                continue
            for item in values:
                item_text = str(item).lower()
                for token in query_tokens:
                    if token and token in item_text:
                        score += 1
        scored.append((score, record))
    scored.sort(key=lambda x: x[0], reverse=True)
    # return highest score record if positive score, else return first record
    return [record for score, record in scored if score >= 0]


def query_for_drug(cache, drug_name, fallback_names=None):
    if fallback_names is None:
        fallback_names = []
    tried = []
    results = []
    chosen_term = None
    for term in [drug_name] + fallback_names:
        for candidate in normalize_search_terms(term):
            if candidate in tried:
                continue
            tried.append(candidate)
            entry = query_cached(cache, candidate)
            data = entry["data"]
            total = data.get("meta", {}).get("total", 0)
            if total > 0:
                chosen_term = candidate
                results = data.get("results", [])
                if results:
                    return chosen_term, results
    return chosen_term, []


def read_drug_list(path):
    drugs = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = row.get("Proper Name, merged") or row.get("Proper Name") or row.get("proper name")
            if not name:
                continue
            name = name.strip()
            if not name:
                continue
            proprietary = row.get("Proprietary Name", "")
            if proprietary:
                proprietary = proprietary.split("|")[0].strip()
            drugs.append((name, proprietary))
    return drugs


def main():
    print(f"Reading drug list from {INPUT_CSV}")
    drugs = read_drug_list(INPUT_CSV)
    if not drugs:
        raise SystemExit("No drug names found in input CSV.")

    cache = load_cache(CACHE_FILE)
    seen = set()
    rows = []
    for idx, (drug_name, proprietary_name) in enumerate(drugs, start=1):
        if drug_name.lower() in seen:
            continue
        seen.add(drug_name.lower())
        fallback_names = []
        if proprietary_name and proprietary_name.lower() != drug_name.lower():
            fallback_names.append(proprietary_name)
        if "," in drug_name:
            fallback_names.extend([part.strip() for part in drug_name.split(",") if part.strip()])
        if " and " in drug_name:
            fallback_names.extend([part.strip() for part in drug_name.split(" and ") if part.strip()])

        print(f"[{idx}/{len(drugs)}] Querying '{drug_name}'")
        chosen_query, results = query_for_drug(cache, drug_name, fallback_names=fallback_names)
        if not results:
            print(f"  No FDA indication records found for '{drug_name}'")
            rows.append({"Drug Name": drug_name, "Disease": "", "Category": "others", "Search Term": chosen_query or ""})
            continue

        merged_text = []
        for record in results:
            merged_text.extend(extract_indication_texts(record))
        diseases = []
        for text in merged_text:
            diseases.extend(extract_diseases_from_text(text))

        unique_diseases = OrderedDict()
        for disease in diseases:
            category = categorize_disease(disease)
            unique_diseases[disease] = category

        if not unique_diseases:
            # fallback to a generic row if the label returned results but no disease phrase could be parsed
            print(f"  Found indications text for '{drug_name}' but could not parse specific diseases.")
            rows.append({"Drug Name": drug_name, "Disease": "", "Category": "others", "Search Term": chosen_query or ""})
            continue

        for disease, category in unique_diseases.items():
            rows.append({"Drug Name": drug_name, "Disease": disease, "Category": category, "Search Term": chosen_query or ""})

    print(f"Writing {len(rows)} rows to {OUTPUT_CSV}")
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print("Done.")


if __name__ == "__main__":
    main()
