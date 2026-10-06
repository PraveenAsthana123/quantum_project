"""
Healthcare Lab Synthetic Data Generator
========================================
Generates a realistic patient diabetes screening dataset (2,000 rows)
modelled on the Pima Indians Diabetes Database (NIDDK / UCI ML Repository).

Columns (matching Pima Indians schema exactly):
    Pregnancies      – number of pregnancies (0–17)
    Glucose          – plasma glucose concentration 2h OGTT (mg/dL, 0–300)
    BloodPressure    – diastolic blood pressure (mmHg, 0–130)
    SkinThickness    – triceps skinfold thickness (mm, 0–100)
    Insulin          – 2-hour serum insulin (µU/mL, 0–900)
    BMI              – body mass index (kg/m², 0–50)
    DiabetesPedigreeFunction – DPF score (0.08–2.42)
    Age              – age in years (20–90)
    Outcome          – diabetes diagnosis (0=No, 1=Yes)

Class balance: ~35 % positive (slightly higher than Pima 34.9 %)

Real Pima statistics used to parameterise generators:
  Glucose: non-diabetic μ=109.98 σ=26.1; diabetic μ=141.3 σ=31.9
  BMI:     non-diabetic μ=30.3 σ=7.1;  diabetic μ=35.4 σ=7.2
  Age:     non-diabetic μ=31.2 σ=11.6; diabetic μ=37.1 σ=10.9

Output:
    qc-healthcare-lab/data/diabetes_synthetic.csv

Usage:
    python src/generate_data.py

Version: 1.0.0
Date: 2026-10-06
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = DATA_DIR / "diabetes_synthetic.csv"

# ---------------------------------------------------------------------------
# Generation parameters
# ---------------------------------------------------------------------------

N_ROWS = 2_000
POSITIVE_RATE = 0.35    # ~35 % diabetes positive
SEED = 42


# ---------------------------------------------------------------------------
# Per-class distribution parameters  (mean, std)
# ---------------------------------------------------------------------------

PARAMS: dict[str, dict[str, tuple[float, float]]] = {
    "Glucose": {
        "neg": (109.98, 26.1),
        "pos": (141.30, 31.9),
    },
    "BloodPressure": {
        "neg": (70.6, 11.5),
        "pos": (74.6, 12.1),
    },
    "SkinThickness": {
        "neg": (19.7, 14.7),
        "pos": (32.5, 11.5),
    },
    "Insulin": {
        "neg": (68.8, 98.9),
        "pos": (100.3, 138.7),
    },
    "BMI": {
        "neg": (30.3, 7.1),
        "pos": (35.4, 7.2),
    },
    "DiabetesPedigreeFunction": {
        "neg": (0.43, 0.30),
        "pos": (0.55, 0.37),
    },
    "Age": {
        "neg": (31.2, 11.6),
        "pos": (37.1, 10.9),
    },
}

# Column bounds [min, max] for realistic clipping
BOUNDS: dict[str, tuple[float, float]] = {
    "Pregnancies": (0.0, 17.0),
    "Glucose": (44.0, 300.0),
    "BloodPressure": (24.0, 130.0),
    "SkinThickness": (7.0, 100.0),
    "Insulin": (14.0, 900.0),
    "BMI": (18.0, 67.0),
    "DiabetesPedigreeFunction": (0.078, 2.42),
    "Age": (20.0, 90.0),
}

# The Pima dataset uses 0 to denote missing for these columns
# (physiologically impossible; replicated for authentic schema)
ZERO_MISSING_COLS = {"Glucose", "BloodPressure", "SkinThickness", "Insulin", "BMI"}
ZERO_MISSING_RATE = 0.04   # ~4 % missing per column, matching real Pima rates


# ---------------------------------------------------------------------------
# Helper: sample a clipped normal column
# ---------------------------------------------------------------------------

def _sample_col(
    name: str,
    n: int,
    class_key: str,
    rng: np.random.Generator,
    is_int: bool = False,
) -> np.ndarray:
    mu, sigma = PARAMS[name][class_key]
    lo, hi = BOUNDS[name]
    samples = rng.normal(mu, sigma, n)
    samples = np.clip(samples, lo, hi)
    if is_int:
        samples = np.round(samples).astype(float)
    return samples


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate(output_path: Path = OUTPUT_FILE, seed: int = SEED) -> pd.DataFrame:
    """Generate synthetic diabetes screening dataset and save to CSV."""
    t_start = time.perf_counter()
    rng = np.random.default_rng(seed)

    n_pos = int(N_ROWS * POSITIVE_RATE)
    n_neg = N_ROWS - n_pos

    print(f"Generating {N_ROWS:,} patient records ({n_pos} positive, {n_neg} negative)...")

    rows: dict[str, np.ndarray] = {}

    # --- Pregnancies (discrete, slightly higher for positive class) ----------
    preg_neg = rng.integers(0, 14, n_neg).astype(float)
    preg_pos = rng.integers(0, 17, n_pos).astype(float)
    # Positive class skews toward more pregnancies
    preg_pos = np.clip(np.round(rng.normal(4.2, 3.6, n_pos)), 0, 17)
    rows["Pregnancies"] = np.concatenate([preg_neg, preg_pos])

    # --- Continuous features -------------------------------------------------
    for col in ["Glucose", "BloodPressure", "SkinThickness", "Insulin", "BMI",
                "DiabetesPedigreeFunction", "Age"]:
        neg_vals = _sample_col(col, n_neg, "neg", rng)
        pos_vals = _sample_col(col, n_pos, "pos", rng)
        rows[col] = np.concatenate([neg_vals, pos_vals])

    # --- Outcome label -------------------------------------------------------
    rows["Outcome"] = np.concatenate([np.zeros(n_neg, int), np.ones(n_pos, int)])

    # --- Assemble and shuffle ------------------------------------------------
    df = pd.DataFrame(rows)
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)

    # --- Inject missing values (encoded as 0, authentic to Pima schema) ------
    for col in ZERO_MISSING_COLS:
        n_missing = int(N_ROWS * ZERO_MISSING_RATE)
        zero_idx = rng.choice(len(df), n_missing, replace=False)
        df.loc[zero_idx, col] = 0.0

    # --- Round and type-cast -------------------------------------------------
    int_cols = ["Pregnancies", "Outcome"]
    round2_cols = ["Glucose", "BloodPressure", "SkinThickness", "Insulin"]
    round4_cols = ["BMI", "DiabetesPedigreeFunction", "Age"]

    for c in int_cols:
        df[c] = df[c].astype(int)
    for c in round2_cols:
        df[c] = df[c].round(1)
    for c in round4_cols:
        df[c] = df[c].round(4)

    # --- Save ----------------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    elapsed_ms = (time.perf_counter() - t_start) * 1000
    file_size_kb = output_path.stat().st_size / 1024
    actual_pos_rate = df["Outcome"].mean()

    print(f"  Rows generated   : {len(df):,}")
    print(f"  Positive cases   : {df['Outcome'].sum():,}  ({actual_pos_rate:.1%})")
    print(f"  Zero-encoded cols: {', '.join(sorted(ZERO_MISSING_COLS))}")
    print(f"  File size        : {file_size_kb:.1f} KB")
    print(f"  Elapsed          : {elapsed_ms:.1f} ms")
    print(f"  Saved            → {output_path}")
    return df


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    generate()
