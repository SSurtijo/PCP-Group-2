import altair as alt
import pandas as pd

#This file contains all chart-related functions

def altair_distribution_chart(df):
    """Distribution of Risk Findings (NIST Functions)."""
    functions = ["Identify", "Protect", "Detect", "Respond", "Recover"]
    dist = pd.DataFrame({"NIST Function": functions})

    if not df.empty:
        counts = df["NIST Function"].value_counts(normalize=True) * 100
        dist["Percentage"] = dist["NIST Function"].map(counts).fillna(0).round(2)
        risk_counts = df.groupby("NIST Function")["Risk Name"].count()
        dist["Risk Count"] = dist["NIST Function"].map(risk_counts).fillna(0).astype(int)
        risk_list = df.groupby("NIST Function")["Risk Name"].apply(lambda x: ", ".join(x))
        dist["Risks"] = dist["NIST Function"].map(risk_list).fillna("None")
    else:
        dist[["Percentage", "Risk Count", "Risks"]] = [0, 0, "None"]

    dist["BarValue"] = dist["Percentage"].apply(lambda x: 0.1 if x == 0 else x)

    base = alt.Chart(dist)
    bars = base.mark_bar(color="skyblue").encode(
        x=alt.X('NIST Function', sort=None),
        y=alt.Y('BarValue', scale=alt.Scale(domain=[0, 100])),
        tooltip=['NIST Function', 'Percentage', 'Risk Count', 'Risks']
    )
    hover = base.mark_point(size=200, opacity=0).encode(
        x='NIST Function',
        y='BarValue',
        tooltip=['NIST Function', 'Percentage', 'Risk Count', 'Risks']
    )
    return bars + hover


def altair_control_maturity_chart(df, target_score=20):
    """Control Maturity (average score by NIST Function)."""
    df["Score"] = pd.to_numeric(df["Score"], errors="coerce")

    avg_scores = (
        df.groupby("NIST Function", as_index=False)["Score"]
        .mean()
        .rename(columns={"Score": "Avg Score"})
    )
    avg_scores["BarValue"] = avg_scores["Avg Score"].apply(lambda x: 0.1 if x == 0 else x)

    tooltip_data = df.groupby("NIST Function", as_index=False).agg({
        "Risk Name": lambda x: ", ".join(x),
        "Score": "count"
    }).rename(columns={"Risk Name": "Risks", "Score": "Risk Count"})

    avg_scores = avg_scores.merge(tooltip_data, on="NIST Function", how="left").fillna({"Risks": "None", "Risk Count": 0})

    base = alt.Chart(avg_scores)
    bars = base.mark_bar(color="skyblue").encode(
        x=alt.X('NIST Function', sort=None),
        y=alt.Y('BarValue', scale=alt.Scale(domain=[0, 100])),
        tooltip=['NIST Function', 'Avg Score', 'Risk Count', 'Risks']
    )
    hover = base.mark_point(size=200, opacity=0).encode(
        x='NIST Function',
        y='BarValue',
        tooltip=['NIST Function', 'Avg Score', 'Risk Count', 'Risks']
    )
    target = alt.Chart(pd.DataFrame({"Target": [target_score]})).mark_rule(
        color='red', strokeDash=[6, 3]
    ).encode(y='Target')

    return bars + hover + target


def altair_individual_risk_chart(df):
    """Individual Risk Chart (each risk and its score)."""
    df = df.copy()
    df["Original Score"] = df["Score"]
    df["BarValue"] = df["Score"].apply(lambda x: 0.1 if x == 0 else x)

    return alt.Chart(df).mark_bar().encode(
        x=alt.X('BarValue', scale=alt.Scale(domain=[0, 100]), title='Score'),
        y=alt.Y('Risk Name', sort='-x'),
        color=alt.Color('BarValue', scale=alt.Scale(domain=[0, 100], range=['green', 'red'])),
        tooltip=['Risk Name', alt.Tooltip('Original Score', title='Score')]
    )
