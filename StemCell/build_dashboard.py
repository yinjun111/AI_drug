"""
Stem Cell Therapy Landscape Dashboard.

Data sources (see merge_data.py):
  - ClinicalTrials.gov full census (query.term="stem cell", 11,517 studies),
    filtered here to the 5,836 "core" rows whose title/intervention itself is
    a stem-cell product (Core_Stem_Cell_Product=='Yes' in the enriched CSV) --
    this excludes incidental mentions (e.g. a non-stem-cell drug trial in HSCT
    patients, or eligibility criteria referencing prior transplant).
  - Web/news research (English + Chinese) on stem cell companies, covering
    preclinical pipelines and globally-approved products (Japan/Korea/EU/China)
    that a US-centric clinicaltrials.gov pull misses.

Palette: the dataviz-skill validated default 8-hue categorical set (CVD-safe,
adjacent-pair validated) for identity/category series; a single blue hue for
magnitude-ranked bars; neutral gray for "Other".
"""
import csv
import json
import sys
from collections import Counter, defaultdict

import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, "/Work1/Zijiang/Combined")
import crypto_gate

SRC_CSV = "/Work1/Zijiang/StemCell/stem_cell_master.csv"
OUT_HTML = "/Work1/Zijiang/StemCell/stem_cell_dashboard.html"

CAT_PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
OTHER_COLOR = "#c3c2b7"
SEQ_BLUE = "#2a78d6"
GRID_COLOR = "#E9ECEF"
PLOT_BG = "#F8F9FA"

STAGE_ORDER = ["Preclinical", "IND-Enabling / Early Clinical", "Early Phase 1", "Phase 1",
               "Phase 1/2", "Phase 2", "Phase 1/2/3", "Phase 2/3", "Phase 3", "Phase 4",
               "Approved", "N/A (Device/Behavioral)", "Not Reported", "Unknown"]

STAGE_COLOR = {
    "Preclinical": "#898781", "IND-Enabling / Early Clinical": "#898781",
    "Early Phase 1": "#cde2fb", "Phase 1": "#9ec5f4",
    "Phase 1/2": "#6da7ec", "Phase 2": "#3987e5", "Phase 1/2/3": "#2a6bcf",
    "Phase 2/3": "#256abf", "Phase 3": "#184f95", "Phase 4": "#0d366b", "Approved": "#0ca30c",
    "N/A (Device/Behavioral)": "#898781", "Not Reported": "#898781", "Unknown": "#898781",
}

REGION_RULES = [
    ("United States", ["United States"]),
    ("China", ["China"]),
    ("South Korea", ["Korea, Republic of", "South Korea"]),
    ("Japan", ["Japan"]),
    ("Europe", ["Germany", "France", "United Kingdom", "Italy", "Spain", "Netherlands",
                "Belgium", "Poland", "Denmark", "Sweden", "Switzerland", "Austria",
                "Ireland", "Portugal", "Norway", "Finland", "Czechia", "Czech Republic",
                "Hungary", "Greece", "Romania", "European Union"]),
    ("Taiwan", ["Taiwan"]),
]


def region_of(country):
    for region, names in REGION_RULES:
        if any(n in country for n in names):
            return region
    return "Other" if country else "Not Reported"


def fold_other(counter, top_n=8):
    top = counter.most_common(top_n)
    rest = sum(v for k, v in counter.items()) - sum(v for k, v in top)
    labels = [k for k, v in top]
    values = [v for k, v in top]
    if rest > 0:
        labels.append("Other")
        values.append(rest)
    return labels, values


def cat_color_map(labels):
    m = {}
    ci = 0
    for lab in labels:
        if lab == "Other":
            m[lab] = OTHER_COLOR
        else:
            m[lab] = CAT_PALETTE[ci % len(CAT_PALETTE)]
            ci += 1
    return m


# ── Load ──────────────────────────────────────────────────────────────────
rows = list(csv.DictReader(open(SRC_CSV, encoding="utf-8-sig")))
df = pd.DataFrame(rows)
df["Stage"] = df["Stage"].replace("", "Not Reported")

n_records = len(df)
n_ct = int((df["Source"] == "ClinicalTrials.gov").sum())
n_news = int((df["Source"] == "Web/News Research").sum())
n_industry = int((df["Sponsor_Class"] == "INDUSTRY").sum())
n_sponsors = df.loc[df["Company_Sponsor"].str.len() > 0, "Company_Sponsor"].nunique()
n_approved = int((df["Stage"] == "Approved").sum())
n_preclinical = int((df["Stage"] == "Preclinical").sum())

# every row's first-listed condition, for a rough unique-disease count
first_conditions = set()
for c in df["Target_Disease"]:
    if c:
        first_conditions.add(c.split(";")[0].strip().lower())
n_diseases = len(first_conditions)

df["Region"] = df["Country"].apply(lambda c: region_of((c or "").split(";")[0].strip()))
n_china = int((df["Region"] == "China").sum())
n_china_companies = df.loc[(df["Region"] == "China") & (df["Sponsor_Class"] == "INDUSTRY")
                            & (df["Company_Sponsor"].str.len() > 0), "Company_Sponsor"].nunique()
n_gene_target = int((df["Gene_Target"].str.len() > 0).sum())

STAT_CARDS = [
    ("Total records analyzed", f"{n_records:,}", None),
    ("ClinicalTrials.gov trials", f"{n_ct:,}", None),
    ("Web/news-sourced programs", f"{n_news:,}", None),
    ("Industry-sponsored trials", f"{n_industry:,}", None),
    ("Unique sponsors/companies", f"{n_sponsors:,}", None),
    ("Distinct disease indications", f"{n_diseases:,}", None),
    ("Approved / marketed products", f"{n_approved:,}", "text-success"),
    ("Preclinical-stage programs", f"{n_preclinical:,}", None),
    ("Gene-engineered / secreting-payload programs", f"{n_gene_target:,}", None),
    ("Chinese industry sponsors", f"{n_china_companies:,}", None),
]


# ── FIG 1 — Pipeline stage bar (ordinal blue ramp) ──────────────────────────
def build_stage_fig():
    counts = Counter(df["Stage"])
    order = [s for s in STAGE_ORDER if s in counts]
    vals = [counts[s] for s in order]
    colors = [STAGE_COLOR.get(s, OTHER_COLOR) for s in order]
    fig = go.Figure(go.Bar(
        x=vals, y=order, orientation="h",
        marker=dict(color=colors, line=dict(color="white", width=0.5)),
        text=[f"{v:,}" for v in vals], textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x:,} records<extra></extra>"))
    fig.update_layout(
        title=dict(text="<b>Pipeline Stage Distribution</b><br>"
                        "<sup>clinicaltrials.gov trials + web-researched preclinical/approved programs</sup>",
                   font=dict(size=14)),
        xaxis=dict(title="Records", showgrid=True, gridcolor=GRID_COLOR, range=[0, max(vals) * 1.18]),
        yaxis=dict(categoryorder="array", categoryarray=order[::-1]),
        margin=dict(l=10, r=60, t=60, b=40), height=max(420, 32 * len(order) + 100),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PLOT_BG)
    return fig


# ── FIG 2 — Disease area bar ────────────────────────────────────────────────
def build_disease_area_fig(n=15):
    counts = Counter(a for a in df["Disease_Area"] if a)
    labels, values = fold_other(counts, top_n=n)
    cmap = cat_color_map([l for l in labels if l != "Other"])
    order = sorted(zip(labels, values), key=lambda x: x[1])
    labels = [l for l, v in order]
    values = [v for l, v in order]
    colors = [cmap.get(l, OTHER_COLOR) for l in labels]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(color=colors, line=dict(color="white", width=0.5)),
        text=[f"{v:,}" for v in values], textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x:,} records<extra></extra>"))
    fig.update_layout(
        title=dict(text="<b>Trials/Programs by Disease Area</b>", font=dict(size=14)),
        xaxis=dict(title="Records", showgrid=True, gridcolor=GRID_COLOR, range=[0, max(values) * 1.18]),
        yaxis=dict(tickfont=dict(size=10)),
        margin=dict(l=10, r=60, t=50, b=40), height=max(420, 28 * len(labels) + 100),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PLOT_BG)
    return fig


# ── FIG 3 — Top sponsors (industry) ─────────────────────────────────────────
def build_top_sponsors_fig(n=20):
    ind = df[(df["Sponsor_Class"] == "INDUSTRY") & (df["Company_Sponsor"].str.len() > 0)]
    counts = Counter(ind["Company_Sponsor"])
    top = counts.most_common(n)
    labels = [k for k, v in top][::-1]
    values = [v for k, v in top][::-1]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(color=SEQ_BLUE, line=dict(color="white", width=0.5)),
        text=[f"{v:,}" for v in values], textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x:,} trials/programs<extra></extra>"))
    fig.update_layout(
        title=dict(text=f"<b>Top {len(labels)} Industry Sponsors</b><br>"
                        "<sup>by number of stem-cell trials/programs (clinicaltrials.gov + news)</sup>",
                   font=dict(size=14)),
        xaxis=dict(title="Trials/Programs", showgrid=True, gridcolor=GRID_COLOR, range=[0, max(values) * 1.18]),
        yaxis=dict(tickfont=dict(size=10)),
        margin=dict(l=10, r=60, t=60, b=40), height=max(420, 24 * len(labels) + 100),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PLOT_BG)
    return fig


# ── FIG 4 — Sankey: Sponsor(top) -> Disease Area -> Stage ──────────────────
def build_sankey_fig(n_sponsors_top=15, n_areas_top=8):
    ind = df[(df["Sponsor_Class"] == "INDUSTRY") & (df["Company_Sponsor"].str.len() > 0) & (df["Disease_Area"].str.len() > 0)]
    top_sponsors = [k for k, v in Counter(ind["Company_Sponsor"]).most_common(n_sponsors_top)]
    sub = ind[ind["Company_Sponsor"].isin(top_sponsors)]
    top_areas = [k for k, v in Counter(sub["Disease_Area"]).most_common(n_areas_top)]
    sub = sub[sub["Disease_Area"].isin(top_areas)].copy()
    sub["Disease_Area2"] = sub["Disease_Area"].where(sub["Disease_Area"].isin(top_areas), "Other")
    stage_top = [s for s in STAGE_ORDER if s in sub["Stage"].unique()]

    area_cmap = cat_color_map(top_areas)

    labels, colors, idx = [], [], {}

    def node(key, label, color):
        idx[key] = len(labels)
        labels.append(label)
        colors.append(color)

    for s in top_sponsors:
        if s in sub["Company_Sponsor"].values:
            node(("sp", s), s, "#898781")
    for a in top_areas:
        node(("area", a), a, area_cmap.get(a, OTHER_COLOR))
    for st in stage_top:
        node(("stage", st), st, STAGE_COLOR.get(st, OTHER_COLOR))

    sa_val = Counter(zip(sub["Company_Sponsor"], sub["Disease_Area"]))
    as_val = Counter(zip(sub["Disease_Area"], sub["Stage"]))

    S, T, V, LC = [], [], [], []
    for (s, a), v in sa_val.items():
        if ("sp", s) not in idx or ("area", a) not in idx:
            continue
        S.append(idx[("sp", s)]); T.append(idx[("area", a)]); V.append(v)
        LC.append("rgba(137,135,129,0.30)")
    for (a, st), v in as_val.items():
        if ("area", a) not in idx or ("stage", st) not in idx:
            continue
        S.append(idx[("area", a)]); T.append(idx[("stage", st)]); V.append(v)
        LC.append("rgba(42,120,214,0.25)")

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(pad=10, thickness=14, line=dict(color="white", width=0.5),
                  label=labels, color=colors, hovertemplate="%{label}<extra></extra>"),
        link=dict(source=S, target=T, value=V, color=LC,
                  hovertemplate="%{source.label} → %{target.label}: %{value}<extra></extra>")))
    fig.update_layout(
        title=dict(text=f"<b>Sponsor → Disease Area → Stage</b><br>"
                        f"<sup>top {len(top_sponsors)} industry sponsors and where their programs sit</sup>",
                   font=dict(size=14)),
        font=dict(size=9), margin=dict(l=10, r=10, t=60, b=10),
        height=max(560, 22 * max(len(top_sponsors), len(top_areas), len(stage_top)) + 100),
        paper_bgcolor="rgba(0,0,0,0)")
    return fig


# ── FIG 5 — Geography ───────────────────────────────────────────────────────
def build_geo_fig(n=15):
    all_countries = Counter()
    for c in df["Country"]:
        for name in [x.strip() for x in (c or "").split(";") if x.strip()]:
            all_countries[name] += 1
    top = all_countries.most_common(n)
    labels = [k for k, v in top][::-1]
    values = [v for k, v in top][::-1]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(color=SEQ_BLUE, line=dict(color="white", width=0.5)),
        text=[f"{v:,}" for v in values], textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x:,} trial-country records<extra></extra>"))
    fig.update_layout(
        title=dict(text="<b>Top Countries by Trial Site</b><br>"
                        "<sup>counts trial×country pairs — a trial with sites in multiple countries counts once per country</sup>",
                   font=dict(size=13)),
        xaxis=dict(title="Records", showgrid=True, gridcolor=GRID_COLOR, range=[0, max(values) * 1.18]),
        yaxis=dict(tickfont=dict(size=10)),
        margin=dict(l=10, r=60, t=60, b=40), height=max(420, 24 * len(labels) + 100),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PLOT_BG)
    return fig


# ── FIG 6 — Cell type breakdown ──────────────────────────────────────────────
def build_cell_type_fig():
    counts = Counter(t for t in df["Cell_Type"] if t)
    labels, values = fold_other(counts, top_n=8)
    cmap = cat_color_map([l for l in labels if l != "Other"])
    order = sorted(zip(labels, values), key=lambda x: x[1])
    labels = [l for l, v in order]
    values = [v for l, v in order]
    colors = [cmap.get(l, OTHER_COLOR) for l in labels]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(color=colors, line=dict(color="white", width=0.5)),
        text=[f"{v:,}" for v in values], textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x:,} records<extra></extra>"))
    fig.update_layout(
        title=dict(text="<b>Cell Type</b>", font=dict(size=13)),
        xaxis=dict(title="Records", showgrid=True, gridcolor=GRID_COLOR, range=[0, max(values) * 1.18]),
        yaxis=dict(tickfont=dict(size=10)),
        margin=dict(l=10, r=60, t=50, b=40), height=max(360, 28 * len(labels) + 100),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PLOT_BG)
    return fig


# ── FIG 7 — Chinese companies: pipeline stage by disease area ──────────────
PROGRESS_STAGE_ORDER = ["Preclinical", "IND-Enabling / Early Clinical", "Early Phase 1", "Phase 1",
                         "Phase 1/2", "Phase 2", "Phase 1/2/3", "Phase 2/3", "Phase 3", "Phase 4",
                         "Approved"]
PROGRESS_STAGE_RANK = {s: i for i, s in enumerate(PROGRESS_STAGE_ORDER)}


def build_china_companies_fig():
    sub = df[(df["Sponsor_Class"] == "INDUSTRY") & (df["Region"] == "China")
             & (df["Company_Sponsor"].str.len() > 0)].copy()
    sub = sub[sub["Stage"].isin(PROGRESS_STAGE_RANK)]
    if sub.empty:
        return None
    sub["stage_rank"] = sub["Stage"].map(PROGRESS_STAGE_RANK)
    sub["Disease_Area"] = sub["Disease_Area"].replace("", "Other / Unclassified")

    # one marker per company at its furthest disclosed stage; hover rolls up
    # every program/disease tracked for that company
    agg = sub.groupby("Company_Sponsor").agg(
        stage_rank=("stage_rank", "max"),
        n_programs=("Stage", "size"),
        diseases=("Target_Disease", lambda s: "; ".join(sorted({x.split(";")[0].strip() for x in s if x}))[:200]),
        products=("Product_Name", lambda s: "; ".join(sorted({x.strip() for x in s if x}))[:200]),
    ).reset_index()
    top_area = (sub.sort_values("stage_rank", ascending=False)
                   .drop_duplicates("Company_Sponsor")[["Company_Sponsor", "Disease_Area"]])
    agg = agg.merge(top_area, on="Company_Sponsor")
    agg["stage_label"] = agg["stage_rank"].map(lambda i: PROGRESS_STAGE_ORDER[i])
    agg = agg.sort_values(["stage_rank", "Company_Sponsor"], ascending=[True, False])
    company_order = agg["Company_Sponsor"].tolist()

    # fold to a fixed top-6 + "Other" so the legend stays a single row —
    # matching the fold_other convention used by every other chart here
    top_areas, _ = fold_other(Counter(agg["Disease_Area"]), top_n=6)
    area_cmap = cat_color_map([a for a in top_areas if a != "Other"])
    agg["Area_Bucket"] = agg["Disease_Area"].where(agg["Disease_Area"].isin(top_areas), "Other")
    bucket_order = [a for a in top_areas if a in set(agg["Area_Bucket"])]

    fig = go.Figure()
    for area in bucket_order:
        d = agg[agg["Area_Bucket"] == area]
        color = area_cmap.get(area, OTHER_COLOR)
        legend_name = area if area != "Other" else "Other disease area"
        fig.add_trace(go.Scatter(
            x=d["stage_rank"], y=d["Company_Sponsor"], mode="markers", name=legend_name,
            marker=dict(size=15, color=color, line=dict(color="white", width=1)),
            customdata=list(zip(d["stage_label"], d["diseases"], d["n_programs"], d["products"], d["Disease_Area"])),
            hovertemplate="<b>%{y}</b><br>Furthest stage: %{customdata[0]}<br>"
                          "Disease area: %{customdata[4]}<br>Disease(s): %{customdata[1]}<br>"
                          "Product(s): %{customdata[3]}<br>Programs tracked: %{customdata[2]}<extra></extra>"))

    n_legend_rows = 1 if len(bucket_order) <= 7 else 2
    fig.update_layout(
        title=dict(text="<b>Chinese Stem Cell Companies — Pipeline Stage</b><br>"
                        "<sup>furthest disclosed stage per company, from web/news research + China industry-sponsored clinicaltrials.gov trials · color = disease area</sup>",
                   font=dict(size=14)),
        xaxis=dict(title="Furthest Stage", tickmode="array", tickvals=list(range(len(PROGRESS_STAGE_ORDER))),
                   ticktext=PROGRESS_STAGE_ORDER, tickangle=-25, range=[-0.6, len(PROGRESS_STAGE_ORDER) - 0.4],
                   showgrid=True, gridcolor=GRID_COLOR),
        yaxis=dict(categoryorder="array", categoryarray=company_order, tickfont=dict(size=10)),
        legend=dict(orientation="h", y=1.0, yanchor="bottom", x=0.5, xanchor="center", font=dict(size=10)),
        margin=dict(l=10, r=20, t=110 + 22 * n_legend_rows, b=60),
        height=max(420, 32 * len(company_order) + 140 + 22 * n_legend_rows),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PLOT_BG)
    return fig


def to_div(fig, div_id):
    fig.update_layout(autosize=True)
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id=div_id,
                       config={"responsive": True, "displaylogo": False,
                               "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"]})


f_stage = build_stage_fig()
f_area = build_disease_area_fig()
f_sponsors = build_top_sponsors_fig()
f_sankey = build_sankey_fig()
f_geo = build_geo_fig()
f_celltype = build_cell_type_fig()
f_china = build_china_companies_fig()


# ── Approved / notable products table ───────────────────────────────────────
approved_rows = df[df["Stage"] == "Approved"].to_dict("records")


def approved_cards_html():
    if not approved_rows:
        return "<p class='text-secondary'>No approved/marketed products identified in this pull.</p>"
    cards = []
    for r in approved_rows:
        disease = (r["Target_Disease"] or "").split(";")[0]
        cards.append(f"""
        <div class="col-md-4 mb-3">
          <div class="card card-sm h-100">
            <div class="card-body">
              <div class="text-success fw-bold small mb-1">APPROVED</div>
              <div class="fw-bold">{r['Product_Name'] or r['Notes'] or '—'}</div>
              <div class="text-secondary small">{r['Company_Sponsor'] or '—'}</div>
              <div class="small mt-1">{disease}</div>
              <div class="text-secondary" style="font-size:0.7rem;">{r['Country'] or ''}</div>
            </div>
          </div>
        </div>""")
    return f"<div class='row'>{''.join(cards)}</div>"


APPROVED_HTML = approved_cards_html()


# ── Data table ───────────────────────────────────────────────────────────────
def build_table_html():
    return """
<div class="card" id="tblMain">
  <div class="card-header">
    <h3 class="card-title">All Records</h3>
  </div>
  <div class="card-body border-bottom py-2">
    <div class="d-flex flex-wrap gap-2 align-items-center">
      <input type="text" id="tblSearch" class="form-control form-control-sm" style="max-width:260px;" placeholder="Search all columns…">
      <select class="form-select form-select-sm col-filter" data-col="source" style="max-width:170px;"><option value="">Source (all)</option></select>
      <select class="form-select form-select-sm col-filter" data-col="area" style="max-width:200px;"><option value="">Disease area (all)</option></select>
      <select class="form-select form-select-sm col-filter" data-col="stage" style="max-width:170px;"><option value="">Stage (all)</option></select>
      <select class="form-select form-select-sm col-filter" data-col="region" style="max-width:170px;"><option value="">Region (all)</option></select>
      <button class="btn btn-sm btn-outline-secondary" id="clearFilters">Clear</button>
      <span class="ms-auto text-secondary small" id="tblCount"></span>
    </div>
  </div>
  <div class="table-responsive">
    <table class="table table-sm table-vcenter card-table">
      <thead><tr>
        <th class="th-sort" data-col="sponsor" style="cursor:pointer;">Sponsor / Company</th>
        <th class="th-sort" data-col="disease" style="cursor:pointer;">Target Disease</th>
        <th class="th-sort" data-col="area" style="cursor:pointer;">Disease Area</th>
        <th class="th-sort" data-col="cell_type" style="cursor:pointer;">Cell Type</th>
        <th class="th-sort" data-col="gene_target" style="cursor:pointer;">Gene/Payload Expressed</th>
        <th class="th-sort" data-col="stage" style="cursor:pointer;">Stage</th>
        <th class="th-sort" data-col="status" style="cursor:pointer;">Status</th>
        <th class="th-sort" data-col="region" style="cursor:pointer;">Region</th>
        <th class="th-sort" data-col="source" style="cursor:pointer;">Source</th>
      </tr></thead>
      <tbody id="tblBody"></tbody>
    </table>
  </div>
  <div class="card-footer d-flex align-items-center gap-2">
    <div class="btn-group" id="tblPager"></div>
    <select class="form-select form-select-sm ms-auto" id="tblPageSize" style="max-width:110px;">
      <option value="50">50 / page</option>
      <option value="100">100 / page</option>
      <option value="9999999">All</option>
    </select>
  </div>
</div>"""


def esc_txt(s, n=None):
    s = (s or "").strip()
    if n and len(s) > n:
        s = s[:n - 1] + "…"
    return s


TBL = []
for _, r in df.iterrows():
    disease_first = esc_txt((r["Target_Disease"] or "").split(";")[0], 90)
    TBL.append({
        "sponsor": esc_txt(r["Company_Sponsor"], 60) or "—",
        "disease": disease_first or "—",
        "area": r["Disease_Area"] or "Other / Unclassified",
        "cell_type": r["Cell_Type"] or "Unspecified",
        "gene_target": esc_txt(r["Gene_Target"], 90) or "—",
        "stage": r["Stage"],
        "status": r["Status"] or "—",
        "region": r["Region"],
        "source": r["Source"],
        "url": r["Source_URL"],
        "notes": esc_txt(r["Notes"], 140),
    })

TABLE_HTML = build_table_html()
n_tbl = len(TBL)
TBL_JSON = json.dumps(TBL, ensure_ascii=False)

HTML = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0"/>
<title>Stem Cell Therapy Landscape Dashboard</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/core@1.0.0/dist/css/tabler.min.css"/>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
body{{background:#F8F9FA;}}
.card{{margin-bottom:1rem;}}
.navbar-brand-image{{height:1.6rem;}}
</style></head><body>
<div class="page">
<div class="page-wrapper">
<div class="page-header d-print-none" style="background:linear-gradient(135deg,#1a2f4a 0%,#2a78d6 55%,#1baf7a 100%);color:#fff;">
  <div class="container-xl py-3">
    <h2 class="page-title text-white">Stem Cell Therapy Landscape Dashboard</h2>
    <p class="text-white-50 mb-0" style="max-width:900px;">
      Full census of ClinicalTrials.gov studies mentioning "stem cell" ({n_ct:,} core trials after
      filtering out incidental mentions, out of 11,517 raw hits), combined with English- and
      Chinese-language web/news research ({n_news:,} programs) covering preclinical pipelines and
      globally-approved products that a US-centric trial registry search misses.
    </p>
  </div>
</div>
<div class="page-body">
<div class="container-xl">

<div class="row row-deck row-cards mb-2">
{''.join(f'''  <div class="col-sm-6 col-lg-3" style="flex:1 1 0;min-width:160px;">
    <div class="card card-sm"><div class="card-body"><div class="subheader">{label}</div><div class="h1 mb-0 {cls or ''}">{val}</div></div></div>
  </div>
''' for label, val, cls in STAT_CARDS)}
</div>

<div class="row row-deck row-cards">
  <div class="col-lg-6"><div class="card"><div class="card-body">{to_div(f_stage, "stage")}</div></div></div>
  <div class="col-lg-6"><div class="card"><div class="card-body">{to_div(f_area, "area")}</div></div></div>
</div>
<div class="row row-deck row-cards">
  <div class="col-12"><div class="card"><div class="card-body">{to_div(f_sankey, "sankey")}</div></div></div>
</div>
<div class="row row-deck row-cards">
  <div class="col-lg-6"><div class="card"><div class="card-body">{to_div(f_sponsors, "sponsors")}</div></div></div>
  <div class="col-lg-6"><div class="card"><div class="card-body">{to_div(f_geo, "geo")}</div></div></div>
</div>
<div class="row row-deck row-cards">
  <div class="col-12"><div class="card"><div class="card-body">{to_div(f_celltype, "celltype")}</div></div></div>
</div>

{f'''<div class="row row-deck row-cards">
  <div class="col-12"><div class="card"><div class="card-body">{to_div(f_china, "china")}</div></div></div>
</div>''' if f_china is not None else ''}

<div class="row row-deck row-cards">
  <div class="col-12">
    <div class="card">
      <div class="card-header"><h3 class="card-title">Approved / Marketed Products</h3></div>
      <div class="card-body">{APPROVED_HTML}</div>
    </div>
  </div>
</div>

<div class="row row-deck row-cards">
  <div class="col-12">{TABLE_HTML}</div>
</div>

<div class="row">
  <div class="col-12">
    <div class="card card-sm">
      <div class="card-body small text-secondary">
        <b>Methodology &amp; caveats.</b> <b>ClinicalTrials.gov</b> data is a full census pulled via the
        public API v2 (<code>query.term="stem cell"</code>, {11517:,} raw studies as of 2026-07-24), then
        flagged <b>Core_Stem_Cell_Product</b> by a keyword match on trial title/intervention (stem cell,
        MSC/mesenchymal, HSC/hematopoietic stem, cord blood, iPSC, embryonic stem, progenitor cell,
        adipose-derived, stromal) — this filters out trials that only mention stem cells incidentally
        (e.g. a non-stem-cell drug studied in prior-HSCT patients, or an eligibility-criteria reference),
        leaving {n_ct:,} core stem-cell-therapy trials. ClinicalTrials.gov registers <i>trials</i>, so it
        structurally cannot show preclinical-stage programs, and only rarely marks a study
        "Approved for Marketing" — both the <b>Preclinical</b> stage and most <b>Approved</b> entries in
        this dashboard come from the separate web/news research pass ({n_news:,} programs, English +
        Chinese sources), which specifically targeted companies and approved products (Japan, Korea, EU,
        China, US) outside what a US-centric trial registry search would surface. Disease Area, Cell
        Type, and Stage are derived by keyword/phase mapping and are approximate categorizations, not
        clinical adjudication. Geography counts trial&times;country pairs (a multi-site trial counts once
        per country), not unique trials. <b>Gene/Payload Expressed</b> flags cell products engineered to
        express or secrete an extra gene/protein beyond the native cell (e.g. Brainstorm-Cell
        Therapeutics' NurOwn secreting BDNF/GDNF/VEGF/HGF, Century Therapeutics' CD19-CAR iPSC-NK cells,
        or 北京吉源生物's GLP-1/FGF21-expressing adipose stem cells for type 2 diabetes) — detected by
        keyword match on trial title/intervention for ClinicalTrials.gov rows (low recall: most
        engineered payloads are only documented in the full protocol, so a blank cell does not mean
        "unmodified") and manually researched for web/news-sourced company rows. It is a distinct concept
        from Cell Type (the base cell platform) and is <i>not</i> populated for the great majority of
        records, which use unmodified/native cells.
      </div>
    </div>
  </div>
</div>

</div>
</div>
</div>
</div>
<script>
(function(){{
const TBL=JSON.parse({json.dumps(TBL_JSON)});
const esc=s=>String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
[...new Set(TBL.map(r=>r.source))].filter(Boolean).sort().forEach(v=>document.querySelector('[data-col=source]').innerHTML+=`<option value="${{esc(v)}}">${{esc(v)}}</option>`);
[...new Set(TBL.map(r=>r.area))].filter(Boolean).sort().forEach(v=>document.querySelector('[data-col=area]').innerHTML+=`<option value="${{esc(v)}}">${{esc(v)}}</option>`);
[...new Set(TBL.map(r=>r.stage))].filter(Boolean).sort().forEach(v=>document.querySelector('[data-col=stage]').innerHTML+=`<option value="${{esc(v)}}">${{esc(v)}}</option>`);
[...new Set(TBL.map(r=>r.region))].filter(Boolean).sort().forEach(v=>document.querySelector('[data-col=region]').innerHTML+=`<option value="${{esc(v)}}">${{esc(v)}}</option>`);
const HAY_FIELDS=['sponsor','disease','area','cell_type','gene_target','stage','status','region','source','notes'];
const _hayCache=new WeakMap();
function rowHaystack(r){{
  let h=_hayCache.get(r);
  if(h===undefined){{h=HAY_FIELDS.map(f=>r[f]==null?'':String(r[f])).join(' ').toLowerCase();_hayCache.set(r,h);}}
  return h;
}}
let sort={{col:null,asc:true}}, page=0, ps=50;
function filt(){{
  const q=document.getElementById('tblSearch').value.toLowerCase(); const cf={{}};
  document.querySelectorAll('.col-filter').forEach(el=>cf[el.dataset.col]=el.value);
  return TBL.filter(r=>{{
    if(q && !rowHaystack(r).includes(q)) return false;
    if(cf.source && r.source!==cf.source) return false;
    if(cf.area && r.area!==cf.area) return false;
    if(cf.stage && r.stage!==cf.stage) return false;
    if(cf.region && r.region!==cf.region) return false;
    return true;
  }});
}}
function render(){{
  let d=filt();
  if(sort.col){{const c=sort.col,a=sort.asc;
    d=[...d].sort((x,y)=>{{
      const vx=String(x[c]||'').toLowerCase(),vy=String(y[c]||'').toLowerCase();
      return a?(vx>vy?1:vx<vy?-1:0):(vx<vy?1:vx>vy?-1:0);}});}}
  const tot=d.length,start=page*ps,slice=ps>={n_tbl}?d:d.slice(start,start+ps);
  const b=document.getElementById('tblBody');b.innerHTML='';
  const STAGEC={json.dumps(STAGE_COLOR)};
  slice.forEach((r,i)=>{{
    const tr=document.createElement('tr');
    tr.style.background=i%2===0?'#fff':'#F8FAFC';
    tr.style.borderBottom='1px solid #E2E8F0';
    const sc=STAGEC[r.stage]||'#c3c2b7';
    const link=r.url?`<a href="${{esc(r.url)}}" target="_blank" rel="noopener">${{esc(r.sponsor)}}</a>`:esc(r.sponsor);
    tr.innerHTML=`
      <td style="padding:5px 8px;vertical-align:top;"><b>${{link}}</b>${{r.notes?`<div style="color:#64748B;font-size:0.68rem;line-height:1.3;margin-top:2px;">${{esc(r.notes)}}</div>`:''}}</td>
      <td style="padding:5px 8px;vertical-align:top;">${{esc(r.disease)}}</td>
      <td style="padding:5px 8px;vertical-align:top;">${{esc(r.area)}}</td>
      <td style="padding:5px 8px;vertical-align:top;">${{esc(r.cell_type)}}</td>
      <td style="padding:5px 8px;vertical-align:top;font-size:0.75rem;color:#7C3AED;">${{esc(r.gene_target)}}</td>
      <td style="padding:5px 8px;vertical-align:top;"><span style="background:${{sc}}22;color:${{sc}};font-weight:700;padding:2px 7px;border-radius:10px;font-size:0.68rem;white-space:nowrap;">${{esc(r.stage)}}</span></td>
      <td style="padding:5px 8px;vertical-align:top;font-size:0.75rem;">${{esc(r.status)}}</td>
      <td style="padding:5px 8px;vertical-align:top;">${{esc(r.region)}}</td>
      <td style="padding:5px 8px;vertical-align:top;font-size:0.72rem;color:#64748B;">${{esc(r.source)}}</td>`;
    b.appendChild(tr);
  }});
  document.getElementById('tblCount').textContent=tot+' / '+TBL.length+' rows';
  const np=ps>={n_tbl}?0:Math.ceil(tot/ps),pg=document.getElementById('tblPager');
  if(np<=1){{pg.innerHTML='';return;}}
  const bs=a=>`style="padding:4px 10px;border:1px solid #E2E8F0;border-radius:6px;font-size:0.78rem;cursor:pointer;background:${{a?'#1E3A5F':'#fff'}};color:${{a?'#fff':'#374151'}};"`;
  const lo=Math.max(0,Math.min(page-2,np-5)),hi=Math.min(np,lo+5);
  let h=`<button ${{bs(false)}} onclick="tblGo(${{page-1}})" ${{page===0?'disabled':''}}>&laquo;</button>`;
  for(let i=lo;i<hi;i++)h+=`<button ${{bs(i===page)}} onclick="tblGo(${{i}})">${{i+1}}</button>`;
  h+=`<button ${{bs(false)}} onclick="tblGo(${{page+1}})" ${{page>=np-1?'disabled':''}}>&raquo;</button>`;pg.innerHTML=h;
}}
window.tblGo=p=>{{const np=Math.ceil(filt().length/ps);page=Math.max(0,Math.min(p,np-1));render();document.getElementById('tblMain').scrollIntoView({{behavior:'smooth',block:'start'}});}};
document.getElementById('tblSearch').addEventListener('input',()=>{{page=0;render();}});
document.querySelectorAll('.col-filter').forEach(el=>el.addEventListener('change',()=>{{page=0;render();}}));
document.getElementById('clearFilters').addEventListener('click',()=>{{document.getElementById('tblSearch').value='';document.querySelectorAll('.col-filter').forEach(el=>el.value='');page=0;render();}});
document.querySelectorAll('.th-sort').forEach(th=>th.addEventListener('click',()=>{{const c=th.dataset.col;if(sort.col===c)sort.asc=!sort.asc;else{{sort.col=c;sort.asc=true;}}page=0;render();}}));
document.getElementById('tblPageSize').addEventListener('change',function(){{ps=parseInt(this.value);page=0;render();}});
render();
}})();
</script>
<script>
const IDS=['stage','area','sankey','sponsors','geo','celltype'{",'china'" if f_china is not None else ""}];
function resizeAll(){{IDS.forEach(id=>{{const el=document.getElementById(id);if(!el||!el.data)return;
  const w=el.parentElement?el.parentElement.clientWidth-16:undefined;
  try{{Plotly.relayout(el,{{autosize:true,width:w||undefined}});}}catch(e){{}}}});}}
let _t;window.addEventListener('resize',()=>{{clearTimeout(_t);_t=setTimeout(resizeAll,150);}});
document.addEventListener('DOMContentLoaded',()=>{{let a=0;const p=setInterval(()=>{{
  if(IDS.every(id=>{{const el=document.getElementById(id);return el&&el.data;}})||a++>40){{clearInterval(p);resizeAll();}}}},150);}});
</script>
</body></html>"""

BODY_MARKER = "<body>"
idx = HTML.index(BODY_MARKER) + len(BODY_MARKER)
HEAD = HTML[:idx]
HTML_BODY = HTML[idx:]
FINAL = HEAD + crypto_gate.dashboard_gate_html(HTML_BODY) + "</body></html>"

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(FINAL)
print(f"Dashboard -> {OUT_HTML}  ({len(FINAL)//1024} KB, password-gated)")
print(f"Records: {n_records}, CT trials: {n_ct}, news: {n_news}, sponsors: {n_sponsors}, "
      f"diseases: {n_diseases}, approved: {n_approved}, preclinical: {n_preclinical}")
