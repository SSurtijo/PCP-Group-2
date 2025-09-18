import streamlit as st
from helpers import to_df, stringify_nested


def show_all_companies(companies_payload):
    """View 1 — All Companies table + total metric."""
    st.subheader("Companies")
    st.metric("Total Companies", len(companies_payload))
    df_all = stringify_nested(to_df(companies_payload))
    if not df_all.empty:
        st.dataframe(df_all, use_container_width=True)
    else:
        st.info("No data.")
