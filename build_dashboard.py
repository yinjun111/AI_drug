"""
Builds a self-contained interactive HTML dashboard covering the full
Purple Book biologic chronic-use analysis pipeline:
  208 drugs → duration classification → chronic/long-term selection
  → non-oncology filter → disease categories → drug targets & indications
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import json

# ── Load data ────────────────────────────────────────────────────────────────
cls = pd.read_csv("/Work/AI_Drug/chronic_use_classification.csv")
ind = pd.read_csv("/Work/AI_Drug/chronic_drugs_indications2.csv")

# ── Colour palette ───────────────────────────────────────────────────────────
CAT_COLORS = {
    "CHRONIC":   "#2563EB",   # blue
    "LONG-TERM": "#7C3AED",   # violet
    "PERIODIC":  "#0891B2",   # teal
    "SHORT":     "#D97706",   # amber
    "ONE-TIME":  "#6B7280",   # grey
}
DISEASE_PALETTE = px.colors.qualitative.Safe

# ═══════════════════════════════════════════════════════════════════════════
# FIG 1 — Sankey: full pipeline flow
# ═══════════════════════════════════════════════════════════════════════════
def build_sankey():
    # Nodes (order matters for layout left→right)
    node_labels = [
        # 0
        "All Evaluated\n(208 biologics)",
        # duration buckets 1-5
        "CHRONIC (84)",
        "LONG-TERM (49)",
        "PERIODIC (14)",
        "SHORT-TERM (15)",
        "ONE-TIME (46)",
        # selection 6-7
        "Long-term Use\n(147 drugs, 70.7%)",
        "Acute / One-off\n(61 drugs, 29.3%)",
        # oncology filter 8-9
        "Non-oncology\nChronic/Long-term\n(96 drugs)",
        "Oncology\nExcluded\n(51 indications)",
        # top disease groups 10-19
        "Autoimmune –\nRheumatology (29)",
        "Autoimmune –\nDermatology (21)",
        "Autoimmune –\nGastroenterology (13)",
        "Ophthalmology (12)",
        "Hematology –\nHemophilia (10)",
        "Autoimmune –\nPulmonology (10)",
        "Enzyme\nDeficiency (10)",
        "Neurology –\nDemyelinating (9)",
        "Endocrinology –\nDiabetes (9)",
        "Other (42)",
    ]

    sources, targets_s, values, link_colors = [], [], [], []

    def add(s, t, v, c="#CBD5E1"):
        sources.append(s); targets_s.append(t); values.append(v); link_colors.append(c)

    # 0 → duration buckets
    add(0, 1, 84,  CAT_COLORS["CHRONIC"])
    add(0, 2, 49,  CAT_COLORS["LONG-TERM"])
    add(0, 3, 14,  CAT_COLORS["PERIODIC"])
    add(0, 4, 15,  CAT_COLORS["SHORT"])
    add(0, 5, 46,  CAT_COLORS["ONE-TIME"])

    # duration → long-term / acute
    for src, n in [(1, 84), (2, 49), (3, 14)]:
        add(src, 6, n, "#93C5FD")
    for src, n in [(4, 15), (5, 46)]:
        add(src, 7, n, "#D1D5DB")

    # long-term → non-oncology / oncology
    add(6, 8, 96, "#3B82F6")
    add(6, 9, 51, "#F87171")

    # non-oncology → disease groups (using actual counts from ind)
    cat_counts = ind["Disease Category"].value_counts()
    # consolidate small categories into "Other"
    top_cats = [
        ("Autoimmune – Rheumatology", 10),
        ("Autoimmune – Dermatology",  11),
        ("Autoimmune – Gastroenterology", 12),
        ("Ophthalmology",             13),
        ("Hematology – Hemophilia",   14),
        ("Autoimmune – Pulmonology",  15),
        ("Enzyme Deficiency",         16),
        ("Neurology – Demyelinating", 17),
        ("Endocrinology – Diabetes",  18),
    ]
    other_total = 0
    for cat, node_idx in top_cats:
        v = int(cat_counts.get(cat, 0))
        add(8, node_idx, v, "#60A5FA")
    for cat in cat_counts.index:
        if not any(cat == c for c, _ in top_cats):
            other_total += int(cat_counts[cat])
    add(8, 19, other_total, "#60A5FA")

    node_colors = [
        "#1E3A5F",           # all drugs
        CAT_COLORS["CHRONIC"],
        CAT_COLORS["LONG-TERM"],
        CAT_COLORS["PERIODIC"],
        CAT_COLORS["SHORT"],
        CAT_COLORS["ONE-TIME"],
        "#1D4ED8",           # long-term use
        "#9CA3AF",           # acute/one-off
        "#1E40AF",           # non-oncology
        "#EF4444",           # oncology excluded
        "#0EA5E9","#0EA5E9","#0EA5E9","#0EA5E9","#0EA5E9",
        "#0EA5E9","#0EA5E9","#0EA5E9","#0EA5E9","#0EA5E9",
    ]

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=18, thickness=22,
            line=dict(color="white", width=0.5),
            label=node_labels,
            color=node_colors,
            hovertemplate="%{label}<extra></extra>",
        ),
        link=dict(
            source=sources, target=targets_s, value=values,
            color=link_colors,
            hovertemplate="%{source.label} → %{target.label}: %{value}<extra></extra>",
        ),
    ))
    fig.update_layout(
        title=dict(text="<b>Analysis Pipeline: 208 FDA Biologics → Chronic Use → Disease Groups</b>",
                   font=dict(size=15)),
        font=dict(size=11),
        margin=dict(l=10, r=10, t=50, b=10),
        height=520,
        paper_bgcolor="#F8FAFC",
    )
    return fig

# ═══════════════════════════════════════════════════════════════════════════
# FIG 2 — Duration classification donut
# ═══════════════════════════════════════════════════════════════════════════
def build_donut():
    counts = cls["Category"].value_counts()
    order  = ["CHRONIC", "LONG-TERM", "PERIODIC", "SHORT", "ONE-TIME"]
    vals   = [counts.get(c, 0) for c in order]
    colors = [CAT_COLORS[c] for c in order]

    fig = go.Figure(go.Pie(
        labels=order, values=vals,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textinfo="label+percent",
        textfont=dict(size=11),
        hovertemplate="<b>%{label}</b><br>%{value} drugs (%{percent})<extra></extra>",
        pull=[0.04 if c in ("CHRONIC", "LONG-TERM") else 0 for c in order],
    ))
    fig.add_annotation(text="<b>208</b><br>biologics", x=0.5, y=0.5,
                       showarrow=False, font=dict(size=13, color="#1E3A5F"))
    fig.update_layout(
        title=dict(text="<b>Duration Classification</b>", font=dict(size=14)),
        showlegend=True,
        legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center"),
        margin=dict(l=10, r=10, t=50, b=30),
        height=380,
        paper_bgcolor="#F8FAFC",
    )
    return fig

# ═══════════════════════════════════════════════════════════════════════════
# FIG 3 — Disease category bar (non-oncology chronic/long-term)
# ═══════════════════════════════════════════════════════════════════════════
def build_disease_bar():
    # unique drug×disease combinations
    uniq = ind[["Drug (Proper Name)", "Disease Category"]].drop_duplicates()
    cat_counts = uniq["Disease Category"].value_counts().reset_index()
    cat_counts.columns = ["Category", "Count"]
    cat_counts = cat_counts.sort_values("Count")

    # colour by broad theme
    def theme_color(cat):
        if "Rheumat" in cat or "Dermat" in cat or "Gastro" in cat or "Pulmon" in cat:
            return "#2563EB"
        if "Neurol" in cat:     return "#7C3AED"
        if "Hematol" in cat:    return "#0891B2"
        if "Endocrin" in cat:   return "#059669"
        if "Ophth" in cat:      return "#D97706"
        if "Enzyme" in cat:     return "#DC2626"
        if "Bone" in cat:       return "#92400E"
        return "#6B7280"

    colors = [theme_color(c) for c in cat_counts["Category"]]

    fig = go.Figure(go.Bar(
        x=cat_counts["Count"],
        y=cat_counts["Category"],
        orientation="h",
        marker=dict(color=colors, line=dict(color="white", width=0.5)),
        text=cat_counts["Count"],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x} drug–indication pairs<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="<b>Disease Category Distribution</b><br>"
                        "<sup>Non-oncology chronic/long-term biologics (unique drug × indication)</sup>",
                   font=dict(size=14)),
        xaxis=dict(title="Drug–Indication Pairs", showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(tickfont=dict(size=10)),
        margin=dict(l=10, r=60, t=65, b=40),
        height=520,
        paper_bgcolor="#F8FAFC",
        plot_bgcolor="#F8FAFC",
    )
    return fig

# ═══════════════════════════════════════════════════════════════════════════
# FIG 4 — Drug target gene bar chart (top targets)
# ═══════════════════════════════════════════════════════════════════════════
def build_target_bar():
    # Expand multi-target entries (e.g. "VEGFA, ANGPT2") into individual genes
    raw_targets = ind["Drug Target (Gene)"].dropna()
    all_genes = []
    for entry in raw_targets:
        for g in str(entry).split(","):
            g = g.strip()
            if g and "polyclonal" not in g and "(viral)" not in g:
                all_genes.append(g)
    gene_counts = pd.Series(all_genes).value_counts().reset_index()
    gene_counts.columns = ["Gene", "Count"]

    # colour by biological function
    def gene_color(g):
        interleukins = {"IL4R","IL5","IL5RA","IL6R","IL12B","IL13","IL17A","IL17F","IL23A","IL31RA","IL1RL2","TSLP","IGHE","IFNAR1","IFNAR2"}
        coag         = {"F7","F8","F9","F10","F12","TFPI","KLKB1"}
        complement   = {"C5","C1S"}
        ophthal      = {"VEGFA","PGF","ANGPT2"}
        endo         = {"INSR","GLP1R","GHR","GHRHR","EPOR","ANGPTL3","PCSK9","TNFSF11"}
        immune_mod   = {"MS4A1","CD19","FCGRT","ITGA4","ITGB7","CSF1R","TNFSF13","TNF","IFNAR1","IFNAR2","INHBA"}
        enz          = {"GAA","GLA","ARG1","IDS","MAN2B1","PNLIP","SERPINA1","SI","SMPD1"}
        neuro        = {"APP","CALCA","SNAP25"}
        if g in interleukins:   return "#2563EB"
        if g in coag:           return "#0891B2"
        if g in complement:     return "#7C3AED"
        if g in ophthal:        return "#D97706"
        if g in endo:           return "#059669"
        if g in immune_mod:     return "#1D4ED8"
        if g in enz:            return "#DC2626"
        if g in neuro:          return "#9333EA"
        return "#6B7280"

    colors = [gene_color(g) for g in gene_counts["Gene"]]

    fig = go.Figure(go.Bar(
        x=gene_counts["Count"],
        y=gene_counts["Gene"],
        orientation="h",
        marker=dict(color=colors, line=dict(color="white", width=0.5)),
        text=gene_counts["Count"],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x} drug–indication pairs<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="<b>Drug Target Genes</b><br>"
                        "<sup>Frequency across all drug–indication pairs</sup>",
                   font=dict(size=14)),
        xaxis=dict(title="Drug–Indication Pairs", showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(tickfont=dict(size=10)),
        margin=dict(l=10, r=60, t=65, b=40),
        height=620,
        paper_bgcolor="#F8FAFC",
        plot_bgcolor="#F8FAFC",
    )
    return fig

# ═══════════════════════════════════════════════════════════════════════════
# FIG 5 — Sunburst: Disease category → Drug Target → Drug
# ═══════════════════════════════════════════════════════════════════════════
def build_sunburst():
    # Simplify target for readability (use first gene if multi-target)
    def first_gene(t):
        if pd.isna(t): return "Other"
        g = str(t).split(",")[0].strip()
        if "(viral)" in g or "polyclonal" in g:
            return str(t).split("(")[0].strip()
        return g

    # Group small disease categories
    def simplify_cat(c):
        keep = {"Autoimmune – Rheumatology","Autoimmune – Dermatology",
                "Autoimmune – Gastroenterology","Ophthalmology",
                "Hematology – Hemophilia","Autoimmune – Pulmonology",
                "Enzyme Deficiency","Neurology – Demyelinating",
                "Endocrinology – Diabetes","Hematology – Complement"}
        return c if c in keep else "Other Chronic"

    df = ind.copy()
    df["Cat2"]   = df["Disease Category"].apply(simplify_cat)
    df["Target1"]= df["Drug Target (Gene)"].apply(first_gene)
    df["Drug_short"] = df["Drug (Proper Name)"].apply(
        lambda x: x[:28] + "…" if len(x) > 30 else x)

    ids, labels, parents, values_sb = [], [], [], []

    # Level 0 – root
    ids.append("root"); labels.append("All Chronic<br>& Long-term<br>Drugs")
    parents.append(""); values_sb.append(0)

    # Level 1 – disease category
    for cat, grp in df.groupby("Cat2"):
        cid = f"cat|{cat}"
        ids.append(cid); labels.append(cat)
        parents.append("root"); values_sb.append(len(grp))

        # Level 2 – gene target
        for gene, grp2 in grp.groupby("Target1"):
            gid = f"gene|{cat}|{gene}"
            ids.append(gid); labels.append(gene)
            parents.append(cid); values_sb.append(len(grp2))

            # Level 3 – drug
            for drug, grp3 in grp2.groupby("Drug_short"):
                did = f"drug|{cat}|{gene}|{drug}"
                ids.append(did); labels.append(drug)
                parents.append(gid); values_sb.append(len(grp3))

    fig = go.Figure(go.Sunburst(
        ids=ids, labels=labels, parents=parents, values=values_sb,
        branchvalues="total",
        insidetextorientation="radial",
        maxdepth=3,
        hovertemplate="<b>%{label}</b><br>Indications: %{value}<extra></extra>",
        marker=dict(colorscale="Blues", line=dict(color="white", width=0.8)),
    ))
    fig.update_layout(
        title=dict(text="<b>Disease Category → Gene Target → Drug</b><br>"
                        "<sup>Click to drill down</sup>",
                   font=dict(size=14)),
        margin=dict(l=10, r=10, t=65, b=10),
        height=600,
        paper_bgcolor="#F8FAFC",
    )
    return fig

# ═══════════════════════════════════════════════════════════════════════════
# FIG 6 — Scatter: drugs by # indications vs target diversity
# ═══════════════════════════════════════════════════════════════════════════
def build_scatter():
    drug_ind_count = ind.groupby("Drug (Proper Name)").agg(
        n_indications=("Disease / Indication", "nunique"),
        n_categories =("Disease Category", "nunique"),
        target       =("Drug Target (Gene)", "first"),
        brand        =("Brand Name(s)", "first"),
    ).reset_index()

    drug_ind_count["target_short"] = drug_ind_count["target"].apply(
        lambda t: str(t).split(",")[0].strip()[:12] if pd.notna(t) else "")

    fig = px.scatter(
        drug_ind_count,
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
        height=420,
        paper_bgcolor="#F8FAFC",
        plot_bgcolor="#F8FAFC",
    )
    return fig

# ═══════════════════════════════════════════════════════════════════════════
# FIG 7 — Heatmap: Drug Target Gene × Disease Category
# ═══════════════════════════════════════════════════════════════════════════
def build_heatmap():
    def first_gene(t):
        if pd.isna(t): return "Other"
        g = str(t).split(",")[0].strip()
        return "viral/other" if any(x in g for x in ["viral","polyclonal","HPV","RSV"]) else g

    def simplify_cat(c):
        mapping = {
            "Autoimmune – Rheumatology":    "AI – Rheumatology",
            "Autoimmune – Dermatology":     "AI – Dermatology",
            "Autoimmune – Gastroenterology":"AI – Gastroenterology",
            "Autoimmune – Pulmonology":     "AI – Pulmonology",
            "Ophthalmology":                "Ophthalmology",
            "Hematology – Hemophilia":      "Hematology – Hemophilia",
            "Hematology – Complement":      "Hematology – Complement",
            "Hematology – Immunodeficiency":"Hematology – Immunodef.",
            "Hematology – Rare Blood":      "Hematology – Rare Blood",
            "Hematology – Anemia":          "Hematology – Anemia",
            "Enzyme Deficiency":            "Enzyme Deficiency",
            "Neurology – Demyelinating":    "Neurology – Demyel.",
            "Neurology – Neuromuscular":    "Neurology – Neuromusc.",
            "Neurology – Neurodegeneration":"Neurology – Neurodegeneration",
            "Endocrinology – Diabetes":     "Endocrinology – Diabetes",
            "Endocrinology – Growth":       "Endocrinology – Growth",
            "Endocrinology – Lipid":        "Endocrinology – Lipid",
            "Cardiovascular / Pulmonary":   "Cardiovascular",
            "Bone / Metabolic":             "Bone / Metabolic",
            "Nephrology":                   "Nephrology",
        }
        return mapping.get(c, "Other")

    df = ind.copy()
    df["Gene"] = df["Drug Target (Gene)"].apply(first_gene)
    df["Cat2"] = df["Disease Category"].apply(simplify_cat)

    pivot = df.groupby(["Gene", "Cat2"]).size().unstack(fill_value=0)

    # filter: genes with ≥2 total entries
    pivot = pivot[pivot.sum(axis=1) >= 2]
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=True).index]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale="Blues",
        showscale=True,
        text=pivot.values,
        texttemplate="%{text}",
        hovertemplate="Gene: <b>%{y}</b><br>Disease: <b>%{x}</b><br>Count: %{z}<extra></extra>",
        xgap=2, ygap=2,
        colorbar=dict(title="Count", thickness=12),
    ))
    fig.update_layout(
        title=dict(text="<b>Drug Target Gene × Disease Category</b><br>"
                        "<sup>Number of drug–indication pairs per cell</sup>",
                   font=dict(size=14)),
        xaxis=dict(tickangle=-40, tickfont=dict(size=9)),
        yaxis=dict(tickfont=dict(size=10)),
        margin=dict(l=10, r=20, t=65, b=130),
        height=540,
        paper_bgcolor="#F8FAFC",
        plot_bgcolor="#F8FAFC",
    )
    return fig

# ═══════════════════════════════════════════════════════════════════════════
# FIG 8 — Revenue: top-selling biologics colored by disease category
# ═══════════════════════════════════════════════════════════════════════════
def build_revenue_chart():
    # One row per drug (take max revenue across indications — same value for all rows)
    rev = (ind[["Drug (Proper Name)", "Brand Name(s)", "Annual Revenue 2024 (USD B)",
                "Drug Target (Gene)", "Disease Category"]]
           .dropna(subset=["Annual Revenue 2024 (USD B)"])
           .groupby("Drug (Proper Name)")
           .agg(
               revenue   =("Annual Revenue 2024 (USD B)", "max"),
               brand     =("Brand Name(s)",               "first"),
               target    =("Drug Target (Gene)",          "first"),
               category  =("Disease Category",            "first"),
           )
           .reset_index()
           .sort_values("revenue", ascending=False)
           .head(25))

    # Short drug label: brand (proper)
    rev["label"] = rev.apply(
        lambda r: f"{r['brand'].split('/')[0].split(',')[0].strip()}"
                  f" ({str(r['target']).split(',')[0].strip()})",
        axis=1)

    # Color by broad disease theme
    def cat_color(c):
        if "Rheumat" in c or "Dermat" in c or "Gastro" in c or "Pulmon" in c:
            return "#2563EB"   # blue – autoimmune
        if "Neurol" in c:     return "#7C3AED"   # violet – neurology
        if "Hematol" in c:    return "#0891B2"   # teal – hematology
        if "Endocrin" in c:   return "#059669"   # green – endocrinology
        if "Ophth" in c:      return "#D97706"   # amber – ophthalmology
        if "Enzyme" in c:     return "#DC2626"   # red – enzyme deficiency
        if "Bone" in c:       return "#92400E"   # brown – bone
        return "#6B7280"

    colors   = [cat_color(c) for c in rev["category"]]
    revenues = rev["revenue"].tolist()
    labels   = rev["label"].tolist()
    targets  = rev["target"].fillna("N/A").tolist()
    cats     = rev["category"].tolist()

    # Sort ascending so longest bar is at top
    order     = sorted(range(len(revenues)), key=lambda i: revenues[i])
    rev_sorted = [revenues[i] for i in order]
    lab_sorted = [labels[i]   for i in order]
    tgt_sorted = [targets[i]  for i in order]
    cat_sorted = [cats[i]     for i in order]
    col_sorted = [colors[i]   for i in order]

    hover = [
        f"<b>{lab_sorted[i]}</b><br>"
        f"Revenue: <b>${rev_sorted[i]:.2f}B</b><br>"
        f"Target: {tgt_sorted[i]}<br>"
        f"Category: {cat_sorted[i]}"
        for i in range(len(rev_sorted))
    ]

    fig = go.Figure(go.Bar(
        x=rev_sorted,
        y=lab_sorted,
        orientation="h",
        marker=dict(color=col_sorted, line=dict(color="white", width=0.5)),
        text=[f"${v:.1f}B" for v in rev_sorted],
        textposition="outside",
        hovertemplate="%{customdata}<extra></extra>",
        customdata=hover,
    ))

    # Legend annotations for colour key
    legend_items = [
        ("#2563EB", "Autoimmune"),
        ("#7C3AED", "Neurology"),
        ("#0891B2", "Hematology"),
        ("#059669", "Endocrinology"),
        ("#D97706", "Ophthalmology"),
        ("#DC2626", "Enzyme Deficiency"),
        ("#6B7280", "Other"),
    ]
    for x_off, (color, name) in enumerate(legend_items):
        fig.add_annotation(
            x=0, y=1.06 - x_off * 0.0,
            xref="paper", yref="paper",
            text=f'<span style="color:{color}">■</span> {name}',
            showarrow=False, font=dict(size=10), xanchor="left",
        )

    fig.update_layout(
        title=dict(
            text="<b>Top 25 Biologics by 2024 Global Revenue</b><br>"
                 "<sup>Color = disease category &nbsp;|&nbsp; Source: FY2024 pharma earnings</sup>",
            font=dict(size=14)),
        xaxis=dict(title="Annual Revenue (USD Billions)", showgrid=True,
                   gridcolor="#E2E8F0", tickprefix="$", ticksuffix="B"),
        yaxis=dict(tickfont=dict(size=9.5)),
        margin=dict(l=10, r=80, t=70, b=40),
        height=680,
        paper_bgcolor="#F8FAFC",
        plot_bgcolor="#F8FAFC",
    )
    return fig

# ═══════════════════════════════════════════════════════════════════════════
# Assemble full HTML
# ═══════════════════════════════════════════════════════════════════════════
def to_div(fig, div_id):
    # autosize=True lets JS resize freely; no fixed width
    fig.update_layout(autosize=True)
    return fig.to_html(
        full_html=False, include_plotlyjs=False,
        div_id=div_id,
        config={"responsive": True, "displaylogo": False,
                "modeBarButtonsToRemove": ["select2d","lasso2d","autoScale2d"],
                "scrollZoom": False},
    )

# Build all figures
f_sankey  = build_sankey()
f_donut   = build_donut()
f_disease = build_disease_bar()
f_target  = build_target_bar()
f_sun     = build_sunburst()
f_scatter = build_scatter()
f_heat    = build_heatmap()
f_revenue = build_revenue_chart()

# Key metric totals
n_total    = len(cls)
n_longterm = int((cls["Category"].isin(["CHRONIC","LONG-TERM","PERIODIC"])).sum())
n_chronic  = int((cls["Category"] == "CHRONIC").sum())
n_nononcol = ind["Drug (Proper Name)"].nunique()
n_targets  = ind["Drug Target (Gene)"].nunique()
n_rows     = len(ind)
top_rev_drug  = ind.groupby("Drug (Proper Name)")["Annual Revenue 2024 (USD B)"].max().idxmax()
top_rev_val   = ind.groupby("Drug (Proper Name)")["Annual Revenue 2024 (USD B)"].max().max()
top_rev_brand = ind.loc[ind["Drug (Proper Name)"] == top_rev_drug, "Brand Name(s)"].iloc[0].split("/")[0].split(",")[0].strip()

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0"/>
<title>FDA Biologics — Chronic Use Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
/* ── Reset & tokens ──────────────────────────────────────────────────── */
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

/* ── Header ─────────────────────────────────────────────────────────── */
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

/* ── Pipeline strip ──────────────────────────────────────────────────── */
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
  position: relative;
}}
.pipe-step::after {{
  content: "›";
  position: absolute; right: -8px; top: 50%;
  transform: translateY(-50%);
  color: rgba(255,255,255,.4); font-size:1.1rem;
  pointer-events: none;
  display: none;   /* hidden on grid layout */
}}
.pipe-step strong {{
  display:block; font-size: clamp(1.15rem,3.5vw,1.5rem); font-weight:700;
  line-height:1.1;
}}
.pipe-step span {{
  font-size: clamp(0.62rem, 1.8vw, 0.72rem); opacity:.82; line-height:1.2;
  display:block; margin-top:2px;
}}

/* ── Metric cards ────────────────────────────────────────────────────── */
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

/* ── Section labels ─────────────────────────────────────────────────── */
.sec {{
  font-size: clamp(0.6rem, 1.8vw, 0.68rem);
  font-weight:700; letter-spacing:.07em; text-transform:uppercase;
  color:#fff; padding: 3px 10px; border-radius:4px;
  margin: 18px var(--pad) 0; display:inline-block;
}}
.s1{{background:#1E3A5F;}} .s2{{background:#2563EB;}}
.s3{{background:#7C3AED;}} .s4{{background:#0891B2;}}
.s5{{background:#16A34A;}}

/* ── Grids ──────────────────────────────────────────────────────────── */
.g1 {{ padding: 8px var(--pad); }}
.g2 {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 440px), 1fr));
  gap: 10px;
  padding: 8px var(--pad);
}}

/* ── Cards ───────────────────────────────────────────────────────────── */
.card {{
  background:var(--card); border-radius:var(--r); padding:8px 6px;
  box-shadow:0 1px 4px rgba(0,0,0,.07);
  overflow:hidden; min-width:0;
}}
/* Heatmap needs horizontal scroll on small screens */
.card-scroll {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
.card-scroll .plotly-graph-div {{ min-width: 500px; }}

/* ── Tabs (Step 4) ──────────────────────────────────────────────────── */
.tabs {{ display:flex; gap:6px; padding: 0 var(--pad) 0; margin-top:10px; flex-wrap:wrap; }}
.tab-btn {{
  background:#E2E8F0; border:none; border-radius:20px;
  padding: 7px 16px; font-size:0.8rem; font-weight:600;
  color:var(--sub); cursor:pointer; transition:all .2s;
}}
.tab-btn.active {{
  background:var(--teal); color:#fff;
}}
.tab-panel {{ display:none; }}
.tab-panel.active {{ display:block; }}

/* ── Footer ─────────────────────────────────────────────────────────── */
footer {{
  text-align:center; font-size:clamp(0.65rem,1.8vw,0.75rem);
  color:var(--sub); padding:18px var(--pad) 24px; line-height:1.6;
}}
</style>
</head>
<body>

<!-- ── Header ── -->
<header>
  <h1>FDA Purple Book Biologics — Chronic Use Analysis Dashboard</h1>
  <p>Systematic evaluation of 208 approved biologics for treatment duration, disease indication, and molecular target</p>
</header>

<!-- ── Pipeline ── -->
<div class="pipeline">
  <div class="pipe-step"><strong>208</strong><span>FDA biologics evaluated</span></div>
  <div class="pipe-step"><strong>5</strong><span>duration categories</span></div>
  <div class="pipe-step"><strong>147</strong><span>long-term use (70.7%)</span></div>
  <div class="pipe-step"><strong>96</strong><span>non-oncology chronic</span></div>
  <div class="pipe-step"><strong>175</strong><span>drug–indication pairs</span></div>
  <div class="pipe-step"><strong>30</strong><span>disease categories</span></div>
  <div class="pipe-step"><strong>62</strong><span>unique targets</span></div>
</div>

<!-- ── Metrics ── -->
<div class="metrics">
  <div class="metric">
    <div class="mval">{n_total}</div>
    <div class="mlabel">Biologics evaluated</div>
  </div>
  <div class="metric v">
    <div class="mval">{n_longterm}</div>
    <div class="mlabel">Require long-term use</div>
  </div>
  <div class="metric t">
    <div class="mval">{n_chronic}</div>
    <div class="mlabel">Strictly chronic use</div>
  </div>
  <div class="metric g">
    <div class="mval">{n_nononcol}</div>
    <div class="mlabel">Non-oncology chronic</div>
  </div>
  <div class="metric o">
    <div class="mval">{n_targets}</div>
    <div class="mlabel">Unique molecular targets</div>
  </div>
  <div class="metric" style="border-color:#16A34A;">
    <div class="mval" style="color:#16A34A;">${top_rev_val:.0f}B</div>
    <div class="mlabel">{top_rev_brand} — top revenue 2024</div>
  </div>
</div>

<!-- ── Step 1 ── -->
<div class="sec s1">Step 1 — Full Analysis Pipeline</div>
<div class="g1"><div class="card">{to_div(f_sankey,"sankey")}</div></div>

<!-- ── Step 2 ── -->
<div class="sec s2">Step 2 — Duration Classification of All 208 Biologics</div>
<div class="g2">
  <div class="card">{to_div(f_donut,"donut")}</div>
  <div class="card">{to_div(f_scatter,"scatter")}</div>
</div>

<!-- ── Step 3 ── -->
<div class="sec s3">Step 3 — Chronic &amp; Long-term Drugs by Disease (Oncology Removed)</div>
<div class="g2">
  <div class="card">{to_div(f_disease,"disease")}</div>
  <div class="card">{to_div(f_target,"target")}</div>
</div>

<!-- ── Step 4 (tabs on mobile) ── -->
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
    <div class="card card-scroll">{to_div(f_heat,"heatmap")}</div>
  </div>
</div>

<!-- ── Step 5 ── -->
<div class="sec s5">Step 5 — Top-Selling Biologics by 2024 Global Revenue</div>
<div class="g1"><div class="card">{to_div(f_revenue,"revenue")}</div></div>

<footer>
  Data source: FDA Purple Book 2020–2026 &nbsp;|&nbsp; Drug targets: ChEMBL v34 + HGNC<br>
  Revenue: AbbVie, Sanofi, Roche, Novartis, J&amp;J, AstraZeneca, Eli Lilly, Novo Nordisk, Amgen FY2024 earnings<br>
  Files: chronic_use_classification.csv · chronic_drugs_indications2.csv
</footer>

<script>
/* ── Tab switcher ──────────────────────────────────────────────────── */
function showTab(id, btn) {{
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('panel-' + id).classList.add('active');
  btn.classList.add('active');
  // Force Plotly to redraw after becoming visible
  const plot = document.getElementById(id === 'sun' ? 'sunburst' : 'heatmap');
  if (plot && plot.data) Plotly.relayout(plot, {{autosize: true}});
}}

/* ── Responsive chart resizing ──────────────────────────────────────── */
const CHART_IDS = ['sankey','donut','scatter','disease','target','sunburst','heatmap','revenue'];

// Heights: [mobile < 480, tablet < 900, desktop]
const HEIGHTS = {{
  sankey:   [380, 460, 520],
  donut:    [320, 360, 380],
  scatter:  [300, 360, 420],
  disease:  [420, 480, 520],
  target:   [520, 580, 620],
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

/* Run on load + resize (debounced) */
let _resizeTimer;
window.addEventListener('resize', () => {{
  clearTimeout(_resizeTimer);
  _resizeTimer = setTimeout(resizeAll, 120);
}});

/* Wait for all Plotly plots to be drawn, then resize */
document.addEventListener('DOMContentLoaded', () => {{
  // Plotly draws asynchronously; poll until all plots exist
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

OUT = "/Work/AI_Drug/chronic_use_dashboard.html"
with open(OUT, "w", encoding="utf-8") as f:
    f.write(HTML)

print(f"✓ Dashboard written → {OUT}")
print(f"  File size: {len(HTML)/1024:.0f} KB")
