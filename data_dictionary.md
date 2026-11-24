# Bluestock Mutual Fund Analytics — Data Dictionary

> Update the source filenames and exact column names after checking the 10 supplied CSVs. The definitions below describe the core model.

## Source files

| Source file | Purpose | Main fields expected |
|---|---|---|
| nav_history.csv | Historical scheme NAV observations | amfi_code, date, nav |
| investor_transactions.csv | Investor purchase/redemption activity | transaction_date, transaction_type, amount, kyc_status, state |
| scheme_performance.csv | Scheme return and cost metrics | amfi_code, return_1y, return_3y, return_5y, expense_ratio |
| Other seven CSVs | Additional source datasets | Document actual columns after inspection |

## Core database tables

| Table | Column | SQLite type | Definition |
|---|---|---|---|
| dim_fund | fund_key | INTEGER PK | Warehouse surrogate key |
| dim_fund | amfi_code | TEXT UNIQUE | AMFI scheme identifier |
| dim_fund | scheme_name | TEXT | Fund/scheme display name |
| dim_fund | fund_house | TEXT | Asset management company |
| dim_fund | category | TEXT | Scheme category |
| dim_date | date_key | INTEGER PK | Date in YYYYMMDD format |
| dim_date | full_date | TEXT UNIQUE | Calendar date, YYYY-MM-DD |
| dim_date | year | INTEGER | Calendar year |
| dim_date | quarter | INTEGER | Calendar quarter |
| dim_date | month | INTEGER | Month number |
| dim_date | month_name | TEXT | Month name |
| dim_date | day | INTEGER | Day of month |
| fact_nav | nav_id | INTEGER PK | NAV fact row identifier |
| fact_nav | fund_key | INTEGER FK | References dim_fund |
| fact_nav | date_key | INTEGER FK | References dim_date |
| fact_nav | nav | REAL | Net asset value; must be positive |
| fact_transactions | transaction_id | INTEGER PK | Transaction row identifier |
| fact_transactions | fund_key | INTEGER FK | Related fund |
| fact_transactions | date_key | INTEGER FK | Transaction date |
| fact_transactions | investor_id | TEXT | Source investor identifier |
| fact_transactions | state | TEXT | Investor state |
| fact_transactions | transaction_type | TEXT | SIP, Lumpsum, or Redemption |
| fact_transactions | amount | REAL | Positive transaction amount |
| fact_transactions | kyc_status | TEXT | Normalized KYC status |
| fact_performance | performance_id | INTEGER PK | Performance row identifier |
| fact_performance | fund_key | INTEGER FK | Related fund |
| fact_performance | date_key | INTEGER FK | Snapshot date, if supplied |
| fact_performance | return_1y | REAL | One-year return |
| fact_performance | return_3y | REAL | Three-year return |
| fact_performance | return_5y | REAL | Five-year return |
| fact_performance | expense_ratio | REAL | Expense ratio in percentage points |
| fact_aum | aum_id | INTEGER PK | AUM fact row identifier |
| fact_aum | fund_key | INTEGER FK | Related fund |
| fact_aum | date_key | INTEGER FK | AUM observation date |
| fact_aum | aum | REAL | Assets under management |

## Cleaning rules

- Dates are parsed to ISO `YYYY-MM-DD`; unparseable dates are excluded from date-dependent facts.
- NAV values are numeric and strictly greater than zero. Missing NAVs are forward-filled within each scheme on existing dated rows only; no artificial weekend/holiday rows are created.
- Duplicate NAV observations are identified by scheme code and date; the last source row is retained.
- Transaction types are standardized to `SIP`, `Lumpsum`, and `Redemption`.
- Transaction amounts must be numeric and greater than zero.
- Unknown KYC labels are retained as `UNKNOWN` for review, not silently treated as verified.
- Return fields are numeric. Expense ratio is flagged when outside 0.1–2.5 percentage points.

## Source references

Record the exact original CSV filename, provider/source URL, download date, and source column for each field here. Do not invent provenance; fill these details from the supplied files.
