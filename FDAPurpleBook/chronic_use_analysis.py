"""
Chronic Use Analysis for 208 FDA-approved Biologics (Purple Book)
Classifies each drug by treatment duration category based on indication and drug class.
"""

import pandas as pd

# -------------------------------------------------------------------
# CLASSIFICATION DATABASE
# Each entry: drug name (lower) -> (category, subcategory, indication, rationale)
#
# CATEGORIES:
#   CHRONIC   - indefinite continuous use (disease is permanent or recurrent without treatment)
#   LONG-TERM - months to years (cancer until progression, multi-year maintenance)
#   PERIODIC  - intermittent long-term (every few months; recurring seasonal)
#   SHORT     - limited course (days to weeks), acute infection, single-procedure
#   ONE-TIME  - gene therapy, CAR-T, transplant, primary vaccine series
# -------------------------------------------------------------------

CLASSIFICATIONS = {
    # ── AUTOIMMUNE / INFLAMMATORY ──────────────────────────────────
    "adalimumab": ("CHRONIC", "Autoimmune biologic", "RA / psoriasis / IBD / AS / uveitis",
        "TNF inhibitor for multiple chronic autoimmune diseases; discontinuation causes relapse"),
    "etanercept": ("CHRONIC", "Autoimmune biologic", "RA / psoriasis / AS",
        "TNF inhibitor; disease relapses off therapy"),
    "infliximab": ("CHRONIC", "Autoimmune biologic", "IBD / RA / psoriasis / AS",
        "TNF inhibitor; maintenance infusions every 8 weeks indefinitely"),
    "secukinumab": ("CHRONIC", "Autoimmune biologic", "Psoriasis / PsA / AS / nr-axSpA",
        "IL-17A inhibitor; disease recurs upon discontinuation"),
    "ustekinumab": ("CHRONIC", "Autoimmune biologic", "Psoriasis / PsA / Crohn's / UC",
        "IL-12/23 inhibitor; used as long-term maintenance"),
    "ixekizumab": ("CHRONIC", "Autoimmune biologic", "Psoriasis / PsA / AS",
        "IL-17A inhibitor; long-term maintenance dosing"),
    "guselkumab": ("CHRONIC", "Autoimmune biologic", "Psoriasis / PsA",
        "IL-23 inhibitor; indefinite maintenance"),
    "risankizumab": ("CHRONIC", "Autoimmune biologic", "Psoriasis / PsA / Crohn's / UC",
        "IL-23 inhibitor; maintenance every 12 weeks"),
    "bimekizumab": ("CHRONIC", "Autoimmune biologic", "Psoriasis / PsA / AS / nr-axSpA",
        "IL-17A/F dual inhibitor; long-term use"),
    "mirikizumab": ("CHRONIC", "Autoimmune biologic", "Ulcerative colitis / Crohn's disease",
        "IL-23 inhibitor; IBD requires indefinite maintenance"),
    "vedolizumab": ("CHRONIC", "Autoimmune biologic", "UC / Crohn's disease",
        "α4β7 integrin blocker; gut-selective long-term IBD maintenance"),
    "tocilizumab": ("CHRONIC", "Autoimmune biologic", "RA / GCA / PJIA / SJIA",
        "IL-6R inhibitor; disease relapses without maintenance"),
    "dupilumab": ("CHRONIC", "Autoimmune biologic", "Atopic dermatitis / asthma / CRSwNP / EoE / PN",
        "IL-4Rα inhibitor; type-2 inflammation requires indefinite control"),
    "tralokinumab": ("CHRONIC", "Autoimmune biologic", "Atopic dermatitis",
        "IL-13 inhibitor; chronic skin disease needs continuous treatment"),
    "lebrikizumab": ("CHRONIC", "Autoimmune biologic", "Atopic dermatitis",
        "IL-13 inhibitor; long-term maintenance required"),
    "nemolizumab-ilto": ("CHRONIC", "Autoimmune biologic", "Atopic dermatitis / prurigo nodularis",
        "IL-31Rα inhibitor; chronic pruritic conditions"),
    "benralizumab": ("CHRONIC", "Autoimmune biologic", "Severe eosinophilic asthma",
        "IL-5Rα blocker; maintenance every 8 weeks indefinitely"),
    "mepolizumab": ("CHRONIC", "Autoimmune biologic", "Severe eosinophilic asthma / EGPA / HES",
        "IL-5 inhibitor; asthma/EGPA maintenance"),
    "tezepelumab": ("CHRONIC", "Autoimmune biologic", "Severe asthma",
        "TSLP inhibitor; add-on maintenance therapy"),
    "omalizumab": ("CHRONIC", "Autoimmune biologic", "Allergic asthma / chronic urticaria / food allergy",
        "Anti-IgE; chronic conditions require ongoing dosing"),
    "depemokimab": ("CHRONIC", "Autoimmune biologic", "Severe eosinophilic asthma / EGPA",
        "Long-acting IL-5 inhibitor; every 6-month maintenance"),
    "anifrolumab": ("CHRONIC", "Autoimmune biologic", "Systemic lupus erythematosus",
        "IFNAR1 inhibitor; SLE is lifelong; monthly maintenance"),
    "spesolimab": ("CHRONIC", "Autoimmune biologic", "Generalized pustular psoriasis (GPP)",
        "IL-36R inhibitor; used for flare treatment and maintenance"),
    "axatilimab-csfr": ("CHRONIC", "Autoimmune biologic", "Chronic graft-versus-host disease",
        "CSF-1R inhibitor; cGVHD is a prolonged condition"),
    "satralizumab-mwge": ("CHRONIC", "Autoimmune biologic", "NMOSD (AQP4-IgG positive)",
        "IL-6R inhibitor; NMOSD relapses require indefinite prevention"),
    "inebilizumab-cdon": ("CHRONIC", "Autoimmune biologic", "NMOSD",
        "CD19 B-cell depletion; NMOSD requires long-term relapse prevention"),
    "ublituximab-xiiy": ("CHRONIC", "Autoimmune biologic", "Relapsing MS",
        "Anti-CD20; MS requires indefinite disease modification"),
    "natalizumab-sztn": ("CHRONIC", "Autoimmune biologic", "Relapsing MS / Crohn's disease",
        "α4-integrin blocker; long-term disease modification for MS/CD"),
    "ocrelizumab and hyaluronidase-ocsq": ("CHRONIC", "Autoimmune biologic", "MS (relapsing and PPMS)",
        "Anti-CD20; MS disease modification is lifelong"),
    "ofatumumab": ("CHRONIC", "Autoimmune biologic", "Relapsing MS",
        "Anti-CD20; self-administered monthly for long-term MS control"),
    "efgartigimod alfa-fcab": ("CHRONIC", "Autoimmune biologic", "Generalized myasthenia gravis",
        "FcRn blocker reducing IgG; cyclic infusions every 4 weeks indefinitely"),
    "efgartigimod alfa and hyaluronidase": ("CHRONIC", "Autoimmune biologic", "Generalized myasthenia gravis",
        "SC formulation of FcRn blocker; long-term cyclic treatment"),
    "rozanolixizumab": ("CHRONIC", "Autoimmune biologic", "Generalized myasthenia gravis",
        "FcRn inhibitor; recurring cycles for chronic MG control"),
    "nipocalimab": ("CHRONIC", "Autoimmune biologic", "Generalized myasthenia gravis / HDFN",
        "FcRn blocker; ongoing MG maintenance"),
    "sibeprenlimab-szsi": ("CHRONIC", "Autoimmune biologic", "IgA nephropathy",
        "APRIL inhibitor; progressive kidney disease requires indefinite treatment"),
    "narsoplimab-wuug": ("LONG-TERM", "Complement inhibitor", "HSCT-TMA",
        "MASP-2 inhibitor; TMA treatment is finite but may extend months"),

    # ── COMPLEMENT / RARE HEMATOLOGY ──────────────────────────────
    "eculizumab": ("CHRONIC", "Complement inhibitor", "PNH / aHUS / gMG / NMOSD",
        "C5 inhibitor; PNH/aHUS require lifelong complement blockade"),
    "ravulizumab": ("CHRONIC", "Complement inhibitor", "PNH / aHUS / gMG / NMOSD / HSCT-TMA",
        "Long-acting C5 inhibitor; same lifelong need as eculizumab"),
    "crovalimab-akkz": ("CHRONIC", "Complement inhibitor", "PNH",
        "C5 inhibitor; PNH is a lifelong condition"),
    "sutimlimab-jome": ("CHRONIC", "Complement inhibitor", "Cold agglutinin disease",
        "C1s inhibitor; CAD requires ongoing hemolysis prevention"),
    "pozelimab-bbfg": ("CHRONIC", "Complement inhibitor", "CHAPLE disease (CD55 deficiency)",
        "C5 inhibitor; ultra-rare lifelong complement-mediated disease"),

    # ── HEMOPHILIA / COAGULATION ───────────────────────────────────
    "emicizumab": ("CHRONIC", "Hemophilia prophylaxis", "Hemophilia A (with/without inhibitors)",
        "Bispecific factor Xa/IXa mimic; lifelong weekly/biweekly prophylaxis"),
    "concizumab": ("CHRONIC", "Hemophilia prophylaxis", "Hemophilia A/B with inhibitors",
        "TFPI inhibitor; subcutaneous prophylaxis, indefinite"),
    "marstacimab": ("CHRONIC", "Hemophilia prophylaxis", "Hemophilia A/B",
        "TFPI inhibitor; long-term prophylaxis"),
    "antihemophilic factor (recombinant), rAHF": ("CHRONIC", "Coagulation factor", "Hemophilia A",
        "Factor VIII replacement; lifelong prophylaxis or on-demand"),
    "antihemophilic factor (recombinant), fc": ("CHRONIC", "Coagulation factor", "Hemophilia A",
        "Extended half-life Factor VIII; lifelong prophylaxis"),
    "antihemophilic factor (recombinant), pegylated-aucl": ("CHRONIC", "Coagulation factor", "Hemophilia A",
        "PEGylated Factor VIII; long-term prophylaxis"),
    "coagulation factor ix (recombinant), glycopegylated": ("CHRONIC", "Coagulation factor", "Hemophilia B",
        "Long-acting Factor IX; weekly prophylaxis, lifelong"),
    "lanadelumab": ("CHRONIC", "HAE prophylaxis", "Hereditary angioedema (HAE)",
        "Kallikrein inhibitor; every 2-4 weeks indefinitely to prevent HAE attacks"),
    "garadacimab": ("CHRONIC", "HAE prophylaxis", "Hereditary angioedema (HAE)",
        "Factor XIIa inhibitor; monthly SC injection for long-term HAE prevention"),

    # ── OPHTHALMOLOGY ─────────────────────────────────────────────
    "ranibizumab": ("CHRONIC", "Anti-VEGF", "AMD / DME / RVO / DR",
        "VEGF inhibitor; retinal neovascular diseases require monthly-quarterly injections indefinitely"),
    "brolucizumab-dbll": ("CHRONIC", "Anti-VEGF", "AMD / DME",
        "Anti-VEGF; long-term maintenance every 8-12 weeks"),
    "aflibercept": ("CHRONIC", "Anti-VEGF", "AMD / DME / RVO",
        "VEGF trap; chronic intravitreal maintenance"),
    "faricimab": ("CHRONIC", "Anti-VEGF", "AMD / DME",
        "Ang-2/VEGF bispecific; extended up to every 16 weeks, indefinitely"),

    # ── ENDOCRINE / METABOLIC ─────────────────────────────────────
    "insulin lispro": ("CHRONIC", "Insulin", "Diabetes mellitus (T1D/T2D)",
        "Insulin replacement; lifelong daily dosing"),
    "insulin glargine": ("CHRONIC", "Insulin", "Diabetes mellitus",
        "Long-acting insulin; lifelong daily basal dosing"),
    "insulin aspart": ("CHRONIC", "Insulin", "Diabetes mellitus",
        "Rapid-acting insulin; lifelong mealtime dosing"),
    "insulin icodec": ("CHRONIC", "Insulin", "Type 2 diabetes",
        "Once-weekly ultra-long-acting insulin; indefinite use"),
    "dulaglutide": ("CHRONIC", "GLP-1 receptor agonist", "Type 2 diabetes",
        "Weekly GLP-1 agonist; T2DM is chronic, indefinite maintenance"),
    "somapacitan": ("CHRONIC", "Growth hormone analog", "Adult GHD / pediatric GHD",
        "Weekly GH analog; adult GHD may require lifelong replacement"),
    "lonapegsomatropin": ("CHRONIC", "Growth hormone analog", "Pediatric GHD",
        "Weekly GH; used until adequate adult height achieved (years)"),
    "somatrogon": ("CHRONIC", "Growth hormone analog", "Pediatric GHD",
        "Weekly GH; used through childhood/adolescence"),
    "tesamorelin": ("CHRONIC", "GHRH analog", "HIV-associated lipodystrophy",
        "Daily SC injection; condition recurs on discontinuation"),
    "epoetin alfa": ("CHRONIC", "Erythropoiesis-stimulating agent", "Anemia (CKD / oncology)",
        "EPO replacement; CKD anemia is permanent; ongoing dosing"),
    "pegfilgrastim": ("PERIODIC", "G-CSF", "Chemotherapy-induced neutropenia",
        "Each chemo cycle gets one dose; long-term only while on chemo"),
    "filgrastim": ("PERIODIC", "G-CSF", "Chemotherapy-induced neutropenia / SCN",
        "Used per chemo cycle or daily in SCN (SCN = lifelong)"),
    "eflapegrastim-xnst": ("PERIODIC", "G-CSF", "Chemotherapy-induced neutropenia",
        "Once-per-cycle G-CSF; duration tied to chemotherapy"),
    "efbemalenograstim alfa-vuxw": ("PERIODIC", "G-CSF", "Chemotherapy-induced neutropenia",
        "Once-per-cycle G-CSF"),
    "evinacumab": ("CHRONIC", "Lipid-lowering biologic", "Homozygous familial hypercholesterolemia (HoFH)",
        "ANGPTL3 inhibitor; HoFH is lifelong, monthly infusions"),
    "lerodalcibep-liga": ("CHRONIC", "Lipid-lowering biologic", "Hypercholesterolemia / HeFH",
        "PCSK9 inhibitor fusion protein; lifelong monthly dosing"),
    "denosumab": ("CHRONIC", "RANK-L inhibitor", "Osteoporosis / bone metastases / GCTB",
        "Osteoporosis: 6-monthly injections, long-term; bone mets: continuous"),
    "pegloticase": ("LONG-TERM", "Uricase", "Refractory chronic gout",
        "Recombinant uricase; infused every 2 weeks for months; some patients long-term"),
    "pegzilarginase": ("CHRONIC", "Enzyme replacement", "Arginase 1 deficiency (hyperargininemia)",
        "Weekly IV arginase; lifelong urea cycle disorder management"),
    "tividenofusp alfa-eknm": ("CHRONIC", "Enzyme replacement / ETV fusion", "MPS II (Hunter syndrome)",
        "IDS-ETV fusion protein; lifelong IV ERT for lysosomal storage disease"),

    # ── ENZYME REPLACEMENT THERAPY ────────────────────────────────
    "sacrosidase": ("CHRONIC", "Enzyme replacement", "Congenital sucrase-isomaltase deficiency",
        "Oral sucrase replacement; lifelong with every meal"),
    "pancrelipase": ("CHRONIC", "Enzyme replacement", "Exocrine pancreatic insufficiency",
        "Pancreatic enzyme replacement; lifelong with every meal"),
    "pegunigalsidase alfa": ("CHRONIC", "Enzyme replacement", "Fabry disease",
        "PEGylated α-galactosidase A; biweekly IV, lifelong"),
    "velmanase alfa-tycv": ("CHRONIC", "Enzyme replacement", "Alpha-mannosidosis",
        "α-mannosidase replacement; lifelong biweekly IV infusions"),
    "olipudase alfa": ("CHRONIC", "Enzyme replacement", "Acid sphingomyelinase deficiency (ASMD)",
        "ASM replacement; biweekly IV, lifelong"),
    "avalglucosidase alfa-ngpt": ("CHRONIC", "Enzyme replacement", "Pompe disease (LOPD)",
        "Acid α-glucosidase; biweekly IV, lifelong"),
    "cipaglucosidase alfa-atga": ("CHRONIC", "Enzyme replacement", "Pompe disease",
        "Next-gen GAA + miglustat; biweekly IV, lifelong"),
    "alpha": ("CHRONIC", "Protein replacement", "Alpha-1 antitrypsin deficiency (AATD)",
        "Weekly IV AAT augmentation therapy; lifelong lung protection"),

    # ── NEUROLOGY / NEURODEGENERATION ─────────────────────────────
    "lecanemab": ("CHRONIC", "Anti-amyloid antibody", "Early Alzheimer's disease",
        "Aβ protofibril clearance; disease is progressive, ongoing infusions"),
    "aducanumab": ("CHRONIC", "Anti-amyloid antibody", "Early Alzheimer's disease",
        "Aβ plaque clearance; monthly infusions indefinitely"),
    "donanemab-azbt": ("LONG-TERM", "Anti-amyloid antibody", "Early symptomatic Alzheimer's",
        "Dosing until plaque clearance (~12-18 months); may discontinue after target reached"),
    "eptinezumab-jjmr": ("CHRONIC", "Anti-CGRP antibody", "Episodic / chronic migraine prevention",
        "Quarterly IV; migraine is recurrent; long-term preventive therapy"),
    "eladocagene exuparvovec-tneq": ("ONE-TIME", "Gene therapy", "AADC deficiency",
        "AAV2-AADC striatal injection; single surgical procedure"),
    "onasemnogene abeparvovec-brve": ("ONE-TIME", "Gene therapy", "Spinal muscular atrophy (SMA)",
        "AAV9-SMN1 IV infusion; single lifetime dose"),
    "delandistrogene moxeparvovec-rokl": ("ONE-TIME", "Gene therapy", "Duchenne muscular dystrophy",
        "AAVrh74-micro-dystrophin; single IV infusion"),

    # ── PULMONARY ARTERIAL HYPERTENSION ───────────────────────────
    "sotatercept": ("CHRONIC", "ActRIIA fusion protein", "Pulmonary arterial hypertension (PAH)",
        "TGF-β trap; PAH is progressive and requires indefinite treatment"),

    # ── RARE METABOLIC / ORPHAN ───────────────────────────────────
    "ropeginterferon alfa-2b-njft": ("CHRONIC", "Pegylated interferon", "Polycythemia vera (PV)",
        "Every 2-week SC injection; PV is chronic, requires indefinite cytoreduction"),

    # ── IMMUNOGLOBULINS / BLOOD PRODUCTS ──────────────────────────
    "immune globulin intravenous, human": ("CHRONIC", "Immunoglobulin replacement", "Primary immunodeficiency / ITP / CIDP",
        "Regular infusions (every 3-4 weeks for PIDD); lifelong in immunodeficiency"),
    "immune globulin subcutaneous (human), 20% liquid": ("CHRONIC", "Immunoglobulin replacement", "Primary immunodeficiency / CIDP",
        "Weekly SC infusions; lifelong in primary immunodeficiency"),
    "immune globulin intravenous, human-1": ("CHRONIC", "Immunoglobulin replacement", "Primary immunodeficiency",
        "Regular IVIg; lifelong"),
    "albumin (human)": ("SHORT", "Plasma protein", "Hypoalbuminemia / cirrhosis / shock",
        "Acute or supportive use; typically not taken indefinitely at home"),

    # ── BOTULINUM TOXINS ──────────────────────────────────────────
    "daxibotulinumtoxina": ("PERIODIC", "Botulinum toxin", "Cervical dystonia",
        "IM injection every ~24 weeks; not daily but indefinitely repeated for chronic condition"),
    "letibotulinumtoxina": ("PERIODIC", "Botulinum toxin", "Cervical dystonia / blepharospasm",
        "Repeated injections every 3-6 months for chronic neurological condition"),

    # ── ALLERGEN IMMUNOTHERAPY ────────────────────────────────────
    "peanut (arachis hypogaea) allergen powder": ("LONG-TERM", "Allergen immunotherapy", "Peanut allergy desensitization",
        "Daily oral immunotherapy; 3+ years of build-up and maintenance"),
    "short ragweed pollen allergen extract": ("LONG-TERM", "Allergen immunotherapy", "Allergic rhinitis (ragweed)",
        "Subcutaneous immunotherapy; 3-5 year course"),

    # ── OPHTHALMOLOGY – ANTI-VEGF (duplicate resolved) ────────────
    "bevacizumab": ("LONG-TERM", "Anti-VEGF / cancer", "Colorectal / lung / cervical / glioblastoma cancer + retinal",
        "Cancer use: until progression. Ophthalmic compounded use: chronic"),

    # ── ONCOLOGY – MAINTENANCE / LONG-TERM UNTIL PROGRESSION ──────
    "rituximab": ("LONG-TERM", "Anti-CD20", "NHL / CLL / RA / pemphigus / MS",
        "Lymphoma maintenance: 2 years; RA/MS: indefinite; CLL: until progression"),
    "trastuzumab": ("LONG-TERM", "HER2 inhibitor", "HER2+ breast / gastric cancer",
        "Adjuvant: 1 year. Metastatic: until progression (months to years)"),
    "pertuzumab, trastuzumab, and hyaluronidase": ("LONG-TERM", "HER2 inhibitor combination", "HER2+ breast cancer",
        "Adjuvant: 1 year; metastatic maintenance until progression"),
    "pertuzumab-dpzb": ("LONG-TERM", "HER2 inhibitor (biosimilar)", "HER2+ breast cancer",
        "Biosimilar pertuzumab; same long-term maintenance use"),
    "margetuximab-cmkb": ("LONG-TERM", "HER2 inhibitor", "HER2+ metastatic breast cancer",
        "Until disease progression in metastatic setting"),
    "nivolumab and relatlimab": ("LONG-TERM", "Checkpoint inhibitor", "Unresectable / metastatic melanoma",
        "PD-1 + LAG-3; until progression or up to 2 years per label"),
    "nivolumab and hyaluronidase": ("LONG-TERM", "Checkpoint inhibitor", "Multiple cancers",
        "SC formulation; used until progression"),
    "dostarlimab-gxly": ("LONG-TERM", "Checkpoint inhibitor (PD-1)", "Endometrial / dMMR solid tumors",
        "Until progression; maintenance phase every 6 weeks indefinitely"),
    "retifanlimab-dlwr": ("LONG-TERM", "Checkpoint inhibitor (PD-1)", "Merkel cell / anal canal carcinoma",
        "Until progression or unacceptable toxicity"),
    "toripalimab-tpzi": ("LONG-TERM", "Checkpoint inhibitor (PD-1)", "NPC / mucosal melanoma",
        "Concurrent then maintenance until progression"),
    "cosibelimab-ipdl": ("LONG-TERM", "Checkpoint inhibitor (PD-L1)", "Cutaneous SCC",
        "Until progression; flat dosing every 3 weeks"),
    "penpulimab-kcqx": ("LONG-TERM", "Checkpoint inhibitor (PD-1)", "NPC / cancer",
        "Until progression or toxicity"),
    "tislelizumab-jsgr": ("LONG-TERM", "Checkpoint inhibitor (PD-1)", "Esophageal SCC / gastric cancer",
        "Maintenance until progression"),
    "atezolizumab and hyaluronidase-tqjs": ("LONG-TERM", "Checkpoint inhibitor (PD-L1)", "NSCLC / TNBC / HCC / UC",
        "SC formulation; until progression"),
    "pembrolizumab and berahyaluronidase alfa": ("LONG-TERM", "Checkpoint inhibitor (PD-1)", "Multiple cancers",
        "SC pembrolizumab; until progression (approx. 2 years in many approvals)"),
    "tremelimumab": ("LONG-TERM", "Checkpoint inhibitor (CTLA-4)", "Hepatocellular carcinoma",
        "Single priming dose + durvalumab maintenance; primarily short priming phase"),
    "amivantamab-vmjw": ("LONG-TERM", "EGFR/MET bispecific", "NSCLC (EGFR exon 20)",
        "Biweekly IV until progression"),
    "amivantamab and hyaluronidase": ("LONG-TERM", "EGFR/MET bispecific (SC)", "NSCLC (EGFR exon 20)",
        "SC formulation; until progression"),
    "zanidatamab-hrii": ("LONG-TERM", "HER2 bispecific", "Biliary tract / gastric cancer",
        "HER2-targeting until progression"),
    "polatuzumab vedotin-piiq": ("LONG-TERM", "ADC (anti-CD79b)", "DLBCL / follicular lymphoma",
        "6 cycles + maintenance; some patients may receive extended dosing"),
    "tafasitamab-cxix": ("LONG-TERM", "Anti-CD19 + lenalidomide", "Relapsed/refractory DLBCL",
        "Induction + maintenance dosing until progression"),
    "mirvetuximab soravtansine-gynx": ("LONG-TERM", "ADC (anti-FRα)", "FRα+ ovarian cancer",
        "Weekly until progression in relapsed setting"),
    "tisotumab vedotin-tftv": ("LONG-TERM", "ADC (anti-TF)", "Recurrent cervical cancer",
        "Every 3 weeks until progression"),
    "datopotamab deruxtecan": ("LONG-TERM", "ADC (TROP2-DXd)", "NSCLC / HR+ breast cancer",
        "Q3W until progression; newer approvals for chronic maintenance use"),
    "telisotuzumab vedotin": ("LONG-TERM", "ADC (anti-c-MET)", "NSCLC (c-MET overexpression)",
        "Biweekly until disease progression"),
    "loncastuximab tesirine-lpyl": ("LONG-TERM", "ADC (anti-CD19)", "Relapsed/refractory DLBCL",
        "Until progression or unacceptable toxicity"),
    "belantamab mafodotin": ("LONG-TERM", "ADC (anti-BCMA)", "Relapsed/refractory myeloma",
        "Every 3 weeks until progression; reversible corneal toxicity limits duration"),
    "naxitamab-gqgk": ("LONG-TERM", "Anti-GD2 antibody", "Relapsed/refractory neuroblastoma",
        "5-day cycles every 4 weeks; ongoing until progression"),
    "mosunetuzumab": ("LONG-TERM", "CD20×CD3 bispecific", "Follicular lymphoma",
        "Fixed 8-cycle treatment; time-limited course"),
    "teclistamab": ("LONG-TERM", "BCMA×CD3 bispecific", "Relapsed/refractory myeloma",
        "Weekly then biweekly; until progression — typically months"),
    "talquetamab": ("LONG-TERM", "GPRC5D×CD3 bispecific", "Relapsed/refractory myeloma",
        "Weekly or biweekly; until progression"),
    "elranatamab": ("LONG-TERM", "BCMA×CD3 bispecific", "Relapsed/refractory myeloma",
        "Weekly then biweekly; until progression"),
    "tarlatamab": ("LONG-TERM", "DLL3×CD3 bispecific", "Extensive-stage SCLC",
        "Biweekly IV; until progression"),
    "glofitamab": ("LONG-TERM", "CD20×CD3 bispecific", "Relapsed/refractory DLBCL",
        "Fixed 12-cycle course; time-limited treatment"),
    "epcoritamab": ("LONG-TERM", "CD20×CD3 bispecific", "DLBCL / follicular lymphoma",
        "SC; weekly then biweekly then monthly; until progression"),
    "linvoseltamab": ("LONG-TERM", "BCMA×CD3 bispecific", "Relapsed/refractory myeloma",
        "Weekly then biweekly; until progression"),
    "zenocutuzumab-zbco": ("LONG-TERM", "NRG1 fusion bispecific (HER2×HER3)", "NRG1+ cancer",
        "Biweekly until progression"),
    "tebentafusp-tebn": ("LONG-TERM", "TCR bispecific (gp100)", "Uveal melanoma",
        "Weekly until progression; median duration ~months"),
    "zolbetuximab": ("LONG-TERM", "Anti-claudin 18.2", "Gastric / GEJ adenocarcinoma",
        "Q3W + Q6W with chemo; until progression"),
    "denileukin diftitox-cxdl": ("LONG-TERM", "IL-2–diphtheria toxin fusion", "CTCL",
        "Cycles of 5 days every 3 weeks; until progression"),
    "nogapendekin alfa inbakicept-pmln": ("LONG-TERM", "IL-15 superagonist fusion", "BCG-unresponsive NMIBC",
        "Adjuvant intravesical instillation; quarterly maintenance up to 3 years"),
    "nadofaragene firadenovec-vncg": ("LONG-TERM", "Gene therapy (intravesical)", "BCG-unresponsive NMIBC",
        "Quarterly intravesical instillation as long as response maintained"),
    "ropeginterferon alfa-2b-njft-dup": ("CHRONIC", "Pegylated interferon", "Polycythemia vera",
        "Biweekly SC; lifelong cytoreduction"),
    "sotatercept-dup": ("CHRONIC", "ActRIIA trap", "PAH",
        "Monthly SC; lifelong for progressive disease"),

    # ── ONCOLOGY – TIME-LIMITED (acute/short-course) ───────────────
    "asparaginase erwinia chrysanthemi (recombinant)-rywn": ("SHORT", "Enzyme (antineoplastic)", "ALL / LBL",
        "IM/IV doses 3× per week × 6 doses in a single course; fixed course"),
    "tenecteplase": ("SHORT", "Thrombolytic", "Acute myocardial infarction",
        "Single IV bolus for acute STEMI; one-time use"),
    "collagenase clostridium histolyticum": ("SHORT", "Collagenase enzyme", "Dupuytren's / Peyronie's disease",
        "1-3 injection sessions; limited course"),
    "anacaulase": ("SHORT", "Bromelain enzyme", "Burn wound debridement",
        "Topical enzymatic debridement; single or few-day application during acute wound care"),

    # ── GENE THERAPIES (ONE-TIME) ─────────────────────────────────
    "betibeglogene autotemcel": ("ONE-TIME", "Gene therapy (HSC)", "Transfusion-dependent β-thalassemia",
        "Single ex vivo gene addition via autologous HSC transplant"),
    "elivaldogene autotemcel": ("ONE-TIME", "Gene therapy (HSC)", "Metachromatic leukodystrophy (MLD)",
        "Single HSC gene therapy infusion"),
    "lovotibeglogene autotemcel": ("ONE-TIME", "Gene therapy (HSC)", "Sickle cell disease",
        "Single autologous HSC gene addition"),
    "exagamglogene autotemcel": ("ONE-TIME", "Gene therapy (HSC, gene editing)", "Sickle cell / TDT",
        "CRISPR-edited autologous HSC; one-time infusion"),
    "atidarsagene autotemcel": ("ONE-TIME", "Gene therapy (HSC)", "Metachromatic leukodystrophy",
        "Single ex vivo lentiviral gene therapy"),
    "valoctocogene roxaparvovec-rvox": ("ONE-TIME", "Gene therapy (AAV)", "Hemophilia A",
        "Single IV AAV5-FVIII infusion; expected durable effect"),
    "etranacogene dezaparvovec": ("ONE-TIME", "Gene therapy (AAV)", "Hemophilia B",
        "Single IV AAV5-FIX infusion"),
    "eladocagene exuparvovec-tneq": ("ONE-TIME", "Gene therapy (AAV)", "AADC deficiency",
        "Single intracranial surgery + AAV2 infusion"),
    "onasemnogene abeparvovec-brve": ("ONE-TIME", "Gene therapy (AAV)", "Spinal muscular atrophy type 1",
        "Single IV AAV9-SMN1 infusion"),
    "delandistrogene moxeparvovec-rokl": ("ONE-TIME", "Gene therapy (AAV)", "Duchenne muscular dystrophy",
        "Single IV AAVrh74-micro-dystrophin"),
    "marnetegragene autotemcel": ("ONE-TIME", "Gene therapy (HSC)", "Sickle cell / hemoglobinopathy",
        "Ex vivo gene addition; single infusion after conditioning"),
    "lunsotogene parvec-cwha": ("ONE-TIME", "Gene therapy (AAV)", "Rare retinal or metabolic disease",
        "AAV-based single IV/intravitreal delivery"),
    "etuvetidigene autotemcel": ("ONE-TIME", "Gene therapy (HSC)", "Rare hematologic disease",
        "Single autologous HSC gene therapy"),
    "revakinagene taroretcel-lwey": ("ONE-TIME", "Gene therapy (retinal)", "Inherited retinal disease",
        "Subretinal AAV injection; single procedure per eye"),
    "prademagene zamikeracel": ("ONE-TIME", "Gene therapy (ex vivo skin)", "Dystrophic epidermolysis bullosa",
        "Gene-corrected autologous keratinocyte grafts; surgical application"),
    "beremagene geperpavec-svdt": ("PERIODIC", "Topical gene therapy", "Dystrophic epidermolysis bullosa",
        "Topical wound gel applied repeatedly to open wounds; chronic condition but applied per wound"),

    # ── CAR-T / CELL THERAPIES (ONE-TIME) ─────────────────────────
    "brexucabtagene autoleucel": ("ONE-TIME", "CAR-T cell therapy", "Mantle cell lymphoma / B-ALL",
        "Single CAR-T infusion after lymphodepletion"),
    "idecabtagene vicleucel": ("ONE-TIME", "CAR-T cell therapy", "Relapsed/refractory myeloma",
        "Single CAR-T infusion"),
    "ciltacabtagene autoleucel": ("ONE-TIME", "CAR-T cell therapy", "Relapsed/refractory myeloma",
        "Single BCMA-targeting CAR-T infusion"),
    "obecabtagene autoleucel": ("ONE-TIME", "CAR-T cell therapy", "B-cell ALL",
        "Single CD19-targeting CAR-T infusion"),
    "lifileucel": ("ONE-TIME", "TIL cell therapy", "Advanced melanoma",
        "Single infusion of expanded tumor-infiltrating lymphocytes"),
    "afamitresgene autoleucel": ("ONE-TIME", "TCR-T cell therapy", "Synovial sarcoma / MRCLS",
        "Single MAGE-A4-targeting TCR-T infusion"),
    "omidubicel": ("ONE-TIME", "Stem cell graft enhancement", "Hematopoietic reconstitution",
        "Single nicotinamide-expanded cord blood transplant; one-time procedure"),
    "donislecel-jujn": ("ONE-TIME", "Islet cell transplant", "Type 1 diabetes (labile)",
        "Allogeneic islet infusion; one to several infusions, then maintenance immunosuppression"),
    "remestemcel-l-rknd": ("SHORT", "Mesenchymal stromal cells", "Steroid-refractory acute GvHD",
        "8 weekly infusions in acute setting; not indefinite"),
    "hpc, cord blood": ("ONE-TIME", "Hematopoietic progenitor cells", "Hematopoietic reconstitution",
        "Single cord blood transplant for malignant/non-malignant hematologic conditions"),
    "allogeneic processed thymus tissue": ("ONE-TIME", "Thymus tissue implant", "Complete DiGeorge anomaly",
        "Single surgical implantation; immune reconstitution over months"),
    "allogeneic keratinocyte cell line (niks), seeded on rat collagen (bd) conditioned with human dermal fibroblasts (clonetics)": ("SHORT", "Cellular wound therapy", "Dystrophic epidermolysis bullosa / chronic wounds",
        "Temporary biological wound dressing; not a permanent treatment"),
    "acellular tissue engineered vessel-tyod": ("ONE-TIME", "Tissue-engineered graft", "Vascular access / bypass",
        "Surgical implant; permanent once implanted"),
    "acellular nerve allograft-arwx": ("ONE-TIME", "Nerve graft", "Peripheral nerve repair",
        "Single surgical implantation for nerve gap repair"),
    "fecal microbiota transplantation, frozen preparation": ("SHORT", "Microbiome therapy", "Recurrent C. difficile infection",
        "1-3 administrations; not ongoing long-term therapy"),
    "fecal microbiota spores": ("SHORT", "Microbiome therapy", "Recurrent C. difficile",
        "3-day oral course; not chronic"),

    # ── ACUTE INFECTIOUS DISEASE ───────────────────────────────────
    "ansuvimab-zykl": ("SHORT", "Monoclonal antibody", "Ebola virus disease",
        "Single IV infusion for acute Ebola infection"),
    "atoltivimab, maftivimab, and odesivimab-ebgn": ("SHORT", "Monoclonal antibody cocktail", "Ebola virus disease",
        "Single IV infusion for acute Ebola; one-time acute treatment"),
    "nirsevimab": ("PERIODIC", "Anti-RSV mAb", "RSV prevention in infants/toddlers",
        "Single dose each RSV season; annual seasonal prophylaxis"),
    "clesrovimab-cfor": ("PERIODIC", "Anti-RSV mAb", "RSV prevention in infants",
        "Seasonal prophylaxis; one dose per RSV season"),

    # ── VACCINES (ONE-TIME or ANNUAL) ──────────────────────────────
    "influenza vaccine, adjuvanted": ("PERIODIC", "Vaccine", "Influenza prevention",
        "Annual vaccination; not chronic daily medication"),
    "influenza a (h5n1) monovalent vaccine, adjuvanted": ("ONE-TIME", "Vaccine", "H5N1 pandemic influenza prevention",
        "Pre-pandemic stockpile vaccine; 2-dose primary series"),
    "influenza vaccine": ("PERIODIC", "Vaccine", "Seasonal influenza prevention",
        "Annual dose; seasonal prevention"),
    "covid": ("PERIODIC", "mRNA / adjuvanted vaccine", "COVID-19 prevention",
        "Primary series + annual boosters; not daily medication"),
    "measles, mumps and rubella virus vaccine live": ("ONE-TIME", "Vaccine", "MMR prevention",
        "2-dose primary series in childhood; lifelong protection"),
    "measles, mumps, rubella and varicella virus vaccine live": ("ONE-TIME", "Vaccine", "MMRV prevention",
        "Childhood 2-dose series"),
    "varicella virus vaccine live": ("ONE-TIME", "Vaccine", "Varicella prevention",
        "2-dose childhood series"),
    "rotavirus vaccine, live, oral": ("ONE-TIME", "Vaccine", "Rotavirus gastroenteritis prevention",
        "2-3 dose infant series; not ongoing"),
    "hepatitis b vaccine (recombinant)": ("ONE-TIME", "Vaccine", "Hepatitis B prevention",
        "3-dose primary series"),
    "meningococcal (groups a, c, y, w) conjugate vaccine": ("ONE-TIME", "Vaccine", "Meningococcal disease prevention",
        "Primary series ± booster; not chronic"),
    "meningococcal (groups a, c, y, and w-135) oligosaccharide diphtheria crm197 conjugate vaccine": ("ONE-TIME", "Vaccine", "Meningococcal prevention",
        "Primary series ± booster"),
    "meningococcal groups a, b, c, w and y vaccine": ("ONE-TIME", "Vaccine", "Meningococcal prevention",
        "Primary series"),
    "pneumococcal 15-valent conjugate vaccine": ("ONE-TIME", "Vaccine", "Pneumococcal disease prevention",
        "One or two doses per schedule; not ongoing"),
    "pneumococcal 21-valent conjugate vaccine": ("ONE-TIME", "Vaccine", "Pneumococcal disease prevention",
        "Single dose in adults"),
    "zoster vaccine recombinant, adjuvanted": ("ONE-TIME", "Vaccine", "Herpes zoster (shingles) prevention",
        "2-dose series in adults ≥50; not repeated annually"),
    "cholera vaccine live oral": ("ONE-TIME", "Vaccine", "Cholera prevention (travelers)",
        "Single dose; not long-term"),
    "respiratory syncytial virus vaccine": ("ONE-TIME", "Vaccine", "RSV prevention (older adults)",
        "Single dose recommended once; not annual"),
    "respiratory syncytial virus vaccine, adjuvanted": ("ONE-TIME", "Vaccine", "RSV prevention (maternal)",
        "Single dose in pregnancy"),
    "respiratory syncytial virus vaccine, mrna (mrna-1345)": ("ONE-TIME", "Vaccine", "RSV prevention (older adults)",
        "Single dose"),
    "anthrax vaccine adsorbed, adjuvanted": ("ONE-TIME", "Vaccine", "Anthrax prevention",
        "Pre-exposure: 3-dose series + boosters; special populations only"),
    "smallpox and mpox vaccine, live, non-replicating": ("ONE-TIME", "Vaccine", "Smallpox / mpox prevention",
        "2-dose series; not repeated annually"),
    "chikungunya vaccine, recombinant": ("ONE-TIME", "Vaccine", "Chikungunya prevention",
        "Single dose"),

    # ── MISCELLANEOUS ─────────────────────────────────────────────
    "teplizumab-mzwv": ("SHORT", "Anti-CD3 antibody", "Delay of clinical T1D in at-risk individuals",
        "14-day IV course; single course; does not cure T1D but delays onset"),
    "emapalumab": ("SHORT", "Anti-IFN-γ antibody", "Primary hemophagocytic lymphohistiocytosis (HLH)",
        "Used until HSCT conditioning; weeks to months, not indefinite"),
    "prothrombin complex concentrate, human": ("SHORT", "Coagulation factor concentrate", "Acute coagulopathy / vitamin K antagonist reversal",
        "Acute dosing for bleeding reversal; not chronic"),
    "fibrinogen, human–chmt": ("SHORT", "Clotting protein", "Congenital fibrinogen deficiency / acute bleeding",
        "Prophylaxis in severe deficiency may be chronic; acute use is short-term"),
    "papzimeos": ("LONG-TERM", "DNA immunotherapy", "HPV-associated recurrent respiratory papillomatosis",
        "Precigen BLA 125832; repeated dosing cycles for RRP; ongoing until disease control"),
    "narsoplimab-wuug-2": ("LONG-TERM", "MASP-2 inhibitor", "HSCT-TMA / IgA nephropathy",
        "Phase 3; HSCT-TMA is time-limited, IgA neph may require long-term"),
}

# -------------------------------------------------------------------
# Load the data and apply classifications
# -------------------------------------------------------------------
df = pd.read_csv('/Work/AI_Drug/purplebook_merged_proper_name.csv')

# Normalise all CLASSIFICATIONS keys to lowercase for case-insensitive lookup
CLASSIFICATIONS_LOWER = {k.lower(): v for k, v in CLASSIFICATIONS.items()}

# Additional entries for coagulation factors (case variants)
CLASSIFICATIONS_LOWER.update({
    "coagulation factor viia (recombinant)": ("PERIODIC", "Coagulation factor", "Hemophilia A/B with inhibitors / rare bleeding",
        "Factor VIIa (NovoSeven/Sevenfact); on-demand for bleeds or prophylaxis; hemophilia care is lifelong"),
    "coagulation factor vii a (recombinant)": ("PERIODIC", "Coagulation factor", "Hemophilia / rare bleeding",
        "Factor VIIa; repeated dosing lifelong in hemophilia with inhibitors"),
    "coagulation factor viia (recombinant)-jncw": ("PERIODIC", "Coagulation factor", "Hemophilia A/B with inhibitors",
        "Next-gen rFVIIa (Alhemo or similar); prophylactic SC dosing long-term"),
    "antihemophilic factor (recombinant), rahf": ("CHRONIC", "Coagulation factor", "Hemophilia A",
        "Factor VIII (Advate/Kogenate); lifelong prophylaxis every 2-3 days"),
})

# Build lookup key
def make_key(name):
    return str(name).strip().lower()

# Build result rows
rows = []
for _, row in df.iterrows():
    drug = row['Proper Name, merged']
    key = make_key(drug)

    # Try exact match, then partial match
    match = CLASSIFICATIONS_LOWER.get(key)
    if not match:
        for k, v in CLASSIFICATIONS_LOWER.items():
            if k in key or key in k:
                match = v
                break

    if match:
        cat, subcat, indication, rationale = match
    else:
        cat, subcat, indication, rationale = ("REVIEW", "Unknown", str(drug), "Requires manual review")

    rows.append({
        'Proper Name': drug,
        'Proprietary Name': row.get('Proprietary Name', ''),
        'BLA Number': row.get('BLA Number', ''),
        'Category': cat,
        'Subcategory': subcat,
        'Primary Indication': indication,
        'Rationale': rationale,
        'Long-term Use': 'YES' if cat in ('CHRONIC', 'LONG-TERM', 'PERIODIC') else 'NO',
    })

result = pd.DataFrame(rows)

# -------------------------------------------------------------------
# Summary statistics
# -------------------------------------------------------------------
print("=" * 65)
print("CHRONIC USE ANALYSIS — FDA Purple Book Biologics (n=208)")
print("=" * 65)

cat_counts = result['Category'].value_counts()
print("\nDuration Category Breakdown:")
for cat, count in cat_counts.items():
    pct = 100 * count / len(result)
    print(f"  {cat:<12} {count:>4}  ({pct:.1f}%)")

print(f"\n{'─'*50}")
long_term = result[result['Long-term Use'] == 'YES']
oneoff = result[result['Category'].isin(['SHORT', 'ONE-TIME'])]
print(f"  LONG-TERM USE  (CHRONIC + LONG-TERM + PERIODIC): {len(long_term):>4}  ({100*len(long_term)/len(result):.1f}%)")
print(f"  SHORT/ONE-TIME USE (SHORT + ONE-TIME):            {len(oneoff):>4}  ({100*len(oneoff)/len(result):.1f}%)")

print(f"\n{'─'*50}")
print("\nSubcategory breakdown for CHRONIC drugs:")
chronic = result[result['Category'] == 'CHRONIC']
for sc, cnt in chronic['Subcategory'].value_counts().items():
    print(f"  {sc:<35} {cnt}")

print("\nSubcategory breakdown for LONG-TERM drugs:")
lt = result[result['Category'] == 'LONG-TERM']
for sc, cnt in lt['Subcategory'].value_counts().items():
    print(f"  {sc:<35} {cnt}")

# Review unclassified
unclassified = result[result['Category'] == 'REVIEW']
if len(unclassified) > 0:
    print(f"\n⚠  {len(unclassified)} drugs need manual review:")
    for _, r in unclassified.iterrows():
        print(f"   - {r['Proper Name']}")

# Save
result.to_csv('/Work/AI_Drug/chronic_use_classification.csv', index=False)
print(f"\n✓ Full classification saved to chronic_use_classification.csv")
print(f"  Total drugs classified: {len(result)}")
