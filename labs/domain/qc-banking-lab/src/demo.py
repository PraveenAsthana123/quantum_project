"""
Banking Lab End-to-End Demo
==============================
Demonstrates the full quantum vs classical fraud detection pipeline:

    Step 1 – Data loading / generation
    Step 2 – Preprocessing (StandardScaler)
    Step 3 – Train / test split (80 / 20)
    Step 4 – Classical ML  (LogisticRegression, RandomForest, XGBoost)
    Step 5 – Quantum ML    (VQC via PennyLane, 100-sample subset)
    Step 6 – Comparison table
    Step 7 – PASS / FAIL gate (accuracy > 0.85)

Run:
    python src/demo.py

The script is self-contained: if creditcard_synthetic.csv is absent it
calls generate_data.generate() to produce it first.

Dependencies (all already required by lab):
    numpy, pandas, scikit-learn, pennylane, jax

Version: 1.0.0
Date: 2026-10-06
"""
from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SRC_DIR = Path(__file__).parent
LAB_DIR = SRC_DIR.parent
DATA_DIR = LAB_DIR / "data"
SYNTHETIC_CSV = DATA_DIR / "creditcard_synthetic.csv"
REAL_CSV = DATA_DIR / "creditcard.csv"

# ---------------------------------------------------------------------------
# Pretty printing helpers
# ---------------------------------------------------------------------------

DIVIDER = "=" * 72


def _header(step: int, title: str) -> None:
    print(f"\n{DIVIDER}")
    print(f"  Step {step}: {title}")
    print(DIVIDER)


def _print_comparison_table(results: list[dict]) -> None:
    """Print aligned comparison table."""
    header = f"{'Model':<24} {'Accuracy':>9} {'F1':>8} {'ROC-AUC':>9} {'Time(ms)':>10} {'Speedup':>9}"
    print("\n" + header)
    print("-" * len(header))

    # Use first model's time as reference for speedup (fastest classical = LR usually)
    ref_time = min(r["time_ms"] for r in results if r["time_ms"] > 0)

    for r in results:
        speedup = ref_time / max(r["time_ms"], 0.001)
        print(
            f"  {r['model']:<22} {r['accuracy']:>8.4f} {r['f1']:>8.4f}"
            f" {r['roc_auc']:>9.4f} {r['time_ms']:>9.1f} {speedup:>8.2f}x"
        )


# ---------------------------------------------------------------------------
# Step 1: Data loading
# ---------------------------------------------------------------------------

def step1_load_data() -> pd.DataFrame:
    _header(1, "Data Loading / Generation")

    # Prefer real Kaggle data, then synthetic
    for csv_path in [REAL_CSV, SYNTHETIC_CSV]:
        if csv_path.exists():
            t0 = time.perf_counter()
            df = pd.read_csv(csv_path)
            load_ms = (time.perf_counter() - t0) * 1000
            print(f"  Loaded: {csv_path.name}  ({load_ms:.1f} ms)")
            break
    else:
        print("  No CSV found — generating synthetic data...")
        # Import locally to avoid circular path issues
        import importlib.util
        spec = importlib.util.spec_from_file_location("generate_data", SRC_DIR / "generate_data.py")
        gen_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen_mod)
        df = gen_mod.generate()

    fraud_count = int(df["Class"].sum())
    fraud_rate = fraud_count / len(df)
    print(f"  Shape              : {df.shape}")
    print(f"  Columns            : {list(df.columns[:5])} ... [{df.shape[1]} total]")
    print(f"  Class distribution : {df['Class'].value_counts().to_dict()}")
    print(f"  Fraud rate         : {fraud_rate:.2%}")
    print(f"  Amount range       : ${df['Amount'].min():.2f} – ${df['Amount'].max():.2f}")
    return df


# ---------------------------------------------------------------------------
# Step 2: Preprocessing
# ---------------------------------------------------------------------------

def step2_preprocess(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    _header(2, "Preprocessing — StandardScaler")

    feature_cols = [c for c in df.columns if c not in ("Class", "Time")]
    X_raw = df[feature_cols].values.astype(float)
    y = df["Class"].values.astype(int)

    print(f"  Features selected  : {len(feature_cols)}")
    print(f"  Before scaling:")
    print(f"    Mean (first 5)   : {X_raw[:, :5].mean(axis=0).round(3)}")
    print(f"    Std  (first 5)   : {X_raw[:, :5].std(axis=0).round(3)}")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    print(f"  After scaling:")
    print(f"    Mean (first 5)   : {X_scaled[:, :5].mean(axis=0).round(3)}")
    print(f"    Std  (first 5)   : {X_scaled[:, :5].std(axis=0).round(3)}")

    return X_scaled, y


# ---------------------------------------------------------------------------
# Step 3: Train / test split
# ---------------------------------------------------------------------------

def step3_split(
    X: np.ndarray, y: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    _header(3, "Train / Test Split (80 / 20, stratified)")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"  Train size         : {len(X_train):,}  (fraud: {y_train.sum():,})")
    print(f"  Test  size         : {len(X_test):,}  (fraud: {y_test.sum():,})")
    print(f"  Train fraud rate   : {y_train.mean():.2%}")
    print(f"  Test  fraud rate   : {y_test.mean():.2%}")
    return X_train, X_test, y_train, y_test


# ---------------------------------------------------------------------------
# Step 4: Classical baseline models
# ---------------------------------------------------------------------------

def _train_evaluate(
    name: str,
    model: Any,
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
) -> dict:
    t0 = time.perf_counter()
    model.fit(X_train, y_train)
    train_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    y_pred = model.predict(X_test)
    pred_ms = (time.perf_counter() - t0) * 1000

    try:
        y_prob = model.predict_proba(X_test)[:, 1]
        auc = float(roc_auc_score(y_test, y_prob))
    except Exception:
        auc = 0.0

    return {
        "model": name,
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": auc,
        "time_ms": round(train_ms + pred_ms, 2),
    }


def step4_classical(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
) -> list[dict]:
    _header(4, "Classical ML Baselines")

    results: list[dict] = []

    # Logistic Regression
    print("  Training LogisticRegression...")
    lr = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    r = _train_evaluate("LogisticRegression", lr, X_train, X_test, y_train, y_test)
    results.append(r)
    print(f"    accuracy={r['accuracy']:.4f}  f1={r['f1']:.4f}  auc={r['roc_auc']:.4f}  time={r['time_ms']:.1f}ms")

    # Random Forest
    print("  Training RandomForest...")
    rf = RandomForestClassifier(
        n_estimators=100, class_weight="balanced", random_state=42, n_jobs=-1
    )
    r = _train_evaluate("RandomForest", rf, X_train, X_test, y_train, y_test)
    results.append(r)
    print(f"    accuracy={r['accuracy']:.4f}  f1={r['f1']:.4f}  auc={r['roc_auc']:.4f}  time={r['time_ms']:.1f}ms")

    # XGBoost (optional)
    try:
        from xgboost import XGBClassifier
        print("  Training XGBoost...")
        scale_pos = max(1, int((y_train == 0).sum() / max((y_train == 1).sum(), 1)))
        xgb = XGBClassifier(
            n_estimators=100, scale_pos_weight=scale_pos,
            random_state=42, eval_metric="logloss", verbosity=0,
        )
        r = _train_evaluate("XGBoost", xgb, X_train, X_test, y_train, y_test)
        results.append(r)
        print(f"    accuracy={r['accuracy']:.4f}  f1={r['f1']:.4f}  auc={r['roc_auc']:.4f}  time={r['time_ms']:.1f}ms")
    except ImportError:
        print("  XGBoost not installed — skipping  (pip install xgboost)")

    return results


# ---------------------------------------------------------------------------
# Step 5: Quantum fraud detection (VQC, 100-sample subset)
# ---------------------------------------------------------------------------

def step5_quantum(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
) -> dict | None:
    _header(5, "Quantum ML — VQC (PennyLane, 100-sample subset)")

    try:
        import importlib.util as ilu
        spec = ilu.spec_from_file_location("quantum_fraud", SRC_DIR / "quantum_fraud.py")
        qf = ilu.module_from_spec(spec)
        spec.loader.exec_module(qf)
    except Exception as exc:
        print(f"  Could not load quantum_fraud.py: {exc}")
        return None

    # Sub-sample to 100 test samples for circuit evaluation speed
    N_SUBSET = 100
    rng = np.random.default_rng(0)

    # Use PCA + MinMaxScaler as in quantum_fraud.py
    try:
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import MinMaxScaler

        n_qubits = qf.N_QUBITS
        pca = PCA(n_components=n_qubits)
        scaler_q = MinMaxScaler(feature_range=(0, np.pi))

        X_tr_pca = pca.fit_transform(X_train)
        X_tr_q = scaler_q.fit_transform(X_tr_pca)

        X_te_pca = pca.transform(X_test)
        X_te_q = scaler_q.transform(X_te_pca)

        # Balance subset for evaluation
        pos_idx = np.where(y_test == 1)[0]
        neg_idx = np.where(y_test == 0)[0]
        n_pos = min(len(pos_idx), N_SUBSET // 2)
        n_neg = N_SUBSET - n_pos
        chosen_pos = rng.choice(pos_idx, n_pos, replace=False)
        chosen_neg = rng.choice(neg_idx, n_neg, replace=False)
        idx_sub = np.concatenate([chosen_pos, chosen_neg])
        rng.shuffle(idx_sub)

        X_te_sub = X_te_q[idx_sub]
        y_te_sub = y_test[idx_sub]

        print(f"  Subset size   : {len(idx_sub)} (pos={n_pos}, neg={n_neg})")
        print(f"  Circuit       : {n_qubits} qubits, {qf.N_LAYERS} layers, {qf.EPOCHS} epochs")

        # Training
        t0 = time.perf_counter()
        weights, losses = qf.train(X_tr_q[:qf.TRAIN_SAMPLES], y_train[:qf.TRAIN_SAMPLES])
        train_ms = (time.perf_counter() - t0) * 1000

        # Prediction on subset
        t0 = time.perf_counter()
        y_pred_q = qf.predict(weights, X_te_sub)
        pred_ms = (time.perf_counter() - t0) * 1000

        acc_q = float(accuracy_score(y_te_sub, y_pred_q))
        f1_q = float(f1_score(y_te_sub, y_pred_q, zero_division=0))
        try:
            import jax.numpy as jnp
            raw_scores = np.array(qf.vqc_batched(jnp.array(X_te_sub), weights))
            auc_q = float(roc_auc_score(y_te_sub, raw_scores))
        except Exception:
            auc_q = 0.0

        total_ms = train_ms + pred_ms
        print(f"  Quantum accuracy: {acc_q:.4f}  f1={f1_q:.4f}  auc={auc_q:.4f}")
        print(f"  Train time      : {train_ms:.0f} ms   Predict: {pred_ms:.1f} ms")

        return {
            "model": "VQC (PennyLane)",
            "accuracy": acc_q,
            "f1": f1_q,
            "roc_auc": auc_q,
            "time_ms": round(total_ms, 2),
        }

    except Exception as exc:
        print(f"  Quantum step failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Step 6: Comparison table
# ---------------------------------------------------------------------------

def step6_comparison(classical: list[dict], quantum: dict | None) -> None:
    _header(6, "Model Comparison Table")

    all_results = classical.copy()
    if quantum is not None:
        all_results.append(quantum)

    _print_comparison_table(all_results)


# ---------------------------------------------------------------------------
# Step 7: PASS / FAIL gate
# ---------------------------------------------------------------------------

def step7_gate(classical: list[dict], quantum: dict | None) -> None:
    _header(7, "PASS / FAIL Gate (accuracy > 0.85)")

    all_results = classical.copy()
    if quantum is not None:
        all_results.append(quantum)

    all_pass = True
    for r in all_results:
        status = "PASS" if r["accuracy"] > 0.85 else "FAIL"
        if status == "FAIL":
            all_pass = False
        indicator = "✓" if status == "PASS" else "✗"
        print(f"  {indicator} {r['model']:<24}  accuracy={r['accuracy']:.4f}  → {status}")

    print()
    if all_pass:
        print("  OVERALL: ALL MODELS PASS")
    else:
        print("  OVERALL: ONE OR MORE MODELS FAILED — review class imbalance handling")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    wall_start = time.perf_counter()
    print(f"\n{'#' * 72}")
    print("  QC Banking Lab — End-to-End Fraud Detection Demo")
    print(f"{'#' * 72}")

    df = step1_load_data()
    X, y = step2_preprocess(df)
    X_train, X_test, y_train, y_test = step3_split(X, y)
    classical_results = step4_classical(X_train, X_test, y_train, y_test)
    quantum_result = step5_quantum(X_train, X_test, y_train, y_test)
    step6_comparison(classical_results, quantum_result)
    step7_gate(classical_results, quantum_result)

    wall_ms = (time.perf_counter() - wall_start) * 1000
    print(f"\n{DIVIDER}")
    print(f"  Total wall time: {wall_ms / 1000:.1f} s")
    print(f"{DIVIDER}\n")


if __name__ == "__main__":
    main()
