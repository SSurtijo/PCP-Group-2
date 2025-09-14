import streamlit as st
import pandas as pd

from services import domain_overview
from api import get_internal_scan
from helpers import to_df
from charts import csf_function_distribution_chart


def render_nist_finding_tab(selected_company_id, company_domains):
    """Render the 'NIST Findings' tab with the Function Distribution chart."""
    st.caption(
        "Distribution of findings by NIST CSF functions (GV / ID / PR / DE / RS / RC)."
    )

    # Gather all findings across this company's domains
    all_findings = []
    for d in company_domains:
        did = d.get("domain_id") or d.get("id") or d.get("domainId")
        try:
            _, findings = domain_overview(did)
            if isinstance(findings, list):
                all_findings.extend(findings)
        except Exception:
            pass

    df_findings = pd.DataFrame(all_findings)

    # Internal GV findings (optional overlay)
    df_gv = pd.DataFrame()
    try:
        raw = get_internal_scan(limit=200)
        df_int = to_df(raw)
        if not df_int.empty and "control_ref" in df_int.columns:
            mask = df_int["control_ref"].astype(str).str.upper().str.startswith("GV.")
            df_gv = df_int[mask].copy()
            if "company_id" in df_gv.columns and selected_company_id is not None:
                df_gv = df_gv[
                    df_gv["company_id"].astype(str) == str(selected_company_id)
                ]
    except Exception:
        pass

    chart = csf_function_distribution_chart(df_findings, internal_gv_df=df_gv)
    st.altair_chart(chart, use_container_width=True)
