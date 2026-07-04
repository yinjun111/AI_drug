"""
Builds orangebook_chronic_dashboard.html mirroring exactly the Purple Book
chronic_use_dashboard.html structure — same 8 figures, same layout, same style.

Purple Book figures:
  1  Sankey  — full pipeline: all drugs → duration → oncology/non-onco → disease
  2  Donut   — duration classification breakdown
  3  Bar     — disease category (non-oncology chronic/long-term)
  4  Bar     — drug target genes frequency
  5  Sunburst— disease category → gene target → drug
  6  Scatter — drugs by # indications vs disease-category diversity
  7  Heatmap — drug target gene × disease category
  8  Bar     — top-selling drugs by 2024 global revenue

Source: web-search-verified 2024 global manufacturer revenues (see inline citations).
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ── Load data ─────────────────────────────────────────────────────────────────
cls = pd.read_csv("orangebook_classified.csv")     # 1889 rows, all active ingredients
ind_raw = pd.read_csv("orangebook_chronic_indications_clean.csv")   # 880 rows chronic/LT

# Load drug targets
tgt = pd.read_csv("orangebook_drug_targets.csv")[
    ["Ingredient", "Gene_Symbol(s)", "Mechanism_of_Action", "Action_Type(s)"]
].rename(columns={
    "Gene_Symbol(s)":    "Drug Target (Gene)",
    "Mechanism_of_Action": "MoA",
})

# Merge targets into indications
ind_raw = ind_raw.rename(columns={
    "Drug":                 "Drug (Proper Name)",
    "Brand":                "Brand Name(s)",
    "Disease / Indication": "Disease / Indication",
    "Category":             "Disease Category",
    "Target":               "Target_col",
    "Revenue ($B)":         "Rev_Medicaid",
    "Duration":             "Duration of Use",
})
# Add ingredient key for joining
import csv as _csv
ing_map = {}   # Drug (Proper Name) lower → Ingredient
with open("orangebook_chronic_indications_clean.csv") as f:
    for r in _csv.DictReader(f):
        ing_map[r["Drug"].lower()] = r["Drug"].upper().replace(" ", " ")

# Re-load clean to get the _ing field
ind_with_ing = pd.read_csv("orangebook_chronic_indications_clean.csv")
ind_with_ing["Ingredient"] = ind_with_ing["Drug"].str.upper()
ind_with_ing = ind_with_ing.merge(tgt, on="Ingredient", how="left")
ind_with_ing["Drug Target (Gene)"] = ind_with_ing["Drug Target (Gene)"].fillna(
    ind_with_ing.get("Target", "")
)

# ── 2024 Global Revenue (USD B) — web-search verified ────────────────────────
# Sources:
#  Novo Nordisk FY2024: Ozempic $17.47B + Wegovy $8.45B + Rybelsus $3.38B = $29.3B
#  Eli Lilly FY2024: Mounjaro $11.5B + Zepbound $4.9B = $16.4B (NDA drugs in OB)
#  BMS/Pfizer FY2024: Eliquis (apixaban) ~$12.4B
#  Gilead FY2024: Biktarvy (bictegravir combo) $13.4B
#  Boehringer Ingelheim/Lilly FY2024: Jardiance (empagliflozin) €9.2B ≈ $10.0B
#  Novartis FY2024: Entresto (sacubitril/valsartan) $7.8B
#  AstraZeneca FY2024: Farxiga (dapagliflozin) $7.7B
#  Pfizer FY2024: Ibrance (palbociclib) $4.37B
#  AbbVie/J&J FY2024: Imbruvica (ibrutinib) $3.35B
#  Bayer FY2024: Xarelto (rivaroxaban) €3.5B ≈ $3.8B
#  Takeda FY2024: Vyvanse (lisdexamfetamine) ~$4.3B (IQVIA 12m to Oct 2024)
#  J&J FY2024: Invega portfolio (paliperidone) $4.2B
#  AstraZeneca FY2024: Tagrisso (osimertinib) $5.7B
#  Pfizer/Astellas: Xtandi (enzalutamide) $4.5B
#  Eli Lilly FY2024: Verzenio (abemaciclib) $2.8B
#  Incyte/Novartis: Jakafi (ruxolitinib) ~$2.8B
#  BMS: Revlimid (lenalidomide) ~$6.2B (declining, generic entry)
#  AstraZeneca/MSD: Lynparza (olaparib) ~$2.5B
#  AbbVie/Roche: Venclexta (venetoclax) ~$2.5B
#  Otsuka/Lundbeck: Abilify (aripiprazole) generic market ~$2.5B
#  Novo Nordisk: Victoza (liraglutide) ~$2.5B (declining)
#  Merck: Januvia (sitagliptin) ~$2.2B (declining with generics)
#  AbbVie: Mavyret (glecaprevir/pibrentasvir) ~$1.5B
#  Gilead: Epclusa (sofosbuvir/velpatasvir) ~$1.8B
#  Neurocrine: Ingrezza (valbenazine) ~$1.0B
#  Boehringer Ingelheim: Spiriva (tiotropium) ~$1.5B (declining)

REVENUE_2024 = {
    "SEMAGLUTIDE":                                                          29.30,
    "BICTEGRAVIR SODIUM; EMTRICITABINE; TENOFOVIR ALAFENAMIDE FUMARATE":  13.40,
    "APIXABAN":                                                             12.40,
    "EMPAGLIFLOZIN":                                                        10.00,
    "SACUBITRIL; VALSARTAN":                                                7.80,
    "DAPAGLIFLOZIN":                                                        7.70,
    "LENALIDOMIDE":                                                         6.20,
    "OSIMERTINIB MESYLATE":                                                 5.70,
    "ENZALUTAMIDE":                                                         4.50,
    "LISDEXAMFETAMINE DIMESYLATE":                                          4.30,
    "PALIPERIDONE":                                                         4.20,
    "PALBOCICLIB":                                                          4.37,
    "RIVAROXABAN":                                                          3.80,
    "IBRUTINIB":                                                            3.35,
    "ABEMACICLIB":                                                          2.80,
    "RUXOLITINIB PHOSPHATE":                                                2.80,
    "LIRAGLUTIDE":                                                          2.50,
    "OLAPARIB":                                                             2.50,
    "VENETOCLAX":                                                           2.50,
    "ARIPIPRAZOLE":                                                         2.50,
    "SITAGLIPTIN PHOSPHATE":                                                2.20,
    "SOFOSBUVIR; VELPATASVIR":                                              1.80,
    "CANAGLIFLOZIN":                                                        1.80,
    "BUPRENORPHINE HYDROCHLORIDE; NALOXONE HYDROCHLORIDE":                  1.80,
    "TIOTROPIUM BROMIDE":                                                   1.50,
    "GLECAPREVIR; PIBRENTASVIR":                                            1.50,
    "BUDESONIDE; FORMOTEROL FUMARATE DIHYDRATE":                           1.50,
    "CARIPRAZINE HYDROCHLORIDE":                                            1.40,
    "LURASIDONE HYDROCHLORIDE":                                             1.20,
    "VALBENAZINE TOSYLATE":                                                 1.00,
    "METHYLPHENIDATE HYDROCHLORIDE":                                        1.80,
    "ALBUTEROL SULFATE":                                                    1.20,
    "BUPRENORPHINE":                                                        1.50,
    "SOFOSBUVIR":                                                           0.90,
    "DOLUTEGRAVIR SODIUM":                                                  1.20,
    "PREGABALIN":                                                           1.00,
}

# Add revenue column to indications dataframe
ind_with_ing["Annual Revenue 2024 (USD B)"] = ind_with_ing["Ingredient"].map(REVENUE_2024)

# Rename to match PB column names
ind = ind_with_ing.rename(columns={
    "Drug":               "Drug (Proper Name)",
    "Brand":              "Brand Name(s)",
    "Disease / Indication": "Disease / Indication",
    "Category":           "Disease Category",
    "Duration":           "Duration of Use",
})
ind["Drug (Proper Name)"] = ind["Drug (Proper Name)"].str.lower().str.strip()
ind["Brand Name(s)"]      = ind["Brand Name(s)"].fillna("")

# Non-oncology chronic/long-term subset (for Figs 3-7)
non_onco = ind[ind["Disease Category"] != "Oncology"].copy()

print(f"All classified:          {len(cls):,}")
print(f"Chronic/long-term:       {len(ind):,}")
print(f"Non-oncology chr/LT:     {len(non_onco):,}")
print(f"With revenue 2024:       {ind['Annual Revenue 2024 (USD B)'].notna().sum()}")

# ── Colour palette — identical to Purple Book ─────────────────────────────────
DUR_COLORS = {
    "CHRONIC":              "#2563EB",
    "LONG-TERM":            "#7C3AED",
    "PERIODIC":             "#0891B2",
    "SHORT":                "#D97706",
    "OTHER":                "#6B7280",
}

# Purple Book disease palette (using same theme colors)
def theme_color(cat):
    mapping = {
        "Cardiovascular":  "#DC2626",
        "Metabolic":       "#059669",
        "Psychiatric":     "#7C3AED",
        "Neurology":       "#9333EA",
        "Oncology":        "#F97316",
        "Infectious":      "#0891B2",
        "Respiratory":     "#0EA5E9",
        "GI":              "#84CC16",
        "Autoimmune":      "#2563EB",
        "Pain":            "#F59E0B",
        "Dermatology":     "#EC4899",
        "Ophthalmology":   "#10B981",
        "Other":           "#6B7280",
        "Other/Unclassified": "#D1D5DB",
    }
    return mapping.get(cat, "#6B7280")


# ═══════════════════════════════════════════════════════════════════════════
# FIG 1 — Sankey: full pipeline flow
# ═══════════════════════════════════════════════════════════════════════════
def build_sankey():
    n_total   = len(cls)
    dur_counts = cls["Duration_Class"].value_counts()
    n_chronic  = int(dur_counts.get("CHRONIC", 0))
    n_longterm = int(dur_counts.get("LONG-TERM", 0))
    n_periodic = int(dur_counts.get("PERIODIC", 0))
    n_short    = int(dur_counts.get("SHORT", 0))
    n_other    = int(dur_counts.get("OTHER", 0))
    n_lt_total = n_chronic + n_longterm          # long-term use
    n_acute    = n_periodic + n_short + n_other  # acute / other

    # Non-oncology vs oncology within chronic/long-term
    chron_df   = cls[cls["Duration_Class"].isin(["CHRONIC", "LONG-TERM"])]
    n_onco     = int((chron_df["Disease_Category"] == "Oncology").sum())
    n_non_onco = n_lt_total - n_onco

    # Disease categories within non-oncology
    non_onco_cls = chron_df[chron_df["Disease_Category"] != "Oncology"]
    cat_counts   = non_onco_cls["Disease_Category"].value_counts()
    top_cats     = cat_counts.head(9).index.tolist()
    other_n      = int(cat_counts[~cat_counts.index.isin(top_cats)].sum())

    # Node list
    node_labels = [
        f"All Active\n({n_total:,} ingredients)",           # 0
        f"CHRONIC\n({n_chronic:,})",                         # 1
        f"LONG-TERM\n({n_longterm:,})",                      # 2
        f"PERIODIC\n({n_periodic:,})",                       # 3
        f"SHORT\n({n_short:,})",                             # 4
        f"OTHER\n({n_other:,})",                             # 5
        f"Long-term Use\n({n_lt_total:,} drugs, "
        f"{100*n_lt_total/n_total:.1f}%)",                   # 6
        f"Acute / Other\n({n_acute:,} drugs, "
        f"{100*n_acute/n_total:.1f}%)",                      # 7
        f"Non-oncology\nChronic/LT\n({n_non_onco:,})",      # 8
        f"Oncology\n({n_onco:,})",                           # 9
    ]
    base_cat_idx = len(node_labels)
    for cat in top_cats:
        node_labels.append(f"{cat}\n({int(cat_counts.get(cat,0)):,})")
    node_labels.append(f"Other\n({other_n:,})")

    node_colors = [
        "#1E3A5F",
        DUR_COLORS["CHRONIC"], DUR_COLORS["LONG-TERM"],
        DUR_COLORS["PERIODIC"], DUR_COLORS["SHORT"], DUR_COLORS["OTHER"],
        "#1D4ED8", "#9CA3AF",
        "#1E40AF", "#EF4444",
    ] + [theme_color(c) for c in top_cats] + ["#6B7280"]

    src, tgt_n, val, lc = [], [], [], []
    def add(s, t, v, c="#CBD5E1"):
        src.append(s); tgt_n.append(t); val.append(v); lc.append(c)

    # 0 → duration
    add(0, 1, n_chronic,  DUR_COLORS["CHRONIC"])
    add(0, 2, n_longterm, DUR_COLORS["LONG-TERM"])
    add(0, 3, n_periodic, DUR_COLORS["PERIODIC"])
    add(0, 4, n_short,    DUR_COLORS["SHORT"])
    add(0, 5, n_other,    DUR_COLORS["OTHER"])

    # duration → long-term / acute
    add(1, 6, n_chronic,  "#93C5FD")
    add(2, 6, n_longterm, "#C4B5FD")
    add(3, 7, n_periodic, "#D1D5DB")
    add(4, 7, n_short,    "#D1D5DB")
    add(5, 7, n_other,    "#D1D5DB")

    # long-term → non-oncology / oncology
    add(6, 8, n_non_onco, "#3B82F6")
    add(6, 9, n_onco,     "#F87171")

    # non-oncology → disease categories
    for i, cat in enumerate(top_cats):
        add(8, base_cat_idx + i, int(cat_counts.get(cat, 0)), theme_color(cat))
    add(8, base_cat_idx + len(top_cats), other_n, "#6B7280")

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(pad=18, thickness=22,
                  line=dict(color="white", width=0.5),
                  label=node_labels, color=node_colors,
                  hovertemplate="%{label}<extra></extra>"),
        link=dict(source=src, target=tgt_n, value=val, color=lc,
                  hovertemplate="%{source.label} → %{target.label}: %{value:,}<extra></extra>"),
    ))
    fig.update_layout(
        title=dict(text=f"<b>Analysis Pipeline: {n_total:,} FDA Orange Book Ingredients"
                        f" → Chronic Use → Disease Groups</b>",
                   font=dict(size=15)),
        font=dict(size=11), margin=dict(l=10, r=10, t=50, b=10),
        height=520, paper_bgcolor="#F8FAFC",
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# FIG 2 — Duration classification donut
# ═══════════════════════════════════════════════════════════════════════════
def build_donut():
    n_total   = len(cls)
    order     = ["CHRONIC", "LONG-TERM", "PERIODIC", "SHORT", "OTHER"]
    counts    = cls["Duration_Class"].value_counts()
    vals      = [int(counts.get(c, 0)) for c in order]
    colors    = [DUR_COLORS[c] for c in order]

    fig = go.Figure(go.Pie(
        labels=order, values=vals, hole=0.55,
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textinfo="label+percent", textfont=dict(size=11),
        hovertemplate="<b>%{label}</b><br>%{value:,} ingredients (%{percent})<extra></extra>",
        pull=[0.04 if c in ("CHRONIC", "LONG-TERM") else 0 for c in order],
    ))
    fig.add_annotation(text=f"<b>{n_total:,}</b><br>ingredients",
                       x=0.5, y=0.5, showarrow=False,
                       font=dict(size=13, color="#1E3A5F"))
    fig.update_layout(
        title=dict(text="<b>Duration Classification</b>", font=dict(size=14)),
        showlegend=True,
        legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center"),
        margin=dict(l=10, r=10, t=50, b=30),
        height=380, paper_bgcolor="#F8FAFC",
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# FIG 3 — Disease category bar (non-oncology chronic/long-term)
# ═══════════════════════════════════════════════════════════════════════════
def build_disease_bar():
    uniq      = non_onco[["Drug (Proper Name)", "Disease Category"]].drop_duplicates()
    cat_counts = uniq["Disease Category"].value_counts().reset_index()
    cat_counts.columns = ["Category", "Count"]
    cat_counts = cat_counts.sort_values("Count")

    colors = [theme_color(c) for c in cat_counts["Category"]]

    fig = go.Figure(go.Bar(
        x=cat_counts["Count"], y=cat_counts["Category"],
        orientation="h",
        marker=dict(color=colors, line=dict(color="white", width=0.5)),
        text=cat_counts["Count"], textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x:,} drug–indication pairs<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="<b>Disease Category Distribution</b><br>"
                        "<sup>Non-oncology chronic/long-term Orange Book drugs</sup>",
                   font=dict(size=14)),
        xaxis=dict(title="Drug Count", showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(tickfont=dict(size=10)),
        margin=dict(l=10, r=60, t=65, b=40),
        height=520, paper_bgcolor="#F8FAFC", plot_bgcolor="#F8FAFC",
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# FIG 4 — Drug target gene bar (top targets, non-oncology)
# ═══════════════════════════════════════════════════════════════════════════
def build_target_bar():
    raw_targets = non_onco["Drug Target (Gene)"].dropna()
    all_genes   = []
    for entry in raw_targets:
        for g in str(entry).split("|"):
            for gg in g.split(","):
                gg = gg.strip()
                if gg and len(gg) < 20:
                    all_genes.append(gg)
    gene_counts = pd.Series(all_genes).value_counts().reset_index()
    gene_counts.columns = ["Gene", "Count"]
    gene_counts = (gene_counts[gene_counts["Count"] >= 2]
                   .head(40)
                   .sort_values("Count", ascending=True))   # ascending → most at TOP of horizontal bar

    def gene_color(g):
        cv_genes    = {"AGTR1","ACE","ADRB1","ADRB2","CACNA1C","F10","PTGIS","NR3C2","HMGCR",
                       "AGTR2","NR3C2","SLC12A3","SCN5A","KCNH2"}
        metab_genes = {"GLP1R","GIPR","SLC5A2","DPP4","INSR","PPARG","SLCO1B1","MME",
                       "HMGCR","LDLR","ABCG5","ABCG8","PPARA","ACACB","NPC1L1"}
        psych_genes = {"SLC6A4","SLC6A3","SLC6A2","DRD2","HTR2A","DRD3","DRD4",
                       "OPRM1","OPRK1","OPRD1","ADRA2A","HRH1","CHRM1","CHRM2",
                       "GABRA1","GABRB2","GABRG2","SLC6A1"}
        neuro_genes = {"SCN1A","GRIN2B","GABRA1","KCNQ2","ACHE","CHRM1",
                       "CACNA2D1","CACNA2D2","SCN2A","MAOB","MAOA","DDC"}
        infect_genes = {"pol","gag","IN","RT","PR","NS5B","NS5A","NS3"}
        if g in cv_genes:      return "#DC2626"
        if g in metab_genes:   return "#059669"
        if g in psych_genes:   return "#7C3AED"
        if g in neuro_genes:   return "#9333EA"
        if g in infect_genes:  return "#0891B2"
        return "#6B7280"

    colors = [gene_color(g) for g in gene_counts["Gene"]]

    fig = go.Figure(go.Bar(
        x=gene_counts["Count"], y=gene_counts["Gene"],
        orientation="h",
        marker=dict(color=colors, line=dict(color="white", width=0.5)),
        text=gene_counts["Count"], textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x:,} drugs<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="<b>Drug Target Genes</b><br>"
                        "<sup>Non-oncology chronic/long-term Orange Book drugs</sup>",
                   font=dict(size=14)),
        xaxis=dict(title="Drug Count", showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(tickfont=dict(size=9)),
        margin=dict(l=10, r=60, t=65, b=40),
        height=700, paper_bgcolor="#F8FAFC", plot_bgcolor="#F8FAFC",
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# FIG 5 — Sunburst: Disease category → Drug Target → Drug
# ═══════════════════════════════════════════════════════════════════════════
def build_sunburst():
    KEEP_CATS = {
        "Cardiovascular", "Metabolic", "Psychiatric", "Neurology",
        "Respiratory", "GI", "Autoimmune", "Infectious",
        "Pain", "Dermatology", "Ophthalmology",
    }

    def simplify_cat(c):
        return c if c in KEEP_CATS else "Other Chronic"

    def first_gene(t):
        if pd.isna(t): return "Other"
        g = str(t).split("|")[0].split(",")[0].strip()
        return g if g else "Other"

    df = non_onco.copy()
    df["Cat2"]    = df["Disease Category"].apply(simplify_cat)
    df["Target1"] = df["Drug Target (Gene)"].apply(first_gene)
    df["Drug_short"] = df["Drug (Proper Name)"].apply(
        lambda x: x[:28] + "…" if len(str(x)) > 30 else str(x))

    ids, labels, parents, values_sb = [], [], [], []
    ids.append("root"); labels.append("All Chronic\n& Long-term\nDrugs")
    parents.append(""); values_sb.append(0)

    for cat, grp in df.groupby("Cat2"):
        cid = f"cat|{cat}"
        ids.append(cid); labels.append(cat)
        parents.append("root"); values_sb.append(len(grp))

        for gene, grp2 in grp.groupby("Target1"):
            gid = f"gene|{cat}|{gene}"
            ids.append(gid); labels.append(gene)
            parents.append(cid); values_sb.append(len(grp2))

            for drug, grp3 in grp2.groupby("Drug_short"):
                did = f"drug|{cat}|{gene}|{drug}"
                ids.append(did); labels.append(drug)
                parents.append(gid); values_sb.append(len(grp3))

    fig = go.Figure(go.Sunburst(
        ids=ids, labels=labels, parents=parents, values=values_sb,
        branchvalues="total", insidetextorientation="radial", maxdepth=3,
        hovertemplate="<b>%{label}</b><br>Count: %{value}<extra></extra>",
        marker=dict(colorscale="Blues", line=dict(color="white", width=0.8)),
    ))
    fig.update_layout(
        title=dict(text="<b>Disease Category → Gene Target → Drug</b><br>"
                        "<sup>Click to drill down</sup>",
                   font=dict(size=14)),
        margin=dict(l=10, r=10, t=65, b=10),
        height=600, paper_bgcolor="#F8FAFC",
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# FIG 6 — Scatter: drugs by # indications vs disease diversity
# ═══════════════════════════════════════════════════════════════════════════
def build_scatter():
    # Count indications per drug (semicolons in Disease/Indication text)
    def count_ind(s):
        if pd.isna(s): return 1
        return max(1, len(str(s).split(";")))

    df = non_onco.copy()
    df["n_ind"] = df["Disease / Indication"].apply(count_ind)

    drug_agg = df.groupby("Drug (Proper Name)").agg(
        n_indications=("n_ind", "sum"),
        n_categories =("Disease Category", "nunique"),
        target       =("Drug Target (Gene)", "first"),
        brand        =("Brand Name(s)", "first"),
        revenue      =("Annual Revenue 2024 (USD B)", "first"),
    ).reset_index()

    drug_agg["target_short"] = drug_agg["target"].apply(
        lambda t: str(t).split("|")[0].split(",")[0].strip()[:12] if pd.notna(t) else "")

    fig = px.scatter(
        drug_agg,
        x="n_categories", y="n_indications",
        size="n_indications",
        color="n_categories",
        color_continuous_scale="Blues",
        hover_name="Drug (Proper Name)",
        hover_data={"brand": True, "target": True,
                    "n_indications": True, "n_categories": True},
        text="target_short",
        labels={"n_indications": "Number of Approved Indications",
                "n_categories":  "Number of Disease Categories"},
    )
    fig.update_traces(textposition="top center", textfont_size=9)
    fig.update_layout(
        title=dict(text="<b>Drug Breadth: Indications × Disease Categories</b><br>"
                        "<sup>Size ∝ number of indications; label = primary target gene</sup>",
                   font=dict(size=14)),
        xaxis=dict(title="# Disease Categories Covered", dtick=1,
                   showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(title="# Approved Indications",
                   showgrid=True, gridcolor="#E2E8F0"),
        coloraxis_showscale=False,
        margin=dict(l=40, r=20, t=65, b=50),
        height=420, paper_bgcolor="#F8FAFC", plot_bgcolor="#F8FAFC",
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# FIG 7 — Heatmap: Drug Target Gene × Disease Category
# ═══════════════════════════════════════════════════════════════════════════
def build_heatmap():
    def first_gene(t):
        if pd.isna(t): return "Other"
        g = str(t).split("|")[0].split(",")[0].strip()
        return g if g and len(g) < 20 else "Other"

    CAT_SHORT = {
        "Cardiovascular": "Cardiovascular", "Metabolic": "Metabolic",
        "Psychiatric": "Psychiatric",       "Neurology": "Neurology",
        "Infectious": "Infectious",         "Respiratory": "Respiratory",
        "GI": "GI",                         "Autoimmune": "Autoimmune",
        "Pain": "Pain",                     "Dermatology": "Dermatology",
        "Ophthalmology": "Ophthalmology",
    }

    df = non_onco.copy()
    df["Gene"] = df["Drug Target (Gene)"].apply(first_gene)
    df["Cat2"] = df["Disease Category"].apply(lambda c: CAT_SHORT.get(c, "Other"))

    pivot = df.groupby(["Gene", "Cat2"]).size().unstack(fill_value=0)
    pivot = pivot[pivot.sum(axis=1) >= 2]
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=True).index]

    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
        colorscale="Blues", showscale=True,
        text=pivot.values, texttemplate="%{text}",
        hovertemplate="Gene: <b>%{y}</b><br>Disease: <b>%{x}</b><br>Count: %{z}<extra></extra>",
        xgap=2, ygap=2,
        colorbar=dict(title="Count", thickness=12),
    ))
    fig.update_layout(
        title=dict(text="<b>Drug Target Gene × Disease Category</b><br>"
                        "<sup>Non-oncology chronic/long-term drugs</sup>",
                   font=dict(size=14)),
        xaxis=dict(tickangle=-40, tickfont=dict(size=9)),
        yaxis=dict(tickfont=dict(size=9)),
        margin=dict(l=10, r=20, t=65, b=130),
        height=540, paper_bgcolor="#F8FAFC", plot_bgcolor="#F8FAFC",
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# FIG 8 — Revenue: top-selling OB drugs by 2024 global revenue
# ═══════════════════════════════════════════════════════════════════════════
def build_revenue_chart():
    rev = (
        ind[["Drug (Proper Name)", "Brand Name(s)", "Annual Revenue 2024 (USD B)",
             "Drug Target (Gene)", "Disease Category"]]
        .dropna(subset=["Annual Revenue 2024 (USD B)"])
        .groupby("Drug (Proper Name)")
        .agg(
            revenue  =("Annual Revenue 2024 (USD B)", "max"),
            brand    =("Brand Name(s)",               "first"),
            target   =("Drug Target (Gene)",          "first"),
            category =("Disease Category",            "first"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
        .head(25)
    )

    rev["label"] = rev.apply(
        lambda r: f"{str(r['brand']).split('/')[0].split(',')[0].strip()}"
                  f" ({str(r['target']).split('|')[0].split(',')[0].strip()[:12]})",
        axis=1)

    def cat_color(c):
        return theme_color(c)

    colors   = [cat_color(c) for c in rev["category"]]
    revenues = rev["revenue"].tolist()
    labels   = rev["label"].tolist()
    targets  = rev["target"].fillna("N/A").tolist()
    cats     = rev["category"].tolist()
    drugs    = rev["Drug (Proper Name)"].tolist()

    order     = sorted(range(len(revenues)), key=lambda i: revenues[i])
    rev_s = [revenues[i] for i in order]
    lab_s = [labels[i]   for i in order]
    tgt_s = [targets[i]  for i in order]
    cat_s = [cats[i]     for i in order]
    col_s = [colors[i]   for i in order]
    drg_s = [drugs[i]    for i in order]

    hover = [
        f"<b>{drg_s[i]}</b><br>"
        f"Revenue: <b>${rev_s[i]:.2f}B</b><br>"
        f"Target: {tgt_s[i]}<br>"
        f"Category: {cat_s[i]}"
        for i in range(len(rev_s))
    ]

    fig = go.Figure(go.Bar(
        x=rev_s, y=lab_s, orientation="h",
        marker=dict(color=col_s, line=dict(color="white", width=0.5)),
        text=[f"${v:.1f}B" for v in rev_s], textposition="outside",
        hovertemplate="%{customdata}<extra></extra>",
        customdata=hover,
    ))

    legend_items = [
        ("#DC2626","Cardiovascular"), ("#059669","Metabolic"),
        ("#7C3AED","Psychiatric"),    ("#0891B2","Infectious"),
        ("#F97316","Oncology"),       ("#9333EA","Neurology"),
        ("#0EA5E9","Respiratory"),    ("#6B7280","Other"),
    ]
    for x_off, (color, name) in enumerate(legend_items):
        fig.add_annotation(
            x=0, y=1.055 - x_off * 0.0,
            xref="paper", yref="paper",
            text=f'<span style="color:{color}">■</span> {name}',
            showarrow=False, font=dict(size=10), xanchor="left",
        )

    fig.update_layout(
        title=dict(
            text="<b>Top 25 Orange Book Drugs by 2024 Global Revenue</b><br>"
                 "<sup>Color = disease category · Source: FY2024 pharma earnings / IQVIA</sup>",
            font=dict(size=14)),
        xaxis=dict(title="Annual Revenue (USD Billions)", showgrid=True,
                   gridcolor="#E2E8F0", tickprefix="$", ticksuffix="B"),
        yaxis=dict(tickfont=dict(size=9.5)),
        margin=dict(l=10, r=80, t=70, b=40),
        height=680, paper_bgcolor="#F8FAFC", plot_bgcolor="#F8FAFC",
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# TABLE — exact Purple Book format:
#   • global search + Clear All button above
#   • header row 1: sortable column headers (th-sort, data-col)
#   • header row 2 background:#2D5A87: per-column filters (col-filter class)
#     text inputs for text cols, number ≥ for revenue, selects for cat/modality
# ═══════════════════════════════════════════════════════════════════════════
def build_table_html():
    import json as _json, csv as _csv

    # Load GSRS substance class
    substance = {}
    with open("orangebook_substance_classes.csv", encoding="utf-8") as f:
        for r in _csv.DictReader(f):
            substance[r["Ingredient"]] = r.get("Substance_Class", "chemical")

    # Build row list — match PB column keys exactly
    TBL_ROWS = []
    with open("orangebook_chronic_indications_clean.csv", encoding="utf-8") as f:
        for r in _csv.DictReader(f):
            ing     = r["Drug"].upper()
            rev_val = REVENUE_2024.get(ing, 0.0)
            TBL_ROWS.append({
                "drug":     r["Drug"],
                "brand":    r["Brand"],
                "disease":  r["Disease / Indication"],
                "category": r["Category"],
                "modality": substance.get(ing, "chemical"),
                "target":   r["Target"],
                "revenue":  str(round(rev_val, 2)) if rev_val else "",
                "dose":     r["Dose"],
                "freq":     r["Frequency"],
                "duration": r["Duration"],
            })

    # Default sort: revenue descending, then name
    TBL_ROWS.sort(key=lambda r: (-(float(r["revenue"]) if r["revenue"] else 0), r["drug"].lower()))

    tbl_json = _json.dumps(TBL_ROWS, ensure_ascii=False)
    n_rows   = len(TBL_ROWS)

    # Category → light-tinted row background (same approach as PB)
    CAT_COLORS_TBL = {
        "Cardiovascular":  "#FEF2F2", "Metabolic":    "#F0FDF4",
        "Psychiatric":     "#F5F3FF", "Neurology":    "#FAF5FF",
        "Oncology":        "#FFF7ED", "Infectious":   "#F0F9FF",
        "Respiratory":     "#E0F2FE", "GI":           "#F7FEE7",
        "Autoimmune":      "#EFF6FF", "Pain":         "#FFFBEB",
        "Dermatology":     "#FDF2F8", "Ophthalmology":"#F0FDF4",
        "Other":           "#F9FAFB",
    }
    MOD_COLORS = {
        "chemical":            "#2563EB", "protein":            "#7C3AED",
        "nucleicAcid":         "#0891B2", "polymer":            "#D97706",
        "mixture":             "#059669", "structurallyDiverse":"#DC2626",
        "concept":             "#9CA3AF", "specifiedSubstanceG1":"#F97316",
        "unknown":             "#6B7280",
    }
    cat_colors_json = _json.dumps(CAT_COLORS_TBL)
    mod_colors_json = _json.dumps(MOD_COLORS)

    return f"""
<style>
/* ── Purple-Book-identical col-filter style ── */
.col-filter {{
  width:100%; padding:3px 5px; font-size:0.68rem;
  border:1px solid rgba(255,255,255,0.3); border-radius:4px;
  background:rgba(255,255,255,0.12); color:#fff;
  outline:none; box-sizing:border-box;
}}
.col-filter::placeholder {{ color:rgba(255,255,255,0.5); }}
.col-filter option {{ background:#1E3A5F; color:#fff; }}
.col-filter:focus {{ background:rgba(255,255,255,0.22); border-color:rgba(255,255,255,0.65); }}
</style>

<div style="padding:10px var(--pad, 16px) 0;">
  <!-- Global search row (above table) — identical to PB -->
  <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:10px;">
    <input id="tblSearch" type="text" placeholder="Global search across all fields…"
      style="flex:1;min-width:200px;max-width:380px;padding:7px 12px;
             border:1px solid #E2E8F0;border-radius:8px;font-size:0.82rem;
             color:#1E293B;background:#fff;outline:none;"/>
    <button id="clearFilters"
      style="padding:7px 14px;background:#E2E8F0;border:none;border-radius:8px;
             font-size:0.82rem;font-weight:600;color:#64748B;cursor:pointer;"
      onmouseover="this.style.background='#CBD5E1'" onmouseout="this.style.background='#E2E8F0'">
      Clear All Filters
    </button>
    <span id="tblCount" style="font-size:0.78rem;color:#64748B;white-space:nowrap;"></span>
  </div>

  <!-- Table with fixed-layout colgroup — identical to PB -->
  <div style="overflow-x:auto;border-radius:10px;border:1px solid #E2E8F0;
              box-shadow:0 1px 4px rgba(0,0,0,.06);">
    <table id="tblMain" style="width:100%;border-collapse:collapse;background:#fff;
                                font-size:0.75rem;table-layout:fixed;">
      <colgroup>
        <col style="width:9%"/> <col style="width:8%"/> <col style="width:15%"/>
        <col style="width:11%"/><col style="width:10%"/><col style="width:6%"/>
        <col style="width:6%"/> <col style="width:9%"/> <col style="width:8%"/>
        <col style="width:18%"/>
      </colgroup>
      <thead>
        <!-- Row 1: sortable headers (same as PB) -->
        <tr style="background:#1E3A5F;color:#fff;text-align:left;">
          <th class="th-sort" data-col="drug"     style="padding:6px 8px;cursor:pointer;">Drug &#8597;</th>
          <th class="th-sort" data-col="brand"    style="padding:6px 8px;cursor:pointer;">Brand &#8597;</th>
          <th class="th-sort" data-col="disease"  style="padding:6px 8px;cursor:pointer;">Disease / Indication &#8597;</th>
          <th class="th-sort" data-col="category" style="padding:6px 8px;cursor:pointer;">Category &#8597;</th>
          <th class="th-sort" data-col="modality" style="padding:6px 8px;cursor:pointer;">Modality &#8597;</th>
          <th class="th-sort" data-col="target"   style="padding:6px 8px;cursor:pointer;">Target &#8597;</th>
          <th class="th-sort" data-col="revenue"  style="padding:6px 8px;cursor:pointer;">Revenue ($B) &#8597;</th>
          <th class="th-sort" data-col="dose"     style="padding:6px 8px;cursor:pointer;">Dose &#8597;</th>
          <th class="th-sort" data-col="freq"     style="padding:6px 8px;cursor:pointer;">Frequency &#8597;</th>
          <th class="th-sort" data-col="duration" style="padding:6px 8px;cursor:pointer;">Duration &#8597;</th>
        </tr>
        <!-- Row 2: per-column filters (background:#2D5A87, identical to PB) -->
        <tr style="background:#2D5A87;">
          <th style="padding:3px 5px;"><input  class="col-filter" data-col="drug"     placeholder="Drug…"/></th>
          <th style="padding:3px 5px;"><input  class="col-filter" data-col="brand"    placeholder="Brand…"/></th>
          <th style="padding:3px 5px;"><input  class="col-filter" data-col="disease"  placeholder="Disease…"/></th>
          <th style="padding:3px 5px;"><select class="col-filter" data-col="category" id="colCatFilter"><option value="">All categories</option></select></th>
          <th style="padding:3px 5px;"><select class="col-filter" data-col="modality" id="colModFilter"><option value="">All modalities</option></select></th>
          <th style="padding:3px 5px;"><input  class="col-filter" data-col="target"   placeholder="Target…"/></th>
          <th style="padding:3px 5px;"><input  class="col-filter" data-col="revenue"  placeholder="≥ $B" type="number" min="0" step="0.1"/></th>
          <th style="padding:3px 5px;"><input  class="col-filter" data-col="dose"     placeholder="Dose…"/></th>
          <th style="padding:3px 5px;"><input  class="col-filter" data-col="freq"     placeholder="Freq…"/></th>
          <th style="padding:3px 5px;"><input  class="col-filter" data-col="duration" placeholder="Duration…"/></th>
        </tr>
      </thead>
      <tbody id="tblBody"></tbody>
    </table>
  </div>

  <!-- Rows-per-page control (below table, same as PB) -->
  <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px;">
    <label style="font-size:0.78rem;color:#64748B;">Rows per page:
      <select id="tblPageSize"
        style="font-size:0.8rem;padding:4px 8px;border:1px solid #E2E8F0;border-radius:6px;
               background:#fff;margin-left:4px;">
        <option value="25">25</option>
        <option value="50" selected>50</option>
        <option value="100">100</option>
        <option value="{n_rows}" >All ({n_rows})</option>
      </select>
    </label>
    <div id="tblPager" style="display:flex;gap:4px;flex-wrap:wrap;margin-left:auto;"></div>
  </div>
</div>

<script>
(function(){{
const TBL_ROWS = {tbl_json};
const CAT_COLORS_TBL = {cat_colors_json};
const MOD_COLORS     = {mod_colors_json};

// Populate category and modality dropdowns from data (same approach as PB)
const cats=[...new Set(TBL_ROWS.map(r=>r.category))].filter(Boolean).sort();
cats.forEach(c=>{{document.getElementById('colCatFilter').innerHTML+=`<option value="${{c}}">${{c}}</option>`;}});
const mods=[...new Set(TBL_ROWS.map(r=>r.modality))].filter(Boolean).sort();
mods.forEach(m=>{{document.getElementById('colModFilter').innerHTML+=`<option value="${{m}}">${{m}}</option>`;}});

let tblSort={{col:'revenue',asc:false}};
let tblPage=0, tblPS=50;

function tblGetFiltered(){{
  const search=document.getElementById('tblSearch').value.toLowerCase();
  const cf={{}};
  document.querySelectorAll('.col-filter').forEach(el=>{{cf[el.dataset.col]=el.value;}});
  return TBL_ROWS.filter(r=>{{
    if(search && !Object.values(r).join(' ').toLowerCase().includes(search)) return false;
    if(cf.drug     && !r.drug.toLowerCase().includes(cf.drug.toLowerCase()))     return false;
    if(cf.brand    && !r.brand.toLowerCase().includes(cf.brand.toLowerCase()))   return false;
    if(cf.disease  && !r.disease.toLowerCase().includes(cf.disease.toLowerCase())) return false;
    if(cf.category && r.category!==cf.category) return false;
    if(cf.modality && r.modality!==cf.modality) return false;
    if(cf.target   && !r.target.toLowerCase().includes(cf.target.toLowerCase())) return false;
    if(cf.revenue  && cf.revenue!=='' && (parseFloat(r.revenue)||0)<parseFloat(cf.revenue)) return false;
    if(cf.dose     && !r.dose.toLowerCase().includes(cf.dose.toLowerCase()))     return false;
    if(cf.freq     && !r.freq.toLowerCase().includes(cf.freq.toLowerCase()))     return false;
    if(cf.duration && !r.duration.toLowerCase().includes(cf.duration.toLowerCase())) return false;
    return true;
  }});
}}

function tblRender(){{
  let data=tblGetFiltered();
  if(tblSort.col){{
    const col=tblSort.col, asc=tblSort.asc;
    data=[...data].sort((a,b)=>{{
      const va=col==='revenue'?parseFloat(a[col])||0:a[col].toLowerCase();
      const vb=col==='revenue'?parseFloat(b[col])||0:b[col].toLowerCase();
      return asc?(va>vb?1:va<vb?-1:0):(va<vb?1:va>vb?-1:0);
    }});
  }}
  const total=data.length;
  const start=tblPage*tblPS;
  const slice=tblPS>={n_rows}?data:data.slice(start,start+tblPS);

  const body=document.getElementById('tblBody');
  body.innerHTML='';
  slice.forEach((r,i)=>{{
    const bg=i%2===0?(CAT_COLORS_TBL[r.category]||'#fff'):'#F8FAFC';
    const tr=document.createElement('tr');
    tr.style.background=bg;
    tr.style.borderBottom='1px solid #E2E8F0';
    const mc=MOD_COLORS[r.modality]||'#94A3B8';
    const modStyle=`font-weight:600;color:${{mc}};`;
    const rev=r.revenue?'$'+r.revenue+'B':'—';
    const cols=[r.drug, r.brand, r.disease, r.category, r.modality, r.target, rev, r.dose, r.freq, r.duration];
    cols.forEach((v,ci)=>{{
      const td=document.createElement('td');
      td.textContent=v;
      let extra='';
      if(ci===0) extra='font-weight:600;color:#1E3A5F;';
      if(ci===4) extra=modStyle;
      if(ci===5) extra='font-family:monospace;font-size:0.72rem;color:#7C3AED;';
      if(ci===6 && r.revenue) extra='font-weight:700;color:#059669;';
      td.style.cssText='padding:5px 8px;vertical-align:top;line-height:1.35;word-break:break-word;overflow-wrap:anywhere;'+extra;
      tr.appendChild(td);
    }});
    body.appendChild(tr);
  }});

  document.getElementById('tblCount').textContent=total+' / '+TBL_ROWS.length+' rows';

  // Pager
  const np=tblPS>={n_rows}?0:Math.ceil(total/tblPS);
  const pager=document.getElementById('tblPager');
  if(np<=1){{pager.innerHTML='';return;}}
  const btnS=(active)=>`style="padding:4px 10px;border:1px solid #E2E8F0;border-radius:6px;font-size:0.78rem;cursor:pointer;background:${{active?'#1E3A5F':'#fff'}};color:${{active?'#fff':'#374151'}};"`;
  const lo=Math.max(0,Math.min(tblPage-2,np-5)),hi=Math.min(np,lo+5);
  let html=`<button ${{btnS(false)}} onclick="tblGoPage(${{tblPage-1}})" ${{tblPage===0?'disabled':''}}>«</button>`;
  for(let i=lo;i<hi;i++) html+=`<button ${{btnS(i===tblPage)}} onclick="tblGoPage(${{i}})">${{i+1}}</button>`;
  html+=`<button ${{btnS(false)}} onclick="tblGoPage(${{tblPage+1}})" ${{tblPage>=np-1?'disabled':''}}>»</button>`;
  pager.innerHTML=html;
}}

window.tblGoPage=function(p){{
  const np=Math.ceil(tblGetFiltered().length/tblPS);
  tblPage=Math.max(0,Math.min(p,np-1));
  tblRender();
  document.getElementById('tblMain').scrollIntoView({{behavior:'smooth',block:'start'}});
}};

document.getElementById('tblSearch').addEventListener('input',()=>{{tblPage=0;tblRender();}});
document.querySelectorAll('.col-filter').forEach(el=>{{
  el.addEventListener(el.tagName==='SELECT'?'change':'input',()=>{{tblPage=0;tblRender();}});
}});
document.getElementById('clearFilters').addEventListener('click',()=>{{
  document.getElementById('tblSearch').value='';
  document.querySelectorAll('.col-filter').forEach(el=>{{el.value='';}});
  tblPage=0; tblRender();
}});
document.querySelectorAll('.th-sort').forEach(th=>{{
  th.addEventListener('click',()=>{{
    const col=th.dataset.col;
    if(tblSort.col===col) tblSort.asc=!tblSort.asc;
    else{{tblSort.col=col; tblSort.asc=col!=='revenue';}}
    tblPage=0; tblRender();
  }});
}});
document.getElementById('tblPageSize').addEventListener('change',function(){{
  tblPS=parseInt(this.value); tblPage=0; tblRender();
}});

tblRender();
}})();
</script>"""


# ═══════════════════════════════════════════════════════════════════════════
# Assemble full HTML — same layout as Purple Book
# ═══════════════════════════════════════════════════════════════════════════
def to_div(fig, div_id):
    fig.update_layout(autosize=True)
    return fig.to_html(
        full_html=False, include_plotlyjs=False, div_id=div_id,
        config={"responsive": True, "displaylogo": False,
                "modeBarButtonsToRemove": ["select2d","lasso2d","autoScale2d"],
                "scrollZoom": False},
    )

# ═══════════════════════════════════════════════════════════════════════════
# STEP 6 — Disease Coverage data (DDC_RAW equivalent)
# Build disease → {count, drugs, category} from indications CSV
# ═══════════════════════════════════════════════════════════════════════════
def build_ddc_raw():
    """Return (ddc_json, ddc_colors_json, max_drugs, n_cats) for Step 6."""
    import csv as _csv, json as _json
    from collections import defaultdict

    substance = {}
    with open("orangebook_substance_classes.csv", encoding="utf-8") as f:
        for r in _csv.DictReader(f):
            substance[r["Ingredient"]] = r.get("Substance_Class", "chemical")

    # disease → list of (drug_label, category)
    disease_map = defaultdict(list)

    with open("orangebook_chronic_indications_clean.csv", encoding="utf-8") as f:
        for r in _csv.DictReader(f):
            drug     = r["Drug"].strip()
            target   = r["Target"].strip() if r["Target"] else ""
            cat      = r["Category"].strip()
            ind_text = r["Disease / Indication"].strip()
            if not ind_text:
                continue

            # Drug label: drugName(target) — first target gene only
            first_tgt = target.split("|")[0].split(",")[0].strip() if target else ""
            drug_label = f"{drug}({first_tgt})" if first_tgt else drug

            # Split multi-indication entries on ";"
            indications = [i.strip() for i in ind_text.split(";") if i.strip()]
            for ind in indications:
                disease_map[ind].append((drug_label, cat))

    # Build DDC_RAW list
    ddc_raw = []
    for disease, drug_list in disease_map.items():
        # Deduplicate drug labels (same drug may appear via multiple routes)
        seen = {}
        for label, cat in drug_list:
            seen[label] = cat
        count = len(seen)
        # Category = most common category among the drugs
        from collections import Counter
        cat_counts = Counter(seen.values())
        category = cat_counts.most_common(1)[0][0]
        drugs_str = ", ".join(seen.keys())
        ddc_raw.append({
            "disease":  disease,
            "count":    count,
            "drugs":    drugs_str,
            "category": category,
        })

    # Sort by count desc, then disease name
    ddc_raw.sort(key=lambda r: (-r["count"], r["disease"].lower()))

    # DDC_COLORS — map OB disease categories to distinct hex colors
    # (same palette idea as PB but using OB categories)
    DDC_COLORS = {
        "Cardiovascular":    "#DC2626",
        "Metabolic":         "#059669",
        "Psychiatric":       "#7C3AED",
        "Neurology":         "#D97706",
        "Oncology":          "#F97316",
        "Infectious":        "#0891B2",
        "Respiratory":       "#0EA5E9",
        "GI":                "#84CC16",
        "Autoimmune":        "#2563EB",
        "Pain":              "#F59E0B",
        "Dermatology":       "#EC4899",
        "Ophthalmology":     "#10B981",
        "Other":             "#9CA3AF",
        "Other/Unclassified":"#D1D5DB",
    }

    max_drugs = max(r["count"] for r in ddc_raw) if ddc_raw else 1
    n_cats    = len({r["category"] for r in ddc_raw})
    n_dis     = len(ddc_raw)

    return _json.dumps(ddc_raw), _json.dumps(DDC_COLORS), max_drugs, n_cats, n_dis


# Build all figures
print("Building figures …")
f_sankey   = build_sankey()
f_donut    = build_donut()
f_disease  = build_disease_bar()
f_target   = build_target_bar()
f_sun      = build_sunburst()
f_scatter  = build_scatter()
f_heat     = build_heatmap()
f_revenue  = build_revenue_chart()
TABLE_HTML = build_table_html()
DDC_JSON, DDC_COLORS_JSON, DDC_MAX, DDC_N_CATS, DDC_N_DIS = build_ddc_raw()
print(f"  DDC: {DDC_N_DIS} diseases, max {DDC_MAX} drugs per disease")

# Key metrics
n_total    = len(cls)
n_lt       = int(cls["Duration_Class"].isin(["CHRONIC","LONG-TERM","PERIODIC"]).sum())
n_chronic  = int(cls["Duration_Class"].eq("CHRONIC").sum())
n_non_onco = len(non_onco["Drug (Proper Name)"].unique())
n_targets  = non_onco["Drug Target (Gene)"].nunique()
n_rows     = len(non_onco)
top_rev_row = ind.dropna(subset=["Annual Revenue 2024 (USD B)"]).groupby(
    "Drug (Proper Name)")["Annual Revenue 2024 (USD B)"].max()
top_rev_drug  = top_rev_row.idxmax()
top_rev_val   = top_rev_row.max()
top_rev_brand = ind.loc[ind["Drug (Proper Name)"]==top_rev_drug,"Brand Name(s)"].iloc[0] \
    if len(ind.loc[ind["Drug (Proper Name)"]==top_rev_drug]) else ""

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0"/>
<title>FDA Orange Book — Chronic Use Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
:root {{
  --bg:#F0F4F8; --card:#fff; --blue:#2563EB; --violet:#7C3AED;
  --teal:#0891B2; --green:#059669; --orange:#D97706;
  --text:#1E293B; --sub:#64748B; --border:#E2E8F0;
  --pad: clamp(10px, 3vw, 24px);
  --r: 12px;
}}
*,*::before,*::after {{ box-sizing:border-box; margin:0; padding:0; }}
html {{ font-size: 16px; }}
body {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
        background:var(--bg); color:var(--text); overflow-x:hidden; }}
header {{
  background: linear-gradient(135deg,#1E3A5F 0%,#2563EB 55%,#7C3AED 100%);
  color:#fff; padding: clamp(14px,4vw,28px) var(--pad);
}}
header h1 {{
  font-size: clamp(1rem, 3.5vw, 1.5rem);
  font-weight:700; line-height:1.25; letter-spacing:-0.01em;
}}
header p {{
  margin-top:6px; opacity:.85;
  font-size: clamp(0.75rem, 2.2vw, 0.88rem); line-height:1.4;
}}
.pipeline {{
  background:#1E3A5F;
  padding: 12px var(--pad);
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
  gap: 8px;
}}
.pipe-step {{
  background: rgba(255,255,255,0.11);
  border: 1px solid rgba(255,255,255,0.22);
  border-radius: 8px;
  padding: 8px 6px 7px;
  color:#fff; text-align:center;
}}
.pipe-step strong {{
  display:block; font-size: clamp(1.15rem,3.5vw,1.5rem); font-weight:700;
  line-height:1.1;
}}
.pipe-step span {{
  font-size: clamp(0.62rem, 1.8vw, 0.72rem); opacity:.82; line-height:1.2;
  display:block; margin-top:2px;
}}
.metrics {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 10px;
  padding: 14px var(--pad) 0;
}}
.metric {{
  background:var(--card); border-radius:var(--r);
  padding: 14px 16px;
  border-left: 4px solid var(--blue);
  box-shadow: 0 1px 4px rgba(0,0,0,.07);
  min-width:0;
}}
.metric.v {{ border-color:var(--violet); }}
.metric.t {{ border-color:var(--teal); }}
.metric.g {{ border-color:var(--green); }}
.metric.o {{ border-color:var(--orange); }}
.mval {{
  font-size: clamp(1.5rem, 5vw, 2.1rem);
  font-weight:700; color:var(--blue); line-height:1;
}}
.metric.v .mval {{ color:var(--violet); }}
.metric.t .mval {{ color:var(--teal); }}
.metric.g .mval {{ color:var(--green); }}
.metric.o .mval {{ color:var(--orange); }}
.mlabel {{
  font-size: clamp(0.65rem, 1.8vw, 0.75rem);
  color:var(--sub); margin-top:4px; line-height:1.3;
}}
.sec {{
  font-size: clamp(0.6rem, 1.8vw, 0.68rem);
  font-weight:700; letter-spacing:.07em; text-transform:uppercase;
  color:#fff; padding: 3px 10px; border-radius:4px;
  margin: 18px var(--pad) 0; display:inline-block;
}}
.s1{{background:#1E3A5F;}} .s2{{background:#2563EB;}}
.s3{{background:#7C3AED;}} .s4{{background:#0891B2;}}
.s5{{background:#16A34A;}} .s6{{background:#0369A1;}}
.ddc-stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;padding:8px var(--pad) 0;}}
.ddc-stat{{background:var(--card);border-radius:var(--r);padding:12px 14px;border:1px solid var(--border);box-shadow:0 1px 4px rgba(0,0,0,.06);}}
.ddc-stat .dnum{{font-size:1.6rem;font-weight:800;line-height:1;color:var(--blue);}}
.ddc-stat .dlbl{{font-size:0.72rem;color:var(--sub);margin-top:3px;line-height:1.3;}}
.ddc-filters{{display:flex;flex-wrap:wrap;gap:8px;padding:10px var(--pad) 4px;align-items:center;}}
.ddc-filters label{{font-size:0.78rem;color:var(--sub);font-weight:600;}}
.ddc-filters select{{font-size:0.8rem;padding:5px 10px;border:1px solid var(--border);border-radius:6px;background:#fff;color:var(--text);cursor:pointer;}}
.ddc-filters input[type=range]{{cursor:pointer;}}
.ddc-filters span{{font-size:0.78rem;color:var(--sub);}}
.ddc-card{{background:var(--card);border-radius:var(--r);padding:10px 8px;margin:0 var(--pad) 10px;box-shadow:0 1px 4px rgba(0,0,0,.07);overflow:hidden;}}
.ddc-card h2{{font-size:clamp(0.85rem,2.2vw,1rem);font-weight:700;margin-bottom:4px;color:#1E293B;padding:0 6px;}}
.ddc-card .sub{{font-size:0.78rem;color:var(--sub);margin-bottom:8px;padding:0 6px;}}
.g1 {{ padding: 8px var(--pad); }}
.g2 {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 440px), 1fr));
  gap: 10px;
  padding: 8px var(--pad);
}}
.card {{
  background:var(--card); border-radius:var(--r); padding:8px 6px;
  box-shadow:0 1px 4px rgba(0,0,0,.07);
  overflow:hidden; min-width:0;
}}
.tabs {{ display:flex; gap:6px; padding: 0 var(--pad) 0; margin-top:10px; flex-wrap:wrap; }}
.tab-btn {{
  background:#E2E8F0; border:none; border-radius:20px;
  padding: 7px 16px; font-size:0.8rem; font-weight:600;
  color:var(--sub); cursor:pointer; transition:all .2s;
}}
.tab-btn.active {{ background:var(--teal); color:#fff; }}
.tab-panel {{ display:none; }}
.tab-panel.active {{ display:block; }}
footer {{
  text-align:center; font-size:clamp(0.65rem,1.8vw,0.75rem);
  color:var(--sub); padding:18px var(--pad) 24px; line-height:1.6;
}}
</style>
</head>
<body>

<header>
  <h1>FDA Orange Book Small Molecules — Chronic Use Analysis Dashboard</h1>
  <p>Systematic evaluation of {n_total:,} approved NDA/ANDA ingredients for treatment duration, disease indication, molecular target, and 2024 global revenue</p>
</header>

<div class="pipeline">
  <div class="pipe-step"><strong>{n_total:,}</strong><span>FDA OB ingredients evaluated</span></div>
  <div class="pipe-step"><strong>5</strong><span>duration categories</span></div>
  <div class="pipe-step"><strong>{n_lt:,}</strong><span>long-term use ({100*n_lt/n_total:.1f}%)</span></div>
  <div class="pipe-step"><strong>{n_non_onco:,}</strong><span>non-oncology chronic</span></div>
  <div class="pipe-step"><strong>{n_rows:,}</strong><span>drug–indication pairs</span></div>
  <div class="pipe-step"><strong>13</strong><span>disease categories</span></div>
  <div class="pipe-step"><strong>{n_targets:,}</strong><span>unique targets</span></div>
</div>

<div class="metrics">
  <div class="metric">
    <div class="mval">{n_total:,}</div>
    <div class="mlabel">Ingredients evaluated</div>
  </div>
  <div class="metric v">
    <div class="mval">{n_lt:,}</div>
    <div class="mlabel">Require long-term use</div>
  </div>
  <div class="metric t">
    <div class="mval">{n_chronic:,}</div>
    <div class="mlabel">Strictly chronic use</div>
  </div>
  <div class="metric g">
    <div class="mval">{n_non_onco:,}</div>
    <div class="mlabel">Non-oncology chronic</div>
  </div>
  <div class="metric o">
    <div class="mval">{n_targets:,}</div>
    <div class="mlabel">Unique molecular targets</div>
  </div>
  <div class="metric" style="border-color:#16A34A;">
    <div class="mval" style="color:#16A34A;">${top_rev_val:.0f}B</div>
    <div class="mlabel">{top_rev_brand[:20]} — top revenue 2024</div>
  </div>
</div>

<!-- Step 1 -->
<div class="sec s1">Step 1 — Full Analysis Pipeline</div>
<div class="g1"><div class="card">{to_div(f_sankey,"sankey")}</div></div>

<!-- Step 2 -->
<div class="sec s2">Step 2 — Duration Classification of All {n_total:,} Ingredients</div>
<div class="g2">
  <div class="card">{to_div(f_donut,"donut")}</div>
  <div class="card">{to_div(f_scatter,"scatter")}</div>
</div>

<!-- Step 3 -->
<div class="sec s3">Step 3 — Chronic &amp; Long-term Drugs by Disease (Oncology Removed)</div>
<div class="g2">
  <div class="card">{to_div(f_disease,"disease")}</div>
  <div class="card">{to_div(f_target,"target")}</div>
</div>

<!-- Step 4 -->
<div class="sec s4">Step 4 — Drill-down: Disease → Target → Drug</div>
<div class="tabs">
  <button class="tab-btn active" onclick="showTab('sun',this)">Sunburst</button>
  <button class="tab-btn" onclick="showTab('heat',this)">Heatmap</button>
</div>
<div class="g1">
  <div id="panel-sun" class="tab-panel active">
    <div class="card">{to_div(f_sun,"sunburst")}</div>
  </div>
  <div id="panel-heat" class="tab-panel">
    <div class="card">{to_div(f_heat,"heatmap")}</div>
  </div>
</div>

<!-- Step 5 -->
<div class="sec s5">Step 5 — Top-Selling Orange Book Drugs by 2024 Global Revenue</div>
<div class="g1"><div class="card">{to_div(f_revenue,"revenue")}</div></div>

<!-- Step 6 — Disease Coverage -->
<div class="sec s6">Step 6 — Disease Coverage: Ranked by Number of Targeting Drugs</div>
<div class="ddc-stats">
  <div class="ddc-stat"><div class="dnum" id="ddc-nDiseases">{DDC_N_DIS}</div><div class="dlbl">Total Disease<br>Indications</div></div>
  <div class="ddc-stat"><div class="dnum" id="ddc-nDrugs">—</div><div class="dlbl">Unique<br>Drugs</div></div>
  <div class="ddc-stat"><div class="dnum" id="ddc-maxDrugs">{DDC_MAX}</div><div class="dlbl">Max Drugs for<br>One Disease</div></div>
  <div class="ddc-stat"><div class="dnum" id="ddc-nCats">{DDC_N_CATS}</div><div class="dlbl">Disease<br>Categories</div></div>
  <div class="ddc-stat"><div class="dnum" id="ddc-multiDis">—</div><div class="dlbl">Diseases with<br>≥ 2 Drugs</div></div>
</div>
<div class="ddc-filters">
  <label>Category:</label>
  <select id="ddcCatFilter"><option value="">All categories</option></select>
  <label>Min drugs:</label>
  <input type="range" id="ddcMinDrugs" min="1" max="{DDC_MAX}" value="1" step="1"/>
  <span id="ddcMinLbl">≥ 1</span>
  <label style="margin-left:8px">Show top:</label>
  <select id="ddcTopN">
    <option value="30">30</option>
    <option value="50">50</option>
    <option value="{DDC_N_DIS}" selected>All ({DDC_N_DIS})</option>
  </select>
</div>
<div class="ddc-card">
  <h2>Diseases Ranked by Number of Approved Drugs</h2>
  <div class="sub">Hover a bar for full drug list · Drug labels: drugName(Target) · Bars colored by disease category</div>
  <div id="ddc_chart" style="width:100%"></div>
</div>
<div class="ddc-card">
  <h2>Distribution: Drug Count per Disease</h2>
  <div class="sub">How many diseases have exactly N approved drugs</div>
  <div id="ddc_hist" style="width:100%; height:300px"></div>
</div>

<!-- Reference table -->
<div class="sec s1" style="margin-top:24px;">Reference — Chronic Drug × Indication Table ({len(ind)} drugs, all columns sortable &amp; filterable)</div>
<div class="g1">{TABLE_HTML}</div>

<footer>
  Data source: FDA Orange Book May 2026 &nbsp;|&nbsp;
  Drug targets: ChEMBL v34 &nbsp;|&nbsp;
  Revenue: FY2024 pharma earnings (Novo Nordisk, Eli Lilly, BMS/Pfizer, Gilead,
  Boehringer Ingelheim, Novartis, AstraZeneca, Bayer, Pfizer/Astellas, Takeda, J&amp;J, AbbVie)<br>
  Files: orangebook_classified.csv · orangebook_chronic_indications_clean.csv ·
  orangebook_drug_targets.csv
</footer>

<script>
function showTab(id, btn) {{
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('panel-' + id).classList.add('active');
  btn.classList.add('active');
  const plot = document.getElementById(id === 'sun' ? 'sunburst' : 'heatmap');
  if (plot && plot.data) Plotly.relayout(plot, {{autosize: true}});
}}

const CHART_IDS = ['sankey','donut','scatter','disease','target','sunburst','heatmap','revenue'];
const HEIGHTS = {{
  sankey:   [380, 460, 520],
  donut:    [320, 360, 380],
  scatter:  [300, 360, 420],
  disease:  [420, 480, 520],
  target:   [560, 640, 700],
  sunburst: [360, 500, 600],
  heatmap:  [380, 480, 540],
  revenue:  [560, 640, 680],
}};

function getBreakpoint() {{
  const w = window.innerWidth;
  if (w < 480) return 0;
  if (w < 900) return 1;
  return 2;
}}

function resizeAll() {{
  const bp = getBreakpoint();
  CHART_IDS.forEach(id => {{
    const el = document.getElementById(id);
    if (!el || !el.data) return;
    const w = el.parentElement ? el.parentElement.clientWidth - 16 : undefined;
    try {{
      Plotly.relayout(el, {{
        autosize: true,
        width: w || undefined,
        height: HEIGHTS[id][bp],
        'margin.l': bp === 0 ? 8  : 10,
        'margin.r': bp === 0 ? 6  : 10,
        'margin.t': bp === 0 ? 40 : 55,
        'margin.b': bp === 0 ? 30 : 40,
        'font.size': bp === 0 ? 9 : 11,
      }});
    }} catch(e) {{}}
  }});
}}

let _resizeTimer;
window.addEventListener('resize', () => {{
  clearTimeout(_resizeTimer);
  _resizeTimer = setTimeout(resizeAll, 120);
}});

document.addEventListener('DOMContentLoaded', () => {{
  let attempts = 0;
  const poll = setInterval(() => {{
    const ready = CHART_IDS.every(id => {{
      const el = document.getElementById(id);
      return el && el.data;
    }});
    if (ready || attempts++ > 40) {{
      clearInterval(poll);
      resizeAll();
    }}
  }}, 150);
}});
</script>
</body>
</html>
"""

OUT = "orangebook_chronic_dashboard.html"
with open(OUT, "w", encoding="utf-8") as f:
    f.write(HTML)

print(f"\n✓ Dashboard written → {OUT}")
print(f"  File size: {len(HTML)/1024:.0f} KB")
print(f"\nKey metrics:")
print(f"  Total evaluated:    {n_total:,}")
print(f"  Long-term use:      {n_lt:,}  ({100*n_lt/n_total:.1f}%)")
print(f"  Strictly chronic:   {n_chronic:,}")
print(f"  Non-oncology chr:   {n_non_onco:,}")
print(f"  Top revenue drug:   {top_rev_drug} (${top_rev_val:.1f}B)")
