###
# File: app.py
# Description: Streamlit entrypoint for PCP project. Handles tab routing and dashboard logic.
###
import streamlit as st

from services import (
    companies,
    domains,
    filter_domains_for_company,
    list_company_options,
)
from ui.view_companies import show_all_companies
from ui.view_dashboard.company_tab import render_company_tab
from ui.view_dashboard.domain_tab import render_domain_tab
from ui.view_dashboard.nist_finding_tab import render_nist_finding_tab

from json_handler import build_all_company_bundles, rebuild_company_bundle_for_id

build_all_company_bundles()  # overwrite data/{company_id}_data.json each run

st.set_page_config(page_title="Supplier Cyber Risk", layout="wide")

try:
    companies_payload = companies()
except Exception as e:
    st.error(f"Failed to load companies: {e}")
    st.stop()
if not companies_payload:
    st.info("No companies available.")
    st.stop()


def show_dashboard(companies_payload):
    # Function: show_dashboard
    # Description: Renders the main dashboard with company selection and tabs.
    # Usage: show_dashboard(companies_payload)
    # Returns: None (renders dashboard UI)
    st.write("### Dashboard")
    # Get company options and mapping
    options, mapping = list_company_options(companies_payload)
    selected_company_label = st.selectbox("Company", options, index=0)
    selected_company_id = mapping.get(selected_company_label)
    # Refresh selected company's JSON when selected
    rebuild_company_bundle_for_id(selected_company_id)
    try:
        # Load domains payload
        domains_payload = domains()
    except Exception as e:
        st.warning(f"Could not load domains: {e}")
        domains_payload = []
    # Filter domains for selected company
    company_domains = filter_domains_for_company(domains_payload, selected_company_id)
    domain_items = []
    for d in company_domains:
        did = d.get("domain_id") or d.get("id") or d.get("domainId")
        dname = (
            d.get("domain_name") or d.get("domain") or d.get("name") or f"domain-{did}"
        )
        domain_items.append({"_id": did, "_name": dname, "_raw": d})
    # Create dashboard tabs
    tab_company, tab_domain, tab_nist = st.tabs(["Company", "Domain", "CSF"])
    with tab_company:
        render_company_tab(companies_payload, selected_company_id, company_domains)
    with tab_domain:
        """Render domain tab"""
        render_domain_tab(domain_items)
    with tab_nist:
        """Render NIST finding tab"""
        render_nist_finding_tab(selected_company_id, company_domains)


# Sidebar navigation for dashboard/companies
view = st.sidebar.radio("Supplier Cyber Risk", ["Dashboard", "Companies"], index=0)
if view == "Companies":
    build_all_company_bundles()
    show_all_companies(companies_payload)
else:
    build_all_company_bundles()
    show_dashboard(companies_payload)
