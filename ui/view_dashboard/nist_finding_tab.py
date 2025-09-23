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
from charts.charts_mixed import external_findings_chart_grouped
from charts.external_csf_charts import internal_controls_cmm_bar_chart
from charts.distribution_l1_csf_charts import distribution_l1_function_bar_chart


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

    # Mix Findings section (grouped horizontal GPA/CMM)
    with st.expander("Mix Findings", expanded=True):
        chart = external_findings_chart_grouped(selected_company_id, internal_rows)
        if chart is None:
            st.info("No category scores available.")
        else:
            st.altair_chart(chart, use_container_width=True)

    # External Findings section
    with st.expander("External Findings", expanded=True):
        chart = csf_maturity_line_chart(selected_company_id)
        if chart is not None:
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No findings GPA data available for this company.")

    # Internal Controls (CMM) section
    with st.expander("Internal Controls (CMM)", expanded=True):
        cmm_chart = internal_controls_cmm_bar_chart(selected_company_id)
        if cmm_chart is not None:
            st.altair_chart(cmm_chart, use_container_width=True)
        else:
            st.info("No internal controls CMM data available for this company.")

    # L1 Function Distribution section
    with st.expander("L1 Function Distribution (Control Count)", expanded=True):
        l1_chart = distribution_l1_function_bar_chart(selected_company_id)
        if l1_chart is not None:
            st.altair_chart(l1_chart, use_container_width=True)
        else:
            st.info(
                "No eligible controls found to compute L1 distribution for this company."
            )

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
