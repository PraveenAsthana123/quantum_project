"""
Classical ML baseline for healthcare disease prediction.
Trains LogisticRegression, RandomForest, and XGBoost classifiers on:
  - Pima Indians Diabetes dataset (diabetes.csv)
  - Heart Disease UCI dataset (heart.csv)
  - Heart Failure Clinical Records (heart_failure_clinical_records_dataset.csv)
Saves results to data/classical_results.json with accuracy, AUC, F1.
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SRC_DIR = Path(__file__).parent
_LAB_DIR = _SRC_DIR.parent
DATA_DIR = _LAB_DIR / "data"

# Shared dataset folder checked as fallback
_SHARED_DATASETS = _LAB_DIR.parent / "datasets" / "healthcare"

RESULTS_FILE = DATA_DIR / "classical_results.json"


def _find_csv(filename: str) -> Path:
    """Return first existing path: project-local data/ then shared datasets/."""
    for candidate in [DATA_DIR / filename, _SHARED_DATASETS / filename]:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"{filename} not found in {DATA_DIR} or {_SHARED_DATASETS}"
    )


# ---------------------------------------------------------------------------
# Dataset loaders
# ---------------------------------------------------------------------------

def load_diabetes() -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Pima Indians Diabetes — 768 rows, 8 features, binary target."""
    path = _find_csv("diabetes.csv")
    print(f"  Loading diabetes data from {path}")
    df = pd.read_csv(path)
    target = "Outcome"
    feature_cols = [c for c in df.columns if c != target]
    X = df[feature_cols].values.astype(float)
    y = df[target].values.astype(int)
    return X, y, feature_cols


def load_heart() -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Heart Disease UCI (Cleveland-style) — 918 rows, mixed features, binary target."""
    path = _find_csv("heart.csv")
    print(f"  Loading heart disease data from {path}")
    df = pd.read_csv(path)
    target = "HeartDisease"

    # Encode categorical columns
    cat_cols = df.select_dtypes(include="object").columns.tolist()
    for col in cat_cols:
        df[col] = LabelEncoder().fit_transform(df[col])

    feature_cols = [c for c in df.columns if c != target]
    X = df[feature_cols].values.astype(float)
    y = df[target].values.astype(int)
    return X, y, feature_cols


def load_heart_failure() -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Heart Failure Clinical Records — 299 rows, binary death event target."""
    path = _find_csv("heart_failure_clinical_records_dataset.csv")
    print(f"  Loading heart failure data from {path}")
    df = pd.read_csv(path)
    target = "DEATH_EVENT"
    feature_cols = [c for c in df.columns if c != target]
    X = df[feature_cols].values.astype(float)
    y = df[target].values.astype(int)
    return X, y, feature_cols


# ---------------------------------------------------------------------------
# Evaluation helper
# ---------------------------------------------------------------------------

def evaluate(name: str, model: Any, X_test: np.ndarray, y_test: np.ndarray) -> dict:
    t0 = time.perf_counter()
    y_pred = model.predict(X_test)
    predict_time = time.perf_counter() - t0

    try:
        y_prob = model.predict_proba(X_test)[:, 1]
        auc = float(roc_auc_score(y_test, y_prob))
    except Exception:
        auc = 0.0

    cm = confusion_matrix(y_test, y_pred)
    return {
        "model": name,
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": auc,
        "confusion_matrix": cm.tolist(),
        "predict_time_s": round(predict_time, 4),
        "classification_report": classification_report(
            y_test, y_pred, output_dict=True
        ),
    }


# ---------------------------------------------------------------------------
# Training pipeline
# ---------------------------------------------------------------------------

def run_dataset(
    dataset_name: str,
    X: np.ndarray,
    y: np.ndarray,
) -> list[dict]:
    """Scale, split, train all classifiers, return list of result dicts."""
    print(f"\n  Dataset: {dataset_name}  shape={X.shape}  pos_rate={y.mean():.2%}")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )

    results: list[dict] = []

    # --- Logistic Regression ------------------------------------------------
    print("  Training LogisticRegression...")
    t0 = time.perf_counter()
    lr = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    lr.fit(X_train, y_train)
    r = evaluate("LogisticRegression", lr, X_test, y_test)
    r["train_time_s"] = round(time.perf_counter() - t0, 4)
    r["dataset"] = dataset_name
    results.append(r)
    print(
        f"    LR  → acc={r['accuracy']:.4f}  f1={r['f1']:.4f}  auc={r['roc_auc']:.4f}"
    )

    # --- Random Forest ------------------------------------------------------
    print("  Training RandomForest...")
    t0 = time.perf_counter()
    rf = RandomForestClassifier(
        n_estimators=100, class_weight="balanced", random_state=42, n_jobs=-1
    )
    rf.fit(X_train, y_train)
    r = evaluate("RandomForest", rf, X_test, y_test)
    r["train_time_s"] = round(time.perf_counter() - t0, 4)
    r["dataset"] = dataset_name
    results.append(r)
    print(
        f"    RF  → acc={r['accuracy']:.4f}  f1={r['f1']:.4f}  auc={r['roc_auc']:.4f}"
    )

    # --- XGBoost (optional) -------------------------------------------------
    try:
        from xgboost import XGBClassifier

        print("  Training XGBoost...")
        t0 = time.perf_counter()
        scale_pos = int((y == 0).sum() / max((y == 1).sum(), 1))
        xgb = XGBClassifier(
            n_estimators=100,
            scale_pos_weight=scale_pos,
            random_state=42,
            eval_metric="logloss",
            verbosity=0,
        )
        xgb.fit(X_train, y_train)
        r = evaluate("XGBoost", xgb, X_test, y_test)
        r["train_time_s"] = round(time.perf_counter() - t0, 4)
        r["dataset"] = dataset_name
        results.append(r)
        print(
            f"    XGB → acc={r['accuracy']:.4f}  f1={r['f1']:.4f}  auc={r['roc_auc']:.4f}"
        )
    except ImportError:
        print("  XGBoost not installed — skipping (pip install xgboost)")

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> list[dict]:
    print("=" * 60)
    print("QC Healthcare Lab — Classical ML Baseline")
    print("=" * 60)

    all_results: list[dict] = []

    # Diabetes
    try:
        X, y, _ = load_diabetes()
        all_results.extend(run_dataset("diabetes", X, y))
    except FileNotFoundError as e:
        print(f"  WARNING: {e}")

    # Heart disease
    try:
        X, y, _ = load_heart()
        all_results.extend(run_dataset("heart_disease", X, y))
    except FileNotFoundError as e:
        print(f"  WARNING: {e}")

    # Heart failure
    try:
        X, y, _ = load_heart_failure()
        all_results.extend(run_dataset("heart_failure", X, y))
    except FileNotFoundError as e:
        print(f"  WARNING: {e}")

    if not all_results:
        print("No datasets loaded — check paths and re-run.")
        return []

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved → {RESULTS_FILE}")

    # Summary table
    print("\n--- Summary ---")
    print(f"{'Dataset':<20} {'Model':<22} {'Acc':>6}  {'F1':>6}  {'AUC':>6}")
    print("-" * 62)
    for r in all_results:
        print(
            f"{r['dataset']:<20} {r['model']:<22} "
            f"{r['accuracy']:>6.4f}  {r['f1']:>6.4f}  {r['roc_auc']:>6.4f}"
        )

    return all_results


if __name__ == "__main__":
    main()
