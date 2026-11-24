from pathlib import Path
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent
PROCESSED = ROOT / "data" / "processed"
DB = ROOT / "database" / "bluestock_mf.db"
SCHEMA = ROOT / "sql" / "schema.sql"

def read_optional(filename):
    path = PROCESSED / filename
    return pd.read_csv(path) if path.exists() else pd.DataFrame()

def date_dim(dates):
    s = pd.to_datetime(pd.Series(dates).dropna().astype(str), errors="coerce").dropna().drop_duplicates()
    d = pd.DataFrame({"full_date": s.dt.strftime("%Y-%m-%d")})
    dt = pd.to_datetime(d["full_date"])
    d["date_key"] = dt.dt.strftime("%Y%m%d").astype(int)
    d["year"] = dt.dt.year
    d["quarter"] = dt.dt.quarter
    d["month"] = dt.dt.month
    d["month_name"] = dt.dt.month_name()
    d["day"] = dt.dt.day
    return d[["date_key","full_date","year","quarter","month","month_name","day"]]

def main():
    DB.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{DB.as_posix()}")
    nav = read_optional("nav_history.csv")
    tx = read_optional("investor_transactions.csv")
    perf = read_optional("scheme_performance.csv")

    # Identify expected fields after clean_data.py normalizes column names.
    date_cols = []
    for df, choices in [(nav, ["date","nav_date","as_of_date"]),
                        (tx, ["transaction_date","date","txn_date"])]:
        for c in choices:
            if c in df.columns:
                date_cols.extend(df[c].dropna().astype(str).tolist())
                break
    dates = date_dim(date_cols)

    with engine.begin() as conn:
        conn.exec_driver_sql(SCHEMA.read_text(encoding="utf-8"))
        dates.to_sql("dim_date", conn, if_exists="append", index=False)
        conn.exec_driver_sql("DELETE FROM dim_date WHERE date_key NOT IN (SELECT MIN(date_key) FROM dim_date GROUP BY full_date)")
        # The source fund dimension is assembled from distinct AMFI codes in available files.
        fund_parts = []
        for df in [nav, tx, perf]:
            if not df.empty:
                code = next((c for c in ["amfi_code","scheme_code","fund_code"] if c in df.columns), None)
                if code:
                    name = next((c for c in ["scheme_name","fund_name","scheme"] if c in df.columns), None)
                    part = pd.DataFrame({"amfi_code": df[code].astype(str)})
                    part["scheme_name"] = df[name].astype(str) if name else part["amfi_code"]
                    fund_parts.append(part)
        funds = pd.concat(fund_parts, ignore_index=True).drop_duplicates("amfi_code") if fund_parts else pd.DataFrame(columns=["amfi_code","scheme_name"])
        funds.insert(0, "fund_key", range(1, len(funds)+1))
        funds["fund_house"] = None
        funds["category"] = None
        funds.to_sql("dim_fund", conn, if_exists="append", index=False)

    # Load source-level cleaned files as staging tables too, preserving all 10 deliverables.
    for csv in PROCESSED.glob("*.csv"):
        table = "stg_" + csv.stem.lower().replace("-", "_")
        pd.read_csv(csv).to_sql(table, engine, if_exists="replace", index=False)

    # Load NAV fact when matching columns exist.
    if not nav.empty:
        code = next(c for c in ["amfi_code","scheme_code","fund_code"] if c in nav.columns)
        date = next(c for c in ["date","nav_date","as_of_date"] if c in nav.columns)
        navcol = next(c for c in ["nav","net_asset_value"] if c in nav.columns)
        x = nav[[code,date,navcol]].copy()
        x.columns = ["amfi_code","full_date","nav"]
        x["full_date"] = pd.to_datetime(x["full_date"]).dt.strftime("%Y-%m-%d")
        x = x.merge(funds[["fund_key","amfi_code"]], on="amfi_code").merge(dates[["date_key","full_date"]], on="full_date")
        x[["fund_key","date_key","nav"]].to_sql("fact_nav", engine, if_exists="append", index=False)

    # Print source vs processed row counts. Staging tables contain the cleaned source rows.
    print("Database:", DB)
    for csv in sorted(PROCESSED.glob("*.csv")):
        table = "stg_" + csv.stem.lower().replace("-", "_")
        source_count = len(pd.read_csv(csv))
        with engine.connect() as conn:
            loaded = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one()
        print(f"{csv.name}: processed={source_count}, loaded={loaded}, match={source_count == loaded}")

if __name__ == "__main__":
    main()
