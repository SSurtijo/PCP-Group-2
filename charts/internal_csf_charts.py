###
# File: charts/internal_csf_charts.py
# Description: Altair chart builders for internal controls and CSF maturity. Used in dashboard visualizations.
###

import altair as alt
import pandas as pd
from api import get_internal_scan
from nist.nist_mappings import EXTERNAL_FINDINGS_TO_CONTROLS
from nist.nist_helpers import controls_for_finding
from utils.dataframe_utils import CATEGORY_NAMES
from helpers import extract_rating, detect_control_ref_col, csv_upper, fmt_or_dash, mean
from utils.normalization import norm_ref

EXTERNAL_FINDINGS_TO_CONTROLS_NORM = {
    finding: [norm_ref(c) for c in ctrls]
    for finding, ctrls in EXTERNAL_FINDINGS_TO_CONTROLS.items()
}


def _ordered_findings(api_findings: list[str]) -> list[str]:
    """Order findings according to CATEGORY_NAMES if available."""
    if CATEGORY_NAMES:
        wanted = [c for c in CATEGORY_NAMES if c in set(api_findings)]
        if wanted:
            return wanted
    return api_findings


def _fallback_chart(scores_df: pd.DataFrame):
    """Fallback: Bar chart of findings GPA if no internal data."""
    """Check for required columns"""
    gpa_col = next((c for c in ("category_gpa", "gpa") if c in scores_df.columns), None)
    if not gpa_col or "Category" not in scores_df.columns:
        return None
    """Filter findings to those with controls"""
    api_findings = [str(x).strip() for x in scores_df["Category"].dropna().tolist()]
    findings = [f for f in api_findings if f in EXTERNAL_FINDINGS_TO_CONTROLS_NORM]
    if not findings:
        return None
    """Prepare DataFrame for chart"""
    df = (
        scores_df[scores_df["Category"].isin(findings)][["Category", gpa_col]]
        .rename(columns={gpa_col: "findings_gpa"})
        .copy()
    )
    df["findings_gpa"] = pd.to_numeric(df["findings_gpa"], errors="coerce").clip(0, 4)
    df["findings_label"] = df["Category"].astype(str)
    df["findings_gpa_disp"] = df["findings_gpa"].apply(lambda v: fmt_or_dash(v, 2))
    df["controls_disp"] = "-"
    df["cmm_mean_disp"] = "-"
    """Set category order"""
    order = _ordered_findings(findings)
    df["Category"] = pd.Categorical(df["Category"], categories=order, ordered=True)
    """Build Altair chart"""
    base = alt.Chart(df).encode(
        x=alt.X("Category:N", sort=order, title=None),
        y=alt.Y(
            "findings_gpa:Q",
            title="Findings GPA",
            scale=alt.Scale(domain=[0, 4], nice=False),
        ),
    )
    bar = base.mark_bar(size=40, opacity=0.85).encode(
        tooltip=[
            alt.Tooltip("findings_gpa_disp:N", title="Finding GPA"),
            alt.Tooltip("controls_disp:N", title="Control"),
        ]
    )
    return bar.configure_axis(labelColor="white", titleColor="white")


def csf_maturity_line_chart(selected_company_id: int) -> alt.Chart:
    """Bar chart of findings GPA with mapped controls for a company."""
    """Load company category scores and internal scan data"""
    from services import get_company_category_scores_df

    scores_df = get_company_category_scores_df(selected_company_id)
    try:
        internal_rows = get_internal_scan(limit=2000)
    except Exception:
        internal_rows = []
    if scores_df is None or scores_df.empty or "Category" not in scores_df.columns:
        return None
    """Filter findings to those with controls"""
    api_findings = [str(x).strip() for x in scores_df["Category"].dropna().tolist()]
    findings = [f for f in api_findings if f in EXTERNAL_FINDINGS_TO_CONTROLS_NORM]
    if not findings:
        return None
    """Prepare internal controls DataFrame"""
    df_ctrl = pd.DataFrame(internal_rows or [])
    if df_ctrl.empty:
        return _fallback_chart(scores_df)
    ctrl_col = detect_control_ref_col(df_ctrl)
    if not ctrl_col:
        return _fallback_chart(scores_df)
    df_ctrl = df_ctrl.copy()
    df_ctrl["control_ref_norm"] = df_ctrl[ctrl_col].apply(norm_ref)
    df_ctrl["rating_val"] = df_ctrl.apply(extract_rating, axis=1)
    df_ctrl = df_ctrl.dropna(subset=["control_ref_norm", "rating_val"])
    """Map findings to GPA"""
    gpa_col = next((c for c in ("category_gpa", "gpa") if c in scores_df.columns), None)
    finding_gpa = {}
    if gpa_col:
        tmp = scores_df[["Category", gpa_col]].copy()
        tmp[gpa_col] = pd.to_numeric(tmp[gpa_col], errors="coerce")
        for _, r in tmp.iterrows():
            name = str(r["Category"]).strip()
            val = r[gpa_col]
            if pd.notna(val):
                finding_gpa[name] = float(val)
    ctrl_index = df_ctrl.set_index("control_ref_norm")["rating_val"]
    """Build chart rows"""
    rows = []
    for finding in findings:
        mapped_controls = controls_for_finding(finding)
        controls_disp = csv_upper(mapped_controls)
        gpa_val = finding_gpa.get(finding, float("nan"))
        rows.append(
            {
                "Finding": finding,
                "findings_gpa": gpa_val,
                "findings_gpa_disp": fmt_or_dash(gpa_val, 2),
                "controls_disp": controls_disp,
            }
        )
    """Prepare DataFrame and build Altair chart"""
    df = pd.DataFrame(rows)
    order = _ordered_findings(findings)
    df["Finding"] = pd.Categorical(df["Finding"], categories=order, ordered=True)
    base = alt.Chart(df).encode(
        x=alt.X("Finding:N", sort=order, title=None),
        y=alt.Y(
            "findings_gpa:Q",
            title="Findings GPA",
            scale=alt.Scale(domain=[0, 4], nice=False),
        ),
    )
    bar = base.mark_bar(size=40, opacity=0.85).encode(
        tooltip=[
            alt.Tooltip("findings_gpa_disp:N", title="Finding GPA"),
            alt.Tooltip("controls_disp:N", title="Control"),
        ]
    )
    return bar.configure_axis(labelColor="white", titleColor="white")


def build_csf_controls_table_df(
    scores_df: pd.DataFrame,
    internal_rows: list[dict] | None,
    company_id,
) -> pd.DataFrame:
    """Builds a table of CSF controls and CMM scores for a company."""
    """Validate input"""
    if scores_df is None or scores_df.empty:
        return pd.DataFrame()
    df_ctrl = pd.DataFrame(internal_rows or [])
    if df_ctrl.empty:
        return pd.DataFrame()
    ctrl_col = detect_control_ref_col(df_ctrl)
    if not ctrl_col:
        return pd.DataFrame()
    df_ctrl = df_ctrl.copy()
    df_ctrl["control_ref_norm"] = df_ctrl[ctrl_col].apply(norm_ref)
    df_ctrl["rating_val"] = df_ctrl.apply(extract_rating, axis=1)
    df_ctrl = df_ctrl.dropna(subset=["control_ref_norm", "rating_val"])
    ctrl_index = df_ctrl.set_index("control_ref_norm")["rating_val"]
    """Determine findings to include"""
    api_findings = (
        [str(x).strip() for x in scores_df["Category"].dropna().tolist()]
        if "Category" in scores_df.columns
        else []
    )
    findings = [f for f in api_findings if f in EXTERNAL_FINDINGS_TO_CONTROLS_NORM]
    if not findings:
        findings = [
            f for f in CATEGORY_NAMES if f in EXTERNAL_FINDINGS_TO_CONTROLS_NORM
        ]
    """Build table rows"""
    rows = []
    for finding in _ordered_findings(findings):
        mapped_controls = EXTERNAL_FINDINGS_TO_CONTROLS_NORM.get(finding, [])
        for c in sorted(mapped_controls):
            if c not in ctrl_index:
                continue
            rows.append(
                {
                    "company_id": company_id,
                    "category": finding,
                    "nist_control": c,
                    "cmm_score": float(ctrl_index[c]),
                }
            )
    """Return DataFrame"""
    return pd.DataFrame(rows)
