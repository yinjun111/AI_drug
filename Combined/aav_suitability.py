"""
AAV gene-therapy suitability assessment for the peptide/protein drugs in the
chronic-use dataset.

Question scored: *could this therapeutic be delivered by having an AAV vector
make the protein in the patient's own cells, instead of injecting the
manufactured molecule?*

Scoring criteria (High / Medium / Low):
  1. Gene size < 4.5 kb — the AAV single-stranded genome packages ~4.7 kb
     including ITRs/promoter/polyA, leaving ~4.5 kb for the coding sequence.
     Coding size ≈ (expressed-chain amino acids) × 3 bp.  For homodimers /
     Fc-fusions the AAV encodes ONE chain that then dimerizes, so the relevant
     ORF is the monomer.
  2. No un-encodable chemistry — a ribosome can only make natural-L-amino-acid
     polypeptides (plus natural post-translational glycosylation / disulfides /
     C-terminal amidation).  It CANNOT add PEG, fatty-acid/lipid chains,
     D-amino acids, other non-natural residues, or substitute metal cofactors.
     Half-life extensions (PEG, lipid, albumin-binding, Fc) are treated as
     *replaceable* by continuous AAV expression; chemistry that is essential to
     the pharmacophore or that makes the molecule non-ribosomal is disqualifying.
  3. Mechanism compatible with continuous secreted expression — locally
     injected toxins (botulinum) and gut-lumen / oral enzymes are mechanistically
     wrong for a secreted AAV transgene regardless of size.

High  = pure protein / Fc- or albumin-fusion, gene < 4.5 kb, natural expression
        and secretion, no essential chemistry.
Medium= encodable protein but a caveat applies (very small peptide that is hard
        to secrete alone, gene near/over capacity but with a known workaround,
        or a half-life/uptake modification the marketed product depends on).
Low   = essential un-encodable chemistry, gene well over capacity, or a
        mechanism incompatible with continuous secreted expression.

Each entry: drug_name -> (score, gene_kb, rationale)
  gene_kb = approximate coding size of the AAV transgene (expressed-chain ORF)
            in kb, or None where no single defined ORF applies (mixtures/toxins).
"""

AAV_SUITABILITY = {
    # ── High ────────────────────────────────────────────────────────────────
    "aflibercept": ("High", 1.3,
        "VEGF-Trap Fc-fusion (~1.3 kb/chain); secreted homodimer with no chemical modification. AAV-aflibercept is already in clinical trials (e.g. ADVM-022 / Ixo-vec for wet AMD)."),
    "etanercept": ("High", 1.4,
        "TNFR2-Fc fusion (~1.4 kb/chain); pure secreted protein. AAV delivery has been studied for sustained anti-TNF therapy in arthritis."),
    "dulaglutide": ("High", 0.8,
        "GLP-1-Fc fusion (~0.8 kb/chain); long action comes from the genetically-encoded Fc, not chemistry, so a cell can fully make and secrete it."),
    "sotatercept": ("High", 1.0,
        "ActRIIA-Fc fusion (~1.0 kb/chain); pure secreted protein, well suited to AAV-mediated secretion."),
    "efgartigimod alfa-fcab": ("High", 0.7,
        "Engineered IgG1 Fc fragment (~0.7 kb/chain); small, secreted, no chemical modification."),
    "efgartigimod alfa and hyaluronidase": ("High", 0.7,
        "Active is the same ~0.7 kb Fc fragment; the co-formulated hyaluronidase is only a subcutaneous-delivery excipient not needed for gene therapy."),
    "filgrastim": ("High", 0.5,
        "Recombinant G-CSF (~0.5 kb); a natural secreted cytokine that AAV can express to treat chronic neutropenia."),
    "epoetin alfa": ("High", 0.5,
        "Recombinant erythropoietin (~0.5 kb); AAV-EPO is extensively validated in animal models (controlling expression level is the main caveat)."),
    "somatrogon": ("High", 0.8,
        "Growth-hormone-CTP fusion (~0.8 kb); long action from genetically-encoded CTP peptides, no chemistry required."),
    "lerodalcibep-liga": ("High", 2.1,
        "Small anti-PCSK9 domain fused to human serum albumin (~2.1 kb); fully protein-based and secreted, suited to continuous AAV expression."),
    "alpha": ("High", 1.2,
        "Alpha-1 antitrypsin (SERPINA1, ~1.2 kb); a secreted serpin and one of the classic AAV gene-therapy targets (multiple AAV-AAT trials)."),
    "coagulation factor ix (recombinant), glycopegylated": ("High", 1.4,
        "Factor IX (~1.4 kb) is the gold-standard AAV target (FDA-approved Hemgenix); the marketed glyco-PEGylation is only a half-life add-on AAV makes unnecessary."),
    "coagulation factor viia (recombinant)": ("High", 1.4,
        "Factor VII/VIIa (~1.4 kb); a small secreted clotting factor comfortably within AAV capacity and mechanism-compatible."),
    "coagulation factor viia (recombinant)-jncw": ("High", 1.4,
        "Factor VII/VIIa (~1.4 kb); small secreted clotting factor well within AAV capacity, no chemical modification."),
    "olipudase alfa": ("High", 1.7,
        "Acid sphingomyelinase (~1.7 kb); a secreted lysosomal enzyme amenable to AAV cross-correction, with no chemical modification."),
    "velmanase alfa-tycv": ("High", 3.0,
        "Alpha-mannosidase (~3.0 kb); a natural secreted glycoprotein within AAV capacity, no chemical modification."),

    # ── Medium ──────────────────────────────────────────────────────────────
    "antihemophilic factor (recombinant), rAHF": ("Medium", 7.0,
        "Hemophilia A is a validated AAV target (FDA-approved Roctavian), but full-length Factor VIII (~7 kb) exceeds AAV capacity and requires a B-domain-deleted construct (~4.4 kb) to fit."),
    "avalglucosidase alfa-ngpt": ("Medium", 2.9,
        "The GAA gene (~2.9 kb) fits AAV and AAV-Pompe programs are in trials, but this product's synthetic bis-M6P glycan conjugation for uptake cannot be gene-encoded."),
    "cipaglucosidase alfa-atga": ("Medium", 2.9,
        "The GAA gene (~2.9 kb) fits AAV, but the product relies on optimized glycosylation plus a co-administered chaperone (miglustat)."),
    "pegunigalsidase alfa": ("Medium", 1.2,
        "Alpha-galactosidase A is small (~1.2 kb) and Fabry AAV is in trials, but this product's PEGylation and chemical cross-linking cannot be genetically encoded."),
    "tividenofusp alfa-eknm": ("Medium", 2.5,
        "Fully protein-encoded IDS-transferrin-receptor-antibody fusion (~2.5 kb) for CNS delivery; gene fits and MPS II AAV is in trials, but the complex bispecific fusion is harder to express well."),
    "ropeginterferon alfa-2b-njft": ("Medium", 0.5,
        "IFN-alpha-2b (~0.5 kb) is small and encodable and PEG only extends half-life, but continuous systemic interferon expression raises tolerability concerns."),
    "lonapegsomatropin": ("Medium", 0.6,
        "The growth-hormone base (~0.6 kb) is a clean AAV target; the TransCon PEG prodrug chemistry cannot be encoded but only provides slow release."),
    "somapacitan": ("Medium", 0.6,
        "Growth hormone (~0.6 kb) is a clean AAV target; the albumin-binding fatty acid is a half-life modification AAV would render unnecessary."),
    "insulin glargine": ("Medium", 0.3,
        "Insulin (~0.3 kb) is small and AAV-insulin is explored, but it needs proinsulin processing and, for diabetes, glucose-regulated secretion."),
    "insulin lispro": ("Medium", 0.3,
        "Insulin (~0.3 kb) is small and encodable, but requires proinsulin processing and ideally glucose-regulated secretion for diabetes."),
    "insulin aspart": ("Medium", 0.3,
        "Insulin (~0.3 kb) is small and encodable, but requires proinsulin processing and ideally glucose-regulated secretion for diabetes."),
    "insulin icodec": ("Medium", 0.3,
        "The insulin backbone is expressible; the C20 fatty-diacid (for weekly dosing) cannot be gene-encoded but is a half-life feature AAV would replace with continuous output."),
    "Exenatide Synthetic": ("Medium", 0.1,
        "39-aa exendin-4 with a natural sequence and no chemistry; AAV-exendin has been explored, but the tiny peptide is a weak standalone transgene."),
    "Teriparatide": ("Medium", 0.1,
        "Natural PTH(1-34), 34 aa; genetically encodable but too short to express and secrete efficiently on its own."),
    "Teduglutide": ("Medium", 0.1,
        "Natural-sequence GLP-2 analog of only 33 aa; encodable, yet very short peptides are hard to secrete efficiently from an AAV transgene."),
    "Calcitonin Salmon": ("Medium", 0.1,
        "32-aa natural (salmon) calcitonin; expressible in principle but very small and of non-human sequence."),

    # ── Low ─────────────────────────────────────────────────────────────────
    "Semaglutide": ("Low", None,
        "31-aa GLP-1 whose C18 fatty-diacid is essential to potency and weekly dosing; not genetically encodable and too small to be a good transgene."),
    "Liraglutide": ("Low", None,
        "31-aa GLP-1 with a C16 fatty-acid pharmacophore that cells cannot attach; unsuitable for AAV expression."),
    "Tirzepatide": ("Low", None,
        "39-aa dual GIP/GLP-1 agonist with a C20 fatty-diacid; the lipid modification cannot be gene-encoded."),
    "Lanreotide Acetate": ("Low", None,
        "8-aa cyclic somatostatin analog containing D-amino acids; chemically synthesized and not ribosomally translatable."),
    "Triptorelin Pamoate": ("Low", None,
        "10-aa GnRH analog with a non-natural D-tryptophan; cannot be produced from a gene."),
    "tesamorelin": ("Low", None,
        "44-aa GHRH analog with an N-terminal hexenoyl group; chemically modified and too small for AAV."),
    "Abaloparatide": ("Low", None,
        "34-aa synthetic PTHrP analog; a chemically manufactured short peptide with little to gain from AAV delivery."),
    "Vosoritide": ("Low", None,
        "39-aa modified CNP analog; a small synthetic peptide that makes a poor AAV transgene."),
    "Navepegritide": ("Low", None,
        "CNP peptide conjugated to a branched 40-kDa PEG; the PEG carrier cannot be genetically encoded."),
    "Palopegteriparatide": ("Low", None,
        "PTH(1-34) conjugated to 40-kDa PEG (TransCon); the PEG carrier cannot be genetically encoded."),
    "Linaclotide": ("Low", None,
        "14-aa GC-C agonist acting in the gut lumen after oral dosing; chemically synthesized and mechanistically incompatible with secreted expression."),
    "Plecanatide": ("Low", None,
        "16-aa oral GC-C agonist acting locally in the intestine; not a secreted-protein target."),
    "Ziconotide Acetate": ("Low", None,
        "25-aa synthetic omega-conotoxin delivered intrathecally to block ion channels; a disulfide-rich synthetic peptide, not an expression target."),
    "daxibotulinumtoxina": ("Low", None,
        "Bacterial neurotoxin injected locally for transient muscle paralysis; continuous AAV expression would be unsafe and mechanistically wrong."),
    "letibotulinumtoxina": ("Low", None,
        "Bacterial botulinum neurotoxin for local injection; not a candidate for sustained genetic expression."),
    "pancrelipase": ("Low", None,
        "Porcine digestive-enzyme mixture acting in the gut lumen; no single gene and the wrong delivery route for AAV."),
    "sacrosidase": ("Low", None,
        "Yeast-derived oral sucrase acting in the intestinal lumen; a non-human enzyme delivered by the wrong route for AAV."),
    "pegloticase": ("Low", None,
        "PEGylated non-human (porcine-baboon) uricase; the foreign protein plus its essential PEG make it immunogenic and non-encodable."),
    "antihemophilic factor (recombinant), fc": ("Low", 5.7,
        "Factor VIII-Fc fusion (~5.7 kb) exceeds single-AAV packaging capacity."),
    "antihemophilic factor (recombinant), pegylated-aucl": ("Low", 7.0,
        "Full-length Factor VIII (~7 kb) exceeds AAV capacity and the PEGylation cannot be gene-encoded."),
    "pegzilarginase": ("Low", None,
        "Cobalt-substituted, PEGylated arginase; both the non-natural metal substitution and the PEG are impossible to genetically encode."),
}


def get(drug: str):
    """Return (score, gene_kb, rationale) for a drug, or ('', None, '') if absent."""
    return AAV_SUITABILITY.get(drug, ("", None, ""))
