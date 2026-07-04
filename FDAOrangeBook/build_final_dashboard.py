"""
Builds:
  1. orangebook_chronic_indications.csv  — Purple-Book-style table with:
       Drug | Brand | Disease/Indication | Category | Target | Revenue($B) | Dose | Frequency | Duration
  2. orangebook_chronic_dashboard.html  — updated full dashboard
"""

import csv, re
from collections import defaultdict
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

SEP = " | "

# ── 1. Load all source tables ─────────────────────────────────────────────────
print("Loading data …")

chronic = {}          # ingredient → row
with open("orangebook_chronic_drugs.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        chronic[r["Ingredient"]] = r

targets = {}          # ingredient → row
with open("orangebook_drug_targets.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        targets[r["Ingredient"]] = r

revenue = {}          # ingredient → row
with open("orangebook_drug_revenue.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        revenue[r["Ingredient"]] = r

patents = {}          # ingredient → row
with open("orangebook_with_patents.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        patents[r["Ingredient"]] = r

print(f"  Chronic drugs: {len(chronic)}, targets: {len(targets)}, revenue: {len(revenue)}")

# ── 2. Extract dose + frequency from products.txt (RLD rows only) ─────────────
print("Extracting RLD dose/route data …")

FREQ_RULES = [
    (r"extended release|ER\b|XR\b|XL\b|once.?a.?day",  "Once daily"),
    (r"SYSTEM;TRANSDERMAL",                              "Once weekly"),
    (r"FILM, EXTENDED RELEASE",                          "Once daily"),
    (r"SUSPENSION, EXTENDED RELEASE;SUBCUTANEOUS",       "Monthly"),
    (r"SOLUTION;SUBCUTANEOUS",                           "Weekly or monthly"),
    (r"INJECTABLE;SUBCUTANEOUS",                         "Weekly or monthly"),
    (r"AEROSOL, METERED;INHALATION",                     "Twice daily"),
    (r"SPRAY, METERED;INHALATION",                       "Twice daily"),
    (r"POWDER;INHALATION",                               "Once or twice daily"),
    (r"CAPSULE;INHALATION",                              "Twice daily"),
    (r"SOLUTION/DROPS;OPHTHALMIC|SUSPENSION;OPHTHALMIC", "Once daily"),
    (r"GEL;TRANSDERMAL|SOLUTION;TRANSDERMAL",            "Once daily"),
    (r"OINTMENT|CREAM|GEL;TOPICAL|LOTION;TOPICAL",       "Once or twice daily"),
    (r"TABLET;ORAL|CAPSULE;ORAL",                        "Once or twice daily"),
    (r"TABLET, DELAYED RELEASE",                         "Once daily"),
    (r"TABLET, ORALLY DISINTEGRATING",                   "Once daily"),
    (r"TABLET, CHEWABLE;ORAL",                           "Once or twice daily"),
    (r"CAPSULE, DELAYED REL",                            "Once daily"),
    (r"SOLUTION;ORAL|SYRUP;ORAL|SUSPENSION;ORAL",        "Once or twice daily"),
    (r"INJECTABLE;INTRAMUSCULAR",                        "Monthly or quarterly"),
    (r"INJECTABLE;INTRAVENOUS",                          "As directed"),
    (r"SUPPOSITORY",                                     "Once or twice daily"),
    (r"FILM;SUBLINGUAL|FILM;BUCCAL|TABLET;SUBLINGUAL",   "As needed"),
    (r"SPRAY, METERED;NASAL",                            "Once daily"),
    (r"AEROSOL, FOAM;NASAL",                             "Once daily"),
]

def infer_frequency(df_route: str) -> str:
    for pattern, freq in FREQ_RULES:
        if re.search(pattern, df_route, re.IGNORECASE):
            return freq
    return "As directed"

def clean_strength(s: str) -> str:
    """Return a tidy dose string from the Strength field."""
    s = s.strip()
    # Remove footnotes like **Federal Register...**
    s = re.sub(r'\*\*.*?\*\*', '', s).strip()
    # For combo products (semicolon-separated strengths), shorten
    parts = [p.strip() for p in s.split(";")]
    if len(parts) > 2:
        parts = parts[:2]
        s = "; ".join(parts) + " …"
    else:
        s = "; ".join(parts)
    # Clean up verbose EQ expressions
    s = re.sub(r'EQ\s+', '', s, flags=re.IGNORECASE)
    # Capitalise units
    s = re.sub(r'\bMG\b', 'mg', s)
    s = re.sub(r'\bMCG\b|\bUG\b', 'mcg', s, flags=re.IGNORECASE)
    s = re.sub(r'\bML\b', 'mL', s)
    s = re.sub(r'\bINH\b', '/inh', s)
    return s[:60]

ing_dose: dict[str, str]  = {}
ing_freq: dict[str, str]  = {}
ing_route: dict[str, str] = {}

with open("data/EOBZIP_2026_05/products.txt", encoding="utf-8", errors="replace") as f:
    for row in csv.DictReader(f, delimiter="~"):
        if row.get("Type","") == "DISCN":
            continue
        ing = row["Ingredient"].strip()
        if ing not in chronic:
            continue
        rld = row.get("RLD","").strip().upper()
        strength  = row.get("Strength","").strip()
        df_route  = row.get("DF;Route","").strip()

        # Prefer RLD rows; fall back to any active row
        if rld == "YES" or ing not in ing_dose:
            dose_str = clean_strength(strength)
            if dose_str:
                ing_dose[ing]  = dose_str
                ing_freq[ing]  = infer_frequency(df_route)
                ing_route[ing] = df_route

print(f"  Dose data for {len(ing_dose)} ingredients")

# ── 3. Disease/Indication generation ─────────────────────────────────────────
# Map MoA text → clinical indication
MOA_INDICATION = [
    # Cardiovascular
    ("angiotensin.converting enzyme inhibitor|ACE inhibitor",    "Hypertension; Heart failure; CKD"),
    ("angiotensin.*receptor.*blocker|ARB",                        "Hypertension; Heart failure; Diabetic nephropathy"),
    ("beta.adrenergic receptor.*antagonist|beta.blocker",         "Hypertension; Heart failure; Angina"),
    ("calcium channel.*blocker|dihydropyridine",                  "Hypertension; Angina"),
    ("HMG.CoA reductase inhibitor|statin",                        "Dyslipidemia; CV risk reduction"),
    ("coagulation factor X inhibitor|factor Xa",                  "Atrial fibrillation; DVT/PE prevention"),
    ("thrombin inhibitor",                                         "Atrial fibrillation; DVT/PE prevention"),
    ("antiplatelet|platelet aggregation",                         "Cardiovascular disease prevention"),
    ("aldosterone.*antagonist|mineralocorticoid.*antagonist",     "Heart failure; Hypertension; Hyperaldosteronism"),
    ("loop diuretic|sodium-potassium-chloride",                   "Edema; Heart failure; Hypertension"),
    ("thiazide diuretic",                                         "Hypertension; Edema"),
    ("nitric oxide.*donor|phosphodiesterase.*inhibitor.*pulmon",  "Pulmonary arterial hypertension"),
    ("endothelin receptor antagonist",                            "Pulmonary arterial hypertension"),
    ("prostacyclin.*agonist|prostaglandin",                       "Pulmonary arterial hypertension"),
    ("antiarrhythm|sodium channel.*blocker.*cardiac",             "Cardiac arrhythmia"),
    ("digoxin|cardiac glycoside",                                 "Heart failure; Atrial fibrillation"),
    ("PCSK9 inhibitor|proprotein convertase",                     "Hypercholesterolemia; CV risk reduction"),

    # Metabolic – diabetes
    ("GLP.1 receptor agonist|glucagon.like peptide.1",            "Type 2 diabetes; Obesity; CV risk reduction"),
    ("GIP.*receptor.*agonist|dual.*GIP.*GLP",                     "Type 2 diabetes; Obesity; OSA"),
    ("DPP.4 inhibitor|dipeptidyl peptidase",                      "Type 2 diabetes"),
    ("SGLT.2 inhibitor|sodium.glucose cotransporter 2",           "Type 2 diabetes; Heart failure; CKD"),
    ("biguanide|AMPK.*activator|metformin",                       "Type 2 diabetes"),
    ("sulfonylurea|ATP.sensitive potassium channel",              "Type 2 diabetes"),
    ("thiazolidinedione|PPAR.*gamma agonist",                     "Type 2 diabetes; Insulin resistance"),
    ("meglitinide|short.acting insulin secretagogue",             "Type 2 diabetes"),
    ("alpha.glucosidase inhibitor",                               "Type 2 diabetes"),
    ("insulin receptor agonist|insulin",                          "Diabetes (Type 1 & 2)"),

    # Metabolic – other
    ("bisphosphonate|bone resorption inhibitor|osteoclast",       "Osteoporosis; Paget's disease"),
    ("parathyroid hormone|PTH receptor",                          "Osteoporosis"),
    ("thyroid hormone|levothyroxine",                             "Hypothyroidism"),
    ("anti.thyroid|thioamide|thyroid peroxidase",                 "Hyperthyroidism"),
    ("lipase inhibitor|orlistat",                                 "Obesity"),
    ("fibrate|PPAR.alpha",                                        "Hypertriglyceridemia; Mixed dyslipidemia"),
    ("cholesterol absorption inhibitor|ezetimibe",                "Hypercholesterolemia"),
    ("bile acid sequestrant|cholestyramine|colesevelam",          "Hypercholesterolemia; Bile acid diarrhea"),
    ("xanthine oxidase inhibitor|allopurinol|febuxostat",         "Gout; Hyperuricemia"),
    ("uricosuric|probenecid",                                     "Gout; Hyperuricemia"),
    ("gout|colchicine",                                           "Gout; Familial Mediterranean fever"),
    ("urea cycle|ammonia|ornithine",                              "Urea cycle disorders"),
    ("iron chelat|deferoxamine|deferasirox",                      "Iron overload"),

    # Psychiatric
    ("serotonin reuptake inhibitor|SSRI|SNRI",                   "Depression; Anxiety disorders; OCD"),
    ("norepinephrine reuptake inhibitor",                         "Depression; ADHD; Neuropathic pain"),
    ("dopamine.*reuptake inhibitor|bupropion",                    "Depression; Smoking cessation"),
    ("dopamine.*norepinephrine.*reuptake|atomoxetine",            "ADHD"),
    ("dopamine transporter inhibitor|methylphenidate|amphetamine","ADHD; Narcolepsy"),
    ("monoamine oxidase inhibitor|MAOI",                         "Depression; Parkinson's disease"),
    ("tricyclic antidepressant|TCA",                              "Depression; Neuropathic pain; Chronic pain"),
    ("serotonin.*partial agonist|buspirone",                      "Generalized anxiety disorder"),
    ("D2.*antagonist|dopamine receptor antagonist",               "Schizophrenia; Bipolar disorder; Nausea"),
    ("serotonin.dopamine.*antagonist|atypical antipsychotic",     "Schizophrenia; Bipolar disorder; MDD"),
    ("lithium",                                                   "Bipolar disorder"),
    ("GABA.*receptor.*modulator|benzodiazepine",                  "Anxiety; Insomnia; Epilepsy"),
    ("melatonin.*agonist|orexin.*antagonist",                     "Insomnia"),
    ("opioid receptor.*partial|buprenorphine",                    "Opioid use disorder; Chronic pain"),
    ("opioid receptor.*antagonist|naltrexone|naloxone",           "Opioid use disorder; Alcohol use disorder"),
    ("cannabinoid.*receptor|cannabidiol",                         "Epilepsy; Anxiety"),
    ("sodium channel.*blocker.*CNS|antiepileptic|anticonvulsant", "Epilepsy; Neuropathic pain"),
    ("vesicular monoamine transporter.*inhibitor|VMAT2",          "Tardive dyskinesia; Huntington's disease"),

    # Neurology
    ("acetylcholinesterase inhibitor|cholinesterase inhibitor",   "Alzheimer's disease; Myasthenia gravis"),
    ("NMDA receptor.*antagonist|memantine",                       "Alzheimer's disease"),
    ("dopamine precursor|levodopa|carbidopa",                     "Parkinson's disease"),
    ("dopamine agonist",                                          "Parkinson's disease; Restless legs syndrome"),
    ("MAO.B inhibitor",                                           "Parkinson's disease"),
    ("COMT inhibitor",                                            "Parkinson's disease (adjunct)"),
    ("beta.interferon|glatiramer|sphingosine",                    "Multiple sclerosis"),
    ("S1P receptor modulator|sphingosine.*phosphate",             "Multiple sclerosis"),
    ("natalizumab|integrin.*antagonist.*neurology",               "Multiple sclerosis"),
    ("BTK.*inhibitor.*neurology",                                 "Multiple sclerosis"),
    ("CGRP.*antagonist|calcitonin.*gene.*related.*peptide",       "Migraine prevention"),
    ("5-HT.*agonist|triptan|serotonin.*receptor.*agonist",        "Migraine (acute)"),
    ("baclofen|GABA.*agonist.*spinal",                            "Spasticity; Trigeminal neuralgia"),
    ("anticholinergic.*urinary|muscarinic.*antagonist.*bladder",  "Overactive bladder; Urinary incontinence"),
    ("beta.3.*adrenergic|mirabegron",                             "Overactive bladder"),

    # Respiratory
    ("beta.2.*adrenergic.*agonist|bronchodilator.*LABA",          "Asthma; COPD"),
    ("muscarinic.*antagonist.*respiratory|anticholinergic.*COPD", "COPD; Asthma"),
    ("corticosteroid.*inhaled|ICS",                               "Asthma; COPD; Allergic rhinitis"),
    ("leukotriene receptor antagonist|montelukast",               "Asthma; Allergic rhinitis"),
    ("phosphodiesterase.4 inhibitor.*lung|roflumilast",           "COPD"),
    ("mast cell.*stabilizer|cromolyn",                            "Asthma; Allergic rhinitis"),
    ("antihistamine.*H1|histamine H1 receptor",                   "Allergic rhinitis; Urticaria"),

    # GI
    ("proton pump inhibitor|PPI",                                 "GERD; Peptic ulcer disease; H. pylori"),
    ("H2 receptor antagonist|H2 blocker",                         "GERD; Peptic ulcer disease"),
    ("aminosalicylate|5-ASA|mesalamine",                          "Inflammatory bowel disease (UC/CD)"),
    ("PDE4 inhibitor.*GI|apremilast",                             "Psoriatic arthritis; Psoriasis"),
    ("somatostatin.*analog|octreotide",                           "Acromegaly; GI neuroendocrine tumours"),
    ("glucagon-like peptide 2|GLP-2|teduglutide",                 "Short bowel syndrome"),
    ("guanylate cyclase.*agonist|linaclotide|plecanatide",        "IBS-C; Chronic idiopathic constipation"),
    ("ursodiol|bile acid",                                        "Primary biliary cholangitis; Gallstones"),
    ("5-HT4 receptor agonist|prucalopride",                       "Chronic idiopathic constipation"),

    # Autoimmune / Transplant
    ("calcineurin inhibitor|tacrolimus|cyclosporine",             "Transplant rejection prevention; Autoimmune"),
    ("mTOR inhibitor|sirolimus|everolimus",                       "Transplant rejection; Oncology"),
    ("purine synthesis inhibitor|mycophenolate|azathioprine",     "Transplant rejection; Autoimmune"),
    ("dihydrofolate reductase inhibitor|methotrexate",            "RA; Psoriasis; Cancer"),
    ("JAK inhibitor|Janus kinase",                                "RA; Psoriatic arthritis; UC; Atopic dermatitis"),
    ("hydroxychloroquine|antimalarial.*autoimmune",               "SLE; RA; Malaria prevention"),
    ("CTLA-4.*agonist|abatacept",                                 "Rheumatoid arthritis"),
    ("leflunomide|DHODH inhibitor",                               "Rheumatoid arthritis; Psoriatic arthritis"),
    ("phosphodiesterase 4 inhibitor|apremilast",                  "Psoriasis; Psoriatic arthritis"),

    # Infectious
    ("HIV.*protease inhibitor|antiretroviral.*protease",          "HIV infection (chronic suppression)"),
    ("integrase strand transfer inhibitor|INSTI",                 "HIV infection (chronic suppression)"),
    ("nucleoside.*reverse transcriptase|NRTI|nucleotide.*RT",     "HIV infection; Hepatitis B"),
    ("non.nucleoside.*reverse transcriptase|NNRTI",               "HIV infection (chronic suppression)"),
    ("entry inhibitor.*HIV|fusion inhibitor",                     "HIV infection (chronic suppression)"),
    ("capsid inhibitor|lenacapavir",                              "HIV infection (long-acting)"),
    ("HBV polymerase inhibitor|hepatitis B",                      "Chronic hepatitis B"),
    ("NS5B.*inhibitor|HCV.*polymerase|sofosbuvir",                "Chronic hepatitis C"),
    ("NS5A.*inhibitor|HCV.*NS5A",                                 "Chronic hepatitis C"),
    ("NS3/4A.*protease.*HCV|hepatitis C.*protease",               "Chronic hepatitis C"),
    ("isoniazid|rifampin|tuberculosis",                           "Tuberculosis prophylaxis/treatment"),

    # Oncology
    ("EGFR.*inhibitor|epidermal growth factor receptor",          "Non-small cell lung cancer (EGFR+)"),
    ("ALK.*inhibitor|anaplastic lymphoma kinase",                 "Non-small cell lung cancer (ALK+)"),
    ("BCR.ABL.*inhibitor|chronic myeloid",                        "Chronic myeloid leukaemia (CML)"),
    ("CDK 4.*6.*inhibitor|cyclin.dependent kinase 4",             "Breast cancer (HR+/HER2-)"),
    ("PARP.*inhibitor|poly.*ADP.ribose polymerase",               "Ovarian / Breast / Prostate cancer"),
    ("BRAF.*inhibitor",                                           "Melanoma (BRAF V600+); Thyroid cancer"),
    ("MEK.*inhibitor",                                            "Melanoma; NSCLC (BRAF/MEK+)"),
    ("BTK.*inhibitor|Bruton.*tyrosine kinase",                    "B-cell malignancies (CLL/MCL)"),
    ("aromatase inhibitor|anastrozole|letrozole|exemestane",      "Breast cancer (HR+, post-menopausal)"),
    ("androgen receptor.*antagonist|enzalutamide|apalutamide",    "Prostate cancer (mCRPC)"),
    ("androgen synthesis inhibitor|abiraterone",                  "Prostate cancer (mCRPC)"),
    ("GnRH.*agonist|LHRH.*agonist.*oncol|leuprolide",            "Prostate / Breast cancer; Endometriosis"),
    ("tamoxifen|SERM.*oncol",                                     "Breast cancer (ER+); Osteoporosis"),
    ("proteasome inhibitor",                                      "Multiple myeloma"),
    ("HDAC inhibitor|histone deacetylase",                        "Haematological malignancies"),
    ("BCL-2 inhibitor|venetoclax",                                "CLL; AML"),
    ("hypomethylating agent|azacitidine|decitabine",              "MDS; AML"),
    ("hydroxyurea|sickle cell",                                   "Sickle cell disease; Chronic myeloid leukaemia"),
    ("thalidomide|immunomodulatory.*agent.*IMiD",                 "Multiple myeloma; Lenalidomide: MDS"),
    ("mTOR inhibitor.*oncol|everolimus.*cancer",                  "Renal cell carcinoma; Breast cancer; Neuroendocrine tumours"),
    ("multi.kinase.*inhibitor|tyrosine kinase inhibitor",         "Solid tumours (various)"),
    ("antiestrogen|fulvestrant",                                  "Breast cancer (ER+, metastatic)"),
    ("temozolomide|alkylating.*CNS",                              "Glioblastoma; Brain tumours"),
    ("capecitabine|fluoropyrimidine",                             "Colorectal / Breast cancer"),

    # Dermatology
    ("retinoid|retinoic acid receptor",                           "Acne; Psoriasis; Photoageing"),
    ("calcineurin inhibitor.*topical|tacrolimus.*topical",        "Atopic dermatitis"),
    ("calcipotriene|vitamin D.*analogue.*topical",                "Psoriasis"),
    ("PDE4 inhibitor.*dermat|crisaborole",                        "Atopic dermatitis"),
    ("corticosteroid.*topical|glucocorticoid.*topical",           "Psoriasis; Eczema; Dermatitis"),

    # Ophthalmology
    ("prostaglandin.*analogue.*ophthalm|latanoprost|bimatoprost", "Glaucoma; Ocular hypertension"),
    ("carbonic anhydrase inhibitor.*ophthalm|dorzolamide",        "Glaucoma"),
    ("beta.adrenergic.*antagonist.*ophthalm|timolol.*ophthalm",  "Glaucoma"),
    ("alpha.2.*adrenergic.*agonist.*ophthalm|brimonidine",        "Glaucoma"),
    ("rho kinase inhibitor.*ophthalm|netarsudil",                 "Glaucoma"),

    # Pain
    ("opioid.*agonist|mu.*opioid|full.*opioid",                   "Chronic pain; Cancer pain"),
    ("NSAID|non.steroidal anti.inflammatory",                     "Pain; Inflammation; Arthritis"),
    ("COX.2 inhibitor|celecoxib",                                 "Arthritis; Pain; Inflammation"),
    ("gabapentinoid|calcium channel alpha.2.delta|pregabalin",   "Neuropathic pain; Fibromyalgia; Epilepsy"),
    ("serotonin.norepinephrine.*reuptake.*pain|duloxetine.*pain", "Neuropathic pain; Fibromyalgia; Depression"),
]

def get_indication(moa: str, disease_cat: str, ingredient: str) -> str:
    moa_lower = (moa or "").lower()
    ing_lower  = ingredient.lower()

    for pattern, indication in MOA_INDICATION:
        if re.search(pattern, moa_lower, re.IGNORECASE) or re.search(pattern, ing_lower, re.IGNORECASE):
            return indication

    # Fallback by category
    cat_defaults = {
        "Cardiovascular":    "Cardiovascular disease",
        "Metabolic":         "Metabolic disorder",
        "Psychiatric":       "Psychiatric disorder",
        "Neurology":         "Neurological disorder",
        "Respiratory":       "Respiratory disease",
        "GI":                "GI disorder",
        "Autoimmune":        "Autoimmune disease",
        "Infectious":        "Infectious disease",
        "Oncology":          "Cancer",
        "Dermatology":       "Skin disorder",
        "Ophthalmology":     "Ophthalmic disorder",
        "Pain":              "Chronic pain",
    }
    return cat_defaults.get(disease_cat, "Chronic condition")

# ── 4. Build the Purple-Book-style table ──────────────────────────────────────
print("Building chronic indications table …")

def title_case_ing(s: str) -> str:
    """Proper-case an INN ingredient name."""
    # Keep all-caps abbreviations, lowercase everything else
    return " ".join(w.capitalize() if w.upper() == w and len(w) > 2 else w.lower() for w in s.split())

def first_brand(trade_names: str) -> str:
    """Return first non-generic trade name from pipe-separated list."""
    brands = [t.strip() for t in (trade_names or "").split(SEP) if t.strip()]
    # Prefer brand names (not same as ingredient)
    proper_brands = [b for b in brands if "/" not in b and "+" not in b and len(b) < 30]
    return proper_brands[0] if proper_brands else (brands[0] if brands else "")

IND_ROWS = []
for ing, row in sorted(chronic.items(), key=lambda x: x[0].lower()):
    tgt  = targets.get(ing, {})
    rev  = revenue.get(ing, {})

    moa        = tgt.get("Mechanism_of_Action", "")
    gene       = tgt.get("Gene_Symbol(s)", "")
    gene_short = " | ".join(g.split(",")[0].strip() for g in gene.split(" | ") if g)[:60]
    brand      = first_brand(row.get("Trade_Name(s)", ""))
    disease_cat = row.get("Disease_Category", "")
    duration    = row.get("Duration_Class", "")
    indication  = get_indication(moa, disease_cat, ing)

    # Revenue: Medicaid in $B
    med_raw = rev.get("Medicaid_Total_Reimbursed_2023_USD_M", "")
    rev_b   = f"{float(med_raw)/1000:.2f}" if med_raw else ""

    dose = ing_dose.get(ing, "")
    freq = ing_freq.get(ing, "")
    route_abbr = ing_route.get(ing, "")
    # Append route shorthand to dose
    if dose:
        r_short = ""
        if "SUBCUTANEOUS" in route_abbr:   r_short = "SC"
        elif "INTRAVENOUS" in route_abbr:  r_short = "IV"
        elif "INHALATION"  in route_abbr:  r_short = "inh"
        elif "TOPICAL"     in route_abbr:  r_short = "topical"
        elif "OPHTHALMIC"  in route_abbr:  r_short = "ophthalmic"
        elif "TRANSDERMAL" in route_abbr:  r_short = "transdermal"
        elif "NASAL"       in route_abbr:  r_short = "nasal"
        elif "ORAL"        in route_abbr:  r_short = "oral"
        if r_short:
            dose = f"{dose} {r_short}"

    duration_label = {
        "CHRONIC":   "Indefinite (lifelong maintenance)",
        "LONG-TERM": "Long-term (until progression / disease control)",
    }.get(duration, duration)

    IND_ROWS.append({
        "Drug":                    title_case_ing(ing),
        "Brand":                   brand,
        "Disease / Indication":    indication,
        "Category":                disease_cat,
        "Target":                  gene_short or moa[:50] if moa else "",
        "Revenue ($B)":            rev_b,
        "Dose":                    dose,
        "Frequency":               freq,
        "Duration":                duration_label,
        "_ing":                    ing,     # for internal use
        "_rev_val":                float(med_raw) if med_raw else 0.0,
    })

IND_COLS = ["Drug","Brand","Disease / Indication","Category","Target",
            "Revenue ($B)","Dose","Frequency","Duration"]

with open("orangebook_chronic_indications.csv", "w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=IND_COLS + ["_ing","_rev_val"], extrasaction="ignore")
    writer.writeheader()
    writer.writerows(IND_ROWS)

# Also write clean version without internal cols
with open("orangebook_chronic_indications_clean.csv", "w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=IND_COLS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(IND_ROWS)

print(f"  {len(IND_ROWS)} rows in indications table")

# ── 5. Load full classified dataset for dashboard ─────────────────────────────
all_df  = pd.read_csv("orangebook_with_patents.csv")
chr_df  = pd.read_csv("orangebook_chronic_drugs.csv")
ind_df  = pd.DataFrame(IND_ROWS)
rev_df  = pd.read_csv("orangebook_drug_revenue.csv")

# Merge revenue into chr_df
chr_df = chr_df.merge(
    rev_df[["Ingredient","Medicaid_Total_Reimbursed_2023_USD_M","NADAC_Avg_Per_Unit_2024_USD"]],
    on="Ingredient", how="left"
)
chr_df["Medicaid_M"] = pd.to_numeric(chr_df["Medicaid_Total_Reimbursed_2023_USD_M"], errors="coerce").fillna(0)

# Merge gene targets into chr_df
tgt_df = pd.read_csv("orangebook_drug_targets.csv")[["Ingredient","Gene_Symbol(s)","Mechanism_of_Action"]]
chr_df = chr_df.merge(tgt_df, on="Ingredient", how="left")

# ── Colour palettes ───────────────────────────────────────────────────────────
DUR_COLORS = {
    "CHRONIC":   "#2563EB", "LONG-TERM": "#7C3AED",
    "PERIODIC":  "#0891B2", "SHORT":     "#D97706", "OTHER": "#6B7280",
}
CAT_COLORS = {
    "Cardiovascular":"#DC2626","Metabolic":"#059669","Psychiatric":"#7C3AED",
    "Neurology":"#9333EA","Oncology":"#F97316","Infectious":"#0891B2",
    "Respiratory":"#0EA5E9","GI":"#84CC16","Autoimmune":"#2563EB",
    "Pain":"#F59E0B","Dermatology":"#EC4899","Ophthalmology":"#10B981",
    "Other":"#9CA3AF","Other/Unclassified":"#D1D5DB",
}
def cat_color(c): return CAT_COLORS.get(c, "#9CA3AF")

# ── FIG 1 — Sankey ────────────────────────────────────────────────────────────
def build_sankey():
    total = len(all_df)
    dur_order  = ["CHRONIC","LONG-TERM","PERIODIC","SHORT","OTHER"]
    dur_counts = all_df["Duration_Class"].value_counts()

    chronic_df  = all_df[all_df["Duration_Class"].isin(["CHRONIC","LONG-TERM"])]
    cat_counts_raw = chronic_df["Disease_Category"].value_counts()
    TOP_N   = 10
    top_cats = cat_counts_raw.head(TOP_N).index.tolist()

    node_labels = [f"All Active\n({total:,} ingredients)"]
    dur_node = {}
    for d in dur_order:
        dur_node[d] = len(node_labels)
        node_labels.append(f"{d}\n({int(dur_counts.get(d,0)):,})")
    n_chron = int(chronic_df.shape[0])
    node_labels.append(f"Chronic/Long-term\n({n_chron:,})")
    chron_idx = len(node_labels)-1
    cat_node = {}
    for cat in top_cats:
        cat_node[cat] = len(node_labels)
        node_labels.append(f"{cat}\n({int(cat_counts_raw.get(cat,0)):,})")
    other_tot = int(cat_counts_raw[~cat_counts_raw.index.isin(top_cats)].sum())
    other_idx = len(node_labels)
    node_labels.append(f"Other\n({other_tot:,})")

    node_colors = ["#1E3A5F"] + [DUR_COLORS[d] for d in dur_order] + ["#1D4ED8"]
    node_colors += [cat_color(c) for c in top_cats] + ["#9CA3AF"]

    src,tgt,val,lc=[],[],[],[]
    def add(s,t,v,c="#CBD5E1"):
        src.append(s);tgt.append(t);val.append(v);lc.append(c)
    for d in dur_order:
        add(0,dur_node[d],int(dur_counts.get(d,0)),DUR_COLORS[d])
    add(dur_node["CHRONIC"],chron_idx,int(dur_counts.get("CHRONIC",0)),"#60A5FA")
    add(dur_node["LONG-TERM"],chron_idx,int(dur_counts.get("LONG-TERM",0)),"#A78BFA")
    for cat in top_cats:
        add(chron_idx,cat_node[cat],int(cat_counts_raw.get(cat,0)),cat_color(cat))
    add(chron_idx,other_idx,other_tot,"#9CA3AF")

    fig=go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(pad=16,thickness=20,line=dict(color="white",width=.5),
                  label=node_labels,color=node_colors,hovertemplate="%{label}<extra></extra>"),
        link=dict(source=src,target=tgt,value=val,color=lc,
                  hovertemplate="%{source.label} → %{target.label}: %{value:,}<extra></extra>"),
    ))
    fig.update_layout(title=dict(text=f"<b>FDA Orange Book — {total:,} Active Ingredients → Duration → Disease</b>",
                                  font=dict(size=14)),
                      font=dict(size=10),margin=dict(l=10,r=10,t=50,b=10),
                      height=560,paper_bgcolor="#F8FAFC")
    return fig

# ── FIG 2 — Donut ─────────────────────────────────────────────────────────────
def build_donut():
    total  = len(all_df)
    order  = ["CHRONIC","LONG-TERM","PERIODIC","SHORT","OTHER"]
    counts = all_df["Duration_Class"].value_counts()
    vals   = [int(counts.get(c,0)) for c in order]
    fig    = go.Figure(go.Pie(
        labels=[f"{c}\n({v:,})" for c,v in zip(order,vals)],
        values=vals, hole=.55,
        marker=dict(colors=[DUR_COLORS[c] for c in order],line=dict(color="white",width=2)),
        textinfo="label+percent",textfont=dict(size=10),
        hovertemplate="<b>%{label}</b><br>%{value:,} ingredients (%{percent})<extra></extra>",
        pull=[.04 if c in ("CHRONIC","LONG-TERM") else 0 for c in order],
    ))
    fig.add_annotation(text=f"<b>{total:,}</b><br>ingredients",x=.5,y=.5,
                       showarrow=False,font=dict(size=12,color="#1E3A5F"))
    fig.update_layout(title=dict(text="<b>Duration Classification</b>",font=dict(size=14)),
                      showlegend=False,margin=dict(l=10,r=10,t=50,b=10),
                      height=400,paper_bgcolor="#F8FAFC")
    return fig

# ── FIG 3 — Disease category bar ──────────────────────────────────────────────
def build_disease_bar():
    cc = chr_df["Disease_Category"].value_counts().reset_index()
    cc.columns=["Category","Count"]
    cc=cc.sort_values("Count")
    fig=go.Figure(go.Bar(
        x=cc["Count"],y=cc["Category"],orientation="h",
        marker=dict(color=[cat_color(c) for c in cc["Category"]],line=dict(color="white",width=.5)),
        text=cc["Count"],textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x:,} chronic/long-term<extra></extra>",
    ))
    fig.update_layout(title=dict(text="<b>Disease Category — Chronic & Long-term Drugs</b>",font=dict(size=14)),
                      xaxis=dict(title="Ingredients",showgrid=True,gridcolor="#E2E8F0"),
                      yaxis=dict(tickfont=dict(size=10)),
                      margin=dict(l=10,r=70,t=60,b=40),height=480,
                      paper_bgcolor="#F8FAFC",plot_bgcolor="#F8FAFC")
    return fig

# ── FIG 4 — Top by generic competitors ───────────────────────────────────────
def build_generic_bar():
    top=chr_df.nlargest(30,"Generic_Competitor_Count")[
        ["Ingredient","Generic_Competitor_Count","Disease_Category"]].copy()
    top=top.sort_values("Generic_Competitor_Count")
    top["Label"]=top["Ingredient"].str[:45]
    fig=go.Figure(go.Bar(
        x=top["Generic_Competitor_Count"],y=top["Label"],orientation="h",
        marker=dict(color=[cat_color(c) for c in top["Disease_Category"]],line=dict(color="white",width=.5)),
        text=top["Generic_Competitor_Count"],textposition="outside",
        customdata=list(zip(top["Disease_Category"],top["Ingredient"])),
        hovertemplate="<b>%{customdata[1]}</b><br>Category: %{customdata[0]}<br>ANDA competitors: %{x:,}<extra></extra>",
    ))
    fig.update_layout(title=dict(text="<b>Generic Competition — Top 30 Chronic Drugs by ANDA Count</b>",font=dict(size=14)),
                      xaxis=dict(title="# ANDA Generic Competitors",showgrid=True,gridcolor="#E2E8F0"),
                      yaxis=dict(tickfont=dict(size=9)),
                      margin=dict(l=10,r=70,t=60,b=40),height=600,
                      paper_bgcolor="#F8FAFC",plot_bgcolor="#F8FAFC")
    return fig

# ── FIG 5 — Patent cliff scatter ──────────────────────────────────────────────
def build_patent_scatter():
    df=chr_df.copy()
    df=df[df["Patent_Expiry_Year"].notna()&(df["Generic_Competitor_Count"]>0)]
    df["Patent_Expiry_Year"]=df["Patent_Expiry_Year"].astype(int)
    df=df[df["Patent_Expiry_Year"].between(2020,2037)]
    fig=go.Figure()
    for cat,grp in df.groupby("Disease_Category"):
        fig.add_trace(go.Scatter(
            x=grp["Patent_Expiry_Year"],y=grp["Generic_Competitor_Count"],
            mode="markers",name=cat,
            marker=dict(color=cat_color(cat),size=8,opacity=.75,line=dict(color="white",width=.5)),
            text=grp["Ingredient"],
            hovertemplate="<b>%{text}</b><br>Patent expiry: %{x}<br>ANDA competitors: %{y:,}<extra></extra>",
        ))
    fig.add_vline(x=2026,line=dict(color="#EF4444",dash="dot",width=1.5),
                  annotation_text="Today (2026)",annotation_position="top right",
                  annotation_font_color="#EF4444")
    fig.update_layout(title=dict(text="<b>Patent-Cliff: Expiry Year vs Generic Competition</b>",font=dict(size=14)),
                      xaxis=dict(title="Latest Patent Expiry Year",dtick=1,showgrid=True,gridcolor="#E2E8F0"),
                      yaxis=dict(title="# ANDA Generic Competitors",showgrid=True,gridcolor="#E2E8F0"),
                      legend=dict(title="Disease Category",font=dict(size=9),x=1.02,xanchor="left"),
                      margin=dict(l=40,r=160,t=60,b=50),height=480,
                      paper_bgcolor="#F8FAFC",plot_bgcolor="#F8FAFC")
    return fig

# ── FIG 6 — Revenue bar (top 30 by Medicaid spend) ───────────────────────────
def build_revenue_bar():
    df=chr_df[chr_df["Medicaid_M"]>0].nlargest(30,"Medicaid_M").copy()
    df=df.sort_values("Medicaid_M")
    df["Label"]=df["Ingredient"].str[:42]
    # merge gene
    df=df.merge(tgt_df[["Ingredient","Gene_Symbol(s)"]].rename(columns={"Gene_Symbol(s)":"GeneSymbols"}),on="Ingredient",how="left")
    df["GeneShort"]=df["GeneSymbols"].fillna("").apply(
        lambda g: g.split(" | ")[0].split(",")[0].strip()[:12])
    fig=go.Figure(go.Bar(
        x=df["Medicaid_M"]/1000,y=df["Label"],orientation="h",
        marker=dict(color=[cat_color(c) for c in df["Disease_Category"]],
                    line=dict(color="white",width=.5)),
        text=[f"${v/1000:.1f}B" for v in df["Medicaid_M"]],textposition="outside",
        customdata=list(zip(df["Disease_Category"],df["GeneShort"].fillna(""),df["Ingredient"])),
        hovertemplate="<b>%{customdata[2]}</b><br>Category: %{customdata[0]}<br>Target: %{customdata[1]}<br>Medicaid 2023: $%{x:.2f}B<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="<b>Top 30 Chronic Drugs by 2023 Medicaid Reimbursement</b><br>"
                        "<sup>Color = disease category | Label = Medicaid spend (USD B)</sup>",font=dict(size=14)),
        xaxis=dict(title="2023 Medicaid Reimbursement (USD B)",showgrid=True,gridcolor="#E2E8F0",
                   tickprefix="$",ticksuffix="B"),
        yaxis=dict(tickfont=dict(size=9)),
        margin=dict(l=10,r=80,t=70,b=40),height=680,
        paper_bgcolor="#F8FAFC",plot_bgcolor="#F8FAFC")
    return fig

# ── FIG 7 — Approval decade bar ───────────────────────────────────────────────
def build_decade_bar():
    df=chr_df.copy()
    df=df[df["Earliest_Approval"].notna()&(df["Earliest_Approval"]!="")]
    df["Year"]=pd.to_datetime(df["Earliest_Approval"],errors="coerce").dt.year
    df=df.dropna(subset=["Year"])
    df["Decade"]=(df["Year"]//10*10).astype(int).astype(str)+"s"
    dc=df.groupby(["Decade","Disease_Category"]).size().reset_index(name="Count")
    decade_order=sorted(dc["Decade"].unique())
    cats=[c for c in CAT_COLORS if c!="Other/Unclassified"]
    fig=go.Figure()
    for cat in cats:
        sub=dc[dc["Disease_Category"]==cat].set_index("Decade").reindex(decade_order,fill_value=0).reset_index()
        fig.add_trace(go.Bar(x=sub["Decade"],y=sub["Count"],name=cat,
                              marker_color=cat_color(cat),
                              hovertemplate=f"<b>{cat}</b><br>%{{x}}: %{{y:,}}<extra></extra>"))
    fig.update_layout(barmode="stack",
                      title=dict(text="<b>Chronic Drug Approvals by Decade</b>",font=dict(size=14)),
                      xaxis=dict(title="Approval Decade",categoryorder="array",categoryarray=decade_order),
                      yaxis=dict(title="Ingredients",showgrid=True,gridcolor="#E2E8F0"),
                      legend=dict(title="Disease Category",font=dict(size=9),x=1.02,xanchor="left"),
                      margin=dict(l=40,r=160,t=60,b=50),height=450,
                      paper_bgcolor="#F8FAFC",plot_bgcolor="#F8FAFC")
    return fig

# ── FIG 9 — Drug Modality Pie chart ──────────────────────────────────────────
def build_modality_pie():
    gsrs_df = pd.read_csv("orangebook_substance_classes.csv")
    # For chronic drugs only
    chronic_ings = set(chronic.keys())
    gsrs_chronic = gsrs_df[gsrs_df["Ingredient"].isin(chronic_ings)].copy()

    MODALITY_COLORS_PY = {
        "chemical":            "#2563EB",
        "protein":             "#7C3AED",
        "nucleicAcid":         "#0891B2",
        "polymer":             "#D97706",
        "mixture":             "#059669",
        "structurallyDiverse": "#DC2626",
        "concept":             "#9CA3AF",
        "specifiedSubstanceG1":"#F97316",
        "unknown":             "#6B7280",
    }
    counts = gsrs_chronic["Substance_Class"].value_counts().reset_index()
    counts.columns = ["Modality","Count"]

    colors = [MODALITY_COLORS_PY.get(m,"#9CA3AF") for m in counts["Modality"]]
    labels_display = [f"{m}\n({n:,})" for m,n in zip(counts["Modality"],counts["Count"])]

    fig = go.Figure(go.Pie(
        labels=labels_display,
        values=counts["Count"],
        hole=0.5,
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textinfo="label+percent",
        textfont=dict(size=10),
        hovertemplate="<b>%{label}</b><br>%{value} drugs (%{percent})<extra></extra>",
        pull=[0.05 if m in ("protein","nucleicAcid") else 0 for m in counts["Modality"]],
    ))
    total_chronic = len(chronic_ings)
    fig.add_annotation(
        text=f"<b>{total_chronic}</b><br>chronic drugs",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=12, color="#1E3A5F"),
    )
    fig.update_layout(
        title=dict(
            text="<b>Drug Modality — Chronic & Long-term Drugs</b><br>"
                 "<sup>FDA GSRS substance class | protein/nucleicAcid highlighted</sup>",
            font=dict(size=14)),
        showlegend=True,
        legend=dict(orientation="v", x=1.02, xanchor="left", font=dict(size=10)),
        margin=dict(l=10, r=130, t=65, b=20),
        height=420,
        paper_bgcolor="#F8FAFC",
    )
    return fig

# ── TABLE — DataTables.js (sortable + filterable) ────────────────────────────
def build_table_html():
    import json as _json

    # Load substance class for modality column
    substance = {}
    with open("orangebook_substance_classes.csv", encoding="utf-8") as _f:
        for _r in csv.DictReader(_f):
            substance[_r["Ingredient"]] = _r.get("Substance_Class", "")

    # Prepare all rows as JSON for JS
    rows_sorted = sorted(IND_ROWS, key=lambda r: (-r["_rev_val"], r["Drug"].lower()))
    # Category colour map for row styling
    cat_css = {c: col.lstrip("#") for c, col in CAT_COLORS.items()}

    # Build JSON data array
    data_list = []
    for r in rows_sorted:
        rev_raw  = r["Revenue ($B)"]
        ing      = r["_ing"]
        modality = substance.get(ing, "chemical")
        data_list.append({
            "Drug":               r["Drug"],
            "Brand":              r["Brand"],
            "Disease":            r["Disease / Indication"],
            "Category":           r["Category"],
            "Modality":           modality,
            "Target":             r["Target"],
            "Revenue":            float(rev_raw) if rev_raw else 0.0,
            "Dose":               r["Dose"],
            "Frequency":          r["Frequency"],
            "Duration":           r["Duration"],
        })

    data_json = _json.dumps(data_list, ensure_ascii=False)
    cat_json  = _json.dumps(CAT_COLORS)

    # Unique sorted category, duration, modality lists for filter dropdowns
    cats      = sorted({r["Category"] for r in IND_ROWS if r["Category"]})
    modalities = sorted({substance.get(r["_ing"],"chemical") for r in IND_ROWS})

    cat_opts  = "\n".join(f'<option value="{c}">{c}</option>' for c in cats)
    mod_opts  = "\n".join(f'<option value="{m}">{m}</option>' for m in modalities)

    MODALITY_COLORS = {
        "chemical":           "#2563EB",
        "protein":            "#7C3AED",
        "nucleicAcid":        "#0891B2",
        "polymer":            "#D97706",
        "mixture":            "#059669",
        "structurallyDiverse":"#DC2626",
        "concept":            "#9CA3AF",
        "specifiedSubstanceG1":"#F97316",
        "unknown":            "#6B7280",
    }
    mod_colors_json = _json.dumps(MODALITY_COLORS)

    return f"""
<div style="background:#fff;border-radius:12px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.07);">
  <h3 style="color:#1E3A5F;font-size:1rem;margin-bottom:12px;">
    &#9660; Chronic Drugs — Full Sortable & Filterable Table
    <span style="font-size:.75rem;font-weight:400;color:#64748B;margin-left:8px;">
      {len(rows_sorted)} drugs · click column headers to sort · use filters below
    </span>
  </h3>

  <!-- Filter bar -->
  <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px;align-items:center;">
    <div style="flex:1;min-width:180px;">
      <input id="tbl-search" type="text" placeholder="🔍  Search any field …"
        style="width:100%;padding:7px 12px;border:1px solid #CBD5E1;border-radius:8px;font-size:.85rem;outline:none;"/>
    </div>
    <select id="tbl-cat" style="padding:7px 12px;border:1px solid #CBD5E1;border-radius:8px;font-size:.85rem;background:#fff;cursor:pointer;">
      <option value="">All Categories</option>
      {cat_opts}
    </select>
    <select id="tbl-mod" style="padding:7px 12px;border:1px solid #CBD5E1;border-radius:8px;font-size:.85rem;background:#fff;cursor:pointer;">
      <option value="">All Modalities</option>
      {mod_opts}
    </select>
    <select id="tbl-dur" style="padding:7px 12px;border:1px solid #CBD5E1;border-radius:8px;font-size:.85rem;background:#fff;cursor:pointer;">
      <option value="">All Durations</option>
      <option value="Indefinite">CHRONIC (Indefinite)</option>
      <option value="Long-term">LONG-TERM</option>
    </select>
    <button id="tbl-reset" onclick="resetFilters()"
      style="padding:7px 14px;background:#1E3A5F;color:#fff;border:none;border-radius:8px;font-size:.85rem;cursor:pointer;">
      Reset
    </button>
    <span id="tbl-count" style="font-size:.8rem;color:#64748B;white-space:nowrap;"></span>
  </div>

  <!-- Table -->
  <div style="overflow-x:auto;-webkit-overflow-scrolling:touch;">
  <table id="drug-table" style="width:100%;border-collapse:collapse;font-size:.82rem;">
    <thead>
      <tr style="background:#1E3A5F;color:#fff;position:sticky;top:0;z-index:2;">
        <th data-col="Drug"      class="th-sort" style="min-width:130px">Drug &#8597;</th>
        <th data-col="Brand"     class="th-sort" style="min-width:90px">Brand &#8597;</th>
        <th data-col="Disease"   class="th-sort" style="min-width:200px">Disease / Indication &#8597;</th>
        <th data-col="Category"  class="th-sort" style="min-width:110px">Category &#8597;</th>
        <th data-col="Modality"  class="th-sort" style="min-width:90px">Modality &#8597;</th>
        <th data-col="Target"    class="th-sort" style="min-width:90px">Target &#8597;</th>
        <th data-col="Revenue"   class="th-sort th-num" style="min-width:90px">Revenue ($B) &#8597;</th>
        <th data-col="Dose"      class="th-sort" style="min-width:100px">Dose &#8597;</th>
        <th data-col="Frequency" class="th-sort" style="min-width:120px">Frequency &#8597;</th>
        <th data-col="Duration"  class="th-sort" style="min-width:120px">Duration &#8597;</th>
      </tr>
    </thead>
    <tbody id="drug-tbody"></tbody>
  </table>
  </div>

  <!-- Pagination -->
  <div style="display:flex;justify-content:space-between;align-items:center;margin-top:10px;flex-wrap:wrap;gap:8px;">
    <div style="display:flex;align-items:center;gap:8px;font-size:.82rem;color:#64748B;">
      Show
      <select id="tbl-pagesize" style="padding:4px 8px;border:1px solid #CBD5E1;border-radius:6px;font-size:.82rem;">
        <option value="25">25</option>
        <option value="50" selected>50</option>
        <option value="100">100</option>
        <option value="9999">All</option>
      </select>
      rows per page
    </div>
    <div style="display:flex;gap:4px;" id="tbl-pager"></div>
  </div>
</div>

<script>
(function() {{
  const RAW = {data_json};
  const CAT_COLORS = {cat_json};
  const MOD_COLORS = {mod_colors_json};

  // State
  let filtered = [...RAW];
  let sortCol = 'Revenue';
  let sortAsc = false;
  let page = 0;
  let pageSize = 50;

  // Lighten hex for row background
  function hexAlpha(hex, a) {{
    const r=parseInt(hex.slice(1,3),16), g=parseInt(hex.slice(3,5),16), b=parseInt(hex.slice(5,7),16);
    return `rgba(${{r}},${{g}},${{b}},${{a}})`;
  }}

  // Sort
  function sortData() {{
    filtered.sort((a,b) => {{
      let av = a[sortCol], bv = b[sortCol];
      if (sortCol === 'Revenue') {{ av = parseFloat(av)||0; bv = parseFloat(bv)||0; }}
      else {{ av = String(av||'').toLowerCase(); bv = String(bv||'').toLowerCase(); }}
      if (av < bv) return sortAsc ? -1 : 1;
      if (av > bv) return sortAsc ? 1 : -1;
      return 0;
    }});
  }}

  // Filter
  function applyFilters() {{
    const q   = document.getElementById('tbl-search').value.toLowerCase();
    const cat = document.getElementById('tbl-cat').value;
    const mod = document.getElementById('tbl-mod').value;
    const dur = document.getElementById('tbl-dur').value;
    filtered = RAW.filter(r => {{
      if (cat && r.Category !== cat) return false;
      if (mod && r.Modality !== mod) return false;
      if (dur && !r.Duration.startsWith(dur)) return false;
      if (q) {{
        const hay = Object.values(r).join(' ').toLowerCase();
        if (!q.split(' ').every(t => hay.includes(t))) return false;
      }}
      return true;
    }});
    page = 0;
    sortData();
    render();
  }}

  // Render table body
  function render() {{
    const tbody = document.getElementById('drug-tbody');
    const start = page * pageSize;
    const slice = pageSize >= 9000 ? filtered : filtered.slice(start, start + pageSize);
    const total = filtered.length;

    document.getElementById('tbl-count').textContent =
      total === RAW.length ? `${{total}} drugs` : `${{total}} of ${{RAW.length}} drugs`;

    tbody.innerHTML = slice.map((r, i) => {{
      const bg = hexAlpha(CAT_COLORS[r.Category] || '#9CA3AF', i%2===0 ? 0.08 : 0.02);
      const catDot = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;
        background:${{CAT_COLORS[r.Category]||'#9CA3AF'}};margin-right:5px;flex-shrink:0;"></span>`;
      const modColor = MOD_COLORS[r.Modality] || '#9CA3AF';
      const modBadge = `<span style="background:${{modColor}}22;color:${{modColor}};border:1px solid ${{modColor}}44;
        padding:1px 7px;border-radius:10px;font-size:.72rem;font-weight:600;white-space:nowrap;">${{r.Modality}}</span>`;
      const rev = r.Revenue > 0 ? `<span style="font-weight:600;color:#059669;">${{r.Revenue.toFixed(2)}}B</span>` : '<span style="color:#CBD5E1;">—</span>';
      return `<tr style="background:${{bg}};border-bottom:1px solid #E2E8F0;">
        <td style="padding:7px 10px;font-weight:600;color:#1E3A5F;">${{r.Drug}}</td>
        <td style="padding:7px 10px;color:#475569;">${{r.Brand||'—'}}</td>
        <td style="padding:7px 10px;">${{r.Disease}}</td>
        <td style="padding:7px 10px;white-space:nowrap;">${{catDot}}${{r.Category}}</td>
        <td style="padding:7px 10px;">${{modBadge}}</td>
        <td style="padding:7px 10px;font-family:monospace;font-size:.78rem;color:#7C3AED;">${{r.Target||'—'}}</td>
        <td style="padding:7px 10px;text-align:right;">${{rev}}</td>
        <td style="padding:7px 10px;color:#475569;">${{r.Dose||'—'}}</td>
        <td style="padding:7px 10px;color:#475569;">${{r.Frequency||'—'}}</td>
        <td style="padding:7px 10px;font-size:.77rem;color:#64748B;">${{r.Duration}}</td>
      </tr>`;
    }}).join('');

    // Pagination
    renderPager(total);
  }}

  function renderPager(total) {{
    const pager = document.getElementById('tbl-pager');
    if (pageSize >= 9000) {{ pager.innerHTML=''; return; }}
    const nPages = Math.ceil(total / pageSize);
    const btns = [];
    const btnStyle = (active) =>
      `style="padding:4px 10px;border:1px solid #CBD5E1;border-radius:6px;font-size:.8rem;
       cursor:pointer;background:${{active?'#1E3A5F':'#fff'}};color:${{active?'#fff':'#374151'}};"`;

    // Prev
    btns.push(`<button ${{btnStyle(false)}} onclick="goPage(${{page-1}})" ${{page===0?'disabled':''}}>&laquo;</button>`);

    // Page numbers (show window of 5)
    const lo = Math.max(0, Math.min(page-2, nPages-5));
    const hi = Math.min(nPages, lo+5);
    for (let i=lo; i<hi; i++) {{
      btns.push(`<button ${{btnStyle(i===page)}} onclick="goPage(${{i}})">${{i+1}}</button>`);
    }}

    // Next
    btns.push(`<button ${{btnStyle(false)}} onclick="goPage(${{page+1}})" ${{page>=nPages-1?'disabled':''}}>&#187;</button>`);
    pager.innerHTML = btns.join('');
  }}

  window.goPage = function(p) {{
    const nPages = Math.ceil(filtered.length / pageSize);
    page = Math.max(0, Math.min(p, nPages-1));
    render();
    document.getElementById('drug-table').scrollIntoView({{behavior:'smooth',block:'start'}});
  }};

  window.resetFilters = function() {{
    document.getElementById('tbl-search').value = '';
    document.getElementById('tbl-cat').value    = '';
    document.getElementById('tbl-mod').value    = '';
    document.getElementById('tbl-dur').value    = '';
    filtered = [...RAW];
    sortCol = 'Revenue'; sortAsc = false;
    page = 0;
    sortData();
    render();
  }};

  // Column sort
  document.querySelectorAll('.th-sort').forEach(th => {{
    th.style.cursor = 'pointer';
    th.style.userSelect = 'none';
    th.style.padding = '10px 10px';
    th.addEventListener('click', () => {{
      const col = th.dataset.col;
      if (sortCol === col) sortAsc = !sortAsc;
      else {{ sortCol = col; sortAsc = col !== 'Revenue'; }}
      sortData();
      page = 0;
      render();
    }});
  }});

  // Live filter events
  ['tbl-search','tbl-cat','tbl-mod','tbl-dur'].forEach(id => {{
    document.getElementById(id).addEventListener('input', applyFilters);
    document.getElementById(id).addEventListener('change', applyFilters);
  }});
  document.getElementById('tbl-pagesize').addEventListener('change', function() {{
    pageSize = parseInt(this.value);
    page = 0;
    render();
  }});

  // Initial render
  sortData();
  render();
}})();
</script>"""

# ── Build all figures ─────────────────────────────────────────────────────────
print("Building figures …")
f_sankey   = build_sankey()
f_donut    = build_donut()
f_disease  = build_disease_bar()
f_generic  = build_generic_bar()
f_patent   = build_patent_scatter()
f_revenue  = build_revenue_bar()
f_decade   = build_decade_bar()
f_modality = build_modality_pie()
TABLE_HTML = build_table_html()   # raw HTML, not Plotly

def to_div(fig, div_id):
    fig.update_layout(autosize=True)
    return fig.to_html(full_html=False,include_plotlyjs=False,div_id=div_id,
                       config={"responsive":True,"displaylogo":False,
                               "modeBarButtonsToRemove":["select2d","lasso2d"]})

# ── Key metrics ───────────────────────────────────────────────────────────────
n_total    = len(all_df)
n_chronic  = int(all_df["Duration_Class"].eq("CHRONIC").sum())
n_longterm = int(all_df["Duration_Class"].eq("LONG-TERM").sum())
n_with_rev = int((chr_df["Medicaid_M"]>0).sum())
total_med  = chr_df["Medicaid_M"].sum()/1000   # $B
n_targets  = chr_df["Gene_Symbol(s)"].dropna().apply(
    lambda g: len([x for x in g.split(" | ") if x.strip()])
).sum()

# ── Assemble HTML ─────────────────────────────────────────────────────────────
HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=5.0"/>
<title>FDA Orange Book — Chronic Use Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
:root{{--bg:#F0F4F8;--card:#fff;--blue:#2563EB;--violet:#7C3AED;--teal:#0891B2;
      --green:#059669;--orange:#D97706;--red:#DC2626;--text:#1E293B;--sub:#64748B;
      --border:#E2E8F0;--pad:clamp(10px,3vw,24px);--r:12px;}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--bg);color:var(--text);overflow-x:hidden;}}
header{{background:linear-gradient(135deg,#1E3A5F 0%,#DC2626 40%,#D97706 100%);color:#fff;padding:clamp(14px,4vw,28px) var(--pad);}}
header h1{{font-size:clamp(1rem,3.5vw,1.5rem);font-weight:700;line-height:1.25;}}
header p{{margin-top:6px;opacity:.85;font-size:clamp(.75rem,2.2vw,.88rem);line-height:1.4;}}
.pipeline{{background:#1E3A5F;padding:12px var(--pad);display:grid;grid-template-columns:repeat(auto-fit,minmax(90px,1fr));gap:8px;}}
.pipe-step{{background:rgba(255,255,255,.11);border:1px solid rgba(255,255,255,.22);border-radius:8px;padding:8px 6px 7px;color:#fff;text-align:center;}}
.pipe-step strong{{display:block;font-size:clamp(1.1rem,3.5vw,1.5rem);font-weight:700;line-height:1.1;}}
.pipe-step span{{font-size:clamp(.62rem,1.8vw,.72rem);opacity:.82;line-height:1.2;display:block;margin-top:2px;}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;padding:14px var(--pad) 0;}}
.metric{{background:var(--card);border-radius:var(--r);padding:14px 16px;border-left:4px solid var(--blue);box-shadow:0 1px 4px rgba(0,0,0,.07);min-width:0;}}
.metric.v{{border-color:var(--violet);}} .metric.t{{border-color:var(--teal);}}
.metric.g{{border-color:var(--green);}} .metric.o{{border-color:var(--orange);}} .metric.r{{border-color:var(--red);}}
.mval{{font-size:clamp(1.5rem,5vw,2.1rem);font-weight:700;color:var(--blue);line-height:1;}}
.metric.v .mval{{color:var(--violet);}} .metric.t .mval{{color:var(--teal);}}
.metric.g .mval{{color:var(--green);}} .metric.o .mval{{color:var(--orange);}} .metric.r .mval{{color:var(--red);}}
.mlabel{{font-size:clamp(.65rem,1.8vw,.75rem);color:var(--sub);margin-top:4px;line-height:1.3;}}
.sec{{font-size:clamp(.6rem,1.8vw,.68rem);font-weight:700;letter-spacing:.07em;text-transform:uppercase;
      color:#fff;padding:3px 10px;border-radius:4px;margin:18px var(--pad) 0;display:inline-block;}}
.s1{{background:#1E3A5F;}} .s2{{background:#DC2626;}} .s3{{background:#D97706;}}
.s4{{background:#0891B2;}} .s5{{background:#059669;}} .s6{{background:#7C3AED;}}
.s7{{background:#10B981;}} .s8{{background:#1E3A5F;}}
.g1{{padding:8px var(--pad);}}
.g2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,440px),1fr));gap:10px;padding:8px var(--pad);}}
.card{{background:var(--card);border-radius:var(--r);padding:8px 6px;box-shadow:0 1px 4px rgba(0,0,0,.07);overflow:hidden;min-width:0;}}
footer{{text-align:center;font-size:clamp(.65rem,1.8vw,.75rem);color:var(--sub);padding:18px var(--pad) 24px;line-height:1.6;}}
</style>
</head>
<body>
<header>
  <h1>FDA Orange Book — Small-Molecule Chronic Use Dashboard</h1>
  <p>{n_total:,} active NDA/ANDA ingredients · duration classification · disease category · generic competition · patent cliff · drug targets · Medicaid revenue</p>
</header>
<div class="pipeline">
  <div class="pipe-step"><strong>{n_total:,}</strong><span>active ingredients</span></div>
  <div class="pipe-step"><strong>5</strong><span>duration classes</span></div>
  <div class="pipe-step"><strong>{n_chronic+n_longterm:,}</strong><span>chronic/long-term</span></div>
  <div class="pipe-step"><strong>13</strong><span>disease categories</span></div>
  <div class="pipe-step"><strong>{n_with_rev:,}</strong><span>with revenue data</span></div>
  <div class="pipe-step"><strong>${total_med:.0f}B</strong><span>total Medicaid 2023</span></div>
</div>
<div class="metrics">
  <div class="metric"><div class="mval">{n_total:,}</div><div class="mlabel">Active ingredients (NDA+ANDA)</div></div>
  <div class="metric v"><div class="mval">{n_chronic:,}</div><div class="mlabel">Strictly chronic</div></div>
  <div class="metric t"><div class="mval">{n_longterm:,}</div><div class="mlabel">Long-term (oncology etc.)</div></div>
  <div class="metric g"><div class="mval">{n_with_rev:,}</div><div class="mlabel">Drugs with Medicaid spend</div></div>
  <div class="metric o"><div class="mval">${total_med:.0f}B</div><div class="mlabel">2023 Medicaid reimbursement</div></div>
  <div class="metric r"><div class="mval">{len(IND_ROWS):,}</div><div class="mlabel">Drug-indication rows</div></div>
</div>

<div class="sec s1">Step 1 — Full Analysis Pipeline</div>
<div class="g1"><div class="card">{to_div(f_sankey,"sankey")}</div></div>

<div class="sec s2">Step 2 — Duration Classification</div>
<div class="g2">
  <div class="card">{to_div(f_donut,"donut")}</div>
  <div class="card">{to_div(f_decade,"decade")}</div>
</div>

<div class="sec s3">Step 3 — Disease Category</div>
<div class="g1"><div class="card">{to_div(f_disease,"disease")}</div></div>

<div class="sec s4">Step 4 — Generic Competition</div>
<div class="g1"><div class="card">{to_div(f_generic,"generic")}</div></div>

<div class="sec s5">Step 5 — 2023 Medicaid Revenue</div>
<div class="g1"><div class="card">{to_div(f_revenue,"revenue")}</div></div>

<div class="sec s6">Step 6 — Patent-Cliff View</div>
<div class="g1"><div class="card">{to_div(f_patent,"patent")}</div></div>

<div class="sec s7">Step 7 — Drug Modality Analysis</div>
<div class="g2">
  <div class="card">{to_div(f_modality,"modality")}</div>
  <div class="card" style="padding:16px;">
    <h4 style="color:#1E3A5F;font-size:.95rem;margin-bottom:10px;">FDA GSRS Modality Definitions</h4>
    <div style="font-size:.82rem;line-height:1.8;color:#374151;">
      <div><span style="color:#2563EB;font-weight:700;">chemical</span> — Conventional small molecules (NDA/ANDA, MW &lt;1000 Da)</div>
      <div><span style="color:#7C3AED;font-weight:700;">protein</span> — Synthetic peptides &lt;40 AA (semaglutide, tirzepatide, liraglutide, teriparatide…)</div>
      <div><span style="color:#0891B2;font-weight:700;">nucleicAcid</span> — Oligonucleotides: siRNA, antisense, PMO (inclisiran, nusinersen, eteplirsen…)</div>
      <div><span style="color:#D97706;font-weight:700;">polymer</span> — Macromolecular chains: heparins, iron complexes, bile acid resins, glatiramer</div>
      <div><span style="color:#059669;font-weight:700;">mixture</span> — Multi-component products: IV solutions, antibiotic combos, fish oil</div>
      <div><span style="color:#DC2626;font-weight:700;">structurallyDiverse</span> — Biologically sourced: albumin, protamine, plant oils</div>
      <div><span style="color:#F97316;font-weight:700;">specifiedSubstanceG1</span> — Complex specified: ferumoxytol nanoparticle, birch triterpenes</div>
      <div><span style="color:#9CA3AF;font-weight:700;">concept</span> — Abstract/kit entries: Tc-99m radiopharmaceutical kits, purified water</div>
    </div>
    <p style="margin-top:12px;font-size:.78rem;color:#64748B;">
      Despite being approved under NDA (Orange Book), FDA's own GSRS substance registry
      classifies 28 drugs as <b>protein</b> and 18 as <b>nucleicAcid</b> — revealing
      an important regulatory boundary between pathway and molecular modality.
    </p>
  </div>
</div>

<div class="sec s8">Step 8 — Drug × Indication Table (all {len(IND_ROWS)} drugs, sortable &amp; filterable)</div>
<div class="g1">{TABLE_HTML}</div>

<footer>
  Data: FDA Orange Book May 2026 · ChEMBL v34 drug targets · CMS Medicaid SDU 2023 · NADAC Dec 2024<br>
  Chronic/long-term: {n_chronic+n_longterm:,} ingredients of {n_total:,} active · July 2026
</footer>
<script>
const IDS=['sankey','donut','decade','disease','generic','revenue','patent','modality'];
const H={{sankey:[400,500,560],donut:[340,380,400],decade:[360,420,450],disease:[380,440,480],
          generic:[500,560,600],revenue:[580,640,680],patent:[360,430,480],modality:[360,400,420]}};
function bp(){{return window.innerWidth<480?0:window.innerWidth<900?1:2;}}
function resizeAll(){{
  const b=bp();
  IDS.forEach(id=>{{
    const el=document.getElementById(id);
    if(!el||!el.data)return;
    const w=el.parentElement?el.parentElement.clientWidth-16:undefined;
    try{{Plotly.relayout(el,{{autosize:true,width:w||undefined,height:H[id][b],
      'margin.l':b===0?8:10,'margin.r':b===0?6:10,'margin.t':b===0?40:55,'margin.b':b===0?30:40,
      'font.size':b===0?9:11}});}}catch(e){{}}
  }});
}}
let _rt;
window.addEventListener('resize',()=>{{clearTimeout(_rt);_rt=setTimeout(resizeAll,120);}});
document.addEventListener('DOMContentLoaded',()=>{{
  let att=0;
  const p=setInterval(()=>{{
    const ready=IDS.every(id=>{{const el=document.getElementById(id);return el&&el.data;}});
    if(ready||att++>40){{clearInterval(p);resizeAll();}}
  }},150);
}});
</script>
</body></html>"""

OUT = "orangebook_chronic_dashboard.html"
with open(OUT,"w",encoding="utf-8") as f:
    f.write(HTML)

print(f"\nDashboard → {OUT}  ({len(HTML)//1024} KB)")
print(f"Indications CSV → orangebook_chronic_indications_clean.csv  ({len(IND_ROWS)} rows)")
