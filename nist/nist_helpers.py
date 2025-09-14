"""
NIST CSF Helper Functions
All summarization, validation, and lookups.
"""

from .nist_mappings import (
    FUNCTION_IDENTIFIER_TO_FUNCTION,
    FUNCTION_TO_CONTROLS,
    CATEGORY_TO_FUNCTION_IDENTIFIERS,
    CSF_FUNCTION_FULL,
)


def _function_name_from_identifier(fid: str) -> str | None:
    return FUNCTION_IDENTIFIER_TO_FUNCTION.get(str(fid).strip().upper())


def _controls_from_function_name(fname: str) -> list[str]:
    return list(FUNCTION_TO_CONTROLS.get(str(fname).strip(), []))


def build_category_to_controls() -> dict[str, list[str]]:
    """
    Category → Function Identifiers → Function Names → Controls
    """
    out: dict[str, list[str]] = {}
    for cat, idents in CATEGORY_TO_FUNCTION_IDENTIFIERS.items():
        controls: list[str] = []
        for fid in idents:
            fname = _function_name_from_identifier(fid)
            if not fname:
                continue
            controls.extend(_controls_from_function_name(fname))
        out[cat] = sorted(set(controls))
    return out


# Derived
CATEGORY_TO_CONTROLS = build_category_to_controls()
CATEGORY_TO_CSF = CATEGORY_TO_CONTROLS  # back-compat alias


def get_functions_for_category(
    category: str, return_kind: str = "identifiers"
) -> list[str]:
    ids = CATEGORY_TO_FUNCTION_IDENTIFIERS.get(str(category).strip(), [])
    if return_kind == "names":
        return [FUNCTION_IDENTIFIER_TO_FUNCTION.get(fid, fid) for fid in ids]
    return list(ids)


def get_function_from_code_or_ref(s: str) -> str:
    """Return CSF function code from a control or GV ref."""
    if not s:
        return ""
    s = str(s).strip()
    if "." in s and len(s.split(".", 1)[0]) == 2:
        return s.split(".", 1)[0].upper()
    if s.upper().startswith("GV."):
        return "GV"
    prefix = s[:2].upper()
    return prefix if prefix in {"GV", "ID", "PR", "DE", "RS", "RC"} else ""


def summarize_csf_for_category(category: str) -> dict:
    """
    Return NIST CSF identifiers for a given category, joined string.
    """
    cat = str(category).strip()
    fids = CATEGORY_TO_FUNCTION_IDENTIFIERS.get(cat, [])
    return {"nist_csf_identifiers": ", ".join(fids)}
