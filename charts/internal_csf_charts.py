# charts/csf_charts.py
import altair as alt
import pandas as pd

from nist.nist_mappings import EXTERNAL_FINDINGS_TO_CONTROLS
from nist.nist_helpers import controls_for_finding
from helpers import CATEGORY_NAMES
from .charts_helpers import (
    _norm_ref,
    _prefix,
    _rating,
    detect_control_ref_col,
    csv_upper,
    fmt_or_dash,
    mean,
)

# Normalize external mapping up-front
EXTERNAL_FINDINGS_TO_CONTROLS_NORM = {
    finding: [_norm_ref(c) for c in ctrls]
    for finding, ctrls in EXTERNAL_FINDINGS_TO_CONTROLS.items()
}


def _ordered_findings(api_findings: list[str]) -> list[str]:
    # If CATEGORY_NAMES mirrors your preferred order, use it; otherwise keep API order
    if CATEGORY_NAMES:
        wanted = [c for c in CATEGORY_NAMES if c in set(api_findings)]
        if wanted:
            return wanted
    return api_findings


def _fallback_chart(scores_df: pd.DataFrame):
    """GPA-only fallback (no internal ratings available)."""
    gpa_col = next((c for c in ("category_gpa", "gpa") if c in scores_df.columns), None)
    if not gpa_col or "Category" not in scores_df.columns:
        return None

    api_findings = [str(x).strip() for x in scores_df["Category"].dropna().tolist()]
    findings = [f for f in api_findings if f in EXTERNAL_FINDINGS_TO_CONTROLS_NORM]
    if not findings:
        return None

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

    order = _ordered_findings(findings)
    df["Category"] = pd.Categorical(df["Category"], categories=order, ordered=True)

    base = alt.Chart(df).encode(
        x=alt.X("Category:N", sort=order, title="External Findings"),
        y=alt.Y(
            "findings_gpa:Q", title="Findings GPA (0–4)", scale=alt.Scale(domain=[0, 4])
        ),
    )
    line = base.mark_line()
    pts = base.mark_circle(size=80).encode(
        tooltip=[
            alt.Tooltip("findings_label:N", title="Findings"),
            alt.Tooltip("findings_gpa_disp:N", title="Findings GPA"),
            alt.Tooltip("controls_disp:N", title="Control"),
            alt.Tooltip("cmm_mean_disp:N", title="Mean CMM"),
        ]
    )
    return (
        (line + pts)
        .properties(title="Internal CSF Graph")
        .configure_axis(labelColor="white", titleColor="white")
        .configure_title(color="white")
    )


def csf_maturity_line_chart(
    scores_df: pd.DataFrame, internal_rows: list[dict] | None = None
):
    """
    Plot by EXTERNAL FINDINGS from the API (scores_df["Category"]).

    Tooltip:
      - Findings                : the finding name (from API)
      - Findings GPA            : API GPA
      - Control                 : ALL CAPS, from EXTERNAL_FINDINGS_TO_CONTROLS
      - Mean CMM                : mean of internal ratings (API) for those mapped controls
    """
    if scores_df is None or scores_df.empty or "Category" not in scores_df.columns:
        return None

    api_findings = [str(x).strip() for x in scores_df["Category"].dropna().tolist()]
    findings = [f for f in api_findings if f in EXTERNAL_FINDINGS_TO_CONTROLS_NORM]
    if not findings:
        return None

    # Internal ratings
    df_ctrl = pd.DataFrame(internal_rows or [])
    if df_ctrl.empty:
        return _fallback_chart(scores_df)

    ctrl_col = detect_control_ref_col(df_ctrl)
    if not ctrl_col:
        return _fallback_chart(scores_df)

    df_ctrl = df_ctrl.copy()
    df_ctrl["control_ref_norm"] = df_ctrl[ctrl_col].apply(_norm_ref)
    df_ctrl["rating_val"] = df_ctrl.apply(_rating, axis=1)
    df_ctrl = df_ctrl.dropna(subset=["control_ref_norm", "rating_val"])

    # Finding -> GPA
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

    # index of ratings by normalized control
    ctrl_index = df_ctrl.set_index("control_ref_norm")["rating_val"]

    rows = []
    for finding in findings:
        mapped_controls = controls_for_finding(finding)  # normalized list
        # Control tooltip (ALL CAPS)
        controls_disp = csv_upper(mapped_controls)

        # Mean CMM across mapped controls present in internal data
        vals = [float(ctrl_index[c]) for c in mapped_controls if c in ctrl_index]
        cmm_mean = mean(vals)

        # GPA
        gpa_val = finding_gpa.get(finding, float("nan"))

        rows.append(
            {
                "Finding": finding,
                "y_val": cmm_mean,
                "findings_label": finding,
                "findings_gpa_disp": fmt_or_dash(gpa_val, 2),
                "controls_disp": controls_disp,
                "cmm_mean_disp": fmt_or_dash(cmm_mean, 2),
            }
        )

    df = pd.DataFrame(rows)
    order = _ordered_findings(findings)
    df["Finding"] = pd.Categorical(df["Finding"], categories=order, ordered=True)

    base = alt.Chart(df).encode(
        x=alt.X("Finding:N", sort=order, title="External Findings"),
        y=alt.Y(
            "y_val:Q", title="Current maturity (0–4)", scale=alt.Scale(domain=[0, 4])
        ),
    )
    line = base.mark_line()
    pts = base.mark_circle(size=80).encode(
        tooltip=[
            alt.Tooltip("findings_label:N", title="Findings"),
            alt.Tooltip("findings_gpa_disp:N", title="Findings GPA"),
            alt.Tooltip("controls_disp:N", title="Control"),
            alt.Tooltip("cmm_mean_disp:N", title="Mean CMM"),
        ]
    )
    return (
        (line + pts)
        .properties(title="Internal CSF Graph")
        .configure_axis(labelColor="white", titleColor="white")
        .configure_title(color="white")
    )


# ---------- NEW: build table DF for CSF Controls ----------
def build_csf_controls_table_df(
    scores_df: pd.DataFrame,
    internal_rows: list[dict] | None,
    company_id,
) -> pd.DataFrame:
    """
    Returns a table with columns:
      - company_id
      - category            (external finding)
      - nist_control        (normalized, e.g., PR.PS-01)
      - cmm_score           (parsed numeric rating from internal scan)

    Uses the same mapping and parsing logic as the graph.
    Only includes controls that actually have a rating in the internal data.
    """
    if scores_df is None or scores_df.empty:
        return pd.DataFrame()

    df_ctrl = pd.DataFrame(internal_rows or [])
    if df_ctrl.empty:
        return pd.DataFrame()

    ctrl_col = detect_control_ref_col(df_ctrl)
    if not ctrl_col:
        return pd.DataFrame()

    df_ctrl = df_ctrl.copy()
    df_ctrl["control_ref_norm"] = df_ctrl[ctrl_col].apply(_norm_ref)
    df_ctrl["rating_val"] = df_ctrl.apply(_rating, axis=1)
    df_ctrl = df_ctrl.dropna(subset=["control_ref_norm", "rating_val"])

    ctrl_index = df_ctrl.set_index("control_ref_norm")["rating_val"]

    # Which categories (findings) to show
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

    rows = []
    for finding in _ordered_findings(findings):
        mapped_controls = EXTERNAL_FINDINGS_TO_CONTROLS_NORM.get(finding, [])
        for c in sorted(mapped_controls):
            if c not in ctrl_index:
                # Skip controls that don't have a rating in internal data
                continue
            rows.append(
                {
                    "company_id": company_id,
                    "category": finding,
                    "nist_control": c,
                    "cmm_score": float(ctrl_index[c]),
                }
            )

    return pd.DataFrame(rows)
