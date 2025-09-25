###
# File: charts/charts_mixed.py
# Description: Altair chart builders for external findings and company category scores. Used in dashboard visualizations.
###
import altair as alt
import pandas as pd
from services import (
    get_company_category_scores_df,
    build_external_finding_gpa_cmm,
    to_external_findings_long,
)

__all__ = [
    "external_findings_chart_overlapped",
    "external_findings_chart_grouped",
    "company_category_scores_chart",
]


def external_findings_chart_overlapped(selected_company_id: int) -> alt.Chart:
    """Build external finding GPA/CMM dataframe for selected company."""
    scores_df = get_company_category_scores_df(selected_company_id)
    """Prepare empty internal_rows for compatibility."""
    internal_rows = []
    """Transform scores_df and internal_rows into chart dataframe."""
    df = build_external_finding_gpa_cmm(scores_df, internal_rows)
    """Create base chart with external finding on y-axis."""
    base = alt.Chart(df).encode(y=alt.Y("external_finding:N", title="External Finding"))
    """GPA bar: x-axis is GPA, tooltip shows category and GPA."""
    gpa = base.mark_bar(opacity=0.45).encode(
        x=alt.X("gpa:Q", title="GPA / CMM", scale=alt.Scale(domain=[0, 4])),
        tooltip=[
            alt.Tooltip("category:N", title="Category"),
            alt.Tooltip("gpa:Q", title="GPA", format=".2f"),
        ],
    )
    """CMM bar: x-axis is CMM score, tooltip shows category, control refs, and mean CMM."""
    cmm = base.mark_bar().encode(
        x=alt.X("cmm_score:Q", title="GPA / CMM", scale=alt.Scale(domain=[0, 4])),
        tooltip=[
            alt.Tooltip("category:N", title="Category"),
            alt.Tooltip("control_refs:N", title="Control Ref(s)"),
            alt.Tooltip("cmm_score:Q", title="Mean CMM", format=".2f"),
        ],
    )
    """Return combined GPA and CMM bar chart."""
    return gpa + cmm


def external_findings_chart_grouped(
    selected_company_id: int, internal_rows=None
) -> alt.Chart:
    """Build and pivot external finding GPA/CMM data to long format."""
    if internal_rows is None:
        internal_rows = []
    """Get scores and build chart dataframe."""
    scores_df = get_company_category_scores_df(selected_company_id)
    df = build_external_finding_gpa_cmm(scores_df, internal_rows)
    long_df = to_external_findings_long(df)
    """Create base chart from long-form dataframe."""
    base = alt.Chart(long_df)
    """Bar chart: y=external finding, x=score, color by metric, yOffset for series, tooltips for details."""
    chart = base.mark_bar().encode(
        y=alt.Y("external_finding:N", title="External Finding"),
        x=alt.X("score:Q", title="GPA / CMM", scale=alt.Scale(domain=[0, 4])),
        color=alt.Color(
            "metric:N",
            title="",
            legend=alt.Legend(orient="right"),
            scale=alt.Scale(range=["#9BD1FF", "#3C556E"]),
        ),
        yOffset="metric:N",
        tooltip=[
            alt.Tooltip("category:N", title="Category"),
            alt.Tooltip("metric:N", title="Series"),
            alt.Tooltip("score:Q", title="Value", format=".2f"),
            alt.Tooltip("control_refs:N", title="Control Ref(s)"),
        ],
    )
    """Return grouped bar chart."""
    return chart


def company_category_scores_chart(
    selected_company_id: int,
    height_per_bar: int = 80,
    bar_size: int = 45,
    label_padding: int = 30,
    sort_mode: str = "score_desc",
) -> alt.Chart:
    """Extract and normalize category and score columns for selected company."""
    df = get_company_category_scores_df(selected_company_id)
    """Handle empty or invalid input dataframe."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None
    """Map columns to expected names."""
    cols = {c.lower(): c for c in df.columns}
    cat_col = cols.get("category") or "Category"
    score_col = cols.get("category_gpa") or cols.get("score") or "Score"
    """Check for required columns."""
    if cat_col not in df.columns or score_col not in df.columns:
        return None
    """Prepare chart data: rename columns, convert scores to numeric."""
    data = (
        df[[cat_col, score_col]]
        .rename(columns={cat_col: "Category", score_col: "Score"})
        .assign(Score=lambda x: pd.to_numeric(x["Score"], errors="coerce").fillna(0))
    )
    """Sort categories by mode and set chart height."""
    y_sort = {"category_asc": "ascending", "score_asc": "x"}.get(sort_mode, "-x")
    height = max(height_per_bar * len(data), 200)
    """Return horizontal bar chart: x=score, y=category, sorted by mode."""
    return (
        alt.Chart(data)
        .mark_bar(size=bar_size, opacity=0.85, clip=True)
        .encode(
            x=alt.X(
                "Score:Q",
                scale=alt.Scale(domain=[0, 4]),
                title="Current maturity (0–4)",
            ),
            y=alt.Y(
                "Category:N", sort=y_sort, axis=alt.Axis(labelPadding=label_padding)
            ),
        )
        .properties(height=height)
    )
