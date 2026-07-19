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
        note="Orphanet class 1-9/1,000,000 (Europe expert estimate). Caveat: the $0.5B filgrastim "
             "revenue here is only its chronic/congenital-SCN slice — filgrastim's real commercial "
             "footprint is far larger, since G-CSFs (filgrastim, pegfilgrastim) are the leading drug "
             "class in the ~$15.8-16.6B global neutropenia-treatment market (Market.us; Research and "
             "Markets, 2025-2026), which is overwhelmingly chemotherapy-induced neutropenia — an acute, "
             "not chronic, indication that's out of scope for this chronic-use dataset by design."),
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


# ═════════════════════════════════════════════════════════════════════════════
# DISEASE MARKET SIZE — the actual global disease/treatment market size (not
# the known 2024 revenue of the specific drugs in our 35-target CSV). Sourced
# one web search per disease (or per bundled disease group) against
# market-research publishers (Grand View Research, Fortune Business Insights,
# Precedence Research, GlobeNewswire, Market.us, DataBridge, GMInsights,
# Coherent Market Insights, IMARC, etc.) in 2026-07. Nearly every disease
# showed real cross-publisher disagreement (often 2-10x) driven by differing
# scope — drugs-only vs. drugs+diagnostics, "7 major markets" vs. truly
# global, disease-subtype bundling — so `b` below is the midpoint of the
# range actually found, not a precise figure; `lo`/`hi` preserve that range
# and `note` carries the sourcing + scope caveats.
#
# A few buckets have no separately-tracked market at all (e.g. CSID, or the
# inhibitor-specific hemophilia sub-populations); those are flagged
# `researched=False` and fall back to this dataset's own known drug revenue
# as a clearly-labeled proxy, since fabricating a number would be worse.
# ═════════════════════════════════════════════════════════════════════════════
MARKET_SIZE_EXCLUDED = {
    "Cardiovascular risk reduction (secondary prevention)":
        "Not an independent disease market — this is a secondary-prevention label on "
        "patients already sized under Type 2 diabetes / their primary CV diagnosis; "
        "sizing it separately would double-count that market.",
}

DISEASE_MARKET_SIZE = {
    "Achondroplasia": dict(b=1.55, lo=0.6, hi=2.5, year=2025, researched=True,
        note="$0.6-2.5B range (DelveInsight, MarketIntelo, MRFR); wide disagreement, some reports cover only 7 major markets."),
    "Acid sphingomyelinase deficiency (ASMD / NPD-A/B)": dict(b=0.19, lo=0.15, hi=0.23, year=2025, researched=True,
        note="$0.15-0.23B (Coherent Market Insights, Exactitude Consultancy) — narrow orphan-drug market."),
    "Acromegaly": dict(b=2.15, lo=1.3, hi=3.0, year=2025, researched=True,
        note="$1.3-3.0B (Grand View Research, Transparency Market Research, Market.us)."),
    "Adult growth hormone deficiency (AGHD)": dict(b=5.5, lo=4.1, hi=6.9, year=2024, researched=True,
        note="$4.1-6.9B (BioSpace/Spherical Insights, DataM Intelligence) — bundled adult+pediatric GHD market, not split by age."),
    "Alpha-1 antitrypsin deficiency (AATD) with emphysema": dict(b=2.5, lo=1.2, hi=3.8, year=2025, researched=True,
        note="$1.2-3.8B (IMARC, Verified Market Research, Future Market Insights) — overall AATD treatment, not emphysema-specific subset."),
    "Alpha-mannosidosis": dict(b=0.24, lo=0.05, hi=0.43, year=2025, researched=True,
        note="$0.05-0.43B (FutureMarketReport, Mordor Intelligence) — ultra-rare, ~10x spread across sources."),
    "Anemia of CKD (non-dialysis)": dict(b=4.6, lo=2.4, hi=6.85, year=2024, researched=True,
        note="$2.4-6.85B (Fact.MR, GlobalData, MRFR) — figures cover overall renal anemia (dialysis + non-dialysis combined), not split."),
    "Ankylosing spondylitis": dict(b=6.5, lo=6.28, hi=6.7, year=2025, researched=True,
        note="$6.28-6.7B (Grand View Research, MetaTech Insights) — good cross-source agreement."),
    "Arginase 1 deficiency (hyperargininemia)": dict(b=0.65, lo=0.10, hi=1.2, year=2024, researched=True,
        note="$0.10-1.2B (Reportprime + others) — ultra-rare, ~10x spread across sources; low-confidence."),
    "Breast cancer": dict(b=29.65, lo=26.2, hi=33.1, year=2025, researched=True,
        note="$26.2-33.1B (Precedence Research, Coherent Market Insights, Fortune Business Insights); therapeutics-only scope is lower (~$15.8B)."),
    "Cervical dystonia": dict(b=0.44, lo=0.28, hi=0.59, year=2025, researched=True,
        note="$0.28-0.59B (BioSpace, Coherent Market Insights) — sub-billion niche market."),
    "Chronic constipation": dict(b=5.05, lo=3.5, hi=6.6, year=2024, researched=True,
        note="$3.5-6.6B (Data Bridge, MRFR, IMARC) — chronic idiopathic constipation treatment market."),
    "Chronic pain": dict(b=80.0, lo=72.0, hi=88.0, year=2024, researched=True,
        note="$72-88B (Coherent Market Insights, Market.us) — very broad/heterogeneous category bundling many pain etiologies; treat as a rough ceiling."),
    "Congenital sucrase-isomaltase deficiency (CSID)": dict(b=0.1, lo=None, hi=None, year=None, researched=False,
        note="No market-research report found for this ultra-rare disease (searched broadly, including by brand name Sucraid) — "
             "figure shown is this dataset's own known drug revenue (sacrosidase, $0.1B), used as a labeled fallback, not an independent market estimate."),
    "Crohn's disease": dict(b=11.85, lo=10.2, hi=13.5, year=2025, researched=True,
        note="$10.2-13.5B (Future Market Insights, DataBridge); combined Crohn's+UC 'IBD market' runs $22.9-29.6B."),
    "Cushing's syndrome": dict(b=1.25, lo=0.4, hi=2.1, year=2024, researched=True,
        note="$0.4-2.1B (Global Growth Insights, Growth Market Reports) — wide spread by treatment-only vs. treatment+diagnostics scope."),
    "Diabetic macular edema (DME)": dict(b=4.2, lo=4.0, hi=4.4, year=2025, researched=True,
        note="$4.0-4.4B (InsightAce Analytic, Future Market Insights, Mordor Intelligence)."),
    "Diabetic retinopathy": dict(b=9.95, lo=9.6, hi=10.3, year=2025, researched=True,
        note="$9.6-10.3B (Precedence Research, Fortune Business Insights, Research and Markets)."),
    "Dyslipidemia": dict(b=21.0, lo=10.0, hi=32.0, year=2025, researched=True,
        note="$10-32B (Fortune Business Insights, DataM Intelligence) — overlaps substantially with LDL-C/HeFH and general lipid-lowering drug markets."),
    "Endometriosis": dict(b=2.1, lo=1.8, hi=2.4, year=2025, researched=True,
        note="$1.8-2.4B (Grand View Research, GMInsights, Precedence Research)."),
    "Epilepsy / seizures": dict(b=14.95, lo=11.0, hi=18.9, year=2025, researched=True,
        note="$11-18.9B (Grand View Research vs. Research and Markets/Precedence) — antiepileptic drugs market."),
    "Exocrine pancreatic insufficiency (EPI)": dict(b=2.65, lo=2.3, hi=3.0, year=2025, researched=True,
        note="$2.3-3.0B (Fortune Business Insights, Cognitive Market Research) — reasonably consistent across sources."),
    "Fabry disease": dict(b=2.25, lo=2.0, hi=2.5, year=2025, researched=True,
        note="$2.0-2.5B (IMARC, Precedence Research, GM Insights)."),
    "Generalized myasthenia gravis": dict(b=1.9, lo=1.6, hi=2.2, year=2025, researched=True,
        note="$1.6-2.2B (Persistence Market Research, DelveInsight) — one 7-major-market-specific gMG estimate runs much higher ($5.9B); treated as an outlier here."),
    "Glabellar (frown) lines": dict(b=9.9, lo=7.85, hi=11.94, year=2025, researched=True,
        note="Cosmetic indication, not a disease: figure is the total global botulinum toxin market ($7.85-11.94B, Fortune Business Insights/Grand View Research), spanning cosmetic + therapeutic use, not glabellar lines alone."),
    "HIV-associated lipodystrophy (abdominal fat excess)": dict(b=1.5, lo=0.18, hi=3.2, year=2024, researched=True,
        note="$0.18-3.2B (Coherent Market Insights, InsightAce) — niche market, sources disagree by ~10x; central estimate ~$1.5B."),
    "Hemophilia A (prophylaxis)": dict(b=11.2, lo=10.4, hi=12.0, year=2024, researched=True,
        note="Derived: total hemophilia A+B market is $14.1-16.2B (Grand View Research, Fortune Business Insights); "
             "Hemophilia A holds ~74% share per GVR, implying ~$10.4-12B for A specifically."),
    "Hemophilia A with inhibitors (prophylaxis)": dict(b=0.5, lo=None, hi=None, year=2024, researched=True,
        note="No standalone global $B figure found (Towards Healthcare describes growth to 'hundreds of millions' by 2032); "
             "bundled within the overall Hemophilia A market above. Inhibitors affect ~20-30% of severe Hemophilia A patients."),
    "Hemophilia A/B with inhibitors": dict(b=0.5, lo=None, hi=None, year=2024, researched=True,
        note="Same as Hemophilia A with inhibitors — no publisher tracks an inhibitor-specific market distinctly from overall hemophilia figures."),
    "Hemophilia B (prophylaxis)": dict(b=4.0, lo=3.7, hi=4.2, year=2024, researched=True,
        note="Derived: residual ~26% share of the $14.1-16.2B total hemophilia A+B market not attributed to Hemophilia A above "
             "(direct Hemophilia B sources were inconsistent — $10B for '7 major markets' vs. $24.7B as a 2035 forecast, neither a reliable current global figure)."),
    "Hidradenitis suppurativa": dict(b=1.15, lo=0.8, hi=1.5, year=2024, researched=True,
        note="$0.8-1.5B (SkyQuest, IMARC); one outlier source reports $3.77B using a broader definition, excluded here."),
    "Irritable bowel syndrome": dict(b=3.63, lo=3.48, hi=3.78, year=2025, researched=True,
        note="$3.48-3.78B (Grand View Research, Straits Research, Market.us) — fairly tight cross-source cluster."),
    "Juvenile idiopathic arthritis": dict(b=3.15, lo=1.3, hi=5.0, year=2025, researched=True,
        note="$1.3-5B — wide divergence between systemic-JIA-only (~$1.3-1.6B) and all-subtype JIA (~$3-5B) framings, often conflated across publishers."),
    "LDL-C reduction (HeFH / ASCVD)": dict(b=11.45, lo=5.6, hi=17.3, year=2025, researched=True,
        note="Heterozygous familial hypercholesterolemia (HeFH): $5.6B (narrower 'drug market') to $17.3B (broader 'management market'), OpenPR/MRFR."),
    "Late-onset Pompe disease (LOPD)": dict(b=1.65, lo=1.1, hi=2.2, year=2024, researched=True,
        note="$1.1-2.2B (Research and Markets, GII Research) — covers all Pompe disease, not an LOPD-specific subset."),
    "MPS II (Hunter syndrome)": dict(b=1.15, lo=1.0, hi=1.3, year=2024, researched=True,
        note="$1.0-1.3B (Fortune Business Insights, Grand View Research) — fairly consistent cluster."),
    "Menopausal / hormone therapy": dict(b=18.25, lo=17.8, hi=18.7, year=2025, researched=True,
        note="$17.8-18.7B (Grand View Research, menopause-specific market); the broader 'HRT market' incl. non-menopausal use runs $23.8-25.2B."),
    "Neovascular (wet) AMD": dict(b=10.05, lo=9.5, hi=10.6, year=2025, researched=True,
        note="$9.5-10.6B (BIS Research, Research and Markets); broader 'macular degeneration' market incl. dry AMD runs $16-17B."),
    "Non-infectious uveitis": dict(b=2.35, lo=2.0, hi=2.7, year=2025, researched=True,
        note="$2.0-2.7B (Data Bridge, Straits Research, Precision Business Insights)."),
    "Obesity / weight management": dict(b=17.5, lo=7.0, hi=28.0, year=2025, researched=True,
        note="$7-28B (Fortune Business Insights, Roots Analysis, Mordor Intelligence) — very wide spread; note actual GLP-1 company "
             "sales (Wegovy/Zepbound) already exceed the low end, suggesting some reports undercount current sales."),
    "Osteoporosis": dict(b=15.25, lo=14.5, hi=16.0, year=2025, researched=True,
        note="$14.5-16B (Grand View Research, GMInsights, Coherent Market Insights) — tight cross-source agreement."),
    "Pediatric growth hormone deficiency": dict(b=5.5, lo=4.1, hi=6.9, year=2024, researched=True,
        note="Same bundled adult+pediatric GHD market as Adult growth hormone deficiency above — not separately tracked by age."),
    "Plaque psoriasis": dict(b=33.45, lo=31.9, hi=35.0, year=2025, researched=True,
        note="No clean standalone global plaque-specific figure found (one 7-major-market estimate: $12.7B); figure shown is the "
             "broader all-subtype psoriasis treatment market (Precedence Research, Grand View Research), of which plaque is the majority (~80-90% of cases)."),
    "Polycythemia vera (PV)": dict(b=4.3, lo=1.5, hi=7.1, year=2024, researched=True,
        note="$1.5-7.1B core estimates (IMARC, MRFR) — extremely wide variance across publishers (up to $19.4B in outlier reports), likely reflecting PV-drug-only vs. broader 'polycythemia' scope."),
    "Prostate cancer": dict(b=13.6, lo=12.9, hi=14.25, year=2025, researched=True,
        note="$12.9-14.25B (Precedence Research, Data M Intelligence)."),
    "Psoriatic arthritis": dict(b=12.6, lo=10.5, hi=14.7, year=2024, researched=True,
        note="$10.5-14.7B (Precedence Research, IMARC, DataBridge)."),
    "Pulmonary arterial hypertension (PAH) – WHO Group I": dict(b=8.05, lo=6.9, hi=9.2, year=2025, researched=True,
        note="$6.9-9.2B (Precedence Research, Research Nester, Market.us); most sources cluster $8-8.5B."),
    "Refractory chronic gout": dict(b=3.05, lo=3.0, hi=6.3, year=2025, researched=True,
        note="Refractory/tophaceous gout is not separately tracked by market researchers — figure is the overall gout therapeutics market "
             "(Grand View Research, Data Bridge), which most sources put at $3.0-3.1B (one outlier reports $6.3B)."),
    "Retinal vein occlusion (BRVO / CRVO)": dict(b=2.6, lo=2.4, hi=2.8, year=2025, researched=True,
        note="$2.4-2.8B (Fact.MR, Coherent Market Insights, SNS Insider)."),
    "Rheumatoid arthritis": dict(b=30.2, lo=19.6, hi=40.8, year=2026, researched=True,
        note="$19.6-40.8B (Statifacts, Mordor Intelligence, Research Nester) — nearly 2x spread reflecting 'RA market' vs. 'RA drugs market' scope differences; midpoint sources cluster $28-36B."),
    "Severe chronic neutropenia (SCN)": dict(b=1.0, lo=0.5, hi=1.5, year=2025, researched=True,
        note="$0.5-1.5B — the congenital/cyclic-neutropenia-specific slice (DataBridge Market Research), not the much larger "
             "$15.8-16.6B overall neutropenia-treatment market, which is overwhelmingly acute chemotherapy-induced neutropenia support."),
    "Short bowel syndrome": dict(b=1.5, lo=1.3, hi=1.7, year=2025, researched=True,
        note="$1.3-1.7B (Persistence Market Research, DataM Intelligence, Fortune Business Insights)."),
    "Systemic lupus erythematosus (SLE)": dict(b=5.1, lo=2.6, hi=7.6, year=2025, researched=True,
        note="$2.6-7.6B (Mordor Intelligence, MRFR) — nearly 3x spread reflecting narrower 'SLE drug market' vs. broader 'SLE treatment market' definitions."),
    "Type 1 diabetes mellitus": dict(b=16.1, lo=13.5, hi=18.7, year=2025, researched=True,
        note="$13.5-18.7B (Coherent Market Insights, The Business Research Company)."),
    "Type 2 diabetes": dict(b=60.5, lo=37.0, hi=84.0, year=2025, researched=True,
        note="$37-84B (Grand View Research, Precedence Research, Business Research Insights) — wide range reflects drugs-only vs. drugs+devices+diagnostics scope."),
    "Ulcerative colitis": dict(b=9.28, lo=7.96, hi=10.6, year=2024, researched=True,
        note="$7.96-10.6B (GMInsights, Precedence Research via Towards Healthcare); combined Crohn's+UC 'IBD market' runs $22.9-29.6B."),
}


def get_market_size(disease_canon_name: str):
    """Return the disease-level market-size dict for a canonical disease name,
    or None if excluded (not an independent market) or simply not in the dataset."""
    return DISEASE_MARKET_SIZE.get(disease_canon_name)
