# Bluestock Mutual Fund Analytics — Day 2

## Setup
1. Copy the 10 original CSV files into `data/raw/`.
2. Ensure the core files are named `nav_history.csv`, `investor_transactions.csv`, and `scheme_performance.csv`.
3. Install dependencies: `pip install -r requirements.txt`
4. Run cleaning: `python clean_data.py`
5. Run database loading: `python load_database.py`

## SQL
- Schema: `sql/schema.sql`
- Analytics: `sql/queries.sql`
- Data dictionary: `reports/data_dictionary.md`

## Important notes
- The cleaning script preserves the other seven CSVs with normalized column names; add dataset-specific validation once their schemas are known.
- Forward-fill applies to missing NAV values on rows already present. It does not generate synthetic weekend/holiday observations.
- The loader creates staging tables for all cleaned CSVs and loads the NAV fact. The transaction, performance, and AUM fact loads require the exact source column mappings and should be finalized after inspecting the source headers.
- Expense ratio inputs are assumed to be percentage points (e.g. 1.25 means 1.25%). If your file stores decimal fractions (e.g. 0.0125), convert before applying the range check.
