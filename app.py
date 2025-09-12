# app.py
# -----------------------------------------------------------------------------
# Dashboard (Streamlit UI)
# -----------------------------------------------------------------------------

import streamlit as st
import pandas as pd

# Helpers
from helpers import (
    CATEGORY_NAMES,
    to_df,
    stringify_nested,
    summarize_csf_for_category,
    get_company_category_scores_df,
)

# Service-layer functions
from services import (
    companies,
    domains,
    list_company_options,
    filter_domains_for_company,
    company_summary,
    domain_overview,
    get_domain_filter_options_original,
    filter_domain_findings_original,
)

# Direct API calls
from api import get_category_gpa

# Charts
from charts import csf_function_distribution_chart, company_category_scores_chart


st.set_page_config(page_title="Supplier Cyber Risk", layout="wide")

# Load Companies
try:
    companies_payload = companies()
except Exception as e:
    st.error(f"Failed to load companies: {e}")
    st.stop()

if not companies_payload:
    st.info("No companies available.")
    st.stop()


# ------------------- VIEW 1: Companies -------------------
def show_all_companies(companies_payload):
    st.subheader("Companies")
    st.metric("Total Companies", len(companies_payload))
    df_all = stringify_nested(to_df(companies_payload))
    if not df_all.empty:
        st.dataframe(df_all, use_container_width=True)
    else:
        st.info("No data.")


# ------------------- VIEW 2: Dashboard -------------------
def show_dashboard(companies_payload):
    st.write("### Dashboard")
    # Company select dropdown (moved from sidebar to main content)
    options, mapping = list_company_options(companies_payload)
    selected_company_label = st.selectbox("Company", options, index=0)
    selected_company_id = mapping.get(selected_company_label)

    # Domains for the company
    try:
        domains_payload = domains()
    except Exception as e:
        st.warning(f"Could not fetch domains: {e}")
        domains_payload = []
    company_domains = filter_domains_for_company(domains_payload, selected_company_id)

    domain_items = []
    for d in company_domains:
        did = d.get("domain_id") or d.get("id") or d.get("domainId")
        dname = (
            d.get("domain_name") or d.get("domain") or d.get("name") or f"domain-{did}"
        )
        domain_items.append({"_id": did, "_name": dname, "_raw": d})

    tab_company, tab_domain = st.tabs(["Company", "Domain"])

    # ------------------- Company Tab -------------------
    with tab_company:

        agg = company_summary(selected_company_id)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Risk Grade", agg["grade"])
        c2.metric("Total GPA", agg["total_gpa"])
        c3.metric("Domains", len(company_domains))
        c4.metric("Last Calculated", agg["calculated_date"])

        # --- Company details ---
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

        # --- Domains table ---
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
                        csf_controls = df_all["Category"].apply(
                            lambda cat: summarize_csf_for_category(cat)["csf_controls"]
                        )
                        df_all.insert(
                            df_all.columns.get_loc("Category") + 1,
                            "csf_controls",
                            csf_controls,
                        )
                    st.dataframe(stringify_nested(df_all), use_container_width=True)
                else:
                    st.info("No Category GPA data available.")
                if errors:
                    with st.expander("Categories with errors", expanded=False):
                        for cat, msg in errors:
                            st.write(f"- {cat}: {msg}")

        # Internal GV findings
        with st.expander("Company Internal Finding", expanded=True):
            from api import get_internal_scan

            try:
                raw = get_internal_scan(limit=200)
                df = to_df(raw)
                if df.empty:
                    st.info("No internal findings available.")
                else:
                    mask = (
                        df["control_ref"].astype(str).str.upper().str.startswith("GV.")
                        if "control_ref" in df.columns
                        else []
                    )
                    df_gv = df[mask].copy() if mask is not None else df.iloc[0:0].copy()
                    if df_gv.empty:
                        st.info("No GV findings in Internal Scan for this company.")
                    else:
                        if "cmm_rating" in df_gv.columns:
                            MAX_CMM = 5.0
                            df_gv["cmm_score"] = (
                                df_gv["cmm_rating"]
                                .apply(
                                    lambda x: (
                                        (float(x) / MAX_CMM) * 100
                                        if x is not None
                                        else None
                                    )
                                )
                                .round(1)
                            )
                        preferred = [
                            "company_id",
                            "domain",
                            "control_ref",
                            "cmm_score",
                            "note",
                        ]
                        cols = [c for c in preferred if c in df_gv.columns] or list(
                            df_gv.columns
                        )
                        st.dataframe(
                            stringify_nested(df_gv[cols]), use_container_width=True
                        )
            except Exception as e:
                st.warning(f"Unable to load internal scan (GV): {e}")

        # Function distribution
        with st.expander("NIST CSF Function Distribution (percent)", expanded=True):
            try:
                all_findings = []
                for d in company_domains:
                    did = d.get("domain_id") or d.get("id") or d.get("domainId")
                    try:
                        _, f = domain_overview(did)
                        if isinstance(f, list):
                            all_findings.extend(f)
                    except Exception:
                        pass
                df_findings = pd.DataFrame(all_findings)

                from api import get_internal_scan

                df_gv = pd.DataFrame()
                try:
                    raw = get_internal_scan(limit=200)
                    df_int = to_df(raw)
                    if not df_int.empty and "control_ref" in df_int.columns:
                        mask = (
                            df_int["control_ref"]
                            .astype(str)
                            .str.upper()
                            .str.startswith("GV.")
                        )
                        df_gv = df_int[mask].copy()
                        if (
                            "company_id" in df_gv.columns
                            and selected_company_id is not None
                        ):
                            df_gv = df_gv[
                                df_gv["company_id"].astype(str)
                                == str(selected_company_id)
                            ]
                except Exception:
                    pass

                chart = csf_function_distribution_chart(
                    df_findings, internal_gv_df=df_gv
                )
                st.altair_chart(chart, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not build function distribution: {e}")

        with st.expander("Risk Graph", expanded=True):
            scores_df = get_company_category_scores_df(selected_company_id)
            chart = company_category_scores_chart(
                scores_df,
                height_per_bar=80,  # more vertical space per row
                bar_size=45,  # thicker bars
                label_padding=30,  # extra spacing for long category names
            )
            if chart is None:
                st.info("No category scores available.")
            else:
                st.altair_chart(chart, use_container_width=True)

    # ------------------- Domain Tab -------------------
    with tab_domain:
        if not domain_items:
            st.info("This company has no domains.")
        else:
            selected_domain = st.selectbox(
                "Domain",
                domain_items,
                index=0,
                key="domain_select",
                format_func=lambda x: f"{x['_id']} — {x['_name']}",
            )
            try:
                domain_score, findings = domain_overview(selected_domain["_id"])
            except Exception as e:
                st.error(f"Failed to load domain overview: {e}")
                domain_score, findings = None, []

            c1, c2 = st.columns(2)
            c1.metric("Score", f"{(domain_score or 0):.2f}")
            c2.metric("Total Finding", f"{len(findings)}")

            opts, orig_cols = get_domain_filter_options_original(findings)
            with st.expander("Filters", expanded=False):
                f1, f2, f3 = st.columns(3)
                ip_opt = f1.selectbox("IP", ["All"] + opts["ips"], index=0)
                type_opt = f2.selectbox("Type", ["All"] + opts["types"], index=0)
                level_opt = f3.selectbox(
                    "Severity level", ["All"] + opts["levels"], index=0
                )

                with st.container(border=True):
                    st.caption("Date range")
                    d1, d2 = st.columns(2)
                    from_opt = d1.selectbox("From", ["Any"] + opts["dates"], index=0)
                    to_opt = d2.selectbox("To", ["Any"] + opts["dates"], index=0)

                fdf = filter_domain_findings_original(
                    findings,
                    ip=ip_opt,
                    ftype=type_opt,
                    level=level_opt,
                    start_date=from_opt,
                    end_date=to_opt,
                )
                if (
                    from_opt != "Any"
                    and to_opt != "Any"
                    and pd.to_datetime(from_opt, errors="coerce")
                    > pd.to_datetime(to_opt, errors="coerce")
                ):
                    st.warning(
                        "'From' date is later than 'To' date — no rows may match."
                    )
                st.caption(f"Filtered findings: {len(fdf)}")

            if not fdf.empty:
                st.dataframe(fdf[orig_cols], use_container_width=True)
            else:
                st.info("No findings match filters.")


# ------------------- View Switch -------------------
view = st.sidebar.radio("Supplier Cyber Risk", ["Dashboard", "Companies"], index=0)
if view == "Companies":
    show_all_companies(companies_payload)
else:
    show_dashboard(companies_payload)
