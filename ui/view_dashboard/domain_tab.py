# ui/view_dashboard/domain_tab.py
import streamlit as st
import pandas as pd

from services import (
    domain_overview,
    get_domain_filter_options_original,
    filter_domain_findings_original,
)


def render_domain_tab(domain_items):
    """Render the 'Domain' tab (metrics + filters/table)."""
    if not domain_items:
        st.info("This company has no domains.")
        return

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

    # Filters + table (original UX)
    opts, orig_cols = get_domain_filter_options_original(findings)
    with st.expander("Filters", expanded=True):
        f1, f2, f3 = st.columns(3)
        ip_opt = f1.selectbox("IP", ["All"] + opts["ips"], index=0)
        type_opt = f2.selectbox("Type", ["All"] + opts["types"], index=0)
        level_opt = f3.selectbox("Severity level", ["All"] + opts["levels"], index=0)

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
            st.warning("'From' date is after 'To' date — showing unfiltered results.")
            fdf = findings

        df = pd.DataFrame(fdf)
        if not df.empty:
            front = [c for c in orig_cols if c in df.columns]
            rest = [c for c in df.columns if c not in front]
            df = df[front + rest]
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No findings match the selected filters.")
