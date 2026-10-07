"""
Step 3: Normalization / Feature Scaling
========================================
Loads cleaned_data.csv and applies three scaling strategies:
  a) MinMaxScaler   → data/normalized_minmax.csv
  b) StandardScaler → data/normalized_standard.csv
  c) RobustScaler   → data/normalized_robust.csv

Produces a comparison report and saves the recommended strategy.

Outputs:
  data/normalized_minmax.csv
  data/normalized_standard.csv
  data/normalized_robust.csv
  data/normalization_report.json
"""

import json
import os
import time

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, RobustScaler, StandardScaler

DATA_DIR    = os.path.join(os.path.dirname(__file__), "data")
INPUT_FILE  = os.path.join(DATA_DIR, "cleaned_data.csv")
OUTPUT_MINMAX   = os.path.join(DATA_DIR, "normalized_minmax.csv")
OUTPUT_STANDARD = os.path.join(DATA_DIR, "normalized_standard.csv")
OUTPUT_ROBUST   = os.path.join(DATA_DIR, "normalized_robust.csv")
OUTPUT_JSON     = os.path.join(DATA_DIR, "normalization_report.json")

LABEL_COL = "label"


def scale_and_save(df_features: pd.DataFrame,
                   labels: pd.Series,
                   scaler,
                   out_path: str,
                   strategy_name: str) -> dict:
    """
    Fit-transform df_features with scaler, reattach labels, save CSV.
    Returns per-strategy stats dict.
    """
    t0 = time.time()
    scaled = scaler.fit_transform(df_features)
    df_scaled = pd.DataFrame(scaled, columns=df_features.columns)
    df_scaled[LABEL_COL] = labels.values

    df_scaled.to_csv(out_path, index=False)
    elapsed = time.time() - t0

    mean_after = float(np.mean(scaled))
    std_after  = float(np.std(scaled))
    min_after  = float(np.min(scaled))
    max_after  = float(np.max(scaled))

    print(f"  [{strategy_name}] mean={mean_after:.4f}  std={std_after:.4f}  "
          f"min={min_after:.4f}  max={max_after:.4f}  ({elapsed:.1f}s)")

    return {
        "strategy"    : strategy_name,
        "mean_after"  : round(mean_after, 4),
        "std_after"   : round(std_after, 4),
        "min_after"   : round(min_after, 4),
        "max_after"   : round(max_after, 4),
        "output_file" : os.path.basename(out_path),
        "elapsed_s"   : round(elapsed, 2),
    }


def choose_recommended(stats_list: list[dict]) -> str:
    """
    Simple heuristic: RobustScaler is best for data with remaining outliers
    (which is typical after IQR capping — some remain at the cap boundary).
    Returns strategy name.
    """
    # Prefer minmax when std is closest to 0.29 (uniform distribution ideal)
    # For this pipeline (post-IQR capping) robust is the pragmatic choice.
    return "robust"


def main():
    t0 = time.time()
    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 60)
    print("STEP 3: Normalization & Scaling")
    print("=" * 60)

    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}\n"
            "Run step2_clean.py first."
        )

    print(f"  Loading {INPUT_FILE} ...")
    df = pd.read_csv(INPUT_FILE)
    print(f"  Loaded: {df.shape[0]} rows × {df.shape[1]} cols")

    labels = df[LABEL_COL]
    df_features = df.drop(columns=[LABEL_COL])

    # Identify numeric feature columns
    numeric_cols = df_features.select_dtypes(include=[np.number]).columns.tolist()
    non_numeric  = [c for c in df_features.columns if c not in numeric_cols]
    if non_numeric:
        print(f"  Non-numeric columns (pass-through): {non_numeric}")

    df_numeric  = df_features[numeric_cols]
    df_passthru = df_features[non_numeric] if non_numeric else None

    print("\n  Applying scaling strategies...")
    stats_list = []

    # a) MinMaxScaler
    s = scale_and_save(df_numeric, labels, MinMaxScaler(), OUTPUT_MINMAX, "minmax")
    stats_list.append(s)

    # b) StandardScaler
    s = scale_and_save(df_numeric, labels, StandardScaler(), OUTPUT_STANDARD, "standard")
    stats_list.append(s)

    # c) RobustScaler
    s = scale_and_save(df_numeric, labels, RobustScaler(), OUTPUT_ROBUST, "robust")
    stats_list.append(s)

    # Pick recommended strategy
    recommended = choose_recommended(stats_list)
    rec_stats = next(x for x in stats_list if x["strategy"] == recommended)

    report = {
        "strategy_used"   : recommended,
        "feature_range"   : [0, 1] if recommended == "minmax" else ["varies"],
        "mean_after"      : rec_stats["mean_after"],
        "std_after"       : rec_stats["std_after"],
        "n_features_scaled": len(numeric_cols),
        "n_rows"          : len(df),
        "recommended_file": rec_stats["output_file"],
        "all_strategies"  : stats_list,
        "selection_reason": (
            "RobustScaler preferred: data contains IQR-capped outliers at "
            "boundary values; robust scaling is insensitive to those."
        ),
    }

    with open(OUTPUT_JSON, "w") as f:
        json.dump(report, f, indent=2)

    elapsed = time.time() - t0
    print(f"\n  Recommended strategy : {recommended}")
    print(f"  Report saved → {OUTPUT_JSON}")
    print(f"  Elapsed: {elapsed:.1f}s")
    print("  STEP 3 COMPLETE\n")


if __name__ == "__main__":
    main()
