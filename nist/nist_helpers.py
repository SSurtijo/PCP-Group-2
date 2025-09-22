###
# File: nist/nist_helpers.py
# Description: Helper functions for NIST CSF mappings in PCP project.
###

from __future__ import annotations
from typing import Iterable

from .nist_mappings import (
    CSF_L1_FUNCTION_FULL,
    FUNCTION_L1_IDENTIFIER_TO_FUNCTION_L2,
    FUNCTION_L2_TO_CONTROLS,
    EXTERNAL_FINDINGS_TO_CONTROLS,
)
from utils.normalization import norm_ref, prefix


def controls_for_l2(l2_name: str) -> list[str]:
    # Function: controls_for_l2
    # Description: Returns normalized control references for a given L2 domain name.
    # Usage: controls_for_l2(l2_name)
    # Returns: list of normalized control refs
    return [norm_ref(c) for c in FUNCTION_L2_TO_CONTROLS.get(str(l2_name).strip(), [])]


def controls_for_finding(finding: str) -> list[str]:
    # Function: controls_for_finding
    # Description: Returns normalized control references for a given external finding.
    # Usage: controls_for_finding(finding)
    # Returns: list of normalized control refs
    return [
        norm_ref(c) for c in EXTERNAL_FINDINGS_TO_CONTROLS.get(str(finding).strip(), [])
    ]


def findings_for_prefix(prefix_str: str) -> list[str]:
    # Function: findings_for_prefix
    # Description: Returns findings mapped to a given control prefix.
    # Usage: findings_for_prefix(prefix_str)
    # Returns: sorted list of findings
    p = prefix(prefix_str)
    outs = []
    for finding, ctrls in EXTERNAL_FINDINGS_TO_CONTROLS.items():
        for c in ctrls:
            if prefix(norm_ref(c)) == p:
                outs.append(finding)
                break
    return sorted(set(outs))


def findings_for_l2(l2_name: str) -> list[str]:
    # Function: findings_for_l2
    # Description: Returns findings mapped to a given L2 domain name.
    # Usage: findings_for_l2(l2_name)
    # Returns: sorted list of findings
    fs = set()
    for c in controls_for_l2(l2_name):
        fs.update(findings_for_prefix(c))
    return sorted(fs)


def prefixes_for_l2(l2_name: str) -> list[str]:
    # Function: prefixes_for_l2
    # Description: Returns sorted list of prefixes for a given L2 domain name.
    # Usage: prefixes_for_l2(l2_name)
    # Returns: sorted list of prefixes
    return sorted({prefix(c) for c in controls_for_l2(l2_name)})


def get_function_from_code_or_ref(ref: str) -> str:
    # Function: get_function_from_code_or_ref
    # Description: Returns the CSF L1 function code (e.g. GV/ID/PR) for a control ref.
    # Usage: get_function_from_code_or_ref(ref)
    # Returns: str function code
    normalized = norm_ref(ref)
    if not normalized:
        return ""

    head = normalized.split(".", 1)[0]
    if head in CSF_L1_FUNCTION_FULL:
        return head

    prefix_head = prefix(normalized).split(".")[0] if prefix(normalized) else ""
    if prefix_head in CSF_L1_FUNCTION_FULL:
        return prefix_head

    for fn_code in CSF_L1_FUNCTION_FULL:
        if normalized.startswith(fn_code):
            return fn_code

    return normalized.split(".", 1)[0]


# Back-compat / simple external->controls view used by charts
def build_category_to_csf() -> dict[str, list[str]]:
    # Function: build_category_to_csf
    # Description: Builds mapping from external finding to normalized control identifiers.
    # Usage: build_category_to_csf()
    # Returns: dict mapping finding to list of controls
    return {k: controls_for_finding(k) for k in EXTERNAL_FINDINGS_TO_CONTROLS.keys()}


CATEGORY_TO_CSF = build_category_to_csf()


def summarize_csf_for_category(category: str) -> dict:
    # Function: summarize_csf_for_category
    # Description: Returns a dict with joined NIST CSF identifiers for the external finding.
    # Usage: summarize_csf_for_category(category)
    # Returns: dict with nist_csf_identifiers (str)
    cat = str(category).strip()
    fids = EXTERNAL_FINDINGS_TO_CONTROLS.get(cat, [])
    return {"nist_csf_identifiers": ", ".join(fids)}


def get_functions_for_category(
    category: str, return_kind: str = "identifiers"
) -> list[str]:
    # Function: get_functions_for_category
    # Description: Returns L1 identifiers or L2 names for the external finding.
    # Usage: get_functions_for_category(category, return_kind)
    # Returns: list of identifiers or names
    ids = EXTERNAL_FINDINGS_TO_CONTROLS.get(str(category).strip(), [])
    if return_kind == "names":
        return [FUNCTION_L1_IDENTIFIER_TO_FUNCTION_L2.get(fid, fid) for fid in ids]
    return list(ids)
