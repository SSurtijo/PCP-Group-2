###
# File: ui/view_dashboard/company_tab.py
# Description: Renders the Company tab for PCP project dashboard UI.
###

import streamlit as st
import pandas as pd
from utils.dataframe_utils import to_df, stringify_nested
from services import get_company_category_scores_df, company_summary
from charts.charts_mixed import company_category_scores_chart
from nist.nist_helpers import summarize_csf_for_category
from json_handler import load_company_bundle


# ---------- helpers to shape tables like the screenshot ----------


def _domains_table(
    selected_company_id: int, company_domains: list[dict]
) -> pd.DataFrame:
    # Function: _domains_table
    # Description: Builds a table with domain info and first/last seen dates for the selected company.
    # Usage: _domains_table(selected_company_id, company_domains)
    # Returns: DataFrame with domain info
    """Prepare rows for each domain"""
    rows = []
    for d in company_domains or []:
        did = d.get("domain_id") or d.get("id") or d.get("domainId")  # Get domain ID
        name = (
            d.get("domain_name") or d.get("domain") or d.get("name")
        )  # Get domain name

        """Derive first/last seen dates from findings"""
        fbc = d.get("findings_by_category") or {}
        dates = []
        for lst in fbc.values():
            for r in lst or []:
                dt = r.get("found_date") or r.get("date") or r.get("scan_date")
                if dt:
                    dates.append(str(dt))
        first_seen = min(dates) if dates else None  # Earliest date
        last_seen = max(dates) if dates else None  # Latest date

        """Add domain info to rows"""
        rows.append(
            {
                "domain_id": did,
                "company_id": int(selected_company_id) if selected_company_id else None,
                "domain_name": name,
                "source": "synthetic",  # label per your screenshot
                "first_seen": first_seen,
                "last_seen": last_seen,
            }
        )

    """Create DataFrame from rows"""
    df = pd.DataFrame(
        rows,
        columns=[
            "domain_id",
            "company_id",
            "domain_name",
            "source",
            "first_seen",
            "last_seen",
        ],
    )
    return df


def _category_scores_table(selected_company_id: int) -> pd.DataFrame:
    """Builds a table with company category scores, GPA, and NIST CSF identifiers for the selected company."""
    scores = get_company_category_scores_df(selected_company_id)
    if scores is None or scores.empty:
        """Return empty DataFrame if no scores"""
        return pd.DataFrame(
            columns=[
                "company_id",
                "Category",
                "nist_csf_identifiers",
                "category_gpa",
                "category_score",
                "aggregated_at",
            ]
        )

    """Get aggregated_at from bundle"""
    bundle = load_company_bundle(selected_company_id) or {}
    cats = pd.DataFrame(bundle.get("categories") or [])
    cats = (
        cats[["Category", "aggregated_at"]]
        if not cats.empty
        else pd.DataFrame(columns=["Category", "aggregated_at"])
    )

    """Merge scores and aggregated_at"""
    df = scores.merge(cats, on="Category", how="left")

    """Add company_id and NIST CSF identifiers columns"""
    df.insert(0, "company_id", int(selected_company_id))
    df.insert(
        2,
        "nist_csf_identifiers",
        df["Category"].map(
            lambda c: (summarize_csf_for_category(c) or {}).get("nist_csf_identifiers")
        ),
    )

    """Tidy up numeric columns"""
    if "category_score" in df.columns:
        df["category_score"] = (
            pd.to_numeric(df["category_score"], errors="coerce")
            .round(0)
            .astype("Int64")
        )
    if "category_gpa" in df.columns:
        df["category_gpa"] = pd.to_numeric(df["category_gpa"], errors="coerce")

    """Final column order"""
    df = df[
        [
            "company_id",
            "Category",
            "nist_csf_identifiers",
            "category_gpa",
            "category_score",
            "aggregated_at",
        ]
    ]
    """Return the DataFrame"""
    return df


# ---------- main render ----------


def render_company_tab(companies_payload, selected_company_id, company_domains):
    """Renders the 'Company' tab with KPIs, company details, domains, category scores, and category graph using Streamlit."""
    """Show KPI row (bundle-backed)"""
    agg = company_summary(selected_company_id)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Risk Grade", agg["grade"])
    c2.metric("Total GPA", agg["total_gpa"])
    c3.metric("Domains", len(company_domains))
    c4.metric("Last Calculated", agg["calculated_date"])

    """Show company details (single-row table)"""
    row = next(
        (
            c
            for c in companies_payload
            if str(c.get("company_id") or c.get("id")) == str(selected_company_id)
        ),
        {},
    )
    df1 = stringify_nested(to_df(row)) if row else pd.DataFrame()
    if df1.empty:
        st.info("No data.")
    else:
        st.dataframe(df1, use_container_width=True)  # show row index

    """Show company domains (exact shape like screenshot)"""
    with st.expander("Company Domains", expanded=True):
        if not company_domains:
            st.info("No domains.")
        else:
            dom_df = _domains_table(selected_company_id, company_domains)
            st.dataframe(dom_df, use_container_width=True)  # show row index

    """Show company category GPA & scores (exact shape like screenshot)"""
    with st.expander("Company Category GPA & Scores", expanded=True):
        if not selected_company_id:
            st.info("Select a company to view Category GPA.")
        else:
            cat_df = _category_scores_table(selected_company_id)
            if cat_df.empty:
                st.info("No Category GPA data available.")
            else:
                st.dataframe(cat_df, use_container_width=True)  # show row index
