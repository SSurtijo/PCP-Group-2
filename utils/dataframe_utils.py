###
# File: utils/dataframe_utils.py
# Description: Utility functions for working with pandas DataFrames.
###


import json
import pandas as pd
from typing import Any


###
# Converts a list of dicts or dicts to a pandas DataFrame.
# Usage: to_df(data)
# Returns: pd.DataFrame
def to_df(data):
    """Convert input to DataFrame (handles dict, list, DataFrame)"""
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if isinstance(data, dict):
        return pd.DataFrame([data])
    if isinstance(data, list):
        if not data:
            return pd.DataFrame()
        if isinstance(data[0], dict):
            return pd.DataFrame(data)
        return pd.DataFrame({"value": data})
    return pd.DataFrame()


# DataFrame utilities for conversion and formatting.
# Used by helpers, services, and UI modules for consistent data handling.


# CATEGORY_NAMES is used throughout the project to refer to the main risk categories.
# It is now centralized here for easy import.
###
# CATEGORY_NAMES: Main risk categories for logic and display.
###
CATEGORY_NAMES = [
    "Attack Surface",
    "Vulnerability Exposure",
    "IP Reputation & Threats",
    "Web Security Posture",
    "Leakage & Breach History",
    "Email Security",
]


def extract_number(x: Any) -> float:
    # Function: extract_number
    # Description: Extracts a float from int, float, str, or dict (score extraction).
    # Usage: extract_number(x)
    # Returns: float or None
    """Handle None input"""
    if x is None:
        return None
    """If input is already a number, convert to float"""
    if isinstance(x, (int, float)):
        return float(x)
    """If input is a string, try to convert to float"""
    if isinstance(x, str):
        try:
            return float(x)
        except Exception:
            return None
    """If input is a dict, look for common score keys and convert"""
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
    """Return None if no conversion succeeded"""
    return None


def domain_overview(domain_id: Any) -> tuple[float | None, list[dict]]:
    # Function: domain_overview
    # Description: Gets the domain score and findings for a given domain_id.
    # Usage: domain_overview(domain_id)
    # Returns: tuple (score: float or None, findings: list of dicts)
    """Load all company bundles"""
    from json_handler import list_company_bundles

    bundles = list_company_bundles()
    """Search for the domain by ID in all bundles"""
    for b in bundles:
        for d in b.get("domains") or []:
            did = d.get("domain_id") or d.get("id") or d.get("domainId")
            if str(did) != str(domain_id):
                continue
            score = d.get("domain_score")
            """Try to convert score to float"""
            try:
                score = float(score) if score is not None else None
            except Exception:
                score = None
            findings: list[dict] = []
            fbc = d.get("findings_by_category") or {}
            """Collect all findings for this domain"""
            for _, rows in fbc.items():
                for r in rows or []:
                    if isinstance(r, dict):
                        rc = dict(r)
                        rc.pop("Category", None)
                        findings.append(rc)
            """If score is missing, calculate average from findings"""
            if score is None and findings:
                vals = []
                for r in findings:
                    for k in ("Finding Score", "finding_score", "score"):
                        try:
                            if r.get(k) is not None:
                                vals.append(float(r[k]))
                                break
                        except Exception:
                            pass
                if vals:
                    score = sum(vals) / len(vals)
            """Return score and findings"""
            return score, findings
    """Return None, [] if not found"""
    return None, []


def stringify_nested(df: pd.DataFrame) -> pd.DataFrame:
    # Function: stringify_nested
    # Description: Converts nested dict/list columns to JSON strings for display.
    # Usage: stringify_nested(df)
    # Returns: pandas DataFrame with nested columns stringified
    """Handle empty DataFrame"""
    if df is None or df.empty:
        return df
    df = df.copy()
    """Convert nested dict/list columns to JSON strings"""
    for c in df.columns:
        if df[c].apply(lambda x: isinstance(x, (dict, list))).any():
            df.loc[:, c] = df[c].apply(lambda x: json.dumps(x, ensure_ascii=False))
    """Convert non-numeric columns to string for display"""
    for c in df.columns:
        try:
            pd.to_numeric(df[c].dropna(), errors="raise")
        except Exception:
            df.loc[:, c] = df[c].astype(str)
    """Return the DataFrame"""
    return df
