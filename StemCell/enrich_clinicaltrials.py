import csv
import re

IN_CSV = "/Work1/Zijiang/StemCell/clinicaltrials_stem_cell.csv"
OUT_CSV = "/Work1/Zijiang/StemCell/clinicaltrials_stem_cell_enriched.csv"

PHASE_LABELS = {
    "": "Not Reported",
    "NA": "N/A (Device/Behavioral)",
    "EARLY_PHASE1": "Early Phase 1",
    "PHASE1": "Phase 1",
    "PHASE1; PHASE2": "Phase 1/2",
    "PHASE2": "Phase 2",
    "PHASE2; PHASE3": "Phase 2/3",
    "PHASE3": "Phase 3",
    "PHASE4": "Phase 4",
}

CORE_KEYWORDS = [
    r"stem cell", r"\bmsc\b", r"mesenchymal", r"\bhsc\b", r"hematopoietic stem",
    r"haematopoietic stem", r"cord blood", r"\bipsc\b", r"induced pluripotent",
    r"embryonic stem", r"progenitor cell", r"\bcd34\+?\b", r"adipose[- ]derived stem",
    r"umbilical cord.*stem", r"stromal cell",
]
CORE_RE = re.compile("|".join(CORE_KEYWORDS), re.IGNORECASE)

DISEASE_AREA_RULES = [
    ("Oncology / Hematologic Malignancy", [
        r"leukemia", r"lymphoma", r"myeloma", r"cancer", r"tumor", r"tumour",
        r"carcinoma", r"sarcoma", r"neoplasm", r"malignan", r"myelodysplastic",
        r"myelofibrosis", r"blastoma",
    ]),
    ("Neurological", [
        r"stroke", r"parkinson", r"alzheimer", r"multiple sclerosis", r"spinal cord injury",
        r"amyotrophic lateral sclerosis", r"\bals\b", r"cerebral palsy", r"neuropathy",
        r"huntington", r"traumatic brain injury", r"autism", r"charcot-marie-tooth",
        r"neuromyelitis", r"ataxia",
    ]),
    ("Cardiovascular", [
        r"heart failure", r"cardiomyopathy", r"myocardial infarction", r"ischemi",
        r"cardiac", r"coronary", r"peripheral artery disease", r"critical limb ischemia",
        r"hypoplastic left heart", r"congenital heart",
    ]),
    ("Hematologic / Genetic Blood Disorder", [
        r"sickle cell", r"thalassemia", r"hemoglobinopathi", r"hemophilia",
        r"haemophilia", r"anemia", r"aplastic anemia",
    ]),
    ("Immunodeficiency / Genetic Metabolic Disorder", [
        r"immunodeficiency", r"granulomatous disease", r"lysosomal storage",
        r"peroxisomal disorder", r"\bgata2\b", r"inborn error",
    ]),
    ("Orthopedic / Musculoskeletal", [
        r"osteoarthritis", r"cartilage", r"knee", r"bone", r"fracture", r"osteonecrosis",
        r"tendon", r"disc degeneration", r"rotator cuff", r"osteogenesis",
    ]),
    ("Autoimmune / Inflammatory", [
        r"crohn", r"graft versus host", r"graft-versus-host", r"\bgvhd\b",
        r"rheumatoid arthritis", r"lupus", r"systemic sclerosis", r"scleroderma",
        r"ulcerative colitis", r"inflammatory bowel", r"psoriasis", r"ankylosing spondylitis",
    ]),
    ("Ophthalmologic", [
        r"cornea", r"macular degeneration", r"retinitis", r"retinal", r"limbal",
        r"eye", r"ocular",
    ]),
    ("Diabetes / Endocrine", [
        r"diabetes", r"diabetic", r"islet",
    ]),
    ("Dermatology / Wound Healing", [
        r"wound", r"burn", r"ulcer", r"skin", r"epidermolysis",
    ]),
    ("Respiratory", [
        r"copd", r"pulmonary fibrosis", r"ards", r"respiratory distress", r"asthma",
        r"bronchopulmonary dysplasia", r"lung",
    ]),
    ("Renal", [
        r"kidney", r"renal",
    ]),
    ("Gastrointestinal / Liver", [
        r"liver", r"cirrhosis", r"hepat", r"fistula",
    ]),
    ("Infectious Disease / COVID-19", [
        r"covid", r"sars-cov", r"sepsis", r"pneumonia",
    ]),
    ("Hematopoietic Stem Cell Transplant (Supportive Care)", [
        r"hematopoietic stem cell transplant", r"haematopoietic stem cell transplant",
        r"bone marrow transplant",
    ]),
    ("Reproductive / Urologic", [
        r"erectile", r"infertility", r"ovarian", r"urinary incontinence",
    ]),
    ("Dental / Oral", [
        r"periodontal", r"dental", r"oral mucos",
    ]),
    ("Aesthetic / Anti-aging / Healthy Volunteer", [
        r"healthy volunteer", r"anti-aging", r"aging", r"cosmetic",
    ]),
]


# Best-effort detection of an engineered/induced gene or protein payload the
# cell product expresses or secretes (e.g. a GLP-1-expressing stem cell, or a
# CD19 CAR-NK cell) -- separate from the cell type itself. This only catches
# what a trial title/intervention name explicitly names; most engineered
# payloads are only documented in the full protocol, so this is a low-recall,
# high-precision flag (blank does not mean "not engineered").

# Specific-antigen CAR patterns are checked first; if any of them hit, the
# generic "CAR construct" bucket is suppressed for that row to avoid a
# redundant double-tag (e.g. "CD19 CAR; CAR construct (unspecified antigen)").
GENE_TARGET_SPECIFIC_RULES = [
    ("GLP-1", [r"glp-?1"]),
    ("FGF21", [r"fgf-?21"]),
    ("BDNF/GDNF/VEGF/HGF (neurotrophic factors)", [r"nurown", r"msc-ntf", r"neurotrophic factor"]),
    ("CD19 CAR", [r"cd19[\s-]?car", r"car[\s-]?.{0,10}cd19"]),
    ("CD20 CAR", [r"cd20[\s-]?car", r"car[\s-]?.{0,10}cd20"]),
    ("BCMA CAR", [r"bcma[\s-]?car", r"car[\s-]?.{0,10}bcma"]),
    ("IL-15", [r"il-?15"]),
    ("Factor VIII", [r"factor viii"]),
    ("Factor IX", [r"factor ix"]),
    ("Telomerase (TERT)", [r"\btert\b", r"telomerase"]),
]
GENE_TARGET_GENERIC_CAR = ("CAR construct (unspecified antigen)",
                            re.compile(r"\bcar-?t\b|\bcar-?nk\b|chimeric antigen receptor", re.IGNORECASE))
GENE_TARGET_SPECIFIC_COMPILED = [(name, re.compile("|".join(pats), re.IGNORECASE))
                                  for name, pats in GENE_TARGET_SPECIFIC_RULES]
_CAR_SPECIFIC_NAMES = {"CD19 CAR", "CD20 CAR", "BCMA CAR"}


def classify_gene_target(title, intervention_name):
    text = f"{title or ''} {intervention_name or ''}"
    hits = []
    for name, rx in GENE_TARGET_SPECIFIC_COMPILED:
        if rx.search(text):
            hits.append(name)
    if not (_CAR_SPECIFIC_NAMES & set(hits)) and GENE_TARGET_GENERIC_CAR[1].search(text):
        hits.append(GENE_TARGET_GENERIC_CAR[0])
    return "; ".join(hits)


def classify_disease_area(condition_text):
    text = condition_text.lower()
    for area, patterns in DISEASE_AREA_RULES:
        for p in patterns:
            if re.search(p, text):
                return area
    return "Other / Unclassified"


def classify_stage(phase, status):
    if status == "APPROVED_FOR_MARKETING":
        return "Approved"
    return PHASE_LABELS.get(phase, phase or "Not Reported")


# Phrases that describe a *transplant/mobilization procedure as context*
# (e.g. a drug trial in patients undergoing HSCT, or a mobilization-agent
# trial) rather than the stem cells themselves being the studied product.
# A title-only match (no core keyword in the intervention name) doesn't count
# unless it survives stripping these context phrases -- otherwise e.g. an
# expanded-access trial of ruxolitinib "following allogeneic hematopoietic
# stem cell transplant" gets wrongly flagged as a stem-cell-product trial.
CONTEXT_ONLY_RE = re.compile(
    r"(allogeneic |autologous )?hematopoietic stem cells?( transplant\w*)?|"
    r"(allogeneic |autologous )?haematopoietic stem cells?( transplant\w*)?|"
    r"stem cell transplant\w*|bone marrow transplant\w*|"
    r"stem cells? mobili[sz]\w*|peripheral blood stem cells?( collection| mobili[sz]\w*)?",
    re.IGNORECASE,
)


def is_core_stem_cell(title, intervention_name):
    if CORE_RE.search(intervention_name or ""):
        return True
    title = title or ""
    if not CORE_RE.search(title):
        return False
    stripped = CONTEXT_ONLY_RE.sub(" ", title)
    return bool(CORE_RE.search(stripped))


CELL_TYPE_RULES = [
    ("iPSC (induced pluripotent)", [r"induced pluripotent", r"\bipsc"]),
    ("Embryonic Stem Cell (ESC)", [r"embryonic stem"]),
    ("Cord Blood / HSC", [r"cord blood", r"hematopoietic stem", r"haematopoietic stem", r"\bhsc\b", r"\bcd34\+?\b"]),
    ("Mesenchymal Stem Cell (MSC)", [r"mesenchymal", r"\bmsc\b", r"stromal cell"]),
    ("Adipose-Derived Stem Cell", [r"adipose[- ]derived"]),
    ("Neural Stem Cell", [r"neural stem"]),
    ("Limbal Stem Cell", [r"limbal stem"]),
    ("Progenitor Cell", [r"progenitor cell"]),
]
CELL_TYPE_COMPILED = [(name, re.compile("|".join(pats), re.IGNORECASE)) for name, pats in CELL_TYPE_RULES]


def classify_cell_type(title, intervention_name):
    text = f"{title or ''} {intervention_name or ''}"
    for name, rx in CELL_TYPE_COMPILED:
        if rx.search(text):
            return name
    if CORE_RE.search(text):
        return "Stem Cell (Unspecified Type)"
    return ""


def main():
    with open(IN_CSV, newline="") as f:
        rows = list(csv.DictReader(f))

    for r in rows:
        r["Disease_Area"] = classify_disease_area(r["Condition"])
        r["Stage"] = classify_stage(r["Phase"], r["Overall_Status"])
        r["Core_Stem_Cell_Product"] = "Yes" if is_core_stem_cell(r["Title"], r["Intervention_Name"]) else "No"
        r["Cell_Type"] = classify_cell_type(r["Title"], r["Intervention_Name"])
        r["Gene_Target"] = classify_gene_target(r["Title"], r["Intervention_Name"])
        r["Data_Source"] = "ClinicalTrials.gov"

    fieldnames = list(rows[0].keys())
    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("wrote", len(rows), "rows ->", OUT_CSV)
    core = sum(1 for r in rows if r["Core_Stem_Cell_Product"] == "Yes")
    print("core stem-cell-product trials:", core, "of", len(rows))


if __name__ == "__main__":
    main()
