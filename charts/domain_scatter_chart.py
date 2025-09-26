###
# File: charts/domain_scatter_chart.py
# Description: Altair chart builders for domain-level security and findings scatter plots. Used in dashboard visualizations.
###
import altair as alt
import pandas as pd
from json_handler import load_company_bundle


def domain_security_scatter_chart(selected_company_id: int) -> alt.Chart:
    """Load company bundle and extract domains."""
    b = load_company_bundle(selected_company_id) or {}
    domains = b.get("domains") or []
    """Build chart data: domain name, score, findings count."""
    chart_data = []
    for domain in domains:
        domain_id = domain.get("domain_id") or domain.get("id")
        domain_name = (
            domain.get("domain_name") or domain.get("domain") or f"domain-{domain_id}"
        )
        score = domain.get("domain_score")
        try:
            score = float(score) if score is not None else 0
        except Exception:
            score = 0
        findings_count = 0
        fbc = domain.get("findings_by_category") or {}
        for _, rows in fbc.items():
            findings_count += len(rows or [])
        chart_data.append(
            {
                "domain_name": domain_name,
                "domain_score": score,
                "findings_count": findings_count,
            }
        )
    """Return None if no chart data."""
    if not chart_data:
        return None
    """Create scatter plot: x=domain score, y=findings count, tooltip for details."""
    df = pd.DataFrame(chart_data)
    chart = (
        alt.Chart(df)
        .mark_circle(opacity=0.7, size=100)
        .encode(
            x=alt.X("domain_score:Q", title="Domain Security Score"),
            y=alt.Y("findings_count:Q", title="Number of Findings"),
            tooltip=[
                alt.Tooltip("domain_name:N", title="Domain"),
                alt.Tooltip("domain_score:Q", format=".2f", title="Security Score"),
                alt.Tooltip("findings_count:Q", title="Findings Count"),
            ],
        )
        .properties(width=600, height=400, title="Domain Security Score Distribution")
        .configure_axis(
            labelColor="#666666",
            titleColor="#666666",
            gridColor="#3a3a3a",
            gridOpacity=0.3,
        )
        .configure_title(color="#444444", fontSize=16)
        .configure_legend(labelColor="#666666", titleColor="#666666")
    )
    """Return Altair chart object."""
    return chart


def ip_findings_scatter_chart(domains_data: list):
    """Handle empty input list."""
    if not domains_data:
        return None
    """Build chart data: extract findings and encode IPs numerically."""
    chart_data = []
    for domain in domains_data:
        domain_id = domain.get("domain_id") or domain.get("id")
        domain_name = (
            domain.get("domain_name") or domain.get("domain") or f"domain-{domain_id}"
        )
        findings = domain.get("findings", [])
        for finding in findings:
            ip_address = finding.get("ip_address", "")
            finding_score = finding.get("finding_score", 0)
            finding_type = finding.get("finding_type", "Unknown")
            severity_level = finding.get("severity_level", 0)
            if ip_address:
                ip_parts = ip_address.split(".")
                try:
                    ip_numeric = sum(
                        int(part) * (256 ** (3 - i)) for i, part in enumerate(ip_parts)
                    )
                except:
                    ip_numeric = hash(ip_address) % 1000000
            else:
                ip_numeric = 0
            chart_data.append(
                {
                    "domain_name": domain_name,
                    "ip_address": ip_address,
                    "ip_numeric": ip_numeric,
                    "finding_score": float(finding_score),
                    "finding_type": finding_type,
                    "severity_level": int(severity_level),
                }
            )
    """Return None if no chart data."""
    if not chart_data:
        return None
    """Create scatter plot: x=IP numeric, y=finding score, color by type, tooltip for details."""
    df = pd.DataFrame(chart_data)
    chart = (
        alt.Chart(df)
        .mark_circle(opacity=0.6, size=60)
        .encode(
            x=alt.X(
                "ip_numeric:Q",
                title="IP Address (Numeric)",
                axis=alt.Axis(format=".0f"),
            ),
            y=alt.Y("finding_score:Q", title="Finding Score"),
            color=alt.Color("finding_type:N", title="Finding Type"),
            tooltip=[
                alt.Tooltip("domain_name:N", title="Domain"),
                alt.Tooltip("ip_address:N", title="IP Address"),
                alt.Tooltip("finding_score:Q", format=".2f", title="Finding Score"),
                alt.Tooltip("finding_type:N", title="Finding Type"),
                alt.Tooltip("severity_level:O", title="Severity Level"),
            ],
        )
        .properties(width=600, height=400, title="IP Address Findings Distribution")
        .configure_axis(
            labelColor="#666666",
            titleColor="#666666",
            gridColor="#3a3a3a",
            gridOpacity=0.3,
        )
        .configure_title(color="#444444", fontSize=16)
        .configure_legend(labelColor="#666666", titleColor="#666666")
    )
    """Return Altair chart object."""
    return chart


def timeline_findings_chart(selected_company_id: int) -> alt.Chart:
    """Load company bundle and extract domains."""
    b = load_company_bundle(selected_company_id) or {}
    domains = b.get("domains") or []
    """Build chart data: extract findings with dates, scores, and types."""
    chart_data = []
    for domain in domains:
        domain_id = domain.get("domain_id") or domain.get("id")
        domain_name = (
            domain.get("domain_name") or domain.get("domain") or f"domain-{domain_id}"
        )
        fbc = domain.get("findings_by_category") or {}
        for _, findings in fbc.items():
            for finding in findings or []:
                found_date = finding.get("found_date", "")
                finding_score = finding.get("finding_score", 0)
                finding_type = finding.get("finding_type", "Unknown")
                ip_address = finding.get("ip_address", "Unknown IP")
                if found_date:
                    chart_data.append(
                        {
                            "domain_name": domain_name,
                            "ip_address": ip_address,
                            "found_date": found_date,
                            "finding_score": float(finding_score),
                            "finding_type": finding_type,
                        }
                    )
    """Return None if no chart data."""
    if not chart_data:
        return None
    """Create scatter plot: x=found date, y=finding score, color by type, tooltip for details."""
    df = pd.DataFrame(chart_data)
    df["found_date"] = pd.to_datetime(df["found_date"], errors="coerce")
    df = df.dropna(subset=["found_date"])
    chart = (
        alt.Chart(df)
        .mark_circle(opacity=0.7, size=80)
        .encode(
            x=alt.X("found_date:T", title="Found Date"),
            y=alt.Y("finding_score:Q", title="Finding Score"),
            color=alt.Color("finding_type:N", title="Finding Type"),
            tooltip=[
                alt.Tooltip("domain_name:N", title="Domain"),
                alt.Tooltip("ip_address:N", title="IP Address"),
                alt.Tooltip("found_date:T", title="Found Date"),
                alt.Tooltip("finding_score:Q", format=".2f", title="Finding Score"),
                alt.Tooltip("finding_type:N", title="Finding Type"),
            ],
        )
        .properties(width=600, height=400, title="Findings Discovery Timeline")
        .configure_axis(
            labelColor="#666666",
            titleColor="#666666",
            gridColor="#3a3a3a",
            gridOpacity=0.3,
        )
        .configure_title(color="#444444", fontSize=16)
        .configure_legend(labelColor="#666666", titleColor="#666666")
    )
    """Return Altair chart object."""
    return chart
