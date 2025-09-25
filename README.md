# PCP-Group-2

A modular Streamlit dashboard for visualizing cybersecurity risk findings, company maturity, and mapping results to the NIST Cybersecurity Framework (CSF).

---

## Project Overview

This project analyzes cybersecurity data for multiple companies,  GPA and maturity scores, and presents interactive dashboards for exploration. Data is organized into JSON bundles, which are loaded and processed for visualization and reporting.

### Main Features
- **Company Data Bundles**: Each company has a JSON file in `data/` containing all relevant info, scores, domains, and findings.
- **Dashboard UI**: Streamlit-based interface with tabs for Companies, Domains, and NIST CSF analysis.
- **Charts & Visualizations**: Altair charts for risk grades, category scores, domain scatter plots, findings timelines, and CSF maturity.
- **NIST CSF Mapping**: All findings and controls are mapped together for compliance analysis.
- **Modular Utilities**: Helper functions for DataFrame conversion, normalization, and mapping logic.

### Folder Structure & Relationships
- `data/` — Contains `{company_id}_data.json` files. See `data/README.txt` for details.
- `json_handler.py` — Builds, loads, and writes company bundles. Central to data flow.
- `services.py` — Provides business logic and API wrappers for data extraction and scoring.
- `utils/` — Utility functions for DataFrame handling and normalization.
- `charts/` — Chart builders for all dashboard visualizations. Depend on data and utils.
- `nist/` — NIST CSF mapping logic and helpers.
- `ui/` — Streamlit UI components and dashboard tabs.

### Key Relationships
- **Data Flow**: Raw data is fetched via APIs, bundled in JSON, and loaded for analysis and visualization.
- **Dependencies**:
  - `json_handler.py` depends on `services.py` and `utils/` for building bundles.
  - `charts/` depend on `utils/`, `services.py`, and `nist/` for chart data and mapping.
  - `ui/` imports chart builders and service functions to render dashboard tabs.
  - `nist/` provides mapping logic used by charts and services.
- **Feature Integration**: All dashboard features (charts & tables) are powered by the company bundles and mapping logic (nist_mappings).

### How to Run
1. Install dependencies (If no image/docker (.py needed to be installed)):
   ```bash
   pip install streamlit pandas altair
   ```
2. Start the dashboard:
   ```bash
   streamlit run app.py
   ```

---

- See folder-level *_folder_functions.txt files for documentation of all major functions and their usage.
- See `data/README.txt` for details on data structure and loading.


