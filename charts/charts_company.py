import altair as alt
import pandas as pd


def company_category_scores_chart(
    df,
    height_per_bar: int = 80,
    bar_size: int = 45,
    label_padding: int = 30,
    sort_mode: str = "score_desc",
):
    """Bar chart of Company category scores (0–4)."""
    if isinstance(df, (dict, list)):
        df = pd.DataFrame(df)
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None

    cols = {c.lower(): c for c in df.columns}
    cat_col = cols.get("category") or "Category"
    score_col = cols.get("category_gpa") or cols.get("score") or "Score"

    if cat_col not in df.columns or score_col not in df.columns:
        return None

    data = (
        df[[cat_col, score_col]]
        .rename(columns={cat_col: "Category", score_col: "Score"})
        .assign(Score=lambda x: pd.to_numeric(x["Score"], errors="coerce").fillna(0))
    )

    y_sort = {"category_asc": "ascending", "score_asc": "x"}.get(sort_mode, "-x")
    height = max(height_per_bar * len(data), 200)

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
