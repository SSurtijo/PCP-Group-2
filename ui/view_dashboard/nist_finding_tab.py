### nist_finding_tab.py
# Renders the CSF tab for PCP project dashboard UI.
# All functions use strict formatting: file-level header (###), function-level header (#), and step-by-step logic (#) comments.

import streamlit as st
from services import get_company_category_scores_df
from api import get_internal_scan
from charts.internal_csf_charts import (
    csf_maturity_line_chart,
    build_csf_controls_table_df,
)
from charts.nist_finding_tab_L2_mapping_table import render_l2_domains_table


# Renders the 'CSF' tab with the Current Maturity graph, controls table, and L2 Domains table using Streamlit.
# Usage: app.py (CSF tab)
# Inputs: selected_company_id (int), company_domains (list)
# Outputs: None (renders tab in UI)
def render_nist_finding_tab(selected_company_id, company_domains):
    # Check if a company is selected
    if not selected_company_id:
        st.info("Select a company to view CSF maturity.")
        return

    # Load scores dataframe and internal scan rows
    scores_df = get_company_category_scores_df(selected_company_id)
    try:
        internal_rows = get_internal_scan(limit=2000)  # control_ref + cmm_rating (etc.)
    except Exception:
        internal_rows = []

    # Internal CSF Graph section
    with st.expander("Internal CSF Graph", expanded=True):
        chart = csf_maturity_line_chart(scores_df, internal_rows)
        if chart is not None:
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No current maturity data available for this company.")

    # Controls & CMM Table section
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

    # L2 Domains table section
    with st.expander("NIST CSF L2 Domains Table", expanded=True):
        render_l2_domains_table(selected_company_id)
