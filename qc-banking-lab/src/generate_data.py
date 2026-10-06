"""
Banking Lab Synthetic Data Generator
=====================================
Generates a realistic credit card fraud detection dataset (10,000 rows)
with 30 features (V1-V28 PCA-style components, Amount, Time, Class).

Fraud rate: ~1.7 %, matching real Kaggle credit card dataset statistics.
V1-V28 are drawn from a multivariate normal distribution.  Fraud samples
have shifted means for features V1, V4, V11, V14, V17 to create separable
signal without making classification trivially easy.

Output:
    qc-banking-lab/data/creditcard_synthetic.csv

Usage:
    python src/generate_data.py

Design notes:
- Seed 42 guarantees bit-for-bit reproducibility across runs.
- Amount follows a log-normal distribution (mean≈88, heavy right tail)
  matching the Kaggle empirical distribution.
- Time spans one full 48-hour window (0..172800 seconds) with higher
  transaction density during business hours (simulated via a mixture).
- The output schema is drop-in compatible with creditcard.csv so that
  all downstream scripts (classical_baseline.py, quantum_fraud.py, demo.py)
  can consume either file without code changes.

Version: 1.0.0
Date: 2026-10-06
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = DATA_DIR / "creditcard_synthetic.csv"

# ---------------------------------------------------------------------------
# Generation parameters
# ---------------------------------------------------------------------------

N_TOTAL = 10_000
FRAUD_RATE = 0.017                    # ~1.7 % to match real Kaggle dataset
N_FRAUD = max(1, int(N_TOTAL * FRAUD_RATE))
N_NORMAL = N_TOTAL - N_FRAUD
SEED = 42

# V-feature shifted means for fraud class (real-world-inspired)
# Positive shift → higher score; negative → lower
FRAUD_SHIFTS: dict[str, float] = {
    "V1":  -3.5,
    "V4":   2.8,
    "V11": -2.1,
    "V14": -4.7,
    "V17": -3.2,
}


# ---------------------------------------------------------------------------
# Helper: generate Time column
# ---------------------------------------------------------------------------

def _generate_time(n: int, rng: np.random.Generator) -> np.ndarray:
    """
    Simulate transaction time over 48 hours (0..172800 seconds).
    Mix uniform background with a business-hours peak to mimic the
    bimodal pattern visible in the real dataset.
    """
    n_peak = int(n * 0.65)
    n_flat = n - n_peak

    # Business-hours peak: 08:00–20:00 on each day
    peak_seconds = np.concatenate([
        rng.uniform(8 * 3600, 20 * 3600, n_peak // 2),
        rng.uniform(8 * 3600 + 86400, 20 * 3600 + 86400, n_peak - n_peak // 2),
    ])
    flat_seconds = rng.uniform(0, 172800, n_flat)
    t = np.concatenate([peak_seconds, flat_seconds])
    rng.shuffle(t)
    return t


# ---------------------------------------------------------------------------
# Helper: generate Amount column
# ---------------------------------------------------------------------------

def _generate_amount(n: int, rng: np.random.Generator) -> np.ndarray:
    """
    Log-normal Amount distribution.
    Real dataset: mean≈88 USD, std≈250 USD, min=0, max≈25691.
    We achieve this by parameterising the underlying normal:
      ln(Amount+1) ~ N(mu_ln, sigma_ln)
    solved from the empirical first two moments.
    """
    # Parameters derived from method of moments
    mu_target = 88.0
    var_target = 250.0 ** 2
    # E[X] = exp(mu + sigma^2/2), Var[X] = (exp(sigma^2)-1)*exp(2*mu+sigma^2)
    # Solve for sigma_ln using log(1 + cv^2) where cv = std/mean
    cv2 = var_target / (mu_target ** 2)
    sigma_ln = float(np.sqrt(np.log(1 + cv2)))
    mu_ln = float(np.log(mu_target) - 0.5 * sigma_ln ** 2)
    amounts = rng.lognormal(mu_ln, sigma_ln, n)
    amounts = np.round(np.clip(amounts, 0.01, 30_000.0), 2)
    return amounts


# ---------------------------------------------------------------------------
# Helper: generate V1-V28 PCA features
# ---------------------------------------------------------------------------

def _build_cov(n_feats: int, rng: np.random.Generator) -> np.ndarray:
    """
    Build a random positive-definite covariance matrix for the V features.
    Using A^T A construction for positive definiteness, then normalising
    diagonal to unit variance so each feature has std≈1 before any shift.
    """
    A = rng.standard_normal((n_feats, n_feats))
    cov = A.T @ A / n_feats
    # Normalise to correlation matrix so features are comparable
    diag_sqrt = np.sqrt(np.diag(cov))
    corr = cov / np.outer(diag_sqrt, diag_sqrt)
    return corr


def _generate_v_features(
    n: int,
    cov: np.ndarray,
    shifts: dict[str, float],
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Sample V1-V28 from a multivariate normal then add per-feature shifts.
    shifts maps feature name → additive mean shift for this class.
    """
    n_feats = cov.shape[0]
    means = np.zeros(n_feats)
    for name, delta in shifts.items():
        idx = int(name[1:]) - 1   # "V1" → 0, "V14" → 13
        if 0 <= idx < n_feats:
            means[idx] += delta
    samples = rng.multivariate_normal(means, cov, n)
    return samples


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate(output_path: Path = OUTPUT_FILE, seed: int = SEED) -> pd.DataFrame:
    """Generate synthetic credit card fraud dataset and save to CSV."""
    t_start = time.perf_counter()
    rng = np.random.default_rng(seed)

    n_feats = 28   # V1-V28
    cov = _build_cov(n_feats, rng)

    print(f"Generating {N_TOTAL:,} transactions ({N_FRAUD} fraud, {N_NORMAL} normal)...")

    # --- Normal transactions --------------------------------------------------
    v_normal = _generate_v_features(N_NORMAL, cov, shifts={}, rng=rng)
    time_normal = _generate_time(N_NORMAL, rng)
    amount_normal = _generate_amount(N_NORMAL, rng)
    class_normal = np.zeros(N_NORMAL, dtype=int)

    # --- Fraud transactions ---------------------------------------------------
    v_fraud = _generate_v_features(N_FRAUD, cov, shifts=FRAUD_SHIFTS, rng=rng)
    time_fraud = _generate_time(N_FRAUD, rng)
    amount_fraud = _generate_amount(N_FRAUD, rng) * 1.8   # fraud amounts skew higher
    amount_fraud = np.round(np.clip(amount_fraud, 0.01, 30_000.0), 2)
    class_fraud = np.ones(N_FRAUD, dtype=int)

    # --- Assemble DataFrame ---------------------------------------------------
    v_cols = {f"V{i+1}": np.concatenate([v_normal[:, i], v_fraud[:, i]]) for i in range(n_feats)}
    data = {
        "Time": np.concatenate([time_normal, time_fraud]),
        **v_cols,
        "Amount": np.concatenate([amount_normal, amount_fraud]),
        "Class": np.concatenate([class_normal, class_fraud]),
    }
    df = pd.DataFrame(data)

    # Shuffle to mix fraud and normal rows
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    # Sort by Time to mimic real dataset ordering
    df = df.sort_values("Time").reset_index(drop=True)

    # --- Save -----------------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    elapsed_ms = (time.perf_counter() - t_start) * 1000
    file_size_kb = output_path.stat().st_size / 1024

    fraud_count = int(df["Class"].sum())
    fraud_rate = fraud_count / len(df)

    print(f"  Rows generated : {len(df):,}")
    print(f"  Fraud count    : {fraud_count:,}")
    print(f"  Fraud rate     : {fraud_rate:.2%}")
    print(f"  File size      : {file_size_kb:.1f} KB")
    print(f"  Elapsed        : {elapsed_ms:.1f} ms")
    print(f"  Saved          → {output_path}")
    return df


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    generate()
