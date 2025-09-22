### charts_helpers.py
# Helper functions for chart data extraction and formatting in PCP project.
# All functions use strict formatting: file-level header (###), function-level header (#), and step-by-step logic (#) comments.

from __future__ import annotations
from typing import Iterable, Sequence
import math
from utils.normalization import norm_ref, prefix


# ---------- Data extraction / detection ----------


# Extracts a float rating from a row dict using typical control-level keys.
# Usage: _rating(row)
# Returns: float rating or None
def _rating(row: dict) -> float | None:
    keys = (
        "cmm_rating",
        "rating",
        "level",
        "score",
        "value",
        "current_maturity",
        "current_rating",
        "cmm",
        "maturity",
        "risk_level",
        "risk_rating",
    )
    for k in keys:
        v = row.get(k)
        if v is None:
            continue
        # Try direct float conversion
        try:
            return float(v)
        except Exception:
            # Try tolerant parse: "3/4", "3.0 (ok)", etc.
            try:
                s = str(v)
                s2 = "".join(ch for ch in s if (ch.isdigit() or ch in ".-"))
                if s2:
                    return float(s2)
            except Exception:
                pass
    return None


# Detects the control reference column name in a DataFrame.
# Usage: detect_control_ref_col(df)
# Returns: str column name or None
def detect_control_ref_col(df) -> str | None:
    lower_cols = {c.lower(): c for c in df.columns}
    candidates_exact = [
        "control_ref",
        "control_reference",
        "control",
        "ref",
        "nist_control",
        "csf_control",
        "controlid",
        "control_id",
        "control_code",
        "controlcode",
        "controlkey",
        "control_key",
        "nist_ref",
        "nist_reference",
    ]
    for k in candidates_exact:
        if k in lower_cols:
            return lower_cols[k]
    # Fuzzy match for control reference columns
    for c in df.columns:
        cl = c.lower()
        if "control" in cl and any(x in cl for x in ("ref", "id", "code", "key")):
            return c
    return None


# ---------- Small utilities ----------


# Joins items as uppercase CSV string, sorted.
# Usage: csv_upper(items)
# Returns: str
def csv_upper(items: Iterable[str]) -> str:
    vals = [str(x).upper() for x in items if str(x).strip()]
    return ", ".join(sorted(vals)) if vals else "-"


# Joins items as plain CSV string, sorted.
# Usage: csv_plain(items)
# Returns: str
def csv_plain(items: Iterable[str]) -> str:
    vals = [str(x).strip() for x in items if str(x).strip()]
    return ", ".join(sorted(vals)) if vals else "-"


# Calculates the mean of a sequence of floats, ignoring None and NaN.
# Usage: mean(values)
# Returns: float mean or NaN
def mean(values: Sequence[float]) -> float:
    xs = [float(v) for v in values if v is not None and not math.isnan(float(v))]
    return (sum(xs) / len(xs)) if xs else float("nan")


# Formats a value as a float string or dash if None/NaN/empty.
# Usage: fmt_or_dash(val, decimals)
# Returns: str
def fmt_or_dash(val: float | str | None, decimals: int = 2) -> str:
    if val is None:
        return "-"
    try:
        f = float(val)
        if math.isnan(f):
            return "-"
        return f"{f:.{decimals}f}"
    except Exception:
        s = str(val).strip()
        return s if s else "-"
