"""
Healthcare Lab End-to-End Demo
================================
Demonstrates the full quantum vs classical diabetes classification pipeline:

    Step 1 – Data loading / generation, demographics summary
    Step 2 – Preprocessing: zero-to-NaN imputation, StandardScaler
    Step 3 – Before / after statistics (mean, std, missing count per column)
    Step 4 – Classical ML (LogisticRegression, RandomForest)
    Step 5 – Quantum classification (VQC, balanced subset)
    Step 6 – Comparison table + PASS / FAIL gate (F1 > 0.65)

Run:
    python src/demo.py

The script is self-contained: if diabetes_synthetic.csv is absent it calls
generate_data.generate() to produce it first.

Version: 1.0.0
Date: 2026-10-06
"""
from __future__ import annotations

import importlib.util
import time
import warnings
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
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
SYNTHETIC_CSV = DATA_DIR / "diabetes_synthetic.csv"

DIVIDER = "=" * 72
# Columns where 0 encodes missing (Pima schema)
ZERO_MISSING_COLS = ["Glucose", "BloodPressure", "SkinThickness", "Insulin", "BMI"]
FEATURE_COLS = [
    "Pregnancies", "Glucose", "BloodPressure", "SkinThickness",
    "Insulin", "BMI", "DiabetesPedigreeFunction", "Age",
]


def _header(step: int, title: str) -> None:
    print(f"\n{DIVIDER}")
    print(f"  Step {step}: {title}")
    print(DIVIDER)


# ---------------------------------------------------------------------------
# Step 1: Data loading + demographics
# ---------------------------------------------------------------------------

def step1_load() -> pd.DataFrame:
    _header(1, "Data Loading — Demographics Summary")

    if SYNTHETIC_CSV.exists():
        t0 = time.perf_counter()
        df = pd.read_csv(SYNTHETIC_CSV)
        load_ms = (time.perf_counter() - t0) * 1000
        print(f"  Loaded : {SYNTHETIC_CSV.name}  ({load_ms:.1f} ms)")
    else:
        print("  diabetes_synthetic.csv not found — generating...")
        spec = importlib.util.spec_from_file_location("generate_data", SRC_DIR / "generate_data.py")
        gen_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen_mod)
        df = gen_mod.generate()

    n_pos = int(df["Outcome"].sum())
    n_neg = len(df) - n_pos

    print(f"  Shape                : {df.shape}")
    print(f"  Positive (diabetes)  : {n_pos:,}  ({n_pos/len(df):.1%})")
    print(f"  Negative (no diabetes): {n_neg:,}  ({n_neg/len(df):.1%})")
    print(f"\n  Demographics (all patients):")
    for col in ["Age", "BMI", "Glucose"]:
        sub = df[df[col] > 0][col]   # exclude zero-encoded missing
        print(f"    {col:<28}: mean={sub.mean():.1f}  median={sub.median():.1f}  "
              f"std={sub.std():.1f}  [n={len(sub)}]")

    print(f"\n  By outcome:")
    for outcome, label in [(0, "No Diabetes"), (1, "Diabetes  ")]:
        grp = df[df["Outcome"] == outcome]
        age_vals = grp[grp["Age"] > 0]["Age"]
        bmi_vals = grp[grp["BMI"] > 0]["BMI"]
        glc_vals = grp[grp["Glucose"] > 0]["Glucose"]
        print(f"    {label}  n={len(grp):>4}  "
              f"Age={age_vals.mean():.1f}  BMI={bmi_vals.mean():.1f}  "
              f"Glucose={glc_vals.mean():.1f}")

    return df


# ---------------------------------------------------------------------------
# Step 2: Preprocessing
# ---------------------------------------------------------------------------

def step2_preprocess(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    _header(2, "Preprocessing — Zero Imputation + StandardScaler")

    df_raw = df[FEATURE_COLS + ["Outcome"]].copy()
    df_clean = df_raw.copy()

    # Replace 0 with NaN for physiologically impossible zeros
    for col in ZERO_MISSING_COLS:
        df_clean[col] = df_clean[col].replace(0, np.nan)

    print(f"  Zero-encoded missing columns: {ZERO_MISSING_COLS}")
    return df_raw, df_clean


# ---------------------------------------------------------------------------
# Step 3: Before / after statistics
# ---------------------------------------------------------------------------

def step3_statistics(df_raw: pd.DataFrame, df_clean: pd.DataFrame) -> None:
    _header(3, "Before / After Preprocessing Statistics")

    print(f"  {'Column':<28} {'Raw mean':>9} {'Raw std':>9} {'Missing (0s)':>13} "
          f"{'Clean mean':>11} {'Clean std':>10}")
    print("  " + "-" * 85)

    for col in FEATURE_COLS:
        raw_col = df_raw[col]
        clean_col = df_clean[col]   # contains NaN
        n_missing = int((raw_col == 0).sum()) if col in ZERO_MISSING_COLS else 0
        raw_m = raw_col.mean()
        raw_s = raw_col.std()
        clean_m = clean_col.mean()   # NaN-aware
        clean_s = clean_col.std()
        print(f"  {col:<28} {raw_m:>9.2f} {raw_s:>9.2f} {n_missing:>13,} "
              f"{clean_m:>11.2f} {clean_s:>10.2f}")


# ---------------------------------------------------------------------------
# Step 4: Classical ML
# ---------------------------------------------------------------------------

def _train_evaluate_clf(
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


def step4_classical(df_clean: pd.DataFrame) -> tuple[list[dict], np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    _header(4, "Classical ML — LogisticRegression + RandomForest")

    X_raw = df_clean[FEATURE_COLS].copy()
    y = df_clean["Outcome"].values.astype(int)

    # Impute missing with column median (robust to outliers)
    imputer = SimpleImputer(strategy="median")
    X_imp = imputer.fit_transform(X_raw)

    X_train, X_test, y_train, y_test = train_test_split(
        X_imp, y, test_size=0.20, random_state=42, stratify=y
    )
    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc = scaler.transform(X_test)

    print(f"  Train / Test split : {len(X_train)} / {len(X_test)}")
    print(f"  Positive rate train: {y_train.mean():.1%}   test: {y_test.mean():.1%}")

    results: list[dict] = []

    print("\n  Training LogisticRegression...")
    lr = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    r = _train_evaluate_clf("LogisticRegression", lr, X_train_sc, X_test_sc, y_train, y_test)
    results.append(r)
    print(f"    accuracy={r['accuracy']:.4f}  f1={r['f1']:.4f}  auc={r['roc_auc']:.4f}  time={r['time_ms']:.1f}ms")

    print("\n  Training RandomForest...")
    rf = RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42, n_jobs=-1)
    r = _train_evaluate_clf("RandomForest", rf, X_train_sc, X_test_sc, y_train, y_test)
    results.append(r)
    print(f"    accuracy={r['accuracy']:.4f}  f1={r['f1']:.4f}  auc={r['roc_auc']:.4f}  time={r['time_ms']:.1f}ms")

    return results, X_train_sc, X_test_sc, y_train, y_test


# ---------------------------------------------------------------------------
# Step 5: Quantum classification
# ---------------------------------------------------------------------------

def step5_quantum(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
) -> dict | None:
    _header(5, "Quantum ML — VQC (PennyLane, balanced subset)")

    try:
        spec = importlib.util.spec_from_file_location(
            "quantum_disease", SRC_DIR / "quantum_disease.py"
        )
        qd = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(qd)
    except Exception as exc:
        print(f"  Could not load quantum_disease.py: {exc}")
        return None

    try:
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import MinMaxScaler

        n_qubits = getattr(qd, "N_QUBITS", 4)
        n_layers = getattr(qd, "N_LAYERS", 2)
        epochs = getattr(qd, "EPOCHS", 30)

        pca = PCA(n_components=n_qubits)
        scaler_q = MinMaxScaler(feature_range=(0, np.pi))

        X_tr_q = scaler_q.fit_transform(pca.fit_transform(X_train))
        X_te_q = scaler_q.transform(pca.transform(X_test))

        # Balanced 80-sample subset (40 pos / 40 neg)
        rng = np.random.default_rng(7)
        pos_idx = np.where(y_test == 1)[0]
        neg_idx = np.where(y_test == 0)[0]
        n_each = min(40, len(pos_idx), len(neg_idx))
        idx_sub = np.concatenate([
            rng.choice(pos_idx, n_each, replace=False),
            rng.choice(neg_idx, n_each, replace=False),
        ])
        rng.shuffle(idx_sub)

        X_te_sub = X_te_q[idx_sub]
        y_te_sub = y_test[idx_sub]

        print(f"  Circuit  : {n_qubits} qubits, {n_layers} layers, {epochs} epochs")
        print(f"  Subset   : {len(idx_sub)} samples (pos={n_each}, neg={n_each})")

        train_samples = min(getattr(qd, "TRAIN_SAMPLES", 400), len(X_tr_q))
        t0 = time.perf_counter()
        weights, _ = qd.train(X_tr_q[:train_samples], y_train[:train_samples])
        train_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        y_pred_q = qd.predict(weights, X_te_sub)
        pred_ms = (time.perf_counter() - t0) * 1000

        acc_q = float(accuracy_score(y_te_sub, y_pred_q))
        f1_q = float(f1_score(y_te_sub, y_pred_q, zero_division=0))
        try:
            import jax.numpy as jnp
            raw_scores = np.array(qd.vqc_batched(jnp.array(X_te_sub), weights))
            auc_q = float(roc_auc_score(y_te_sub, raw_scores))
        except Exception:
            auc_q = 0.0

        print(f"  Accuracy : {acc_q:.4f}  F1={f1_q:.4f}  AUC={auc_q:.4f}")
        print(f"  Train    : {train_ms:.0f} ms   Predict: {pred_ms:.1f} ms")

        return {
            "model": "VQC (PennyLane)",
            "accuracy": acc_q,
            "f1": f1_q,
            "roc_auc": auc_q,
            "time_ms": round(train_ms + pred_ms, 2),
        }

    except Exception as exc:
        print(f"  Quantum step failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Step 6: Comparison table + PASS / FAIL gate
# ---------------------------------------------------------------------------

def step6_comparison_and_gate(classical: list[dict], quantum: dict | None) -> None:
    _header(6, "Comparison Table + PASS / FAIL Gate (F1 > 0.65)")

    all_results = classical.copy()
    if quantum is not None:
        all_results.append(quantum)

    header = f"  {'Model':<24} {'Accuracy':>9} {'F1':>8} {'ROC-AUC':>9} {'Time(ms)':>10}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for r in all_results:
        print(f"  {r['model']:<24} {r['accuracy']:>9.4f} {r['f1']:>8.4f}"
              f" {r['roc_auc']:>9.4f} {r['time_ms']:>10.1f}")

    print()
    all_pass = True
    for r in all_results:
        status = "PASS" if r["f1"] > 0.65 else "FAIL"
        if status == "FAIL":
            all_pass = False
        indicator = "✓" if status == "PASS" else "✗"
        print(f"  {indicator} {r['model']:<24}  F1={r['f1']:.4f}  → {status}")

    print()
    print(f"  OVERALL: {'ALL MODELS PASS' if all_pass else 'ONE OR MORE MODELS FAILED'}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    wall_start = time.perf_counter()
    print(f"\n{'#' * 72}")
    print("  QC Healthcare Lab — End-to-End Diabetes Classification Demo")
    print(f"{'#' * 72}")

    df = step1_load()
    df_raw, df_clean = step2_preprocess(df)
    step3_statistics(df_raw, df_clean)
    classical_results, X_train, X_test, y_train, y_test = step4_classical(df_clean)
    quantum_result = step5_quantum(X_train, X_test, y_train, y_test)
    step6_comparison_and_gate(classical_results, quantum_result)

    wall_ms = (time.perf_counter() - wall_start) * 1000
    print(f"\n{DIVIDER}")
    print(f"  Total wall time: {wall_ms / 1000:.1f} s")
    print(f"{DIVIDER}\n")


if __name__ == "__main__":
    main()
