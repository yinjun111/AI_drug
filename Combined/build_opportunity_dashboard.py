"""
Target x Disease Opportunity Dashboard.

Combines, per disease indication in the curated 35-target biologics/peptide
dataset (fda_all_drugs_chronic_indications_35genes.csv):
  - Disease market size + known drug-level capture: an independently
    researched global market-size estimate per disease (web-searched against
    market-research publishers — Grand View Research, Fortune Business
    Insights, Precedence Research, etc. — see opportunity_data.py's
    DISEASE_MARKET_SIZE for the full sourcing/range/caveat behind every
    number), matched against this dataset's own known 2024 drug-level
    revenue as a secondary "how much of that market do these specific drugs
    already capture" figure. Market size is the primary metric everywhere
    below — it is NOT the same thing as the drug revenue, which only
    reflects the handful of drugs in this 35-target dataset.
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

from opportunity_data import (canon, EPI_EXCLUDED, get_epi, US_POPULATION,
                               MARKET_SIZE_EXCLUDED, get_market_size)

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
    revenue = sum(b["drugs"].values())  # known drug-level revenue in THIS dataset only
    top_cat = b["cats"].most_common(1)[0][0] if b["cats"] else ""
    excluded_note = EPI_EXCLUDED.get(d)
    market_excluded_note = MARKET_SIZE_EXCLUDED.get(d)
    epi = get_epi(d)
    ms = get_market_size(d)
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
        "market_excluded": market_excluded_note is not None,
        "market_excluded_note": market_excluded_note or "",
    }
    if ms is not None:
        rec.update({
            "market_size": ms["b"], "market_size_lo": ms["lo"], "market_size_hi": ms["hi"],
            "market_size_year": ms["year"], "market_researched": ms["researched"],
            "market_note": ms["note"],
            "capture_rate": (revenue / ms["b"]) if ms["b"] else None,
        })
    else:
        rec.update({"market_size": None, "market_size_lo": None, "market_size_hi": None,
                     "market_size_year": None, "market_researched": False,
                     "market_note": "", "capture_rate": None})
    if epi is not None:
        patients = epi["prevalence_per_100k"] / 100_000 * US_POPULATION
        rec.update({
            "prevalence_per_100k": epi["prevalence_per_100k"],
            "patients_est": patients,
            "epi_source": epi["source"],
            "epi_note": epi["note"],
        })
    else:
        rec.update({"prevalence_per_100k": None, "patients_est": None,
                     "epi_source": "", "epi_note": ""})
    records.append(rec)

df = pd.DataFrame(records)
df_scored = df[~df["excluded"]].dropna(subset=["patients_est"]).copy()
df_market = df[(~df["market_excluded"]) & df["market_size"].notna()].copy()

n_diseases = len(df)
n_scored = len(df_scored)
n_rare = int((df_scored["epi_source"] == "orphanet").sum())
n_targets = len({g.strip() for gs in df["genes"] for g in gs.split(",") if g.strip()})
total_patients = df_scored["patients_est"].sum()
total_market_size = df_market["market_size"].sum()
total_revenue = df["revenue"].sum()

SRC_COLORS = {"orphanet": "#0CA678", "curated": "#4263EB"}
CAT_LIST = sorted(df["category"].unique())
_palette = (px.colors.qualitative.Safe + px.colors.qualitative.Set3 + px.colors.qualitative.Bold)
CAT_COLORS = {c: _palette[i % len(_palette)] for i, c in enumerate(CAT_LIST)}

# ── FIG 0a — Top diseases by market size (first plot) ───────────────────────
def build_disease_market_size_bar(n=25):
    d = df_market.sort_values("market_size", ascending=False).head(n).sort_values("market_size")
    fig = go.Figure(go.Bar(
        x=d["market_size"], y=d["disease"], orientation="h",
        marker=dict(color=[CAT_COLORS.get(c, "#868E96") for c in d["category"]], line=dict(color="white", width=0.5)),
        text=[f"${v:.1f}B" for v in d["market_size"]], textposition="outside",
        customdata=list(zip(d["category"], d["revenue"], d["genes"], d["market_size_year"])),
        hovertemplate="<b>%{y}</b><br>%{customdata[0]}<br>Est. market size: $%{x:.1f}B (%{customdata[3]})<br>"
                      "Known drug revenue in this dataset: $%{customdata[1]:.2f}B<br>"
                      "Target(s): %{customdata[2]}<extra></extra>"))
    fig.update_layout(
        title=dict(text=f"<b>Top {len(d)} Diseases by Market Size</b><br>"
                        "<sup>independently researched global disease/treatment market size (not this dataset's drug revenue) · colored by disease category</sup>", font=dict(size=14)),
        xaxis=dict(title="Estimated Global Market Size (USD B)", showgrid=True, gridcolor="#E9ECEF",
                   tickprefix="$", ticksuffix="B", range=[0, d["market_size"].max() * 1.18]),
        yaxis=dict(tickfont=dict(size=9)),
        margin=dict(l=10, r=70, t=60, b=40), height=max(420, 24 * len(d) + 120),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#F8F9FA")
    return fig


# ── FIG 0b — Sankey: Disease → Target → Drug (second plot) ──────────────────
# Same 3-level-Sankey pattern as the first plot on
# combined_chronic_use_peptide_dashboard.html (there: Source → Modality →
# Disease Category), but re-cut for this dataset's disease/target/drug
# relationships. Restricted to the same top-market-size diseases as FIG 0a so
# the two plots tell one connected story and the node count stays legible.
def build_disease_target_drug_sankey(n_diseases=20):
    top_diseases = set(df_market.sort_values("market_size", ascending=False).head(n_diseases)["disease"])
    disease_order = (df[df["disease"].isin(top_diseases)]
                      .sort_values("market_size", ascending=False)["disease"].tolist())

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
                        f"<sup>top {len(disease_order)} diseases by market size, and every target/drug they connect to</sup>", font=dict(size=14)),
        font=dict(size=9), margin=dict(l=10, r=10, t=60, b=10),
        height=max(560, 22 * max(len(disease_order), len(gene_list), len(drug_list)) + 100),
        paper_bgcolor="rgba(0,0,0,0)")
    return fig


# ── FIG 1 — Patient population vs. disease market size ───────────────────────
def build_market_vs_patients_scatter():
    d = df_scored[df_scored["market_size"].notna() & (~df_scored["market_excluded"])].copy()
    d["rev_size"] = d["revenue"].clip(lower=0.05) + 0.3
    fig = px.scatter(
        d, x="market_size", y="patients_est", size="rev_size", color="epi_source",
        color_discrete_map=SRC_COLORS, hover_name="disease",
        custom_data=["category", "revenue", "prevalence_per_100k", "genes"],
        labels={"market_size": "Estimated Disease Market Size (USD B)",
                "patients_est": "Estimated US Patients", "epi_source": "Prevalence source"},
        log_x=True, log_y=True,
    )
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>Category: %{customdata[0]}<br>"
                      "Est. US patients: %{y:,.0f}<br>Market size: $%{x:.1f}B<br>"
                      "Known drug revenue (this dataset): $%{customdata[1]:.2f}B<br>"
                      "Prevalence: %{customdata[2]} / 100,000<br>"
                      "Target(s): %{customdata[3]}<extra></extra>")
    fig.update_layout(
        title=dict(text="<b>Patient Population vs. Disease Market Size</b><br>"
                        "<sup>bubble size ∝ known drug revenue in this dataset · log-log</sup>", font=dict(size=14)),
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right"),
        margin=dict(l=10, r=10, t=70, b=40), height=480,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#F8F9FA",
        xaxis=dict(showgrid=True, gridcolor="#E9ECEF"),
        yaxis=dict(showgrid=True, gridcolor="#E9ECEF"))
    return fig


# ── FIG 2 — Known drug revenue vs patients (capture check, this dataset only) ─
def build_capture_vs_patients():
    d = df_scored[df_scored["revenue"] > 0].copy()
    fig = px.scatter(
        d, x="patients_est", y="revenue", color="category", color_discrete_map=CAT_COLORS,
        hover_name="disease", log_x=True,
        custom_data=["n_drugs", "genes", "market_size"],
        labels={"patients_est": "Estimated US Patients (log scale)",
                "revenue": "Known Drug Revenue in This Dataset (USD B)"})
    fig.update_traces(marker=dict(size=10, line=dict(color="white", width=0.5)),
        hovertemplate="<b>%{hovertext}</b><br>Est. patients: %{x:,.0f}<br>"
                      "Known drug revenue: $%{y:.2f}B<br>Est. market size: $%{customdata[2]:.1f}B<br>"
                      "Competing drugs: %{customdata[0]}<br>"
                      "Target(s): %{customdata[1]}<extra></extra>")
    fig.update_layout(
        title=dict(text="<b>Known Drug Revenue vs. Patient Population</b><br>"
                        "<sup>this dataset's specific drugs only — not the total disease market size shown above</sup>", font=dict(size=13)),
        showlegend=False, margin=dict(l=10, r=10, t=60, b=40), height=460,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#F8F9FA",
        xaxis=dict(showgrid=True, gridcolor="#E9ECEF"), yaxis=dict(showgrid=True, gridcolor="#E9ECEF"))
    return fig


# ── FIG 3 — Category rollup: total patients + total known drug revenue ──────
def build_category_bar():
    g = df_scored.groupby("category").agg(patients=("patients_est", "sum"),
                                           revenue=("revenue", "sum"), n=("disease", "nunique")).reset_index()
    g = g.sort_values("patients")
    fig = go.Figure(go.Bar(
        x=g["patients"], y=g["category"], orientation="h",
        marker=dict(color=[CAT_COLORS.get(c, "#868E96") for c in g["category"]], line=dict(color="white", width=0.5)),
        text=[f"{v:,.0f}" for v in g["patients"]], textposition="outside",
        customdata=list(zip(g["revenue"], g["n"])),
        hovertemplate="<b>%{y}</b><br>Est. patients: %{x:,.0f}<br>Known drug revenue: $%{customdata[0]:.2f}B<br>%{customdata[1]} diseases<extra></extra>"))
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
# researched disease market size (primary bar) with two explicit exceptions
# where a bucket has no independent market of its own (CV risk reduction,
# hemophilia inhibitor sub-populations) and this dataset's own known drug
# revenue is what carries the argument instead.
MARKET_BAR = 5.0  # USD B

def dstat(name):
    row = df[df["disease"] == name]
    if row.empty:
        return {"revenue": 0.0, "n_drugs": 0, "patients": None, "market_size": None}
    r = row.iloc[0]
    return {"revenue": float(r["revenue"]), "n_drugs": int(r["n_drugs"]),
            "patients": r["patients_est"] if pd.notna(r["patients_est"]) else None,
            "market_size": r["market_size"] if pd.notna(r["market_size"]) else None}

# Total hemophilia franchise revenue in this dataset: dedup by drug across
# every hemophilia A/B (+/- inhibitor) bucket — this dataset's own known
# capture, to compare against the researched ~$14.1-16.2B total hemophilia
# A+B market size (opportunity_data.DISEASE_MARKET_SIZE).
_hemo_drugs = {}
for _dname, _b in by_disease.items():
    if "hemophilia" in _dname.lower():
        for _drug, _rev in _b["drugs"].items():
            _hemo_drugs[_drug] = max(_rev, _hemo_drugs.get(_drug, 0.0))
HEMOPHILIA_TOTAL_REVENUE = sum(_hemo_drugs.values())
HEMOPHILIA_MARKET_SIZE = 15.15  # midpoint of researched $14.1-16.2B total hemophilia A+B market

RECOMMENDATIONS = [
    dict(targets=["GIPR"], drug="tirzepatide, exenatide", verdict="EXPAND", color="#0CA678",
         diseases=[("Type 2 diabetes", dstat("Type 2 diabetes")),
                   ("Obesity / weight management", dstat("Obesity / weight management"))],
         rationale="Both markets individually clear $5B. Type 2 diabetes is a ~$37-84B market "
                    "($60.5B midpoint) where this dataset's known drug revenue ($41.02B, 10 "
                    "competitors) already implies high capture — validated but crowded. Obesity is a "
                    "~$7-28B market ($17.5B midpoint) with only 2 competitors and known revenue "
                    "($11.51B) already close to the low end of researched estimates — GIP co-agonism "
                    "is the mechanism behind the newest, best-in-class efficacy data (tirzepatide), so "
                    "incremental obesity share is the highest-confidence expansion path for this target."),
    dict(targets=["GLP1R"], drug="semaglutide, dulaglutide, liraglutide, tirzepatide", verdict="EXPAND", color="#0CA678",
         diseases=[("Type 2 diabetes", dstat("Type 2 diabetes")),
                   ("Obesity / weight management", dstat("Obesity / weight management")),
                   ("Cardiovascular risk reduction (secondary prevention)", dstat("Cardiovascular risk reduction (secondary prevention)"))],
         rationale="Same metabolic franchise as GIPR, plus a third pool with no independent market "
                    "size of its own: CV-outcomes labeling isn't a distinct disease, but this dataset "
                    "still shows $21.51B in known drug revenue (semaglutide $16.7B + dulaglutide $4.8B) "
                    "already being generated purely from a label expansion — not a new drug — on top of "
                    "the T2D/obesity markets above. That's the single largest incremental-revenue lever "
                    "of any target in this dataset."),
    dict(targets=["INSR"], drug="insulin aspart, glargine, lispro, icodec", verdict="DEFEND", color="#4263EB",
         diseases=[("Type 1 diabetes mellitus", dstat("Type 1 diabetes mellitus")),
                   ("Type 2 diabetes", dstat("Type 2 diabetes"))],
         rationale="Type 1 diabetes alone is a $13.5-18.7B market ($16.1B midpoint, 1.8M patients) and "
                    "insulin remains a required component of the much larger Type 2 pool. Guideline-"
                    "anchored and durable, but structurally the slowest-growth franchise here — GIP/"
                    "GLP-1 agonists are taking the incremental T2D dollars, not insulin. Defend share; "
                    "don't expect it to lead growth."),
    dict(targets=["TNF"], drug="adalimumab, etanercept, infliximab", verdict="DEFEND", color="#4263EB",
         diseases=[("Rheumatoid arthritis", dstat("Rheumatoid arthritis")),
                   ("Psoriatic arthritis", dstat("Psoriatic arthritis")),
                   ("Ankylosing spondylitis", dstat("Ankylosing spondylitis")),
                   ("Plaque psoriasis", dstat("Plaque psoriasis")),
                   ("Crohn's disease", dstat("Crohn's disease")),
                   ("Ulcerative colitis", dstat("Ulcerative colitis"))],
         rationale="The broadest label franchise in the dataset — the same 3 drugs span 6+ markets "
                    "worth $6.5-33.5B each individually (RA $30.2B, plaque psoriasis $33.45B [broader "
                    "all-psoriasis figure], PsA $12.6B, Crohn's $11.85B, UC $9.28B, AS $6.5B). Known "
                    "drug revenue ($13.99B) is a small fraction of that combined total, but most of the "
                    "gap is other mechanisms (IL-17, IL-23, JAK inhibitors) sharing the same markets, not "
                    "unclaimed TNF whitespace. The real risk: Humira, Enbrel and Remicade are all "
                    "off-patent, and biosimilar erosion is the single biggest threat to any franchise "
                    "analyzed here."),
    dict(targets=["VEGFA", "PGF"], drug="aflibercept (+ brolucizumab, faricimab, ranibizumab)", verdict="EXPAND", color="#0CA678",
         diseases=[("Neovascular (wet) AMD", dstat("Neovascular (wet) AMD")),
                   ("Diabetic macular edema (DME)", dstat("Diabetic macular edema (DME)")),
                   ("Diabetic retinopathy", dstat("Diabetic retinopathy")),
                   ("Retinal vein occlusion (BRVO / CRVO)", dstat("Retinal vein occlusion (BRVO / CRVO)"))],
         rationale="AMD ($10.05B) and DME ($4.2B) are separately-sized markets on the same 4-drug "
                    "group; DR ($9.95B) and RVO ($2.6B) round it out. Diabetic retinopathy stands out as "
                    "the biggest gap in an otherwise-mature franchise: 9.7M estimated patients against "
                    "only 2 competitors and a market nearly as large as AMD's, but comparatively "
                    "under-served by label/access."),
    dict(targets=["F9", "F10"], drug="coagulation factor IX (recombinant), glycoPEGylated", verdict="FRANCHISE PLAY", color="#D97706",
         diseases=[("Hemophilia B (prophylaxis)", dstat("Hemophilia B (prophylaxis)")),
                   ("Hemophilia A (prophylaxis)", dstat("Hemophilia A (prophylaxis)")),
                   ("Hemophilia A with inhibitors (prophylaxis)", dstat("Hemophilia A with inhibitors (prophylaxis)")),
                   ("Hemophilia A/B with inhibitors", dstat("Hemophilia A/B with inhibitors"))],
         rationale=f"This specific product is only $0.4B in known revenue (Hemophilia B prophylaxis) — "
                    f"well below the $5B bar in isolation. The researched hemophilia A+B market size is "
                    f"${HEMOPHILIA_MARKET_SIZE:.1f}B (Grand View Research/Fortune Business Insights, "
                    f"$14.1-16.2B range), while this dataset's own known revenue across every hemophilia "
                    f"A/B/inhibitor drug totals only ${HEMOPHILIA_TOTAL_REVENUE:.2f}B — roughly half the "
                    f"market already captured by approved factor/non-factor products, meaning real "
                    f"remaining headroom (~${HEMOPHILIA_MARKET_SIZE - HEMOPHILIA_TOTAL_REVENUE:.1f}B) "
                    f"sits inside a disease-class market that's already proven, not a new one to create."),
    dict(targets=["SSTR2", "SSTR5"], drug="Lanreotide Acetate", verdict="REPOSITION", color="#AE3EC9",
         diseases=[("Dyslipidemia", dstat("Dyslipidemia")),
                   ("Cardiovascular risk reduction (secondary prevention)", dstat("Cardiovascular risk reduction (secondary prevention)")),
                   ("Acromegaly", dstat("Acromegaly"))],
         rationale="Lanreotide itself is commercially negligible today ($0.01B, in this dataset's "
                    "Dyslipidemia row) — the smallest revenue line here. But dyslipidemia is a real, "
                    "independently-sized $10-32B market ($21B midpoint), and the same molecule already "
                    "carries $21.51B in known label-expansion revenue (mostly semaglutide/dulaglutide) "
                    "under the adjacent CV-risk-reduction bucket. Somatostatin-analog effects on the "
                    "GH/IGF-1 and lipid axes (the mechanism class's classical use is acromegaly, a "
                    "$2.15B market) are the rationale for a fresh look here — not as a standalone play, "
                    "but as an adjunct/combination angle into a market GLP-1s are currently defining alone."),
    dict(targets=["PNLIP"], drug="pancrelipase", verdict="HOLD / NICHE", color="#868E96",
         diseases=[("Exocrine pancreatic insufficiency (EPI)", dstat("Exocrine pancreatic insufficiency (EPI)")),
                   ("Obesity / weight management", dstat("Obesity / weight management"))],
         rationale="EPI is a modest $2.3-3.0B market ($2.65B midpoint, 837K patients) where pancrelipase "
                    "already holds an estimated ~57% share ($1.5B known revenue) as the sole competitor — "
                    "real, but a mature, sub-scale niche, not a growth market. Lipase inhibition's other "
                    "outlet (orlistat, inside the $7-28B obesity market) is a legacy mechanism now "
                    "eclipsed by GIP/GLP-1 agonists. Call: hold and defend the EPI niche; not a primary "
                    "growth bet."),
]

def build_recommendations_html():
    cards = []
    for rec in RECOMMENDATIONS:
        tgt_badges = "".join(f'<span class="font-monospace" style="background:#1E3A5F11;color:#1E3A5F;'
                              f'font-weight:700;padding:2px 8px;border-radius:6px;margin-right:4px;font-size:0.8rem;">{t}</span>'
                              for t in rec["targets"])
        chips = []
        for dname, s in rec["diseases"]:
            ms = s["market_size"]
            clears = (ms or 0) >= MARKET_BAR
            if ms:
                ms_html = f'<b style="color:{"#059669" if clears else "#B54708"};">${ms:.1f}B market</b>'
            else:
                ms_html = '<span style="color:#868E96;">no independent market</span>'
            rev_html = f'${s["revenue"]:.2f}B known rev' if s["revenue"] else "no known revenue"
            pat_html = f'{s["patients"]:,.0f} pts' if s["patients"] else ""
            chips.append(
                f'<div style="background:#F8F9FA;border:1px solid #E9ECEF;border-radius:8px;'
                f'padding:6px 10px;font-size:0.76rem;color:#495057;">'
                f'<div style="font-weight:700;color:#212529;">{dname}</div>'
                f'<div>{ms_html} &middot; {rev_html}</div>'
                f'<div>{s["n_drugs"]} competitor(s)'
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
      Called against a $5B researched-market-size bar per disease, with two explicit exceptions where a
      bucket has no independent market of its own (CV risk reduction is a label on top of an
      already-counted disease; hemophilia inhibitor sub-populations aren't separately tracked) and this
      dataset's own known drug revenue carries the argument instead.
    </p>
  </div>
</div>
<div class="row row-deck row-cards mb-2">
{''.join(cards)}
</div>"""

print("Building figures …")
f_diskrev = build_disease_market_size_bar()
f_dtd_sankey = build_disease_target_drug_sankey()
f_scatter = build_market_vs_patients_scatter()
f_capture = build_capture_vs_patients()
f_catbar = build_category_bar()
RECOMMENDATIONS_HTML = build_recommendations_html()


# ── Sortable / filterable table — same structure/style as the other two
# dashboards' tables (combined_chronic_use_dashboard.html /
# combined_chronic_use_peptide_dashboard.html): dark header row, a per-column
# filter row underneath it, category-tinted row striping, and a footer pager.
# Default sort is by market size (descending) — the primary metric.
def build_table_html():
    tbl_rows = []
    for _, r in df.sort_values("market_size", ascending=False, na_position="last").iterrows():
        tbl_rows.append({
            "disease": r["disease"], "category": r["category"], "genes": r["genes"],
            "n_drugs": int(r["n_drugs"]), "drugs_list": r["drugs_list"],
            "market_size": r["market_size"] if pd.notna(r["market_size"]) else None,
            "market_note": (r["market_note"] or r["market_excluded_note"]),
            "market_researched": bool(r["market_researched"]),
            "revenue": r["revenue"],
            "patients": r["patients_est"] if pd.notna(r["patients_est"]) else None,
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
          <col style="width:15%"/><col style="width:9%"/><col style="width:9%"/><col style="width:6%"/>
          <col style="width:18%"/><col style="width:10%"/><col style="width:8%"/><col style="width:10%"/><col style="width:8%"/>
        </colgroup>
        <thead>
          <tr style="background:#1E3A5F;color:#fff;text-align:left;">
            <th class="th-sort" data-col="disease"  style="padding:6px 8px;cursor:pointer;">Disease / Indication &#8597;</th>
            <th class="th-sort" data-col="category" style="padding:6px 8px;cursor:pointer;">Category &#8597;</th>
            <th class="th-sort" data-col="genes"    style="padding:6px 8px;cursor:pointer;">Target(s) &#8597;</th>
            <th class="th-sort" data-col="n_drugs"  style="padding:6px 8px;cursor:pointer;">Drugs &#8597;</th>
            <th class="th-sort" data-col="drugs_list" style="padding:6px 8px;cursor:pointer;">Competing Drugs &#8597;</th>
            <th class="th-sort" data-col="market_size" style="padding:6px 8px;cursor:pointer;" title="Researched disease market size">Market Size ($B) &#8597;</th>
            <th class="th-sort" data-col="revenue"  style="padding:6px 8px;cursor:pointer;" title="Known drug revenue in this dataset only">Known Rev ($B) &#8597;</th>
            <th class="th-sort" data-col="patients" style="padding:6px 8px;cursor:pointer;">Est. US Patients &#8597;</th>
            <th class="th-sort" data-col="source"   style="padding:6px 8px;cursor:pointer;">Source &#8597;</th>
          </tr>
          <tr style="background:#2D5A87;">
            <th style="padding:3px 5px;"><input class="col-filter" data-col="disease" placeholder="Disease…"/></th>
            <th style="padding:3px 5px;"><select class="col-filter" data-col="category" id="colCatFilter"><option value="">All categories</option></select></th>
            <th style="padding:3px 5px;"><input class="col-filter" data-col="genes" placeholder="Target…"/></th>
            <th style="padding:3px 5px;"><input class="col-filter" data-col="n_drugs" placeholder="&ge; n" type="number" min="0" step="1"/></th>
            <th style="padding:3px 5px;"><input class="col-filter" data-col="drugs_list" placeholder="Drug…"/></th>
            <th style="padding:3px 5px;"><input class="col-filter" data-col="market_size" placeholder="&ge; $B" type="number" min="0" step="0.1"/></th>
            <th style="padding:3px 5px;"><input class="col-filter" data-col="revenue" placeholder="&ge; $B" type="number" min="0" step="0.1"/></th>
            <th style="padding:3px 5px;"><input class="col-filter" data-col="patients" placeholder="&ge; patients" type="number" min="0" step="1"/></th>
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
const esc=s=>String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const HAY_FIELDS=['disease','category','genes','drugs_list','n_drugs','market_size','revenue','patients','source','note','market_note'];
const _hayCache=new WeakMap();
function rowHaystack(r){{
  let h=_hayCache.get(r);
  if(h===undefined){{h=HAY_FIELDS.map(f=>r[f]==null?'':String(r[f])).join(' ').toLowerCase();_hayCache.set(r,h);}}
  return h;
}}
let sort={{col:'market_size',asc:false}}, page=0, ps=50;
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
    if(cf.market_size && (r.market_size||0)<parseFloat(cf.market_size)) return false;
    if(cf.revenue && (r.revenue||0)<parseFloat(cf.revenue)) return false;
    if(cf.patients && (r.patients||0)<parseFloat(cf.patients)) return false;
    if(cf.source && r.source!==cf.source) return false;
    return true;
  }});
}}
const NUM=new Set(['n_drugs','market_size','revenue','patients']);
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
    const msTitle=esc(r.market_note);
    const msBadge=r.market_researched?'':' <span style="color:#B54708;font-size:0.62rem;" title="No independently-tracked market found — showing known drug revenue as a labeled fallback">(proxy)</span>';
    tr.innerHTML=`
      <td style="padding:5px 8px;vertical-align:top;"><b style="color:#1E3A5F;">${{r.disease}}</b>${{r.note?`<div style="color:#64748B;font-size:0.68rem;line-height:1.35;margin-top:2px;">${{r.note}}</div>`:''}}</td>
      <td style="padding:5px 8px;vertical-align:top;">${{r.category||'—'}}</td>
      <td style="padding:5px 8px;vertical-align:top;font-family:monospace;font-size:0.7rem;color:#7C3AED;">${{r.genes||'—'}}</td>
      <td style="padding:5px 8px;vertical-align:top;">${{r.n_drugs}}</td>
      <td style="padding:5px 8px;vertical-align:top;color:#334155;">${{r.drugs_list||'—'}}</td>
      <td style="padding:5px 8px;vertical-align:top;cursor:help;" title="${{msTitle}}">${{r.market_size!=null?'<b style="color:#7C3AED;">$'+r.market_size.toFixed(2)+'B</b>'+msBadge:'—'}}</td>
      <td style="padding:5px 8px;vertical-align:top;">${{r.revenue?'<b style="color:#059669;">$'+r.revenue+'B</b>':'—'}}</td>
      <td style="padding:5px 8px;vertical-align:top;">${{fmtN(r.patients)}}</td>
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
document.querySelectorAll('.th-sort').forEach(th=>th.addEventListener('click',()=>{{const c=th.dataset.col;if(sort.col===c)sort.asc=!sort.asc;else{{sort.col=c;sort.asc=false;}}page=0;render();}}));
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
      For each disease indication in the 35-target biologics/peptide dataset: an independently
      researched global market-size estimate, matched against estimated US patient population &amp;
      unmet need (Orphanet prevalence via ToolUniverse for rare diseases, curated CDC/registry
      estimates for common ones), with this dataset's own known drug revenue shown separately as a
      capture-rate check.
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
    <div class="card card-sm"><div class="card-body"><div class="subheader">Est. total market size</div><div class="h1 mb-0">${total_market_size:.0f}B</div></div></div>
  </div>
  <div class="col-sm-6" style="flex:1 1 0;min-width:170px;">
    <div class="card card-sm"><div class="card-body"><div class="subheader">Known drug revenue (this dataset)</div><div class="h1 mb-0">${total_revenue:.0f}B</div></div></div>
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
  <div class="col-lg-6"><div class="card"><div class="card-body">{to_div(f_capture, "capture")}</div></div></div>
  <div class="col-lg-6"><div class="card"><div class="card-body">{to_div(f_catbar, "catbar")}</div></div></div>
</div>

<div class="row row-deck row-cards">
  <div class="col-12">{TABLE_HTML}</div>
</div>

<div class="row">
  <div class="col-12">
    <div class="card card-sm">
      <div class="card-body small text-secondary">
        <b>Methodology &amp; caveats.</b> <b>Market Size</b> is an independently researched global
        disease/treatment market-size estimate (one web search per disease against market-research
        publishers — Grand View Research, Fortune Business Insights, Precedence Research, GlobeNewswire,
        Market.us, and similar — July 2026), and is the primary metric driving every chart, the table's
        default sort, and the recommendations above. It is <i>not</i> the same thing as this dataset's
        own <b>Known Rev</b> column, which is only the 2024 revenue of the specific drugs in this
        35-target CSV. Nearly every disease showed real cross-publisher disagreement (often 2-10x)
        driven by differing scope (drugs-only vs. drugs+diagnostics, "7 major markets" vs. truly global,
        disease-subtype bundling) — hover the Market Size cell in the table for the exact range and
        sources behind each figure. A few niche/ultra-rare diseases have no independently-tracked market
        at all; those are flagged "(proxy)" and fall back to known drug revenue rather than a fabricated
        number (see <code>opportunity_data.py</code>'s <code>DISEASE_MARKET_SIZE</code> for full sourcing
        on every disease). Patient estimates are order-of-magnitude: rare-disease figures use Orphanet's
        own prevalence-class bucket midpoint (via the ToolUniverse MCP,
        <code>Orphanet_get_epidemiology</code>), scaled to the US population (335M); common-disease
        figures are curated from CDC/registry literature. Cosmetic indications and secondary-prevention
        labels are excluded from market-size/patient scoring but still appear in the table. A few drugs
        also show only a sliver of their real commercial value because this dataset is scoped to
        <i>chronic</i>-use indications only: filgrastim's $0.4B known revenue here is just its
        chronic/congenital-SCN slice — G-CSFs are the leading drug class in the much larger, mostly-acute
        ~$15.8-16.6B global neutropenia-treatment market (see the Severe chronic neutropenia row).
      </div>
    </div>
  </div>
</div>

</div>
</div>
</div>
</div>
<script>
const IDS=['diskrev','dtdsankey','scatter','capture','catbar'];
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
print(f"Total market size: ${total_market_size:.0f}B, total known drug revenue: ${total_revenue:.0f}B")
