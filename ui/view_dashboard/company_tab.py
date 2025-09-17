import streamlit as st
import pandas as pd

from helpers import (
    CATEGORY_NAMES,
    to_df,
    stringify_nested,
    get_company_category_scores_df,
)
from services import company_summary
from api import get_category_gpa
from charts.charts_company import company_category_scores_chart
from nist.nist_helpers import summarize_csf_for_category


def render_company_tab(companies_payload, selected_company_id, company_domains):
    """Render the 'Company' tab."""
    # KPI row
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
        st.dataframe(df1, use_container_width=True)

    # Domains table
    with st.expander("Company Domains", expanded=True):
        if not company_domains:
            st.info("No domains.")
        else:
            df_domains = stringify_nested(to_df(company_domains))
            if df_domains.empty:
                st.info("No domains.")
            else:
                st.dataframe(df_domains, use_container_width=True)

    # Category GPA
    with st.expander("Company Category GPA & Scores", expanded=True):
        if not selected_company_id:
            st.info("Select a company to view Category GPA.")
        else:
            rows, errors = [], []
            CANON = [
                "company_id",
                "Category",
                "category_gpa",
                "category_score",
                "aggregated_at",
            ]
            for cat in CATEGORY_NAMES:
                try:
                    payload = get_category_gpa(selected_company_id, cat)
                    df = to_df(payload)
                    if df is None or df.empty:
                        continue
                    if "category" in df.columns and "Category" not in df.columns:
                        df.rename(columns={"category": "Category"}, inplace=True)
                    if "Category" not in df.columns:
                        df.insert(0, "Category", cat)
                    if "company_id" not in df.columns:
                        df["company_id"] = selected_company_id
                    for col in CANON:
                        if col not in df.columns:
                            df[col] = pd.NA
                    df = df[CANON]
                    rows.append(df)
                except Exception as e:
                    errors.append((cat, str(e)))

            if rows:
                df_all = pd.concat(rows, ignore_index=True)
                if "category" in df_all.columns and "Category" in df_all.columns:
                    df_all.drop(columns=["category"], inplace=True, errors="ignore")
                if "Category" in df_all.columns and not df_all.empty:
                    nist_ids = df_all["Category"].apply(
                        lambda cat: summarize_csf_for_category(cat)[
                            "nist_csf_identifiers"
                        ]
                    )
                    df_all.insert(
                        df_all.columns.get_loc("Category") + 1,
                        "nist_csf_identifiers",
                        nist_ids,
                    )
                st.dataframe(stringify_nested(df_all), use_container_width=True)
            else:
                st.info("No Category GPA data available.")
            if errors:
                with st.expander("Categories with errors", expanded=False):
                    for cat, msg in errors:
                        st.write(f"- {cat}: {msg}")

    # Category Graph
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
