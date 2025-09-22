###
# File: utils/normalization.py
# Description: Utility functions for normalizing scores and extracting prefixes from control references.
###

from typing import Optional


def norm_ref(s: Optional[str]) -> str:
    # Function: norm_ref
    # Description: Normalizes control references to a standard format (e.g. PR-PS-1 → PR.PS-01).
    # Usage: norm_ref('PR-PS-1')
    # Returns: str - normalized control reference
    """Handle empty input"""
    if not s:
        return ""
    """ Convert input to uppercase string and remove leading/trailing spaces """
    s = str(s).upper().strip()
    """ If input contains a dash, split into prefix and tail """
    if "-" in s:
        prefix, tail = s.split("-", 1)
        """ Replace underscores and dashes in prefix with dots """
        prefix = prefix.replace("_", ".").replace("-", ".")
        """ Remove any double dots """
        while ".." in prefix:
            prefix = prefix.replace("..", ".")
        tail = tail.strip()
        """ If tail is a number, pad with zero if needed """
        if tail.isdigit():
            tail = tail.zfill(2)
        """ Return normalized format """
        return f"{prefix}-{tail}"
    """ If no dash, replace underscores/dashes with dots """
    s2 = s.replace("_", ".").replace("-", ".")
    """ Remove any double dots """
    while ".." in s2:
        s2 = s2.replace("..", ".")
    """ Split into parts by dot """
    parts = [p for p in s2.split(".") if p]
    """ If third part is a number, format accordingly """
    if len(parts) >= 3 and parts[2].isdigit():
        return f"{parts[0]}.{parts[1]}-{parts[2].zfill(2)}"
    """ Return original string if no formatting applied """
    return s


def prefix(x: Optional[str]) -> str:
    # Function: prefix
    # Description: Returns the prefix from a control reference (e.g. PR.PS-01 → PR.PS).
    # Usage: prefix('PR.PS-01')
    # Returns: str - prefix portion of control reference
    """Handle empty input"""
    if not x:
        return ""
    """ Convert input to uppercase string and remove leading/trailing spaces """
    x = str(x).upper().strip()
    """ If input contains a dash, keep only the part before the dash """
    if "-" in x:
        x = x.split("-", 1)[0]
    """ Replace underscores and dashes with dots """
    x = x.replace("_", ".").replace("-", ".")
    """ Remove any double dots """
    while ".." in x:
        x = x.replace("..", ".")
    """ Split into parts by dot """
    parts = [p for p in x.split(".") if p]
    """ If there are at least two parts, return them joined by a dot """
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[1]}"
    """ Otherwise, return the first part or empty string """
    return parts[0] if parts else ""
