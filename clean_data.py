from pathlib import Path
import re
import shutil
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

def norm(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).strip().lower()).strip("_")

def find_col(df, candidates, required=True):
    lookup = {norm(c): c for c in df.columns}
    for name in candidates:
        if norm(name) in lookup:
            return lookup[norm(name)]
    if required:
        raise ValueError(f"Missing expected column. Tried {candidates}. Available: {list(df.columns)}")
    return None

def load_csv(path):
    df = pd.read_csv(path)
    df.columns = [norm(c) for c in df.columns]
    return df

def clean_nav(path):
    df = load_csv(path)
    code = find_col(df, ["amfi_code", "scheme_code", "fund_code"])
    date = find_col(df, ["date", "nav_date", "as_of_date"])
    nav = find_col(df, ["nav", "net_asset_value"])
    df[date] = pd.to_datetime(df[date], errors="coerce", dayfirst=True)
    df[nav] = pd.to_numeric(df[nav], errors="coerce")
    df = df.dropna(subset=[code, date])
    df = df.sort_values([code, date])
    df = df.drop_duplicates(subset=[code, date], keep="last")
    # Forward-fill only existing date rows within each scheme; do not invent weekend rows.
    df[nav] = df.groupby(code, sort=False)[nav].ffill()
    df = df[df[nav].notna() & (df[nav] > 0)].copy()
    df[date] = df[date].dt.strftime("%Y-%m-%d")
    return df

def clean_transactions(path):
    df = load_csv(path)
    date = find_col(df, ["transaction_date", "date", "txn_date"])
    amount = find_col(df, ["amount", "transaction_amount", "txn_amount"])
    typ = find_col(df, ["transaction_type", "txn_type", "type"])
    kyc = find_col(df, ["kyc_status", "kyc"])
    df[date] = pd.to_datetime(df[date], errors="coerce", dayfirst=True)
    df[amount] = pd.to_numeric(df[amount], errors="coerce")
    mapping = {
        "sip": "SIP", "systematic investment plan": "SIP",
        "lumpsum": "Lumpsum", "lump sum": "Lumpsum", "lump-sum": "Lumpsum",
        "redemption": "Redemption", "redeem": "Redemption"
    }
    df[typ] = df[typ].astype(str).str.strip().str.lower().map(mapping)
    df[kyc] = df[kyc].astype(str).str.strip().str.upper()
    valid_kyc = {"YES", "NO", "VERIFIED", "PENDING", "REJECTED", "Y", "N"}
    df.loc[~df[kyc].isin(valid_kyc), kyc] = "UNKNOWN"
    df = df.dropna(subset=[date, amount, typ])
    df = df[df[amount] > 0].copy()
    df[date] = df[date].dt.strftime("%Y-%m-%d")
    return df

def clean_performance(path):
    df = load_csv(path)
    # Convert columns with return/ratio/performance names to numeric.
    for col in df.columns:
        if any(key in col for key in ["return", "expense_ratio", "cagr", "alpha", "beta", "sharpe"]):
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace("%", "", regex=False).str.strip(),
                errors="coerce"
            )
    expense = find_col(df, ["expense_ratio"], required=False)
    if expense:
        # Assumes values are expressed in percentage points (e.g. 1.25 means 1.25%).
        df["expense_ratio_flag"] = np.where(
            df[expense].between(0.1, 2.5), "OK", "CHECK"
        )
    return df

def main():
    csvs = sorted(RAW.glob("*.csv"))
    if not csvs:
        raise SystemExit(f"No CSV files found. Put your 10 original CSVs in: {RAW}")
    special = {
        "nav_history.csv": clean_nav,
        "investor_transactions.csv": clean_transactions,
        "scheme_performance.csv": clean_performance,
    }
    for src in csvs:
        key = src.name.lower()
        if key in special:
            cleaned = special[key](src)
        else:
            # Preserve the other source datasets while normalizing column names.
            cleaned = load_csv(src)
        dest = OUT / src.name
        cleaned.to_csv(dest, index=False)
        print(f"{src.name}: {len(pd.read_csv(src))} source rows -> {len(cleaned)} cleaned rows -> {dest}")
    print(f"\nProcessed {len(csvs)} CSV files. Expected deliverable: 10 files.")

if __name__ == "__main__":
    main()
