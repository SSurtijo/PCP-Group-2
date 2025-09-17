# services.py
# -----------------------------------------------------------------------------
# Service layer — JSON-first (bundles), CMM/internal stays live. + Domain filters.
# -----------------------------------------------------------------------------
from typing import Any, Dict, List, Tuple, Optional
import pandas as pd

from helpers import CATEGORY_NAMES, extract_number
from json_handler import list_company_bundles, load_company_bundle
from api import get_internal_scan  # only for CMM/internal


# ------------------------------- Company & domain sources (JSON) --------------
def companies() -> List[Dict]:
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
    bundles = list_company_bundles()
    out = []
    for b in bundles:
        cid = b.get("company_id")
        for d in b.get("domains") or []:
            row = dict(d)  # domain_id, domain_name, domain_score, findings_by_category
            row["company_id"] = cid
            out.append(row)
    return out


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
def domain_overview(domain_id: Any) -> Tuple[Optional[float], List[Dict]]:
    bundles = list_company_bundles()
    for b in bundles:
        for d in b.get("domains") or []:
            did = d.get("domain_id") or d.get("id") or d.get("domainId")
            if str(did) != str(domain_id):
                continue

            score = d.get("domain_score")
            try:
                score = float(score) if score is not None else None
            except Exception:
                score = None

            findings: List[Dict] = []
            fbc = d.get("findings_by_category") or {}
            for _, rows in fbc.items():
                for r in rows or []:
                    if isinstance(r, dict):
                        rc = dict(r)
                        rc.pop("Category", None)
                        findings.append(rc)

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
    return None, []


# ------------------------------- Domain filters (original UX) -----------------
def _pluck_first(d: Dict, keys: List[str]) -> Optional[str]:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return str(d[k])
    return None


def get_domain_filter_options_original(findings: List[Dict]):
    """Collect unique values for IP / Type / Level / Date from findings."""
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
    import pandas as pd

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
