"""
Finance Lab End-to-End Demo
=============================
Demonstrates the full quantum vs classical options pricing pipeline:

    Step 1 – Load / generate options data
    Step 2 – Preprocessing (normalise S, K, sigma; derive moneyness features)
    Step 3 – Classical analytical pricing (Black-Scholes), print MAE / RMSE
    Step 4 – ML pricing models (LinearRegression, RandomForest)
    Step 5 – Comparison table
    Step 6 – PASS / FAIL gate (RMSE < 5.0)

Run:
    python src/demo.py

The script is self-contained: if options_synthetic.csv is absent it calls
generate_data.generate() to produce it first.

Version: 1.0.0
Date: 2026-10-06
"""
from __future__ import annotations

import importlib.util
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SRC_DIR = Path(__file__).parent
LAB_DIR = SRC_DIR.parent
DATA_DIR = LAB_DIR / "data"
SYNTHETIC_CSV = DATA_DIR / "options_synthetic.csv"

DIVIDER = "=" * 72


def _header(step: int, title: str) -> None:
    print(f"\n{DIVIDER}")
    print(f"  Step {step}: {title}")
    print(DIVIDER)


# ---------------------------------------------------------------------------
# Step 1: Data loading
# ---------------------------------------------------------------------------

def step1_load() -> pd.DataFrame:
    _header(1, "Data Loading / Generation")

    if SYNTHETIC_CSV.exists():
        t0 = time.perf_counter()
        df = pd.read_csv(SYNTHETIC_CSV)
        load_ms = (time.perf_counter() - t0) * 1000
        print(f"  Loaded : {SYNTHETIC_CSV.name}  ({load_ms:.1f} ms)")
    else:
        print("  options_synthetic.csv not found — generating...")
        spec = importlib.util.spec_from_file_location("generate_data", SRC_DIR / "generate_data.py")
        gen_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen_mod)
        df = gen_mod.generate()

    n_calls = (df["option_type"] == "call").sum()
    n_puts = (df["option_type"] == "put").sum()
    print(f"  Shape            : {df.shape}")
    print(f"  Calls / Puts     : {n_calls} / {n_puts}")
    print(f"  Price range      : ${df['option_price'].min():.2f} – ${df['option_price'].max():.2f}")
    print(f"  Spot range (S)   : ${df['S'].min():.0f} – ${df['S'].max():.0f}")
    print(f"  Strike range (K) : ${df['K'].min():.0f} – ${df['K'].max():.0f}")
    return df


# ---------------------------------------------------------------------------
# Step 2: Preprocessing
# ---------------------------------------------------------------------------

def step2_preprocess(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    _header(2, "Preprocessing — Feature Engineering + Scaling")

    # Encode option type: call=1, put=0
    df = df.copy()
    df["is_call"] = (df["option_type"] == "call").astype(float)

    raw_features = ["S", "K", "T", "r", "sigma", "moneyness", "log_moneyness", "is_call"]
    X_raw = df[raw_features].values.astype(float)
    y = df["option_price"].values.astype(float)
    y_theo = df["theo_price"].values.astype(float)   # ground truth BS price

    print(f"  Features         : {raw_features}")
    print(f"  Before scaling (S col): mean={X_raw[:, 0].mean():.2f}  std={X_raw[:, 0].std():.2f}")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    print(f"  After scaling  (S col): mean={X_scaled[:, 0].mean():.4f}  std={X_scaled[:, 0].std():.4f}")
    print(f"  Target mean / std : {y.mean():.4f} / {y.std():.4f}")

    return X_scaled, y, y_theo


# ---------------------------------------------------------------------------
# Step 3: Classical Black-Scholes pricing
# ---------------------------------------------------------------------------

def step3_black_scholes(df: pd.DataFrame) -> dict:
    _header(3, "Classical Analytical Pricing — Black-Scholes")

    t0 = time.perf_counter()
    y_true = df["option_price"].values
    y_pred = df["theo_price"].values
    elapsed_ms = (time.perf_counter() - t0) * 1000

    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))

    print(f"  MAE   : {mae:.4f}")
    print(f"  RMSE  : {rmse:.4f}")
    print(f"  Note  : residual is market noise (~{rmse:.2f} = ~{100*rmse/y_true.mean():.1f}% of avg price)")
    print(f"  Time  : {elapsed_ms:.2f} ms")

    return {
        "model": "Black-Scholes (analytical)",
        "mae": mae,
        "rmse": rmse,
        "time_ms": round(elapsed_ms, 2),
    }


# ---------------------------------------------------------------------------
# Step 4: ML pricing models
# ---------------------------------------------------------------------------

def step4_ml(
    X: np.ndarray, y: np.ndarray
) -> list[dict]:
    _header(4, "ML Pricing Models — LinearRegression + RandomForest")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )
    print(f"  Train / Test split: {len(X_train)} / {len(X_test)} rows")

    results = []

    # Linear Regression
    print("\n  Training LinearRegression...")
    t0 = time.perf_counter()
    lr = LinearRegression()
    lr.fit(X_train, y_train)
    train_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    y_pred_lr = lr.predict(X_test)
    pred_ms = (time.perf_counter() - t0) * 1000

    mae_lr = float(mean_absolute_error(y_test, y_pred_lr))
    rmse_lr = float(np.sqrt(mean_squared_error(y_test, y_pred_lr)))
    total_ms_lr = train_ms + pred_ms
    print(f"    MAE={mae_lr:.4f}  RMSE={rmse_lr:.4f}  time={total_ms_lr:.1f}ms")
    results.append({"model": "LinearRegression", "mae": mae_lr, "rmse": rmse_lr, "time_ms": round(total_ms_lr, 2)})

    # Random Forest Regressor
    print("\n  Training RandomForest...")
    t0 = time.perf_counter()
    rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    train_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    y_pred_rf = rf.predict(X_test)
    pred_ms = (time.perf_counter() - t0) * 1000

    mae_rf = float(mean_absolute_error(y_test, y_pred_rf))
    rmse_rf = float(np.sqrt(mean_squared_error(y_test, y_pred_rf)))
    total_ms_rf = train_ms + pred_ms
    print(f"    MAE={mae_rf:.4f}  RMSE={rmse_rf:.4f}  time={total_ms_rf:.1f}ms")
    results.append({"model": "RandomForest", "mae": mae_rf, "rmse": rmse_rf, "time_ms": round(total_ms_rf, 2)})

    return results


# ---------------------------------------------------------------------------
# Step 5: Comparison table
# ---------------------------------------------------------------------------

def step5_comparison(bs_result: dict, ml_results: list[dict]) -> None:
    _header(5, "Model Comparison Table")

    all_results = [bs_result] + ml_results
    header = f"  {'Model':<32} {'MAE':>8} {'RMSE':>8} {'Time(ms)':>10}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for r in all_results:
        print(f"  {r['model']:<32} {r['mae']:>8.4f} {r['rmse']:>8.4f} {r['time_ms']:>10.1f}")


# ---------------------------------------------------------------------------
# Step 6: PASS / FAIL gate
# ---------------------------------------------------------------------------

def step6_gate(bs_result: dict, ml_results: list[dict]) -> None:
    _header(6, "PASS / FAIL Gate (RMSE < 5.0)")

    all_results = [bs_result] + ml_results
    all_pass = True
    for r in all_results:
        status = "PASS" if r["rmse"] < 5.0 else "FAIL"
        if status == "FAIL":
            all_pass = False
        indicator = "✓" if status == "PASS" else "✗"
        print(f"  {indicator} {r['model']:<32}  RMSE={r['rmse']:.4f}  → {status}")

    print()
    if all_pass:
        print("  OVERALL: ALL MODELS PASS")
    else:
        print("  OVERALL: ONE OR MORE MODELS FAILED")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    wall_start = time.perf_counter()
    print(f"\n{'#' * 72}")
    print("  QC Finance Lab — End-to-End Options Pricing Demo")
    print(f"{'#' * 72}")

    df = step1_load()
    X, y, y_theo = step2_preprocess(df)
    bs_result = step3_black_scholes(df)
    ml_results = step4_ml(X, y)
    step5_comparison(bs_result, ml_results)
    step6_gate(bs_result, ml_results)

    wall_ms = (time.perf_counter() - wall_start) * 1000
    print(f"\n{DIVIDER}")
    print(f"  Total wall time: {wall_ms / 1000:.1f} s")
    print(f"{DIVIDER}\n")


if __name__ == "__main__":
    main()
