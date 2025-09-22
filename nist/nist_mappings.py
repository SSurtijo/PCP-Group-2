###
# File: nist/nist_mappings.py
# Description: NIST CSF function and control mappings for PCP project.
# Defines L1/L2 function names, control mappings, and external finding mappings.
###

### CSF function names (Level 1)
CSF_L1_FUNCTION_FULL = {
    "GV": "Govern",
    "ID": "Identify",
    "PR": "Protect",
    "DE": "Detect",
    "RS": "Respond",
    "RC": "Recover",
}

### Function Identifier → Function Name (L1→L2)
FUNCTION_L1_IDENTIFIER_TO_FUNCTION_L2 = {
    "GV.OC": "Organizational Context",
    "GV.OV": "Oversight",
    "GV.PO": "Policy",
    "GV.RM": "Risk Management Strategy",
    "GV.RR": "Roles, Responsibilities and Authorities",
    "GV.SC": "Supply Chain Risk Management",
    "ID.AM": "Asset Management",
    "ID.RA": "Risk Assessment",
    "ID.IM": "Improvement",
    "PR.AA": "Identity & Access Control",
    "PR.AT": "Awareness & Training",
    "PR.DS": "Data Security",
    "PR.PS": "Platform Security",
    "PR.IR": "Technology Infrastructure Resilience",
    "DE.CM": "Continuous Monitoring",
    "DE.AE": "Adverse Event Analysis",
    "RS.MA": "Incident Management",
    "RS.AN": "Incident Analysis",
    "RS.CO": "Incident Response & Reporting",
    "RS.MI": "Incident Mitigation",
    "RC.RP": "Incident Recovery Plan Execution",
    "RC.CO": "Incident Recovery Communication",
}

### Function (L2) → Controls
FUNCTION_L2_TO_CONTROLS = {
    "Organizational Context": ["GV.OC-02", "GV.OC-03", "GV.OC-04", "GV.OC-05"],
    "Oversight": ["GV.OV-01", "GV.OV-02", "GV.OV-03"],
    "Policy": ["GV.PO-01", "GV.PO-02"],
    "Risk Management Strategy": [
        "GV.RM-01",
        "GV.RM-02",
        "GV.RM-03",
        "GV.RM-04",
        "GV.RM-05",
        "GV.RM-06",
        "GV.RM-07",
    ],
    "Roles, Responsibilities and Authorities": [
        "GV.RR-01",
        "GV.RR-02",
        "GV.RR-03",
        "GV.RR-04",
    ],
    "Supply Chain Risk Management": [
        "GV.SC-01",
        "GV.SC-02",
        "GV.SC-03",
        "GV.SC-04",
        "GV.SC-05",
        "GV.SC-06",
        "GV.SC-07",
        "GV.SC-08",
        "GV.SC-09",
        "GV.SC-10",
    ],
    "Asset Management": [
        "ID.AM-01",
        "ID.AM-02",
        "ID.AM-03",
        "ID.AM-04",
        "ID.AM-05",
        "ID.AM-07",
        "ID.AM-08",
    ],
    "Risk Assessment": [
        "ID.RA-01",
        "ID.RA-02",
        "ID.RA-03",
        "ID.RA-04",
        "ID.RA-05",
        "ID.RA-06",
        "ID.RA-07",
        "ID.RA-08",
        "ID.RA-09",
        "ID.RA-10",
    ],
    "Improvement": ["ID.IM-01", "ID.IM-02", "ID.IM-03", "ID.IM-04"],
    "Identity & Access Control": [
        "PR.AA-01",
        "PR.AA-02",
        "PR.AA-03",
        "PR.AA-04",
        "PR.AA-05",
        "PR.AA-06",
    ],
    "Awareness & Training": ["PR.AT-01", "PR.AT-02"],
    "Data Security": ["PR.DS-01", "PR.DS-02", "PR.DS-10", "PR.DS-11"],
    "Platform Security": [
        "PR.PS-01",
        "PR.PS-02",
        "PR.PS-03",
        "PR.PS-04",
        "PR.PS-05",
        "PR.PS-06",
    ],
    "Technology Infrastructure Resilience": [
        "PR.IR-01",
        "PR.IR-02",
        "PR.IR-03",
        "PR.IR-04",
    ],
    "Continuous Monitoring": [
        "DE.CM-01",
        "DE.CM-02",
        "DE.CM-03",
        "DE.CM-06",
        "DE.CM-09",
    ],
    "Adverse Event Analysis": [
        "DE.AE-02",
        "DE.AE-03",
        "DE.AE-04",
        "DE.AE-06",
        "DE.AE-07",
        "DE.AE-08",
    ],
    "Incident Management": ["RS.MA-01", "RS.MA-02", "RS.MA-03", "RS.MA-04", "RS.MA-05"],
    "Incident Analysis": ["RS.AN-03", "RS.AN-06", "RS.AN-07", "RS.AN-08"],
    "Incident Response & Reporting": ["RS.CO-02", "RS.CO-03"],
    "Incident Mitigation": ["RS.MI-01", "RS.MI-02"],
    "Incident Recovery Plan Execution": [
        "RC.RP-01",
        "RC.RP-02",
        "RC.RP-03",
        "RC.RP-04",
        "RC.RP-05",
        "RC.RP-06",
    ],
    "Incident Recovery Communication": ["RC.CO-03", "RC.CO-04"],
}

### External Findings → Controls (per your remap)
EXTERNAL_FINDINGS_TO_CONTROLS = {
    "Attack Surface": ["ID.AM-01", "ID.RA-01"],
    "Vulnerability Exposure": ["PR.PS-01", "DE.CM-01"],
    "IP Reputation & Threats": ["DE.CM-02", "DE.AE-02"],
    "Web Security Posture": ["PR.PS-02", "PR.DS-01"],
    "Leakage & Breach History": ["RS.AN-03", "RC.RP-01"],
    "Email Security": ["PR.AA-02", "PR.AT-01"],
}
