"""
Step 2: Data Cleaning
=====================
Loads raw_1000x1000.csv and applies:
  1. Remove duplicate rows
  2. Drop columns >30% null; impute remaining with median
  3. Detect and cap outliers using IQR method (1.5×IQR)
  4. Encode any categorical columns (LabelEncoder)

Outputs:
  data/cleaned_data.csv
  data/cleaning_report.json
"""

import json
import os
import time

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
INPUT_FILE  = os.path.join(DATA_DIR, "raw_1000x1000.csv")
OUTPUT_CSV  = os.path.join(DATA_DIR, "cleaned_data.csv")
OUTPUT_JSON = os.path.join(DATA_DIR, "cleaning_report.json")

NULL_DROP_THRESHOLD = 0.30   # drop columns with > 30% nulls
IQR_MULTIPLIER     = 1.5


# ── helpers ──────────────────────────────────────────────────────────────────

def remove_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Remove exact duplicate rows; return cleaned df and count removed."""
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    print(f"  [Step 2.1] Duplicates removed : {removed:,}  (rows: {before} → {len(df)})")
    return df.reset_index(drop=True), removed


def handle_nulls(df: pd.DataFrame, label_col: str = "label") -> tuple[pd.DataFrame, int, int]:
    """
    Drop columns with >30% nulls (excluding label).
    Impute remaining numeric NaNs with column median.
    Returns (df, cols_dropped, cells_imputed).
    """
    feature_cols = [c for c in df.columns if c != label_col]
    null_fracs = df[feature_cols].isnull().mean()

    # Columns to drop
    drop_cols = null_fracs[null_fracs > NULL_DROP_THRESHOLD].index.tolist()
    cols_dropped = len(drop_cols)
    df = df.drop(columns=drop_cols)
    print(f"  [Step 2.2] Columns dropped (>{NULL_DROP_THRESHOLD*100:.0f}% null): {cols_dropped:,}")

    # Impute remaining
    remaining_features = [c for c in df.columns if c != label_col]
    cells_imputed = 0
    for col in remaining_features:
        n_null = df[col].isnull().sum()
        if n_null > 0:
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
            cells_imputed += n_null

    print(f"  [Step 2.2] Cells imputed with median  : {cells_imputed:,}")
    return df, cols_dropped, cells_imputed


def cap_outliers_iqr(df: pd.DataFrame, label_col: str = "label") -> tuple[pd.DataFrame, int]:
    """Cap numeric feature values at Q1 - 1.5×IQR and Q3 + 1.5×IQR."""
    feature_cols = [c for c in df.columns if c != label_col and
                    pd.api.types.is_numeric_dtype(df[c])]
    total_capped = 0
    for col in feature_cols:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - IQR_MULTIPLIER * iqr
        upper = q3 + IQR_MULTIPLIER * iqr
        n_capped = ((df[col] < lower) | (df[col] > upper)).sum()
        df[col] = df[col].clip(lower=lower, upper=upper)
        total_capped += n_capped

    print(f"  [Step 2.3] Outlier cells capped (IQR) : {total_capped:,}")
    return df, total_capped


def encode_categoricals(df: pd.DataFrame, label_col: str = "label") -> tuple[pd.DataFrame, list]:
    """LabelEncode any object/category columns (except label)."""
    cat_cols = [c for c in df.columns
                if c != label_col and df[c].dtype in ["object", "category"]]
    encoded_cols = []
    for col in cat_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        encoded_cols.append(col)
    if encoded_cols:
        print(f"  [Step 2.4] Categorical columns encoded: {encoded_cols}")
    else:
        print(f"  [Step 2.4] No categorical columns found — skipping.")
    return df, encoded_cols


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 60)
    print("STEP 2: Data Cleaning")
    print("=" * 60)

    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}\n"
            "Run step1_generate_data.py first."
        )

    print(f"  Loading {INPUT_FILE} ...")
    df = pd.read_csv(INPUT_FILE)
    rows_before, cols_before = df.shape
    print(f"  Loaded: {rows_before} rows × {cols_before} cols")

    # ── Apply cleaning steps ────────────────────────────────────────────────
    df, duplicates_removed = remove_duplicates(df)
    df, cols_dropped, nulls_imputed = handle_nulls(df)
    df, outliers_capped = cap_outliers_iqr(df)
    df, _encoded = encode_categoricals(df)

    rows_after, cols_after = df.shape

    # ── Save outputs ────────────────────────────────────────────────────────
    print(f"\n  Saving cleaned data → {OUTPUT_CSV}")
    df.to_csv(OUTPUT_CSV, index=False)

    report = {
        "rows_before"       : int(rows_before),
        "rows_after"        : int(rows_after),
        "cols_before"       : int(cols_before),
        "cols_after"        : int(cols_after),
        "duplicates_removed": int(duplicates_removed),
        "cols_dropped_null" : int(cols_dropped),
        "nulls_imputed"     : int(nulls_imputed),
        "outliers_capped"   : int(outliers_capped),
        "categorical_encoded": int(len(_encoded)),
    }

    with open(OUTPUT_JSON, "w") as f:
        json.dump(report, f, indent=2)
    print(f"  Saving cleaning report → {OUTPUT_JSON}")

    # ── Summary ─────────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    print(f"\n  Summary:")
    print(f"    Rows  : {rows_before} → {rows_after} (removed {rows_before - rows_after})")
    print(f"    Cols  : {cols_before} → {cols_after} (dropped {cols_before - cols_after})")
    print(f"    Nulls imputed   : {nulls_imputed:,}")
    print(f"    Outliers capped : {outliers_capped:,}")
    print(f"  Elapsed: {elapsed:.1f}s")
    print("  STEP 2 COMPLETE\n")


if __name__ == "__main__":
    main()
