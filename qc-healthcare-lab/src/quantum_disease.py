"""
Quantum ML disease classifier using PennyLane VQC.
Trains a Variational Quantum Classifier on:
  - Pima Indians Diabetes (primary)
  - Heart Disease UCI (secondary)

Architecture: 4-qubit circuit, 2 variational layers, angle encoding via RY.
Optimizer: Adam (manual JAX implementation for full control).
Saves results to data/quantum_results.json.
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
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, MinMaxScaler

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SRC_DIR = Path(__file__).parent
_LAB_DIR = _SRC_DIR.parent
DATA_DIR = _LAB_DIR / "data"
_SHARED_DATASETS = _LAB_DIR.parent / "datasets" / "healthcare"

RESULTS_FILE = DATA_DIR / "quantum_results.json"


def _find_csv(filename: str) -> Path:
    for candidate in [DATA_DIR / filename, _SHARED_DATASETS / filename]:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"{filename} not found in {DATA_DIR} or {_SHARED_DATASETS}")


# ---------------------------------------------------------------------------
# Hyperparameters
# ---------------------------------------------------------------------------

N_QUBITS = 4
N_LAYERS = 2
EPOCHS = 40
LEARNING_RATE = 0.05
BATCH_SIZE = 24
TRAIN_SAMPLES = 500   # max balanced subset — keeps runtime sensible
TEST_SAMPLES = 150

# ---------------------------------------------------------------------------
# PennyLane circuit
# ---------------------------------------------------------------------------

import jax
import jax.numpy as jnp
import pennylane as qml

jax.config.update("jax_enable_x64", True)

dev = qml.device("default.qubit", wires=N_QUBITS)


@qml.qnode(dev, interface="jax")
def vqc(features: jnp.ndarray, weights: jnp.ndarray) -> jnp.ndarray:
    """
    Variational Quantum Classifier.

    Encoding: angle encoding via RY gates on each qubit.
    Ansatz:   N_LAYERS repetitions of {RY, RZ per qubit} + ring CNOT entanglement.
    Output:   expectation value of PauliZ on qubit 0 ∈ (-1, +1).

    weights shape: (N_LAYERS * N_QUBITS * 2,)
    """
    # Angle encoding
    for i in range(N_QUBITS):
        qml.RY(features[i], wires=i)

    # Variational layers
    for layer in range(N_LAYERS):
        for i in range(N_QUBITS):
            base = layer * N_QUBITS * 2 + i * 2
            qml.RY(weights[base], wires=i)
            qml.RZ(weights[base + 1], wires=i)
        # Ring entanglement
        for i in range(N_QUBITS - 1):
            qml.CNOT(wires=[i, i + 1])
        qml.CNOT(wires=[N_QUBITS - 1, 0])

    return qml.expval(qml.PauliZ(0))


# Vectorise over the batch dimension (axis 0 of features)
_vqc_batched = jax.vmap(vqc, in_axes=(0, None))


def _cost(weights: jnp.ndarray, X: jnp.ndarray, y: jnp.ndarray) -> jnp.ndarray:
    """MSE loss between circuit output and {+1, -1} labels."""
    preds = _vqc_batched(X, weights)
    labels = jnp.where(y == 1, 1.0, -1.0)
    return jnp.mean((preds - labels) ** 2)


_grad_fn = jax.jit(jax.grad(_cost))
_cost_jit = jax.jit(_cost)


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _load_and_encode(filename: str, target_col: str, cat_cols: list[str] | None = None) -> tuple[np.ndarray, np.ndarray]:
    path = _find_csv(filename)
    print(f"  Loading {path.name}")
    df = pd.read_csv(path)
    if cat_cols:
        for col in cat_cols:
            df[col] = LabelEncoder().fit_transform(df[col])
    feature_cols = [c for c in df.columns if c != target_col]
    X = df[feature_cols].values.astype(float)
    y = df[target_col].values.astype(int)
    return X, y


def _preprocess(X: np.ndarray, y: np.ndarray, n_train: int, n_test: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """PCA to N_QUBITS dimensions, scale to [0, π], stratified split."""
    # Balance classes
    pos_idx = np.where(y == 1)[0]
    neg_idx = np.where(y == 0)[0]
    rng = np.random.default_rng(42)
    n_each = min(len(pos_idx), len(neg_idx), (n_train + n_test) // 2)
    idx = np.concatenate([
        rng.choice(pos_idx, n_each, replace=False),
        rng.choice(neg_idx, n_each, replace=False),
    ])
    X_sub, y_sub = X[idx], y[idx]

    pca = PCA(n_components=N_QUBITS, random_state=42)
    scaler = MinMaxScaler(feature_range=(0, np.pi))
    X_pca = pca.fit_transform(X_sub)
    X_scaled = scaler.fit_transform(X_pca)

    test_size = min(n_test, len(X_scaled) - n_train)
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y_sub,
        train_size=min(n_train, len(X_scaled) - test_size),
        test_size=test_size,
        random_state=42,
        stratify=y_sub,
    )
    return X_train, X_test, y_train, y_test


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(X_train: np.ndarray, y_train: np.ndarray) -> tuple[jnp.ndarray, list[float]]:
    """Adam optimisation loop over VQC parameters."""
    rng = np.random.default_rng(0)
    n_params = N_LAYERS * N_QUBITS * 2
    weights = jnp.array(rng.uniform(-np.pi, np.pi, n_params))

    # Adam state
    m = jnp.zeros_like(weights)
    v = jnp.zeros_like(weights)
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    lr = LEARNING_RATE
    losses: list[float] = []

    n = len(X_train)
    for epoch in range(EPOCHS):
        idx = np.random.choice(n, min(BATCH_SIZE, n), replace=False)
        Xb = jnp.array(X_train[idx])
        yb = y_train[idx]

        yb_jnp = jnp.array(yb)
        loss = float(_cost_jit(weights, Xb, yb_jnp))
        g = _grad_fn(weights, Xb, yb_jnp)

        t = epoch + 1
        m = beta1 * m + (1 - beta1) * g
        v = beta2 * v + (1 - beta2) * g ** 2
        m_hat = m / (1 - beta1 ** t)
        v_hat = v / (1 - beta2 ** t)
        weights = weights - lr * m_hat / (jnp.sqrt(v_hat) + eps)

        losses.append(loss)
        if (epoch + 1) % 10 == 0:
            print(f"    epoch {epoch+1:>3}/{EPOCHS}  loss={loss:.4f}")

    return weights, losses


def predict(weights: jnp.ndarray, X: np.ndarray) -> np.ndarray:
    raw = np.array(_vqc_batched(jnp.array(X), weights))
    return (raw > 0.0).astype(int)


# ---------------------------------------------------------------------------
# Per-dataset experiment
# ---------------------------------------------------------------------------

def run_experiment(
    dataset_name: str,
    filename: str,
    target_col: str,
    cat_cols: list[str] | None = None,
) -> dict[str, Any]:
    print(f"\n--- VQC Experiment: {dataset_name} ---")

    try:
        X, y = _load_and_encode(filename, target_col, cat_cols)
    except FileNotFoundError as e:
        print(f"  Skipping — {e}")
        return {"dataset": dataset_name, "error": str(e)}

    X_train, X_test, y_train, y_test = _preprocess(X, y, TRAIN_SAMPLES, TEST_SAMPLES)
    print(f"  Train: {len(X_train)}  Test: {len(X_test)}  Pos rate: {y_test.mean():.2%}")
    print(f"  Circuit: {N_QUBITS} qubits, {N_LAYERS} layers, {N_LAYERS * N_QUBITS * 2} params")

    print(f"  Training VQC ({EPOCHS} epochs, Adam lr={LEARNING_RATE})...")
    t0 = time.perf_counter()
    weights, losses = train(X_train, y_train)
    train_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    y_pred = predict(weights, X_test)
    predict_time = time.perf_counter() - t0

    acc = float(accuracy_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    try:
        raw_scores = np.array(_vqc_batched(jnp.array(X_test), weights))
        auc = float(roc_auc_score(y_test, raw_scores))
    except Exception:
        auc = 0.0

    print(f"  acc={acc:.4f}  f1={f1:.4f}  auc={auc:.4f}  train_time={train_time:.1f}s")

    # Draw circuit (first sample)
    try:
        circuit_diagram = str(qml.draw(vqc)(jnp.array(X_test[0]), weights))
    except Exception:
        circuit_diagram = "unavailable"

    return {
        "dataset": dataset_name,
        "model": "VQC-PennyLane",
        "n_qubits": N_QUBITS,
        "n_layers": N_LAYERS,
        "n_params": N_LAYERS * N_QUBITS * 2,
        "encoding": "angle-encoding-RY",
        "epochs": EPOCHS,
        "learning_rate": LEARNING_RATE,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "accuracy": acc,
        "f1": f1,
        "roc_auc": auc,
        "train_time_s": round(train_time, 4),
        "predict_time_s": round(predict_time, 4),
        "loss_history": [round(l, 6) for l in losses],
        "final_loss": round(losses[-1], 6) if losses else None,
        "circuit_diagram": circuit_diagram,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> list[dict]:
    print("=" * 60)
    print("QC Healthcare Lab — Quantum Disease Classifier (VQC)")
    print("=" * 60)

    results = []

    results.append(run_experiment(
        dataset_name="diabetes",
        filename="diabetes.csv",
        target_col="Outcome",
    ))

    results.append(run_experiment(
        dataset_name="heart_disease",
        filename="heart.csv",
        target_col="HeartDisease",
        cat_cols=["Sex", "ChestPainType", "RestingECG", "ExerciseAngina", "ST_Slope"],
    ))

    # Filter out error-only entries for saving but keep them in return value
    valid = [r for r in results if "error" not in r]
    if not valid:
        print("No experiments completed successfully.")
        return results

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved → {RESULTS_FILE}")

    print("\n--- Quantum Results Summary ---")
    print(f"{'Dataset':<18} {'Acc':>6}  {'F1':>6}  {'AUC':>6}  {'Train(s)':>9}")
    print("-" * 52)
    for r in valid:
        print(
            f"{r['dataset']:<18} {r['accuracy']:>6.4f}  {r['f1']:>6.4f}  "
            f"{r['roc_auc']:>6.4f}  {r['train_time_s']:>9.1f}"
        )

    return results


if __name__ == "__main__":
    main()
