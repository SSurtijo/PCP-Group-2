### charts_company.py
# Chart functions for company category scores in PCP project.
# All functions use strict formatting: file-level header (###), function-level header (#), and step-by-step logic (#) comments.

import altair as alt
import pandas as pd


# Bar chart of Company category scores (0–4).
# Usage: company_category_scores_chart(df, ...)
# Returns: Altair chart or None
def company_category_scores_chart(
    df,
    height_per_bar: int = 80,
    bar_size: int = 45,
    label_padding: int = 30,
    sort_mode: str = "score_desc",
):
    # Convert input to DataFrame if needed
    if isinstance(df, (dict, list)):
        df = pd.DataFrame(df)
    # Return None if input is not a valid DataFrame
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None
    # Identify category and score columns
    cols = {c.lower(): c for c in df.columns}
    cat_col = cols.get("category") or "Category"
    score_col = cols.get("category_gpa") or cols.get("score") or "Score"
    if cat_col not in df.columns or score_col not in df.columns:
        return None
    # Prepare data for chart
    data = (
        df[[cat_col, score_col]]
        .rename(columns={cat_col: "Category", score_col: "Score"})
        .assign(Score=lambda x: pd.to_numeric(x["Score"], errors="coerce").fillna(0))
    )
    # Set sort mode and chart height
    y_sort = {"category_asc": "ascending", "score_asc": "x"}.get(sort_mode, "-x")
    height = max(height_per_bar * len(data), 200)
    # Return Altair bar chart
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
