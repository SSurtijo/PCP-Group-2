###
# File: charts/external_csf_charts.py
# Description: Altair chart builders for external CSF findings and controls. Used in dashboard visualizations.
###
import altair as alt
import pandas as pd
from api import get_internal_scan
from helpers import extract_rating, detect_control_ref_col, fmt_or_dash, csv_plain
from utils.normalization import norm_ref
from nist.nist_mappings import EXTERNAL_FINDINGS_TO_CONTROLS


def internal_controls_cmm_bar_chart(selected_company_id: int) -> alt.Chart | None:
    """Get internal scan data for selected company."""
    internal_rows = []
    try:
        internal_rows = get_internal_scan(limit=2000)
    except Exception:
        return None
    """Handle empty scan data."""
    if not internal_rows:
        return None
    """Build dataframe from internal scan rows."""
    df = pd.DataFrame(internal_rows)
    if df.empty:
        return None
    """Detect control reference column and normalize references."""
    ctrl_col = detect_control_ref_col(df)
    if not ctrl_col:
        return None
    df = df.copy()
    df["control_ref_norm"] = df[ctrl_col].apply(norm_ref)
    df["rating_val"] = df.apply(extract_rating, axis=1)
    df = df.dropna(subset=["control_ref_norm", "rating_val"])
    from json_handler import load_company_bundle

    """Load company bundle and collect present categories."""
    bundle = load_company_bundle(selected_company_id) or {}
    present_categories = set()
    for cat in bundle.get("categories", []):
        c = cat.get("Category")
        if c:
            present_categories.add(c)
    for domain in bundle.get("domains", []):
        fbc = domain.get("findings_by_category", {})
        present_categories.update(fbc.keys())
    from services import get_company_category_scores_df
    from collections import defaultdict

    """Get company category scores and filter present categories."""
    scores_df = get_company_category_scores_df(selected_company_id)
    present_categories = set()
    if (
        scores_df is not None
        and not scores_df.empty
        and "Category" in scores_df.columns
    ):
        present_categories = {
            str(x).strip() for x in scores_df["Category"].dropna().tolist()
        }
    """Map controls to findings for present categories."""
    control_to_findings = defaultdict(list)
    for finding, ctrls in EXTERNAL_FINDINGS_TO_CONTROLS.items():
        if finding not in present_categories:
            continue
        for c in ctrls:
            control_to_findings[norm_ref(c)].append(finding)
    allowed_controls = set(control_to_findings.keys())
    df_ctrl = df[df["control_ref_norm"].isin(allowed_controls)]
    if df_ctrl.empty:
        return None
    """Build chart rows for each control and mapped category."""
    rows = []
    for _, r in df_ctrl.iterrows():
        c = r["control_ref_norm"]
        val = float(r["rating_val"])
        mapped_present = control_to_findings.get(c, [])
        rows.append(
            {
                "control": c,
                "cmm_score": val,
                "cmm_score_disp": fmt_or_dash(val, 2),
                "mapped_category_disp": (
                    csv_plain(mapped_present) if mapped_present else "-"
                ),
            }
        )
    if not rows:
        return None
    """Prepare chart dataframe and sort by category order."""
    chart_df = pd.DataFrame(rows)
    cat_index = (
        {c: i for i, c in enumerate(scores_df["Category"].dropna().tolist())}
        if scores_df is not None and "Category" in scores_df.columns
        else {}
    )
    chart_df["cat_order"] = chart_df["control"].apply(
        lambda c: min(
            [cat_index.get(f, 10**6) for f in control_to_findings.get(c, [])] or [10**6]
        )
    )
    chart_df = chart_df.sort_values(["cat_order", "control"])
    chart_df = chart_df.drop(columns=["cat_order"])
    """Create bar chart: x=control, y=CMM score, tooltip for score and mapped category."""
    base = alt.Chart(chart_df).encode(
        x=alt.X("control:N", sort="ascending", title=None),
        y=alt.Y(
            "cmm_score:Q",
            title="CMM Score (0–4)",
            scale=alt.Scale(domain=[0, 4], nice=False),
        ),
    )
    bar = base.mark_bar(size=28, opacity=0.85).encode(
        tooltip=[
            alt.Tooltip("cmm_score_disp:N", title="CMM Score"),
            alt.Tooltip("mapped_category_disp:N", title="Mapped Category"),
        ]
    )
    """Return Altair chart object."""
    return bar.configure_axis(labelColor="white", titleColor="white")
