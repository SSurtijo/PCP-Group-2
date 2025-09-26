###
# File: ui/view_companies.py
# Description: Displays all companies in a table for PCP project UI.
###

import streamlit as st
from utils.dataframe_utils import to_df, stringify_nested


def show_all_companies(companies_payload):
    # Function: show_all_companies
    # Description: Displays all companies in a table and shows the total count metric using Streamlit.
    # Usage: show_all_companies(companies_payload)
    # Returns: None (renders table in UI)
    """Show section header for companies"""
    st.subheader("Companies")

    """Show total companies metric"""
    st.metric("Total Companies", len(companies_payload))

    """Convert company data to DataFrame for display"""
    df_all = stringify_nested(to_df(companies_payload))

    """Display the DataFrame if not empty, otherwise show info message"""
    if not df_all.empty:
        st.dataframe(df_all, use_container_width=True)
    else:
        st.info("No data.")
