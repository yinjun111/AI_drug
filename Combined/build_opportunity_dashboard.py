"""
Target x Disease Opportunity Dashboard.

Combines, per disease indication in the curated 35-target biologics/peptide
dataset (fda_all_drugs_chronic_indications_35genes.csv):
  - Market size + competitive landscape: # approved competing drugs and their
    known 2024 revenue, from the FDA Purple/Orange Book merged CSV.
  - Patient population + unmet need: prevalence-derived US patient estimates,
    sourced live from Orphanet (via the ToolUniverse MCP) for rare diseases,
    curated from CDC/registry literature for common chronic diseases
    (see opportunity_data.py for the full sourcing/rationale per disease).

Output is a Tabler-based (https://tabler.io) admin-style page — distinct from
the other dashboards' custom CSS shell — with Plotly charts inside Tabler
cards, and a sortable/filterable Tabler table for the underlying data.
"""

import csv, json
from collections import defaultdict, Counter
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from opportunity_data import canon, EPI_EXCLUDED, get_epi, US_POPULATION

SRC_CSV = "fda_all_drugs_chronic_indications_35genes.csv"
OUT_HTML = "target_disease_opportunity_dashboard.html"

# ── Load + canonicalize + aggregate ──────────────────────────────────────────
rows = list(csv.DictReader(open(SRC_CSV, encoding="utf-8-sig")))

by_disease = defaultdict(lambda: {
    "drugs": {}, "genes": set(), "modalities": set(), "cats": Counter(),
})

for r in rows:
    d = canon(r["Disease / Indication"].strip())
    b = by_disease[d]
    drug = r["Drug"].strip()
    try:
        rev = float(r["Annual Revenue 2024 (USD B)"])
    except ValueError:
        rev = 0.0
    # keep the max revenue seen for this drug (guards against blank dup rows)
    b["drugs"][drug] = max(rev, b["drugs"].get(drug, 0.0))
    for g in r["Drug Target (Gene)"].replace(";", ",").split(","):
        g = g.strip()
        if g:
            b["genes"].add(g)
    b["modalities"].add(r["Modality"].strip())
    b["cats"][r["Disease Category"].strip()] += 1

records = []
for d, b in by_disease.items():
    n_drugs = len(b["drugs"])
    revenue = sum(b["drugs"].values())
    top_cat = b["cats"].most_common(1)[0][0] if b["cats"] else ""
    excluded_note = EPI_EXCLUDED.get(d)
    epi = get_epi(d)
    rec = {
        "disease": d,
        "category": top_cat,
        "genes": ", ".join(sorted(b["genes"])),
        "modalities": ", ".join(sorted(b["modalities"])),
        "n_drugs": n_drugs,
        "drugs_list": ", ".join(sorted(b["drugs"])),
        "revenue": round(revenue, 2),
        "excluded": excluded_note is not None,
        "excluded_note": excluded_note or "",
    }
    if epi is not None:
        patients = epi["prevalence_per_100k"] / 100_000 * US_POPULATION
        rec.update({
            "prevalence_per_100k": epi["prevalence_per_100k"],
            "patients_est": patients,
            "epi_source": epi["source"],
            "epi_note": epi["note"],
            "opportunity_score": patients / (n_drugs + 1),
        })
    else:
        rec.update({"prevalence_per_100k": None, "patients_est": None,
                     "epi_source": "", "epi_note": "", "opportunity_score": None})
    records.append(rec)

df = pd.DataFrame(records)
df_scored = df[~df["excluded"]].dropna(subset=["patients_est"]).copy()

n_diseases = len(df)
n_scored = len(df_scored)
n_rare = int((df_scored["epi_source"] == "orphanet").sum())
n_targets = len({g.strip() for gs in df["genes"] for g in gs.split(",") if g.strip()})
total_patients = df_scored["patients_est"].sum()
total_revenue = df["revenue"].sum()

SRC_COLORS = {"orphanet": "#0CA678", "curated": "#4263EB"}
CAT_LIST = sorted(df["category"].unique())
_palette = (px.colors.qualitative.Safe + px.colors.qualitative.Set3 + px.colors.qualitative.Bold)
CAT_COLORS = {c: _palette[i % len(_palette)] for i, c in enumerate(CAT_LIST)}

# ── FIG 0a — Top disease indications by revenue (first plot) ────────────────
def build_disease_revenue_bar(n=25):
    d = df[df["revenue"] > 0].sort_values("revenue", ascending=False).head(n).sort_values("revenue")
    fig = go.Figure(go.Bar(
        x=d["revenue"], y=d["disease"], orientation="h",
        marker=dict(color=[CAT_COLORS.get(c, "#868E96") for c in d["category"]], line=dict(color="white", width=0.5)),
        text=[f"${v:.2f}B" for v in d["revenue"]], textposition="outside",
        customdata=list(zip(d["category"], d["n_drugs"], d["genes"])),
        hovertemplate="<b>%{y}</b><br>%{customdata[0]}<br>Revenue: $%{x:.2f}B<br>"
                      "%{customdata[1]} competing drug(s)<br>Target(s): %{customdata[2]}<extra></extra>"))
    fig.update_layout(
        title=dict(text=f"<b>Top {len(d)} Disease Indications by 2024 Revenue</b><br>"
                        "<sup>known drug-level revenue in this 35-target dataset · colored by disease category</sup>", font=dict(size=14)),
        xaxis=dict(title="Known 2024 Revenue (USD B)", showgrid=True, gridcolor="#E9ECEF",
                   tickprefix="$", ticksuffix="B", range=[0, d["revenue"].max() * 1.18]),
        yaxis=dict(tickfont=dict(size=9)),
        margin=dict(l=10, r=70, t=60, b=40), height=max(420, 24 * len(d) + 120),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#F8F9FA")
    return fig


# ── FIG 0b — Sankey: Disease → Target → Drug (second plot) ──────────────────
# Same 3-level-Sankey pattern as the first plot on
# combined_chronic_use_peptide_dashboard.html (there: Source → Modality →
# Disease Category), but re-cut for this dataset's disease/target/drug
# relationships. Restricted to the same top-revenue diseases as FIG 0a so the
# two plots tell one connected story and the node count stays legible.
def build_disease_target_drug_sankey(n_diseases=20):
    top_diseases = set(df[df["revenue"] > 0].sort_values("revenue", ascending=False).head(n_diseases)["disease"])
    disease_order = (df[df["disease"].isin(top_diseases)]
                      .sort_values("revenue", ascending=False)["disease"].tolist())

    triples = set()
    for r in rows:
        d = canon(r["Disease / Indication"].strip())
        if d not in top_diseases:
            continue
        drug = r["Drug"].strip()
        genes = {g.strip() for g in r["Drug Target (Gene)"].replace(";", ",").split(",") if g.strip()}
        for g in genes:
            triples.add((d, g, drug))

    gene_list = sorted({g for _, g, _ in triples})
    drug_list = sorted({dr for _, _, dr in triples}, key=lambda x: x.lower())

    dis_cat = dict(zip(df["disease"], df["category"]))
    labels, colors, idx = [], [], {}
    def node(key, label, color):
        idx[key] = len(labels); labels.append(label); colors.append(color)
    for d in disease_order:
        node(("dis", d), d, CAT_COLORS.get(dis_cat.get(d, ""), "#868E96"))
    for g in gene_list:
        node(("gene", g), g, "#7C3AED")
    for dr in drug_list:
        node(("drug", dr), dr, "#0CA678")

    dg_val = Counter((d, g) for d, g, _ in triples)
    gd_val = Counter((g, dr) for _, g, dr in triples)
    S, T, V, LC = [], [], [], []
    for (d, g), v in dg_val.items():
        S.append(idx[("dis", d)]); T.append(idx[("gene", g)]); V.append(v); LC.append("rgba(124,58,237,0.25)")
    for (g, dr), v in gd_val.items():
        S.append(idx[("gene", g)]); T.append(idx[("drug", dr)]); V.append(v); LC.append("rgba(12,166,137,0.25)")

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(pad=10, thickness=14, line=dict(color="white", width=0.5),
                  label=labels, color=colors, hovertemplate="%{label}<extra></extra>"),
        link=dict(source=S, target=T, value=V, color=LC,
                  hovertemplate="%{source.label} → %{target.label}: %{value}<extra></extra>")))
    fig.update_layout(
        title=dict(text=f"<b>Disease → Target → Drug</b><br>"
                        f"<sup>top {len(disease_order)} diseases by revenue, and every target/drug they connect to</sup>", font=dict(size=14)),
        font=dict(size=9), margin=dict(l=10, r=10, t=60, b=10),
        height=max(560, 22 * max(len(disease_order), len(gene_list), len(drug_list)) + 100),
        paper_bgcolor="rgba(0,0,0,0)")
    return fig


# ── FIG 1 — Opportunity scatter: patients vs competing drugs ────────────────
def build_opportunity_scatter():
    d = df_scored.copy()
    d["rev_size"] = d["revenue"].clip(lower=0.05) + 0.3
    fig = px.scatter(
        d, x="n_drugs", y="patients_est", size="rev_size", color="epi_source",
        color_discrete_map=SRC_COLORS, hover_name="disease",
        custom_data=["category", "revenue", "prevalence_per_100k", "genes"],
        labels={"n_drugs": "# Approved Competing Drugs (in this target set)",
                "patients_est": "Estimated US Patients", "epi_source": "Prevalence source"},
        log_y=True,
    )
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>Category: %{customdata[0]}<br>"
                      "Est. US patients: %{y:,.0f}<br>Competing drugs: %{x}<br>"
                      "Known 2024 revenue: $%{customdata[1]:.2f}B<br>"
                      "Prevalence: %{customdata[2]} / 100,000<br>"
                      "Target(s): %{customdata[3]}<extra></extra>")
    fig.add_annotation(x=0.02, y=0.98, xref="paper", yref="paper", showarrow=False,
                        align="left", font=dict(size=10, color="#868E96"),
                        text="↖ high patients, few competitors = whitespace")
    fig.update_layout(
        title=dict(text="<b>Patient Population vs. Competitive Density</b><br>"
                        "<sup>bubble size ∝ known 2024 revenue · log Y axis</sup>", font=dict(size=14)),
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right"),
        margin=dict(l=10, r=10, t=70, b=40), height=480,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#F8F9FA",
        xaxis=dict(dtick=1, showgrid=True, gridcolor="#E9ECEF"),
        yaxis=dict(showgrid=True, gridcolor="#E9ECEF"))
    return fig


# ── FIG 2 — Top opportunity ranking bar ──────────────────────────────────────
def build_opportunity_bar(n=20):
    d = df_scored.sort_values("opportunity_score", ascending=False).head(n).sort_values("opportunity_score")
    fig = go.Figure(go.Bar(
        x=d["opportunity_score"], y=d["disease"], orientation="h",
        marker=dict(color=[SRC_COLORS.get(s, "#868E96") for s in d["epi_source"]],
                    line=dict(color="white", width=0.5)),
        text=[f"{v:,.0f}" for v in d["opportunity_score"]], textposition="outside",
        customdata=list(zip(d["patients_est"], d["n_drugs"], d["category"])),
        hovertemplate="<b>%{y}</b><br>Opportunity score: %{x:,.0f}<br>"
                      "Est. patients: %{customdata[0]:,.0f}<br>"
                      "Competing drugs: %{customdata[1]}<br>%{customdata[2]}<extra></extra>"))
    fig.update_layout(
        title=dict(text=f"<b>Top {len(d)} Whitespace Opportunities</b><br>"
                        "<sup>score = est. US patients ÷ (competing drugs + 1)</sup>", font=dict(size=13)),
        xaxis=dict(title="Opportunity score (patients per competitor)", showgrid=True, gridcolor="#E9ECEF"),
        yaxis=dict(tickfont=dict(size=9)),
        margin=dict(l=10, r=60, t=55, b=40), height=max(420, 26 * len(d) + 100),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#F8F9FA")
    return fig


# ── FIG 3 — Revenue vs patients (market realization check) ──────────────────
def build_revenue_vs_patients():
    d = df_scored[df_scored["revenue"] > 0].copy()
    fig = px.scatter(
        d, x="patients_est", y="revenue", color="category", color_discrete_map=CAT_COLORS,
        hover_name="disease", log_x=True,
        custom_data=["n_drugs", "genes"],
        labels={"patients_est": "Estimated US Patients (log scale)",
                "revenue": "Known 2024 Revenue (USD B)"})
    fig.update_traces(marker=dict(size=10, line=dict(color="white", width=0.5)),
        hovertemplate="<b>%{hovertext}</b><br>Est. patients: %{x:,.0f}<br>"
                      "Revenue: $%{y:.2f}B<br>Competing drugs: %{customdata[0]}<br>"
                      "Target(s): %{customdata[1]}<extra></extra>")
    fig.update_layout(
        title=dict(text="<b>Revenue Realized vs. Patient Population</b><br>"
                        "<sup>diseases below the trend = priced/penetrated below population size</sup>", font=dict(size=13)),
        showlegend=False, margin=dict(l=10, r=10, t=60, b=40), height=460,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#F8F9FA",
        xaxis=dict(showgrid=True, gridcolor="#E9ECEF"), yaxis=dict(showgrid=True, gridcolor="#E9ECEF"))
    return fig


# ── FIG 4 — Category rollup: total patients + total revenue ─────────────────
def build_category_bar():
    g = df_scored.groupby("category").agg(patients=("patients_est", "sum"),
                                           revenue=("revenue", "sum"), n=("disease", "nunique")).reset_index()
    g = g.sort_values("patients")
    fig = go.Figure(go.Bar(
        x=g["patients"], y=g["category"], orientation="h",
        marker=dict(color=[CAT_COLORS.get(c, "#868E96") for c in g["category"]], line=dict(color="white", width=0.5)),
        text=[f"{v:,.0f}" for v in g["patients"]], textposition="outside",
        customdata=list(zip(g["revenue"], g["n"])),
        hovertemplate="<b>%{y}</b><br>Est. patients: %{x:,.0f}<br>Revenue: $%{customdata[0]:.2f}B<br>%{customdata[1]} diseases<extra></extra>"))
    fig.update_layout(
        title=dict(text="<b>Estimated US Patients by Disease Category</b>", font=dict(size=13)),
        xaxis=dict(title="Estimated US Patients", showgrid=True, gridcolor="#E9ECEF"),
        yaxis=dict(tickfont=dict(size=9)), margin=dict(l=10, r=60, t=50, b=40),
        height=max(360, 24 * len(g) + 100), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#F8F9FA")
    return fig


def to_div(fig, div_id):
    fig.update_layout(autosize=True)
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id=div_id,
                       config={"responsive": True, "displaylogo": False,
                               "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"]})


# ── Final Recommendations — curated target-level calls, grounded in the ─────
# aggregated disease data above. Rule of thumb: only recommend around
# diseases clearing $5B in known 2024 revenue, with two explicit exceptions
# called out below (hemophilia franchise-level size; SSTR2/5 repositioning
# toward the CV-risk-reduction market) where the disease-level, not the
# single-drug, revenue is what clears the bar.
MARKET_BAR = 5.0  # USD B

def dstat(name):
    row = df[df["disease"] == name]
    if row.empty:
        return {"revenue": 0.0, "n_drugs": 0, "patients": None}
    r = row.iloc[0]
    return {"revenue": float(r["revenue"]), "n_drugs": int(r["n_drugs"]),
            "patients": r["patients_est"] if pd.notna(r["patients_est"]) else None}

# Total hemophilia franchise revenue: dedup by drug across every hemophilia
# A/B (+/- inhibitor) bucket, since the >$5B claim is at the disease-franchise
# level, not any single factor product.
_hemo_drugs = {}
for _dname, _b in by_disease.items():
    if "hemophilia" in _dname.lower():
        for _drug, _rev in _b["drugs"].items():
            _hemo_drugs[_drug] = max(_rev, _hemo_drugs.get(_drug, 0.0))
HEMOPHILIA_TOTAL_REVENUE = sum(_hemo_drugs.values())

RECOMMENDATIONS = [
    dict(targets=["GIPR"], drug="tirzepatide, exenatide", verdict="EXPAND", color="#0CA678",
         diseases=[("Type 2 diabetes", dstat("Type 2 diabetes")),
                   ("Obesity / weight management", dstat("Obesity / weight management"))],
         rationale="Both indications individually clear the $5B bar. Type 2 diabetes is the single "
                    "largest bucket in this dataset ($41.02B, 10 competitors) — validated but crowded. "
                    "Obesity is far less contested (2 competitors) against a very large treatable "
                    "population; GIP co-agonism is the mechanism behind the newest, best-in-class "
                    "efficacy data (tirzepatide), so incremental obesity share is the highest-confidence "
                    "expansion path for this target."),
    dict(targets=["GLP1R"], drug="semaglutide, dulaglutide, liraglutide, tirzepatide", verdict="EXPAND", color="#0CA678",
         diseases=[("Type 2 diabetes", dstat("Type 2 diabetes")),
                   ("Obesity / weight management", dstat("Obesity / weight management")),
                   ("Cardiovascular risk reduction (secondary prevention)", dstat("Cardiovascular risk reduction (secondary prevention)"))],
         rationale="Same metabolic franchise as GIPR, plus a third, distinct >$5B pool: CV-outcomes "
                    "labeling ($21.51B combined, driven by semaglutide $16.7B + dulaglutide $4.8B). "
                    "Label expansion from glycemic control into CV risk reduction — not a new drug — is "
                    "what unlocked that third pool, and is the single largest incremental revenue lever "
                    "of any target in this dataset."),
    dict(targets=["INSR"], drug="insulin aspart, glargine, lispro, icodec", verdict="DEFEND", color="#4263EB",
         diseases=[("Type 1 diabetes mellitus", dstat("Type 1 diabetes mellitus")),
                   ("Type 2 diabetes", dstat("Type 2 diabetes"))],
         rationale="Type 1 diabetes alone clears $5B ($6.5B, 1.8M patients) and insulin remains a "
                    "required component of the much larger Type 2 pool. Guideline-anchored and durable, "
                    "but structurally the slowest-growth franchise here — GIP/GLP-1 agonists are taking "
                    "the incremental T2D dollars, not insulin. Defend share; don't expect it to lead growth."),
    dict(targets=["TNF"], drug="adalimumab, etanercept, infliximab", verdict="DEFEND", color="#4263EB",
         diseases=[("Rheumatoid arthritis", dstat("Rheumatoid arthritis")),
                   ("Psoriatic arthritis", dstat("Psoriatic arthritis")),
                   ("Ankylosing spondylitis", dstat("Ankylosing spondylitis")),
                   ("Plaque psoriasis", dstat("Plaque psoriasis")),
                   ("Crohn's disease", dstat("Crohn's disease")),
                   ("Ulcerative colitis", dstat("Ulcerative colitis"))],
         rationale="The broadest label franchise in the dataset — the same 3 drugs ($13.99B combined) "
                    "clear $5B across 6+ separate indications spanning rheumatology, dermatology and GI. "
                    "That breadth is also the risk: Humira, Enbrel and Remicade are all off-patent, and "
                    "biosimilar erosion is the single biggest threat to any franchise analyzed here."),
    dict(targets=["VEGFA", "PGF"], drug="aflibercept (+ brolucizumab, faricimab, ranibizumab)", verdict="EXPAND", color="#0CA678",
         diseases=[("Neovascular (wet) AMD", dstat("Neovascular (wet) AMD")),
                   ("Diabetic macular edema (DME)", dstat("Diabetic macular edema (DME)")),
                   ("Diabetic retinopathy", dstat("Diabetic retinopathy")),
                   ("Retinal vein occlusion (BRVO / CRVO)", dstat("Retinal vein occlusion (BRVO / CRVO)"))],
         rationale="AMD and DME each clear $14.6B (shared 4-drug group); DR and RVO each clear $9.6B on "
                    "the same drugs. Diabetic retinopathy stands out as the whitespace inside an "
                    "otherwise-saturated franchise: 9.7M estimated patients against only 2 competitors, "
                    "the largest patient pool of any indication these targets already touch."),
    dict(targets=["F9", "F10"], drug="coagulation factor IX (recombinant), glycoPEGylated", verdict="FRANCHISE PLAY", color="#D97706",
         diseases=[("Hemophilia B (prophylaxis)", dstat("Hemophilia B (prophylaxis)")),
                   ("Hemophilia A (prophylaxis)", dstat("Hemophilia A (prophylaxis)")),
                   ("Hemophilia A with inhibitors (prophylaxis)", dstat("Hemophilia A with inhibitors (prophylaxis)")),
                   ("Hemophilia A/B with inhibitors", dstat("Hemophilia A/B with inhibitors"))],
         rationale=f"This specific product is only $0.4B on its own (Hemophilia B prophylaxis) — below "
                    f"the $5B bar in isolation. But the hemophilia A+B franchise this drug competes in "
                    f"totals ${HEMOPHILIA_TOTAL_REVENUE:.2f}B across factor replacement, extended-half-life "
                    f"and non-factor (emicizumab, $4.9B) products. The disease-level market is large even "
                    f"though this asset's current share isn't — the opportunity is share-shift within an "
                    f"existing >$5B pool, not category creation."),
    dict(targets=["SSTR2", "SSTR5"], drug="Lanreotide Acetate", verdict="REPOSITION", color="#AE3EC9",
         diseases=[("Dyslipidemia", dstat("Dyslipidemia")),
                   ("Cardiovascular risk reduction (secondary prevention)", dstat("Cardiovascular risk reduction (secondary prevention)")),
                   ("Acromegaly", dstat("Acromegaly"))],
         rationale="Lanreotide itself is commercially negligible today ($0.01B) — the smallest revenue "
                    "line in this entire dataset. But it already sits in the same 'Cardiovascular risk "
                    "reduction' bucket as semaglutide and dulaglutide, a $21.51B and growing market. "
                    "Somatostatin-analog effects on the GH/IGF-1 and lipid axes are the mechanistic "
                    "rationale for a fresh look here — not as a standalone play, but as an adjunct/"
                    "combination angle into a market GLP-1s are currently defining alone."),
    dict(targets=["PNLIP"], drug="pancrelipase", verdict="HOLD / NICHE", color="#868E96",
         diseases=[("Exocrine pancreatic insufficiency (EPI)", dstat("Exocrine pancreatic insufficiency (EPI)")),
                   ("Obesity / weight management", dstat("Obesity / weight management"))],
         rationale="Doesn't clear the $5B bar on its own merits: EPI is $1.5B / 837K patients with just "
                    "1 competitor — real whitespace, but sub-scale. Lipase inhibition's other outlet "
                    "(orlistat, in the $11.51B obesity market) is a legacy mechanism now eclipsed by "
                    "GIP/GLP-1 agonists. Call: hold and defend the EPI niche; not a primary growth bet."),
]

def build_recommendations_html():
    cards = []
    for rec in RECOMMENDATIONS:
        tgt_badges = "".join(f'<span class="font-monospace" style="background:#1E3A5F11;color:#1E3A5F;'
                              f'font-weight:700;padding:2px 8px;border-radius:6px;margin-right:4px;font-size:0.8rem;">{t}</span>'
                              for t in rec["targets"])
        chips = []
        for dname, s in rec["diseases"]:
            rev = s["revenue"]
            clears = rev >= MARKET_BAR
            rev_html = f'<b style="color:{"#059669" if clears else "#B54708"};">${rev:.2f}B</b>' if rev else "—"
            pat_html = f'{s["patients"]:,.0f} pts' if s["patients"] else ""
            chips.append(
                f'<div style="background:#F8F9FA;border:1px solid #E9ECEF;border-radius:8px;'
                f'padding:6px 10px;font-size:0.76rem;color:#495057;">'
                f'<div style="font-weight:700;color:#212529;">{dname}</div>'
                f'<div>{rev_html} &middot; {s["n_drugs"]} competitor(s)'
                f'{" &middot; " + pat_html if pat_html else ""}</div></div>')
        cards.append(f"""
<div class="col-md-6">
  <div class="card" style="border-left:4px solid {rec['color']};height:100%;">
    <div class="card-body">
      <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
        {tgt_badges}
        <span style="margin-left:auto;background:{rec['color']}1A;color:{rec['color']};font-weight:700;
              padding:3px 10px;border-radius:12px;font-size:0.7rem;letter-spacing:.03em;">{rec['verdict']}</span>
      </div>
      <div class="text-secondary small mb-2"><b>Drug(s):</b> {rec['drug']}</div>
      <div class="d-flex flex-wrap gap-2 mb-3">{''.join(chips)}</div>
      <div class="small" style="color:#495057;line-height:1.5;">{rec['rationale']}</div>
    </div>
  </div>
</div>""")
    return f"""
<div class="card mb-3" style="border-top:4px solid #F59F00;">
  <div class="card-body">
    <div class="d-flex align-items-center gap-2 mb-1">
      <span style="font-size:1.4rem;">&#11088;</span>
      <h2 class="mb-0" style="font-size:1.15rem;font-weight:700;">Final Recommendations — Target Priority Calls</h2>
    </div>
    <p class="text-secondary small mb-0">
      Called against a $5B known-2024-revenue bar per disease, with two explicit exceptions where the
      <i>franchise</i>/adjacent-market size — not the single asset's current revenue — is what clears it
      (hemophilia F9/F10, and SSTR2/5 repositioning toward cardiovascular risk reduction).
    </p>
  </div>
</div>
<div class="row row-deck row-cards mb-2">
{''.join(cards)}
</div>"""

print("Building figures …")
f_diskrev = build_disease_revenue_bar()
f_dtd_sankey = build_disease_target_drug_sankey()
f_scatter = build_opportunity_scatter()
f_rank = build_opportunity_bar()
f_revpat = build_revenue_vs_patients()
f_catbar = build_category_bar()
RECOMMENDATIONS_HTML = build_recommendations_html()


# ── Sortable / filterable table — same structure/style as the other two
# dashboards' tables (combined_chronic_use_dashboard.html /
# combined_chronic_use_peptide_dashboard.html): dark header row, a per-column
# filter row underneath it, category-tinted row striping, and a footer pager.
# Default sort is by revenue (descending), matching those dashboards.
def build_table_html():
    tbl_rows = []
    for _, r in df.sort_values("revenue", ascending=False).iterrows():
        tbl_rows.append({
            "disease": r["disease"], "category": r["category"], "genes": r["genes"],
            "n_drugs": int(r["n_drugs"]), "drugs_list": r["drugs_list"], "revenue": r["revenue"],
            "patients": r["patients_est"] if pd.notna(r["patients_est"]) else None,
            "score": r["opportunity_score"] if pd.notna(r["opportunity_score"]) else None,
            "source": r["epi_source"], "note": r["epi_note"] or r["excluded_note"],
        })
    tbl_json = json.dumps(tbl_rows, ensure_ascii=False)
    n = len(tbl_rows)
    cat_colors_json = json.dumps(CAT_COLORS)
    src_colors_json = json.dumps(SRC_COLORS)

    return f"""
<style>
.col-filter{{width:100%;padding:3px 5px;font-size:0.66rem;border:1px solid rgba(255,255,255,0.3);
  border-radius:4px;background:rgba(255,255,255,0.12);color:#fff;outline:none;box-sizing:border-box;}}
.col-filter::placeholder{{color:rgba(255,255,255,0.5);}}
.col-filter option{{background:#1E3A5F;color:#fff;}}
.col-filter:focus{{background:rgba(255,255,255,0.22);border-color:rgba(255,255,255,0.65);}}
</style>
<div class="card">
  <div class="card-header"><h3 class="card-title">All Disease Indications — 35-Target Dataset ({n} rows)</h3></div>
  <div style="padding:10px 16px 0;">
    <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:10px;">
      <input id="tblSearch" type="text" placeholder="Global search across all fields…"
        style="flex:1;min-width:200px;max-width:380px;padding:7px 12px;border:1px solid #E2E8F0;
               border-radius:8px;font-size:0.82rem;color:#1E293B;background:#fff;outline:none;"/>
      <button id="clearFilters" style="padding:7px 14px;background:#E2E8F0;border:none;border-radius:8px;
        font-size:0.82rem;font-weight:600;color:#64748B;cursor:pointer;"
        onmouseover="this.style.background='#CBD5E1'" onmouseout="this.style.background='#E2E8F0'">Clear All Filters</button>
      <span id="tblCount" style="font-size:0.78rem;color:#64748B;white-space:nowrap;"></span>
    </div>
    <div style="overflow-x:auto;border-radius:10px;border:1px solid #E2E8F0;box-shadow:0 1px 4px rgba(0,0,0,.06);">
      <table id="tblMain" style="width:100%;border-collapse:collapse;background:#fff;font-size:0.74rem;table-layout:fixed;">
        <colgroup>
          <col style="width:16%"/><col style="width:10%"/><col style="width:10%"/><col style="width:7%"/>
          <col style="width:20%"/><col style="width:8%"/><col style="width:10%"/><col style="width:10%"/><col style="width:9%"/>
        </colgroup>
        <thead>
          <tr style="background:#1E3A5F;color:#fff;text-align:left;">
            <th class="th-sort" data-col="disease"  style="padding:6px 8px;cursor:pointer;">Disease / Indication &#8597;</th>
            <th class="th-sort" data-col="category" style="padding:6px 8px;cursor:pointer;">Category &#8597;</th>
            <th class="th-sort" data-col="genes"    style="padding:6px 8px;cursor:pointer;">Target(s) &#8597;</th>
            <th class="th-sort" data-col="n_drugs"  style="padding:6px 8px;cursor:pointer;">Drugs &#8597;</th>
            <th class="th-sort" data-col="drugs_list" style="padding:6px 8px;cursor:pointer;">Competing Drugs &#8597;</th>
            <th class="th-sort" data-col="revenue"  style="padding:6px 8px;cursor:pointer;">Rev ($B) &#8597;</th>
            <th class="th-sort" data-col="patients" style="padding:6px 8px;cursor:pointer;">Est. US Patients &#8597;</th>
            <th class="th-sort" data-col="score"    style="padding:6px 8px;cursor:pointer;">Opportunity Score &#8597;</th>
            <th class="th-sort" data-col="source"   style="padding:6px 8px;cursor:pointer;">Source &#8597;</th>
          </tr>
          <tr style="background:#2D5A87;">
            <th style="padding:3px 5px;"><input class="col-filter" data-col="disease" placeholder="Disease…"/></th>
            <th style="padding:3px 5px;"><select class="col-filter" data-col="category" id="colCatFilter"><option value="">All categories</option></select></th>
            <th style="padding:3px 5px;"><input class="col-filter" data-col="genes" placeholder="Target…"/></th>
            <th style="padding:3px 5px;"><input class="col-filter" data-col="n_drugs" placeholder="&ge; n" type="number" min="0" step="1"/></th>
            <th style="padding:3px 5px;"><input class="col-filter" data-col="drugs_list" placeholder="Drug…"/></th>
            <th style="padding:3px 5px;"><input class="col-filter" data-col="revenue" placeholder="&ge; $B" type="number" min="0" step="0.1"/></th>
            <th style="padding:3px 5px;"><input class="col-filter" data-col="patients" placeholder="&ge; patients" type="number" min="0" step="1"/></th>
            <th style="padding:3px 5px;"><input class="col-filter" data-col="score" placeholder="&ge; score" type="number" min="0" step="1"/></th>
            <th style="padding:3px 5px;"><select class="col-filter" data-col="source" id="colSrcFilter"><option value="">All sources</option></select></th>
          </tr>
        </thead>
        <tbody id="tblBody"></tbody>
      </table>
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0;">
      <label style="font-size:0.78rem;color:#64748B;">Rows per page:
        <select id="tblPageSize" style="font-size:0.8rem;padding:4px 8px;border:1px solid #E2E8F0;border-radius:6px;margin-left:4px;">
          <option value="25">25</option><option value="50" selected>50</option><option value="100">100</option><option value="{n}">All ({n})</option>
        </select></label>
      <div id="tblPager" style="display:flex;gap:4px;flex-wrap:wrap;margin-left:auto;"></div>
    </div>
  </div>
</div>
<script>
(function(){{
const TBL=JSON.parse({json.dumps(tbl_json)});
const CATC={cat_colors_json}, SRCC={src_colors_json};
[...new Set(TBL.map(r=>r.category))].filter(Boolean).sort().forEach(c=>document.getElementById('colCatFilter').innerHTML+=`<option value="${{c}}">${{c}}</option>`);
[...new Set(TBL.map(r=>r.source))].filter(Boolean).sort().forEach(s=>document.getElementById('colSrcFilter').innerHTML+=`<option value="${{s}}">${{s}}</option>`);
const HAY_FIELDS=['disease','category','genes','drugs_list','n_drugs','revenue','patients','score','source','note'];
const _hayCache=new WeakMap();
function rowHaystack(r){{
  let h=_hayCache.get(r);
  if(h===undefined){{h=HAY_FIELDS.map(f=>r[f]==null?'':String(r[f])).join(' ').toLowerCase();_hayCache.set(r,h);}}
  return h;
}}
let sort={{col:'revenue',asc:false}}, page=0, ps=50;
function filt(){{
  const q=document.getElementById('tblSearch').value.toLowerCase(); const cf={{}};
  document.querySelectorAll('.col-filter').forEach(el=>cf[el.dataset.col]=el.value);
  return TBL.filter(r=>{{
    if(q && !rowHaystack(r).includes(q)) return false;
    if(cf.disease && !r.disease.toLowerCase().includes(cf.disease.toLowerCase())) return false;
    if(cf.category && r.category!==cf.category) return false;
    if(cf.genes && !r.genes.toLowerCase().includes(cf.genes.toLowerCase())) return false;
    if(cf.n_drugs && r.n_drugs<parseFloat(cf.n_drugs)) return false;
    if(cf.drugs_list && !r.drugs_list.toLowerCase().includes(cf.drugs_list.toLowerCase())) return false;
    if(cf.revenue && (r.revenue||0)<parseFloat(cf.revenue)) return false;
    if(cf.patients && (r.patients||0)<parseFloat(cf.patients)) return false;
    if(cf.score && (r.score||0)<parseFloat(cf.score)) return false;
    if(cf.source && r.source!==cf.source) return false;
    return true;
  }});
}}
const NUM=new Set(['n_drugs','revenue','patients','score']);
function render(){{
  let d=filt();
  if(sort.col){{const c=sort.col,a=sort.asc,isNum=NUM.has(c);
    d=[...d].sort((x,y)=>{{
      const vx=isNum?(x[c]??-1):String(x[c]||'').toLowerCase(),vy=isNum?(y[c]??-1):String(y[c]||'').toLowerCase();
      return a?(vx>vy?1:vx<vy?-1:0):(vx<vy?1:vx>vy?-1:0);}});}}
  const tot=d.length,start=page*ps,slice=ps>={n}?d:d.slice(start,start+ps);
  const b=document.getElementById('tblBody');b.innerHTML='';
  const fmtN=v=>v==null?'—':Math.round(v).toLocaleString();
  slice.forEach((r,i)=>{{
    const tr=document.createElement('tr');
    tr.style.background=i%2===0?(CATC[r.category]?CATC[r.category]+'22':'#fff'):'#F8FAFC';
    tr.style.borderBottom='1px solid #E2E8F0';
    const sc=SRCC[r.source]||'#64748B';
    tr.innerHTML=`
      <td style="padding:5px 8px;vertical-align:top;"><b style="color:#1E3A5F;">${{r.disease}}</b>${{r.note?`<div style="color:#64748B;font-size:0.68rem;line-height:1.35;margin-top:2px;">${{r.note}}</div>`:''}}</td>
      <td style="padding:5px 8px;vertical-align:top;">${{r.category||'—'}}</td>
      <td style="padding:5px 8px;vertical-align:top;font-family:monospace;font-size:0.7rem;color:#7C3AED;">${{r.genes||'—'}}</td>
      <td style="padding:5px 8px;vertical-align:top;">${{r.n_drugs}}</td>
      <td style="padding:5px 8px;vertical-align:top;color:#334155;">${{r.drugs_list||'—'}}</td>
      <td style="padding:5px 8px;vertical-align:top;">${{r.revenue?'<b style="color:#059669;">$'+r.revenue+'B</b>':'—'}}</td>
      <td style="padding:5px 8px;vertical-align:top;">${{fmtN(r.patients)}}</td>
      <td style="padding:5px 8px;vertical-align:top;">${{r.score!=null?'<b>'+fmtN(r.score)+'</b>':'—'}}</td>
      <td style="padding:5px 8px;vertical-align:top;">${{r.source?`<span style="background:${{sc}}22;color:${{sc}};font-weight:700;padding:2px 7px;border-radius:10px;font-size:0.66rem;white-space:nowrap;">${{r.source}}</span>`:'—'}}</td>`;
    b.appendChild(tr);
  }});
  document.getElementById('tblCount').textContent=tot+' / '+TBL.length+' rows';
  const np=ps>={n}?0:Math.ceil(tot/ps),pg=document.getElementById('tblPager');
  if(np<=1){{pg.innerHTML='';return;}}
  const bs=a=>`style="padding:4px 10px;border:1px solid #E2E8F0;border-radius:6px;font-size:0.78rem;cursor:pointer;background:${{a?'#1E3A5F':'#fff'}};color:${{a?'#fff':'#374151'}};"`;
  const lo=Math.max(0,Math.min(page-2,np-5)),hi=Math.min(np,lo+5);
  let h=`<button ${{bs(false)}} onclick="tblGo(${{page-1}})" ${{page===0?'disabled':''}}>&laquo;</button>`;
  for(let i=lo;i<hi;i++)h+=`<button ${{bs(i===page)}} onclick="tblGo(${{i}})">${{i+1}}</button>`;
  h+=`<button ${{bs(false)}} onclick="tblGo(${{page+1}})" ${{page>=np-1?'disabled':''}}>&raquo;</button>`;pg.innerHTML=h;
}}
window.tblGo=p=>{{const np=Math.ceil(filt().length/ps);page=Math.max(0,Math.min(p,np-1));render();document.getElementById('tblMain').scrollIntoView({{behavior:'smooth',block:'start'}});}};
document.getElementById('tblSearch').addEventListener('input',()=>{{page=0;render();}});
document.querySelectorAll('.col-filter').forEach(el=>el.addEventListener(el.tagName==='SELECT'?'change':'input',()=>{{page=0;render();}}));
document.getElementById('clearFilters').addEventListener('click',()=>{{document.getElementById('tblSearch').value='';document.querySelectorAll('.col-filter').forEach(el=>el.value='');page=0;render();}});
document.querySelectorAll('.th-sort').forEach(th=>th.addEventListener('click',()=>{{const c=th.dataset.col;if(sort.col===c)sort.asc=!sort.asc;else{{sort.col=c;sort.asc=c!=='revenue';}}page=0;render();}}));
document.getElementById('tblPageSize').addEventListener('change',function(){{ps=parseInt(this.value);page=0;render();}});
render();
}})();
</script>"""

TABLE_HTML = build_table_html()

HTML = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0"/>
<title>Target &times; Disease Opportunity Dashboard</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/core@1.0.0/dist/css/tabler.min.css"/>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
body{{background:#F8F9FA;}}
.card{{margin-bottom:1rem;}}
.navbar-brand-image{{height:1.6rem;}}
</style></head><body>
<div class="page">
<header class="navbar navbar-expand-md navbar-dark d-print-none" style="background:linear-gradient(135deg,#1E3A5F 0%,#4263EB 55%,#0CA678 100%);">
  <div class="container-xl">
    <a href="index.html" class="navbar-brand">&larr; FDA Chronic-Use Dashboards</a>
  </div>
</header>
<div class="page-wrapper">
<div class="page-header d-print-none" style="background:linear-gradient(135deg,#1E3A5F 0%,#4263EB 55%,#0CA678 100%);color:#fff;">
  <div class="container-xl py-3">
    <h2 class="page-title text-white">Target &times; Disease Opportunity Dashboard</h2>
    <p class="text-white-50 mb-0" style="max-width:820px;">
      For each disease indication in the 35-target biologics/peptide dataset:
      market size &amp; competitive landscape (known drugs + 2024 revenue, from
      the FDA Purple/Orange Book merge) matched against estimated US patient
      population &amp; unmet need (Orphanet prevalence via ToolUniverse for rare
      diseases, curated CDC/registry estimates for common ones).
    </p>
  </div>
</div>
<div class="page-body">
<div class="container-xl">

{RECOMMENDATIONS_HTML}

<div class="row row-deck row-cards mb-2">
  <div class="col-sm-6 col-lg-2-4" style="flex:1 1 0;min-width:150px;">
    <div class="card card-sm"><div class="card-body"><div class="subheader">Diseases analyzed</div><div class="h1 mb-0">{n_diseases}</div></div></div>
  </div>
  <div class="col-sm-6" style="flex:1 1 0;min-width:150px;">
    <div class="card card-sm"><div class="card-body"><div class="subheader">Scored (epi + market)</div><div class="h1 mb-0">{n_scored}</div></div></div>
  </div>
  <div class="col-sm-6" style="flex:1 1 0;min-width:150px;">
    <div class="card card-sm"><div class="card-body"><div class="subheader text-success">Rare — Orphanet-sourced</div><div class="h1 mb-0 text-success">{n_rare}</div></div></div>
  </div>
  <div class="col-sm-6" style="flex:1 1 0;min-width:150px;">
    <div class="card card-sm"><div class="card-body"><div class="subheader">Unique targets (genes)</div><div class="h1 mb-0">{n_targets}</div></div></div>
  </div>
  <div class="col-sm-6" style="flex:1 1 0;min-width:170px;">
    <div class="card card-sm"><div class="card-body"><div class="subheader">Est. US patients (scored)</div><div class="h1 mb-0">{total_patients/1e6:.1f}M</div></div></div>
  </div>
  <div class="col-sm-6" style="flex:1 1 0;min-width:170px;">
    <div class="card card-sm"><div class="card-body"><div class="subheader">Known 2024 revenue</div><div class="h1 mb-0">${total_revenue:.0f}B</div></div></div>
  </div>
</div>

<div class="row row-deck row-cards">
  <div class="col-12"><div class="card"><div class="card-body">{to_div(f_diskrev, "diskrev")}</div></div></div>
</div>
<div class="row row-deck row-cards">
  <div class="col-12"><div class="card"><div class="card-body">{to_div(f_dtd_sankey, "dtdsankey")}</div></div></div>
</div>
<div class="row row-deck row-cards">
  <div class="col-12"><div class="card"><div class="card-body">{to_div(f_scatter, "scatter")}</div></div></div>
</div>
<div class="row row-deck row-cards">
  <div class="col-lg-6"><div class="card"><div class="card-body">{to_div(f_rank, "rank")}</div></div></div>
  <div class="col-lg-6"><div class="card"><div class="card-body">{to_div(f_catbar, "catbar")}</div></div></div>
</div>
<div class="row row-deck row-cards">
  <div class="col-12"><div class="card"><div class="card-body">{to_div(f_revpat, "revpat")}</div></div></div>
</div>

<div class="row row-deck row-cards">
  <div class="col-12">{TABLE_HTML}</div>
</div>

<div class="row">
  <div class="col-12">
    <div class="card card-sm">
      <div class="card-body small text-secondary">
        <b>Methodology &amp; caveats.</b> "Competing drugs" and "revenue" count only
        drugs within this 35-target curated dataset, not all FDA-approved
        therapies for a disease — an indication can look artificially
        whitespace-y if it's mainly served by drugs outside this target list.
        Revenue is drug-level (2024, from the Purple/Orange Book build), and a
        multi-indication drug's full revenue is attributed to every disease it
        treats. Patient estimates are order-of-magnitude: rare-disease figures
        use Orphanet's own prevalence-class bucket midpoint (via the
        ToolUniverse MCP, <code>Orphanet_get_epidemiology</code>), scaled to
        the US population (335M); common-disease figures are curated from
        CDC/registry literature (see <code>opportunity_data.py</code> for the
        source note behind every number). Cosmetic indications and
        secondary-prevention labels are excluded from patient/opportunity
        scoring but still appear in the table.
      </div>
    </div>
  </div>
</div>

</div>
</div>
</div>
</div>
<script>
const IDS=['diskrev','dtdsankey','scatter','rank','catbar','revpat'];
function resizeAll(){{IDS.forEach(id=>{{const el=document.getElementById(id);if(!el||!el.data)return;
  const w=el.parentElement?el.parentElement.clientWidth-16:undefined;
  try{{Plotly.relayout(el,{{autosize:true,width:w||undefined}});}}catch(e){{}}}});}}
let _t;window.addEventListener('resize',()=>{{clearTimeout(_t);_t=setTimeout(resizeAll,150);}});
document.addEventListener('DOMContentLoaded',()=>{{let a=0;const p=setInterval(()=>{{
  if(IDS.every(id=>{{const el=document.getElementById(id);return el&&el.data;}})||a++>40){{clearInterval(p);resizeAll();}}}},150);}});
</script>
"""

BODY_MARKER = "<body>"
idx = HTML.index(BODY_MARKER) + len(BODY_MARKER)
HEAD = HTML[:idx]
HTML_BODY = HTML[idx:]

import crypto_gate
FINAL = HEAD + crypto_gate.dashboard_gate_html(HTML_BODY) + "</body></html>"

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(FINAL)
print(f"Dashboard -> {OUT_HTML}  ({len(FINAL)//1024} KB)")
print(f"Diseases: {n_diseases} total, {n_scored} scored, {n_rare} Orphanet-sourced, {n_targets} unique targets")
