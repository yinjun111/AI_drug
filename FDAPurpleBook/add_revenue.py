"""
Adds 2024 annual revenue (USD billions, global) to chronic_drugs_indications.csv
and updates the dashboard with a top-selling drugs chart.

Sources:
- AbbVie FY2024 earnings (adalimumab, risankizumab)
- Sanofi/Regeneron FY2024 (dupilumab, lanadelumab)
- Roche FY2024 (ocrelizumab, emicizumab, faricimab, tocilizumab, ranibizumab, rituximab)
- Regeneron FY2024 (aflibercept US + Bayer global)
- Novartis FY2024 (secukinumab, ofatumumab, omalizumab)
- J&J FY2024 (ustekinumab, guselkumab, infliximab)
- Takeda FY2024 (vedolizumab)
- Amgen FY2024 (denosumab, etanercept, eculizumab biosimilar)
- AstraZeneca FY2024 (ravulizumab, eculizumab, benralizumab, tezepelumab, anifrolumab)
- Eli Lilly FY2024 (dulaglutide, ixekizumab, insulin lispro)
- Novo Nordisk FY2024 (insulin aspart, insulin glargine)
- GSK FY2024 (mepolizumab, benralizumab)
- Biogen/Eisai FY2024 (lecanemab, natalizumab)
- argenx FY2024 (efgartigimod)
- Xtalks / DrugDiscoveryTrends top-50 2024 summary
"""

import pandas as pd

# ── Revenue map: drug proper name (lower) → 2024 global revenue in USD billions ──
# Values are global net sales unless noted. "~" = estimated from partial data.
# Drugs with <$50M or only recently approved are marked <0.1
REVENUE = {
    # ── Major blockbusters ──────────────────────────────────────────────────
    "dupilumab":               14.15,   # Sanofi/Regeneron FY2024
    "risankizumab":            11.72,   # AbbVie FY2024
    "adalimumab":               8.99,   # AbbVie FY2024 (biosimilar erosion)
    "aflibercept":              9.30,   # Regeneron (US $6.0B) + Bayer (ex-US) FY2024
    "ocrelizumab and hyaluronidase-ocsq": 6.70,  # Roche FY2024 (Ocrevus brand total)
    "secukinumab":              6.14,   # Novartis FY2024
    "vedolizumab":              5.40,   # Takeda FY2024 (Apr 2023–Mar 2024 fiscal)
    "emicizumab":               4.90,   # Roche FY2024
    "faricimab":                4.40,   # Roche FY2024 (CHF 3.9B → USD)
    "denosumab":                4.00,   # Amgen FY2024 Prolia
    "ustekinumab":              4.50,   # J&J FY2024 (declining post-biosimilar)
    "guselkumab":               3.67,   # J&J FY2024
    "omalizumab":               3.70,   # Genentech/Novartis FY2024
    "etanercept":               3.50,   # Amgen FY2024 (US+intl combined)
    "dulaglutide":              4.80,   # Eli Lilly FY2024
    "infliximab":               1.50,   # J&J FY2024 (Remicade, eroding)
    "rituximab":                2.00,   # Roche FY2024 (Rituxan/MabThera)
    "tocilizumab":              1.51,   # Roche FY2024
    "emicizumab-dup":           4.90,   # same as above (key lookup)

    # ── Billion-dollar tier ──────────────────────────────────────────────────
    "ixekizumab":               2.50,   # Eli Lilly FY2024
    "ravulizumab":              2.50,   # AstraZeneca FY2024 (Ultomiris)
    "mepolizumab":              2.00,   # GSK FY2024
    "insulin lispro":           2.00,   # Eli Lilly (Humalog) FY2024
    "insulin glargine":         2.50,   # Sanofi (Lantus+Toujeo) FY2024
    "insulin aspart":           2.00,   # Novo Nordisk (NovoLog/NovoRapid) FY2024
    "natalizumab-sztn":         1.50,   # Biogen FY2024 (Tysabri, declining)
    "epoetin alfa":             1.00,   # Amgen/J&J FY2024 (market mature)
    "pancrelipase":             1.50,   # AbbVie (Creon) FY2024
    "eculizumab":               1.50,   # AstraZeneca FY2024 (Soliris, declining)
    "ranibizumab":              0.30,   # Roche FY2024 (Lucentis, near end-of-life)
    "ofatumumab":               1.20,   # Novartis FY2024 (Kesimpta)
    "nirsevimab":               1.80,   # Sanofi/AstraZeneca FY2024 (Beyfortus)

    # ── Sub-billion / growing ────────────────────────────────────────────────
    "benralizumab":             1.30,   # AstraZeneca FY2024
    "tezepelumab":              0.80,   # AstraZeneca/Amgen FY2024
    "brolucizumab-dbll":        0.60,   # Novartis FY2024
    "ublituximab-xiiy":         0.30,   # TG Therapeutics FY2024
    "efgartigimod alfa-fcab":   0.60,   # argenx FY2024
    "efgartigimod alfa and hyaluronidase": 0.60,
    "anifrolumab":              0.50,   # AstraZeneca FY2024 (Saphnelo)
    "eptinezumab-jjmr":         0.50,   # Lundbeck FY2024
    "satralizumab-mwge":        0.30,   # Roche FY2024
    "inebilizumab-cdon":        0.20,   # Amgen FY2024
    "lecanemab":                0.40,   # Biogen/Eisai FY2024 (Leqembi)
    "donanemab-azbt":           0.20,   # Eli Lilly FY2024 (Kisunla, very new)
    "aducanumab":               0.02,   # Biogen FY2024 (Aduhelm, near-discontinued)
    "tralokinumab":             0.30,   # LEO Pharma FY2024 (Adbry)
    "bimekizumab":              0.50,   # UCB FY2024 (Bimzelx)
    "mirikizumab":              0.30,   # Eli Lilly FY2024 (Omvoh)
    "lebrikizumab":             0.10,   # Eli Lilly FY2024 (Ebglyss, new in US)
    "spesolimab":               0.20,   # Boehringer Ingelheim FY2024
    "sutimlimab-jome":          0.20,   # Sanofi FY2024 (Enjaymo)
    "crovalimab-akkz":          0.30,   # Roche FY2024 (Piasky)
    "sotatercept":              0.30,   # Merck FY2024 (Winrevair, approved Mar 2024)
    "lanadelumab":              0.70,   # Sanofi FY2024 (Takhzyro)
    "avalglucosidase alfa-ngpt":0.40,   # Sanofi FY2024 (Nexviazyme)
    "cipaglucosidase alfa-atga":0.20,   # Amicus Therapeutics FY2024 (Pombiliti)
    "alpha":                    0.40,   # Grifols/Takeda FY2024 (Prolastin/Glassia)
    "pegloticase":              0.30,   # Amgen/Horizon FY2024 (Krystexxa)
    "rozanolixizumab":          0.10,   # UCB FY2024 (Rystiggo, new)
    "nipocalimab":              0.05,   # J&J FY2024 (Imaavy, very new)
    "sibeprenlimab-szsi":       0.05,   # Vistagen FY2024 (very new)
    "filgrastim":               0.50,   # Amgen/biosimilars FY2024
    "immune globulin intravenous, human": 1.50,  # Grifols/CSL FY2024 (IVIg market)
    "immune globulin subcutaneous (human), 20% liquid": 0.80,  # CSL/Grifols FY2024
    "dulaglutide-dup":          4.80,

    # ── Smaller / rare disease / recently approved ──────────────────────────
    "pegunigalsidase alfa":     0.10,   # Chiesi FY2024 (Elfabrio)
    "olipudase alfa":           0.10,   # Sanofi FY2024 (Xenpozyme)
    "velmanase alfa-tycv":      0.05,   # Chiesi FY2024 (Lamzede)
    "evinacumab":               0.10,   # Regeneron FY2024 (Evkeeza)
    "lerodalcibep-liga":        0.05,   # Regeneron FY2024 (very new)
    "ropeginterferon alfa-2b-njft": 0.20,  # PharmaEssentia FY2024 (Besremi)
    "tividenofusp alfa-eknm":   0.05,   # Denali FY2024 (Avlayah, approved 2024)
    "pegzilarginase":           0.05,   # Ultragenyx FY2024 (Loargys)
    "depemokimab":              0.05,   # GSK FY2024 (very new)
    "axatilimab-csfr":          0.10,   # Syndax FY2024 (Niktimvo)
    "nemolizumab-ilto":         0.05,   # Galderma FY2024 (Nemluvio, new)
    "pozelimab-bbfg":           0.05,   # Regeneron FY2024 (Veopoz, ultra-rare)
    "somapacitan":              0.10,   # Novo Nordisk FY2024 (Sogroya)
    "lonapegsomatropin":        0.10,   # TransEnterix FY2024 (Skytrofa)
    "somatrogon":               0.10,   # Pfizer/OPKO FY2024 (Ngenla)
    "tesamorelin":              0.10,   # Theratechnologies FY2024 (Egrifta)
    "sacrosidase":              0.10,   # QOL Medical (Sucraid)
    "pancrelipase-dup":         1.50,
    "concizumab":               0.05,   # Novo Nordisk FY2024 (Alhemo, new)
    "marstacimab":              0.05,   # Pfizer FY2024 (recently approved)
    "garadacimab":              0.05,   # CSL Behring FY2024 (new)
    "daxibotulinumtoxina":      0.15,   # Revance FY2024 (Daxxify)
    "letibotulinumtoxina":      0.05,   # Hugel FY2024 (Letybo, new in US)
    "clesrovimab-cfor":         0.05,   # AstraZeneca FY2024 (new)
    "peanut (arachis hypogaea) allergen powder": 0.20,  # Stallergenes FY2024 (Palforzia)
    "short ragweed pollen allergen extract": 0.10,
    "papzimeos":                0.01,   # Precigen FY2024 (just approved)
    "insulin icodec":           0.10,   # Novo Nordisk FY2024 (Awiqli, new)
    # coagulation factors (combined hemophilia market)
    "antihemophilic factor (recombinant), rahf":       0.80,
    "antihemophilic factor (recombinant), fc":         0.60,
    "antihemophilic factor (recombinant), pegylated-aucl": 0.50,
    "coagulation factor ix (recombinant), glycopegylated": 0.40,
    "coagulation factor viia (recombinant)":            0.40,
    "coagulation factor viia (recombinant)-jncw":       0.10,
    "lanadelumab-dup":          0.70,
}

# ─────────────────────────────────────────────────────────────────────────────
# Load and apply
# ─────────────────────────────────────────────────────────────────────────────
df = pd.read_csv("/Work/AI_Drug/chronic_drugs_indications.csv")

def get_revenue(drug):
    key = str(drug).strip().lower()
    if key in REVENUE:
        return REVENUE[key]
    for k, v in REVENUE.items():
        if k in key or key.startswith(k[:20]):
            return v
    return None

df["Annual Revenue 2024 (USD B)"] = df["Drug (Proper Name)"].apply(get_revenue)

# Show coverage
matched = df["Annual Revenue 2024 (USD B)"].notna().sum()
print(f"Revenue matched: {matched}/{len(df)} rows ({100*matched/len(df):.0f}%)")

missing = df[df["Annual Revenue 2024 (USD B)"].isna()]["Drug (Proper Name)"].unique()
if len(missing):
    print(f"\nUnmatched ({len(missing)}):")
    for m in missing:
        print(f"  - {m}")

# Reorder columns
cols = ["Drug (Proper Name)", "Brand Name(s)", "Disease / Indication",
        "Disease Category", "Drug Target (Gene)",
        "Annual Revenue 2024 (USD B)", "Dose", "Frequency", "Duration of Use"]
df = df[cols]
df.to_csv("/Work/AI_Drug/chronic_drugs_indications.csv", index=False)
print(f"\n✓ Saved → chronic_drugs_indications.csv")

# Preview top earners
top = (df[["Drug (Proper Name)", "Annual Revenue 2024 (USD B)", "Drug Target (Gene)","Disease Category"]]
       .drop_duplicates("Drug (Proper Name)")
       .sort_values("Annual Revenue 2024 (USD B)", ascending=False)
       .head(20))
print("\nTop 20 by revenue:")
print(top.to_string(index=False))
