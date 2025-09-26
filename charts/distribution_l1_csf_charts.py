###
# File: charts/distribution_l1_csf_charts.py
# Description: Altair chart builder for L1 CSF function distribution. Used in dashboard visualizations.
###
import altair as alt
import pandas as pd
from collections import defaultdict
from nist.nist_mappings import EXTERNAL_FINDINGS_TO_CONTROLS
from utils.normalization import norm_ref
from helpers import detect_control_ref_col
from services import get_company_category_scores_df
from api import get_internal_scan


def distribution_l1_function_bar_chart(selected_company_id: int) -> alt.Chart | None:
    """Get company category scores and internal scan data."""
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
    """Map controls to present categories."""
    control_to_present_categories = defaultdict(list)
    for finding, ctrls in EXTERNAL_FINDINGS_TO_CONTROLS.items():
        if finding in present_categories:
            for c in ctrls:
                control_to_present_categories[norm_ref(c)].append(finding)
    allowed_controls = set(control_to_present_categories.keys())
    try:
        internal_rows = get_internal_scan(limit=2000)
    except Exception:
        return None
    """Handle empty internal scan data."""
    if not internal_rows:
        return None
    df_ctrl = pd.DataFrame(internal_rows)
    if df_ctrl.empty:
        return None
    """Detect control reference column and normalize references."""
    ctrl_col = detect_control_ref_col(df_ctrl)
    if not ctrl_col:
        return None
    df_ctrl = df_ctrl.copy()
    df_ctrl["control_ref_norm"] = df_ctrl[ctrl_col].apply(norm_ref)
    df_ctrl = df_ctrl[df_ctrl["control_ref_norm"].isin(allowed_controls)]
    if df_ctrl.empty:
        return None
    """Count unique controls and map to L1 functions."""
    unique_controls = df_ctrl["control_ref_norm"].drop_duplicates().tolist()
    L1 = {
        "GV": "Govern",
        "ID": "Identify",
        "PR": "Protect",
        "DE": "Detect",
        "RS": "Respond",
        "RC": "Recover",
    }

    def to_l1(control: str) -> str:
        p = (control.split(".")[0] if control else "").upper()
        return L1.get(p[:2], "Other")

    l1_counts = defaultdict(int)
    for c in unique_controls:
        l1 = to_l1(c)
        l1_counts[l1] += 1
    order = ["Govern", "Identify", "Protect", "Detect", "Respond", "Recover"]
    rows = []
    for l1 in order:
        if l1_counts[l1] > 0:
            rows.append({"l1_func": l1, "count": l1_counts[l1]})
    if l1_counts["Other"] > 0:
        rows.append({"l1_func": "Other", "count": l1_counts["Other"]})
    """Return None if no rows for chart."""
    if not rows:
        return None
    """Create bar chart: x=L1 function, y=control count, tooltip for function and count."""
    df = pd.DataFrame(rows)
    base = alt.Chart(df).encode(
        x=alt.X("l1_func:N", sort=order, title=None),
        y=alt.Y("count:Q", title="Control Count", scale=alt.Scale(domainMin=0)),
    )
    bar = base.mark_bar(size=42, opacity=0.85).encode(
        tooltip=[
            alt.Tooltip("l1_func:N", title="Function"),
            alt.Tooltip("count:Q", title="Control Count"),
        ]
    )
    """Return Altair chart object."""
    return bar.configure_axis(labelColor="white", titleColor="white")
