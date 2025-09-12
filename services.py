# services.py
# -----------------------------------------------------------------------------
# Service layer
# - Bridges API responses and the UI.
# - Keep "business/data shaping" logic out of app.py so the UI stays clean.
# - Safe to unit test these functions without Streamlit.
# -----------------------------------------------------------------------------

from typing import Any, Dict, List, Tuple, Optional
import pandas as pd

from helpers import CATEGORY_NAMES, extract_number
from api import (
    get_companies,
    get_domains,
    get_company_risk_grade,
    get_domain_score,
    get_category_gpa,
    get_findings_by_category,
)


# -------------------------------
# Basic pass-through fetchers
# -------------------------------
def companies() -> List[Dict]:
    """Return list of companies from the API."""
    return get_companies()


def domains() -> List[Dict]:
    """Return list of domains from the API."""
    return get_domains()


# -------------------------------------------------------
# Sidebar company list drop down
# -------------------------------------------------------
def list_company_options(cs: List[Dict]) -> Tuple[List[str], Dict[str, Any]]:
    """
    Build sidebar labels and a lookup map back to company_id.
    - options: list of strings shown in the selectbox
    - mapping: {option_label -> company_id}
    """
    opts, map_ = [], {}
    for c in cs:
        cid = c.get("company_id") or c.get("id")
        name = c.get("company_name") or c.get("name") or f"Company {cid}"
        label = f"{cid} — {name}" if cid is not None else name
        opts.append(label)
        map_[label] = cid
    return opts, map_


# ---------------------------------------------
# Filter all domains down to a single company
# ---------------------------------------------
def filter_domains_for_company(ds: List[Dict], company_id: Any) -> List[Dict]:
    """Return only domains whose company_id matches the given id."""
    sid = None if company_id is None else str(company_id)

    def _cid(d):
        # Try several common key names to be robust to API schema
        return d.get("company_id") or d.get("companyId") or d.get("cid")

    return [d for d in ds if (None if _cid(d) is None else str(_cid(d))) == sid]


# ----------------------------------------------------
# Company summary card (grade, total_gpa, calc date)
# ----------------------------------------------------
def company_summary(company_id: Any) -> Dict[str, str]:
    """
    Return a small dict for the KPI row:
    - grade: string (e.g., 'A', 'B', '—')
    - total_gpa: string 'xx.xx' or '—'
    - calculated_date: string or '—'

    If total_gpa is missing, we fall back to mean(Category GPAs).
    """
    out = {"grade": "—", "total_gpa": "—", "calculated_date": "—"}
    try:
        crg = get_company_risk_grade(company_id) or {}
        if crg:
            if crg.get("grade"):
                out["grade"] = str(crg["grade"])
            if crg.get("total_gpa") is not None:
                out["total_gpa"] = f"{float(crg['total_gpa']):.2f}"
            if crg.get("calculated_date"):
                out["calculated_date"] = str(crg["calculated_date"])
    except Exception:
        # Silently ignore since the UI can still render other fields
        pass

    # Fallback if the API omitted total_gpa: average per-category GPAs
    if out["total_gpa"] == "—":
        gpas = []
        for cat in CATEGORY_NAMES:
            try:
                gp = get_category_gpa(company_id, cat)
                row = gp[0] if isinstance(gp, list) and gp else gp
                if isinstance(row, dict):
                    for k in ("category_gpa", "gpa", "value"):
                        if row.get(k) is not None:
                            gpas.append(float(row[k]))
                            break
            except Exception:
                pass
        if gpas:
            out["total_gpa"] = f"{sum(gpas) / len(gpas):.2f}"
    return out


# ---------------------------------------------------
# Domain overview: (score, findings_list-of-dicts)
# ---------------------------------------------------
def domain_overview(domain_id: Any) -> Tuple[Optional[float], List[Dict]]:
    """
    Return a domain score (float) and a raw findings list (list[dict]).
    - If get_domain_score fails/returns None, compute a mean from findings.
    - Findings are concatenated across all categories, stripping 'Category' to
      keep the RAW table neutral on this tab.
    """
    score = None

    # Try the direct score endpoint first
    try:
        score = extract_number(get_domain_score(domain_id))
    except Exception:
        pass

    # Build one big list of raw findings across all categories
    findings: List[Dict] = []
    for cat in CATEGORY_NAMES:
        try:
            data = get_findings_by_category(domain_id, cat)
            # Normalize the many possible shapes into a list of dicts
            rows = (
                data
                if isinstance(data, list)
                else (
                    data.get("findings", [])
                    if isinstance(data, dict) and isinstance(data.get("findings"), list)
                    else ([data] if isinstance(data, dict) and data else [])
                )
            )
            # Remove any stray 'Category' so the table remains "original"
            for r in rows:
                if isinstance(r, dict):
                    r.pop("Category", None)
            findings.extend([r for r in rows if isinstance(r, dict)])
        except Exception:
            # Keep looping other categories even if one fails
            pass

    # Fallback: if no score endpoint value, compute mean from rows
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

    return score, findings


# ------------------------------------------------------------
# Chart data helper (optional; used if you later build charts)
# ------------------------------------------------------------
def findings_to_chart_df(findings: List[Dict]) -> pd.DataFrame:
    """
    Convert raw findings to a minimal chart-ready DataFrame with:
    - Risk Name
    - Score
    - NIST Function
    """
    if not findings:
        return pd.DataFrame(columns=["Risk Name", "Score", "NIST Function"])

    rows = []
    for r in findings:
        if not isinstance(r, dict):
            continue
        name = (
            r.get("Risk Name")
            or r.get("risk_name")
            or r.get("name")
            or r.get("title")
            or "Risk"
        )

        # Extract a numeric score from several possible keys
        score = None
        for k in ("Finding Score", "finding_score", "score"):
            if r.get(k) is not None:
                try:
                    score = float(r[k])
                    break
                except Exception:
                    pass

        nist = (
            r.get("NIST Function")
            or r.get("nist_function")
            or r.get("function")
            or None
        )
        rows.append(
            {
                "Risk Name": str(name),
                "Score": score if score is not None else 0.0,
                "NIST Function": nist,
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------
# Original-table column resolution + filter implementation
# ---------------------------------------------------------
def _resolve_domain_cols(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Pick which column names to use for IP / Type / Level / Found Date,
    being tolerant to different spellings from the API.
    """

    def pick(cands):
        for c in cands:
            if c in df.columns:
                return c
        return None

    return {
        "ip": pick(["IP address", "ip_address", "address", "ip", "IP"]),
        "type": pick(["Type", "finding_type", "Category", "category"]),
        "level": pick(["Severity level", "severity_level", "severity", "level"]),
        "fdate": pick(["Found date", "found_date", "date_found", "found", "Date"]),
    }


def _as_dt(s: pd.Series) -> pd.Series:
    """Safe datetime conversion that yields NaT for bad values (no crash)."""
    try:
        return pd.to_datetime(s, errors="coerce", utc=False)
    except Exception:
        return pd.to_datetime(pd.Series([], dtype=object))


def get_domain_filter_options_original(
    findings: List[Dict],
) -> Tuple[Dict[str, list], list]:
    """
    From the raw findings table, compute:
    - distinct IPs / Types / Levels / Dates (strings)
    - original column order (so UI can keep the table "as returned")
    """
    df = pd.DataFrame(findings or [])
    cols_order = list(df.columns)

    if df.empty:
        return {"ips": [], "types": [], "levels": [], "dates": []}, cols_order

    cols = _resolve_domain_cols(df)

    ips = (
        sorted(df[cols["ip"]].dropna().astype(str).unique().tolist())
        if cols["ip"]
        else []
    )
    types = (
        sorted(df[cols["type"]].dropna().astype(str).unique().tolist())
        if cols["type"]
        else []
    )

    levels = (
        df[cols["level"]].dropna().astype(str).unique().tolist()
        if cols["level"]
        else []
    )
    try:
        # If levels are numeric, sort numerically; else lexical
        levels = sorted(levels, key=lambda x: float(x))
    except Exception:
        levels = sorted(levels)

    dates = []
    if cols["fdate"]:
        dates = (
            _as_dt(df[cols["fdate"]]).dropna().dt.strftime("%Y-%m-%d").unique().tolist()
        )
        dates = sorted(dates)

    return {"ips": ips, "types": types, "levels": levels, "dates": dates}, cols_order


def filter_domain_findings_original(
    findings: List[Dict],
    ip: Optional[str] = None,
    ftype: Optional[str] = None,
    level: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Apply filters on the original raw findings DataFrame.
    - Filters accept "All"/"Any" to mean "no filter".
    - Dates are inclusive (>= start and <= end).
    """
    df = pd.DataFrame(findings or [])
    if df.empty:
        return df

    cols = _resolve_domain_cols(df)

    if ip and ip != "All" and cols["ip"]:
        df = df[df[cols["ip"]].astype(str) == str(ip)]

    if ftype and ftype != "All" and cols["type"]:
        df = df[df[cols["type"]].astype(str) == str(ftype)]

    if level and level != "All" and cols["level"]:
        df = df[df[cols["level"]].astype(str) == str(level)]

    if (start_date and start_date != "Any") or (end_date and end_date != "Any"):
        if cols["fdate"]:
            s = _as_dt(df[cols["fdate"]])  # may contain NaT
            if start_date and start_date != "Any":
                df = df[s >= pd.to_datetime(start_date, errors="coerce")]
            if end_date and end_date != "Any":
                df = df[s <= pd.to_datetime(end_date, errors="coerce")]

    return df
