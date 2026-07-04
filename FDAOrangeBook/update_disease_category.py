"""
Re-map orangebook_chronic_indications_clean.csv 'Category' column to the
Purple Book granular 'Area – Subarea' scheme (adopt-fully).

Top-level area comes from the existing (correct) OB coarse category; the
sub-area is picked by scanning the drug's Disease / Indication text.
Reuses PB's exact category names where they apply
(e.g. 'Autoimmune – Rheumatology', 'Endocrinology – Diabetes',
'Bone / Metabolic', 'Cardiovascular / Pulmonary', 'Ophthalmology', 'Nephrology').
"""

import csv, re, shutil

CLEAN = "orangebook_chronic_indications_clean.csv"

def has(t, *pats):
    return any(re.search(p, t, re.I) for p in pats)

# Drug-class name overrides — used where the label lists a condition as a
# risk-factor/population rather than the treated disease (e.g. statins mention
# "type 2 diabetes" as a CHD risk factor). Keyed on ingredient name substrings.
NAME_OVERRIDES = [
    (r"statin\b|ezetimibe|fenofibr|gemfibrozil|\bfibrate|bempedoic|icosapent|"
     r"omega-3|\bniacin|colesevelam|cholestyramine|colestipol|lomitapide|"
     r"evolocumab|alirocumab|inclisiran", "Endocrinology – Lipid"),
]

def granular_category(coarse: str, indication: str, drug: str = "") -> str:
    t = indication or ""
    dn = (drug or "").lower()

    # Name-based class overrides first
    for pat, cat in NAME_OVERRIDES:
        if re.search(pat, dn):
            return cat

    if coarse == "Cardiovascular":
        if has(t, r"pulmonary arterial hypertension|\bpah\b"):    return "Cardiovascular / Pulmonary"
        if has(t, r"heart failure"):                             return "Cardiovascular – Heart Failure"
        if has(t, r"atrial fibrillation|arrhythmia|tachycardia|fibrillation"): return "Cardiovascular – Arrhythmia"
        if has(t, r"\bdvt\b|venous throm|pulmonary embol|thromboemb|stroke"):  return "Cardiovascular – Thrombosis"
        if has(t, r"angina|myocardial infarction|coronary|ischemi"): return "Cardiovascular – Ischemic"
        if has(t, r"hypertension|blood pressure"):              return "Cardiovascular – Hypertension"
        return "Cardiovascular – Other"

    if coarse == "Metabolic":
        if has(t, r"diabet"):                                   return "Endocrinology – Diabetes"
        if has(t, r"cholesterol|lipid|triglyceride|dyslipid"):  return "Endocrinology – Lipid"
        if has(t, r"thyroid"):                                  return "Endocrinology – Thyroid"
        if has(t, r"osteoporosis|\bbone\b|paget"):              return "Bone / Metabolic"
        if has(t, r"\bgout\b|uric"):                            return "Metabolic – Gout"
        if has(t, r"hyperkalemia|hyperphosphat|electrolyte"):   return "Metabolic – Electrolyte"
        if has(t, r"growth hormone|acromegaly|short stature"):  return "Endocrinology – Growth"
        if has(t, r"cushing"):                                  return "Endocrinology – Metabolic"
        if has(t, r"hypogonad|testosterone|contracep|menopaus|estrogen|endometrios|reproductive|hormone (replacement|therapy)"): return "Endocrinology – Reproductive"
        if has(t, r"benign prostatic|\bbph\b|prostatic hyperplasia"): return "Urology – Prostate"
        if has(t, r"anemia"):                                   return "Hematology – Anemia"
        return "Endocrinology – Metabolic"

    if coarse == "Psychiatric":
        if has(t, r"schizophren|psychotic"):                    return "Psychiatry – Psychotic"
        if has(t, r"bipolar|depress|major depressive|\bmdd\b|mood"): return "Psychiatry – Mood"
        if has(t, r"anxiety|obsessive|\bocd\b|panic|\bptsd\b|traumatic"): return "Psychiatry – Anxiety"
        if has(t, r"\badhd\b|attention deficit|narcolep|wakefulness|sleepiness"): return "Psychiatry – ADHD / Wakefulness"
        if has(t, r"insomnia|\bsleep\b"):                       return "Psychiatry – Sleep"
        if has(t, r"opioid|alcohol|smoking|nicotine|substance|addiction|dependence"): return "Psychiatry – Substance Use"
        return "Psychiatry – Other"

    if coarse == "Neurology":
        if has(t, r"multiple sclerosis|demyelin"):              return "Neurology – Demyelinating"
        if has(t, r"parkinson|huntington|tardive|restless legs|dystonia|movement"): return "Neurology – Movement Disorder"
        if has(t, r"alzheimer|dementia|neurodegener"):          return "Neurology – Neurodegeneration"
        if has(t, r"myasthenia|amyotrophic|\bals\b|spasticity|neuromuscular"): return "Neurology – Neuromuscular"
        if has(t, r"migraine|headache|neuropathic pain|fibromyalgia"): return "Neurology – Pain / Headache"
        if has(t, r"epilepsy|seizure|convuls"):                 return "Neurology – Epilepsy"
        if has(t, r"overactive bladder|urinary (incontinence|urgency|frequency)"): return "Urology – Bladder"
        return "Neurology – Other"

    if coarse == "Oncology":
        if has(t, r"leukemia|lymphoma|myeloma|myelodysplastic|myelofibrosis|hematolog"): return "Oncology – Hematologic"
        return "Oncology – Solid Tumor"

    if coarse == "Infectious":
        if has(t, r"\bhiv\b|immunodeficiency virus"):           return "Infectious – HIV"
        if has(t, r"hepatitis"):                                return "Infectious – Hepatitis"
        return "Infectious – Other"

    if coarse == "Respiratory":
        if has(t, r"asthma|\bcopd\b|obstructive pulmonary|bronchospasm|emphysema"): return "Respiratory – Obstructive"
        if has(t, r"rhinitis|allerg|nasal"):                    return "Respiratory – Allergy"
        if has(t, r"cystic fibrosis|pulmonary fibrosis|fibrosis"): return "Respiratory – Fibrosis"
        return "Respiratory – Other"

    if coarse == "GI":
        if has(t, r"crohn|ulcerative colitis|inflammatory bowel"): return "Autoimmune – Gastroenterology"
        if has(t, r"gerd|reflux|peptic ulcer|acid|esophagitis"): return "Gastroenterology – Acid-Related"
        if has(t, r"irritable bowel|\bibs\b|constipation|motility|nausea|vomiting"): return "Gastroenterology – Motility"
        if has(t, r"biliary|cholangitis|hepatic|liver"):        return "Gastroenterology – Hepatic"
        if has(t, r"pancrea|short bowel"):                      return "Gastroenterology – Pancreatic"
        return "Gastroenterology – Other"

    if coarse == "Autoimmune":
        if has(t, r"rheumatoid|psoriatic arthritis|spondylitis|\bsle\b|lupus|arthritis"): return "Autoimmune – Rheumatology"
        if has(t, r"psoriasis|atopic dermatitis|eczema"):       return "Autoimmune – Dermatology"
        if has(t, r"crohn|colitis|bowel"):                      return "Autoimmune – Gastroenterology"
        return "Autoimmune – Rheumatology"

    if coarse == "Pain":
        if has(t, r"osteoarthritis"):                           return "Pain – Osteoarthritis"
        return "Pain – Chronic"

    if coarse == "Dermatology":
        if has(t, r"psoriasis|atopic dermatitis|eczema"):       return "Autoimmune – Dermatology"
        return "Dermatology – General"

    if coarse == "Ophthalmology":
        return "Ophthalmology"

    return "Other"


# ── Apply ─────────────────────────────────────────────────────────────────────
shutil.copy(CLEAN, CLEAN + ".catbak")
rows = list(csv.DictReader(open(CLEAN, encoding="utf-8")))
fields = list(rows[0].keys())

from collections import Counter
before = Counter(r["Category"] for r in rows)
for r in rows:
    r["Category"] = granular_category(r["Category"], r["Disease / Indication"], r["Drug"])
after = Counter(r["Category"] for r in rows)

with open(CLEAN, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

print(f"Backup: {CLEAN}.catbak")
print(f"\nGranular categories ({len(after)}):")
for c, n in sorted(after.items(), key=lambda x: -x[1]):
    print(f"  {n:>4}  {c}")
print(f"\nUpdated -> {CLEAN}")
