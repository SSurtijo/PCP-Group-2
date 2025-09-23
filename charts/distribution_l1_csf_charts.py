### distribution_l1_csf_charts.py
# Chart functions for L1 function distribution of internal controls in PCP project.
# All functions use strict formatting: file-level header (###), function-level header (#), and step-by-step logic (#) comments.

import altair as alt
import pandas as pd
from collections import defaultdict
from nist.nist_mappings import EXTERNAL_FINDINGS_TO_CONTROLS
from utils.normalization import norm_ref
from helpers import detect_control_ref_col
from services import get_company_category_scores_df
from api import get_internal_scan

# Bar chart of internal controls grouped by CSF v2 L1 function.
# Usage: distribution_l1_function_bar_chart(selected_company_id)
# Returns: Altair chart or None


def distribution_l1_function_bar_chart(selected_company_id: int) -> alt.Chart | None:
    # Build present categories from company scores
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
    # Build allowed controls mapped to present categories
    control_to_present_categories = defaultdict(list)
    for finding, ctrls in EXTERNAL_FINDINGS_TO_CONTROLS.items():
        if finding in present_categories:
            for c in ctrls:
                control_to_present_categories[norm_ref(c)].append(finding)
    allowed_controls = set(control_to_present_categories.keys())
    # Load internal scan rows
    try:
        internal_rows = get_internal_scan(limit=2000)
    except Exception:
        return None
    if not internal_rows:
        return None
    df_ctrl = pd.DataFrame(internal_rows)
    if df_ctrl.empty:
        return None
    ctrl_col = detect_control_ref_col(df_ctrl)
    if not ctrl_col:
        return None
    df_ctrl = df_ctrl.copy()
    df_ctrl["control_ref_norm"] = df_ctrl[ctrl_col].apply(norm_ref)
    # Filter to allowed controls and dedupe
    df_ctrl = df_ctrl[df_ctrl["control_ref_norm"].isin(allowed_controls)]
    if df_ctrl.empty:
        return None
    unique_controls = df_ctrl["control_ref_norm"].drop_duplicates().tolist()
    # Map control prefix to L1 function
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
    # Build dataframe for chart
    order = ["Govern", "Identify", "Protect", "Detect", "Respond", "Recover"]
    rows = []
    for l1 in order:
        if l1_counts[l1] > 0:
            rows.append({"l1_func": l1, "count": l1_counts[l1]})
    # Optionally include 'Other' if present
    if l1_counts["Other"] > 0:
        rows.append({"l1_func": "Other", "count": l1_counts["Other"]})
    if not rows:
        return None
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
    return bar.configure_axis(labelColor="white", titleColor="white")
