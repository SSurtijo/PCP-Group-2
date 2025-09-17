# charts/charts_helpers.py

from __future__ import annotations
from typing import Iterable, Sequence
import math

# ---------- Normalizers ----------


def _norm_ref(s: str) -> str:
    """Normalize control refs like PR-PS-1 → PR.PS-01."""
    if not s:
        return ""
    s = str(s).upper().strip()
    if "-" in s:
        prefix, tail = s.split("-", 1)
        prefix = prefix.replace("_", ".").replace("-", ".")
        while ".." in prefix:
            prefix = prefix.replace("..", ".")
        tail = tail.strip()
        if tail.isdigit():
            tail = tail.zfill(2)
        return f"{prefix}-{tail}"
    s2 = s.replace("_", ".").replace("-", ".")
    while ".." in s2:
        s2 = s2.replace("..", ".")
    parts = [p for p in s2.split(".") if p]
    if len(parts) >= 3 and parts[2].isdigit():
        return f"{parts[0]}.{parts[1]}-{parts[2].zfill(2)}"
    return s


def _prefix(x: str) -> str:
    """Return 'FN.CAT' from control (PR.PS-01 → PR.PS)."""
    if not x:
        return ""
    x = str(x).upper().strip()
    if "-" in x:
        x = x.split("-", 1)[0]
    x = x.replace("_", ".").replace("-", ".")
    while ".." in x:
        x = x.replace("..", ".")
    parts = [p for p in x.split(".") if p]
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[1]}"
    return parts[0] if parts else ""


# ---------- Data extraction / detection ----------


def _rating(row: dict) -> float | None:
    """
    Try multiple typical keys used by APIs for per-control maturity.
    We avoid 'gpa' here because that's category-level, not control-level.
    """
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
        # fast path
        try:
            return float(v)
        except Exception:
            # tolerant parse: "3/4", "3.0 (ok)", etc.
            try:
                s = str(v)
                s2 = "".join(ch for ch in s if (ch.isdigit() or ch in ".-"))
                if s2:
                    return float(s2)
            except Exception:
                pass
    return None


def detect_control_ref_col(df) -> str | None:
    """Be generous about control reference column names from API."""
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
    for c in df.columns:  # fuzzy
        cl = c.lower()
        if "control" in cl and any(x in cl for x in ("ref", "id", "code", "key")):
            return c
    return None


# ---------- Small utilities ----------


def csv_upper(items: Iterable[str]) -> str:
    vals = [str(x).upper() for x in items if str(x).strip()]
    return ", ".join(sorted(vals)) if vals else "-"


def csv_plain(items: Iterable[str]) -> str:
    vals = [str(x).strip() for x in items if str(x).strip()]
    return ", ".join(sorted(vals)) if vals else "-"


def mean(values: Sequence[float]) -> float:
    xs = [float(v) for v in values if v is not None and not math.isnan(float(v))]
    return (sum(xs) / len(xs)) if xs else float("nan")


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
