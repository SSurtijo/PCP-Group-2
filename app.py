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
from ui.view_dashboard.nist_finding_tab import render_nist_finding_tab  # remains

st.set_page_config(page_title="Supplier Cyber Risk", layout="wide")

# Load Companies once
try:
    companies_payload = companies()
except Exception as e:
    st.error(f"Failed to load companies: {e}")
    st.stop()

if not companies_payload:
    st.info("No companies available.")
    st.stop()


# ------------------- VIEW 2: Dashboard -------------------
def show_dashboard(companies_payload):
    """Dashboard with Company / Domain / NIST Findings tabs."""
    st.write("### Dashboard")

    # Company select
    options, mapping = list_company_options(companies_payload)
    selected_company_label = st.selectbox("Company", options, index=0)
    selected_company_id = mapping.get(selected_company_label)

    # Domains for this company
    try:
        domains_payload = domains()
    except Exception as e:
        st.warning(f"Could not fetch domains: {e}")
        domains_payload = []
    company_domains = filter_domains_for_company(domains_payload, selected_company_id)

    # For Domain tab dropdown
    domain_items = []
    for d in company_domains:
        did = d.get("domain_id") or d.get("id") or d.get("domainId")
        dname = (
            d.get("domain_name") or d.get("domain") or d.get("name") or f"domain-{did}"
        )
        domain_items.append({"_id": did, "_name": dname, "_raw": d})

    # Tabs (IP tab removed)
    tab_company, tab_domain, tab_nist = st.tabs(["Company", "Domain", "NIST Findings"])
    with tab_company:
        render_company_tab(companies_payload, selected_company_id, company_domains)
    with tab_domain:
        render_domain_tab(domain_items)
    with tab_nist:
        render_nist_finding_tab(selected_company_id, company_domains)


# ------------------- View Switch -------------------
view = st.sidebar.radio("Supplier Cyber Risk", ["Dashboard", "Companies"], index=0)
if view == "Companies":
    show_all_companies(companies_payload)
else:
    show_dashboard(companies_payload)
