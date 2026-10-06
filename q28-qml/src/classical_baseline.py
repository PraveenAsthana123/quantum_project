"""
Classical ML baseline for wine quality classification.
Trains SVM and RandomForest classifiers, evaluates them, and saves
results to data/classical_results.json.

Dataset: winequalityN.csv (binary label: quality >= 6 → "good", else "bad")
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent / "data"
RESULTS_FILE = DATA_DIR / "classical_results.json"

# Shared dataset folder
DATASET_PATH = Path(__file__).parent.parent.parent / "datasets" / "qml" / "winequalityN.csv"


def load_wine_data() -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Load wine quality data and create binary labels (good=1 if quality>=6)."""
    path = DATASET_PATH
    if not path.exists():
        # Fallback: look inside the qml datasets folder in the parent
        path = Path(__file__).parent.parent / "data" / "winequalityN.csv"
    if path.exists():
        print(f"Loading wine data from {path}")
        df = pd.read_csv(path)
    else:
        print("winequalityN.csv not found — generating synthetic demo data")
        rng = np.random.default_rng(42)
        n = 500
        feature_names = [
            "fixed_acidity", "volatile_acidity", "citric_acid",
            "residual_sugar", "chlorides", "free_sulfur_dioxide",
            "total_sulfur_dioxide", "density", "pH", "sulphates", "alcohol",
        ]
        X = rng.standard_normal((n, len(feature_names)))
        y = (rng.random(n) > 0.45).astype(int)
        return X, y, feature_names

    # Drop 'type' column (categorical wine type) — encode it instead
    if "type" in df.columns:
        df["type"] = (df["type"] == "red").astype(int)

    feature_cols = [c for c in df.columns if c != "quality"]
    X = df[feature_cols].values.astype(float)
    # Binary classification: good (1) if quality >= 6
    y = (df["quality"] >= 6).astype(int).values
    print(f"  Loaded {len(df)} samples | good={y.sum()} bad={(1-y).sum()}")
    return X, y, feature_cols


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
        "classification_report": classification_report(
            y_test, y_pred, output_dict=True, zero_division=0
        ),
    }


def main():
    print("=" * 60)
    print("  Q28 QML — Classical Baseline (Wine Quality)")
    print("=" * 60)

    X, y, feature_names = load_wine_data()

    # Impute any NaN values (wine dataset has ~38 NaNs across 6498 rows)
    imputer = SimpleImputer(strategy="median")
    X = imputer.fit_transform(X)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train: {len(X_train)}  Test: {len(X_test)}  Good-rate: {y_test.mean():.2%}")

    results = []

    # ---- SVM (RBF kernel) ----
    print("\nTraining SVM (RBF)...")
    t0 = time.perf_counter()
    svm = SVC(kernel="rbf", C=10.0, gamma="scale", probability=True, random_state=42)
    svm.fit(X_train, y_train)
    train_time = time.perf_counter() - t0

    cv_scores = cross_val_score(svm, X_scaled, y, cv=5, scoring="accuracy")
    r = evaluate("SVM-RBF", svm, X_test, y_test)
    r["train_time_s"] = round(train_time, 4)
    r["cv_accuracy_mean"] = float(cv_scores.mean())
    r["cv_accuracy_std"] = float(cv_scores.std())
    results.append(r)
    print(f"  SVM  → accuracy={r['accuracy']:.4f}  f1={r['f1']:.4f}  auc={r['roc_auc']:.4f}  cv={r['cv_accuracy_mean']:.4f}±{r['cv_accuracy_std']:.4f}")

    # ---- Random Forest ----
    print("\nTraining RandomForest...")
    t0 = time.perf_counter()
    rf = RandomForestClassifier(
        n_estimators=200, max_depth=None, class_weight="balanced",
        random_state=42, n_jobs=-1
    )
    rf.fit(X_train, y_train)
    train_time = time.perf_counter() - t0

    cv_scores_rf = cross_val_score(rf, X_scaled, y, cv=5, scoring="accuracy")
    r = evaluate("RandomForest", rf, X_test, y_test)
    r["train_time_s"] = round(train_time, 4)
    r["cv_accuracy_mean"] = float(cv_scores_rf.mean())
    r["cv_accuracy_std"] = float(cv_scores_rf.std())

    # Feature importances
    r["feature_importances"] = dict(
        zip(feature_names, rf.feature_importances_.tolist())
    )
    results.append(r)
    print(f"  RF   → accuracy={r['accuracy']:.4f}  f1={r['f1']:.4f}  auc={r['roc_auc']:.4f}  cv={r['cv_accuracy_mean']:.4f}±{r['cv_accuracy_std']:.4f}")

    # ---- Summary ----
    best = max(results, key=lambda x: x["roc_auc"])
    summary = {
        "task": "wine-quality-binary",
        "n_samples_train": int(len(X_train)),
        "n_samples_test": int(len(X_test)),
        "n_features": int(X.shape[1]),
        "best_model": best["model"],
        "best_roc_auc": best["roc_auc"],
        "results": results,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved → {RESULTS_FILE}")
    return summary


if __name__ == "__main__":
    main()
