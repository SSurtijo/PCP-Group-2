import streamlit as st
from helpers import get_company_category_scores_df
from charts.csf_charts import csf_maturity_line_chart
from api import get_internal_scan


def render_nist_finding_tab(selected_company_id, company_domains):
    """Render the 'CSF' tab with the Current Maturity line chart."""
    with st.expander("Internal CSF Graph", expanded=True):

        if not selected_company_id:
            st.info("Select a company to view CSF maturity.")
            return

        scores_df = get_company_category_scores_df(selected_company_id)

        try:
            internal_rows = get_internal_scan(
                limit=2000
            )  # list[dict] with control_ref + cmm_rating
        except Exception:
            internal_rows = []

        chart = csf_maturity_line_chart(scores_df, internal_rows)
        if chart is not None:
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No current maturity data available for this company.")
