"""
Classical ML baseline for credit card fraud detection.
Trains LogisticRegression, RandomForest, and XGBoost classifiers,
evaluates them, and saves results to data/classical_results.json.
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent / "data"
RESULTS_FILE = DATA_DIR / "classical_results.json"


def load_data() -> tuple[np.ndarray, np.ndarray]:
    # Check project-local data first, then shared data folder
    csv_path = DATA_DIR / "creditcard.csv"
    if not csv_path.exists():
        csv_path = DATA_DIR / "creditcardfraud" / "creditcard.csv"
    if not csv_path.exists():
        # Try shared data folder
        csv_path = Path(__file__).parent.parent.parent / "data" / "creditcardfraud" / "creditcard.csv"
    if csv_path.exists():
        print(f"Loading data from {csv_path}")
        df = pd.read_csv(csv_path)
    else:
        print("creditcard.csv not found — generating demo data (run: qlab data qc-banking-lab)")
        rng = np.random.default_rng(42)
        n = 5000
        X = rng.standard_normal((n, 29))
        y = (rng.random(n) < 0.02).astype(int)
        return X, y

    feature_cols = [c for c in df.columns if c not in ("Class", "Time")]
    X = df[feature_cols].values
    y = df["Class"].values
    return X, y


def evaluate(name: str, model, X_test: np.ndarray, y_test: np.ndarray) -> dict:
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
        "classification_report": classification_report(y_test, y_pred, output_dict=True),
    }


def main():
    X, y = load_data()

    # Split FIRST — scaler must be fit on train data only to prevent leakage
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)   # fit on train only
    X_test = scaler.transform(X_test)          # transform test (no fit)

    results = []

    # Logistic Regression
    print("Training LogisticRegression...")
    t0 = time.perf_counter()
    lr = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    lr.fit(X_train, y_train)
    train_time = time.perf_counter() - t0
    r = evaluate("LogisticRegression", lr, X_test, y_test)
    r["train_time_s"] = round(train_time, 4)
    results.append(r)
    print(f"  LR  → accuracy={r['accuracy']:.4f}  f1={r['f1']:.4f}  auc={r['roc_auc']:.4f}")

    # Random Forest
    print("Training RandomForest...")
    t0 = time.perf_counter()
    rf = RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    train_time = time.perf_counter() - t0
    r = evaluate("RandomForest", rf, X_test, y_test)
    r["train_time_s"] = round(train_time, 4)
    results.append(r)
    print(f"  RF  → accuracy={r['accuracy']:.4f}  f1={r['f1']:.4f}  auc={r['roc_auc']:.4f}")

    # XGBoost (optional)
    try:
        from xgboost import XGBClassifier
        print("Training XGBoost...")
        t0 = time.perf_counter()
        scale_pos = int((y == 0).sum() / max((y == 1).sum(), 1))
        xgb = XGBClassifier(
            n_estimators=100, scale_pos_weight=scale_pos,
            random_state=42, eval_metric="logloss", verbosity=0
        )
        xgb.fit(X_train, y_train)
        train_time = time.perf_counter() - t0
        r = evaluate("XGBoost", xgb, X_test, y_test)
        r["train_time_s"] = round(train_time, 4)
        results.append(r)
        print(f"  XGB → accuracy={r['accuracy']:.4f}  f1={r['f1']:.4f}  auc={r['roc_auc']:.4f}")
    except ImportError:
        print("XGBoost not installed — skipping (pip install xgboost)")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved → {RESULTS_FILE}")
    return results


if __name__ == "__main__":
    main()
