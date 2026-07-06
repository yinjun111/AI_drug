"""
Peptide / protein-focused chronic-use dashboard.

Reads the pre-filtered peptide subset fda_all_drugs_chronic_indications_peptide.csv
(same long-format schema as the full merged file, one row per drug-disease pair,
Source + Modality columns) and builds combined_chronic_use_peptide_dashboard.html
with the same set of plots + sortable/filterable table as the combined dashboard.
"""

import csv, json, re, io
from collections import defaultdict, Counter
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from aav_suitability import AAV_SUITABILITY

PEPTIDE_CSV = "fda_all_drugs_chronic_indications_peptide.csv"
OUT_HTML    = "combined_chronic_use_peptide_dashboard.html"

COLS = ["Source", "Drug", "Brand", "Disease / Indication", "Disease Category",
        "Modality", "Drug Target (Gene)", "Annual Revenue 2024 (USD B)",
        "Dose", "Frequency", "Duration of Use",
        "Amino Acid Length", "Molecular Weight (Da)",
        "AAV Suitability", "AAV Rationale"]

def norm_target(t: str) -> str:
    return re.sub(r"\s*\|\s*", ", ", (t or "").strip())

# ── Read peptide CSV (repair corrupted en-dash bytes from Excel roundtrip) ────
def load_peptide_csv(path):
    raw = open(path, "rb").read()
    raw = raw.replace(b"\x3f\x80\x3f", "–".encode("utf-8"))   # '? \x80 ?' -> '–'
    text = raw.decode("utf-8", errors="replace").replace("�", "")
    rows = []
    for r in csv.DictReader(io.StringIO(text)):
        rows.append({
            "Source": (r["Source"] or "").strip(),
            "Drug": (r["Drug"] or "").strip(),
            "Brand": (r["Brand"] or "").strip(),
            "Disease / Indication": (r["Disease / Indication"] or "").strip(),
            "Disease Category": (r["Disease Category"] or "").strip(),
            "Modality": (r["Modality"] or "").strip(),
            "Drug Target (Gene)": norm_target(r["Drug Target (Gene)"]),
            "Annual Revenue 2024 (USD B)": (r["Annual Revenue 2024 (USD B)"] or "").strip(),
            "Dose": (r["Dose"] or "").strip(),
            "Frequency": (r["Frequency"] or "").strip(),
            "Duration of Use": (r["Duration of Use"] or "").strip(),
            "Amino Acid Length": (r.get("Amino Acid Length") or "").strip(),
            "Molecular Weight (Da)": (r.get("Molecular Weight (Da)") or "").strip(),
        })
    # Attach AAV suitability from the module (source of truth), so the dashboard
    # is correct even if the CSV on disk hasn't been refreshed (e.g. Excel lock).
    for row in rows:
        score, _kb, rationale = AAV_SUITABILITY.get(row["Drug"], ("", None, ""))
        row["AAV Suitability"] = score
        row["AAV Rationale"] = rationale
    return rows

merged = load_peptide_csv(PEPTIDE_CSV)
n_pb = sum(1 for m in merged if m["Source"] == "Purple Book")
n_ob = sum(1 for m in merged if m["Source"] == "Orange Book")
print(f"Peptide rows: {len(merged)}  (Purple Book {n_pb}, Orange Book {n_ob})")

# ══════════════════════════════════════════════════════════════════════════
# Build dashboard from peptide data
# ══════════════════════════════════════════════════════════════════════════
df = pd.DataFrame(merged)
df["rev"] = pd.to_numeric(df["Annual Revenue 2024 (USD B)"], errors="coerce").fillna(0.0)

SRC_COLORS = {"Purple Book": "#7C3AED", "Orange Book": "#D97706"}
MOD_COLORS = {
    # Purple Book biologic formats
    "Monoclonal Antibody": "#7C3AED", "Fusion Protein": "#A855F7",
    "Enzyme / Protein Replacement": "#C084FC", "Peptide / Hormone": "#6D28D9",
    "Polyclonal Immunoglobulin": "#9333EA", "Allergen / Vaccine": "#D8B4FE",
    "Biologic": "#7C3AED",
    # Orange Book GSRS substance classes
    "chemical": "#2563EB", "protein": "#0EA5E9", "nucleicAcid": "#0891B2",
    "polymer": "#D97706", "mixture": "#059669", "structurallyDiverse": "#DC2626",
    "concept": "#9CA3AF", "specifiedSubstanceG1": "#F97316", "unknown": "#6B7280",
}

# Distinct category palette (granular PB scheme)
_cat_list = sorted(df["Disease Category"].unique())
_palette = (px.colors.qualitative.Safe + px.colors.qualitative.Set3
            + px.colors.qualitative.Pastel + px.colors.qualitative.Bold
            + px.colors.qualitative.Dark24)
CAT_COLORS = {c: _palette[i % len(_palette)] for i, c in enumerate(_cat_list)}
def cat_color(c): return CAT_COLORS.get(c, "#9CA3AF")

# ── metrics ───────────────────────────────────────────────────────────────────
n_pairs   = len(df)
n_drugs   = df["Drug"].nunique()
n_pb_drug = df[df.Source == "Purple Book"]["Drug"].nunique()
n_ob_drug = df[df.Source == "Orange Book"]["Drug"].nunique()
n_cats    = df["Disease Category"].nunique()
n_dis     = df["Disease / Indication"].replace("", pd.NA).dropna().nunique()
def first_gene(t):
    g = str(t).split(",")[0].strip()
    return g
n_targets = df["Drug Target (Gene)"].apply(first_gene).replace("", pd.NA).dropna().nunique()
top_rev   = df.groupby("Drug")["rev"].max()
top_rev_drug = top_rev.idxmax(); top_rev_val = top_rev.max()


# ── FIG 1 — Sankey: Source → Modality → Disease Category (top) ────────────────
def build_sankey():
    du = df.drop_duplicates(subset=["Drug"])          # one modality/source per drug
    dcat = df.drop_duplicates(subset=["Drug", "Disease Category"])

    sources = ["Purple Book", "Orange Book"]
    # PB biologic subtypes first, then OB GSRS classes — dynamic on what's present
    _mod_order = ["Monoclonal Antibody", "Fusion Protein", "Enzyme / Protein Replacement",
                  "Peptide / Hormone", "Polyclonal Immunoglobulin", "Allergen / Vaccine",
                  "Biologic", "chemical", "protein", "nucleicAcid", "polymer", "mixture",
                  "structurallyDiverse", "concept", "specifiedSubstanceG1", "unknown"]
    present = set(du["Modality"])
    mods = [m for m in _mod_order if m in present]
    mods += [m for m in sorted(present) if m not in mods]   # any extras
    cat_counts = dcat["Disease Category"].value_counts()
    top_cats = cat_counts.head(14).index.tolist()

    labels, colors, idx = [], [], {}
    def node(key, label, color):
        idx[key] = len(labels); labels.append(label); colors.append(color)
    for s in sources:
        node(("src", s), f"{s}\n({du[du.Source==s].shape[0]})", SRC_COLORS[s])
    for m in mods:
        node(("mod", m), f"{m}\n({(du.Modality==m).sum()})", MOD_COLORS.get(m, "#9CA3AF"))
    for c in top_cats:
        node(("cat", c), f"{c}\n({int(cat_counts[c])})", cat_color(c))

    S, T, V, LC = [], [], [], []
    def link(a, b, v, c):
        if v > 0: S.append(idx[a]); T.append(idx[b]); V.append(int(v)); LC.append(c)
    # source → modality
    for s in sources:
        for m in mods:
            v = du[(du.Source == s) & (du.Modality == m)].shape[0]
            link(("src", s), ("mod", m), v, MOD_COLORS.get(m, "#CBD5E1"))
    # modality → category
    for m in mods:
        sub = dcat[dcat.Modality == m]
        vc = sub["Disease Category"].value_counts()
        for c in top_cats:
            link(("mod", m), ("cat", c), int(vc.get(c, 0)), cat_color(c))

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(pad=14, thickness=18, line=dict(color="white", width=0.5),
                  label=labels, color=colors, hovertemplate="%{label}<extra></extra>"),
        link=dict(source=S, target=T, value=V, color=LC,
                  hovertemplate="%{source.label} → %{target.label}: %{value}<extra></extra>")))
    fig.update_layout(
        title=dict(text=f"<b>Combined Pipeline: {n_drugs} FDA Drugs → Modality → Disease Category</b><br>"
                        "<sup>Purple Book biologics + Orange Book peptides</sup>", font=dict(size=14)),
        font=dict(size=9), margin=dict(l=10, r=10, t=55, b=10), height=560, paper_bgcolor="#F8FAFC")
    return fig


# ── FIG 2 — Source donut + Modality donut ────────────────────────────────────
def build_source_donut():
    du = df.drop_duplicates(subset=["Drug"])
    sc = du["Source"].value_counts()
    fig = go.Figure(go.Pie(
        labels=sc.index.tolist(), values=sc.values.tolist(), hole=0.55,
        marker=dict(colors=[SRC_COLORS[s] for s in sc.index], line=dict(color="white", width=2)),
        textinfo="label+percent+value", textfont=dict(size=11)))
    fig.add_annotation(text=f"<b>{n_drugs}</b><br>drugs", x=0.5, y=0.5, showarrow=False,
                       font=dict(size=13, color="#1E3A5F"))
    fig.update_layout(title=dict(text="<b>Drugs by Source</b>", font=dict(size=14)),
                      showlegend=True, legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"),
                      margin=dict(l=10, r=10, t=50, b=30), height=380, paper_bgcolor="#F8FAFC")
    return fig

def build_modality_pie(source):
    """Separate modality pie for one book (Purple = biologic formats,
    Orange = GSRS substance classes)."""
    du = df[df.Source == source].drop_duplicates(subset=["Drug"])
    mc = du["Modality"].value_counts()
    n = int(mc.sum())
    sub = ("biologic formats" if source == "Purple Book"
           else "FDA GSRS substance class")
    pull_set = ({"Fusion Protein", "Enzyme / Protein Replacement",
                 "Peptide / Hormone", "Polyclonal Immunoglobulin", "Allergen / Vaccine"}
                if source == "Purple Book" else {"protein", "nucleicAcid"})
    fig = go.Figure(go.Pie(
        labels=mc.index.tolist(), values=mc.values.tolist(), hole=0.5,
        marker=dict(colors=[MOD_COLORS.get(m, "#9CA3AF") for m in mc.index],
                    line=dict(color="white", width=2)),
        textinfo="label+percent", textfont=dict(size=10), sort=True,
        pull=[0.06 if m in pull_set else 0 for m in mc.index],
        hovertemplate="<b>%{label}</b><br>%{value} drugs (%{percent})<extra></extra>"))
    fig.add_annotation(text=f"<b>{n}</b><br>drugs", x=0.5, y=0.5, showarrow=False,
                       font=dict(size=12, color="#1E3A5F"))
    fig.update_layout(
        title=dict(text=f"<b>{source} — Drug Modality</b><br><sup>{sub}</sup>", font=dict(size=13)),
        showlegend=True, legend=dict(font=dict(size=9), orientation="h", y=-0.08, x=0.5, xanchor="center"),
        margin=dict(l=10, r=10, t=55, b=40), height=420, paper_bgcolor="#F8FAFC")
    return fig


# ── FIG 3 — Disease category bar, stacked by Source ──────────────────────────
def build_category_bar():
    dcat = df.drop_duplicates(subset=["Drug", "Disease Category"])
    piv = dcat.groupby(["Disease Category", "Source"]).size().unstack(fill_value=0)
    piv["total"] = piv.sum(axis=1)
    piv = piv.sort_values("total")
    fig = go.Figure()
    for src in ["Purple Book", "Orange Book"]:
        if src in piv.columns:
            fig.add_trace(go.Bar(y=piv.index, x=piv[src], orientation="h", name=src,
                                 marker_color=SRC_COLORS[src],
                                 hovertemplate="<b>%{y}</b><br>"+src+": %{x}<extra></extra>"))
    fig.update_layout(barmode="stack",
        title=dict(text="<b>Disease Category — Unique Drugs (stacked by source)</b>", font=dict(size=14)),
        xaxis=dict(title="Unique Drugs", showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(tickfont=dict(size=9)), legend=dict(orientation="h", y=1.02, x=1, xanchor="right"),
        margin=dict(l=10, r=40, t=60, b=40), height=640, paper_bgcolor="#F8FAFC", plot_bgcolor="#F8FAFC")
    return fig


# ── FIG 4 — Target gene bar, separate per source (each book's own top 30) ────
def build_target_bar(source):
    d = df[df.Source == source].drop_duplicates(subset=["Drug", "Drug Target (Gene)"])
    genes = []
    for _, row in d.iterrows():
        for g in str(row["Drug Target (Gene)"]).split(","):
            g = g.strip()
            if g and len(g) < 22 and g.lower() not in ("nan", "supplement", "unknown", ""):
                genes.append(g)
    gc = pd.Series(genes).value_counts().head(30).sort_values(ascending=True)  # most at top
    sub = "biologics" if source == "Purple Book" else "small molecules"
    fig = go.Figure(go.Bar(
        x=gc.values, y=gc.index.tolist(), orientation="h",
        marker=dict(color=SRC_COLORS[source], line=dict(color="white", width=0.5)),
        text=gc.values, textposition="outside",
        hovertemplate="<b>%{y}</b><br>" + source + ": %{x} drugs<extra></extra>"))
    fig.update_layout(
        title=dict(text=f"<b>Top {len(gc)} Target Genes — {source}</b><br>"
                        f"<sup>{sub} · most-targeted at top</sup>", font=dict(size=13)),
        xaxis=dict(title="Number of Drugs", showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(tickfont=dict(size=9)),
        margin=dict(l=10, r=45, t=55, b=40), height=700,
        paper_bgcolor="#F8FAFC", plot_bgcolor="#F8FAFC")
    return fig


# ── FIG 6 — Scatter: #indications vs #categories per drug ────────────────────
def build_scatter():
    g = df[df["Disease / Indication"] != ""].groupby("Drug").agg(
        n_ind=("Disease / Indication", "nunique"),
        n_cat=("Disease Category", "nunique"),
        src=("Source", "first"), rev=("rev", "max"),
        tgt=("Drug Target (Gene)", "first")).reset_index()
    fig = px.scatter(g, x="n_cat", y="n_ind", color="src", size=g["rev"] + 0.5,
                     color_discrete_map=SRC_COLORS, hover_name="Drug",
                     hover_data={"tgt": True, "rev": ":.2f", "src": False},
                     labels={"n_cat": "# Disease Categories", "n_ind": "# Indications", "src": "Source"})
    fig.update_layout(title=dict(text="<b>Drug Breadth: Indications × Disease Categories</b><br>"
                                 "<sup>size ∝ 2024 revenue</sup>", font=dict(size=14)),
                      xaxis=dict(dtick=1, showgrid=True, gridcolor="#E2E8F0"),
                      yaxis=dict(showgrid=True, gridcolor="#E2E8F0"),
                      margin=dict(l=40, r=20, t=60, b=45), height=440,
                      paper_bgcolor="#F8FAFC", plot_bgcolor="#F8FAFC")
    return fig


# ── FIG 7 — Heatmap: top genes × top categories ──────────────────────────────
def build_heatmap():
    d = df.drop_duplicates(subset=["Drug", "Drug Target (Gene)", "Disease Category"]).copy()
    d["g1"] = d["Drug Target (Gene)"].apply(lambda t: str(t).split(",")[0].strip())
    d = d[(d.g1 != "") & (~d.g1.str.lower().isin(["nan", "supplement", "unknown"]))]
    top_g = d["g1"].value_counts().head(25).index.tolist()
    top_c = d["Disease Category"].value_counts().head(18).index.tolist()
    d = d[d.g1.isin(top_g) & d["Disease Category"].isin(top_c)]
    piv = d.groupby(["g1", "Disease Category"]).size().unstack(fill_value=0)
    piv = piv.reindex(index=[g for g in top_g if g in piv.index])
    fig = go.Figure(go.Heatmap(z=piv.values, x=piv.columns.tolist(), y=piv.index.tolist(),
        colorscale="Purples", showscale=True, xgap=2, ygap=2,
        hovertemplate="Gene <b>%{y}</b> × <b>%{x}</b>: %{z}<extra></extra>"))
    fig.update_layout(title=dict(text="<b>Target Gene × Disease Category</b>", font=dict(size=14)),
                      xaxis=dict(tickangle=-40, tickfont=dict(size=8)), yaxis=dict(tickfont=dict(size=9)),
                      margin=dict(l=10, r=20, t=55, b=150), height=560, paper_bgcolor="#F8FAFC", plot_bgcolor="#F8FAFC")
    return fig


# ── FIG 8 — Revenue bar (top 25 drugs, colored by source) ────────────────────
def build_revenue_bar():
    g = (df[df.rev > 0].groupby("Drug").agg(rev=("rev", "max"), src=("Source", "first"),
         brand=("Brand", "first"), tgt=("Drug Target (Gene)", "first"),
         cat=("Disease Category", "first")).reset_index()
         .sort_values("rev", ascending=False).head(25).sort_values("rev"))
    fig = go.Figure(go.Bar(x=g["rev"], y=g["Drug"], orientation="h",
        marker=dict(color=[SRC_COLORS[s] for s in g["src"]], line=dict(color="white", width=0.5)),
        text=[f"${v:.1f}B" for v in g["rev"]], textposition="outside",
        customdata=list(zip(g["src"], g["brand"], g["tgt"], g["cat"])),
        hovertemplate="<b>%{y}</b><br>%{customdata[0]} — %{customdata[1]}<br>Target: %{customdata[2]}<br>%{customdata[3]}<br>Revenue: $%{x:.2f}B<extra></extra>"))
    fig.update_layout(title=dict(text="<b>Top 25 Drugs by 2024 Global Revenue</b><br>"
                                 "<sup>Purple = biologic · Orange = peptide/protein</sup>", font=dict(size=14)),
                      xaxis=dict(title="Annual Revenue (USD B)", showgrid=True, gridcolor="#E2E8F0", tickprefix="$", ticksuffix="B"),
                      yaxis=dict(tickfont=dict(size=9)), margin=dict(l=10, r=70, t=60, b=40),
                      height=680, paper_bgcolor="#F8FAFC", plot_bgcolor="#F8FAFC")
    return fig


# ── FIG 9 — Disease coverage: diseases by # drugs ────────────────────────────
def build_disease_coverage():
    d = df[df["Disease / Indication"] != ""].drop_duplicates(subset=["Drug", "Disease / Indication"])
    dc = d.groupby("Disease / Indication").agg(n=("Drug", "nunique"),
         cat=("Disease Category", lambda s: s.value_counts().index[0])).reset_index()
    dc = dc.sort_values("n", ascending=False).head(30).sort_values("n")
    fig = go.Figure(go.Bar(x=dc["n"], y=dc["Disease / Indication"], orientation="h",
        marker=dict(color=[cat_color(c) for c in dc["cat"]], line=dict(color="white", width=0.5)),
        text=dc["n"], textposition="outside",
        customdata=dc["cat"], hovertemplate="<b>%{y}</b><br>%{customdata}<br>%{x} drugs<extra></extra>"))
    fig.update_layout(title=dict(text="<b>Disease Coverage: Top 30 Indications by Number of Drugs</b><br>"
                                 "<sup>colored by disease category · both books</sup>", font=dict(size=14)),
                      xaxis=dict(title="Number of Drugs", showgrid=True, gridcolor="#E2E8F0"),
                      yaxis=dict(tickfont=dict(size=9)), margin=dict(l=10, r=60, t=60, b=40),
                      height=760, paper_bgcolor="#F8FAFC", plot_bgcolor="#F8FAFC")
    return fig


# ── FIG 10/11 — Drug size by target gene (MW + amino acid length), all drugs ──
# Covers every drug in the dataset with a defined single molecular species
# (all except pancrelipase, an undefined porcine enzyme mixture with no single
# MW/length). Amino acid length is residues in the mature active chain(s),
# summed across chains for multimeric/dimeric proteins; molecular weight is
# the drug substance as administered (incl. glycosylation/PEG where present).
# Values are FDA-label-sourced (openFDA "Description" section) except where
# marked approximate in the source data (recently approved or compositionally
# variable drugs lacking a public authoritative figure).
def _drug_size_rows():
    seen, rows = set(), []
    for m in merged:
        d = m["Drug"]
        if d in seen:
            continue
        seen.add(d)
        aa, mw = m["Amino Acid Length"], m["Molecular Weight (Da)"]
        if not aa or not mw:
            continue
        rows.append((d, m["Drug Target (Gene)"] or "—", int(aa), int(mw)))
    return rows

DRUG_SIZE_ROWS = _drug_size_rows()

def build_size_bar(metric):
    idx = 2 if metric == "aa" else 3
    items = sorted(DRUG_SIZE_ROWS, key=lambda r: r[idx])
    labels = [f"{d} ({g})" for d, g, _, _ in items]
    vals = [r[idx] for r in items]
    if metric == "mw":
        title, xtitle, texts = "Molecular Weight", "Molecular Weight (Da, log scale)", [f"{v:,.0f} Da" for v in vals]
    else:
        title, xtitle, texts = "Amino Acid Length", "Amino Acids (log scale)", [f"{v:,.0f} aa" for v in vals]
    fig = go.Figure(go.Bar(
        x=vals, y=labels, orientation="h",
        marker=dict(color="#0891B2", line=dict(color="white", width=0.5)),
        text=texts, textposition="outside",
        hovertemplate="<b>%{y}</b><br>" + title + ": %{text}<extra></extra>"))
    fig.update_layout(
        title=dict(text=f"<b>Drug {title} by Target Gene</b><br>"
                        f"<sup>{len(items)} drugs with a defined molecular species · log scale spans peptides to fusion proteins</sup>", font=dict(size=13)),
        xaxis=dict(title=xtitle, type="log", showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(tickfont=dict(size=9)),
        margin=dict(l=10, r=90, t=55, b=40), height=max(480, 17 * len(items) + 120),
        paper_bgcolor="#F8FAFC", plot_bgcolor="#F8FAFC")
    return fig


# ── FIG 12 — Native (endogenous) target protein length, all 35 targets + GLP-1 ─
# Canonical human UniProt sequence length (full precursor unless noted) for each
# of the 35 drug targets in this dataset, plus native GLP-1(7-37) itself (the
# hormone semaglutide/liraglutide/etc. mimic) for comparison against its own
# receptor GLP1R. UOX (uricase) is excluded: it is a non-functional pseudogene
# in humans (three inactivating mutations during primate evolution), so there
# is no native human protein to report.
TARGET_LENGTH = {
    "GLP1 (native hormone)": 31,
    "SNAP25":  206,
    "VEGFA":   191,
    "TNF":     233,
    "CACNA1B": 2339,
    "GHRHR":   423,
    "GNRHR":   328,
    "SSTR5":   364,
    "CALCR":   474,
    "GLA":     429,
    "PNLIP":   449,
    "SERPINA1":418,
    "F7":      406,
    "F9":      415,
    "GLP1R":   463,
    "GIPR":    466,
    "INHBA":   426,
    "FCGRT":   290,
    "EPOR":    508,
    "ARG1":    322,
    "GLP2R":   553,
    "IDS":     550,
    "PTH1R":   593,
    "GHR":     620,
    "SMPD1":   631,
    "PCSK9":   692,
    "CSF3R":   836,
    "GAA":     952,
    "MAN2B1":  1011,
    "NPR2":    1047,
    "GUCY2C":  1073,
    "INSR":    1382,
    "SI":      1827,
    "F8":      2351,
}

def build_target_length_bar():
    items = sorted(TARGET_LENGTH.items(), key=lambda kv: kv[1])
    labels = [g for g, _ in items]
    vals = [v for _, v in items]
    fig = go.Figure(go.Bar(
        x=vals, y=labels, orientation="h",
        marker=dict(color=["#F97316" if l.startswith("GLP1 ") else "#7C3AED" for l in labels],
                    line=dict(color="white", width=0.5)),
        text=[f"{v:,} aa" for v in vals], textposition="outside",
        hovertemplate="<b>%{y}</b><br>Native length: %{text}<extra></extra>"))
    fig.update_layout(
        title=dict(text="<b>Native (Endogenous) Target Protein Length</b><br>"
                        f"<sup>{len(items)} targets — all 35 drug targets in this dataset plus native GLP-1 · "
                        "UOX omitted (human pseudogene, no functional protein)</sup>", font=dict(size=13)),
        xaxis=dict(title="Amino Acids (native UniProt length)", showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(tickfont=dict(size=9)),
        margin=dict(l=10, r=80, t=55, b=40), height=900,
        paper_bgcolor="#F8FAFC", plot_bgcolor="#F8FAFC")
    return fig


# ── FIG 13 — Rare / orphan disease therapies by 2024 revenue ──────────────────
# Restricted to indications with unambiguous rare-disease status (Orphanet /
# FDA orphan-designation consensus) — mostly enzyme replacement therapies and
# hemophilia factor replacement. Excludes borderline cases (exocrine pancreatic
# insufficiency, growth hormone deficiency) where the indication is common
# enough, or broad enough, that "rare disease" doesn't unambiguously apply.
RARE_DISEASE_INDICATIONS = {
    "Fabry disease": "Enzyme Replacement",
    "Late-onset Pompe disease (LOPD)": "Enzyme Replacement",
    "Late-onset Pompe disease (+miglustat)": "Enzyme Replacement",
    "Alpha-mannosidosis": "Enzyme Replacement",
    "Acid sphingomyelinase deficiency (ASMD / NPD-A/B)": "Enzyme Replacement",
    "MPS II (Hunter syndrome)": "Enzyme Replacement",
    "Arginase 1 deficiency (hyperargininemia)": "Enzyme Replacement",
    "Congenital sucrase-isomaltase deficiency (CSID)": "Enzyme Replacement",
    "Alpha-1 antitrypsin deficiency (AATD) with emphysema": "Enzyme Replacement",
    "Achondroplasia": "Skeletal / Growth",
    "Short bowel syndrome": "Gastrointestinal",
    "Severe chronic neutropenia (SCN)": "Hematology",
    "Hemophilia A (prophylaxis)": "Hemophilia",
    "Hemophilia A (prophylaxis, extended half-life)": "Hemophilia",
    "Hemophilia B (prophylaxis)": "Hemophilia",
    "Hemophilia A/B with inhibitors (prophylaxis)": "Hemophilia",
    "Hemophilia A/B with inhibitors": "Hemophilia",
}
RARE_GROUP_COLORS = {
    "Enzyme Replacement": "#7C3AED", "Hemophilia": "#DC2626",
    "Skeletal / Growth": "#0891B2", "Gastrointestinal": "#059669", "Hematology": "#D97706",
}

def build_rare_disease_bar(group):
    d = df[df["Disease / Indication"].isin(RARE_DISEASE_INDICATIONS)].copy()
    d = d.drop_duplicates(subset=["Drug", "Disease / Indication"])
    d["group"] = d["Disease / Indication"].map(RARE_DISEASE_INDICATIONS)
    d = d[d["group"] == group]
    d["label"] = d["Brand"].where(d["Brand"] != "", d["Drug"]) + " (" + d["Disease / Indication"] + ")"
    d = d.sort_values("rev")
    fig = go.Figure(go.Bar(
        x=d["rev"], y=d["label"], orientation="h",
        marker=dict(color=RARE_GROUP_COLORS[group], line=dict(color="white", width=0.5)),
        text=[f"${v:.2f}B" if v > 0 else "n/a" for v in d["rev"]], textposition="outside",
        hovertemplate="<b>%{y}</b><br>Revenue: %{text}<extra></extra>"))
    fig.update_layout(
        title=dict(text=f"<b>{group}</b><br><sup>{len(d)} indications</sup>", font=dict(size=13)),
        xaxis=dict(title="Annual Revenue (USD B)", showgrid=True, gridcolor="#E2E8F0", tickprefix="$", ticksuffix="B"),
        yaxis=dict(tickfont=dict(size=9)),
        margin=dict(l=10, r=70, t=50, b=40), height=max(220, 70 + 55 * len(d)),
        paper_bgcolor="#F8FAFC", plot_bgcolor="#F8FAFC")
    return fig


def to_div(fig, div_id):
    fig.update_layout(autosize=True)
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id=div_id,
                       config={"responsive": True, "displaylogo": False,
                               "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"]})

print("Building figures …")
f_sankey = build_sankey()
f_srcd   = build_source_donut()
f_modpb  = build_modality_pie("Purple Book")
f_modob  = build_modality_pie("Orange Book")
f_catbar = build_category_bar()
f_tgt_pb = build_target_bar("Purple Book")
f_tgt_ob = build_target_bar("Orange Book")
f_scat   = build_scatter()
f_heat   = build_heatmap()
f_rev    = build_revenue_bar()
f_cov    = build_disease_coverage()
f_sizemw = build_size_bar("mw")
f_sizeaa = build_size_bar("aa")
f_tgtlen = build_target_length_bar()
f_rare = {g: build_rare_disease_bar(g) for g in RARE_GROUP_COLORS}


# ── Sortable / filterable table (PB format: filter row under headers) ─────────
def build_table_html():
    rows_all = []
    for m in merged:
        rows_all.append({
            "source": m["Source"], "drug": m["Drug"], "brand": m["Brand"],
            "disease": m["Disease / Indication"], "category": m["Disease Category"],
            "modality": m["Modality"], "target": m["Drug Target (Gene)"],
            "revenue": m["Annual Revenue 2024 (USD B)"], "dose": m["Dose"],
            "freq": m["Frequency"], "duration": m["Duration of Use"],
            "aalen": m["Amino Acid Length"], "mw": m["Molecular Weight (Da)"],
            "aav": m["AAV Suitability"], "aavc": m["AAV Rationale"],
        })
    rows_all.sort(key=lambda r: (-(float(r["revenue"]) if r["revenue"] else 0), r["drug"].lower()))
    tbl_json = json.dumps(rows_all, ensure_ascii=False)
    n = len(rows_all)
    cat_colors_json = json.dumps(CAT_COLORS)
    mod_colors_json = json.dumps(MOD_COLORS)
    src_colors_json = json.dumps(SRC_COLORS)

    return f"""
<style>
.col-filter{{width:100%;padding:3px 5px;font-size:0.66rem;border:1px solid rgba(255,255,255,0.3);
  border-radius:4px;background:rgba(255,255,255,0.12);color:#fff;outline:none;box-sizing:border-box;}}
.col-filter::placeholder{{color:rgba(255,255,255,0.5);}}
.col-filter option{{background:#1E3A5F;color:#fff;}}
.col-filter:focus{{background:rgba(255,255,255,0.22);border-color:rgba(255,255,255,0.65);}}
</style>
<div style="padding:10px var(--pad,16px) 0;">
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
        <col style="width:6%"/><col style="width:9%"/><col style="width:6%"/><col style="width:11%"/>
        <col style="width:9%"/><col style="width:6%"/><col style="width:6%"/><col style="width:5%"/>
        <col style="width:7%"/><col style="width:5%"/><col style="width:8%"/><col style="width:5%"/>
        <col style="width:6%"/><col style="width:6%"/>
      </colgroup>
      <thead>
        <tr style="background:#1E3A5F;color:#fff;text-align:left;">
          <th class="th-sort" data-col="source"   style="padding:6px 8px;cursor:pointer;">Source &#8597;</th>
          <th class="th-sort" data-col="drug"     style="padding:6px 8px;cursor:pointer;">Drug &#8597;</th>
          <th class="th-sort" data-col="brand"    style="padding:6px 8px;cursor:pointer;">Brand &#8597;</th>
          <th class="th-sort" data-col="disease"  style="padding:6px 8px;cursor:pointer;">Disease / Indication &#8597;</th>
          <th class="th-sort" data-col="category" style="padding:6px 8px;cursor:pointer;">Category &#8597;</th>
          <th class="th-sort" data-col="modality" style="padding:6px 8px;cursor:pointer;">Modality &#8597;</th>
          <th class="th-sort" data-col="target"   style="padding:6px 8px;cursor:pointer;">Target &#8597;</th>
          <th class="th-sort" data-col="revenue"  style="padding:6px 8px;cursor:pointer;">Rev ($B) &#8597;</th>
          <th class="th-sort" data-col="dose"     style="padding:6px 8px;cursor:pointer;">Dose &#8597;</th>
          <th class="th-sort" data-col="freq"     style="padding:6px 8px;cursor:pointer;">Frequency &#8597;</th>
          <th class="th-sort" data-col="duration" style="padding:6px 8px;cursor:pointer;">Duration &#8597;</th>
          <th class="th-sort" data-col="aalen"    style="padding:6px 8px;cursor:pointer;">AA Length &#8597;</th>
          <th class="th-sort" data-col="mw"       style="padding:6px 8px;cursor:pointer;">MW (Da) &#8597;</th>
          <th class="th-sort" data-col="aav"      style="padding:6px 8px;cursor:pointer;" title="AAV gene-therapy suitability">AAV Fit &#8597;</th>
        </tr>
        <tr style="background:#2D5A87;">
          <th style="padding:3px 5px;"><select class="col-filter" data-col="source" id="colSrcFilter"><option value="">All sources</option></select></th>
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
          <th style="padding:3px 5px;"><input  class="col-filter" data-col="aalen"    placeholder="≥ aa" type="number" min="0" step="1"/></th>
          <th style="padding:3px 5px;"><input  class="col-filter" data-col="mw"       placeholder="≥ Da" type="number" min="0" step="1"/></th>
          <th style="padding:3px 5px;"><select class="col-filter" data-col="aav" id="colAavFilter"><option value="">All AAV</option></select></th>
        </tr>
      </thead>
      <tbody id="tblBody"></tbody>
    </table>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px;">
    <label style="font-size:0.78rem;color:#64748B;">Rows per page:
      <select id="tblPageSize" style="font-size:0.8rem;padding:4px 8px;border:1px solid #E2E8F0;border-radius:6px;margin-left:4px;">
        <option value="25">25</option><option value="50" selected>50</option><option value="100">100</option><option value="{n}">All ({n})</option>
      </select></label>
    <div id="tblPager" style="display:flex;gap:4px;flex-wrap:wrap;margin-left:auto;"></div>
  </div>
</div>
<script>
(function(){{
const TBL=JSON.parse({json.dumps(tbl_json)});
const CATC={cat_colors_json}, MODC={mod_colors_json}, SRCC={src_colors_json};
[...new Set(TBL.map(r=>r.source))].sort().forEach(s=>document.getElementById('colSrcFilter').innerHTML+=`<option value="${{s}}">${{s}}</option>`);
[...new Set(TBL.map(r=>r.category))].filter(Boolean).sort().forEach(c=>document.getElementById('colCatFilter').innerHTML+=`<option value="${{c}}">${{c}}</option>`);
[...new Set(TBL.map(r=>r.modality))].filter(Boolean).sort().forEach(m=>document.getElementById('colModFilter').innerHTML+=`<option value="${{m}}">${{m}}</option>`);
const AAVC={{High:'#059669',Medium:'#D97706',Low:'#94A3B8'}};
const AAV_RANK={{High:0,Medium:1,Low:2}};
const esc=s=>String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
['High','Medium','Low'].filter(v=>TBL.some(r=>r.aav===v)).forEach(v=>document.getElementById('colAavFilter').innerHTML+=`<option value="${{v}}">${{v}}</option>`);
let sort={{col:'revenue',asc:false}}, page=0, ps=50;
function filt(){{
  const q=document.getElementById('tblSearch').value.toLowerCase(); const cf={{}};
  document.querySelectorAll('.col-filter').forEach(el=>cf[el.dataset.col]=el.value);
  return TBL.filter(r=>{{
    if(q&&!Object.values(r).join(' ').toLowerCase().includes(q))return false;
    if(cf.source&&r.source!==cf.source)return false;
    if(cf.drug&&!r.drug.toLowerCase().includes(cf.drug.toLowerCase()))return false;
    if(cf.brand&&!r.brand.toLowerCase().includes(cf.brand.toLowerCase()))return false;
    if(cf.disease&&!r.disease.toLowerCase().includes(cf.disease.toLowerCase()))return false;
    if(cf.category&&r.category!==cf.category)return false;
    if(cf.modality&&r.modality!==cf.modality)return false;
    if(cf.target&&!r.target.toLowerCase().includes(cf.target.toLowerCase()))return false;
    if(cf.revenue&&(parseFloat(r.revenue)||0)<parseFloat(cf.revenue))return false;
    if(cf.dose&&!r.dose.toLowerCase().includes(cf.dose.toLowerCase()))return false;
    if(cf.freq&&!r.freq.toLowerCase().includes(cf.freq.toLowerCase()))return false;
    if(cf.duration&&!r.duration.toLowerCase().includes(cf.duration.toLowerCase()))return false;
    if(cf.aalen&&(parseFloat(r.aalen)||0)<parseFloat(cf.aalen))return false;
    if(cf.mw&&(parseFloat(r.mw)||0)<parseFloat(cf.mw))return false;
    if(cf.aav&&r.aav!==cf.aav)return false;
    return true;
  }});
}}
const NUMERIC_COLS=new Set(['revenue','aalen','mw']);
function render(){{
  let d=filt();
  if(sort.col){{const c=sort.col,a=sort.asc,isNum=NUMERIC_COLS.has(c),isAav=c==='aav';d=[...d].sort((x,y)=>{{
    const vx=isAav?(AAV_RANK[x[c]]??9):isNum?parseFloat(x[c])||0:x[c].toLowerCase(),
          vy=isAav?(AAV_RANK[y[c]]??9):isNum?parseFloat(y[c])||0:y[c].toLowerCase();
    return a?(vx>vy?1:vx<vy?-1:0):(vx<vy?1:vx>vy?-1:0);}});}}
  const tot=d.length,start=page*ps,slice=ps>={n}?d:d.slice(start,start+ps);
  const b=document.getElementById('tblBody');b.innerHTML='';
  slice.forEach((r,i)=>{{
    const tr=document.createElement('tr');
    tr.style.background=i%2===0?(CATC[r.category]?CATC[r.category]+'22':'#fff'):'#F8FAFC';
    tr.style.borderBottom='1px solid #E2E8F0';
    const sc=SRCC[r.source]||'#64748B',mc=MODC[r.modality]||'#94A3B8';
    const rev=r.revenue?'$'+r.revenue+'B':'—';
    const cells=[
      ['source',`<span style="color:${{sc}};font-weight:700;">${{r.source==='Purple Book'?'PB':'OB'}}</span>`],
      ['drug',`<b style="color:#1E3A5F;">${{r.drug}}</b>`],['brand',r.brand||'—'],['disease',r.disease||'—'],
      ['category',r.category],['modality',`<span style="color:${{mc}};font-weight:600;">${{r.modality}}</span>`],
      ['target',`<span style="font-family:monospace;font-size:0.7rem;color:#7C3AED;">${{r.target||'—'}}</span>`],
      ['revenue',r.revenue?`<b style="color:#059669;">${{rev}}</b>`:'—'],
      ['dose',r.dose||'—'],['freq',r.freq||'—'],['duration',r.duration||'—'],
      ['aalen',r.aalen?r.aalen+' aa':'—'],
      ['mw',r.mw?Number(r.mw).toLocaleString()+' Da':'—'],
      ['aav',r.aav?`<span title="${{esc(r.aavc)}}" style="background:${{AAVC[r.aav]}}22;color:${{AAVC[r.aav]}};font-weight:700;padding:2px 7px;border-radius:10px;font-size:0.66rem;white-space:nowrap;cursor:help;">${{r.aav}}</span>`:'—']];
    cells.forEach(([,html])=>{{const td=document.createElement('td');td.innerHTML=html;
      td.style.cssText='padding:5px 8px;vertical-align:top;line-height:1.35;word-break:break-word;overflow-wrap:anywhere;';tr.appendChild(td);}});
    b.appendChild(tr);
  }});
  document.getElementById('tblCount').textContent=tot+' / '+TBL.length+' rows';
  const np=ps>={n}?0:Math.ceil(tot/ps),pg=document.getElementById('tblPager');
  if(np<=1){{pg.innerHTML='';return;}}
  const bs=a=>`style="padding:4px 10px;border:1px solid #E2E8F0;border-radius:6px;font-size:0.78rem;cursor:pointer;background:${{a?'#1E3A5F':'#fff'}};color:${{a?'#fff':'#374151'}};"`;
  const lo=Math.max(0,Math.min(page-2,np-5)),hi=Math.min(np,lo+5);
  let h=`<button ${{bs(false)}} onclick="tblGo(${{page-1}})" ${{page===0?'disabled':''}}>«</button>`;
  for(let i=lo;i<hi;i++)h+=`<button ${{bs(i===page)}} onclick="tblGo(${{i}})">${{i+1}}</button>`;
  h+=`<button ${{bs(false)}} onclick="tblGo(${{page+1}})" ${{page>=np-1?'disabled':''}}>»</button>`;pg.innerHTML=h;
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


# ── Step 9 — AAV suitability: counts + Highly Recommended table ───────────────
def _aav_counts():
    seen, c = set(), Counter()
    for m in merged:
        d = m["Drug"]
        if d in seen:
            continue
        seen.add(d)
        c[m["AAV Suitability"] or "—"] += 1
    return c

AAV_COUNTS = _aav_counts()
N_AAV_DRUGS = sum(AAV_COUNTS.values())

def build_aav_high_table():
    # One row per unique High-scored drug, with brand/target/modality/size/rationale.
    seen, rows = set(), []
    for m in merged:
        d = m["Drug"]
        if d in seen or m["AAV Suitability"] != "High":
            continue
        seen.add(d)
        _score, gene_kb, rationale = AAV_SUITABILITY.get(d, ("", None, ""))
        rows.append((d, m["Brand"], m["Drug Target (Gene)"], m["Modality"],
                     m["Amino Acid Length"], gene_kb, rationale))
    # Sort by gene size (smallest transgene first), then name.
    rows.sort(key=lambda r: (r[5] if r[5] is not None else 99, r[0].lower()))

    body = []
    for d, brand, target, modality, aa, gene_kb, rationale in rows:
        gk = f"{gene_kb:.1f} kb" if gene_kb is not None else "—"
        aa_disp = f"{aa} aa" if aa else "—"
        body.append(
            f'<tr style="border-bottom:1px solid #E2E8F0;">'
            f'<td style="padding:6px 8px;"><b style="color:#1E3A5F;">{d}</b></td>'
            f'<td style="padding:6px 8px;">{brand or "—"}</td>'
            f'<td style="padding:6px 8px;font-family:monospace;font-size:0.7rem;color:#7C3AED;">{target or "—"}</td>'
            f'<td style="padding:6px 8px;">{modality or "—"}</td>'
            f'<td style="padding:6px 8px;white-space:nowrap;">{aa_disp}</td>'
            f'<td style="padding:6px 8px;white-space:nowrap;color:#059669;font-weight:700;">{gk}</td>'
            f'<td style="padding:6px 8px;line-height:1.4;">{rationale}</td>'
            f'</tr>')
    return f"""
<div style="padding:6px var(--pad,16px) 0;font-size:0.86rem;color:#334155;line-height:1.5;max-width:1100px;">
  <p><b>Scoring.</b> Each drug is rated for delivery by an <b>AAV</b> vector that makes the
  protein in the patient's own cells. Two gates: <b>(1) gene size &lt; 4.5 kb</b> — the AAV
  genome fits ~4.5 kb of coding sequence (≈ expressed-chain amino acids × 3 bp; for
  Fc-fusions/homodimers the AAV encodes one monomer that dimerizes); and
  <b>(2) no un-encodable chemistry</b> — ribosomes cannot add PEG, fatty-acid/lipid chains,
  D- or other non-natural amino acids, or substitute metal cofactors. Half-life extensions
  (PEG, lipid, albumin-binding, Fc) are treated as <i>replaceable</i> by continuous
  expression; toxins and gut-lumen enzymes are mechanistically incompatible.
  <b>{AAV_COUNTS.get('High',0)} High</b>, {AAV_COUNTS.get('Medium',0)} Medium,
  {AAV_COUNTS.get('Low',0)} Low across {N_AAV_DRUGS} drugs. Hover the
  <b>AAV Fit</b> chip in the table above for any drug's rationale.</p>
</div>
<div style="padding:8px var(--pad,16px) 0;">
  <div style="overflow-x:auto;border-radius:10px;border:1px solid #E2E8F0;box-shadow:0 1px 4px rgba(0,0,0,.06);">
    <table style="width:100%;border-collapse:collapse;background:#fff;font-size:0.76rem;">
      <colgroup><col style="width:12%"/><col style="width:13%"/><col style="width:9%"/><col style="width:13%"/>
        <col style="width:7%"/><col style="width:7%"/><col style="width:39%"/></colgroup>
      <thead><tr style="background:#059669;color:#fff;text-align:left;">
        <th style="padding:7px 8px;">Drug</th><th style="padding:7px 8px;">Brand</th>
        <th style="padding:7px 8px;">Target (Gene)</th><th style="padding:7px 8px;">Modality</th>
        <th style="padding:7px 8px;">AA Length</th><th style="padding:7px 8px;">Gene ≈</th>
        <th style="padding:7px 8px;">Why it's a strong AAV candidate</th>
      </tr></thead>
      <tbody>{"".join(body)}</tbody>
    </table>
  </div>
</div>"""

AAV_HIGH_TABLE = build_aav_high_table()

RARE_GROUP_IDS = {g: f"rare{i}" for i, g in enumerate(RARE_GROUP_COLORS)}
RARE_CARDS_HTML = "".join(
    f'<div class="card">{to_div(f_rare[g], RARE_GROUP_IDS[g])}</div>' for g in RARE_GROUP_COLORS)

HTML = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0"/>
<title>FDA Peptide &amp; Protein Drugs — Chronic Use Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
:root{{--bg:#F0F4F8;--card:#fff;--text:#1E293B;--sub:#64748B;--border:#E2E8F0;--pad:clamp(10px,3vw,24px);--r:12px;}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--bg);color:var(--text);overflow-x:hidden;}}
header{{background:linear-gradient(135deg,#1E3A5F 0%,#7C3AED 50%,#D97706 100%);color:#fff;padding:clamp(14px,4vw,28px) var(--pad);}}
header h1{{font-size:clamp(1rem,3.5vw,1.5rem);font-weight:700;line-height:1.25;}}
header p{{margin-top:6px;opacity:.9;font-size:clamp(0.75rem,2.2vw,0.9rem);line-height:1.45;}}
.pipeline{{background:#1E3A5F;padding:12px var(--pad);display:grid;grid-template-columns:repeat(auto-fit,minmax(90px,1fr));gap:8px;}}
.pipe-step{{background:rgba(255,255,255,0.11);border:1px solid rgba(255,255,255,0.22);border-radius:8px;padding:8px 6px 7px;color:#fff;text-align:center;}}
.pipe-step strong{{display:block;font-size:clamp(1.1rem,3.5vw,1.5rem);font-weight:700;line-height:1.1;}}
.pipe-step span{{font-size:clamp(0.62rem,1.8vw,0.72rem);opacity:.82;line-height:1.2;display:block;margin-top:2px;}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;padding:14px var(--pad) 0;}}
.metric{{background:var(--card);border-radius:var(--r);padding:14px 16px;border-left:4px solid #7C3AED;box-shadow:0 1px 4px rgba(0,0,0,.07);}}
.metric.o{{border-color:#D97706;}}.metric.b{{border-color:#2563EB;}}.metric.g{{border-color:#059669;}}.metric.t{{border-color:#0891B2;}}
.mval{{font-size:clamp(1.5rem,5vw,2.1rem);font-weight:700;color:#7C3AED;line-height:1;}}
.metric.o .mval{{color:#D97706;}}.metric.b .mval{{color:#2563EB;}}.metric.g .mval{{color:#059669;}}.metric.t .mval{{color:#0891B2;}}
.mlabel{{font-size:clamp(0.65rem,1.8vw,0.75rem);color:var(--sub);margin-top:4px;line-height:1.3;}}
.sec{{font-size:clamp(0.6rem,1.8vw,0.68rem);font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#fff;padding:3px 10px;border-radius:4px;margin:18px var(--pad) 0;display:inline-block;}}
.s1{{background:#1E3A5F;}}.s2{{background:#7C3AED;}}.s3{{background:#D97706;}}.s4{{background:#0891B2;}}.s5{{background:#059669;}}.s6{{background:#DC2626;}}
.g1{{padding:8px var(--pad);}}
.g2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,440px),1fr));gap:10px;padding:8px var(--pad);}}
.card{{background:var(--card);border-radius:var(--r);padding:8px 6px;box-shadow:0 1px 4px rgba(0,0,0,.07);overflow:hidden;min-width:0;}}
footer{{text-align:center;font-size:clamp(0.65rem,1.8vw,0.75rem);color:var(--sub);padding:18px var(--pad) 24px;line-height:1.6;}}
</style></head><body>"""

HTML_BODY = f"""<header>
  <h1>FDA Peptide &amp; Protein Drugs — Chronic Use Dashboard</h1>
  <p>Peptide / protein-modality subset of the combined <b>Purple Book</b> (biologics) +
     <b>Orange Book</b> (small molecules) chronic-use dataset — {n_drugs} unique chronic /
     long-term peptide &amp; protein drugs across {n_pairs} drug–indication pairs, from
     <b>fda_all_drugs_chronic_indications_peptide.csv</b>.</p>
</header>
<div class="pipeline">
  <div class="pipe-step"><strong>{n_drugs}</strong><span>total drugs</span></div>
  <div class="pipe-step"><strong>{n_pb_drug}</strong><span>Purple Book biologics</span></div>
  <div class="pipe-step"><strong>{n_ob_drug}</strong><span>Orange Book peptides</span></div>
  <div class="pipe-step"><strong>{n_pairs}</strong><span>drug–indication pairs</span></div>
  <div class="pipe-step"><strong>{n_dis}</strong><span>unique diseases</span></div>
  <div class="pipe-step"><strong>{n_cats}</strong><span>disease categories</span></div>
  <div class="pipe-step"><strong>{n_targets}</strong><span>target genes</span></div>
</div>
<div class="metrics">
  <div class="metric"><div class="mval">{n_drugs}</div><div class="mlabel">Unique chronic drugs</div></div>
  <div class="metric b"><div class="mval">{n_pb_drug}</div><div class="mlabel">Purple Book biologics</div></div>
  <div class="metric o"><div class="mval">{n_ob_drug}</div><div class="mlabel">Orange Book peptides</div></div>
  <div class="metric t"><div class="mval">{n_cats}</div><div class="mlabel">Granular disease categories</div></div>
  <div class="metric g"><div class="mval">${top_rev_val:.0f}B</div><div class="mlabel">{top_rev_drug[:20]} — top 2024 revenue</div></div>
</div>

<div class="sec s1">Step 1 — Combined Pipeline: Source → Modality → Disease</div>
<div class="g1"><div class="card">{to_div(f_sankey,"sankey")}</div></div>

<div class="sec s2">Step 2 — Source Composition</div>
<div class="g1"><div class="card">{to_div(f_srcd,"srcd")}</div></div>

<div class="sec s2">Step 2b — Drug Modality by Source (Purple Book vs Orange Book)</div>
<div class="g2"><div class="card">{to_div(f_modpb,"modpb")}</div><div class="card">{to_div(f_modob,"modob")}</div></div>

<div class="sec s3">Step 3 — Disease Categories</div>
<div class="g1"><div class="card">{to_div(f_catbar,"catbar")}</div></div>

<div class="sec s3">Step 3b — Top 30 Target Genes, split by source</div>
<div class="g2"><div class="card">{to_div(f_tgt_pb,"tgtpb")}</div><div class="card">{to_div(f_tgt_ob,"tgtob")}</div></div>

<div class="sec s4">Step 4 — Drill-down: Gene × Category</div>
<div class="g1"><div class="card">{to_div(f_heat,"heat")}</div></div>

<div class="sec s5">Step 5 — Drug Breadth &amp; Top Revenue</div>
<div class="g2"><div class="card">{to_div(f_scat,"scat")}</div><div class="card">{to_div(f_rev,"rev")}</div></div>

<div class="sec s6">Step 6 — Disease Coverage: Ranked by Number of Drugs</div>
<div class="g1"><div class="card">{to_div(f_cov,"cov")}</div></div>

<div class="sec s6">Step 7 — Drug Size by Target Gene (All Drugs, Amino Acid Length &amp; MW)</div>
<div class="g2"><div class="card">{to_div(f_sizemw,"sizemw")}</div><div class="card">{to_div(f_sizeaa,"sizeaa")}</div></div>
<div class="g1"><div class="card">{to_div(f_tgtlen,"tgtlen")}</div></div>

<div class="sec s6">Step 8 — Rare / Orphan Disease Therapies, split by category</div>
<div class="g2">{RARE_CARDS_HTML}</div>

<div class="sec s5">Step 9 — AAV Gene-Therapy Suitability: Highly Recommended Candidates</div>
{AAV_HIGH_TABLE}

<div class="sec s1" style="margin-top:24px;">Source Data — fda_all_drugs_chronic_indications_peptide.csv ({n_pairs} pairs, sortable &amp; filterable)</div>
<div class="g1">{TABLE_HTML}</div>

<footer>
  Data sources: FDA Purple Book (biologics, 2020–2026) + FDA Orange Book (small molecules, May 2026)<br>
  Targets: ChEMBL v34 · Indications: openFDA drug labels · Categories: unified granular scheme<br>
  Source file: fda_all_drugs_chronic_indications_peptide.csv &nbsp;|&nbsp; {n_drugs} peptide/protein drugs · {n_pairs} drug–indication pairs
</footer>
<script>
const IDS=['sankey','srcd','modpb','modob','catbar','tgtpb','tgtob','heat','scat','rev','cov','sizemw','sizeaa','tgtlen',{",".join(repr(v) for v in RARE_GROUP_IDS.values())}];
function bp(){{const w=window.innerWidth;return w<480?0:w<900?1:2;}}
function resizeAll(){{IDS.forEach(id=>{{const el=document.getElementById(id);if(!el||!el.data)return;
  const w=el.parentElement?el.parentElement.clientWidth-16:undefined;
  try{{Plotly.relayout(el,{{autosize:true,width:w||undefined}});}}catch(e){{}}}});}}
let _t;window.addEventListener('resize',()=>{{clearTimeout(_t);_t=setTimeout(resizeAll,150);}});
document.addEventListener('DOMContentLoaded',()=>{{let a=0;const p=setInterval(()=>{{
  if(IDS.every(id=>{{const el=document.getElementById(id);return el&&el.data;}})||a++>40){{clearInterval(p);resizeAll();}}}},150);}});
</script>"""

import crypto_gate
HTML = HTML + crypto_gate.dashboard_gate_html(HTML_BODY) + "</body></html>"

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(HTML)
print(f"Dashboard -> {OUT_HTML}  ({len(HTML)//1024} KB)")
