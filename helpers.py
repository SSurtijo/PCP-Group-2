# helpers.py
# -----------------------------------------------------------------------------
# API-agnostic helpers + JSON-backed get_company_category_scores_df
# -----------------------------------------------------------------------------
import json
import pandas as pd
from typing import Any

CATEGORY_NAMES = [
    "Attack Surface",
    "Vulnerability Exposure",
    "IP Reputation & Threats",
    "Web Security Posture",
    "Leakage & Breach History",
    "Email Security",
]


def extract_number(x: Any):
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
    if df is None or df.empty:
        return df
    df = df.copy()
    for c in df.columns:
        if df[c].apply(lambda x: isinstance(x, (dict, list))).any():
            df.loc[:, c] = df[c].apply(lambda x: json.dumps(x, ensure_ascii=False))
    for c in df.columns:
        try:
            pd.to_numeric(df[c].dropna(), errors="raise")
        except Exception:
            df.loc[:, c] = df[c].astype(str)
    return df


def get_company_category_scores_df(company_id) -> pd.DataFrame:
    """
    Read Category + {category_score, category_gpa} from the per-company bundle.
    """
    from json_handler import load_company_bundle  # avoid cycles

    b = load_company_bundle(company_id) or {}
    rows = []
    for cat in b.get("categories") or []:
        label = cat.get("Category")
        score = cat.get("category_score")
        gpa = cat.get("category_gpa")
        try:
            score = float(score) if score is not None else None
        except Exception:
            score = None
        try:
            gpa = float(gpa) if gpa is not None else None
        except Exception:
            gpa = None
        rows.append({"Category": label, "category_score": score, "category_gpa": gpa})

    out = pd.DataFrame(rows)
    if not out.empty and "category_score" in out.columns:
        out["category_score"] = pd.to_numeric(
            out["category_score"], errors="coerce"
        ).fillna(0)
    return out
