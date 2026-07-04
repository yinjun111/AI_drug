"""
Disease Coverage analysis — rank diseases by number of chronic/long-term
Orange Book drugs that treat them.

Step A: generate orangebook_disease_drug_count.csv
Step B: build a horizontal bar plot (PNG + standalone HTML)

Mirrors Purple Book Step 6 ("Disease Coverage: Ranked by Number of Targeting Drugs").
"""

import csv
from collections import defaultdict, Counter

IN_CSV  = "orangebook_chronic_indications_clean.csv"
OUT_CSV = "orangebook_disease_drug_count.csv"

# ── Step A: build disease → drugs mapping ─────────────────────────────────────
disease_map = defaultdict(list)   # disease → list of (drug_label, category)

with open(IN_CSV, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        drug     = r["Drug"].strip()
        target   = (r["Target"] or "").strip()
        cat      = r["Category"].strip()
        ind_text = r["Disease / Indication"].strip()
        if not ind_text:
            continue

        # Drug label: drugName(Target) — first gene only
        first_tgt  = target.split("|")[0].split(",")[0].strip() if target else ""
        drug_label = f"{drug}({first_tgt})" if first_tgt else drug

        # Split multi-indication cells on ";"
        for ind in (i.strip() for i in ind_text.split(";")):
            if ind:
                disease_map[ind].append((drug_label, cat))

# Generic category-fallback labels (not real diseases — assigned when a drug's
# mechanism did not match a specific indication rule). Flagged, excluded from plot.
GENERIC_LABELS = {
    "Cardiovascular disease", "Metabolic disorder", "Psychiatric disorder",
    "Neurological disorder", "Respiratory disease", "GI disorder",
    "Autoimmune disease", "Infectious disease", "Cancer", "Skin disorder",
    "Ophthalmic disorder", "Chronic pain", "Chronic condition",
}

# ── Aggregate per disease ─────────────────────────────────────────────────────
rows = []
for disease, drug_list in disease_map.items():
    # Deduplicate drug labels (same drug via multiple routes / formulations)
    seen = {}
    for label, cat in drug_list:
        seen[label] = cat
    count    = len(seen)
    category = Counter(seen.values()).most_common(1)[0][0]
    drugs    = ", ".join(sorted(seen.keys()))
    rows.append({
        "Disease / Indication": disease,
        "Drug_Count":           count,
        "Disease_Category":     category,
        "Is_Specific":          "No" if disease in GENERIC_LABELS else "Yes",
        "Drugs":                drugs,
    })

# Sort by count desc, then disease name
rows.sort(key=lambda r: (-r["Drug_Count"], r["Disease / Indication"].lower()))

# ── Write CSV ─────────────────────────────────────────────────────────────────
with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["Disease / Indication", "Drug_Count",
                                      "Disease_Category", "Is_Specific", "Drugs"])
    w.writeheader()
    w.writerows(rows)

# ── Summary ───────────────────────────────────────────────────────────────────
n_dis      = len(rows)
max_drugs  = rows[0]["Drug_Count"] if rows else 0
n_cats     = len({r["Disease_Category"] for r in rows})
n_multi    = sum(1 for r in rows if r["Drug_Count"] >= 2)
all_drugs  = set()
for r in rows:
    for d in r["Drugs"].split(", "):
        all_drugs.add(d.split("(")[0].strip())

print(f"Diseases / indications:      {n_dis}")
print(f"Unique drugs:                {len(all_drugs)}")
print(f"Max drugs for one disease:   {max_drugs}")
print(f"Disease categories:          {n_cats}")
print(f"Diseases with >=2 drugs:     {n_multi}")
specific = [r for r in rows if r["Is_Specific"] == "Yes"]
print(f"Specific (real) diseases:    {len(specific)}")
print(f"\nTop 20 SPECIFIC diseases by drug count:")
for r in specific[:20]:
    print(f"  {r['Drug_Count']:>3}  {r['Disease_Category']:<15}  {r['Disease / Indication'][:55]}")
print(f"\nOutput -> {OUT_CSV}")


# ══════════════════════════════════════════════════════════════════════════
# Step B — horizontal bar plot (top-N specific diseases)
# ══════════════════════════════════════════════════════════════════════════
import plotly.graph_objects as go

TOP_N = 30

CAT_COLORS = {
    "Cardiovascular": "#DC2626", "Metabolic": "#059669", "Psychiatric": "#7C3AED",
    "Neurology": "#D97706", "Oncology": "#F97316", "Infectious": "#0891B2",
    "Respiratory": "#0EA5E9", "GI": "#84CC16", "Autoimmune": "#2563EB",
    "Pain": "#F59E0B", "Dermatology": "#EC4899", "Ophthalmology": "#10B981",
    "Other": "#9CA3AF", "Other/Unclassified": "#D1D5DB",
}

top = specific[:TOP_N][::-1]   # reverse so highest is at top of horizontal bar

diseases = [r["Disease / Indication"] for r in top]
counts   = [r["Drug_Count"] for r in top]
cats     = [r["Disease_Category"] for r in top]
colors   = [CAT_COLORS.get(c, "#9CA3AF") for c in cats]


def wrap_drugs(s, n=3):
    parts = s.split(", ")
    return "<br>".join(", ".join(parts[i:i+n]) for i in range(0, len(parts), n))


hover = [
    f"<b>{diseases[i]}</b><br><i>{cats[i]}</i><br><br>"
    f"<b>{counts[i]} drug{'s' if counts[i] > 1 else ''}</b><br>"
    f"{wrap_drugs(top[i]['Drugs'])}"
    for i in range(len(top))
]

fig = go.Figure(go.Bar(
    x=counts, y=diseases, orientation="h",
    marker=dict(color=colors, opacity=0.9, line=dict(width=0)),
    text=[str(c) for c in counts], textposition="outside",
    textfont=dict(size=11, color="#1E293B"),
    hovertemplate="%{customdata}<extra></extra>", customdata=hover,
    cliponaxis=False,
))
fig.update_layout(
    title=dict(text="<b>Disease Coverage: Top 30 Specific Indications by Number of "
                    "Chronic/Long-term Orange Book Drugs</b><br>"
                    "<sup>Bars colored by disease category · hover for full drug list</sup>",
               font=dict(size=14)),
    xaxis=dict(title="Number of Approved Drugs", showgrid=True, gridcolor="#E2E8F0",
               zeroline=False),
    yaxis=dict(tickfont=dict(size=10), automargin=True),
    height=max(500, len(top) * 26 + 120),
    margin=dict(l=10, r=70, t=70, b=45),
    paper_bgcolor="#fff", plot_bgcolor="#F8FAFC",
    hoverlabel=dict(bgcolor="#1E293B", font=dict(color="#fff", size=11),
                    bordercolor="#334155", align="left"),
    showlegend=False,
)

OUT_HTML = "orangebook_disease_drug_count.html"
fig.write_html(OUT_HTML, include_plotlyjs="cdn",
               config={"responsive": True, "displaylogo": False})
print(f"Bar plot -> {OUT_HTML}")

# Also try a static PNG (needs kaleido; skip silently if unavailable)
try:
    fig.write_image("orangebook_disease_drug_count.png", width=1000,
                    height=max(500, len(top) * 26 + 120), scale=2)
    print("Bar plot -> orangebook_disease_drug_count.png")
except Exception as e:
    print(f"(PNG export skipped: {str(e)[:60]})")
