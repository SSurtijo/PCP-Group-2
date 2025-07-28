import streamlit as st
import pandas as pd
from charts import (
    altair_distribution_chart,
    altair_control_maturity_chart,
    altair_individual_risk_chart,
)
from utils import load_past_scans

# ------------------------------
# Streamlit App
# ------------------------------
st.set_page_config(page_title="Cybersecurity Risk Dashboard", layout="wide")
past_scans = load_past_scans()
past_domains = ["-- New Domain --"] + [item["domain"] for item in past_scans]
page = st.sidebar.radio("Navigation", ["Domain Input", "Past Scans"])

# ------------------------------
# Domain Input Page
# ------------------------------
if page == "Domain Input":
    st.subheader("Enter Domain or IP")
    selected = st.selectbox("Select Past Domain or Enter New:", past_domains)
    domain = (
        st.text_input("Domain/IP", placeholder="e.g., example.com")
        if selected == "-- New Domain --"
        else selected
    )

    if st.button("Run Scan"):
        if not domain:
            st.warning("Please enter or select a domain.")
        else:
            scan = next((item for item in past_scans if item["domain"] == domain), None)
            if scan:
                st.success(
                    f"Showing saved scan for {domain} (Last Scan: {scan['last_scan']})"
                )
                df = pd.DataFrame(scan["results"])
                df.insert(0, "No.", range(1, len(df) + 1))

                with st.expander("Risks table", expanded=True):
                    st.table(df.set_index("No."))

                # Analytics
                with st.expander(
                    "Analytics Overview (Click to Expand/Collapse)", expanded=True
                ):
                    with st.expander(
                        "Distribution of Risk Findings (NIST Functions)", expanded=True
                    ):
                        st.altair_chart(
                            altair_distribution_chart(df), use_container_width=True
                        )
                    with st.expander(
                        "Individual Risk Graph (0 = good, 100 = bad)", expanded=True
                    ):
                        st.altair_chart(
                            altair_individual_risk_chart(
                                df.sort_values(by="Score", ascending=False)
                            ),
                            use_container_width=True,
                        )
                    with st.expander(
                        "Control Maturity Graph (0 = good, 100 = bad)", expanded=True
                    ):
                        st.altair_chart(
                            altair_control_maturity_chart(df), use_container_width=True
                        )
            else:
                st.warning(f"No previous scan found for {domain}.")

# ------------------------------
# Past Scans Page
# ------------------------------
elif page == "Past Scans":
    st.title("Past Scan Results")
    if past_scans:
        for scan in past_scans:
            st.write(f"**Domain:** {scan['domain']} | Last Scan: {scan['last_scan']}")
            df_past = pd.DataFrame(scan["results"])
            df_past.insert(0, "No.", range(1, len(df_past) + 1))
            st.dataframe(df_past.set_index("No."))
    else:
        st.warning("No past scans found.")
