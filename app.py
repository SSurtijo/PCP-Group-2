# app.py
# -----------------------------------------------------------------------------
# Streamlit entrypoint (runs the app). Tabs and routing live here.
# -----------------------------------------------------------------------------
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

# Refresh/build JSON bundles for all companies on run (existing behavior)
from json_handler import build_all_company_bundles, rebuild_company_bundle_for_id

build_all_company_bundles()  # overwrite data/{company_id}_data.json each run

st.set_page_config(page_title="Supplier Cyber Risk", layout="wide")

# Load Companies once (JSON-first)
try:
    companies_payload = companies()
except Exception as e:
    st.error(f"Failed to load companies: {e}")
    st.stop()

if not companies_payload:
    st.info("No companies available.")
    st.stop()


def show_dashboard(companies_payload):
    """Dashboard with Company / Domain / CSF tabs."""
    st.write("### Dashboard")

    # Company select
    options, mapping = list_company_options(companies_payload)
    selected_company_label = st.selectbox("Company", options, index=0)
    selected_company_id = mapping.get(selected_company_label)

    # 🔁 COMPANY-SPECIFIC REFRESH (UI-initiated from app.py, BEFORE any function uses company data)
    if selected_company_id is not None:
        try:
            rebuild_company_bundle_for_id(selected_company_id)
        except Exception as e:
            # Non-fatal: show a warning but continue with last known JSON
            st.warning(f"Could not refresh company {selected_company_id}: {e}")

    # Domains for this company (from JSON bundles)
    try:
        domains_payload = domains()
    except Exception as e:
        st.warning(f"Could not load domains: {e}")
        domains_payload = []
    company_domains = filter_domains_for_company(domains_payload, selected_company_id)

    # Domain items for UI
    domain_items = []
    for d in company_domains:
        did = d.get("domain_id") or d.get("id") or d.get("domainId")
        dname = (
            d.get("domain_name") or d.get("domain") or d.get("name") or f"domain-{did}"
        )
        domain_items.append({"_id": did, "_name": dname, "_raw": d})

    # Tabs
    tab_company, tab_domain, tab_nist = st.tabs(["Company", "Domain", "CSF"])
    with tab_company:
        render_company_tab(companies_payload, selected_company_id, company_domains)
    with tab_domain:
        render_domain_tab(domain_items)
    with tab_nist:
        render_nist_finding_tab(selected_company_id, company_domains)


# View Switch
view = st.sidebar.radio("Supplier Cyber Risk", ["Dashboard", "Companies"], index=0)
if view == "Companies":
    show_all_companies(companies_payload)
else:
    show_dashboard(companies_payload)
