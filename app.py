import json
import streamlit as st
import pandas as pd

from utils import (
    get_companies,
    get_domains,
    get_company_risk_grade,
    get_domain_score,
)

# Optional endpoints (guarded)
try:
    from utils import get_category_gpa
except Exception:
    get_category_gpa = None

try:
    from utils import get_findings_by_category
except Exception:
    get_findings_by_category = None

CATEGORY_NAMES = [
    "Attack Surface",
    "Vulnerability Exposure",
    "IP Reputation & Threats",
    "Web Security Posture",
    "Leakage & Breach History",
    "Email Security",
]

st.set_page_config(page_title="Supplier Cyber Risk", layout="wide")
st.title("Supplier Cyber Risk Dashboard")


# ------------------------------ Helpers ------------------------------
def _extract_number(x):
    """Best-effort number extraction from scalar, text, or dict-like payload."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x)
        except Exception:
            return None
    if isinstance(x, dict):
        for k in (
            "domain_score",
            "score",
            "overall_score",
            "value",
            "avg",
            "overall",
            "category_gpa",
            "gpa",
            "total_gpa",
        ):
            v = x.get(k)
            try:
                return float(v)
            except Exception:
                pass
    return None


def render_table(payload, *, title=None, expanded=False):
    """Normalize payload and render as a dataframe, without ever leaking a DG."""

    def _to_df(obj):
        if obj is None:
            return pd.DataFrame()
        if isinstance(obj, list):
            if not obj:
                return pd.DataFrame()
            return (
                pd.DataFrame(obj)
                if (len(obj) and isinstance(obj[0], dict))
                else pd.DataFrame({"Value": obj})
            )
        if isinstance(obj, dict):
            try:
                df = pd.json_normalize(obj, max_level=1)
                if df.empty:
                    df = pd.DataFrame.from_dict(obj, orient="index").reset_index(
                        names="Key"
                    )
            except Exception:
                df = pd.DataFrame.from_dict(obj, orient="index").reset_index(
                    names="Key"
                )
            return df
        return pd.DataFrame({"Value": [obj]})

    def _coerce(df):
        if df.empty:
            return df
        for c in df.columns:
            if df[c].apply(lambda x: isinstance(x, (dict, list))).any():
                df[c] = df[c].apply(lambda x: json.dumps(x, ensure_ascii=False))
        for c in df.columns:
            s = df[c]
            try:
                pd.to_numeric(s.dropna(), errors="raise")
            except Exception:
                df[c] = s.astype(str)
        return df

    # Build DF first, outside any DG creation
    try:
        df = _coerce(_to_df(payload))
    except Exception as e:
        if title is not None:
            with st.expander(title, expanded=expanded):
                st.error(f"Failed to render table: {e}")
                st.json(payload)
        else:
            st.error(f"Failed to render table: {e}")
            st.json(payload)
        return  # never return a DG

    # Always use a 'with' block; never leave a DG object hanging around
    if title is not None:
        exp = st.expander(title, expanded=expanded)
        with exp:
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No data.")
    else:
        cont = st.container()
        with cont:
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No data.")
    return  # explicit: never return a Streamlit object


def _to_str(x):
    return None if x is None else str(x)


def _id_equal(a, b):
    return _to_str(a) == _to_str(b)


def _belongs_to_company(d: dict, company_id):
    return _id_equal(
        d.get("company_id") or d.get("companyId") or d.get("cid"), company_id
    )


def _normalize_findings(cat, data):
    """Return a normalized list of finding rows for a category."""
    rows = []
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        if isinstance(data.get("findings"), list):
            rows = data["findings"]
        elif data:
            rows = [data]
    out = []
    for item in rows:
        if isinstance(item, dict):
            out.append({"Category": cat, **item})
        else:
            out.append({"Category": cat, "Finding": item})
    return out


# ------------------------------ Cached fetches ------------------------------
@st.cache_data(ttl=60, show_spinner=False)
def _load_companies():
    return get_companies()


@st.cache_data(ttl=60, show_spinner=False)
def _load_domains():
    return get_domains()


# ------------------------------ Load companies ------------------------------
try:
    companies_payload = _load_companies()
except Exception as e:
    st.error(f"Failed to load companies: {e}")
    st.stop()

if not companies_payload:
    st.info("No companies available.")
    st.stop()

company_options, company_map = [], {}
for c in companies_payload:
    cid = c.get("company_id") or c.get("id")
    cname = c.get("company_name") or c.get("name") or f"Company {cid}"
    label = f"{cid} — {cname}" if cid is not None else cname
    company_options.append(label)
    company_map[label] = cid

# ------------------------------ Sidebar ------------------------------
view = st.sidebar.radio("View", ["Risk Dashboard", "All Companies"], index=0)
if view == "All Companies":
    st.subheader("All Companies")
    render_table(companies_payload, title="All Companies (from API)", expanded=True)
    st.stop()

st.sidebar.subheader("Select Company")
selected_company_label = st.sidebar.selectbox("Company", company_options, index=0)
selected_company_id = company_map.get(selected_company_label)

# ------------------------------ Main: Company + Domains ------------------------------
selected_company_row = next(
    (
        c
        for c in companies_payload
        if _id_equal(c.get("company_id") or c.get("id"), selected_company_id)
    ),
    None,
)

try:
    domains_payload = _load_domains()
except Exception as e:
    st.warning(f"Could not fetch domains from API: {e}")
    domains_payload = []

company_domains = [
    d for d in domains_payload if _belongs_to_company(d, selected_company_id)
]

st.subheader("Selected Company")
with st.expander("Selected Company — Details & Domains", expanded=True):
    # ----- Aggregated Risk Overview -----
    grade_str, total_gpa_str, last_calc = "—", "—", "—"
    try:
        crg = get_company_risk_grade(selected_company_id) or {}
        if isinstance(crg, dict) and crg:
            if crg.get("grade"):
                grade_str = str(crg["grade"])
            if crg.get("total_gpa") is not None:
                total_gpa_str = f"{float(crg['total_gpa']):.2f}"
            if crg.get("calculated_date"):
                last_calc = str(crg["calculated_date"])
    except Exception:
        pass

    # Fallback: compute mean GPA from category endpoints if total_gpa missing
    if total_gpa_str == "—" and get_category_gpa is not None:
        gpas = []
        for cat in CATEGORY_NAMES:
            try:
                gp_payload = get_category_gpa(selected_company_id, cat)
                row = (
                    gp_payload[0]
                    if isinstance(gp_payload, list) and gp_payload
                    else gp_payload
                )
                if isinstance(row, dict):
                    val = row.get("category_gpa") or row.get("gpa") or row.get("value")
                    if val is not None:
                        gpas.append(float(val))
            except Exception:
                continue
        if gpas:
            total_gpa_str = f"{sum(gpas)/len(gpas):.2f}"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Risk Grade", grade_str)
    c2.metric("Total GPA", total_gpa_str)
    c3.metric("Domains", len(company_domains))
    c4.metric("Last Calculated", last_calc)

    st.markdown("**Company Details**")
    try:
        df1 = pd.json_normalize(selected_company_row or {}, max_level=1)
        if df1.empty:
            df1 = pd.DataFrame.from_dict(
                selected_company_row or {}, orient="index"
            ).reset_index(names="Key")

        if not df1.empty:
            st.dataframe(df1, use_container_width=True)
        else:
            st.info("No data.")
    except Exception:
        st.json(selected_company_row or {})

    st.markdown("**Company Domains**")
    try:
        if company_domains:
            if isinstance(company_domains[0], dict):
                df2 = pd.DataFrame(company_domains)
            else:
                df2 = pd.DataFrame({"Value": company_domains})
        else:
            df2 = pd.DataFrame()

        if not df2.empty:
            st.dataframe(df2, use_container_width=True)
        else:
            st.info("No data.")
    except Exception:
        st.json(company_domains)

if not company_domains:
    st.info("No domains found for this company.")
    st.stop()

# ------------------------------ Domain Picker ------------------------------
domain_items = []
for d in company_domains:
    did = d.get("domain_id") or d.get("id") or d.get("domainId")
    dname = d.get("domain_name") or d.get("domain") or d.get("name") or f"domain-{did}"
    domain_items.append({"_id": did, "_name": dname, "_raw": d})

st.subheader("Select a Domain")
selected_domain = st.selectbox(
    "Domain",
    domain_items,
    index=0,
    key=f"domain_select_{selected_company_id}",
    format_func=lambda x: f"{x['_id']} — {x['_name']}",
)
selected_domain_id = selected_domain["_id"]
selected_domain_raw = selected_domain["_raw"]

# ------------------------------ Selected Domain ------------------------------
st.subheader("Selected Domain")
with st.expander("Selected Domain — Risk Overview & Findings", expanded=True):
    # Domain Score (API first)
    dom_score_value = None
    try:
        ds = get_domain_score(selected_domain_id)
        dom_score_value = _extract_number(ds)
    except Exception:
        dom_score_value = None

    # Pull findings (all categories) if endpoint exists
    all_risks = []
    if get_findings_by_category is not None and selected_domain_id is not None:
        for cat in CATEGORY_NAMES:
            try:
                data = get_findings_by_category(selected_domain_id, cat)
                all_risks.extend(_normalize_findings(cat, data))
            except Exception:
                continue

    # Fallback: compute mean from findings if no API domain_score
    if dom_score_value is None and all_risks:
        scores = []
        for r in all_risks:
            for k in ("Finding Score", "finding_score", "score"):
                if k in r and r[k] is not None:
                    try:
                        scores.append(float(r[k]))
                        break
                    except Exception:
                        pass
        if scores:
            dom_score_value = sum(scores) / len(scores)

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Domain Score (mean)",
        f"{dom_score_value:.2f}" if dom_score_value is not None else "—",
    )
    c2.metric("Total Findings", len(all_risks))
    c3.metric(
        "Categories Covered",
        len({r.get("Category") for r in all_risks}) if all_risks else 0,
    )

    st.markdown("**Findings (All Categories)**")
    render_table(all_risks if all_risks else selected_domain_raw)

# ------------------------------ Domain Analysis ------------------------------
st.subheader("Domain Analysis")
has_gpa = get_category_gpa is not None
has_findings = get_findings_by_category is not None

gpa_choice = st.radio(
    "Category GPA", ["Hide", "Show"] if has_gpa else ["Hide"], index=0, horizontal=True
)
findings_choice = st.radio(
    "Findings", ["Hide", "Show"] if has_findings else ["Hide"], index=0, horizontal=True
)

if (gpa_choice == "Show" and has_gpa) or (findings_choice == "Show" and has_findings):
    with st.form("domain_analysis_form", clear_on_submit=False):
        gpa_cat = (
            st.selectbox("Category for GPA", CATEGORY_NAMES, index=0)
            if gpa_choice == "Show" and has_gpa
            else None
        )
        findings_cat = None
        if findings_choice == "Show" and has_findings:
            findings_cat = st.selectbox(
                "Category for Findings", ["All Categories"] + CATEGORY_NAMES, index=0
            )
        submitted = st.form_submit_button("Run Analysis")

    if submitted:
        if gpa_cat and has_gpa:
            try:
                payload = get_category_gpa(selected_company_id, gpa_cat)
                render_table(payload, title=f"Category GPA — {gpa_cat}", expanded=True)
            except Exception as e:
                st.warning(f"Category GPA unavailable: {e}")

        if findings_cat and has_findings and selected_domain_id is not None:
            if findings_cat == "All Categories":
                combined, skipped = [], []
                for cat in CATEGORY_NAMES:
                    try:
                        data = get_findings_by_category(selected_domain_id, cat)
                        combined.extend(_normalize_findings(cat, data))
                    except Exception as e:
                        skipped.append((cat, str(e)))
                render_table(combined, title="Findings — All Categories", expanded=True)
                if not combined:
                    st.info("No findings returned for any category.")
                if skipped:
                    with st.expander(
                        "Categories with no data / non-JSON", expanded=False
                    ):
                        for cat, msg in skipped:
                            st.write(f"- {cat}: {msg}")
            else:
                try:
                    data = get_findings_by_category(selected_domain_id, findings_cat)
                    single = _normalize_findings(findings_cat, data)
                    render_table(
                        single, title=f"Findings — {findings_cat}", expanded=True
                    )
                    if not single:
                        st.info(f"No findings for {findings_cat}.")
                except Exception as e:
                    st.warning(f"Findings for {findings_cat} unavailable: {e}")
else:
    st.info("Use the radios above to choose what to analyze.")
