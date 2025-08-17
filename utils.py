# utils.py
import os, requests
from typing import Any, Dict, List, Union
from urllib.parse import quote

RISK_API_BASE = os.getenv(
    "RISK_API_BASE",
    "https://abfzxwlwbqbrsdd-dev.adb.ap-sydney-1.oraclecloudapps.com/ords/uws_project/riskapi",
).rstrip("/")


class RiskAPIError(RuntimeError):
    pass


_session = requests.Session()


def _request(url: str) -> Any:
    r = _session.get(url, timeout=20, headers={"Accept": "application/json"})
    try:
        r.raise_for_status()
    except requests.HTTPError:
        raise RiskAPIError(
            f"Request failed: {r.status_code} {r.reason} — {url}\n{r.text[:800]}"
        )
    # Prefer JSON; tolerate bare numeric bodies (e.g., "5.33")
    try:
        return r.json()
    except ValueError:
        txt = (r.text or "").strip()
        try:
            return float(txt)
        except Exception:
            raise RiskAPIError(f"Response was not valid JSON — {url}\n{txt[:800]}")


def _get(path: str) -> Any:
    """Call URL; on failure, toggle trailing slash and retry once."""
    path = path if path.startswith("/") else "/" + path
    url = f"{RISK_API_BASE}{path}"
    try:
        return _request(url)
    except RiskAPIError:
        alt = url[:-1] if url.endswith("/") else url + "/"
        if alt != url:
            return _request(alt)
        raise


def _items(data: Union[Dict[str, Any], List[Any]]) -> Any:
    return data.get("items", data) if isinstance(data, dict) else data


# ---------- Endpoints ----------
def get_companies() -> List[Dict[str, Any]]:
    # (no trailing slash)
    return _items(_get("/get_companies"))


def get_domains() -> List[Dict[str, Any]]:
    # (no trailing slash)
    return _items(_get("/get_domains"))


def get_company_risk_grade(company_id: int) -> Dict[str, Any]:
    # requires trailing slash
    return _get(f"/get_company_risk_grade/{company_id}/")


def get_domain_score(domain_id: int) -> Any:
    # requires trailing slash (may return a bare number)
    return _get(f"/get_domain_score/{domain_id}/")


def get_category_gpa(company_id: int, category_name: str) -> Any:
    # requires trailing slash
    return _items(
        _get(f"/get_category_gpa/{company_id}/{quote(category_name, safe='')}/")
    )


def get_findings_by_category(domain_id: int, category_name: str) -> Any:
    # requires trailing slash
    return _items(
        _get(f"/get_findings_by_category/{domain_id}/{quote(category_name, safe='')}/")
    )
