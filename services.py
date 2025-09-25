###
# File: services.py
# Description: Core service functions for PCP project data access and transformation.
###

from typing import Any, Dict, List, Tuple, Optional
import pandas as pd
from utils.dataframe_utils import CATEGORY_NAMES, extract_number, domain_overview
from json_handler import list_company_bundles, load_company_bundle
from api import get_internal_scan  # only for CMM/internal
from nist.nist_helpers import controls_for_finding


def get_company_category_scores_df(company_id) -> pd.DataFrame:
    # Function: get_company_category_scores_df
    # Description: Reads category scores and GPA from a company's bundle JSON file and returns them as a pandas DataFrame.
    # Usage: get_company_category_scores_df(company_id)
    # Returns: pandas DataFrame with category scores and GPA
    """Load company bundle JSON"""
    b = load_company_bundle(company_id) or {}
    rows = []
    """Extract category scores and GPA for each category"""
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
    """Create DataFrame from extracted rows"""
    out = pd.DataFrame(rows)
    if not out.empty and "category_score" in out.columns:
        out["category_score"] = pd.to_numeric(
            out["category_score"], errors="coerce"
        ).fillna(0)
    """Return DataFrame with category scores and GPA"""
    return out


# ------------------------------- Company & domain sources (JSON) --------------


def companies() -> List[Dict]:
    # Function: companies
    # Description: Loads company data for dashboard and company views from all company bundles.
    # Usage: companies()
    # Returns: List of company dicts
    bundles = list_company_bundles()
    out = []
    for b in bundles:
        row = {}
        c = b.get("company") or {}
        row.update(c)
        row["company_id"] = b.get("company_id") or c.get("company_id") or c.get("id")
        row["id"] = row["company_id"]
        row["company_name"] = (
            c.get("company_name") or c.get("name") or f"Company {row['company_id']}"
        )
        out.append(row)
    return out


def domains() -> List[Dict]:
    # Function: domains
    # Description: Loads domain data for dashboard and domain views from all company bundles.
    # Usage: domains()
    # Returns: List of domain dicts
    bundles = list_company_bundles()
    out = []
    for b in bundles:
        cid = b.get("company_id")
        for d in b.get("domains") or []:
            row = dict(d)
            row["company_id"] = cid
            out.append(row)
    return out


# ------------------------------- Company select options -----------------------


def list_company_options(cs: List[Dict]) -> Tuple[List[str], Dict[str, Any]]:
    # Function: list_company_options
    # Description: Creates a list of company options for selection dropdown and a mapping from label to company_id.
    # Usage: list_company_options(cs)
    # Returns: tuple (list of option labels, mapping from label to company_id)
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
    # Function: filter_domains_for_company
    # Description: Filters domains for the selected company.
    # Usage: filter_domains_for_company(ds, company_id)
    # Returns: list of domain dicts for the company
    sid = None if company_id is None else str(company_id)

    def _cid(d):
        return d.get("company_id") or d.get("companyId") or d.get("cid")

    return [d for d in ds if (None if _cid(d) is None else str(_cid(d))) == sid]


# ------------------------------- Company summary (KPIs) -----------------------


def company_summary(company_id: Any) -> Dict[str, str]:
    # Function: company_summary
    # Description: Returns summary KPIs (grade, total GPA, calculated date) for a company.
    # Usage: company_summary(company_id)
    # Returns: dict with grade, total_gpa, calculated_date
    out = {"grade": "—", "total_gpa": "—", "calculated_date": "—"}
    b = load_company_bundle(company_id) or {}
    rg = b.get("risk_grade") or {}
    if rg:
        if rg.get("grade"):
            out["grade"] = str(rg["grade"])
        if rg.get("total_gpa") is not None:
            try:
                out["total_gpa"] = f"{float(rg['total_gpa']):.2f}"
            except Exception:
                pass
        if rg.get("calculated_date"):
            out["calculated_date"] = str(rg["calculated_date"])
    if out["total_gpa"] == "—":
        gpas = []
        for cat in b.get("categories") or []:
            v = cat.get("category_gpa")
            try:
                if v is not None:
                    gpas.append(float(v))
            except Exception:
                pass
        if gpas:
            out["total_gpa"] = f"{sum(gpas) / len(gpas):.2f}"
    return out


# ------------------------------- Domain overview ------------------------------

# domain_overview is now imported from utils.dataframe_utils

# ------------------------------- Domain filters (original UX) -----------------


def _pluck_first(d: Dict, keys: List[str]) -> Optional[str]:
    # Function: _pluck_first
    # Description: Returns the first non-empty value for any key in keys from dict d.
    # Usage: _pluck_first(d, keys)
    # Returns: str or None
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return str(d[k])
    return None


def get_domain_filter_options_original(findings: List[Dict]):
    # Function: get_domain_filter_options_original
    # Description: Collects unique filter options (IP, Type, Level, Date) from findings.
    # Usage: get_domain_filter_options_original(findings)
    # Returns: tuple (dict of options, list of original column names)
    ips, types, levels, dates = set(), set(), set(), set()
    for r in findings or []:
        ip = _pluck_first(r, ["ip_address", "ip", "address"])
        ftype = _pluck_first(r, ["finding_type", "type"])
        lvl = _pluck_first(r, ["severity_level", "severity", "level"])
        dt = _pluck_first(r, ["date", "found_date", "scan_date"])
        if ip:
            ips.add(ip)
        if ftype:
            types.add(ftype)
        if lvl:
            levels.add(lvl)
        if dt:
            dates.add(dt)
    opts = {
        "ips": sorted(ips),
        "types": sorted(types),
        "levels": sorted(levels),
        "dates": sorted(dates),
    }
    orig_cols = ["ip_address", "finding_type", "severity_level", "date"]
    return opts, orig_cols


def _date_ok(v: Optional[str], start: Optional[str], end: Optional[str]) -> bool:
    # Function: _date_ok
    # Description: Checks if a date value is within the start and end date range.
    # Usage: _date_ok(v, start, end)
    # Returns: bool
    if not v:
        return True
    try:
        vv = pd.to_datetime(v, errors="coerce")
    except Exception:
        return True
    if isinstance(start, str) and start != "Any":
        ss = pd.to_datetime(start, errors="coerce")
        if pd.notna(ss) and pd.notna(vv) and vv < ss:
            return False
    if isinstance(end, str) and end != "Any":
        ee = pd.to_datetime(end, errors="coerce")
        if pd.notna(ee) and pd.notna(vv) and vv > ee:
            return False
    return True


def filter_domain_findings_original(
    findings: List[Dict],
    ip: str = "All",
    ftype: str = "All",
    level: str = "All",
    start_date: str = "Any",
    end_date: str = "Any",
) -> List[Dict]:
    # Function: filter_domain_findings_original
    # Description: Filters findings by IP, type, level, and date range for domain tab.
    # Usage: filter_domain_findings_original(findings, ip, ftype, level, start_date, end_date)
    # Returns: list of filtered findings
    out = []
    for r in findings or []:
        ip_ok = (ip == "All") or (r.get("ip_address") == ip or r.get("ip") == ip)
        type_ok = (ftype == "All") or (
            r.get("finding_type") == ftype or r.get("type") == ftype
        )
        lvl_ok = (level == "All") or (
            r.get("severity_level") == level
            or r.get("severity") == level
            or r.get("level") == level
        )
        dt_val = r.get("date") or r.get("found_date") or r.get("scan_date")
        if ip_ok and type_ok and lvl_ok and _date_ok(dt_val, start_date, end_date):
            out.append(r)
    return out


__all__ = [
    "get_company_category_scores_df",
    "companies",
    "domains",
    "list_company_options",
    "filter_domains_for_company",
    "company_summary",
    "build_external_finding_gpa_cmm",
    "to_external_findings_long",
]


def build_external_finding_gpa_cmm(
    scores_df: pd.DataFrame, internal_rows: list
) -> pd.DataFrame:
    # Compose GPA and CMM per external finding
    # scores_df: must have ['Category', 'category_gpa']
    # internal_rows: must have control_ref and cmm_rating (etc.)
    gpa_map = {
        str(row["Category"]): row.get("category_gpa", None)
        for _, row in scores_df.iterrows()
    }
    cmm_map = {}
    control_map = {}
    df_ctrl = pd.DataFrame(internal_rows or [])
    if not df_ctrl.empty:
        ctrl_col = None
        for c in df_ctrl.columns:
            if c.lower() in [
                "control_ref",
                "control_reference",
                "control",
                "ref",
                "nist_control",
            ]:
                ctrl_col = c
                break
        if ctrl_col:
            df_ctrl["control_ref_norm"] = df_ctrl[ctrl_col].astype(str)
            df_ctrl["rating_val"] = pd.to_numeric(
                df_ctrl.get("cmm_rating", df_ctrl.get("rating", None)), errors="coerce"
            )
            for finding in gpa_map.keys():
                refs = controls_for_finding(finding)
                vals = (
                    df_ctrl[df_ctrl["control_ref_norm"].isin(refs)]["rating_val"]
                    .dropna()
                    .tolist()
                )
                cmm_map[finding] = sum(vals) / len(vals) if vals else None
                control_map[finding] = ", ".join(refs)
        else:
            for finding in gpa_map.keys():
                cmm_map[finding] = None
                control_map[finding] = ""
    else:
        for finding in gpa_map.keys():
            cmm_map[finding] = None
            control_map[finding] = ""
    out = pd.DataFrame(
        {
            "external_finding": list(gpa_map.keys()),
            "category": list(gpa_map.keys()),
            "gpa": [gpa_map[k] for k in gpa_map.keys()],
            "cmm_score": [cmm_map[k] for k in gpa_map.keys()],
            "control_refs": [control_map[k] for k in gpa_map.keys()],
        }
    )
    return out


def to_external_findings_long(df: pd.DataFrame) -> pd.DataFrame:
    long_df = df.melt(
        id_vars=["external_finding", "category", "control_refs"],
        value_vars=["gpa", "cmm_score"],
        var_name="metric",
        value_name="score",
    )
    long_df["metric"] = long_df["metric"].map({"gpa": "GPA", "cmm_score": "CMM"})
    return long_df
