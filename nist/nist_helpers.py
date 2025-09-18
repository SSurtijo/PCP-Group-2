# nist/nist_helpers.py
from __future__ import annotations
from typing import Iterable

from .nist_mappings import (
    CSF_L1_FUNCTION_FULL,
    FUNCTION_L1_IDENTIFIER_TO_FUNCTION_L2,
    FUNCTION_L2_TO_CONTROLS,
    EXTERNAL_FINDINGS_TO_CONTROLS,
)


def _norm_ref(s: str) -> str:
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


def controls_for_l2(l2_name: str) -> list[str]:
    return [_norm_ref(c) for c in FUNCTION_L2_TO_CONTROLS.get(str(l2_name).strip(), [])]


def controls_for_finding(finding: str) -> list[str]:
    return [
        _norm_ref(c)
        for c in EXTERNAL_FINDINGS_TO_CONTROLS.get(str(finding).strip(), [])
    ]


def findings_for_prefix(prefix: str) -> list[str]:
    p = _prefix(prefix)
    outs = []
    for finding, ctrls in EXTERNAL_FINDINGS_TO_CONTROLS.items():
        for c in ctrls:
            if _prefix(_norm_ref(c)) == p:
                outs.append(finding)
                break
    return sorted(set(outs))


def findings_for_l2(l2_name: str) -> list[str]:
    fs = set()
    for c in controls_for_l2(l2_name):
        fs.update(findings_for_prefix(c))
    return sorted(fs)


def prefixes_for_l2(l2_name: str) -> list[str]:
    return sorted({_prefix(c) for c in controls_for_l2(l2_name)})


# Back-compat / simple external->controls view used by charts
def build_category_to_csf() -> dict[str, list[str]]:
    # For each external finding, return its mapped control identifiers (normalized)
    return {k: controls_for_finding(k) for k in EXTERNAL_FINDINGS_TO_CONTROLS.keys()}


CATEGORY_TO_CSF = build_category_to_csf()


def summarize_csf_for_category(category: str) -> dict:
    """
    Compatibility shim used by company_tab.py.
    Returns a dict with a joined string of NIST CSF identifiers for the external finding.
    """
    cat = str(category).strip()
    fids = EXTERNAL_FINDINGS_TO_CONTROLS.get(cat, [])
    return {"nist_csf_identifiers": ", ".join(fids)}


def get_functions_for_category(
    category: str, return_kind: str = "identifiers"
) -> list[str]:
    """
    If someone still calls this, return the L1 identifiers for the external finding.
    Set return_kind="names" to map to L2 names via FUNCTION_L1_IDENTIFIER_TO_FUNCTION_L2.
    """
    ids = EXTERNAL_FINDINGS_TO_CONTROLS.get(str(category).strip(), [])
    if return_kind == "names":
        return [FUNCTION_L1_IDENTIFIER_TO_FUNCTION_L2.get(fid, fid) for fid in ids]
    return list(ids)


def get_function_from_code_or_ref(code_or_ref: str) -> str:
    """
    Get the L1 function code from a control reference.
    For example: "GV.OC-02" -> "GV", "ID.AM-01" -> "ID"
    """
    if not code_or_ref:
        return ""

    # Normalize the reference
    ref = str(code_or_ref).upper().strip()

    # If it's already just a function code (e.g., "GV", "ID")
    if ref in CSF_L1_FUNCTION_FULL:
        return ref

    # Extract the L1 function code from a full reference
    # Handle both "GV.OC-02" and "GV.OC" formats
    if "." in ref:
        parts = ref.split(".")
        if parts[0] in CSF_L1_FUNCTION_FULL:
            return parts[0]

    # Try splitting by hyphen if dot didn't work
    if "-" in ref:
        prefix = ref.split("-")[0]
        if "." in prefix:
            func = prefix.split(".")[0]
            if func in CSF_L1_FUNCTION_FULL:
                return func

    return ""
