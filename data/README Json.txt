# data/README.txt

This folder contains company data files in JSON format, named as `{company_id}_data.json`.

How JSON is built and loaded:

- JSON files are created and managed by the PCP project using the `json_handler.py` module.
- Each file stores a full data bundle for a company, including:
  - Company info
  - Risk grade
  - Category GPAs and scores
  - Domain details and scores
  - Findings grouped by category
- Bundles are built from live API data and written to disk atomically for safety.
- To load a bundle, the code calls `load_company_bundle(company_id)`, which reads the JSON file for that company.
- To list all bundles, use `list_company_bundles()`, which loads all JSON files in this folder.
- To write/update a bundle, use `write_company_bundle(company_id, bundle)`.

Dependencies:
- Main logic is in `json_handler.py`.
- Data is used by services, charts, and UI modules for analysis and display.
- Helper functions in `utils/dataframe_utils.py` assist with DataFrame conversion and formatting.

Summary:
- Data is always loaded from disk as needed.
- All company analysis, charts, and UI views depend on these JSON bundles for their data source.
