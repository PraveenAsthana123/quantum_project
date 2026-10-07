"""
Step 1: Generate Synthetic 1000×1000 Dataset
=============================================
Generates a realistic messy dataset with:
  - 1000 rows, 1000 features, binary classification
  - 30% missing values in random cells
  - 50 correlated feature pairs
  - 5% outliers (3σ)
  - 23 duplicate rows
  - Class imbalance: 80% class 0, 20% class 1
"""

import numpy as np
import pandas as pd
import os
import time

RANDOM_SEED = 42
N_ROWS = 1000
N_FEATURES = 1000
MISSING_RATE = 0.30
N_CORRELATED_PAIRS = 50
OUTLIER_RATE = 0.05
N_DUPLICATES = 23
CLASS_IMBALANCE = 0.20  # fraction of class 1

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "raw_1000x1000.csv")


def generate_base_data(rng: np.random.Generator) -> np.ndarray:
    """Generate base numeric feature matrix."""
    print("  Generating base feature matrix (1000×1000)...")
    return rng.standard_normal((N_ROWS, N_FEATURES))


def inject_correlated_pairs(data: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Inject 50 correlated feature pairs by overwriting some columns."""
    print(f"  Injecting {N_CORRELATED_PAIRS} correlated feature pairs...")
    for i in range(N_CORRELATED_PAIRS):
        src_col = i * 2           # columns 0, 2, 4, ..., 98
        dst_col = i * 2 + 1       # columns 1, 3, 5, ..., 99
        noise = rng.normal(0, 0.05, N_ROWS)
        data[:, dst_col] = data[:, src_col] + noise  # |r| ≈ 0.998
    return data


def inject_outliers(data: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Inject 5% outlier cells (values > 3σ from mean)."""
    total_cells = N_ROWS * N_FEATURES
    n_outliers = int(total_cells * OUTLIER_RATE)
    print(f"  Injecting {n_outliers:,} outlier cells ({OUTLIER_RATE*100:.0f}%)...")
    row_idx = rng.integers(0, N_ROWS, n_outliers)
    col_idx = rng.integers(0, N_FEATURES, n_outliers)
    # Values ±5–10σ
    outlier_values = rng.choice([-1, 1], n_outliers) * rng.uniform(5, 10, n_outliers)
    data[row_idx, col_idx] = outlier_values
    return data


def inject_missing_values(data: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Inject 30% missing values as NaN."""
    total_cells = N_ROWS * N_FEATURES
    n_missing = int(total_cells * MISSING_RATE)
    print(f"  Injecting {n_missing:,} missing values ({MISSING_RATE*100:.0f}%)...")
    row_idx = rng.integers(0, N_ROWS, n_missing)
    col_idx = rng.integers(0, N_FEATURES, n_missing)
    data[row_idx, col_idx] = np.nan
    return data


def generate_labels(rng: np.random.Generator) -> np.ndarray:
    """Generate imbalanced binary labels: 80% class 0, 20% class 1."""
    print(f"  Generating labels: {int((1-CLASS_IMBALANCE)*100)}% class 0, "
          f"{int(CLASS_IMBALANCE*100)}% class 1...")
    labels = rng.choice([0, 1], size=N_ROWS, p=[1 - CLASS_IMBALANCE, CLASS_IMBALANCE])
    return labels


def inject_duplicates(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Duplicate 23 random rows and insert them back."""
    print(f"  Injecting {N_DUPLICATES} duplicate rows...")
    dup_indices = rng.choice(df.index, size=N_DUPLICATES, replace=False)
    dup_rows = df.loc[dup_indices].copy()
    df = pd.concat([df, dup_rows], ignore_index=True)
    # Shuffle so duplicates aren't all at the end
    df = df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)
    return df


def main():
    t0 = time.time()
    os.makedirs(DATA_DIR, exist_ok=True)
    rng = np.random.default_rng(RANDOM_SEED)

    print("=" * 60)
    print("STEP 1: Generating Synthetic 1000×1000 Dataset")
    print("=" * 60)

    # Build feature matrix
    data = generate_base_data(rng)
    data = inject_correlated_pairs(data, rng)
    data = inject_outliers(data, rng)
    data = inject_missing_values(data, rng)

    # Labels
    labels = generate_labels(rng)

    # Build DataFrame
    feature_names = [f"feature_{i:04d}" for i in range(N_FEATURES)]
    df = pd.DataFrame(data, columns=feature_names)
    df["label"] = labels

    # Inject duplicates (after label column is set)
    df = inject_duplicates(df, rng)

    # Summary stats
    actual_rows, actual_cols = df.shape
    missing_pct = df.isnull().sum().sum() / (actual_rows * (actual_cols - 1)) * 100
    dup_count = df.duplicated().sum()
    class_dist = df["label"].value_counts(normalize=True)

    print(f"\n  Dataset shape : {actual_rows} rows × {actual_cols} columns")
    print(f"  Missing values: {missing_pct:.1f}%")
    print(f"  Duplicate rows: {dup_count}")
    print(f"  Class 0       : {class_dist.get(0, 0)*100:.1f}%")
    print(f"  Class 1       : {class_dist.get(1, 0)*100:.1f}%")

    # Save
    print(f"\n  Saving to {OUTPUT_FILE} ...")
    df.to_csv(OUTPUT_FILE, index=False)

    elapsed = time.time() - t0
    size_mb = os.path.getsize(OUTPUT_FILE) / 1e6
    print(f"  Saved {size_mb:.1f} MB in {elapsed:.1f}s")
    print("  STEP 1 COMPLETE\n")


if __name__ == "__main__":
    main()
