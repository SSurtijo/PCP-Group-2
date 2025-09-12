# api.py

import os
import requests
from typing import Any, Dict, List, Union
from urllib.parse import quote

# Base URL can be overridden with the env var RISK_API_BASE
BASE = os.getenv(
    "RISK_API_BASE",
    "https://abfzxwlwbqbrsdd-dev.adb.ap-sydney-1.oraclecloudapps.com/ords/uws_project/riskapi",
).rstrip("/")

# Use a Session for connection pooling (more efficient than raw requests.get)
_session = requests.Session()


def _request(url: str) -> Any:
    """
    Core GET request:
    - Raises on non-2xx status codes
    - Returns JSON if possible
    - If body is not JSON, try to parse as a float (some endpoints return numbers)
    """
    r = _session.get(url, timeout=20, headers={"Accept": "application/json"})
    r.raise_for_status()
    try:
        return r.json()
    except ValueError:
        t = (r.text or "").strip()
        try:
            return float(t)
        except Exception:
            raise RuntimeError(f"Non-JSON response from {url}\n{t[:800]}")


def _get(path: str) -> Any:
    """
    Build the full URL and fetch it.
    If it fails due to trailing slash mis-match, flip and retry once.
    """
    url = f"{BASE}{path if path.startswith('/') else '/'+path}"
    try:
        return _request(url)
    except Exception:
        alt = url[:-1] if url.endswith("/") else url + "/"
        if alt != url:
            return _request(alt)
        raise


def _items(x: Union[Dict, List]) -> Any:
    """
    Many ORDS endpoints wrap results inside {"items": [...] }.
    This helper returns the 'items' list if present, otherwise the original object.
    """
    return x.get("items", x) if isinstance(x, dict) else x


# -----------------------
# Public API Endpoints
# -----------------------
def get_companies() -> List[Dict]:
    """GET /get_companies → list of company dicts."""
    return _items(_get("/get_companies"))


def get_domains() -> List[Dict]:
    """GET /get_domains → list of domain dicts."""
    return _items(_get("/get_domains"))


def get_category_gpa(company_id: int, name: str) -> Any:
    """
    GET /get_category_gpa/{company_id}/{category}/
    - Often returns an object or list with GPA fields.
    - We normalize the wrapper via _items.
    """
    return _items(_get(f"/get_category_gpa/{company_id}/{quote(name, safe='')}/"))


def get_company_risk_grade(company_id: int) -> Dict:
    """GET /get_company_risk_grade/{company_id}/ → object with grade/total_gpa/date."""
    return _get(f"/get_company_risk_grade/{company_id}/")


def get_domain_score(domain_id: int) -> Any:
    """GET /get_domain_score/{domain_id}/ → may be JSON or a bare number (float)."""
    return _get(f"/get_domain_score/{domain_id}/")


def get_findings_by_category(domain_id: int, name: str) -> Any:
    """
    GET /get_findings_by_category/{domain_id}/{category}/
    - Result varies by category; may be list or dict with 'findings' list.
    """
    return _items(
        _get(f"/get_findings_by_category/{domain_id}/{quote(name, safe='')}/")
    )


def get_internal_scan(limit: int = 200):
    """
    Fetch the 'Internal Scan' data (actually comes from the CMM ratings stub).
    Returns a list of dicts (unwraps {"items": [...]} if present).
    """
    url = (
        "https://abfzxwlwbqbrsdd-dev.adb.ap-sydney-1.oraclecloudapps.com/"
        f"ords/dev/cmm_ratings_stub/?limit={limit}"
    )

    r = _session.get(url, timeout=20, headers={"Accept": "application/json"})
    r.raise_for_status()

    payload = r.json()
    return payload.get("items", payload) if isinstance(payload, dict) else payload
