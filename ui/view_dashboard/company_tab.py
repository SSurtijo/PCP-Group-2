# company_tab.py — drop-in (row numbers visible)
import streamlit as st
import pandas as pd

from helpers import (
    to_df,
    stringify_nested,
    get_company_category_scores_df,
)
from services import company_summary
from charts.charts_company import company_category_scores_chart
from nist.nist_helpers import summarize_csf_for_category
from json_handler import load_company_bundle


# ---------- helpers to shape tables like the screenshot ----------


def _domains_table(
    selected_company_id: int, company_domains: list[dict]
) -> pd.DataFrame:
    """
    Build: domain_id | company_id | domain_name | source | first_seen | last_seen
    Derives first/last_seen from nested findings_by_category dates if present.
    """
    rows = []
    for d in company_domains or []:
        did = d.get("domain_id") or d.get("id") or d.get("domainId")
        name = d.get("domain_name") or d.get("domain") or d.get("name")

        # derive first/last seen from nested findings dates
        fbc = d.get("findings_by_category") or {}
        dates = []
        for lst in fbc.values():
            for r in lst or []:
                dt = r.get("found_date") or r.get("date") or r.get("scan_date")
                if dt:
                    dates.append(str(dt))
        first_seen = min(dates) if dates else None
        last_seen = max(dates) if dates else None

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
    """
    Build: company_id | Category | nist_csf_identifiers | category_gpa | category_score | aggregated_at
    Pulls GPA/score from helpers, aggregated_at from bundle, adds NIST IDs.
    """
    scores = get_company_category_scores_df(selected_company_id)
    if scores is None or scores.empty:
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

    # bring aggregated_at from bundle
    bundle = load_company_bundle(selected_company_id) or {}
    cats = pd.DataFrame(bundle.get("categories") or [])
    cats = (
        cats[["Category", "aggregated_at"]]
        if not cats.empty
        else pd.DataFrame(columns=["Category", "aggregated_at"])
    )

    df = scores.merge(cats, on="Category", how="left")

    # add columns to match screenshot
    df.insert(0, "company_id", int(selected_company_id))
    df.insert(
        2,
        "nist_csf_identifiers",
        df["Category"].map(
            lambda c: (summarize_csf_for_category(c) or {}).get("nist_csf_identifiers")
        ),
    )

    # tidy numerics
    if "category_score" in df.columns:
        df["category_score"] = (
            pd.to_numeric(df["category_score"], errors="coerce")
            .round(0)
            .astype("Int64")
        )
    if "category_gpa" in df.columns:
        df["category_gpa"] = pd.to_numeric(df["category_gpa"], errors="coerce")

    # final column order
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
    return df


# ---------- main render ----------


def render_company_tab(companies_payload, selected_company_id, company_domains):
    """Render the 'Company' tab."""

    # KPI row (bundle-backed)
    agg = company_summary(selected_company_id)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Risk Grade", agg["grade"])
    c2.metric("Total GPA", agg["total_gpa"])
    c3.metric("Domains", len(company_domains))
    c4.metric("Last Calculated", agg["calculated_date"])

    # Company details (single-row table)
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

    # ---- Company Domains (exact shape like screenshot) ----
    with st.expander("Company Domains", expanded=True):
        if not company_domains:
            st.info("No domains.")
        else:
            dom_df = _domains_table(selected_company_id, company_domains)
            st.dataframe(dom_df, use_container_width=True)  # show row index

    # ---- Company Category GPA & Scores (exact shape like screenshot) ----
    with st.expander("Company Category GPA & Scores", expanded=True):
        if not selected_company_id:
            st.info("Select a company to view Category GPA.")
        else:
            cat_df = _category_scores_table(selected_company_id)
            if cat_df.empty:
                st.info("No Category GPA data available.")
            else:
                st.dataframe(cat_df, use_container_width=True)  # show row index

    # Category Graph (unchanged)
    with st.expander("Category Graph", expanded=True):
        sort_label = st.selectbox(
            "Sort by",
            ["A → Z (Category)", "Score: High → Low", "Score: Low → High"],
            index=1,
            key="category_graph_sort",
        )
        sort_mode = {
            "A → Z (Category)": "category_asc",
            "Score: High → Low": "score_desc",
            "Score: Low → High": "score_asc",
        }[sort_label]

        scores_df = get_company_category_scores_df(selected_company_id)
        chart = company_category_scores_chart(
            scores_df,
            height_per_bar=80,
            bar_size=45,
            label_padding=30,
            sort_mode=sort_mode,
        )
        if chart is None:
            st.info("No category scores available.")
        else:
            st.altair_chart(chart, use_container_width=True)
