# services.py
# -----------------------------------------------------------------------------
# Service layer — bridges API responses and the UI.
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


# ------------------------------- Basic pass-through fetchers ------------------
def companies() -> List[Dict]:
    return get_companies()


def domains() -> List[Dict]:
    return get_domains()


# ------------------------------- Company select options -----------------------
def list_company_options(cs: List[Dict]) -> Tuple[List[str], Dict[str, Any]]:
    opts, map_ = [], {}
    for c in cs:
        cid = c.get("company_id") or c.get("id")
        name = c.get("company_name") or c.get("name") or f"Company {cid}"
        label = f"{cid} — {name}" if cid is not None else name
        opts.append(label)
        map_[label] = cid
    return opts, map_


# ------------------------------- Filter domains by company --------------------
def filter_domains_for_company(ds: List[Dict], company_id: Any) -> List[Dict]:
    sid = None if company_id is None else str(company_id)

    def _cid(d):
        return d.get("company_id") or d.get("companyId") or d.get("cid")

    return [d for d in ds if (None if _cid(d) is None else str(_cid(d))) == sid]


# ------------------------------- Company summary (KPIs) -----------------------
def company_summary(company_id: Any) -> Dict[str, str]:
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
        pass

    # Fallback: average per-category GPAs if total_gpa missing
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


# ------------------------------- Domain overview ------------------------------
def domain_overview(domain_id: Any) -> Tuple[Optional[float], List[Dict]]:
    score = None
    try:
        score = extract_number(get_domain_score(domain_id))
    except Exception:
        pass

    findings: List[Dict] = []
    for cat in CATEGORY_NAMES:
        try:
            data = get_findings_by_category(domain_id, cat)
            rows = (
                data
                if isinstance(data, list)
                else (
                    data.get("findings", [])
                    if isinstance(data, dict) and isinstance(data.get("findings"), list)
                    else ([data] if isinstance(data, dict) and data else [])
                )
            )
            for r in rows:
                if isinstance(r, dict):
                    r.pop("Category", None)
            findings.extend([r for r in rows if isinstance(r, dict)])
        except Exception:
            pass

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


# ------------------------------- Original-table filters -----------------------
def _resolve_domain_cols(df: pd.DataFrame) -> Dict[str, Optional[str]]:
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
    try:
        return pd.to_datetime(s, errors="coerce", utc=False)
    except Exception:
        return pd.to_datetime(pd.Series([], dtype=object))


def get_domain_filter_options_original(
    findings: List[Dict],
) -> Tuple[Dict[str, list], list]:
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
            s = _as_dt(df[cols["fdate"]])
            if start_date and start_date != "Any":
                df = df[s >= pd.to_datetime(start_date, errors="coerce")]
            if end_date and end_date != "Any":
                df = df[s <= pd.to_datetime(end_date, errors="coerce")]

    return df
