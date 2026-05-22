"""
Builds a detailed per-drug-per-indication table for CHRONIC and LONG-TERM biologics,
excluding oncology indications. Includes dose, frequency, and duration.
"""
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# DATA: one entry per (drug, indication)
# Fields: drug, brand, disease, disease_category, dose, frequency, duration
# ─────────────────────────────────────────────────────────────────────────────
ROWS = [

    # ══ AUTOIMMUNE – RHEUMATOLOGY ════════════════════════════════════════════
    ("adalimumab", "Humira / biosimilars", "Rheumatoid arthritis", "Autoimmune – Rheumatology",
     "40 mg SC", "Every 2 weeks", "Indefinite (lifelong maintenance)"),
    ("adalimumab", "Humira / biosimilars", "Psoriatic arthritis", "Autoimmune – Rheumatology",
     "40 mg SC", "Every 2 weeks", "Indefinite"),
    ("adalimumab", "Humira / biosimilars", "Ankylosing spondylitis / axSpA", "Autoimmune – Rheumatology",
     "40 mg SC", "Every 2 weeks", "Indefinite"),
    ("adalimumab", "Humira / biosimilars", "Juvenile idiopathic arthritis", "Autoimmune – Rheumatology",
     "10–20 mg SC (weight-based)", "Every 2 weeks", "Indefinite"),

    ("etanercept", "Enbrel / biosimilars", "Rheumatoid arthritis", "Autoimmune – Rheumatology",
     "50 mg SC", "Once weekly", "Indefinite"),
    ("etanercept", "Enbrel / biosimilars", "Psoriatic arthritis", "Autoimmune – Rheumatology",
     "50 mg SC", "Once weekly", "Indefinite"),
    ("etanercept", "Enbrel / biosimilars", "Ankylosing spondylitis", "Autoimmune – Rheumatology",
     "50 mg SC", "Once weekly", "Indefinite"),
    ("etanercept", "Enbrel / biosimilars", "Juvenile idiopathic arthritis", "Autoimmune – Rheumatology",
     "0.8 mg/kg SC (max 50 mg)", "Once weekly", "Indefinite"),

    ("infliximab", "Remicade / biosimilars", "Rheumatoid arthritis", "Autoimmune – Rheumatology",
     "3 mg/kg IV (wk 0, 2, 6 induction)", "Every 8 weeks (maintenance)", "Indefinite"),
    ("infliximab", "Remicade / biosimilars", "Ankylosing spondylitis / axSpA", "Autoimmune – Rheumatology",
     "5 mg/kg IV (wk 0, 2, 6 induction)", "Every 6 weeks (maintenance)", "Indefinite"),
    ("infliximab", "Remicade / biosimilars", "Psoriatic arthritis", "Autoimmune – Rheumatology",
     "5 mg/kg IV (wk 0, 2, 6 induction)", "Every 8 weeks (maintenance)", "Indefinite"),

    ("secukinumab", "Cosentyx", "Psoriatic arthritis", "Autoimmune – Rheumatology",
     "150 mg SC (weekly ×5, then q4w; or 300 mg if prior anti-TNF failure)", "Every 4 weeks", "Indefinite"),
    ("secukinumab", "Cosentyx", "Ankylosing spondylitis / AS", "Autoimmune – Rheumatology",
     "150 mg SC (weekly ×5, then q4w)", "Every 4 weeks", "Indefinite"),
    ("secukinumab", "Cosentyx", "Non-radiographic axSpA", "Autoimmune – Rheumatology",
     "150 mg SC (weekly ×5, then q4w)", "Every 4 weeks", "Indefinite"),

    ("ixekizumab", "Taltz", "Psoriatic arthritis", "Autoimmune – Rheumatology",
     "160 mg SC (wk 0), then 80 mg", "Every 4 weeks", "Indefinite"),
    ("ixekizumab", "Taltz", "Ankylosing spondylitis", "Autoimmune – Rheumatology",
     "160 mg SC (wk 0), then 80 mg", "Every 4 weeks", "Indefinite"),
    ("ixekizumab", "Taltz", "Non-radiographic axSpA", "Autoimmune – Rheumatology",
     "80 mg SC", "Every 4 weeks", "Indefinite"),

    ("guselkumab", "Tremfya", "Psoriatic arthritis", "Autoimmune – Rheumatology",
     "100 mg SC (wk 0 & 4, then q8w)", "Every 8 weeks", "Indefinite"),

    ("tocilizumab", "Actemra", "Rheumatoid arthritis", "Autoimmune – Rheumatology",
     "4–8 mg/kg IV q4w; or 162 mg SC", "Every 1–2 weeks (SC) / every 4 weeks (IV)", "Indefinite"),
    ("tocilizumab", "Actemra", "Giant cell arteritis", "Autoimmune – Rheumatology",
     "162 mg SC (+ steroid taper)", "Every week", "Indefinite (disease recurs off therapy)"),
    ("tocilizumab", "Actemra", "Juvenile idiopathic arthritis (SJIA/PJIA)", "Autoimmune – Rheumatology",
     "8–12 mg/kg IV (weight-based)", "Every 2–4 weeks", "Indefinite"),

    ("rituximab", "Rituxan / biosimilars", "Rheumatoid arthritis (anti-TNF inadequate responders)", "Autoimmune – Rheumatology",
     "1000 mg IV ×2 doses (2 wks apart)", "Repeat course every 24 weeks (or on relapse)", "Indefinite maintenance"),
    ("rituximab", "Rituxan / biosimilars", "ANCA-associated vasculitis (GPA / MPA)", "Autoimmune – Rheumatology",
     "375 mg/m² IV ×4 (induction); then 500 mg IV ×2 (at 6 and 12 mo)", "Every 6 months (maintenance)", "≥2 years (long-term remission maintenance)"),
    ("rituximab", "Rituxan / biosimilars", "Pemphigus vulgaris", "Autoimmune – Dermatology",
     "1000 mg IV ×2 doses (2 wks apart)", "Repeat at 12 mo, 18 mo, then PRN", "Indefinite (disease relapse common)"),

    ("bimekizumab", "Bimzelx", "Psoriatic arthritis", "Autoimmune – Rheumatology",
     "160 mg SC", "Every 4 weeks", "Indefinite"),
    ("bimekizumab", "Bimzelx", "Ankylosing spondylitis / nr-axSpA", "Autoimmune – Rheumatology",
     "160 mg SC", "Every 4 weeks", "Indefinite"),

    # ══ AUTOIMMUNE – DERMATOLOGY ══════════════════════════════════════════════
    ("adalimumab", "Humira / biosimilars", "Plaque psoriasis", "Autoimmune – Dermatology",
     "80 mg SC (wk 0), then 40 mg (wk 1), then 40 mg", "Every 2 weeks", "Indefinite"),
    ("adalimumab", "Humira / biosimilars", "Hidradenitis suppurativa", "Autoimmune – Dermatology",
     "160 mg SC (day 1), 80 mg (day 15), then 40 mg", "Weekly", "Indefinite"),
    ("adalimumab", "Humira / biosimilars", "Non-infectious uveitis", "Autoimmune – Dermatology",
     "80 mg SC (wk 0), then 40 mg (wk 1), then 40 mg", "Every 2 weeks", "Indefinite"),

    ("etanercept", "Enbrel / biosimilars", "Plaque psoriasis", "Autoimmune – Dermatology",
     "50 mg SC twice weekly ×12 wks (induction), then 50 mg", "Once weekly (maintenance)", "Indefinite"),

    ("infliximab", "Remicade / biosimilars", "Plaque psoriasis", "Autoimmune – Dermatology",
     "5 mg/kg IV (wk 0, 2, 6 induction)", "Every 8 weeks", "Indefinite"),

    ("secukinumab", "Cosentyx", "Plaque psoriasis", "Autoimmune – Dermatology",
     "300 mg SC weekly ×5 (induction), then 300 mg", "Every 4 weeks", "Indefinite"),

    ("ixekizumab", "Taltz", "Plaque psoriasis", "Autoimmune – Dermatology",
     "160 mg SC (wk 0); 80 mg q2w ×5 doses", "Every 4 weeks (maintenance)", "Indefinite"),

    ("guselkumab", "Tremfya", "Plaque psoriasis", "Autoimmune – Dermatology",
     "100 mg SC (wk 0 & 4)", "Every 8 weeks", "Indefinite"),

    ("risankizumab", "Skyrizi", "Plaque psoriasis", "Autoimmune – Dermatology",
     "150 mg SC (2 × 75 mg at wk 0 & 4)", "Every 12 weeks", "Indefinite"),
    ("risankizumab", "Skyrizi", "Psoriatic arthritis", "Autoimmune – Rheumatology",
     "150 mg SC (wk 0 & 4, then q12w)", "Every 12 weeks", "Indefinite"),

    ("bimekizumab", "Bimzelx", "Plaque psoriasis", "Autoimmune – Dermatology",
     "320 mg SC q4w ×16 wks (induction)", "Every 8 weeks (maintenance)", "Indefinite"),

    ("dupilumab", "Dupixent", "Atopic dermatitis (adults)", "Autoimmune – Dermatology",
     "600 mg SC loading (2 × 300 mg), then 300 mg", "Every 2 weeks", "Indefinite"),
    ("dupilumab", "Dupixent", "Prurigo nodularis", "Autoimmune – Dermatology",
     "600 mg SC loading, then 300 mg", "Every 2 weeks", "Indefinite (recurrent pruritic condition)"),

    ("tralokinumab", "Adbry", "Atopic dermatitis", "Autoimmune – Dermatology",
     "600 mg SC loading (4 × 150 mg), then 300 mg q2w; may step down to q4w if controlled",
     "Every 2–4 weeks", "Indefinite"),

    ("lebrikizumab", "Ebglyss", "Atopic dermatitis", "Autoimmune – Dermatology",
     "500 mg SC ×2 at wk 0, then 250 mg", "Every 2 weeks", "Indefinite"),

    ("nemolizumab-ilto", "Nemluvio", "Atopic dermatitis", "Autoimmune – Dermatology",
     "30 mg SC", "Every 4 weeks", "Indefinite"),
    ("nemolizumab-ilto", "Nemluvio", "Prurigo nodularis", "Autoimmune – Dermatology",
     "30 mg SC", "Every 4 weeks", "Indefinite"),

    ("spesolimab", "Spevigo", "Generalized pustular psoriasis – acute flare", "Autoimmune – Dermatology",
     "900 mg IV (single dose per flare)", "Per flare episode", "As needed for acute flares"),
    ("spesolimab", "Spevigo", "Generalized pustular psoriasis – maintenance", "Autoimmune – Dermatology",
     "600 mg SC", "Every 12 weeks", "Indefinite (chronic prophylaxis)"),

    # ══ AUTOIMMUNE – GASTROENTEROLOGY (IBD) ══════════════════════════════════
    ("adalimumab", "Humira / biosimilars", "Crohn's disease", "Autoimmune – Gastroenterology",
     "160 mg SC (wk 0), 80 mg (wk 2), then 40 mg", "Every 2 weeks", "Indefinite"),
    ("adalimumab", "Humira / biosimilars", "Ulcerative colitis", "Autoimmune – Gastroenterology",
     "160 mg SC (wk 0), 80 mg (wk 2), then 40 mg", "Every 2 weeks", "Indefinite"),

    ("infliximab", "Remicade / biosimilars", "Crohn's disease", "Autoimmune – Gastroenterology",
     "5 mg/kg IV (wk 0, 2, 6 induction)", "Every 8 weeks", "Indefinite"),
    ("infliximab", "Remicade / biosimilars", "Ulcerative colitis", "Autoimmune – Gastroenterology",
     "5 mg/kg IV (wk 0, 2, 6 induction)", "Every 8 weeks", "Indefinite"),

    ("ustekinumab", "Stelara", "Crohn's disease", "Autoimmune – Gastroenterology",
     "~260–520 mg IV (single weight-based induction), then 90 mg SC", "Every 8 weeks (SC maintenance)", "Indefinite"),
    ("ustekinumab", "Stelara", "Ulcerative colitis", "Autoimmune – Gastroenterology",
     "~260–520 mg IV (single induction), then 90 mg SC", "Every 8 weeks", "Indefinite"),
    ("ustekinumab", "Stelara", "Plaque psoriasis", "Autoimmune – Dermatology",
     "45 mg (≤100 kg) or 90 mg SC at wk 0 & 4", "Every 12 weeks", "Indefinite"),
    ("ustekinumab", "Stelara", "Psoriatic arthritis", "Autoimmune – Rheumatology",
     "45 mg or 90 mg SC at wk 0 & 4", "Every 12 weeks", "Indefinite"),

    ("vedolizumab", "Entyvio", "Ulcerative colitis", "Autoimmune – Gastroenterology",
     "300 mg IV (wk 0, 2, 6 induction)", "Every 8 weeks (maintenance)", "Indefinite"),
    ("vedolizumab", "Entyvio", "Crohn's disease", "Autoimmune – Gastroenterology",
     "300 mg IV (wk 0, 2, 6 induction)", "Every 8 weeks (maintenance)", "Indefinite"),

    ("risankizumab", "Skyrizi", "Crohn's disease", "Autoimmune – Gastroenterology",
     "600 mg IV ×3 (q8w induction), then 360 mg SC", "Every 8 weeks", "Indefinite"),
    ("risankizumab", "Skyrizi", "Ulcerative colitis", "Autoimmune – Gastroenterology",
     "600 mg IV ×3 (q8w induction), then 180 mg SC", "Every 8 weeks", "Indefinite"),

    ("mirikizumab", "Omvoh", "Ulcerative colitis", "Autoimmune – Gastroenterology",
     "300 mg IV ×3 (q4w induction), then 200 mg SC", "Every 4 weeks", "Indefinite"),

    # ══ AUTOIMMUNE – PULMONOLOGY / ALLERGY ═══════════════════════════════════
    ("dupilumab", "Dupixent", "Moderate-to-severe asthma", "Autoimmune – Pulmonology",
     "200 or 300 mg SC (dose by eosinophil/OCS status)", "Every 2 weeks", "Indefinite"),
    ("dupilumab", "Dupixent", "CRSwNP (chronic rhinosinusitis with nasal polyps)", "Autoimmune – Pulmonology",
     "300 mg SC", "Every 2 weeks", "Indefinite"),
    ("dupilumab", "Dupixent", "Eosinophilic esophagitis (EoE)", "Autoimmune – Gastroenterology",
     "300 mg SC", "Once weekly", "Indefinite"),
    ("dupilumab", "Dupixent", "COPD with type-2 inflammation (eosinophilic)", "Autoimmune – Pulmonology",
     "300 mg SC", "Every 2 weeks", "Indefinite"),

    ("omalizumab", "Xolair", "Moderate-to-severe allergic asthma", "Autoimmune – Pulmonology",
     "75–375 mg SC (IgE- and weight-based)", "Every 2–4 weeks", "Indefinite"),
    ("omalizumab", "Xolair", "Chronic spontaneous urticaria", "Autoimmune – Dermatology",
     "150 or 300 mg SC", "Every 4 weeks", "Indefinite (while disease is active)"),
    ("omalizumab", "Xolair", "Nasal polyps / CRSwNP", "Autoimmune – Pulmonology",
     "75–600 mg SC (IgE/weight-based)", "Every 2–4 weeks", "Indefinite"),
    ("omalizumab", "Xolair", "IgE-mediated food allergy (multi-food)", "Allergy / Immunology",
     "75–600 mg SC (IgE/weight-based)", "Every 2–4 weeks", "Indefinite (ongoing protection)"),

    ("mepolizumab", "Nucala", "Severe eosinophilic asthma", "Autoimmune – Pulmonology",
     "100 mg SC", "Every 4 weeks", "Indefinite"),
    ("mepolizumab", "Nucala", "EGPA (eosinophilic granulomatosis with polyangiitis)", "Autoimmune – Rheumatology",
     "300 mg SC (3 × 100 mg)", "Every 4 weeks", "Indefinite"),
    ("mepolizumab", "Nucala", "Hypereosinophilic syndrome (HES)", "Hematology – Rare Blood",
     "300 mg SC (3 × 100 mg)", "Every 4 weeks", "Indefinite"),
    ("mepolizumab", "Nucala", "CRSwNP", "Autoimmune – Pulmonology",
     "100 mg SC", "Every 4 weeks", "Indefinite"),

    ("benralizumab", "Fasenra", "Severe eosinophilic asthma", "Autoimmune – Pulmonology",
     "30 mg SC q4w ×3 doses (induction)", "Every 8 weeks (maintenance)", "Indefinite"),

    ("tezepelumab", "Tezspire", "Severe asthma (uncontrolled)", "Autoimmune – Pulmonology",
     "210 mg SC", "Every 4 weeks", "Indefinite"),

    ("depemokimab", "Nuraev (Asthma) / Nucala Ultra", "Severe eosinophilic asthma / EGPA", "Autoimmune – Pulmonology",
     "100 mg SC", "Every 6 months", "Indefinite (longest-acting IL-5 inhibitor)"),

    ("peanut (arachis hypogaea) allergen powder", "Palforzia", "Peanut allergy (desensitization)", "Allergy / Immunology",
     "Gradual oral up-titration to 300 mg/day maintenance", "Daily oral dosing", "≥3 years (lifelong maintenance while on therapy)"),
    ("short ragweed pollen allergen extract", "Grastek / Ragwitek", "Ragweed allergic rhinitis", "Allergy / Immunology",
     "1 tablet (6 Amb a 1-U) sublingual daily", "Daily", "3–5 years (standard SLIT course)"),

    # ══ AUTOIMMUNE – NEUROLOGY ════════════════════════════════════════════════
    ("ofatumumab", "Kesimpta", "Relapsing multiple sclerosis", "Neurology – Demyelinating",
     "20 mg SC at wk 0, 1, 2; then 20 mg", "Every 4 weeks", "Indefinite"),

    ("natalizumab-sztn", "Tysabri", "Relapsing multiple sclerosis", "Neurology – Demyelinating",
     "300 mg IV", "Every 4 weeks", "Indefinite (JC virus monitoring required)"),
    ("natalizumab-sztn", "Tysabri", "Crohn's disease", "Autoimmune – Gastroenterology",
     "300 mg IV", "Every 4 weeks", "Indefinite"),

    ("ocrelizumab and hyaluronidase-ocsq", "Ocrevus / Ocrevus Zunovo", "Relapsing MS", "Neurology – Demyelinating",
     "600 mg IV or 920 mg SC", "Every 6 months", "Indefinite"),
    ("ocrelizumab and hyaluronidase-ocsq", "Ocrevus / Ocrevus Zunovo", "Primary progressive MS (PPMS)", "Neurology – Demyelinating",
     "600 mg IV or 920 mg SC", "Every 6 months", "Indefinite"),

    ("ublituximab-xiiy", "Briumvi", "Relapsing multiple sclerosis", "Neurology – Demyelinating",
     "150 mg IV then 450 mg IV", "Every 6 months", "Indefinite"),

    ("satralizumab-mwge", "Enspryng", "NMOSD (AQP4-IgG+)", "Neurology – Demyelinating",
     "120 mg SC at wk 0, 2, 4; then 120 mg", "Every 4 weeks", "Indefinite"),

    ("inebilizumab-cdon", "Uplizna", "NMOSD", "Neurology – Demyelinating",
     "300 mg IV ×2 doses (2 wks apart induction)", "300 mg every 6 months", "Indefinite"),

    ("efgartigimod alfa-fcab", "Vyvgart", "Generalized myasthenia gravis (gMG)", "Neurology – Neuromuscular",
     "10 mg/kg IV weekly ×4 doses per cycle", "Repeat cycles every 4–8 weeks based on response", "Indefinite cycling"),

    ("efgartigimod alfa and hyaluronidase", "Vyvgart Hytrulo", "Generalized myasthenia gravis", "Neurology – Neuromuscular",
     "1000 mg/11,250 U SC weekly ×4 per cycle", "Repeat cycles every 4–8 weeks", "Indefinite"),

    ("rozanolixizumab", "Rystiggo", "Generalized myasthenia gravis", "Neurology – Neuromuscular",
     "7 mg/kg SC weekly ×6 weeks per cycle", "Repeat cycles as needed", "Indefinite"),

    ("nipocalimab", "Imaavy", "Generalized myasthenia gravis", "Neurology – Neuromuscular",
     "30 mg/kg IV loading; then 15 mg/kg", "Every 2 weeks", "Indefinite"),

    ("anifrolumab", "Saphnelo", "Systemic lupus erythematosus (SLE)", "Autoimmune – Rheumatology",
     "300 mg IV", "Every 4 weeks", "Indefinite"),

    ("axatilimab-csfr", "Niktimvo", "Chronic graft-versus-host disease (cGVHD)", "Hematology – Rare Blood",
     "0.3 mg/kg IV", "Every 2 weeks", "Indefinite (while cGVHD persists)"),

    ("sibeprenlimab-szsi", "Vrumvit", "IgA nephropathy (IgAN)", "Nephrology",
     "3 mg/kg SC", "Every 4 weeks", "Indefinite (progressive disease)"),

    ("ropeginterferon alfa-2b-njft", "Besremi", "Polycythemia vera (PV)", "Hematology – Myeloproliferative",
     "100–500 mcg SC (titrated)", "Every 2 weeks", "Indefinite"),

    # ══ COMPLEMENT DISORDERS ══════════════════════════════════════════════════
    ("eculizumab", "Soliris", "Paroxysmal nocturnal hemoglobinuria (PNH)", "Hematology – Complement",
     "600 mg IV q7d ×4; 900 mg at wk 5; then 900 mg", "Every 14 days", "Lifelong"),
    ("eculizumab", "Soliris", "Atypical hemolytic uremic syndrome (aHUS)", "Hematology – Complement",
     "900 mg IV q7d ×4; 1200 mg at wk 5; then 1200 mg", "Every 14 days", "Lifelong (or until sustained remission)"),
    ("eculizumab", "Soliris", "Generalized myasthenia gravis (refractory)", "Neurology – Neuromuscular",
     "900 mg IV q7d ×4; 1200 mg at wk 5; then 1200 mg", "Every 14 days", "Indefinite"),
    ("eculizumab", "Soliris", "NMOSD (AQP4-IgG+)", "Neurology – Demyelinating",
     "900 mg IV q7d ×4; 1200 mg at wk 5; then 1200 mg", "Every 2 weeks", "Indefinite"),

    ("ravulizumab", "Ultomiris", "Paroxysmal nocturnal hemoglobinuria (PNH)", "Hematology – Complement",
     "2400–3000 mg IV (weight-based loading); then 3000 mg", "Every 8 weeks", "Lifelong"),
    ("ravulizumab", "Ultomiris", "Atypical HUS (aHUS)", "Hematology – Complement",
     "2400–3000 mg IV (loading); then 3000 mg", "Every 8 weeks", "Lifelong"),
    ("ravulizumab", "Ultomiris", "Generalized myasthenia gravis", "Neurology – Neuromuscular",
     "2700–3000 mg IV (loading); then 3000 mg", "Every 8 weeks", "Indefinite"),
    ("ravulizumab", "Ultomiris", "NMOSD", "Neurology – Demyelinating",
     "2700–3000 mg IV (loading); then 3000 mg", "Every 8 weeks", "Indefinite"),

    ("crovalimab-akkz", "Piasky", "Paroxysmal nocturnal hemoglobinuria (PNH)", "Hematology – Complement",
     "341 mg IV ×1; 170 mg SC ×4 weekly; then 340 mg SC", "Every 4 weeks", "Lifelong"),

    ("sutimlimab-jome", "Enjaymo", "Cold agglutinin disease (CAD)", "Hematology – Complement",
     "6500 mg (<75 kg) or 7500 mg (≥75 kg) IV", "Every 2 weeks", "Indefinite"),

    ("pozelimab-bbfg", "Veopoz", "CHAPLE disease (CD55 deficiency)", "Hematology – Complement",
     "30 mg/kg IV loading; then 12 mg/kg SC", "Once weekly", "Lifelong (ultra-rare)"),

    # ══ HEMOPHILIA / COAGULATION ══════════════════════════════════════════════
    ("emicizumab", "Hemlibra", "Hemophilia A with inhibitors (prophylaxis)", "Hematology – Hemophilia",
     "3 mg/kg SC q1w ×4 (loading); then 1.5 mg/kg q1w", "Weekly (or 3 mg/kg q2w or 6 mg/kg q4w)", "Lifelong"),
    ("emicizumab", "Hemlibra", "Hemophilia A without inhibitors (prophylaxis)", "Hematology – Hemophilia",
     "Same loading/maintenance dosing as above", "Weekly / biweekly / monthly options", "Lifelong"),

    ("concizumab", "Alhemo", "Hemophilia A or B with inhibitors", "Hematology – Hemophilia",
     "0.2 mg/kg SC daily", "Once daily", "Lifelong"),

    ("marstacimab", "Marstacimab (trade name pending)", "Hemophilia A / B (with or without inhibitors)", "Hematology – Hemophilia",
     "~300 mg SC loading; then 150–300 mg", "Weekly", "Lifelong"),

    ("antihemophilic factor (recombinant), rAHF", "Advate / Kogenate / Kovaltry", "Hemophilia A (prophylaxis)", "Hematology – Hemophilia",
     "20–40 IU/kg IV", "Every 2–3 days", "Lifelong"),

    ("antihemophilic factor (recombinant), fc", "Eloctate / Elocta", "Hemophilia A (prophylaxis, extended half-life)", "Hematology – Hemophilia",
     "25–65 IU/kg IV", "Every 3–5 days", "Lifelong"),

    ("antihemophilic factor (recombinant), pegylated-aucl", "Adynovate / Jivi", "Hemophilia A (prophylaxis)", "Hematology – Hemophilia",
     "40–60 IU/kg IV", "Twice weekly", "Lifelong"),

    ("coagulation factor ix (recombinant), glycopegylated", "Rebinyn / Refixia", "Hemophilia B (prophylaxis)", "Hematology – Hemophilia",
     "40 IU/kg IV", "Once weekly", "Lifelong"),

    ("coagulation factor viia (recombinant)", "Sevenfact / NovoSeven", "Hemophilia A/B with inhibitors (prophylaxis)", "Hematology – Hemophilia",
     "90 mcg/kg IV q2h until hemostasis (acute); prophylaxis varies", "Per bleed (on-demand); prophylaxis daily/twice weekly", "Lifelong (on-demand or prophylaxis)"),

    ("coagulation factor viia (recombinant)-jncw", "Alhemo / Pfizer rFVIIa", "Hemophilia A/B with inhibitors", "Hematology – Hemophilia",
     "Varies by indication", "Daily to weekly SC (prophylaxis)", "Lifelong"),

    ("lanadelumab", "Takhzyro", "Hereditary angioedema (HAE) – attack prevention", "Rare / Orphan – Immunology",
     "300 mg SC", "Every 2 weeks (may extend to q4w after 6 months)", "Indefinite"),

    ("garadacimab", "Garadacimab (trade name TBD)", "Hereditary angioedema (HAE) prevention", "Rare / Orphan – Immunology",
     "200 mg SC", "Once monthly", "Indefinite"),

    # ══ OPHTHALMOLOGY ═════════════════════════════════════════════════════════
    ("ranibizumab", "Lucentis", "Neovascular (wet) AMD", "Ophthalmology",
     "0.5 mg intravitreal injection", "Monthly (treat-and-extend after stabilization)", "Indefinite"),
    ("ranibizumab", "Lucentis", "Diabetic macular edema (DME)", "Ophthalmology",
     "0.3 mg intravitreal injection", "Monthly (or PRN)", "Indefinite (while active)"),
    ("ranibizumab", "Lucentis", "Retinal vein occlusion (BRVO / CRVO)", "Ophthalmology",
     "0.5 mg intravitreal injection", "Monthly ×6, then PRN", "Indefinite (chronic/recurrent)"),
    ("ranibizumab", "Lucentis", "Diabetic retinopathy", "Ophthalmology",
     "0.3 mg intravitreal injection", "Monthly", "Indefinite"),

    ("brolucizumab-dbll", "Beovu", "Neovascular (wet) AMD", "Ophthalmology",
     "6 mg intravitreal injection (monthly ×3 loading)", "Every 8–12 weeks (T&E)", "Indefinite"),
    ("brolucizumab-dbll", "Beovu", "Diabetic macular edema (DME)", "Ophthalmology",
     "6 mg intravitreal injection (monthly ×6 loading)", "Every 8–12 weeks (T&E)", "Indefinite"),

    ("aflibercept", "Eylea / Eylea HD", "Neovascular (wet) AMD", "Ophthalmology",
     "2 mg intravitreal (monthly ×3); or 8 mg monthly ×4 (HD)", "Every 8 weeks (standard) / up to every 16 weeks (HD T&E)", "Indefinite"),
    ("aflibercept", "Eylea / Eylea HD", "Diabetic macular edema (DME)", "Ophthalmology",
     "2 mg intravitreal monthly ×5, then q8w", "Every 8 weeks", "Indefinite"),
    ("aflibercept", "Eylea / Eylea HD", "Macular edema from retinal vein occlusion (RVO)", "Ophthalmology",
     "2 mg intravitreal monthly ×6, then PRN", "Monthly / PRN", "Indefinite"),
    ("aflibercept", "Eylea", "Diabetic retinopathy (all DR)", "Ophthalmology",
     "2 mg intravitreal monthly ×5", "Every 8 weeks", "Indefinite"),

    ("faricimab", "Vabysmo", "Neovascular (wet) AMD", "Ophthalmology",
     "6 mg intravitreal monthly ×4 (loading)", "Up to every 16 weeks (treat-and-extend)", "Indefinite"),
    ("faricimab", "Vabysmo", "Diabetic macular edema (DME)", "Ophthalmology",
     "6 mg intravitreal monthly ×4 (loading)", "Up to every 16 weeks (T&E)", "Indefinite"),

    # ══ ENDOCRINOLOGY – DIABETES ══════════════════════════════════════════════
    ("insulin lispro", "Humalog / Admelog / Lyumjev", "Type 1 diabetes mellitus", "Endocrinology – Diabetes",
     "0.5–1 IU/kg/day total; mealtime dose ~0.1–0.2 IU/kg", "Multiple daily injections (or continuous pump)", "Lifelong"),
    ("insulin lispro", "Humalog / Admelog", "Type 2 diabetes mellitus", "Endocrinology – Diabetes",
     "4–10 IU per meal (initial), titrate", "With meals, as prescribed", "Lifelong (or while required)"),

    ("insulin glargine", "Lantus / Toujeo / Basaglar", "Type 1 diabetes mellitus", "Endocrinology – Diabetes",
     "0.2–0.4 IU/kg SC once daily", "Once daily (any time, consistent)", "Lifelong"),
    ("insulin glargine", "Lantus / Toujeo", "Type 2 diabetes mellitus", "Endocrinology – Diabetes",
     "0.2 IU/kg once daily (starting); titrate to FBG target", "Once daily", "Lifelong"),

    ("insulin aspart", "NovoLog / NovoRapid / Fiasp", "Type 1 diabetes mellitus", "Endocrinology – Diabetes",
     "~5–10 IU per meal or per 15 g carbohydrate (individualized)", "Before each meal", "Lifelong"),
    ("insulin aspart", "NovoLog / Fiasp", "Type 2 diabetes mellitus", "Endocrinology – Diabetes",
     "4–10 IU per meal (starting), titrate", "With meals", "Lifelong (or while required)"),

    ("insulin icodec", "Awiqli", "Type 2 diabetes mellitus", "Endocrinology – Diabetes",
     "~70% of total daily insulin dose equivalent SC", "Once weekly", "Lifelong"),

    ("dulaglutide", "Trulicity", "Type 2 diabetes mellitus", "Endocrinology – Diabetes",
     "0.75 mg SC (starting); up to 4.5 mg weekly", "Once weekly", "Indefinite"),
    ("dulaglutide", "Trulicity", "Cardiovascular risk reduction (T2DM with CVD)", "Endocrinology – Diabetes",
     "0.75–1.5 mg SC weekly", "Once weekly", "Indefinite"),

    # ══ ENDOCRINOLOGY – GROWTH DISORDERS ═════════════════════════════════════
    ("somapacitan", "Sogroya", "Adult growth hormone deficiency (AGHD)", "Endocrinology – Growth",
     "1.5–8 mg SC (individualized, titrate)", "Once weekly", "Indefinite (adult GHD)"),
    ("somapacitan", "Sogroya", "Pediatric growth hormone deficiency", "Endocrinology – Growth",
     "0.16 mg/kg SC weekly (titrate)", "Once weekly", "Until adequate adult height"),

    ("lonapegsomatropin", "Skytrofa", "Pediatric growth hormone deficiency", "Endocrinology – Growth",
     "0.24 mg/kg SC", "Once weekly", "Until adequate adult height (years)"),

    ("somatrogon", "Ngenla", "Pediatric growth hormone deficiency", "Endocrinology – Growth",
     "0.66 mg/kg SC", "Once weekly", "Until adequate adult height (years)"),

    ("tesamorelin", "Egrifta WR", "HIV-associated lipodystrophy (abdominal fat excess)", "Endocrinology – Metabolic",
     "2 mg SC", "Once daily", "Indefinite (fat accumulates on discontinuation)"),

    # ══ ENDOCRINOLOGY – LIPID / CARDIOVASCULAR ═══════════════════════════════
    ("evinacumab", "Evkeeza", "Homozygous familial hypercholesterolemia (HoFH)", "Endocrinology – Lipid",
     "15 mg/kg IV", "Every 4 weeks", "Indefinite"),

    ("lerodalcibep-liga", "Lerodalcibep (Lepodisiran/approved name)", "LDL-C reduction (HeFH / ASCVD)", "Endocrinology – Lipid",
     "300 mg SC", "Once monthly", "Indefinite"),

    # ══ BONE / OSTEOPOROSIS ══════════════════════════════════════════════════
    ("denosumab", "Prolia", "Postmenopausal osteoporosis", "Bone / Metabolic",
     "60 mg SC", "Every 6 months", "Indefinite (rebound fracture risk if stopped without follow-on therapy)"),
    ("denosumab", "Prolia", "Glucocorticoid-induced osteoporosis", "Bone / Metabolic",
     "60 mg SC", "Every 6 months", "Indefinite while on glucocorticoids"),
    ("denosumab", "Prolia", "Osteoporosis in men at high fracture risk", "Bone / Metabolic",
     "60 mg SC", "Every 6 months", "Indefinite"),

    # ══ ANEMIA / HEMATOPOIETIC ════════════════════════════════════════════════
    ("epoetin alfa", "Epogen / Procrit", "Anemia of chronic kidney disease (dialysis)", "Hematology – Anemia",
     "50–300 IU/kg IV/SC", "3 times per week", "Indefinite (until transplant or change in therapy)"),
    ("epoetin alfa", "Epogen / Procrit", "Anemia of CKD (non-dialysis)", "Hematology – Anemia",
     "50–200 IU/kg SC", "3 times per week", "Indefinite"),

    ("filgrastim", "Neupogen / Granix", "Severe chronic neutropenia (SCN)", "Hematology – Rare Blood",
     "6–12 mcg/kg SC daily", "Daily", "Lifelong (congenital neutropenia)"),

    # ══ NEUROLOGY – NEURODEGENERATION ════════════════════════════════════════
    ("lecanemab", "Leqembi", "Early Alzheimer's disease (mild cognitive impairment / mild AD)", "Neurology – Neurodegeneration",
     "10 mg/kg IV", "Every 2 weeks", "Indefinite (ongoing amyloid clearance and monitoring)"),

    ("aducanumab", "Aduhelm", "Early Alzheimer's disease", "Neurology – Neurodegeneration",
     "1–10 mg/kg IV (titrating protocol over ~6 months)", "Every 4 weeks", "Indefinite"),

    ("donanemab-azbt", "Kisunla", "Early symptomatic Alzheimer's disease", "Neurology – Neurodegeneration",
     "700 mg IV q4w ×3 doses; then 1400 mg IV", "Every 4 weeks", "Until amyloid plaque clearance (~12–18 months); may discontinue after clearance"),

    ("eptinezumab-jjmr", "Vyepti", "Episodic migraine prevention", "Neurology – Pain / Headache",
     "100 mg IV (or 300 mg in high-frequency)", "Every 3 months", "Indefinite (migraine is chronic)"),
    ("eptinezumab-jjmr", "Vyepti", "Chronic migraine prevention", "Neurology – Pain / Headache",
     "100–300 mg IV", "Every 3 months", "Indefinite"),

    # ══ PULMONARY ARTERIAL HYPERTENSION ══════════════════════════════════════
    ("sotatercept", "Winrevair", "Pulmonary arterial hypertension (PAH) – WHO Group I", "Cardiovascular / Pulmonary",
     "0.3 mg/kg SC (titrate up to 0.7 mg/kg)", "Every 3 weeks", "Indefinite (progressive disease)"),

    # ══ ENZYME REPLACEMENT THERAPY ═══════════════════════════════════════════
    ("sacrosidase", "Sucraid", "Congenital sucrase-isomaltase deficiency (CSID)", "Enzyme Deficiency",
     "1–2 mL (8500 IU/mL) per meal (weight-adjusted)", "With every meal", "Lifelong"),

    ("pancrelipase", "Creon / Zenpep / Pancreaze", "Exocrine pancreatic insufficiency (EPI)", "Enzyme Deficiency",
     "500–2500 lipase IU/kg per meal (individualized)", "With every meal and snack", "Lifelong"),

    ("pegunigalsidase alfa", "Elfabrio", "Fabry disease", "Enzyme Deficiency",
     "1 mg/kg IV", "Every 2 weeks", "Lifelong"),

    ("velmanase alfa-tycv", "Lamzede", "Alpha-mannosidosis", "Enzyme Deficiency",
     "1 IU/kg IV", "Every 2 weeks", "Lifelong"),

    ("olipudase alfa", "Xenpozyme", "Acid sphingomyelinase deficiency (ASMD / NPD-A/B)", "Enzyme Deficiency",
     "3 mg/kg IV", "Every 2 weeks", "Lifelong"),

    ("avalglucosidase alfa-ngpt", "Nexviazyme", "Late-onset Pompe disease (LOPD)", "Enzyme Deficiency",
     "20 mg/kg IV", "Every 2 weeks", "Lifelong"),

    ("cipaglucosidase alfa-atga", "Pombiliti", "Late-onset Pompe disease (+miglustat)", "Enzyme Deficiency",
     "20 mg/kg IV (+ 260 mg oral miglustat 1h prior)", "Every 2 weeks", "Lifelong"),

    ("tividenofusp alfa-eknm", "Avlayah", "MPS II (Hunter syndrome)", "Enzyme Deficiency",
     "3 mg/kg IV", "Once weekly", "Lifelong"),

    ("pegzilarginase", "Loargys", "Arginase 1 deficiency (hyperargininemia)", "Enzyme Deficiency",
     "0.1 mg/kg IV (start); titrate to 0.2 mg/kg", "Once weekly", "Lifelong"),

    ("alpha", "Prolastin-C / Glassia", "Alpha-1 antitrypsin deficiency (AATD) with emphysema", "Enzyme Deficiency",
     "60 mg/kg IV", "Once weekly", "Lifelong augmentation"),

    # ══ IMMUNOGLOBULIN REPLACEMENT ════════════════════════════════════════════
    ("immune globulin intravenous, human", "Gammagard / Privigen / Gamunex / Flebogamma", "Primary immunodeficiency disease (PIDD)", "Hematology – Immunodeficiency",
     "400–600 mg/kg IV", "Every 3–4 weeks", "Lifelong"),
    ("immune globulin intravenous, human", "Gammagard / Privigen", "Chronic inflammatory demyelinating polyneuropathy (CIDP)", "Neurology – Neuromuscular",
     "1–2 g/kg IV (loading); then 0.5–1 g/kg", "Every 3–4 weeks", "Indefinite (or until CIDP remission)"),
    ("immune globulin intravenous, human", "Privigen / Gammagard", "Immune thrombocytopenic purpura (ITP) – acute", "Hematology – Rare Blood",
     "0.4–1 g/kg IV", "1–3 days (acute); repeat courses PRN", "As needed for platelet-stabilization"),

    ("immune globulin subcutaneous (human), 20% liquid", "Hizentra / Cuvitru", "Primary immunodeficiency disease", "Hematology – Immunodeficiency",
     "~0.2–0.4 g/kg total weekly dose SC (divided)", "Weekly (or every 2 weeks for facilitated SC)", "Lifelong"),
    ("immune globulin subcutaneous (human), 20% liquid", "Hizentra", "CIDP", "Neurology – Neuromuscular",
     "0.2–0.4 g/kg SC weekly", "Weekly", "Indefinite"),

    # ══ BOTULINUM TOXINS (PERIODIC LONG-TERM) ════════════════════════════════
    ("daxibotulinumtoxina", "Daxxify", "Cervical dystonia", "Neurology – Movement Disorder",
     "125–250 IU IM (injected into affected muscles)", "Every ~24 weeks (longest-acting BoNT-A)", "Indefinite (repeated every ~6 months)"),

    ("letibotulinumtoxina", "Letybo", "Glabellar (frown) lines", "Aesthetic / Neurology",
     "30–40 IU IM (5-point injection)", "Every 3–4 months", "Indefinite (periodic)"),

    # ══ INFECTIOUS DISEASE PREVENTION (SEASONAL / PERIODIC) ══════════════════
    ("nirsevimab", "Beyfortus", "RSV prevention in infants and young children", "Infectious Disease – Prevention",
     "50 mg IM (<5 kg) or 100 mg IM (≥5 kg)", "Once per RSV season", "Annual (each RSV season during high-risk years)"),

    ("clesrovimab-cfor", "Clesrovimab (approved name TBD)", "RSV prevention in infants (≤8 months at birth; ≤24 months at high risk)", "Infectious Disease – Prevention",
     "1000 mg IM", "Once per RSV season", "Annual during high-risk period"),

    # ══ REFRACTORY GOUT ══════════════════════════════════════════════════════
    ("pegloticase", "Krystexxa", "Refractory chronic gout", "Rheumatology / Metabolic",
     "8 mg IV", "Every 2 weeks", "Until therapeutic goal (months to years; may stop if serum urate normalizes)"),

    # ══ RARE / OTHER NON-ONCOLOGY LONG-TERM ══════════════════════════════════
    ("papzimeos", "PAPZIMEOS (Precigen)", "Recurrent respiratory papillomatosis (HPV-associated)", "Rare / ENT",
     "Intralesional injection (per surgical session)", "Repeated at each surgical debulking (~every 1–6 months)", "Long-term (until disease control)"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Build DataFrame
# ─────────────────────────────────────────────────────────────────────────────
cols = ["Drug (Proper Name)", "Brand Name(s)", "Disease / Indication",
        "Disease Category", "Dose", "Frequency", "Duration of Use"]
df = pd.DataFrame(ROWS, columns=cols)

print(f"Total rows: {len(df)}")
print(f"Unique drugs: {df['Drug (Proper Name)'].nunique()}")
print(f"\nDisease category breakdown:")
print(df["Disease Category"].value_counts().to_string())

df.to_csv("/Work/AI_Drug/chronic_drugs_indications.csv", index=False)
print(f"\n✓ Saved → chronic_drugs_indications.csv  ({len(df)} rows)")
