"""
Classical ML baseline for network intrusion detection using NSL-KDD dataset.
Trains RandomForest and XGBoost classifiers for binary classification
(normal vs. attack) and saves results to data/classical_results.json.

NSL-KDD format: 41 features (duration, protocol_type, service, flag, + 38
numeric features) + label + difficulty_score (42 total columns, no header).
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
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

# NSL-KDD column names (41 features + label + difficulty)
NSL_KDD_COLUMNS = [
    "duration", "protocol_type", "service", "flag",
    "src_bytes", "dst_bytes", "land", "wrong_fragment", "urgent",
    "hot", "num_failed_logins", "logged_in", "num_compromised",
    "root_shell", "su_attempted", "num_root", "num_file_creations",
    "num_shells", "num_access_files", "num_outbound_cmds", "is_host_login",
    "is_guest_login", "count", "srv_count", "serror_rate", "srv_serror_rate",
    "rerror_rate", "srv_rerror_rate", "same_srv_rate", "diff_srv_rate",
    "srv_diff_host_rate", "dst_host_count", "dst_host_srv_count",
    "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate",
    "dst_host_serror_rate", "dst_host_srv_serror_rate",
    "dst_host_rerror_rate", "dst_host_srv_rerror_rate",
    "label", "difficulty",
]

CATEGORICAL_COLS = ["protocol_type", "service", "flag"]

# Attack categories → binary label mapping
# Any non-"normal" label is an attack
def _binary_label(label: str) -> int:
    return 0 if label.strip().lower() == "normal" else 1


def load_data() -> tuple[np.ndarray, np.ndarray]:
    """Load NSL-KDD training data, encode categoricals, return (X, y)."""
    candidates = [
        Path(__file__).parent.parent.parent / "datasets" / "security" / "KDDTrain+.txt",
        Path(__file__).parent.parent.parent / "datasets" / "security" / "nsl-kdd" / "KDDTrain+.txt",
        Path("/mnt/deepa/quantum/datasets/security/KDDTrain+.txt"),
        DATA_DIR / "KDDTrain+.txt",
    ]
    txt_path = None
    for p in candidates:
        if p.exists():
            txt_path = p
            break

    if txt_path is not None:
        print(f"Loading NSL-KDD data from {txt_path}")
        df = pd.read_csv(txt_path, header=None, names=NSL_KDD_COLUMNS)
    else:
        print("NSL-KDD data not found — generating demo data")
        rng = np.random.default_rng(42)
        n = 3000
        X = rng.standard_normal((n, 41))
        y = (rng.random(n) < 0.45).astype(int)   # ~45% attacks
        return X, y

    # Binary target
    y = df["label"].apply(_binary_label).values

    # Encode categorical features
    for col in CATEGORICAL_COLS:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))

    feature_cols = [c for c in df.columns if c not in ("label", "difficulty")]
    X = df[feature_cols].values.astype(float)

    # Use a representative sample for demo speed (cap at 20 000 rows)
    if len(X) > 20_000:
        idx = np.random.default_rng(42).choice(len(X), 20_000, replace=False)
        X, y = X[idx], y[idx]

    print(f"  Samples: {len(X)}  Attack rate: {y.mean():.2%}")
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
        "classification_report": classification_report(
            y_test, y_pred, target_names=["normal", "attack"], output_dict=True
        ),
    }


def main():
    X, y = load_data()

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train: {len(X_train)}  Test: {len(X_test)}")

    results = []

    # ── Random Forest ──────────────────────────────────────────────────────────
    print("\nTraining RandomForest...")
    t0 = time.perf_counter()
    rf = RandomForestClassifier(
        n_estimators=100, class_weight="balanced", random_state=42, n_jobs=-1
    )
    rf.fit(X_train, y_train)
    train_time = time.perf_counter() - t0
    r = evaluate("RandomForest", rf, X_test, y_test)
    r["train_time_s"] = round(train_time, 4)
    results.append(r)
    print(f"  RF  → accuracy={r['accuracy']:.4f}  f1={r['f1']:.4f}  auc={r['roc_auc']:.4f}")

    # ── XGBoost ───────────────────────────────────────────────────────────────
    try:
        from xgboost import XGBClassifier
        print("\nTraining XGBoost...")
        t0 = time.perf_counter()
        scale_pos = int((y_train == 0).sum() / max((y_train == 1).sum(), 1))
        xgb = XGBClassifier(
            n_estimators=100,
            scale_pos_weight=scale_pos,
            random_state=42,
            eval_metric="logloss",
            verbosity=0,
        )
        xgb.fit(X_train, y_train)
        train_time = time.perf_counter() - t0
        r = evaluate("XGBoost", xgb, X_test, y_test)
        r["train_time_s"] = round(train_time, 4)
        results.append(r)
        print(f"  XGB → accuracy={r['accuracy']:.4f}  f1={r['f1']:.4f}  auc={r['roc_auc']:.4f}")
    except ImportError:
        print("XGBoost not installed — skipping (pip install xgboost)")

    # ── Save ───────────────────────────────────────────────────────────────────
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved → {RESULTS_FILE}")
    return results


if __name__ == "__main__":
    main()
