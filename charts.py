# charts.py
import altair as alt
import pandas as pd

# Canonical NIST helpers (mappings & utility):
from nist.nist_helpers import CATEGORY_TO_CSF, get_function_from_code_or_ref
from nist.nist_mappings import CSF_FUNCTION_FULL


def csf_function_distribution_chart(
    findings_df: pd.DataFrame,
    internal_gv_df: pd.DataFrame | None = None,
    type_col_candidates=("Type", "finding_type", "Category", "category"),
):
    """
    Build a function-level distribution (GV/ID/PR/DE/RS/RC) as percentages (0–100).

    Inputs:
      - findings_df: DataFrame that contains a column with your company categories (Type).
      - internal_gv_df: optional DataFrame from internal API (GV control_ref rows).
        If provided, each row counts +1 to GV.
    Logic:
      1) Count frequency of each company category in findings.
      2) Expand each category to its CSF controls (CATEGORY_TO_CSF).
      3) Convert each control to its Function (ID/PR/DE/RS/RC).
      4) If internal_gv_df is present, increment GV counts for each GV row.
      5) Convert counts to percentages of the total.
    """
    if findings_df is None:
        findings_df = pd.DataFrame()

    # 1) find the company-category column
    type_col = next((c for c in type_col_candidates if c in findings_df.columns), None)

    func_counts: dict[str, int] = {}

    # 2..3) category -> CSF controls -> Functions
    if type_col and not findings_df.empty:
        freq = (
            findings_df[type_col]
            .dropna()
            .astype(str)
            .value_counts()
            .rename_axis("company_category")
            .reset_index(name="count")
        )
        for _, r in freq.iterrows():
            company_cat = r["company_category"]
            n = int(r["count"])
            codes = CATEGORY_TO_CSF.get(company_cat, [])
            for code in codes:
                fn = get_function_from_code_or_ref(code)  # e.g., "ID"
                if not fn:
                    continue
                func_counts[fn] = func_counts.get(fn, 0) + n

    # 4) add GV rows from internal API
    if internal_gv_df is not None and not internal_gv_df.empty:
        if "control_ref" in internal_gv_df.columns:
            gv_n = (
                internal_gv_df["control_ref"]
                .astype(str)
                .str.upper()
                .str.startswith("GV.")
                .sum()
            )
            if gv_n:
                func_counts["GV"] = func_counts.get("GV", 0) + int(gv_n)

    # If nothing to show
    if not func_counts:
        return (
            alt.Chart(pd.DataFrame({"msg": ["No data for function distribution"]}))
            .mark_text()
            .encode(text="msg")
        )

    # 5) turn into percentages
    df = pd.DataFrame([{"function": k, "count": v} for k, v in func_counts.items()])
    total = df["count"].sum()
    df["percent"] = (df["count"] / total * 100).round(1)
    df["function_full"] = df["function"].map(lambda f: CSF_FUNCTION_FULL.get(f, f))

    df = df.sort_values("percent", ascending=False).reset_index(drop=True)

    base = alt.Chart(df)
    bars = base.mark_bar().encode(
        x=alt.X("function_full:N", title="NIST CSF Function", sort=None),
        y=alt.Y("percent:Q", title="Percent of total (0–100)"),
        tooltip=[
            alt.Tooltip("function_full:N", title="Function"),
            alt.Tooltip("function:N", title="Code"),
            alt.Tooltip("count:Q", title="Count"),
            alt.Tooltip("percent:Q", title="Percent", format=".1f"),
        ],
    )
    return bars


def company_category_scores_chart(
    df,
    height_per_bar: int = 80,
    bar_size: int = 45,
    label_padding: int = 30,
    sort_mode: str = "score_desc",
):
    """
    Build a bar chart for per-category scores.

    sort_mode:
      - "category_asc" → A → Z by Category
      - "score_desc"   → Score: High → Low
      - "score_asc"    → Score: Low → High
    """
    if isinstance(df, (dict, list)):
        df = pd.DataFrame(df)
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None

    col_map = {c.lower(): c for c in df.columns}
    category_col = col_map.get("category") or "Category"
    score_col = (
        col_map.get("category_score")
        or col_map.get("score")
        or col_map.get("value")
        or "Score"
    )

    if category_col not in df.columns:
        return None
    if score_col not in df.columns:
        alt_score = col_map.get("category_gpa") or col_map.get("gpa")
        if alt_score and alt_score in df.columns:
            score_col = alt_score
        else:
            return None

    work = df[[category_col, score_col]].copy()
    work.rename(columns={category_col: "Category", score_col: "Score"}, inplace=True)
    work["Score"] = pd.to_numeric(work["Score"], errors="coerce").fillna(0)

    if sort_mode == "category_asc":
        y_sort = "ascending"
    elif sort_mode == "score_asc":
        y_sort = "x"
    else:
        y_sort = "-x"

    bar_height = max(height_per_bar * len(work), 200)

    chart = (
        alt.Chart(work)
        .mark_bar(size=bar_size, opacity=0.7, clip=True)
        .encode(
            x=alt.X("Score:Q", scale=alt.Scale(domain=[0, 100]), title="Score"),
            y=alt.Y(
                "Category:N", sort=y_sort, axis=alt.Axis(labelPadding=label_padding)
            ),
            tooltip=["Category", alt.Tooltip("Score:Q", format=".1f")],
        )
        .properties(height=bar_height)
    )
    return chart
