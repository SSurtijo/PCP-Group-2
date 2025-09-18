# domain_scatter_chart.py
import altair as alt
import pandas as pd
import datetime


def domain_security_scatter_chart(domains_data: list, findings_data: dict = None):
    """
    Domain Security Score Scatter Plot
    X-axis: Domain security score (domain_score)
    Y-axis: Number of findings (findings_count)
    Color: Average severity level
    Size: Activity (days since last_seen)
    """
    if not domains_data:
        return None

    # Prepare data
    chart_data = []

    for domain in domains_data:
        domain_id = domain.get("domain_id") or domain.get("id")
        domain_name = domain.get("domain_name") or domain.get("domain") or f"domain-{domain_id}"
        last_seen = domain.get("last_seen", "")

        # Get domain score and findings
        from services import domain_overview
        try:
            score, findings = domain_overview(domain_id)
            if score is None:
                score = 0

            findings_count = len(findings)

            chart_data.append({
                "domain_name": domain_name,
                "domain_score": float(score),
                "findings_count": findings_count
            })

        except Exception:
            # If fetch fails, use default values
            chart_data.append({
                "domain_name": domain_name,
                "domain_score": 0,
                "findings_count": 0
            })

    if not chart_data:
        return None

    df = pd.DataFrame(chart_data)

    # Create scatter plot
    chart = (
        alt.Chart(df)
        .mark_circle(opacity=0.7, size=100)
        .encode(
            x=alt.X(
                "domain_score:Q",
                title="Domain Security Score"
            ),
            y=alt.Y(
                "findings_count:Q",
                title="Number of Findings"
            ),
            tooltip=[
                alt.Tooltip("domain_name:N", title="Domain"),
                alt.Tooltip("domain_score:Q", format=".2f", title="Security Score"),
                alt.Tooltip("findings_count:Q", title="Findings Count"),
            ],
        )
        .properties(
            width=600,
            height=400,
            title="Domain Security Score Distribution"
        )
        .configure_axis(labelColor="#666666", titleColor="#666666", gridColor="#3a3a3a", gridOpacity=0.3)
        .configure_title(color="#444444", fontSize=16)
        .configure_legend(labelColor="#666666", titleColor="#666666")
    )

    return chart


def ip_findings_scatter_chart(domains_data: list):
    """
    IP Address Findings Scatter Plot
    X-axis: IP address (numeric)
    Y-axis: Finding score (finding_score)
    Color: Finding type
    """
    if not domains_data:
        return None

    chart_data = []

    for domain in domains_data:
        domain_id = domain.get("domain_id") or domain.get("id")
        domain_name = domain.get("domain_name") or domain.get("domain") or f"domain-{domain_id}"

        from services import domain_overview
        try:
            _, findings = domain_overview(domain_id)

            for finding in findings:
                ip_address = finding.get("ip_address", "")
                finding_score = finding.get("finding_score", 0)
                finding_type = finding.get("finding_type", "Unknown")
                severity_level = finding.get("severity_level", 0)

                # Convert IP address to numeric (simple hash method)
                if ip_address:
                    ip_parts = ip_address.split('.')
                    try:
                        ip_numeric = sum(int(part) * (256 ** (3-i)) for i, part in enumerate(ip_parts))
                    except:
                        ip_numeric = hash(ip_address) % 1000000
                else:
                    ip_numeric = 0

                chart_data.append({
                    "domain_name": domain_name,
                    "ip_address": ip_address,
                    "ip_numeric": ip_numeric,
                    "finding_score": float(finding_score),
                    "finding_type": finding_type,
                    "severity_level": int(severity_level)
                })

        except Exception:
            continue

    if not chart_data:
        return None

    df = pd.DataFrame(chart_data)

    chart = (
        alt.Chart(df)
        .mark_circle(opacity=0.6, size=60)
        .encode(
            x=alt.X(
                "ip_numeric:Q",
                title="IP Address (Numeric)",
                axis=alt.Axis(format=".0f")
            ),
            y=alt.Y(
                "finding_score:Q",
                title="Finding Score"
            ),
            color=alt.Color(
                "finding_type:N",
                title="Finding Type"
            ),
            tooltip=[
                alt.Tooltip("domain_name:N", title="Domain"),
                alt.Tooltip("ip_address:N", title="IP Address"),
                alt.Tooltip("finding_score:Q", format=".2f", title="Finding Score"),
                alt.Tooltip("finding_type:N", title="Finding Type"),
                alt.Tooltip("severity_level:O", title="Severity Level"),
            ],
        )
        .properties(
            width=600,
            height=400,
            title="IP Address Findings Distribution"
        )
        .configure_axis(labelColor="#666666", titleColor="#666666", gridColor="#3a3a3a", gridOpacity=0.3)
        .configure_title(color="#444444", fontSize=16)
        .configure_legend(labelColor="#666666", titleColor="#666666")
    )

    return chart


def timeline_findings_chart(domains_data: list):
    """
    Timeline Findings Chart
    X-axis: Found date
    Y-axis: Finding score
    Color: Domain name
    """
    if not domains_data:
        return None

    chart_data = []

    for domain in domains_data:
        domain_id = domain.get("domain_id") or domain.get("id")
        domain_name = domain.get("domain_name") or domain.get("domain") or f"domain-{domain_id}"

        from services import domain_overview
        try:
            _, findings = domain_overview(domain_id)

            for finding in findings:
                found_date = finding.get("found_date", "")
                finding_score = finding.get("finding_score", 0)
                finding_type = finding.get("finding_type", "Unknown")
                ip_address = finding.get("ip_address", "Unknown IP")

                if found_date:  # Only include records with dates
                    chart_data.append({
                        "domain_name": domain_name,
                        "ip_address": ip_address,
                        "found_date": found_date,
                        "finding_score": float(finding_score),
                        "finding_type": finding_type
                    })

        except Exception:
            continue

    if not chart_data:
        return None

    df = pd.DataFrame(chart_data)

    # Convert date format
    df['found_date'] = pd.to_datetime(df['found_date'], errors='coerce')
    df = df.dropna(subset=['found_date'])

    chart = (
        alt.Chart(df)
        .mark_circle(opacity=0.7, size=80)
        .encode(
            x=alt.X(
                "found_date:T",
                title="Found Date"
            ),
            y=alt.Y(
                "finding_score:Q",
                title="Finding Score"
            ),
            color=alt.Color(
                "finding_type:N",
                title="Finding Type"
            ),
            tooltip=[
                alt.Tooltip("domain_name:N", title="Domain"),
                alt.Tooltip("ip_address:N", title="IP Address"),
                alt.Tooltip("found_date:T", title="Found Date"),
                alt.Tooltip("finding_score:Q", format=".2f", title="Finding Score"),
                alt.Tooltip("finding_type:N", title="Finding Type"),
            ],
        )
        .properties(
            width=600,
            height=400,
            title="Findings Discovery Timeline"
        )
        .configure_axis(labelColor="#666666", titleColor="#666666", gridColor="#3a3a3a", gridOpacity=0.3)
        .configure_title(color="#444444", fontSize=16)
        .configure_legend(labelColor="#666666", titleColor="#666666")
    )

    return chart