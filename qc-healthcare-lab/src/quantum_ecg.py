"""
Quantum ML anomaly detection on ECG data (MIT-BIH Arrhythmia).
Binary classification: Normal (class 0) vs Abnormal (classes 1-4).

Dataset: mitbih_train.csv  — 87 554 rows x 187 time-step features + 1 label
  Class 0 = Normal beat (72 471 samples)
  Classes 1-4 = Various arrhythmia types

Approach: Quantum Kernel SVM
  - Reduce 187 features → N_QUBITS via PCA
  - Build quantum kernel matrix K[i,j] = |<φ(xi)|φ(xj)>|² using ZZFeatureMap
  - Train classical SVM on the quantum kernel matrix
  - Compare against a classical RBF-SVM baseline

Fallback: If Qiskit/quantum kernel unavailable, falls back to PennyLane VQC
(angle encoding, same architecture as quantum_disease.py).

Saves results to data/ecg_results.json.
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.metrics import accuracy_score, classification_report, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.svm import SVC

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SRC_DIR = Path(__file__).parent
_LAB_DIR = _SRC_DIR.parent
DATA_DIR = _LAB_DIR / "data"
_SHARED_DATASETS = _LAB_DIR.parent / "datasets" / "healthcare"

RESULTS_FILE = DATA_DIR / "ecg_results.json"


def _find_csv(filename: str) -> Path:
    for candidate in [DATA_DIR / filename, _SHARED_DATASETS / filename]:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"{filename} not found in {DATA_DIR} or {_SHARED_DATASETS}")


# ---------------------------------------------------------------------------
# Hyperparameters
# ---------------------------------------------------------------------------

N_QUBITS = 4          # PCA target + circuit width
TRAIN_SAMPLES = 800   # balanced subset (400 normal + 400 abnormal)
TEST_SAMPLES = 200    # balanced subset (100 + 100)
KERNEL_TRAIN = 300    # rows used for kernel matrix (quantum kernel is O(n²))
KERNEL_TEST = 100

# VQC fallback params
VQC_N_LAYERS = 2
VQC_EPOCHS = 40
VQC_LR = 0.05
VQC_BATCH = 24

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_ecg(train_only: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """
    Load MIT-BIH data, binarise labels (0=normal, 1=abnormal),
    return balanced subset for reasonable runtime.
    """
    fname = "mitbih_train.csv" if train_only else "mitbih_test.csv"
    path = _find_csv(fname)
    print(f"  Loading ECG data from {path}  (this may take a moment)...")

    # No header in this dataset; last column is the label
    df = pd.read_csv(path, header=None)
    y_raw = df.iloc[:, -1].values.astype(int)
    X_raw = df.iloc[:, :-1].values.astype(float)

    # Binary: 0=normal, 1=any arrhythmia
    y_binary = (y_raw != 0).astype(int)

    n_normal = (y_binary == 0).sum()
    n_abnormal = (y_binary == 1).sum()
    print(f"  Total: {len(y_binary)} rows  Normal: {n_normal}  Abnormal: {n_abnormal}")

    return X_raw, y_binary


def _balanced_subset(
    X: np.ndarray, y: np.ndarray, n_each: int, seed: int = 42
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    pos = np.where(y == 1)[0]
    neg = np.where(y == 0)[0]
    n = min(n_each, len(pos), len(neg))
    idx = np.concatenate([
        rng.choice(pos, n, replace=False),
        rng.choice(neg, n, replace=False),
    ])
    rng.shuffle(idx)
    return X[idx], y[idx]


def _pca_scale(X: np.ndarray) -> np.ndarray:
    pca = PCA(n_components=N_QUBITS, random_state=42)
    scaler = MinMaxScaler(feature_range=(0, np.pi))
    return scaler.fit_transform(pca.fit_transform(X))


# ---------------------------------------------------------------------------
# Classical SVM baseline
# ---------------------------------------------------------------------------

def classical_svm(X_train: np.ndarray, X_test: np.ndarray, y_train: np.ndarray, y_test: np.ndarray) -> dict:
    print("  Training Classical RBF-SVM baseline...")
    t0 = time.perf_counter()
    clf = SVC(kernel="rbf", class_weight="balanced", probability=True, random_state=42)
    clf.fit(X_train, y_train)
    train_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    y_pred = clf.predict(X_test)
    predict_time = time.perf_counter() - t0

    y_prob = clf.predict_proba(X_test)[:, 1]
    acc = float(accuracy_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    auc = float(roc_auc_score(y_test, y_prob))
    print(f"  Classical SVM → acc={acc:.4f}  f1={f1:.4f}  auc={auc:.4f}")

    return {
        "model": "Classical-RBF-SVM",
        "accuracy": acc,
        "f1": f1,
        "roc_auc": auc,
        "train_time_s": round(train_time, 4),
        "predict_time_s": round(predict_time, 4),
        "classification_report": classification_report(y_test, y_pred, output_dict=True),
    }


# ---------------------------------------------------------------------------
# Quantum Kernel SVM (Qiskit ZZFeatureMap)
# ---------------------------------------------------------------------------

def quantum_kernel_svm(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
) -> dict:
    """
    Build a quantum kernel K[i,j] = |<φ(xi)|φ(xj)>|²
    using Qiskit's ZZFeatureMap, then train a classical SVM on it.
    Uses a smaller subset (KERNEL_TRAIN samples) since kernel matrix is O(n²).
    """
    try:
        from qiskit.circuit.library import ZZFeatureMap
        from qiskit_machine_learning.kernels import FidelityQuantumKernel
        from qiskit.primitives import StatevectorSampler
        from qiskit_algorithms.state_fidelities import ComputeUncompute
    except ImportError as e:
        print(f"  Qiskit quantum kernel unavailable ({e}) — falling back to PennyLane VQC")
        return _pennylane_vqc_fallback(X_train, X_test, y_train, y_test)

    # Use smaller subset for kernel computation
    n_tr = min(KERNEL_TRAIN, len(X_train))
    n_te = min(KERNEL_TEST, len(X_test))
    Xtr = X_train[:n_tr]
    ytr = y_train[:n_tr]
    Xte = X_test[:n_te]
    yte = y_test[:n_te]

    print(f"  Building ZZFeatureMap quantum kernel ({n_tr} train, {n_te} test)...")
    feature_map = ZZFeatureMap(feature_dimension=N_QUBITS, reps=2)

    try:
        sampler = StatevectorSampler()
        fidelity = ComputeUncompute(sampler=sampler)
        qkernel = FidelityQuantumKernel(fidelity=fidelity, feature_map=feature_map)

        print("  Computing train kernel matrix...")
        t0 = time.perf_counter()
        K_train = qkernel.evaluate(x_vec=Xtr)
        print("  Computing test kernel matrix...")
        K_test = qkernel.evaluate(x_vec=Xte, y_vec=Xtr)
        kernel_time = time.perf_counter() - t0
        print(f"  Kernel matrices computed in {kernel_time:.1f}s")

        print("  Training SVM on quantum kernel...")
        t0 = time.perf_counter()
        svm = SVC(kernel="precomputed", class_weight="balanced", probability=True, random_state=42)
        svm.fit(K_train, ytr)
        train_time = time.perf_counter() - t0

        t0 = time.perf_counter()
        y_pred = svm.predict(K_test)
        predict_time = time.perf_counter() - t0
        y_prob = svm.predict_proba(K_test)[:, 1]

        acc = float(accuracy_score(yte, y_pred))
        f1 = float(f1_score(yte, y_pred, zero_division=0))
        auc = float(roc_auc_score(yte, y_prob))
        print(f"  QKernel-SVM → acc={acc:.4f}  f1={f1:.4f}  auc={auc:.4f}")

        return {
            "model": "QuantumKernel-SVM",
            "feature_map": "ZZFeatureMap",
            "n_qubits": N_QUBITS,
            "reps": 2,
            "kernel_train_samples": n_tr,
            "kernel_test_samples": n_te,
            "accuracy": acc,
            "f1": f1,
            "roc_auc": auc,
            "kernel_time_s": round(kernel_time, 4),
            "train_time_s": round(train_time, 4),
            "predict_time_s": round(predict_time, 4),
            "classification_report": classification_report(yte, y_pred, output_dict=True),
        }
    except Exception as e:
        print(f"  Quantum kernel failed ({e}) — falling back to PennyLane VQC")
        return _pennylane_vqc_fallback(X_train, X_test, y_train, y_test)


# ---------------------------------------------------------------------------
# PennyLane VQC fallback
# ---------------------------------------------------------------------------

def _pennylane_vqc_fallback(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
) -> dict:
    """
    VQC binary classifier as fallback when Qiskit is unavailable.
    Same angle-encoding + ring-CNOT ansatz as quantum_disease.py.
    """
    import jax
    import jax.numpy as jnp
    import pennylane as qml

    jax.config.update("jax_enable_x64", True)

    print(f"  Running PennyLane VQC fallback ({VQC_N_LAYERS} layers, {VQC_EPOCHS} epochs)...")

    dev = qml.device("default.qubit", wires=N_QUBITS)

    @qml.qnode(dev, interface="jax")
    def _vqc(features, weights):
        for i in range(N_QUBITS):
            qml.RY(features[i], wires=i)
        for layer in range(VQC_N_LAYERS):
            for i in range(N_QUBITS):
                base = layer * N_QUBITS * 2 + i * 2
                qml.RY(weights[base], wires=i)
                qml.RZ(weights[base + 1], wires=i)
            for i in range(N_QUBITS - 1):
                qml.CNOT(wires=[i, i + 1])
            qml.CNOT(wires=[N_QUBITS - 1, 0])
        return qml.expval(qml.PauliZ(0))

    _vb = jax.vmap(_vqc, in_axes=(0, None))

    def _cost(w, X, y):
        p = _vb(X, w)
        lbls = jnp.where(y == 1, 1.0, -1.0)
        return jnp.mean((p - lbls) ** 2)

    _gfn = jax.jit(jax.grad(_cost))
    _cfn = jax.jit(_cost)

    rng = np.random.default_rng(0)
    n_params = VQC_N_LAYERS * N_QUBITS * 2
    weights = jnp.array(rng.uniform(-np.pi, np.pi, n_params))
    m = jnp.zeros_like(weights)
    v = jnp.zeros_like(weights)
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    losses: list[float] = []

    n = len(X_train)
    t0 = time.perf_counter()
    for epoch in range(VQC_EPOCHS):
        idx = np.random.choice(n, min(VQC_BATCH, n), replace=False)
        Xb = jnp.array(X_train[idx])
        yb = jnp.array(y_train[idx])
        loss = float(_cfn(weights, Xb, yb))
        g = _gfn(weights, Xb, yb)
        t = epoch + 1
        m = beta1 * m + (1 - beta1) * g
        v = beta2 * v + (1 - beta2) * g ** 2
        weights = weights - VQC_LR * (m / (1 - beta1 ** t)) / (jnp.sqrt(v / (1 - beta2 ** t)) + eps)
        losses.append(loss)
        if (epoch + 1) % 10 == 0:
            print(f"    epoch {epoch+1:>3}/{VQC_EPOCHS}  loss={loss:.4f}")
    train_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    raw = np.array(_vb(jnp.array(X_test), weights))
    predict_time = time.perf_counter() - t0
    y_pred = (raw > 0.0).astype(int)

    acc = float(accuracy_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    try:
        auc = float(roc_auc_score(y_test, raw))
    except Exception:
        auc = 0.0
    print(f"  VQC → acc={acc:.4f}  f1={f1:.4f}  auc={auc:.4f}")

    return {
        "model": "VQC-PennyLane-fallback",
        "n_qubits": N_QUBITS,
        "n_layers": VQC_N_LAYERS,
        "epochs": VQC_EPOCHS,
        "accuracy": acc,
        "f1": f1,
        "roc_auc": auc,
        "train_time_s": round(train_time, 4),
        "predict_time_s": round(predict_time, 4),
        "loss_history": [round(l, 6) for l in losses],
        "classification_report": classification_report(y_test, y_pred, output_dict=True),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> dict[str, Any]:
    print("=" * 60)
    print("QC Healthcare Lab — Quantum ECG Anomaly Detection")
    print("=" * 60)

    # Load ECG data
    try:
        X_raw, y_binary = load_ecg()
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return {"error": str(e)}

    print(f"\n  Binary label distribution: Normal={( y_binary==0).sum()}  Abnormal={(y_binary==1).sum()}")

    # PCA + scale for quantum models
    print("  Applying PCA (187 → 4 dims) + MinMaxScaler...")
    X_pca = _pca_scale(X_raw)

    # Balanced subsets
    n_train_each = TRAIN_SAMPLES // 2
    n_test_each = TEST_SAMPLES // 2

    X_sub, y_sub = _balanced_subset(X_pca, y_binary, n_train_each + n_test_each)
    X_train, X_test, y_train, y_test = train_test_split(
        X_sub, y_sub,
        test_size=TEST_SAMPLES,
        random_state=42,
        stratify=y_sub,
    )
    print(f"  Train: {len(X_train)}  Test: {len(X_test)}")

    # --- Classical SVM baseline ---
    print("\n--- Classical SVM Baseline ---")
    classical_result = classical_svm(X_train, X_test, y_train, y_test)

    # --- Quantum Model ---
    print("\n--- Quantum Kernel SVM (or VQC fallback) ---")
    quantum_result = quantum_kernel_svm(X_train, X_test, y_train, y_test)

    # Compile final result
    result = {
        "task": "ECG-anomaly-detection",
        "dataset": "MIT-BIH-Arrhythmia",
        "n_features_raw": X_raw.shape[1],
        "n_features_quantum": N_QUBITS,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "label_map": {"0": "normal", "1": "abnormal"},
        "classical": classical_result,
        "quantum": quantum_result,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResults saved → {RESULTS_FILE}")

    # Comparison summary
    print("\n--- Comparison Summary ---")
    print(f"{'Model':<30} {'Acc':>6}  {'F1':>6}  {'AUC':>6}")
    print("-" * 48)
    for label, res in [("Classical RBF-SVM", classical_result), ("Quantum", quantum_result)]:
        if "accuracy" in res:
            print(
                f"{label:<30} {res['accuracy']:>6.4f}  {res['f1']:>6.4f}  {res['roc_auc']:>6.4f}"
            )

    return result


if __name__ == "__main__":
    main()
