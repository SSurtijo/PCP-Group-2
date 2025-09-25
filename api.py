###
# File: api.py
# Description: API layer for PCP project. Handles external and internal data requests.
###

import os
import requests
from typing import Any, Dict, List, Union
from urllib.parse import quote

BASE = os.getenv(
    "RISK_API_BASE",
    "https://abfzxwlwbqbrsdd-dev.adb.ap-sydney-1.oraclecloudapps.com/ords/uws_project/riskapi",
).rstrip("/")
_session = requests.Session()


def _request(url: str) -> Any:
    # Function: _request
    # Description: Core GET request for API endpoints.
    # Usage: _request(url)
    # Returns: JSON, float, or raises error
    """Send GET request to API endpoint"""
    r = _session.get(url, timeout=20, headers={"Accept": "application/json"})
    r.raise_for_status()
    try:
        """Try to parse JSON response"""
        return r.json()
    except ValueError:
        t = (r.text or "").strip()
        try:
            """Try to parse as float if not JSON"""
            return float(t)
        except Exception:
            raise RuntimeError(f"Non-JSON response from {url}\n{t[:800]}")


def _get(path: str) -> Any:
    # Function: _get
    # Description: Build the full URL and fetch it. Retries on trailing slash mismatch.
    # Usage: _get(path)
    # Returns: API response
    """Build full API URL"""
    url = f"{BASE}{path if path.startswith('/') else '/'+path}"
    try:
        """Request URL"""
        return _request(url)
    except Exception:
        alt = url[:-1] if url.endswith("/") else url + "/"
        if alt != url:
            """Try alternate URL with/without trailing slash"""
            return _request(alt)
        raise


def _items(x: Union[Dict, List]) -> Any:
    # Function: _items
    # Description: Returns the 'items' list from ORDS endpoints if present, else original object.
    # Usage: _items(x)
    # Returns: list or original object
    """Return 'items' list if present, else original object"""
    return x.get("items", x) if isinstance(x, dict) else x


# -----------------------
# Public API Endpoints
# -----------------------
def get_companies() -> List[Dict]:
    # Function: get_companies
    # Description: Fetches companies from external API.
    # Usage: get_companies()
    # Returns: list of company dicts
    return _items(_get("/get_companies"))


def get_domains() -> List[Dict]:
    # Function: get_domains
    # Description: Fetches domains from external API.
    # Usage: get_domains()
    # Returns: list of domain dicts
    return _items(_get("/get_domains"))


def get_category_gpa(company_id: int, name: str) -> Any:
    # Function: get_category_gpa
    # Description: Fetches category GPA for a company from API.
    # Usage: get_category_gpa(company_id, name)
    # Returns: GPA value or list
    return _items(_get(f"/get_category_gpa/{company_id}/{quote(name, safe='')}/"))


def get_company_risk_grade(company_id: int) -> Dict:
    # Function: get_company_risk_grade
    # Description: Fetches risk grade for a company from API.
    # Usage: get_company_risk_grade(company_id)
    # Returns: dict with risk grade info
    return _get(f"/get_company_risk_grade/{company_id}/")


def get_domain_score(domain_id: int) -> Any:
    # Function: get_domain_score
    # Description: Fetches domain score from API.
    # Usage: get_domain_score(domain_id)
    # Returns: score value
    return _get(f"/get_domain_score/{domain_id}/")


def get_findings_by_category(domain_id: int, name: str) -> Any:
    # Function: get_findings_by_category
    # Description: Fetches findings by category for a domain from API.
    # Usage: get_findings_by_category(domain_id, name)
    # Returns: findings list or value
    return _items(
        _get(f"/get_findings_by_category/{domain_id}/{quote(name, safe='')}/")
    )


def get_internal_scan(limit: int = 200):
    # Function: get_internal_scan
    # Description: Fetches internal scan ratings (CMM) from API.
    # Usage: get_internal_scan(limit)
    # Returns: list of ratings
    url = (
        "https://abfzxwlwbqbrsdd-dev.adb.ap-sydney-1.oraclecloudapps.com/"
        f"ords/dev/cmm_ratings_stub/?limit={limit}"
    )
    r = _session.get(url, timeout=20, headers={"Accept": "application/json"})
    r.raise_for_status()
    payload = r.json()
    return payload.get("items", payload) if isinstance(payload, dict) else payload


# -----------------------
# Optional: trigger bundle rebuild from API layer
# -----------------------
def rebuild_all_company_jsons() -> int:
    # Function: rebuild_all_company_jsons
    # Description: Triggers bundle rebuild from API layer.
    # Usage: rebuild_all_company_jsons()
    # Returns: int (number of bundles rebuilt)
    try:
        from json_handler import build_all_company_bundles

        paths = build_all_company_bundles()
        return len(paths or [])
    except Exception:
        return 0
