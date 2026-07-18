"""
Canonicalization + epidemiology reference data for the Target/Disease
Opportunity Dashboard (build_opportunity_dashboard.py).

Two epidemiology sourcing tracks:
  - "orphanet": live-queried via the ToolUniverse MCP (Orphanet_get_epidemiology),
    using the ORPHA code's own prevalence *class* bucket (e.g. "1-9 / 100 000"),
    not the raw mean_value field (which is inconsistently scaled across rows/
    sources in Orphanet's own data — the class bucket is Orphanet's standardized,
    citable figure). We take the bucket midpoint as prevalence-per-100,000.
  - "curated": well-established literature/CDC/registry estimates for common
    chronic diseases that Orphanet doesn't carry (it only covers rare diseases;
    non-rare terms come back explicitly flagged "NON RARE IN EUROPE" with no
    prevalence data).

All prevalence figures are expressed as estimated cases per 100,000 population,
scaled against the US population (~335M) to get an estimated patient count.
These are order-of-magnitude planning estimates, not clinical-grade figures.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Canonicalize near-duplicate disease labels from Purple Book / Orange Book
# indication text into one bucket per real-world condition.
# ─────────────────────────────────────────────────────────────────────────────
DISEASE_CANON = {
    "Ankylosing spondylitis / axSpA": "Ankylosing spondylitis",
    "Generalized myasthenia gravis (gMG)": "Generalized myasthenia gravis",
    "Type 2 diabetes mellitus": "Type 2 diabetes",
    "Diabetes mellitus": "Type 2 diabetes",
    "Diabetic retinopathy (all DR)": "Diabetic retinopathy",
    "Late-onset Pompe disease (+miglustat)": "Late-onset Pompe disease (LOPD)",
    "Anemia of chronic kidney disease (dialysis)": "Anemia of CKD (non-dialysis)",
    "Hemophilia A (prophylaxis, extended half-life)": "Hemophilia A (prophylaxis)",
    "Hemophilia A without inhibitors (prophylaxis)": "Hemophilia A with inhibitors (prophylaxis)",
    "Hemophilia A/B with inhibitors (prophylaxis)": "Hemophilia A/B with inhibitors",
    "Macular edema from retinal vein occlusion (RVO)": "Retinal vein occlusion (BRVO / CRVO)",
    "CV risk reduction": "Cardiovascular risk reduction (secondary prevention)",
    "Cardiovascular risk reduction (T2DM with CVD)": "Cardiovascular risk reduction (secondary prevention)",
    "Myocardial infarction (risk reduction)": "Cardiovascular risk reduction (secondary prevention)",
    "Stroke (risk reduction)": "Cardiovascular risk reduction (secondary prevention)",
}

def canon(name: str) -> str:
    return DISEASE_CANON.get(name, name)


# ─────────────────────────────────────────────────────────────────────────────
# Indications excluded from patient-population / unmet-need scoring: not a
# distinct disease (cosmetic indication, life-stage population, or a
# secondary-prevention label riding on an already-counted underlying disease).
# Still shown in the market/competitive-landscape table with a note.
# ─────────────────────────────────────────────────────────────────────────────
EPI_EXCLUDED = {
    "Glabellar (frown) lines": "Cosmetic indication, not a disease — no patient-population/unmet-need estimate.",
    "Menopausal / hormone therapy": "Physiological life stage, not a disease — sized by demographic population, not prevalence.",
    "Cardiovascular risk reduction (secondary prevention)": "Secondary-prevention label on patients already counted under Type 2 diabetes / their primary CV diagnosis.",
}

# Orphanet prevalence-class bucket -> midpoint, in cases per 100,000 population.
_CLASS_MIDPOINT_PER_100K = {
    "<1 / 1 000 000": 0.05,
    "1-9 / 1 000 000": 0.5,
    "1-9 / 100 000": 5.0,
    "1-5 / 10 000": 30.0,
    "6-9 / 10 000": 75.0,
    "1-5 / 1 000": 300.0,
    "6-9 / 1 000": 750.0,
    ">1 / 1000": 150.0,
}

US_POPULATION = 335_000_000

# ─────────────────────────────────────────────────────────────────────────────
# EPIDEMIOLOGY: canonical disease -> {
#   prevalence_per_100k, source ("orphanet"/"curated"), note, orpha_code
# }
# ─────────────────────────────────────────────────────────────────────────────
EPIDEMIOLOGY = {
    # ── Rare diseases — Orphanet (ToolUniverse), class-bucket midpoint ────────
    "Achondroplasia": dict(prevalence_per_100k=5.0, source="orphanet", orpha_code=15,
        note="Orphanet class 1-9/100,000 (worldwide birth prevalence, PMID 32803853)."),
    "Acromegaly": dict(prevalence_per_100k=5.0, source="orphanet", orpha_code=963,
        note="Orphanet class 1-9/100,000 (US point prevalence, PMID 26792654)."),
    "Adult growth hormone deficiency (AGHD)": dict(prevalence_per_100k=30.0, source="orphanet", orpha_code=631,
        note="Orphanet class 1-5/10,000 (Europe, non-acquired isolated GH deficiency, not yet validated)."),
    "Pediatric growth hormone deficiency": dict(prevalence_per_100k=30.0, source="orphanet", orpha_code=631,
        note="Orphanet class 1-5/10,000 (Europe, non-acquired isolated GH deficiency, not yet validated)."),
    "Alpha-1 antitrypsin deficiency (AATD) with emphysema": dict(prevalence_per_100k=30.0, source="orphanet", orpha_code=60,
        note="Orphanet class 1-5/10,000 (US, severe deficiency variants, PMID 10954251/18565211)."),
    "Alpha-mannosidosis": dict(prevalence_per_100k=0.5, source="orphanet", orpha_code=61,
        note="Orphanet class 1-9/1,000,000 (Europe, EMA 2005)."),
    "Arginase 1 deficiency (hyperargininemia)": dict(prevalence_per_100k=0.5, source="orphanet", orpha_code=90,
        note="Orphanet class 1-9/1,000,000, listed as 'Argininemia' (US, PMID 8794176)."),
    "Congenital sucrase-isomaltase deficiency (CSID)": dict(prevalence_per_100k=30.0, source="orphanet", orpha_code=35122,
        note="Orphanet class 1-5/10,000 (Europe general population; much higher in Indigenous Arctic populations)."),
    "Cushing's syndrome": dict(prevalence_per_100k=5.0, source="orphanet", orpha_code=96253,
        note="Orphanet class 1-9/100,000, using 'Cushing disease' (pituitary ACTH-secreting form, EMA)."),
    "Generalized myasthenia gravis": dict(prevalence_per_100k=30.0, source="orphanet", orpha_code=589,
        note="Orphanet class 1-5/10,000 (US, PMID 8909435)."),
    "Hemophilia A (prophylaxis)": dict(prevalence_per_100k=5.0, source="orphanet", orpha_code=98878,
        note="Orphanet class 1-9/100,000 (US, PMID 19845775)."),
    "Hemophilia A with inhibitors (prophylaxis)": dict(prevalence_per_100k=5.0, source="orphanet", orpha_code=98878,
        note="Orphanet class 1-9/100,000 (US Hemophilia A base rate; inhibitor subset is a fraction of this)."),
    "Hemophilia A/B with inhibitors": dict(prevalence_per_100k=3.0, source="orphanet", orpha_code=98878,
        note="Orphanet class 1-9/100,000 blended A/B; inhibitor subset is a fraction of this."),
    "Hemophilia B (prophylaxis)": dict(prevalence_per_100k=5.0, source="orphanet", orpha_code=98879,
        note="Orphanet class 1-9/100,000 (Europe, PMID 21649801)."),
    "Juvenile idiopathic arthritis": dict(prevalence_per_100k=5.0, source="orphanet", orpha_code=92,
        note="Orphanet class 1-9/100,000 (US, PMID 23588938)."),
    "Fabry disease": dict(prevalence_per_100k=0.5, source="orphanet", orpha_code=324,
        note="Orphanet class 1-9/1,000,000 (worldwide birth prevalence)."),
    "Late-onset Pompe disease (LOPD)": dict(prevalence_per_100k=5.0, source="orphanet", orpha_code=420429,
        note="Orphanet class 1-9/100,000 (worldwide birth prevalence, PMID 6789760)."),
    "MPS II (Hunter syndrome)": dict(prevalence_per_100k=0.5, source="orphanet", orpha_code=580,
        note="Orphanet class 1-9/1,000,000 (worldwide birth prevalence)."),
    "Polycythemia vera (PV)": dict(prevalence_per_100k=30.0, source="orphanet", orpha_code=729,
        note="Orphanet class 1-5/10,000 (Europe, EMA 2014)."),
    "Pulmonary arterial hypertension (PAH) – WHO Group I": dict(prevalence_per_100k=5.0, source="orphanet", orpha_code=182090,
        note="Orphanet class 1-9/100,000 (US, PMID 21793646)."),
    "Severe chronic neutropenia (SCN)": dict(prevalence_per_100k=0.5, source="orphanet", orpha_code=42738,
        note="Orphanet class 1-9/1,000,000 (Europe expert estimate)."),
    "Short bowel syndrome": dict(prevalence_per_100k=5.0, source="orphanet", orpha_code=104008,
        note="Orphanet class 1-9/100,000 (Europe, EMA 2019)."),
    "Systemic lupus erythematosus (SLE)": dict(prevalence_per_100k=30.0, source="orphanet", orpha_code=536,
        note="Orphanet class 1-5/10,000 (US, PMID 15333286); consistent with ~55-73/100,000 US estimates."),

    # ── Rare diseases — Orphanet had no usable prevalence row; curated ────────
    "Acid sphingomyelinase deficiency (ASMD / NPD-A/B)": dict(prevalence_per_100k=0.1, source="curated",
        note="No Orphanet prevalence class returned; literature estimate ~0.4-2 per million (Niemann-Pick A/B)."),
    "Cervical dystonia": dict(prevalence_per_100k=7.0, source="curated",
        note="No Orphanet prevalence class returned; literature range ~5-9 per 100,000 (isolated cervical dystonia)."),
    "LDL-C reduction (HeFH / ASCVD)": dict(prevalence_per_100k=400.0, source="curated",
        note="Heterozygous familial hypercholesterolemia ~1:250 (CDC/FH Foundation); Orphanet flags 'NON RARE IN EUROPE' with no prevalence row."),
    "HIV-associated lipodystrophy (abdominal fat excess)": dict(prevalence_per_100k=36.0, source="curated",
        note="~1.2M US people living with HIV; lipodystrophy subset on/after older ART regimens estimated ~10%."),

    # ── Common chronic diseases — curated (Orphanet explicitly non-rare / no data) ─
    "Rheumatoid arthritis": dict(prevalence_per_100k=600.0, source="curated",
        note="~0.5-1% of US adults (CDC); Orphanet returns 'NON RARE IN EUROPE' with no prevalence row."),
    "Ankylosing spondylitis": dict(prevalence_per_100k=250.0, source="curated",
        note="~0.2-0.35% of US adults; Orphanet returns 'NON RARE IN EUROPE'."),
    "Crohn's disease": dict(prevalence_per_100k=200.0, source="curated",
        note="~700K US patients (CDC IBD estimate); Orphanet returns 'NON RARE IN EUROPE'."),
    "Ulcerative colitis": dict(prevalence_per_100k=250.0, source="curated",
        note="~900K US patients (CDC IBD estimate); Orphanet returns 'NON RARE IN EUROPE'."),
    "Psoriatic arthritis": dict(prevalence_per_100k=150.0, source="curated",
        note="~0.1-0.2% of US adults (~30% of psoriasis patients); Orphanet returns 'NON RARE IN EUROPE'."),
    "Hidradenitis suppurativa": dict(prevalence_per_100k=1000.0, source="curated",
        note="~1% of adults (literature range 0.05-4%); Orphanet returns 'NON RARE IN EUROPE'."),
    "Plaque psoriasis": dict(prevalence_per_100k=2500.0, source="curated",
        note="~2-3% of US adults (National Psoriasis Foundation)."),
    "Type 1 diabetes mellitus": dict(prevalence_per_100k=540.0, source="curated",
        note="~1.8M US patients (~0.5% of population, ADA/CDC); Orphanet resolves to a narrower monogenic-diabetes bucket."),
    "Type 2 diabetes": dict(prevalence_per_100k=11000.0, source="curated",
        note="~11% of US adults / ~38M patients (CDC National Diabetes Statistics Report)."),
    "Obesity / weight management": dict(prevalence_per_100k=42000.0, source="curated",
        note="~42% of US adults (CDC NHANES)."),
    "Osteoporosis": dict(prevalence_per_100k=3000.0, source="curated",
        note="~10M diagnosed US patients (NOF/BHOF)."),
    "Breast cancer": dict(prevalence_per_100k=1200.0, source="curated",
        note="~4M US women living with a breast cancer history (SEER)."),
    "Prostate cancer": dict(prevalence_per_100k=1000.0, source="curated",
        note="~3.3M US men living with a prostate cancer history (SEER)."),
    "Endometriosis": dict(prevalence_per_100k=2000.0, source="curated",
        note="~10% of US reproductive-age women (ACOG)."),
    "Chronic constipation": dict(prevalence_per_100k=15000.0, source="curated",
        note="~15% of US adults report chronic constipation (population-level, not all treated pharmacologically)."),
    "Irritable bowel syndrome": dict(prevalence_per_100k=12000.0, source="curated",
        note="~10-15% of US adults (AGA)."),
    "Diabetic retinopathy": dict(prevalence_per_100k=2900.0, source="curated",
        note="~9.6M US adults with diabetic retinopathy (CDC Vision Health Initiative)."),
    "Diabetic macular edema (DME)": dict(prevalence_per_100k=450.0, source="curated",
        note="~1.5M US patients (NEI)."),
    "Neovascular (wet) AMD": dict(prevalence_per_100k=520.0, source="curated",
        note="~1.75M US patients (NEI)."),
    "Retinal vein occlusion (BRVO / CRVO)": dict(prevalence_per_100k=600.0, source="curated",
        note="~2.5M US patients (population-based eye studies, ~0.7-1.6% over age 40)."),
    "Chronic pain": dict(prevalence_per_100k=20000.0, source="curated",
        note="~20% of US adults report chronic pain (CDC); this bucket spans very heterogeneous drugs/indications here, so treat as a rough ceiling, not a specific addressable population."),
    "Dyslipidemia": dict(prevalence_per_100k=53000.0, source="curated",
        note="~53% of US adults have some form of dyslipidemia (CDC); broad population-level figure, not specific to the niche drug indication in this row."),
    "Epilepsy / seizures": dict(prevalence_per_100k=1200.0, source="curated",
        note="~1.2% of US adults have active epilepsy (CDC)."),
    "Non-infectious uveitis": dict(prevalence_per_100k=58.0, source="curated",
        note="~58 per 100,000 (Gritz & Wong population estimate); Orphanet code resolved with no prevalence row."),
    "Exocrine pancreatic insufficiency (EPI)": dict(prevalence_per_100k=250.0, source="curated",
        note="Secondary condition (chronic pancreatitis, cystic fibrosis, post-surgical); rough population-level estimate."),
    "Refractory chronic gout": dict(prevalence_per_100k=120.0, source="curated",
        note="~4% of US adults have gout; refractory/tophaceous subset ~3% of those."),
    "Anemia of CKD (non-dialysis)": dict(prevalence_per_100k=2000.0, source="curated",
        note="~14% of US adults have CKD; anemia affects a meaningful minority as eGFR declines."),
}


def get_epi(disease_canon_name: str):
    """Return epidemiology dict for a canonical disease name, or None if excluded/unknown."""
    return EPIDEMIOLOGY.get(disease_canon_name)
