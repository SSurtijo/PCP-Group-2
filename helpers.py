# helpers.py
# -----------------------------------------------------------------------------
# Small, API-agnostic helpers:
# - CATEGORY_NAMES: fixed category list used across the app
# - extract_number: best-effort numeric extractor from flexible payloads
# - to_df: normalize "anything" into a pandas DataFrame
# - stringify_nested: stringify dict/list cells so Streamlit can display them
# -----------------------------------------------------------------------------

import json
import pandas as pd
from typing import Any

# Central single source of truth for categories (used by UI + services)
CATEGORY_NAMES = [
    "Attack Surface",
    "Vulnerability Exposure",
    "IP Reputation & Threats",
    "Web Security Posture",
    "Leakage & Breach History",
    "Email Security",
]

CATEGORY_TO_CSF = {
    "Attack Surface": ["ID.AM", "ID.RA", "DE.CM", "PR.PS"],
    "Vulnerability Exposure": ["PR.PS", "ID.RA", "DE.CM", "RS.MI"],
    "IP Reputation & Threats": ["DE.CM", "DE.AE", "RS.AN", "RS.MI"],
    "Web Security Posture": ["PR.PS", "PR.DS", "DE.CM"],
    "Leakage & Breach History": ["ID.RA", "DE.AE", "RS.CO", "RC.RP"],
    "Email Security": ["PR.PS", "PR.AT", "DE.CM", "RS.MI"],
}

CSF_FUNCTION_FULL = {
    "GV": "Govern",
    "ID": "Identify",
    "PR": "Protect",
    "DE": "Detect",
    "RS": "Respond",
    "RC": "Recover",
}


def extract_number(x: Any):
    """
    Try to turn an input into a float.
    Works for:
      - ints/floats
      - numeric strings (e.g., "5.33")
      - dicts with common keys ('score', 'gpa', etc.)
    Returns: float or None.
    """
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
    """
    Convert many shapes to a DataFrame:
      - list[dict] -> DataFrame
      - list[scalar] -> single 'Value' column
      - dict -> json_normalize (fallback to key/value rows)
      - scalar -> single-row 'Value'
    """
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
    For display only:
    - Turn dict/list cells into compact JSON strings (so Streamlit can render).
    - Keep numeric columns numeric wherever possible.
    """
    if df.empty:
        return df

    # stringify nested objects
    for c in df.columns:
        if df[c].apply(lambda x: isinstance(x, (dict, list))).any():
            df[c] = df[c].apply(lambda x: json.dumps(x, ensure_ascii=False))

    # keep numerics numeric; fall back to strings for non-numeric
    for c in df.columns:
        try:
            pd.to_numeric(df[c].dropna(), errors="raise")
        except Exception:
            df[c] = df[c].astype(str)
    return df


def cmm_to_percent(rating, max_rating: float = 5.0):
    """
    Convert a CMM rating (e.g., 0..5) to a 0..100 Score.
    Returns a float (0..100) or None if rating is missing/invalid.
    """
    try:
        r = float(rating)
        if max_rating <= 0:
            return None
        return (r / max_rating) * 100.0
    except Exception:
        return None


def extract_function(csf_code: str) -> str:
    """Return the first 2 letters (Function) from a CSF code like 'ID.AM'."""
    try:
        return csf_code.split(".")[0]  # 'ID' part
    except Exception:
        return ""


def extract_category(csf_code: str) -> str:
    """Return the category part from a CSF code like 'ID.AM'."""
    try:
        return csf_code.split(".")[1]  # 'AM' part
    except Exception:
        return ""


def csf_split(code: str) -> tuple[str, str]:
    """'ID.AM' → ('ID', 'AM'). Safe for malformed inputs."""
    try:
        fn, cat = code.split(".")
        return fn.strip(), cat.strip()
    except Exception:
        return "", ""


def get_function_from_code_or_ref(s: str) -> str:
    if not s:
        return ""
    s = str(s).strip()
    # If it looks like "XX.YY" (CSF control), take the part before the dot
    if "." in s and len(s.split(".", 1)[0]) == 2:
        return s.split(".", 1)[0].upper()
    # If it looks like "GV.OC-02", take the part before the dot as well
    if s.upper().startswith("GV."):
        return "GV"
    # fallback: first two letters if they match a known function
    prefix = s[:2].upper()
    return prefix if prefix in {"GV", "ID", "PR", "DE", "RS", "RC"} else ""


# Keep this slim: return CSF controls only (semicolon-joined)
def summarize_csf_for_category(category: str) -> dict:
    codes = CATEGORY_TO_CSF.get(str(category).strip(), [])
    return {"csf_controls": "; ".join(codes)}


def get_company_category_scores_df(company_id) -> pd.DataFrame:
    """
    Fetch per-category scores for a company using get_category_gpa().
    Returns a DataFrame with columns: Category, category_score, category_gpa.
    """
    # local import to avoid circulars
    from api import get_category_gpa

    # uses: CATEGORY_NAMES, to_df (already in helpers.py)

    rows = []
    for cat in CATEGORY_NAMES:
        label, score, gpa = cat, None, None

        # Call API (shape can vary: dict / list / df)
        try:
            payload = get_category_gpa(company_id, cat)
        except Exception:
            payload = None

        # Dict path
        if isinstance(payload, dict):
            label = payload.get("Category") or payload.get("category") or label
            score = (
                payload.get("category_score")
                or payload.get("score")
                or payload.get("value")
            )
            gpa = payload.get("category_gpa") or payload.get("gpa")

        # DataFrame-like path
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

        # Coerce
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
