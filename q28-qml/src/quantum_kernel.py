"""
Quantum Kernel Estimation — Wine Quality Classification.

Compares:
  1. Classical RBF kernel SVM (sklearn)
  2. Quantum kernel SVM  (PennyLane fidelity kernel via kernel_matrix)
  3. Quantum kernel SVM  (manual ZZFeatureMap-style kernel, same as qsvm.py approach)

The PennyLane `qml.kernels.kernel_matrix` utility is used for the
'hardware-friendly' fidelity kernel, providing a clean reference implementation.

Results saved to data/kernel_results.json
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pennylane as qml
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.svm import SVC

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent / "data"
RESULTS_FILE = DATA_DIR / "kernel_results.json"
DATASET_PATH = Path(__file__).parent.parent.parent / "datasets" / "qml" / "winequalityN.csv"

# ---- Config ----
N_QUBITS = 4
N_FEATURES = N_QUBITS
TRAIN_SAMPLES = 150
TEST_SAMPLES = 60


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_wine_data() -> tuple[np.ndarray, np.ndarray]:
    path = DATASET_PATH
    if not path.exists():
        path = DATA_DIR / "winequalityN.csv"
    if path.exists():
        print(f"Loading wine data from {path}")
        df = pd.read_csv(path)
        if "type" in df.columns:
            df["type"] = (df["type"] == "red").astype(int)
        feature_cols = [c for c in df.columns if c != "quality"]
        X = df[feature_cols].values.astype(float)
        y = (df["quality"] >= 6).astype(int).values
    else:
        print("Dataset not found — using synthetic data")
        rng = np.random.default_rng(42)
        n = 400
        X = rng.standard_normal((n, 11))
        y = (rng.random(n) > 0.45).astype(int)
        print(f"  {len(X)} samples | good={y.sum()} bad={(1 - y).sum()}")
        return X, y

    # Impute NaNs (~38 values across 6498 rows)
    imputer = SimpleImputer(strategy="median")
    X = imputer.fit_transform(X)
    print(f"  {len(X)} samples | good={y.sum()} bad={(1 - y).sum()}")
    return X, y


def preprocess(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        train_size=TRAIN_SAMPLES,
        test_size=TEST_SAMPLES,
        random_state=42,
        stratify=y,
    )
    pca = PCA(n_components=N_FEATURES, random_state=42)
    scaler = MinMaxScaler(feature_range=(0.0, np.pi))
    X_tr = scaler.fit_transform(pca.fit_transform(X_train))
    X_te = scaler.transform(pca.transform(X_test))
    print(f"  PCA: {N_FEATURES} features | Train={len(X_tr)} Test={len(X_te)}")
    return X_tr, X_te, y_train, y_test


# ---------------------------------------------------------------------------
# Quantum kernel definitions
# ---------------------------------------------------------------------------

dev = qml.device("default.qubit", wires=N_QUBITS)


# --- Kernel A: ZZFeatureMap (manually) ---

@qml.qnode(dev)
def _zz_kernel_circuit(x1: np.ndarray, x2: np.ndarray):
    """ZZFeatureMap fidelity kernel circuit."""
    # U(x1)
    for i in range(N_QUBITS):
        qml.Hadamard(wires=i)
        qml.RZ(2.0 * x1[i], wires=i)
    for i in range(N_QUBITS - 1):
        qml.CNOT(wires=[i, i + 1])
        qml.RZ(2.0 * (np.pi - x1[i]) * (np.pi - x1[i + 1]), wires=i + 1)
        qml.CNOT(wires=[i, i + 1])
    # U†(x2)
    for i in range(N_QUBITS - 2, -1, -1):
        qml.CNOT(wires=[i, i + 1])
        qml.RZ(-2.0 * (np.pi - x2[i]) * (np.pi - x2[i + 1]), wires=i + 1)
        qml.CNOT(wires=[i, i + 1])
    for i in range(N_QUBITS - 1, -1, -1):
        qml.RZ(-2.0 * x2[i], wires=i)
        qml.Hadamard(wires=i)
    return qml.probs(wires=range(N_QUBITS))


def zz_kernel(x1: np.ndarray, x2: np.ndarray) -> float:
    probs = _zz_kernel_circuit(x1, x2)
    return float(probs[0])


def build_kernel_matrix_zz(Xa: np.ndarray, Xb: np.ndarray) -> np.ndarray:
    K = np.zeros((len(Xa), len(Xb)))
    total = len(Xa) * len(Xb)
    done = 0
    for i in range(len(Xa)):
        for j in range(len(Xb)):
            K[i, j] = zz_kernel(Xa[i], Xb[j])
            done += 1
            if done % 100 == 0:
                print(f"    ZZ kernel matrix: {done}/{total} ({done/total:.0%})")
    return K


# --- Kernel B: PennyLane's built-in kernel_matrix with angle embedding ---

@qml.qnode(dev)
def _angle_feature_circuit(x: np.ndarray):
    """Angle embedding circuit (used by qml.kernels.kernel_matrix)."""
    qml.AngleEmbedding(x, wires=range(N_QUBITS), rotation="Y")
    qml.StronglyEntanglingLayers(
        weights=np.zeros((1, N_QUBITS, 3)),  # identity init — pure encoding test
        wires=range(N_QUBITS),
    )
    return qml.state()


def pennylane_kernel(x1: np.ndarray, x2: np.ndarray) -> float:
    """Fidelity (overlap) kernel using PennyLane's adjoint trick."""
    return float(qml.kernels.kernel(
        lambda x: qml.AngleEmbedding(x, wires=range(N_QUBITS), rotation="Y"),
        x1,
        x2,
        device=dev,
    ))


def build_pennylane_kernel_matrix(Xa: np.ndarray, Xb: np.ndarray) -> np.ndarray:
    """Build kernel matrix using qml.kernels.kernel_matrix helper."""
    if Xa is Xb or np.array_equal(Xa, Xb):
        # Use the square-matrix shortcut
        return qml.kernels.kernel_matrix(
            Xa,
            Xa,
            lambda x1, x2: pennylane_kernel(x1, x2),
        )
    return qml.kernels.kernel_matrix(
        Xa,
        Xb,
        lambda x1, x2: pennylane_kernel(x1, x2),
    )


# ---------------------------------------------------------------------------
# Benchmark helper
# ---------------------------------------------------------------------------

def run_svm(name: str, K_train: np.ndarray, K_test: np.ndarray,
            y_train: np.ndarray, y_test: np.ndarray,
            kernel_build_time: float) -> dict:
    t0 = time.perf_counter()
    svm = SVC(kernel="precomputed", C=1.0, probability=True, random_state=42)
    svm.fit(K_train, y_train)
    train_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    y_pred = svm.predict(K_test)
    predict_time = time.perf_counter() - t0

    try:
        y_prob = svm.predict_proba(K_test)[:, 1]
        auc = float(roc_auc_score(y_test, y_prob))
    except Exception:
        auc = 0.0

    acc = float(accuracy_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    cm = confusion_matrix(y_test, y_pred)
    print(f"  {name}: accuracy={acc:.4f}  f1={f1:.4f}  auc={auc:.4f}  kernel_build={kernel_build_time:.1f}s")

    return {
        "model": name,
        "accuracy": acc,
        "f1": f1,
        "roc_auc": auc,
        "confusion_matrix": cm.tolist(),
        "train_time_s": round(train_time, 4),
        "predict_time_s": round(predict_time, 4),
        "kernel_build_time_s": round(kernel_build_time, 2),
        "classification_report": classification_report(
            y_test, y_pred, output_dict=True, zero_division=0
        ),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  Q28 QML — Quantum Kernel Estimation (Wine Quality)")
    print("=" * 60)

    X, y = load_wine_data()
    X_train, X_test, y_train, y_test = preprocess(X, y)

    results = {}

    # ---- 1. Classical RBF kernel SVM ----
    print("\n[1/3] Classical RBF kernel SVM...")
    t0 = time.perf_counter()
    clf_rbf = SVC(kernel="rbf", C=10.0, gamma="scale", probability=True, random_state=42)
    clf_rbf.fit(X_train, y_train)
    rbf_train_time = time.perf_counter() - t0
    y_pred_rbf = clf_rbf.predict(X_test)
    try:
        rbf_auc = float(roc_auc_score(y_test, clf_rbf.predict_proba(X_test)[:, 1]))
    except Exception:
        rbf_auc = 0.0
    rbf_acc = float(accuracy_score(y_test, y_pred_rbf))
    rbf_f1 = float(f1_score(y_test, y_pred_rbf, zero_division=0))
    print(f"  Classical RBF: accuracy={rbf_acc:.4f}  f1={rbf_f1:.4f}  auc={rbf_auc:.4f}  train={rbf_train_time:.3f}s")
    results["classical_rbf"] = {
        "model": "SVM-RBF-Classical",
        "accuracy": rbf_acc,
        "f1": rbf_f1,
        "roc_auc": rbf_auc,
        "confusion_matrix": confusion_matrix(y_test, y_pred_rbf).tolist(),
        "train_time_s": round(rbf_train_time, 4),
        "kernel_build_time_s": 0.0,
    }

    # ---- 2. Quantum ZZFeatureMap kernel SVM ----
    print(f"\n[2/3] ZZFeatureMap quantum kernel SVM ({len(X_train)}×{len(X_train)})...")
    t0 = time.perf_counter()
    K_zz_train = build_kernel_matrix_zz(X_train, X_train)
    K_zz_test = build_kernel_matrix_zz(X_test, X_train)
    zz_kernel_time = time.perf_counter() - t0
    print(f"  ZZ kernel matrices built in {zz_kernel_time:.1f}s")
    results["quantum_zz_kernel"] = run_svm(
        "SVM-ZZFeatureMapKernel", K_zz_train, K_zz_test, y_train, y_test, zz_kernel_time
    )

    # ---- 3. PennyLane angle-embedding fidelity kernel SVM ----
    print(f"\n[3/3] PennyLane angle-embedding fidelity kernel SVM...")
    t0 = time.perf_counter()
    K_pl_train = build_pennylane_kernel_matrix(X_train, X_train)
    K_pl_test = build_pennylane_kernel_matrix(X_test, X_train)
    pl_kernel_time = time.perf_counter() - t0
    print(f"  PennyLane kernel matrices built in {pl_kernel_time:.1f}s")
    results["quantum_pennylane_kernel"] = run_svm(
        "SVM-PennyLaneFidelityKernel", K_pl_train, K_pl_test, y_train, y_test, pl_kernel_time
    )

    # ---- Comparison summary ----
    print("\n--- Comparison Summary ---")
    for key, r in results.items():
        print(f"  {r['model']:<40} acc={r['accuracy']:.4f}  f1={r['f1']:.4f}  auc={r['roc_auc']:.4f}")

    summary = {
        "task": "wine-quality-binary",
        "n_qubits": N_QUBITS,
        "n_features_pca": N_FEATURES,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "results": results,
        "best_model": max(results.items(), key=lambda kv: kv[1]["roc_auc"])[1]["model"],
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as fh:
        json.dump(summary, fh, indent=2)
    print(f"\nResults saved → {RESULTS_FILE}")
    return summary


if __name__ == "__main__":
    main()
