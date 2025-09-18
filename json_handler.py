# json_handler.py
# -----------------------------------------------------------------------------
# Disk-backed company bundles:
# - One JSON per company at data/{company_id}_data.json
# - Views read these bundles (except CMM/internal which stays live)
# - You can call build_company_bundle(...) yourself wherever you prefer.
# -----------------------------------------------------------------------------

from __future__ import annotations
import os
import json
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from helpers import CATEGORY_NAMES
from api import (
    get_companies,
    get_domains,
    get_company_risk_grade,
    get_category_gpa,
    get_domain_score,
    get_findings_by_category,
)

DATA_ROOT = os.getenv("DATA_DIR", "data")


# --------------------------- small fs helpers --------------------------------
def _ensure_dir():
    os.makedirs(DATA_ROOT, exist_ok=True)


def _atomic_write_json(path: str, data: dict):
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=d, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def _strip_transport(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            kl = str(k).lower()
            if kl in ("href", "links", "link", "rel"):
                continue
            out[k] = _strip_transport(v)
        return out
    if isinstance(obj, list):
        return [_strip_transport(x) for x in obj]
    return obj


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------- bundle build/load --------------------------------
def company_bundle_path(company_id: Any) -> str:
    """data/{company_id}_data.json"""
    return os.path.join(DATA_ROOT, f"{company_id}_data.json")


def load_company_bundle(company_id: Any) -> dict:
    path = company_bundle_path(company_id)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def list_company_bundles() -> List[dict]:
    _ensure_dir()
    out = []
    try:
        for name in sorted(os.listdir(DATA_ROOT)):
            if not name.endswith("_data.json"):
                continue
            full = os.path.join(DATA_ROOT, name)
            if not os.path.isfile(full):
                continue
            try:
                with open(full, "r", encoding="utf-8") as f:
                    out.append(json.load(f))
            except Exception:
                pass
    except FileNotFoundError:
        pass
    return out


def write_company_bundle(company_id: Any, bundle: dict):
    _ensure_dir()
    _atomic_write_json(company_bundle_path(company_id), bundle)


def build_company_bundle(company: dict, all_domains: List[dict]) -> dict:
    """
    Build a canonical bundle for a single company using live API data.
    Includes: company record, risk grade, all category GPAs/scores,
    company domains, per-domain score, and findings per category.
    """
    cid = company.get("company_id") or company.get("id")
    if cid is None:
        raise ValueError("Company has no ID")

    # 1) company record (stripped)
    company_clean = _strip_transport(company)

    # 2) risk grade
    risk_grade = _strip_transport(get_company_risk_grade(cid) or {})

    # 3) category GPAs/scores
    categories = []
    for cat in CATEGORY_NAMES:
        payload = get_category_gpa(cid, cat)
        row = payload[0] if isinstance(payload, list) and payload else payload
        if not isinstance(row, dict):
            row = {"Category": cat, "category_gpa": None, "category_score": None}
        c_name = row.get("Category") or row.get("category") or cat
        gpa = row.get("category_gpa") or row.get("gpa") or row.get("value")
        score = row.get("category_score") or row.get("score")
        aggregated_at = row.get("aggregated_at") or row.get("date") or None
        try:
            gpa = float(gpa) if gpa is not None else None
        except Exception:
            gpa = None
        try:
            score = float(score) if score is not None else None
        except Exception:
            score = None
        categories.append(
            {
                "Category": c_name,
                "category_gpa": gpa,
                "category_score": score,
                "aggregated_at": aggregated_at,
            }
        )

    # 4) filter all domains to this company
    sid = str(cid)

    def _dcid(d):  # flexible key
        return d.get("company_id") or d.get("companyId") or d.get("cid")

    domains_for_company = [d for d in (all_domains or []) if str(_dcid(d)) == sid]
    domains_for_company = _strip_transport(domains_for_company)

    # 5) per-domain score + findings by category
    domain_details = []
    for d in domains_for_company:
        did = d.get("domain_id") or d.get("id") or d.get("domainId")
        dname = d.get("domain_name") or d.get("domain") or d.get("name")
        try:
            dscore = get_domain_score(did)
        except Exception:
            dscore = None
        try:
            dscore = float(dscore) if dscore is not None else None
        except Exception:
            dscore = None

        per_cat = {}
        for cat in CATEGORY_NAMES:
            raw = get_findings_by_category(did, cat)
            if isinstance(raw, dict) and isinstance(raw.get("findings"), list):
                rows = raw.get("findings", [])
            elif isinstance(raw, list):
                rows = raw
            elif isinstance(raw, dict) and raw:
                rows = [raw]
            else:
                rows = []
            rows = [r for r in rows if isinstance(r, dict)]
            for r in rows:
                r.pop("Category", None)  # avoid duplication
            per_cat[cat] = _strip_transport(rows)

        domain_details.append(
            {
                "domain_id": did,
                "domain_name": dname,
                "domain_score": dscore,
                "findings_by_category": per_cat,
            }
        )

    bundle = {
        "schema_version": 1,
        "generated_at": _now_iso(),
        "company_id": cid,
        "company": company_clean,
        "risk_grade": risk_grade,
        "categories": categories,
        "domains": domain_details,
    }
    return bundle


# --- Bulk / convenience builders ---------------------------------------------


def build_all_company_bundles() -> list[str]:
    """
    Build/refresh one JSON per company into data/{company_id}_data.json
    using the live API. Returns list of written file paths.
    """
    _ensure_dir()
    cs = get_companies() or []
    all_domains = get_domains() or []
    written = []
    for c in cs:
        cid = c.get("company_id") or c.get("id")
        if cid is None:
            continue
        bundle = build_company_bundle(c, all_domains)
        write_company_bundle(cid, bundle)
        written.append(company_bundle_path(cid))
    return written


def ensure_initial_bundles() -> int:
    """
    If data/ has no *"_data.json" files, build them all once.
    Returns the number of bundles on disk after the call.
    """
    existing = list_company_bundles()
    if existing:
        return len(existing)
    written = build_all_company_bundles()
    return len(written)


def rebuild_company_bundle_for_id(company_id: int | str) -> str | None:
    """
    Rebuild a single company's JSON bundle from the live API.
    Returns the path written, or None if the company isn't found.
    """
    cs = get_companies() or []
    all_domains = get_domains() or []
    for c in cs:
        cid = c.get("company_id") or c.get("id")
        if str(cid) == str(company_id):
            bundle = build_company_bundle(c, all_domains)
            write_company_bundle(cid, bundle)
            return company_bundle_path(cid)
    return None


def ensure_missing_bundles() -> int:
    """
    Build bundles only for companies that don't yet have data/{id}_data.json.
    Returns how many new files were written.
    """
    _ensure_dir()
    existing_ids = set()
    for name in os.listdir(DATA_ROOT):
        if name.endswith("_data.json"):
            try:
                existing_ids.add(name.split("_data.json")[0])
            except Exception:
                pass

    cs = get_companies() or []
    all_domains = get_domains() or []
    written = 0
    for c in cs:
        cid = c.get("company_id") or c.get("id")
        if cid is None:
            continue
        if str(cid) in existing_ids:
            continue
        bundle = build_company_bundle(c, all_domains)
        write_company_bundle(cid, bundle)
        written += 1
    return written


def refresh_stale_bundles(ttl_hours: int = 24) -> int:
    """
    Rebuild bundles whose files are older than ttl_hours.
    Returns how many files were refreshed.
    """
    _ensure_dir()
    cutoff = time.time() - ttl_hours * 3600
    cs = get_companies() or []
    # index companies by id for quick access
    by_id = {str(c.get("company_id") or c.get("id")): c for c in cs}
    all_domains = get_domains() or []

    refreshed = 0
    for name in os.listdir(DATA_ROOT):
        if not name.endswith("_data.json"):
            continue
        cid = name.split("_data.json")[0]
        fpath = os.path.join(DATA_ROOT, name)
        try:
            mtime = os.path.getmtime(fpath)
        except Exception:
            mtime = 0
        if mtime >= cutoff:
            continue  # fresh enough
        comp = by_id.get(str(cid))
        if not comp:
            continue  # company no longer exists
        bundle = build_company_bundle(comp, all_domains)
        write_company_bundle(cid, bundle)
        refreshed += 1
    return refreshed
