import streamlit as st
from helpers import get_company_category_scores_df
from api import get_internal_scan
from charts.internal_csf_charts import (
    csf_maturity_line_chart,
    build_csf_controls_table_df,
)


def render_nist_finding_tab(selected_company_id, company_domains):
    """Render the 'CSF' tab with the Current Maturity graph + controls table."""
    if not selected_company_id:
        st.info("Select a company to view CSF maturity.")
        return

    # Load once, reuse for both expanders
    scores_df = get_company_category_scores_df(selected_company_id)
    try:
        internal_rows = get_internal_scan(limit=2000)  # control_ref + cmm_rating (etc.)
    except Exception:
        internal_rows = []

    # 1) Graph (existing)
    with st.expander("Internal CSF Graph", expanded=True):
        chart = csf_maturity_line_chart(scores_df, internal_rows)
        if chart is not None:
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No current maturity data available for this company.")

    # 2) New table
    with st.expander("CSF — Controls & CMM Table", expanded=True):
        df = build_csf_controls_table_df(
            scores_df=scores_df,
            internal_rows=internal_rows,
            company_id=selected_company_id,
        )
        if df is None or df.empty:
            st.info("No control-level CMM ratings available to display.")
        else:
            st.dataframe(df, use_container_width=True)
