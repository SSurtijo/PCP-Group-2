### helpers.py
# Centralized utility functions for PCP project (used by charts/ and other modules)
# Only pure utilities (no chart libs, no I/O, no service logic)

from typing import Iterable, Sequence, Any
import math


# Joins items as uppercase CSV string, sorted.
def csv_upper(items: Iterable[str]) -> str:
    vals = [str(x).upper() for x in items if str(x).strip()]
    return ", ".join(sorted(vals)) if vals else "-"


# Joins items as plain CSV string, sorted.
def csv_plain(items: Iterable[str]) -> str:
    vals = [str(x).strip() for x in items if str(x).strip()]
    return ", ".join(sorted(vals)) if vals else "-"


# Calculates the mean of a sequence of floats, ignoring None and NaN.
def mean(values: Sequence[float]) -> float:
    xs = [float(v) for v in values if v is not None and not math.isnan(float(v))]
    return (sum(xs) / len(xs)) if xs else float("nan")


# Formats a value as a float string or dash if None/NaN/empty.
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


# Extracts a float rating from a row dict using typical control-level keys.
def extract_rating(row: dict) -> float | None:
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
        try:
            return float(v)
        except Exception:
            try:
                s = str(v)
                s2 = "".join(ch for ch in s if (ch.isdigit() or ch in ".-"))
                if s2:
                    return float(s2)
            except Exception:
                pass
    return None


# Detects the control reference column name in a DataFrame.
def detect_control_ref_col(df: Any) -> str | None:
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
    for c in df.columns:
        cl = c.lower()
        if "control" in cl and any(x in cl for x in ("ref", "id", "code", "key")):
            return c
    return None
