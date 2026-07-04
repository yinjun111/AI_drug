"""
Step 5 — Self-contained Plotly HTML dashboard for FDA Orange Book chronic-use analysis.
7 figures matching the plan:
  1. Sankey — all active ingredients → duration class → disease category
  2. Donut — duration class breakdown
  3. Bar — disease category counts (chronic/long-term only)
  4. Bar — top chronic ingredients by # ANDA generic competitors
  5. Scatter — latest patent expiry year vs # generic competitors (patent-cliff view)
  6. Heatmap — disease category × generic-availability (AB-rated vs not)
  7. Bar — chronic drugs by approval decade (market maturity)
Output: orangebook_chronic_dashboard.html
"""

import csv
from collections import Counter, defaultdict

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ── Load data ─────────────────────────────────────────────────────────────────
all_df = pd.read_csv("orangebook_with_patents.csv")
chr_df = pd.read_csv("orangebook_chronic_drugs.csv")

# ── Colour palette ────────────────────────────────────────────────────────────
DUR_COLORS = {
    "CHRONIC":              "#2563EB",
    "LONG-TERM":            "#7C3AED",
    "PERIODIC":             "#0891B2",
    "SHORT":                "#D97706",
    "OTHER":                "#6B7280",
}

CAT_COLORS = {
    "Cardiovascular":       "#DC2626",
    "Metabolic":            "#059669",
    "Psychiatric":          "#7C3AED",
    "Neurology":            "#9333EA",
    "Oncology":             "#F97316",
    "Infectious":           "#0891B2",
    "Respiratory":          "#0EA5E9",
    "GI":                   "#84CC16",
    "Autoimmune":           "#2563EB",
    "Pain":                 "#F59E0B",
    "Dermatology":          "#EC4899",
    "Ophthalmology":        "#10B981",
    "Other":                "#9CA3AF",
    "Other/Unclassified":   "#D1D5DB",
}


def cat_color(c):
    return CAT_COLORS.get(c, "#9CA3AF")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 1 — Sankey: all active ingredients → duration → disease category
# ══════════════════════════════════════════════════════════════════════════════
def build_sankey():
    total = len(all_df)
    dur_order = ["CHRONIC", "LONG-TERM", "PERIODIC", "SHORT", "OTHER"]
    dur_counts = all_df["Duration_Class"].value_counts()

    # Chronic/long-term by disease category
    chronic_df = all_df[all_df["Duration_Class"].isin(["CHRONIC", "LONG-TERM"])]
    cat_order = [k for k in CAT_COLORS if k not in ("Other/Unclassified",)]
    cat_counts_raw = chronic_df["Disease_Category"].value_counts()

    # Consolidate small cats into "Other chronic"
    TOP_N = 10
    top_cats = cat_counts_raw.head(TOP_N).index.tolist()

    # Node list
    node_labels = [f"All Active\n({total:,} ingredients)"]
    # duration nodes: 1..5
    dur_node_idx = {}
    for d in dur_order:
        dur_node_idx[d] = len(node_labels)
        n = int(dur_counts.get(d, 0))
        node_labels.append(f"{d}\n({n:,})")

    # chronic aggregate node: 6
    n_chronic_total = int(chronic_df.shape[0])
    node_labels.append(f"Chronic / Long-term\n({n_chronic_total:,} drugs)")
    chronic_agg_idx = len(node_labels) - 1

    # disease category nodes: 7..
    cat_node_idx = {}
    for cat in top_cats:
        cat_node_idx[cat] = len(node_labels)
        n = int(cat_counts_raw.get(cat, 0))
        node_labels.append(f"{cat}\n({n:,})")
    other_total = int(cat_counts_raw[~cat_counts_raw.index.isin(top_cats)].sum())
    other_cat_idx = len(node_labels)
    node_labels.append(f"Other\n({other_total:,})")

    # Node colors
    node_colors = ["#1E3A5F"]  # root
    for d in dur_order:
        node_colors.append(DUR_COLORS[d])
    node_colors.append("#1D4ED8")   # chronic aggregate
    for cat in top_cats:
        node_colors.append(cat_color(cat))
    node_colors.append("#9CA3AF")   # other

    sources, targets, values, link_colors = [], [], [], []

    def add(s, t, v, c="#CBD5E1"):
        sources.append(s); targets.append(t); values.append(v); link_colors.append(c)

    # root → duration
    for d in dur_order:
        add(0, dur_node_idx[d], int(dur_counts.get(d, 0)), DUR_COLORS[d])

    # CHRONIC + LONG-TERM → chronic aggregate
    add(dur_node_idx["CHRONIC"],   chronic_agg_idx, int(dur_counts.get("CHRONIC", 0)),   "#60A5FA")
    add(dur_node_idx["LONG-TERM"], chronic_agg_idx, int(dur_counts.get("LONG-TERM", 0)), "#A78BFA")

    # chronic aggregate → disease categories
    for cat in top_cats:
        add(chronic_agg_idx, cat_node_idx[cat], int(cat_counts_raw.get(cat, 0)), cat_color(cat))
    add(chronic_agg_idx, other_cat_idx, other_total, "#9CA3AF")

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=16, thickness=20,
            line=dict(color="white", width=0.5),
            label=node_labels,
            color=node_colors,
            hovertemplate="%{label}<extra></extra>",
        ),
        link=dict(
            source=sources, target=targets, value=values,
            color=link_colors,
            hovertemplate="%{source.label} → %{target.label}: %{value:,}<extra></extra>",
        ),
    ))
    fig.update_layout(
        title=dict(
            text=f"<b>FDA Orange Book — Full Analysis Pipeline: {total:,} Ingredients → Duration → Disease</b>",
            font=dict(size=14)),
        font=dict(size=10),
        margin=dict(l=10, r=10, t=50, b=10),
        height=560,
        paper_bgcolor="#F8FAFC",
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# FIG 2 — Duration classification donut
# ══════════════════════════════════════════════════════════════════════════════
def build_donut():
    total = len(all_df)
    order  = ["CHRONIC", "LONG-TERM", "PERIODIC", "SHORT", "OTHER"]
    counts = all_df["Duration_Class"].value_counts()
    vals   = [int(counts.get(c, 0)) for c in order]
    colors = [DUR_COLORS[c] for c in order]
    labels = [f"{c}\n({v:,})" for c, v in zip(order, vals)]

    fig = go.Figure(go.Pie(
        labels=labels, values=vals,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textinfo="label+percent",
        textfont=dict(size=10),
        hovertemplate="<b>%{label}</b><br>%{value:,} ingredients (%{percent})<extra></extra>",
        pull=[0.04 if c in ("CHRONIC", "LONG-TERM") else 0 for c in order],
    ))
    fig.add_annotation(
        text=f"<b>{total:,}</b><br>ingredients",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=12, color="#1E3A5F"),
    )
    fig.update_layout(
        title=dict(text="<b>Duration Classification — All Active Ingredients</b>", font=dict(size=14)),
        showlegend=False,
        margin=dict(l=10, r=10, t=50, b=10),
        height=400,
        paper_bgcolor="#F8FAFC",
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# FIG 3 — Disease category bar (chronic/long-term only)
# ══════════════════════════════════════════════════════════════════════════════
def build_disease_bar():
    cat_counts = chr_df["Disease_Category"].value_counts().reset_index()
    cat_counts.columns = ["Category", "Count"]
    cat_counts = cat_counts.sort_values("Count")

    colors = [cat_color(c) for c in cat_counts["Category"]]

    fig = go.Figure(go.Bar(
        x=cat_counts["Count"],
        y=cat_counts["Category"],
        orientation="h",
        marker=dict(color=colors, line=dict(color="white", width=0.5)),
        text=cat_counts["Count"],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x:,} chronic/long-term ingredients<extra></extra>",
    ))
    fig.update_layout(
        title=dict(
            text="<b>Disease Category — Chronic & Long-term Drugs Only</b><br>"
                 "<sup>CHRONIC + LONG-TERM ingredients by therapeutic area</sup>",
            font=dict(size=14)),
        xaxis=dict(title="Ingredients", showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(tickfont=dict(size=10)),
        margin=dict(l=10, r=70, t=65, b=40),
        height=480,
        paper_bgcolor="#F8FAFC",
        plot_bgcolor="#F8FAFC",
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# FIG 4 — Top chronic drugs by # ANDA generic competitors (Orange-Book-specific)
# ══════════════════════════════════════════════════════════════════════════════
def build_generic_bar():
    top = chr_df.nlargest(30, "Generic_Competitor_Count")[
        ["Ingredient", "Generic_Competitor_Count", "Disease_Category", "Duration_Class"]
    ].copy()
    top = top.sort_values("Generic_Competitor_Count")
    top["Label"] = top["Ingredient"].str[:45]

    colors = [cat_color(c) for c in top["Disease_Category"]]

    fig = go.Figure(go.Bar(
        x=top["Generic_Competitor_Count"],
        y=top["Label"],
        orientation="h",
        marker=dict(color=colors, line=dict(color="white", width=0.5)),
        text=top["Generic_Competitor_Count"],
        textposition="outside",
        customdata=list(zip(top["Disease_Category"], top["Duration_Class"], top["Ingredient"])),
        hovertemplate=(
            "<b>%{customdata[2]}</b><br>"
            "Category: %{customdata[0]}<br>"
            "Duration: %{customdata[1]}<br>"
            "ANDA competitors: %{x:,}<extra></extra>"
        ),
    ))
    fig.update_layout(
        title=dict(
            text="<b>Generic Competition: Top 30 Chronic Drugs by ANDA Count</b><br>"
                 "<sup>Color = disease category | Orange-Book-specific view</sup>",
            font=dict(size=14)),
        xaxis=dict(title="# ANDA Generic Competitors", showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(tickfont=dict(size=9)),
        margin=dict(l=10, r=70, t=65, b=40),
        height=600,
        paper_bgcolor="#F8FAFC",
        plot_bgcolor="#F8FAFC",
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# FIG 5 — Scatter: patent expiry year vs # generic competitors (patent-cliff)
# ══════════════════════════════════════════════════════════════════════════════
def build_patent_scatter():
    df = chr_df.copy()
    df = df[df["Patent_Expiry_Year"].notna() & (df["Generic_Competitor_Count"] > 0)]
    df["Patent_Expiry_Year"] = df["Patent_Expiry_Year"].astype(int)
    df = df[df["Patent_Expiry_Year"].between(2020, 2035)]

    if df.empty:
        fig = go.Figure()
        fig.update_layout(title=dict(text="<b>Patent-Cliff View (no data)</b>"))
        return fig

    # Shorten ingredient name for label
    df["Label"] = df["Ingredient"].str.split().str[:2].str.join(" ")

    # Color by category
    colors_scatter = [cat_color(c) for c in df["Disease_Category"]]

    fig = go.Figure()

    # Group by category for legend
    for cat, grp in df.groupby("Disease_Category"):
        fig.add_trace(go.Scatter(
            x=grp["Patent_Expiry_Year"],
            y=grp["Generic_Competitor_Count"],
            mode="markers",
            name=cat,
            marker=dict(color=cat_color(cat), size=8, opacity=0.75,
                        line=dict(color="white", width=0.5)),
            text=grp["Ingredient"],
            customdata=list(zip(
                grp["Disease_Category"],
                grp["Latest_Patent_Expiry"],
                grp["Has_Blocking_Exclusivity"],
            )),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Category: %{customdata[0]}<br>"
                "Patent expiry: %{customdata[1]}<br>"
                "Blocking exclusivity: %{customdata[2]}<br>"
                "ANDA competitors: %{y:,}<extra></extra>"
            ),
        ))

    # Add reference line: today
    fig.add_vline(x=2026, line=dict(color="#EF4444", dash="dot", width=1.5),
                  annotation_text="Today (2026)", annotation_position="top right",
                  annotation_font_color="#EF4444")

    fig.update_layout(
        title=dict(
            text="<b>Patent-Cliff View: Patent Expiry Year vs Generic Competition</b><br>"
                 "<sup>Chronic/long-term drugs with patents expiring 2020–2035</sup>",
            font=dict(size=14)),
        xaxis=dict(title="Latest Patent Expiry Year", dtick=1,
                   showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(title="# ANDA Generic Competitors",
                   showgrid=True, gridcolor="#E2E8F0"),
        legend=dict(title="Disease Category", orientation="v",
                    font=dict(size=9), x=1.02, xanchor="left"),
        margin=dict(l=40, r=160, t=65, b=50),
        height=480,
        paper_bgcolor="#F8FAFC",
        plot_bgcolor="#F8FAFC",
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# FIG 6 — Heatmap: disease category × generic availability (AB-rated vs not)
# ══════════════════════════════════════════════════════════════════════════════
def build_availability_heatmap():
    # Load classified full dataset to get TE_Code(s)
    df = all_df[all_df["Duration_Class"].isin(["CHRONIC", "LONG-TERM"])].copy()
    df["Has_AB"] = df["TE_Code(s)"].fillna("").apply(
        lambda x: "AB-rated\n(generic available)" if "AB" in str(x) else "No AB rating\n(brand only)"
    )

    # Cross-tab: disease category × generic availability
    pivot = (
        df.groupby(["Disease_Category", "Has_AB"])
        .size()
        .unstack(fill_value=0)
    )
    # Remove unclassified
    pivot = pivot[pivot.index != "Other/Unclassified"]

    # Ensure both columns exist
    for col in ["AB-rated\n(generic available)", "No AB rating\n(brand only)"]:
        if col not in pivot.columns:
            pivot[col] = 0

    pivot = pivot.sort_values("AB-rated\n(generic available)", ascending=True)

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=["AB-rated (generic\navailable)", "No AB rating\n(brand only)"],
        y=pivot.index.tolist(),
        colorscale="Blues",
        showscale=True,
        text=pivot.values,
        texttemplate="%{text}",
        hovertemplate="<b>%{y}</b><br>%{x}<br>%{z:,} ingredients<extra></extra>",
        xgap=3, ygap=3,
        colorbar=dict(title="Count", thickness=12),
    ))
    fig.update_layout(
        title=dict(
            text="<b>Generic Availability: Disease Category × AB-Rated Status</b><br>"
                 "<sup>Chronic/long-term drugs only; AB rating = therapeutically equivalent generic exists</sup>",
            font=dict(size=14)),
        xaxis=dict(tickfont=dict(size=11)),
        yaxis=dict(tickfont=dict(size=10)),
        margin=dict(l=10, r=30, t=70, b=50),
        height=500,
        paper_bgcolor="#F8FAFC",
        plot_bgcolor="#F8FAFC",
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# FIG 7 — Bar: chronic drugs by approval decade (market maturity)
# ══════════════════════════════════════════════════════════════════════════════
def build_decade_bar():
    df = chr_df.copy()
    df = df[df["Earliest_Approval"].notna() & (df["Earliest_Approval"] != "")]
    df["Year"] = pd.to_datetime(df["Earliest_Approval"], errors="coerce").dt.year
    df = df.dropna(subset=["Year"])
    df["Decade"] = (df["Year"] // 10 * 10).astype(int).astype(str) + "s"

    decade_cat = (
        df.groupby(["Decade", "Disease_Category"])
        .size()
        .reset_index(name="Count")
    )

    decade_order = sorted(decade_cat["Decade"].unique())
    cats         = [c for c in CAT_COLORS if c != "Other/Unclassified"]

    fig = go.Figure()
    for cat in cats:
        sub = decade_cat[decade_cat["Disease_Category"] == cat]
        sub = sub.set_index("Decade").reindex(decade_order, fill_value=0).reset_index()
        fig.add_trace(go.Bar(
            x=sub["Decade"],
            y=sub["Count"],
            name=cat,
            marker_color=cat_color(cat),
            hovertemplate=f"<b>{cat}</b><br>Decade: %{{x}}<br>%{{y:,}} ingredients<extra></extra>",
        ))

    fig.update_layout(
        barmode="stack",
        title=dict(
            text="<b>Chronic Drug Approvals by Decade</b><br>"
                 "<sup>First NDA/ANDA approval decade for each chronic/long-term ingredient</sup>",
            font=dict(size=14)),
        xaxis=dict(title="Approval Decade", categoryorder="array",
                   categoryarray=decade_order),
        yaxis=dict(title="Ingredients", showgrid=True, gridcolor="#E2E8F0"),
        legend=dict(title="Disease Category", font=dict(size=9),
                    orientation="v", x=1.02, xanchor="left"),
        margin=dict(l=40, r=160, t=65, b=50),
        height=450,
        paper_bgcolor="#F8FAFC",
        plot_bgcolor="#F8FAFC",
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# Assemble full HTML
# ══════════════════════════════════════════════════════════════════════════════
def to_div(fig, div_id):
    fig.update_layout(autosize=True)
    return fig.to_html(
        full_html=False, include_plotlyjs=False,
        div_id=div_id,
        config={"responsive": True, "displaylogo": False,
                "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
                "scrollZoom": False},
    )


# Build all figures
f_sankey     = build_sankey()
f_donut      = build_donut()
f_disease    = build_disease_bar()
f_generic    = build_generic_bar()
f_patent     = build_patent_scatter()
f_heatmap    = build_availability_heatmap()
f_decade     = build_decade_bar()

# Key metrics
n_total       = len(all_df)
n_chronic_dur = int(all_df["Duration_Class"].eq("CHRONIC").sum())
n_longterm    = int(all_df["Duration_Class"].eq("LONG-TERM").sum())
n_with_patent = int((all_df["Patent_Count"] > 0).sum())
n_generic_avail = int(all_df["TE_Code(s)"].fillna("").str.contains("AB").sum())
n_chronic_total = n_chronic_dur + n_longterm
top_generic_ing = chr_df.loc[chr_df["Generic_Competitor_Count"].idxmax(), "Ingredient"]
top_generic_n   = int(chr_df["Generic_Competitor_Count"].max())

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
  --teal:#0891B2; --green:#059669; --orange:#D97706; --red:#DC2626;
  --text:#1E293B; --sub:#64748B; --border:#E2E8F0;
  --pad: clamp(10px, 3vw, 24px);
  --r: 12px;
}}
*,*::before,*::after {{ box-sizing:border-box; margin:0; padding:0; }}
html {{ font-size:16px; }}
body {{ font-family: system-ui,-apple-system,"Segoe UI",sans-serif;
        background:var(--bg); color:var(--text); overflow-x:hidden; }}

header {{
  background: linear-gradient(135deg,#1E3A5F 0%,#DC2626 40%,#D97706 100%);
  color:#fff; padding: clamp(14px,4vw,28px) var(--pad);
}}
header h1 {{
  font-size: clamp(1rem,3.5vw,1.5rem); font-weight:700; line-height:1.25;
}}
header p {{
  margin-top:6px; opacity:.85;
  font-size: clamp(0.75rem,2.2vw,0.88rem); line-height:1.4;
}}

.pipeline {{
  background:#1E3A5F; padding:12px var(--pad);
  display:grid; grid-template-columns:repeat(auto-fit,minmax(90px,1fr)); gap:8px;
}}
.pipe-step {{
  background:rgba(255,255,255,.11); border:1px solid rgba(255,255,255,.22);
  border-radius:8px; padding:8px 6px 7px; color:#fff; text-align:center;
}}
.pipe-step strong {{
  display:block; font-size:clamp(1.1rem,3.5vw,1.5rem); font-weight:700; line-height:1.1;
}}
.pipe-step span {{
  font-size:clamp(0.62rem,1.8vw,0.72rem); opacity:.82; line-height:1.2;
  display:block; margin-top:2px;
}}

.metrics {{
  display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr));
  gap:10px; padding:14px var(--pad) 0;
}}
.metric {{
  background:var(--card); border-radius:var(--r); padding:14px 16px;
  border-left:4px solid var(--blue); box-shadow:0 1px 4px rgba(0,0,0,.07); min-width:0;
}}
.metric.v {{ border-color:var(--violet); }}
.metric.t {{ border-color:var(--teal); }}
.metric.g {{ border-color:var(--green); }}
.metric.o {{ border-color:var(--orange); }}
.metric.r {{ border-color:var(--red); }}
.mval {{ font-size:clamp(1.5rem,5vw,2.1rem); font-weight:700; color:var(--blue); line-height:1; }}
.metric.v .mval {{ color:var(--violet); }}
.metric.t .mval {{ color:var(--teal); }}
.metric.g .mval {{ color:var(--green); }}
.metric.o .mval {{ color:var(--orange); }}
.metric.r .mval {{ color:var(--red); }}
.mlabel {{ font-size:clamp(0.65rem,1.8vw,0.75rem); color:var(--sub); margin-top:4px; line-height:1.3; }}

.sec {{
  font-size:clamp(0.6rem,1.8vw,0.68rem); font-weight:700; letter-spacing:.07em;
  text-transform:uppercase; color:#fff; padding:3px 10px; border-radius:4px;
  margin:18px var(--pad) 0; display:inline-block;
}}
.s1{{background:#1E3A5F;}} .s2{{background:#DC2626;}} .s3{{background:#D97706;}}
.s4{{background:#0891B2;}} .s5{{background:#059669;}} .s6{{background:#7C3AED;}} .s7{{background:#10B981;}}

.g1 {{ padding:8px var(--pad); }}
.g2 {{
  display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,440px),1fr));
  gap:10px; padding:8px var(--pad);
}}
.card {{
  background:var(--card); border-radius:var(--r); padding:8px 6px;
  box-shadow:0 1px 4px rgba(0,0,0,.07); overflow:hidden; min-width:0;
}}

footer {{
  text-align:center; font-size:clamp(0.65rem,1.8vw,0.75rem);
  color:var(--sub); padding:18px var(--pad) 24px; line-height:1.6;
}}
</style>
</head>
<body>

<header>
  <h1>FDA Orange Book — Small-Molecule Chronic Use Dashboard</h1>
  <p>Analysis of {n_total:,} active NDA/ANDA ingredients: duration classification · disease category · generic competition · patent-cliff view</p>
</header>

<div class="pipeline">
  <div class="pipe-step"><strong>{n_total:,}</strong><span>active ingredients</span></div>
  <div class="pipe-step"><strong>5</strong><span>duration classes</span></div>
  <div class="pipe-step"><strong>{n_chronic_total:,}</strong><span>chronic/long-term</span></div>
  <div class="pipe-step"><strong>13</strong><span>disease categories</span></div>
  <div class="pipe-step"><strong>{n_with_patent:,}</strong><span>have patents</span></div>
  <div class="pipe-step"><strong>{n_generic_avail:,}</strong><span>AB-rated generics</span></div>
</div>

<div class="metrics">
  <div class="metric">
    <div class="mval">{n_total:,}</div>
    <div class="mlabel">Active ingredients (NDA+ANDA)</div>
  </div>
  <div class="metric v">
    <div class="mval">{n_chronic_dur:,}</div>
    <div class="mlabel">Strictly chronic use</div>
  </div>
  <div class="metric t">
    <div class="mval">{n_longterm:,}</div>
    <div class="mlabel">Long-term until progression</div>
  </div>
  <div class="metric g">
    <div class="mval">{n_generic_avail:,}</div>
    <div class="mlabel">AB-rated (substitutable generic)</div>
  </div>
  <div class="metric o">
    <div class="mval">{n_with_patent:,}</div>
    <div class="mlabel">Ingredients with active patents</div>
  </div>
  <div class="metric r">
    <div class="mval">{top_generic_n:,}</div>
    <div class="mlabel">{top_generic_ing[:22]}… — most generic competitors</div>
  </div>
</div>

<div class="sec s1">Step 1 — Full Analysis Pipeline</div>
<div class="g1"><div class="card">{to_div(f_sankey,"sankey")}</div></div>

<div class="sec s2">Step 2 — Duration Classification of All {n_total:,} Active Ingredients</div>
<div class="g2">
  <div class="card">{to_div(f_donut,"donut")}</div>
  <div class="card">{to_div(f_decade,"decade")}</div>
</div>

<div class="sec s3">Step 3 — Chronic & Long-term Drugs by Disease Category</div>
<div class="g1"><div class="card">{to_div(f_disease,"disease")}</div></div>

<div class="sec s4">Step 4 — Generic Competition: Top ANDA Counts (Orange Book Exclusive)</div>
<div class="g1"><div class="card">{to_div(f_generic,"generic")}</div></div>

<div class="sec s5">Step 5 — Patent-Cliff View: Patent Expiry vs Generic Entrants</div>
<div class="g1"><div class="card">{to_div(f_patent,"patent")}</div></div>

<div class="sec s6">Step 6 — Generic Availability Heatmap by Disease Category</div>
<div class="g1"><div class="card">{to_div(f_heatmap,"heatmap")}</div></div>

<footer>
  Data source: FDA Orange Book May 2026 (EOBZIP_2026_05)<br>
  Classification: rule-based INN stem/suffix analysis (no external API calls)<br>
  Files: orangebook_with_patents.csv · orangebook_chronic_drugs.csv<br>
  Reference date: July 2026 · {n_chronic_total:,} chronic/long-term ingredients of {n_total:,} active
</footer>

<script>
const CHART_IDS = ['sankey','donut','decade','disease','generic','patent','heatmap'];
const HEIGHTS = {{
  sankey:  [400, 500, 560],
  donut:   [340, 380, 400],
  decade:  [360, 420, 450],
  disease: [380, 440, 480],
  generic: [500, 560, 600],
  patent:  [360, 430, 480],
  heatmap: [420, 480, 500],
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
        'margin.l': bp === 0 ? 8 : 10,
        'margin.r': bp === 0 ? 6 : 10,
        'margin.t': bp === 0 ? 40 : 55,
        'margin.b': bp === 0 ? 30 : 40,
        'font.size': bp === 0 ? 9 : 11,
      }});
    }} catch(e) {{}}
  }});
}}

let _rt;
window.addEventListener('resize', () => {{ clearTimeout(_rt); _rt = setTimeout(resizeAll, 120); }});

document.addEventListener('DOMContentLoaded', () => {{
  let attempts = 0;
  const poll = setInterval(() => {{
    const ready = CHART_IDS.every(id => {{ const el = document.getElementById(id); return el && el.data; }});
    if (ready || attempts++ > 40) {{ clearInterval(poll); resizeAll(); }}
  }}, 150);
}});
</script>
</body>
</html>
"""

OUT_HTML = "orangebook_chronic_dashboard.html"
with open(OUT_HTML, "w", encoding="utf-8") as fh:
    fh.write(HTML)

print(f"Dashboard written → {OUT_HTML}")
print(f"File size: {len(HTML) / 1024:.0f} KB")
