###
# File: charts/nist_finding_tab_L2_mapping_table.py
# Description: Streamlit table builder for NIST CSF L2 domain maturity mapping.
###

import streamlit as st
import pandas as pd
from api import get_internal_scan
from utils.dataframe_utils import to_df
from nist.nist_mappings import CSF_L1_FUNCTION_FULL
from nist.nist_helpers import get_function_from_code_or_ref


def get_maturity_label(rating):
    """Map CMM rating to maturity label and indicator."""
    if rating < 2.0:
        return "Weak", "🔴"
    elif rating < 3.0:
        return "Marginal", "🟡"
    elif rating < 3.5:
        return "Marginal/Strong", "🟢"
    else:
        return "Strong", "🟢"


def render_l2_domains_table(selected_company_id=None):
    """Render NIST CSF L2 domain maturity table for selected company."""
    st.caption("Detailed view of maturity per NIST CSF L2 Domain using CMM ratings")
    raw_data = get_internal_scan(limit=1000)
    df_cmm = to_df(raw_data)
    """Handle empty input dataframe."""
    if df_cmm.empty:
        st.warning("No CMM ratings data available")
        return
    """Filter by company if selected."""
    if selected_company_id is not None and "company_id" in df_cmm.columns:
        try:
            df_cmm = df_cmm[
                df_cmm["company_id"].astype(str) == str(selected_company_id)
            ]
        except (TypeError, ValueError):
            st.warning("Company ID filtering issue. Showing all data.")
    """Check for required columns."""
    required_cols = ["control_ref", "cmm_rating"]
    missing_cols = [col for col in required_cols if col not in df_cmm.columns]
    if missing_cols:
        st.error(f"Missing required columns: {missing_cols}")
        return
    """Aggregate ratings by domain."""
    unique_domains = df_cmm["domain"].dropna().unique()
    domain_ratings = []
    for api_domain_name in unique_domains:
        domain_data = df_cmm[df_cmm["domain"] == api_domain_name]
        ratings_for_domain = []
        for _, row in domain_data.iterrows():
            try:
                rating = pd.to_numeric(row["cmm_rating"], errors="coerce")
                if not pd.isna(rating):
                    ratings_for_domain.append(float(rating))
            except (TypeError, ValueError, KeyError):
                continue
        if ratings_for_domain:
            avg_rating = sum(ratings_for_domain) / len(ratings_for_domain)
            try:
                first_control = domain_data["control_ref"].iloc[0]
                function_code = get_function_from_code_or_ref(first_control)
                function_name = CSF_L1_FUNCTION_FULL.get(function_code, function_code)
            except (IndexError, KeyError):
                function_name = "Unknown"
            domain_ratings.append(
                {
                    "function": function_name,
                    "domain": api_domain_name,
                    "cmm_rating": avg_rating,
                    "control_count": len(ratings_for_domain),
                }
            )
    """Handle case with no valid domain ratings."""
    if not domain_ratings:
        st.warning("No valid data found for the selected company")
        return
    domain_ratings = pd.DataFrame(domain_ratings)
    domain_ratings["cmm_rating"] = pd.to_numeric(
        domain_ratings["cmm_rating"], errors="coerce"
    ).fillna(0)
    domain_ratings["control_count"] = pd.to_numeric(
        domain_ratings["control_count"], errors="coerce"
    ).fillna(0)
    domain_ratings[["label", "indicator"]] = domain_ratings["cmm_rating"].apply(
        lambda x: pd.Series(get_maturity_label(x))
    )
    """Categorize and sort functions."""
    function_order = ["Govern", "Identify", "Protect", "Detect", "Respond", "Recover"]
    try:
        domain_ratings["function"] = domain_ratings["function"].astype(str)
        existing_functions = [
            f for f in function_order if f in domain_ratings["function"].values
        ]
        other_functions = [
            f for f in domain_ratings["function"].unique() if f not in function_order
        ]
        all_categories = existing_functions + other_functions
        domain_ratings["function"] = pd.Categorical(
            domain_ratings["function"], categories=all_categories, ordered=True
        )
        domain_ratings = domain_ratings.sort_values(["function", "domain"])
    except (TypeError, ValueError):
        st.warning("Function categorization issue. Using simple sorting.")
        domain_ratings = domain_ratings.sort_values(["domain"])
    """Display summary metrics for domain maturity levels."""
    col1, col2, col3, col4 = st.columns(4)
    try:
        domain_ratings["cmm_rating"] = pd.to_numeric(
            domain_ratings["cmm_rating"], errors="coerce"
        ).fillna(0)
        with col1:
            weak_count = len(domain_ratings[domain_ratings["cmm_rating"] < 2.0])
            st.metric("Weak Domains", int(weak_count))
        with col2:
            marginal_count = len(
                domain_ratings[
                    (domain_ratings["cmm_rating"] >= 2.0)
                    & (domain_ratings["cmm_rating"] < 3.0)
                ]
            )
            st.metric("Marginal Domains", int(marginal_count))
        with col3:
            marginal_strong_count = len(
                domain_ratings[
                    (domain_ratings["cmm_rating"] >= 3.0)
                    & (domain_ratings["cmm_rating"] < 3.5)
                ]
            )
            st.metric("Marginal/Strong Domains", int(marginal_strong_count))
        with col4:
            strong_count = len(domain_ratings[domain_ratings["cmm_rating"] >= 3.5])
            st.metric("Strong Domains", int(strong_count))
    except (TypeError, ValueError):
        st.warning("Error calculating summary statistics. Using default values.")
        with col1:
            st.metric("Weak Domains", 0)
        with col2:
            st.metric("Marginal Domains", 0)
        with col3:
            st.metric("Marginal/Strong Domains", 0)
        with col4:
            st.metric("Strong Domains", 0)
    """Prepare table for display."""
    display_df = domain_ratings[
        ["function", "domain", "cmm_rating", "label", "indicator"]
    ].copy()
    display_df["function"] = display_df["function"].astype(str)
    merged_display_df = display_df.copy()
    prev_function = None
    for idx, row in merged_display_df.iterrows():
        if row["function"] == prev_function:
            merged_display_df.at[idx, "function"] = ""
        else:
            prev_function = row["function"]
    merged_display_df = merged_display_df.rename(
        {
            "function": "Function (L1)",
            "domain": "Domain (L2)",
            "cmm_rating": "Rating",
            "label": "Maturity Level",
            "indicator": "Status",
        },
        axis=1,
    )
    try:
        merged_display_df["Rating"] = pd.to_numeric(
            merged_display_df["Rating"], errors="coerce"
        ).fillna(0)
        st.dataframe(
            merged_display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Function (L1)": st.column_config.TextColumn(width="medium"),
                "Domain (L2)": st.column_config.TextColumn(width="large"),
                "Rating": st.column_config.NumberColumn(format="%.2f", width="small"),
                "Maturity Level": st.column_config.TextColumn(width="medium"),
                "Status": st.column_config.TextColumn(width="small"),
            },
        )
    except Exception:
        st.warning("Error displaying table with formatting. Showing simple table.")
        st.dataframe(merged_display_df, use_container_width=True, hide_index=True)
