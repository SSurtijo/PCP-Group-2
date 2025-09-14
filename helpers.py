# helpers.py
# -----------------------------------------------------------------------------
# Small, API-agnostic helpers:
# - CATEGORY_NAMES: fixed category list used across the app
# - to_df: normalize "anything" into a pandas DataFrame
# - stringify_nested: stringify dict/list cells so Streamlit can display them
# - summarize_csf_for_category / get_company_category_scores_df: data shaping
# -----------------------------------------------------------------------------
import json
import pandas as pd
from typing import Any

# ---------------------------------------------------------------------
# Categories used by the UI & services (API requires explicit category)
# ---------------------------------------------------------------------
CATEGORY_NAMES = [
    "Attack Surface",
    "Vulnerability Exposure",
    "IP Reputation & Threats",
    "Web Security Posture",
    "Leakage & Breach History",
    "Email Security",
]


# ---------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------
def extract_number(x: Any):
    """Best-effort numeric extractor from flexible payloads."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x)
        except Exception:
            return None
    if isinstance(x, dict):
        for k in (
            "domain_score",
            "score",
            "overall_score",
            "value",
            "avg",
            "overall",
            "category_gpa",
            "gpa",
            "total_gpa",
        ):
            v = x.get(k)
            try:
                return float(v)
            except Exception:
                pass
    return None


def to_df(obj: Any) -> pd.DataFrame:
    """Convert many shapes to a DataFrame."""
    if obj is None:
        return pd.DataFrame()
    if isinstance(obj, list):
        if not obj:
            return pd.DataFrame()
        return (
            pd.DataFrame(obj)
            if isinstance(obj[0], dict)
            else pd.DataFrame({"Value": obj})
        )
    if isinstance(obj, dict):
        try:
            df = pd.json_normalize(obj, max_level=1)
            if df.empty:
                df = pd.DataFrame.from_dict(obj, orient="index").reset_index(
                    names="Key"
                )
        except Exception:
            df = pd.DataFrame.from_dict(obj, orient="index").reset_index(names="Key")
        return df
    return pd.DataFrame({"Value": [obj]})


def stringify_nested(df: pd.DataFrame) -> pd.DataFrame:
    """
    Display helper:
    - Turn dict/list cells into compact JSON strings.
    - Keep numerics numeric; cast non-numeric to str.
    (Works on a copy to avoid SettingWithCopy warnings.)
    """
    if df is None or df.empty:
        return df
    df = df.copy()
    # stringify nested objects
    for c in df.columns:
        if df[c].apply(lambda x: isinstance(x, (dict, list))).any():
            df.loc[:, c] = df[c].apply(lambda x: json.dumps(x, ensure_ascii=False))
    # keep numerics numeric; cast others to str
    for c in df.columns:
        try:
            pd.to_numeric(df[c].dropna(), errors="raise")
        except Exception:
            df.loc[:, c] = df[c].astype(str)
    return df


def get_function_from_code_or_ref(s: str) -> str:
    """Return CSF function code from a control or GV ref."""
    if not s:
        return ""
    s = str(s).strip()
    if "." in s and len(s.split(".", 1)[0]) == 2:
        return s.split(".", 1)[0].upper()  # 'ID' from 'ID.AM' or 'GV' from 'GV.OC-01'
    if s.upper().startswith("GV."):
        return "GV"
    prefix = s[:2].upper()
    return prefix if prefix in {"GV", "ID", "PR", "DE", "RS", "RC"} else ""


def get_company_category_scores_df(company_id) -> pd.DataFrame:
    """Fetch per-category scores for a company using get_category_gpa()."""
    from api import get_category_gpa  # local import to avoid circulars

    rows = []
    for cat in CATEGORY_NAMES:
        label, score, gpa = cat, None, None
        try:
            payload = get_category_gpa(company_id, cat)
        except Exception:
            payload = None

        if isinstance(payload, dict):
            label = payload.get("Category") or payload.get("category") or label
            score = (
                payload.get("category_score")
                or payload.get("score")
                or payload.get("value")
            )
            gpa = payload.get("category_gpa") or payload.get("gpa")

        try:
            dfp = to_df(payload)
        except Exception:
            dfp = None

        if isinstance(dfp, pd.DataFrame) and not dfp.empty:
            if "Category" in dfp.columns and pd.notna(dfp["Category"].iloc[0]):
                label = dfp["Category"].iloc[0]
            elif "category" in dfp.columns and pd.notna(dfp["category"].iloc[0]):
                label = dfp["category"].iloc[0]

            if "category_score" in dfp.columns:
                score = dfp["category_score"].iloc[0]
            elif "score" in dfp.columns:
                score = dfp["score"].iloc[0]
            elif "value" in dfp.columns:
                score = dfp["value"].iloc[0]

            if "category_gpa" in dfp.columns:
                gpa = dfp["category_gpa"].iloc[0]
            elif "gpa" in dfp.columns:
                gpa = dfp["gpa"].iloc[0]

        try:
            score = float(score)
        except Exception:
            score = None
        try:
            gpa = float(gpa)
        except Exception:
            gpa = None

        rows.append({"Category": label, "category_score": score, "category_gpa": gpa})

    out = pd.DataFrame(rows)
    out["category_score"] = pd.to_numeric(
        out["category_score"], errors="coerce"
    ).fillna(0)
    return out
