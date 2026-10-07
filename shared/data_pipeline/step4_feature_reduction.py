"""
Step 4: Feature Reduction
==========================
Loads normalized data (robust-scaled) and reduces 1000 features to 4 and 8
for quantum circuit use via a 5-stage pipeline:

  Stage 1: Remove highly correlated features (|r| > 0.95)
  Stage 2: Remove near-zero variance features (threshold = 0.01)
  Stage 3: SelectKBest (f_classif, k=50)
  Stage 4: PCA to retain 95% variance
  Stage 5: Select top 4 and top 8 features (first N PCA components)

Outputs:
  data/features_4.csv
  data/features_8.csv
  data/reduction_report.json
"""

import json
import os
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.feature_selection import (SelectKBest, VarianceThreshold,
                                       f_classif)
from sklearn.preprocessing import MinMaxScaler

warnings.filterwarnings("ignore")

DATA_DIR         = os.path.join(os.path.dirname(__file__), "data")
INPUT_FILE       = os.path.join(DATA_DIR, "normalized_robust.csv")
INPUT_FALLBACK   = os.path.join(DATA_DIR, "normalized_minmax.csv")
OUTPUT_4         = os.path.join(DATA_DIR, "features_4.csv")
OUTPUT_8         = os.path.join(DATA_DIR, "features_8.csv")
OUTPUT_JSON      = os.path.join(DATA_DIR, "reduction_report.json")

LABEL_COL        = "label"
CORR_THRESHOLD   = 0.95
VAR_THRESHOLD    = 0.01
KBEST_K          = 50
PCA_VARIANCE     = 0.95
QUANTUM_TOP_4    = 4
QUANTUM_TOP_8    = 8


# ── Stage 1: Correlation filter ──────────────────────────────────────────────

def remove_correlated(df: pd.DataFrame, threshold: float = CORR_THRESHOLD) -> tuple[pd.DataFrame, list]:
    """
    Remove features where |Pearson r| > threshold with any earlier feature.
    Returns (filtered_df, list_of_dropped_col_names).
    """
    print(f"  [Stage 1] Computing correlation matrix ({df.shape[1]} features)...")
    corr_matrix = df.corr().abs()
    upper_tri = corr_matrix.where(
        np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
    )
    to_drop = [col for col in upper_tri.columns if (upper_tri[col] > threshold).any()]
    df_filtered = df.drop(columns=to_drop)
    print(f"  [Stage 1] Dropped {len(to_drop):,} correlated features "
          f"→ {df_filtered.shape[1]} remaining")
    return df_filtered, to_drop


# ── Stage 2: Variance filter ─────────────────────────────────────────────────

def remove_low_variance(df: pd.DataFrame, threshold: float = VAR_THRESHOLD) -> tuple[pd.DataFrame, int]:
    """Remove near-zero variance features."""
    selector = VarianceThreshold(threshold=threshold)
    selector.fit(df)
    mask = selector.get_support()
    cols_kept = df.columns[mask].tolist()
    dropped = df.shape[1] - len(cols_kept)
    df_filtered = df[cols_kept]
    print(f"  [Stage 2] Dropped {dropped:,} near-zero variance features "
          f"→ {df_filtered.shape[1]} remaining")
    return df_filtered, dropped


# ── Stage 3: SelectKBest ─────────────────────────────────────────────────────

def select_kbest(df: pd.DataFrame, labels: pd.Series, k: int = KBEST_K) -> tuple[pd.DataFrame, list]:
    """Select k best features by F-statistic (f_classif)."""
    # f_classif requires non-negative input; shift if needed
    df_shifted = df - df.min()
    selector = SelectKBest(score_func=f_classif, k=min(k, df.shape[1]))
    selector.fit(df_shifted, labels)
    mask = selector.get_support()
    selected_cols = df.columns[mask].tolist()
    df_filtered = df[selected_cols]
    print(f"  [Stage 3] SelectKBest (f_classif, k={k}) → {df_filtered.shape[1]} features")
    return df_filtered, selected_cols


# ── Stage 4: PCA ─────────────────────────────────────────────────────────────

def apply_pca(df: pd.DataFrame, variance_target: float = PCA_VARIANCE
              ) -> tuple[pd.DataFrame, PCA, list]:
    """
    Apply PCA retaining `variance_target` fraction of variance.
    Returns (pca_df with named components, fitted PCA, explained_variance_ratios).
    """
    pca = PCA(n_components=variance_target, random_state=42)
    components = pca.fit_transform(df)
    n_comp = components.shape[1]
    evr = pca.explained_variance_ratio_.tolist()
    col_names = [f"PC{i+1}" for i in range(n_comp)]
    df_pca = pd.DataFrame(components, columns=col_names)
    print(f"  [Stage 4] PCA retaining {variance_target*100:.0f}% variance → "
          f"{n_comp} components (cumulative: {sum(evr)*100:.1f}%)")
    return df_pca, pca, evr


# ── Stage 5: Select top N for quantum ────────────────────────────────────────

def select_top_n(df_pca: pd.DataFrame, labels: pd.Series, n: int, out_path: str) -> list:
    """Select first n PCA components (sorted by explained variance desc)."""
    cols = df_pca.columns[:n].tolist()
    df_out = df_pca[cols].copy()
    df_out[LABEL_COL] = labels.values
    # Re-scale to [0, 1] so quantum angle encoding stays in valid range
    scaler = MinMaxScaler()
    df_out[cols] = scaler.fit_transform(df_out[cols])
    df_out.to_csv(out_path, index=False)
    print(f"  [Stage 5] Saved top-{n} features → {os.path.basename(out_path)}")
    return cols


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 60)
    print("STEP 4: Feature Reduction")
    print("=" * 60)

    # Load normalized data (prefer robust, fall back to minmax)
    input_file = INPUT_FILE if os.path.exists(INPUT_FILE) else INPUT_FALLBACK
    if not os.path.exists(input_file):
        raise FileNotFoundError(
            f"No normalized file found at {INPUT_FILE} or {INPUT_FALLBACK}.\n"
            "Run step3_normalize.py first."
        )
    print(f"  Loading {input_file} ...")
    df = pd.read_csv(input_file)
    print(f"  Loaded: {df.shape[0]} rows × {df.shape[1]} cols")

    labels = df[LABEL_COL].copy()
    df_features = df.drop(columns=[LABEL_COL])
    original_features = df_features.shape[1]

    # Stage 1: Correlation
    df_stage1, dropped_corr = remove_correlated(df_features)
    after_correlation = df_stage1.shape[1]

    # Stage 2: Variance
    df_stage2, dropped_var = remove_low_variance(df_stage1)
    after_variance = df_stage2.shape[1]

    # Stage 3: SelectKBest
    k = min(KBEST_K, after_variance)
    df_stage3, kbest_cols = select_kbest(df_stage2, labels, k=k)
    after_selectkbest = df_stage3.shape[1]

    # Stage 4: PCA
    df_pca, pca_model, evr = apply_pca(df_stage3)
    after_pca = df_pca.shape[1]

    # Stage 5: Select top 4 and top 8
    quantum_4 = select_top_n(df_pca, labels, QUANTUM_TOP_4, OUTPUT_4)
    quantum_8 = select_top_n(df_pca, labels, min(QUANTUM_TOP_8, after_pca), OUTPUT_8)

    # ── Report ───────────────────────────────────────────────────────────────
    report = {
        "original_features"     : original_features,
        "after_correlation"     : after_correlation,
        "after_variance"        : after_variance,
        "after_selectkbest"     : after_selectkbest,
        "after_pca"             : after_pca,
        "pca_variance_target"   : PCA_VARIANCE,
        "pca_variance_achieved" : round(float(sum(evr[:after_pca])), 4),
        "quantum_4"             : quantum_4,
        "quantum_8"             : quantum_8,
        "explained_variance_ratios": [round(v, 6) for v in evr[:after_pca]],
        "correlated_dropped"    : len(dropped_corr),
        "variance_dropped"      : dropped_var,
        "kbest_k"               : k,
        "n_samples"             : len(df),
    }

    with open(OUTPUT_JSON, "w") as f:
        json.dump(report, f, indent=2)

    elapsed = time.time() - t0
    print(f"\n  Reduction pipeline summary:")
    print(f"    {original_features} → {after_correlation} (corr) "
          f"→ {after_variance} (var) "
          f"→ {after_selectkbest} (kbest) "
          f"→ {after_pca} (pca)")
    print(f"    Quantum-4 features : {quantum_4}")
    print(f"    Quantum-8 features : {quantum_8}")
    print(f"  Report saved → {OUTPUT_JSON}")
    print(f"  Elapsed: {elapsed:.1f}s")
    print("  STEP 4 COMPLETE\n")


if __name__ == "__main__":
    main()
