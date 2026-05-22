"""
Adds a 'Drug Target (Gene)' column to chronic_drugs_indications.csv.
Gene symbols from ChEMBL + HGNC; for enzyme replacements, lists the deficient enzyme gene.
"""
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# Drug → target gene(s) mapping
# For bispecifics both targets are listed.
# For enzyme replacement therapies: gene of the deficient enzyme being replaced.
# For viral targets: noted as "(viral)" since no human gene applies.
# ─────────────────────────────────────────────────────────────────────────────
TARGETS = {
    # ── TNF inhibitors ───────────────────────────────────────────────────────
    "adalimumab":           "TNF",
    "etanercept":           "TNF",          # TNFRSF1B-Fc fusion trapping TNF ligand
    "infliximab":           "TNF",

    # ── IL-17 / IL-23 axis ───────────────────────────────────────────────────
    "secukinumab":          "IL17A",
    "ixekizumab":           "IL17A",
    "bimekizumab":          "IL17A, IL17F", # dual IL-17A/F blocker
    "guselkumab":           "IL23A",        # anti-p19 (IL-23 specific subunit)
    "risankizumab":         "IL23A",
    "ustekinumab":          "IL12B",        # anti-p40 (shared by IL-12 and IL-23)
    "mirikizumab":          "IL23A",

    # ── IL-4/13 / type-2 inflammation ────────────────────────────────────────
    "dupilumab":            "IL4R",         # IL-4Rα; blocks both IL-4 and IL-13 signalling
    "tralokinumab":         "IL13",
    "lebrikizumab":         "IL13",
    "nemolizumab-ilto":     "IL31RA",       # IL-31 receptor α (pruritus pathway)

    # ── IL-5 / eosinophil axis ───────────────────────────────────────────────
    "mepolizumab":          "IL5",
    "benralizumab":         "IL5RA",        # IL-5 receptor α (depletes eosinophils)
    "depemokimab":          "IL5",

    # ── TSLP / IgE / upper airway ────────────────────────────────────────────
    "tezepelumab":          "TSLP",
    "omalizumab":           "IGHE",         # binds IgE (encoded by IGHE / IGHΕ)

    # ── IL-6R ────────────────────────────────────────────────────────────────
    "tocilizumab":          "IL6R",
    "satralizumab-mwge":    "IL6R",

    # ── IL-36R ───────────────────────────────────────────────────────────────
    "spesolimab":           "IL1RL2",       # IL-36 receptor (gene IL1RL2; confirmed ChEMBL)

    # ── Integrin blockers ────────────────────────────────────────────────────
    "vedolizumab":          "ITGA4, ITGB7", # α4β7 integrin; gut-selective
    "natalizumab-sztn":     "ITGA4",        # α4 integrin (α4β1 and α4β7)

    # ── CD20 (B-cell depletion) ───────────────────────────────────────────────
    "rituximab":            "MS4A1",        # CD20
    "ofatumumab":           "MS4A1",
    "ublituximab-xiiy":     "MS4A1",
    "ocrelizumab and hyaluronidase-ocsq": "MS4A1",

    # ── CD19 ─────────────────────────────────────────────────────────────────
    "inebilizumab-cdon":    "CD19",

    # ── IFN / SLE ────────────────────────────────────────────────────────────
    "anifrolumab":          "IFNAR1",       # type-I IFN receptor subunit 1
    "ropeginterferon alfa-2b-njft": "IFNAR1, IFNAR2",  # activates IFN receptor

    # ── FcRn (IgG recycling) – MG / neuromuscular ────────────────────────────
    "efgartigimod alfa-fcab":               "FCGRT",
    "efgartigimod alfa and hyaluronidase":  "FCGRT",
    "rozanolixizumab":                      "FCGRT",
    "nipocalimab":                          "FCGRT",

    # ── CSF1R ────────────────────────────────────────────────────────────────
    "axatilimab-csfr":      "CSF1R",        # M-CSF receptor; depletes pathogenic macrophages in cGVHD

    # ── APRIL / TNFSF13 ──────────────────────────────────────────────────────
    "sibeprenlimab-szsi":   "TNFSF13",      # APRIL; drives IgA class switching

    # ── Complement cascade ───────────────────────────────────────────────────
    "eculizumab":           "C5",
    "ravulizumab":          "C5",
    "crovalimab-akkz":      "C5",
    "pozelimab-bbfg":       "C5",
    "sutimlimab-jome":      "C1S",          # C1s serine protease (classical pathway)

    # ── Hemophilia / coagulation ─────────────────────────────────────────────
    "emicizumab":           "F9, F10",      # bispecific bridging FIXa and FX (replaces FVIIIa)
    "concizumab":           "TFPI",         # tissue factor pathway inhibitor (confirmed ChEMBL)
    "marstacimab":          "TFPI",
    "antihemophilic factor (recombinant), rahf":   "F8",   # replaces FVIII
    "antihemophilic factor (recombinant), fc":     "F8",
    "antihemophilic factor (recombinant), pegylated-aucl": "F8",
    "coagulation factor ix (recombinant), glycopegylated": "F9",
    "coagulation factor viia (recombinant)":        "F7",  # activated FVII
    "coagulation factor viia (recombinant)-jncw":   "F7",

    # ── HAE (kallikrein / FXII) ───────────────────────────────────────────────
    "lanadelumab":          "KLKB1",        # plasma kallikrein; prevents bradykinin generation
    "garadacimab":          "F12",          # Factor XII (Hageman factor)

    # ── Anti-VEGF / ophthalmology ────────────────────────────────────────────
    "ranibizumab":          "VEGFA",
    "brolucizumab-dbll":    "VEGFA",
    "aflibercept":          "VEGFA, PGF",   # VEGF trap: binds VEGF-A, VEGF-B, PlGF
    "faricimab":            "VEGFA, ANGPT2",# bispecific (confirmed ChEMBL)

    # ── Endocrine ────────────────────────────────────────────────────────────
    "insulin lispro":       "INSR",
    "insulin glargine":     "INSR",
    "insulin aspart":       "INSR",
    "insulin icodec":       "INSR",
    "dulaglutide":          "GLP1R",
    "somapacitan":          "GHR",
    "lonapegsomatropin":    "GHR",
    "somatrogon":           "GHR",
    "tesamorelin":          "GHRHR",
    "epoetin alfa":         "EPOR",
    "evinacumab":           "ANGPTL3",
    "lerodalcibep-liga":    "PCSK9",
    "denosumab":            "TNFSF11",      # RANKL (RANK ligand)

    # ── PAH ──────────────────────────────────────────────────────────────────
    "sotatercept":          "INHBA",        # activin A / ActRIIA trap (confirmed ChEMBL: INHBA)

    # ── Neurology – neurodegeneration ────────────────────────────────────────
    "lecanemab":            "APP",          # targets Aβ protofibrils (from APP processing)
    "aducanumab":           "APP",
    "donanemab-azbt":       "APP",          # pyroglutamated Aβ3(pE)-42 form
    "eptinezumab-jjmr":     "CALCA",        # CGRP (calcitonin gene-related peptide α, gene CALCA)

    # ── Enzyme replacement (gene of deficient enzyme) ─────────────────────────
    "sacrosidase":          "SI",           # sucrase-isomaltase; replaces deficient SI
    "pancrelipase":         "PNLIP",        # pancreatic lipase; EPI (multi-enzyme product)
    "pegunigalsidase alfa": "GLA",          # α-galactosidase A; Fabry disease
    "velmanase alfa-tycv":  "MAN2B1",       # lysosomal α-mannosidase; alpha-mannosidosis
    "olipudase alfa":       "SMPD1",        # acid sphingomyelinase; ASMD
    "avalglucosidase alfa-ngpt": "GAA",     # acid α-glucosidase; Pompe disease
    "cipaglucosidase alfa-atga": "GAA",
    "tividenofusp alfa-eknm": "IDS",        # iduronate-2-sulfatase; MPS II (Hunter)
    "pegzilarginase":       "ARG1",         # arginase 1; arginase-1 deficiency
    "alpha":                "SERPINA1",     # α1-antitrypsin; AATD augmentation

    # ── Immunoglobulin / G-CSF ───────────────────────────────────────────────
    "immune globulin intravenous, human":              "IGHG1 (polyclonal IgG)",
    "immune globulin subcutaneous (human), 20% liquid":"IGHG1 (polyclonal IgG)",
    "filgrastim":           "CSF3R",        # G-CSF receptor; stimulates neutrophil production

    # ── Gout ─────────────────────────────────────────────────────────────────
    "pegloticase":          "UOX",          # recombinant urate oxidase; degrades uric acid

    # ── Botulinum toxins ─────────────────────────────────────────────────────
    "daxibotulinumtoxina":  "SNAP25",       # SNARE protein cleaved by BoNT/A serotype
    "letibotulinumtoxina":  "SNAP25",

    # ── RSV prophylaxis ──────────────────────────────────────────────────────
    "nirsevimab":           "RSV F (viral)", # RSV fusion glycoprotein (prefusion epitope)
    "clesrovimab-cfor":     "RSV F (viral)",

    # ── Gout (repeat from different key form) ────────────────────────────────
    "peanut (arachis hypogaea) allergen powder": "FCER1A, IL4R",   # IgE-mediated; desensitization through IgE / IL-4Rα pathway
    "short ragweed pollen allergen extract":      "FCER1A, IL4R",

    # ── Rare / ENT ───────────────────────────────────────────────────────────
    "papzimeos":            "HPV E6/E7 (viral)", # HPV oncoprotein-directed DNA immunotherapy
}

# ─────────────────────────────────────────────────────────────────────────────
# Load and merge
# ─────────────────────────────────────────────────────────────────────────────
df = pd.read_csv("/Work/AI_Drug/chronic_drugs_indications.csv")

def lookup_target(drug_name):
    key = str(drug_name).strip().lower()
    # exact match
    if key in TARGETS:
        return TARGETS[key]
    # partial match
    for k, v in TARGETS.items():
        if k in key or key.startswith(k[:15]):
            return v
    return "N/A"

df["Drug Target (Gene)"] = df["Drug (Proper Name)"].apply(lookup_target)

# Report any missing
missing = df[df["Drug Target (Gene)"] == "N/A"]["Drug (Proper Name)"].unique()
if len(missing):
    print(f"⚠  {len(missing)} drugs without target mapping:")
    for m in missing:
        print(f"   - {m}")
else:
    print("✓ All drugs matched to a target")

# Reorder columns
cols = ["Drug (Proper Name)", "Brand Name(s)", "Disease / Indication",
        "Disease Category", "Drug Target (Gene)", "Dose", "Frequency", "Duration of Use"]
df = df[cols]

df.to_csv("/Work/AI_Drug/chronic_drugs_indications.csv", index=False)
print(f"✓ Updated → chronic_drugs_indications.csv  ({len(df)} rows, {len(cols)} columns)")

# Quick preview
pd.set_option("display.max_colwidth", 45)
print()
print(df[["Drug (Proper Name)", "Disease / Indication", "Drug Target (Gene)"]].drop_duplicates().to_string(index=False))
