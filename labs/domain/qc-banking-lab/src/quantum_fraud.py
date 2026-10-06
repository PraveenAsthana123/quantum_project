"""
Quantum ML fraud detector using PennyLane VQC.
Reduces features via PCA then trains a Variational Quantum Classifier.
Compares performance against classical baseline.
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

import jax
import jax.numpy as jnp
import pennylane as qml

jax.config.update("jax_enable_x64", True)
warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent / "data"
RESULTS_FILE = DATA_DIR / "quantum_results.json"

N_QUBITS = 4
N_LAYERS = 2
EPOCHS = 30
LEARNING_RATE = 0.1
TRAIN_SAMPLES = 400   # balanced subset from real data
TEST_SAMPLES = 200


# ---------------------------------------------------------------------------
# Circuit definition
# ---------------------------------------------------------------------------

dev = qml.device("default.qubit", wires=N_QUBITS)


@qml.qnode(dev, interface="jax")
def vqc(features, weights):
    """Variational Quantum Classifier circuit.
    weights: flat 1-D array of length N_LAYERS * N_QUBITS * 2
    """
    for i in range(N_QUBITS):
        qml.RY(features[i], wires=i)

    for layer in range(N_LAYERS):
        for i in range(N_QUBITS):
            base = layer * N_QUBITS * 2 + i * 2
            qml.RY(weights[base], wires=i)
            qml.RZ(weights[base + 1], wires=i)
        for i in range(N_QUBITS - 1):
            qml.CNOT(wires=[i, i + 1])
        qml.CNOT(wires=[N_QUBITS - 1, 0])

    return qml.expval(qml.PauliZ(0))


vqc_batched = jax.vmap(vqc, in_axes=(0, None))


def cost_fn(weights, X, y):
    predictions = vqc_batched(X, weights)
    labels = jnp.array([1.0 if yi == 1 else -1.0 for yi in y])
    return jnp.mean((predictions - labels) ** 2)


# ---------------------------------------------------------------------------
# Data loading + preprocessing
# ---------------------------------------------------------------------------

def load_balanced_subset() -> tuple[np.ndarray, np.ndarray]:
    csv_path = DATA_DIR / "creditcard.csv"
    if not csv_path.exists():
        csv_path = DATA_DIR / "creditcardfraud" / "creditcard.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        fraud = df[df["Class"] == 1]
        normal = df[df["Class"] == 0].sample(len(fraud) * 3, random_state=42)
        df = pd.concat([fraud, normal]).sample(frac=1, random_state=42)
        feature_cols = [c for c in df.columns if c not in ("Class", "Time")]
        X = df[feature_cols].values
        y = df["Class"].values
    else:
        print("Demo data — run: qlab data qc-banking-lab")
        rng = np.random.default_rng(42)
        n = 400
        X = rng.standard_normal((n, 29))
        y = np.array([1] * (n // 4) + [0] * (3 * n // 4))
        rng.shuffle(y)

    # Split FIRST — preprocessing must be fit on train data only to prevent leakage
    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    # Fit PCA + scaler on TRAIN data only
    pca = PCA(n_components=N_QUBITS)
    scaler = MinMaxScaler(feature_range=(0, np.pi))
    X_train_pca = pca.fit_transform(X_train_raw)
    X_train = scaler.fit_transform(X_train_pca)
    # Transform test with TRAIN-fitted preprocessor (no fit_transform)
    X_test_pca = pca.transform(X_test_raw)
    X_test = scaler.transform(X_test_pca)
    # Reconstruct a combined array for the caller; it will re-split deterministically
    X_all = np.concatenate([X_train, X_test], axis=0)
    y_all = np.concatenate([y_train, y_test], axis=0)
    return X_all, y_all


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(X_train: np.ndarray, y_train: np.ndarray) -> tuple[np.ndarray, list[float]]:
    rng = np.random.default_rng(0)
    weights = jnp.array(rng.uniform(-np.pi, np.pi, N_LAYERS * N_QUBITS * 2))

    grad_fn = jax.grad(cost_fn)
    losses: list[float] = []

    # Adam hyperparams
    lr = LEARNING_RATE
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    m = jnp.zeros_like(weights)
    v = jnp.zeros_like(weights)

    batch_size = min(20, len(X_train))
    for epoch in range(EPOCHS):
        idx = np.random.choice(len(X_train), batch_size, replace=False)
        Xb = jnp.array(X_train[idx])
        yb = y_train[idx]

        loss = float(cost_fn(weights, Xb, yb))
        g = grad_fn(weights, Xb, yb)

        t = epoch + 1
        m = beta1 * m + (1 - beta1) * g
        v = beta2 * v + (1 - beta2) * g ** 2
        m_hat = m / (1 - beta1 ** t)
        v_hat = v / (1 - beta2 ** t)
        weights = weights - lr * m_hat / (jnp.sqrt(v_hat) + eps)

        losses.append(loss)
        if (epoch + 1) % 10 == 0:
            print(f"  epoch {epoch+1}/{EPOCHS}  loss={loss:.4f}")

    return weights, losses


def predict(weights, X):
    X_jax = jnp.array(X)
    raw = np.array(vqc_batched(X_jax, weights))
    return (raw > 0.0).astype(int)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Loading and preprocessing data...")
    # load_balanced_subset() already splits train/test and fits preprocessor on train only.
    # The returned array is [train | test] concatenated; re-split with the same seed/ratio
    # (0.2 test, random_state=42, stratified) used inside load_balanced_subset().
    X, y = load_balanced_subset()
    n_total = len(X)
    n_test_full = int(n_total * 0.2)
    n_train_full = n_total - n_test_full
    # Slice deterministically: first n_train_full rows are train, rest are test
    X_train_full, X_test_full = X[:n_train_full], X[n_train_full:]
    y_train_full, y_test_full = y[:n_train_full], y[n_train_full:]
    # Sub-sample to TRAIN_SAMPLES / TEST_SAMPLES for VQC speed
    n_train = min(TRAIN_SAMPLES, n_train_full)
    n_test = min(TEST_SAMPLES, n_test_full)
    rng_sub = np.random.default_rng(0)
    tr_idx = rng_sub.choice(n_train_full, n_train, replace=False)
    te_idx = rng_sub.choice(n_test_full, n_test, replace=False)
    X_train, y_train = X_train_full[tr_idx], y_train_full[tr_idx]
    X_test, y_test = X_test_full[te_idx], y_test_full[te_idx]
    print(f"Train: {len(X_train)}  Test: {len(X_test)}  Fraud rate: {y_test.mean():.2%}")

    print(f"\nTraining VQC ({N_QUBITS} qubits, {N_LAYERS} layers, {EPOCHS} epochs)...")
    t0 = time.perf_counter()
    weights, losses = train(X_train, y_train)
    train_time = time.perf_counter() - t0

    print("\nEvaluating on test set...")
    t0 = time.perf_counter()
    y_pred = predict(weights, X_test)
    predict_time = time.perf_counter() - t0

    acc = float(accuracy_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    try:
        raw_scores = np.array(vqc_batched(jnp.array(X_test), weights))
        auc = float(roc_auc_score(y_test, raw_scores))
    except Exception:
        auc = 0.0

    print(f"\nVQC results:")
    print(f"  accuracy={acc:.4f}  f1={f1:.4f}  auc={auc:.4f}")
    print(f"  train_time={train_time:.1f}s  predict_time={predict_time:.3f}s")

    # Circuit info
    circuit_info = qml.draw(vqc)(X_train[0], weights)

    result = {
        "model": "VQC-PennyLane",
        "n_qubits": N_QUBITS,
        "n_layers": N_LAYERS,
        "epochs": EPOCHS,
        "accuracy": acc,
        "f1": f1,
        "roc_auc": auc,
        "train_time_s": round(train_time, 4),
        "predict_time_s": round(predict_time, 4),
        "loss_history": losses,
        "circuit_diagram": str(circuit_info),
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as fh:
        json.dump(result, fh, indent=2)
    print(f"\nResults saved → {RESULTS_FILE}")
    return result


if __name__ == "__main__":
    main()
