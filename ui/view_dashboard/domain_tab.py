###
# File: ui/view_dashboard/domain_tab.py
# Description: Renders the Domain tab for PCP project dashboard UI.
###

import streamlit as st
from json_handler import rebuild_company_bundle_for_id
import pandas as pd
from utils.dataframe_utils import domain_overview
from services import get_domain_filter_options_original, filter_domain_findings_original
from charts.domain_scatter_chart import (
    domain_security_scatter_chart,
    timeline_findings_chart,
)


# Renders the 'Domain' tab with metrics, charts, filters, and findings table using Streamlit.
# Usage: app.py (Domain tab)
# Inputs: domain_items (list of domain dicts)
# Outputs: None (renders tab in UI)
def render_domain_tab(domain_items):
    """Renders the 'Domain' tab with metrics, charts, filters, and findings table using Streamlit."""
    """Check if domain_items is empty"""
    if not domain_items:
        st.info("This company has no domains.")
        return

    """Add scatter chart analysis section - showing ALL domains"""
    with st.expander("Domain Security Analysis Charts", expanded=True):
        chart_tabs = st.tabs(["Security Score Distribution", "Timeline Trends"])

        """Security Score Distribution tab"""
        with chart_tabs[0]:
            st.subheader("Domain Security Score Scatter Plot")
            try:
                selected_company_id = (
                    domain_items[0]["_raw"].get("company_id") if domain_items else None
                )
                scatter_chart = domain_security_scatter_chart(selected_company_id)
                if scatter_chart:
                    st.altair_chart(scatter_chart, use_container_width=True)
                else:
                    st.info("No scatter plot data available")
            except Exception as e:
                st.error(f"Failed to generate scatter plot: {e}")

        """Timeline Trends tab"""
        with chart_tabs[1]:
            st.subheader("Findings Discovery Timeline")
            try:
                selected_company_id = (
                    domain_items[0]["_raw"].get("company_id") if domain_items else None
                )
                timeline_chart = timeline_findings_chart(selected_company_id)
                if timeline_chart:
                    st.altair_chart(timeline_chart, use_container_width=True)
                else:
                    st.info("No timeline data available")
            except Exception as e:
                st.error(f"Failed to generate timeline chart: {e}")

    """Select domain from dropdown"""
    selected_domain = st.selectbox(
        "Domain",
        domain_items,
        index=0,
        key="domain_select",
        format_func=lambda x: f"{x['_id']} — {x['_name']}",
    )
    """Refresh selected company's JSON when domain is selected"""
    selected_company_id = (
        selected_domain["_raw"].get("company_id") if selected_domain else None
    )
    if selected_company_id:
        rebuild_company_bundle_for_id(selected_company_id)

    """Try to get domain score and findings"""
    try:
        domain_score, findings = domain_overview(selected_domain["_id"])
    except Exception as e:
        st.error(f"Failed to load domain overview: {e}")
        domain_score, findings = None, []

    """Show metrics for selected domain"""
    c1, c2 = st.columns(2)
    c1.metric("Score", f"{(domain_score or 0):.2f}")
    c2.metric("Total Finding", f"{len(findings)}")

    """Filters + table (original UX)"""
    opts, orig_cols = get_domain_filter_options_original(findings)
    with st.expander("Filters", expanded=True):
        """Filter columns"""
        f1, f2, f3 = st.columns(3)
        ip_opt = f1.selectbox("IP", ["All"] + opts["ips"], index=0)
        type_opt = f2.selectbox("Type", ["All"] + opts["types"], index=0)
        level_opt = f3.selectbox("Severity level", ["All"] + opts["levels"], index=0)

        """Date range filter"""
        with st.container(border=True):
            st.caption("Date range")
            d1, d2 = st.columns(2)
            from_opt = d1.selectbox("From", ["Any"] + opts["dates"], index=0)
            to_opt = d2.selectbox("To", ["Any"] + opts["dates"], index=0)

        """Filter findings based on selected options"""
        fdf = filter_domain_findings_original(
            findings,
            ip=ip_opt,
            ftype=type_opt,
            level=level_opt,
            start_date=from_opt,
            end_date=to_opt,
        )
        """Check if date range is valid"""
        if (
            from_opt != "Any"
            and to_opt != "Any"
            and pd.to_datetime(from_opt, errors="coerce")
            > pd.to_datetime(to_opt, errors="coerce")
        ):
            st.warning("'From' date is after 'To' date — showing unfiltered results.")
            fdf = findings

        """Prepare DataFrame for display"""
        df = pd.DataFrame(fdf)
        if not df.empty:
            front = [c for c in orig_cols if c in df.columns]
            rest = [c for c in df.columns if c not in front]
            df = df[front + rest]
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No findings match the selected filters.")
