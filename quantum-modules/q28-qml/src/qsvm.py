"""
Quantum Support Vector Machine (QSVM) using a quantum kernel.

Dataset : winequalityN.csv  (binary: quality >= 6 → good)
Encoding: ZZFeatureMap-style angle encoding via PennyLane
Kernel  : K(x,i, x_j) = |<0|U†(x_j)U(x_i)|0>|²
          computed via PennyLane's kernel_matrix helper

Results saved to data/qsvm_results.json
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
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

import pennylane as qml

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent / "data"
RESULTS_FILE = DATA_DIR / "qsvm_results.json"
DATASET_PATH = Path(__file__).parent.parent.parent / "datasets" / "qml" / "winequalityN.csv"

# ---- Hyperparameters ----
N_QUBITS = 4          # must equal n_features after PCA
N_FEATURES = N_QUBITS
TRAIN_SAMPLES = 200   # keep small for quantum kernel runtime
TEST_SAMPLES = 80


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
        n = 500
        X = rng.standard_normal((n, 11))
        y = (rng.random(n) > 0.45).astype(int)
        print(f"  {len(X)} samples | good={y.sum()} bad={(1 - y).sum()}")
        return X, y

    # Impute NaNs (dataset has ~38 NaN values)
    imputer = SimpleImputer(strategy="median")
    X = imputer.fit_transform(X)
    print(f"  {len(X)} samples | good={y.sum()} bad={(1 - y).sum()}")
    return X, y


def preprocess(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Stratified split → PCA to N_FEATURES → scale to [0, π]."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        train_size=TRAIN_SAMPLES,
        test_size=TEST_SAMPLES,
        random_state=42,
        stratify=y,
    )

    pca = PCA(n_components=N_FEATURES, random_state=42)
    scaler = MinMaxScaler(feature_range=(0, np.pi))

    X_train_pca = pca.fit_transform(X_train)
    X_test_pca = pca.transform(X_test)

    X_train_sc = scaler.fit_transform(X_train_pca)
    X_test_sc = scaler.transform(X_test_pca)

    print(f"  PCA variance explained: {pca.explained_variance_ratio_.sum():.3f}")
    return X_train_sc, X_test_sc, y_train, y_test


# ---------------------------------------------------------------------------
# Quantum kernel circuit
# ---------------------------------------------------------------------------

dev = qml.device("default.qubit", wires=N_QUBITS)


@qml.qnode(dev)
def kernel_circuit(x1: np.ndarray, x2: np.ndarray) -> float:
    """
    ZZFeatureMap-inspired kernel circuit.
    Prepares U(x1)|0> then measures <0|U†(x2)U(x1)|0>.
    Returns probability of measuring the all-zeros state.
    """
    # Encoding U(x1)
    for i in range(N_QUBITS):
        qml.Hadamard(wires=i)
        qml.RZ(2.0 * x1[i], wires=i)
    for i in range(N_QUBITS - 1):
        qml.CNOT(wires=[i, i + 1])
        qml.RZ(2.0 * (np.pi - x1[i]) * (np.pi - x1[i + 1]), wires=i + 1)
        qml.CNOT(wires=[i, i + 1])

    # Adjoint encoding U†(x2)
    qml.adjoint(lambda: _encode(x2))()

    return qml.probs(wires=range(N_QUBITS))


def _encode(x: np.ndarray) -> None:
    """ZZFeatureMap encoding block."""
    for i in range(N_QUBITS):
        qml.Hadamard(wires=i)
        qml.RZ(2.0 * x[i], wires=i)
    for i in range(N_QUBITS - 1):
        qml.CNOT(wires=[i, i + 1])
        qml.RZ(2.0 * (np.pi - x[i]) * (np.pi - x[i + 1]), wires=i + 1)
        qml.CNOT(wires=[i, i + 1])


def quantum_kernel_value(x1: np.ndarray, x2: np.ndarray) -> float:
    """K(x1, x2) = probability of all-zeros after U†(x2) U(x1) |0>."""
    probs = kernel_circuit(x1, x2)
    return float(probs[0])  # |00...0> amplitude squared


def build_kernel_matrix(X_a: np.ndarray, X_b: np.ndarray) -> np.ndarray:
    """Compute the full kernel matrix between two sets of samples."""
    n_a, n_b = len(X_a), len(X_b)
    K = np.zeros((n_a, n_b))
    total = n_a * n_b
    done = 0
    for i in range(n_a):
        for j in range(n_b):
            K[i, j] = quantum_kernel_value(X_a[i], X_b[j])
            done += 1
            if done % 200 == 0:
                print(f"    kernel matrix: {done}/{total} ({done/total:.0%})")
    return K


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  Q28 QML — Quantum SVM (Wine Quality)")
    print("=" * 60)

    X, y = load_wine_data()
    X_train, X_test, y_train, y_test = preprocess(X, y)
    print(f"  Train: {len(X_train)}  Test: {len(X_test)}")

    # ---- Quantum kernel matrix ----
    print(f"\nBuilding quantum kernel matrix ({len(X_train)}×{len(X_train)}) ...")
    t_k0 = time.perf_counter()
    K_train = build_kernel_matrix(X_train, X_train)
    K_train_time = time.perf_counter() - t_k0
    print(f"  Train kernel done in {K_train_time:.1f}s")

    print(f"Building test kernel matrix ({len(X_test)}×{len(X_train)}) ...")
    t_k1 = time.perf_counter()
    K_test = build_kernel_matrix(X_test, X_train)
    K_test_time = time.perf_counter() - t_k1
    print(f"  Test  kernel done in {K_test_time:.1f}s")

    # ---- Quantum SVM ----
    print("\nTraining QSVM with precomputed quantum kernel...")
    t0 = time.perf_counter()
    qsvm = SVC(kernel="precomputed", C=1.0, probability=True, random_state=42)
    qsvm.fit(K_train, y_train)
    train_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    y_pred = qsvm.predict(K_test)
    predict_time = time.perf_counter() - t0

    try:
        y_prob = qsvm.predict_proba(K_test)[:, 1]
        auc = float(roc_auc_score(y_test, y_prob))
    except Exception:
        auc = 0.0

    acc = float(accuracy_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    cm = confusion_matrix(y_test, y_pred)

    print(f"\nQSVM Results:")
    print(f"  accuracy={acc:.4f}  f1={f1:.4f}  auc={auc:.4f}")
    print(f"  kernel_build_time={K_train_time + K_test_time:.1f}s  train_time={train_time:.3f}s")

    # ---- Classical SVM baseline for comparison ----
    print("\nClassical SVM (RBF) for comparison...")
    csvm = SVC(kernel="rbf", C=10.0, gamma="scale", probability=True, random_state=42)
    csvm.fit(X_train, y_train)
    cy_pred = csvm.predict(X_test)
    try:
        cy_prob = csvm.predict_proba(X_test)[:, 1]
        cauc = float(roc_auc_score(y_test, cy_prob))
    except Exception:
        cauc = 0.0
    cacc = float(accuracy_score(y_test, cy_pred))
    cf1 = float(f1_score(y_test, cy_pred, zero_division=0))
    print(f"  Classical SVM → accuracy={cacc:.4f}  f1={cf1:.4f}  auc={cauc:.4f}")

    # ---- Circuit diagram ----
    circuit_str = qml.draw(kernel_circuit)(X_train[0], X_train[1])

    result = {
        "model": "QSVM-QuantumKernel",
        "n_qubits": N_QUBITS,
        "n_features_pca": N_FEATURES,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "encoding": "ZZFeatureMap-angle",
        "quantum_svm": {
            "accuracy": acc,
            "f1": f1,
            "roc_auc": auc,
            "confusion_matrix": cm.tolist(),
            "train_time_s": round(train_time, 4),
            "predict_time_s": round(predict_time, 4),
            "kernel_build_time_s": round(K_train_time + K_test_time, 2),
            "classification_report": classification_report(
                y_test, y_pred, output_dict=True, zero_division=0
            ),
        },
        "classical_svm_comparison": {
            "accuracy": cacc,
            "f1": cf1,
            "roc_auc": cauc,
        },
        "accuracy_delta": round(acc - cacc, 4),
        "circuit_diagram": str(circuit_str),
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as fh:
        json.dump(result, fh, indent=2)
    print(f"\nResults saved → {RESULTS_FILE}")
    return result


if __name__ == "__main__":
    main()
