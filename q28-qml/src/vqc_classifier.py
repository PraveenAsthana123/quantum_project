"""
Variational Quantum Classifier (VQC) on MNIST digits 0 vs 1.

Pipeline:
  - Load mnist_train.csv / mnist_test.csv
  - Filter digits 0 and 1 only
  - Reduce 784 features → 4 features via PCA
  - Scale features to [0, π] for angle encoding
  - 4-qubit VQC with 2 entangling layers trained using JAX + Adam
  - Save results to data/vqc_results.json

Circuit structure (per qubit):
  RY(x_i) → [RY(w_i) RZ(w_i') CNOT ring] × n_layers → expval(PauliZ(0))
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

import jax
import jax.numpy as jnp
import numpy as np
import pandas as pd
import pennylane as qml
from sklearn.decomposition import PCA
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

jax.config.update("jax_enable_x64", True)
warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent / "data"
RESULTS_FILE = DATA_DIR / "vqc_results.json"
DATASETS_DIR = Path(__file__).parent.parent.parent / "datasets" / "qml"

# ---- Hyperparameters ----
N_QUBITS = 4
N_LAYERS = 2
N_FEATURES = N_QUBITS   # PCA target dimension
EPOCHS = 40
LEARNING_RATE = 0.05
BATCH_SIZE = 16
TRAIN_SAMPLES = 300      # per class (balanced)
TEST_SAMPLES = 100       # per class (balanced)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_mnist_binary(
    train_csv: Path,
    test_csv: Path,
    digit_a: int = 0,
    digit_b: int = 1,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Load MNIST, keep only digit_a and digit_b, return (X_tr, X_te, y_tr, y_te)."""
    if train_csv.exists() and test_csv.exists():
        print(f"Loading MNIST from {train_csv.parent}")
        df_train = pd.read_csv(train_csv)
        df_test = pd.read_csv(test_csv)
    else:
        # Synthetic fallback
        print("MNIST CSVs not found — using synthetic pixel data")
        rng = np.random.default_rng(42)
        n = 1000
        X_syn = rng.integers(0, 256, (n, 784)).astype(float)
        y_syn = rng.integers(0, 2, n)
        half = n // 2
        return X_syn[:half], X_syn[half:], y_syn[:half], y_syn[half:]

    # Standardise column names
    label_col = "label" if "label" in df_train.columns else df_train.columns[0]

    def filter_and_balance(df: pd.DataFrame, n_per_class: int | None = None) -> tuple[np.ndarray, np.ndarray]:
        mask = df[label_col].isin([digit_a, digit_b])
        df = df[mask].copy()
        if n_per_class:
            da = df[df[label_col] == digit_a].sample(
                min(n_per_class, (df[label_col] == digit_a).sum()), random_state=42
            )
            db = df[df[label_col] == digit_b].sample(
                min(n_per_class, (df[label_col] == digit_b).sum()), random_state=42
            )
            df = pd.concat([da, db]).sample(frac=1, random_state=42)
        feat_cols = [c for c in df.columns if c != label_col]
        X = df[feat_cols].values.astype(float)
        y = (df[label_col] == digit_b).astype(int).values   # 0=digit_a, 1=digit_b
        return X, y

    X_tr, y_tr = filter_and_balance(df_train, TRAIN_SAMPLES)
    X_te, y_te = filter_and_balance(df_test, TEST_SAMPLES)
    print(f"  Train: {len(X_tr)} (label 0={( y_tr==0).sum()}, 1={(y_tr==1).sum()})")
    print(f"  Test : {len(X_te)} (label 0={(y_te==0).sum()}, 1={(y_te==1).sum()})")
    return X_tr, X_te, y_tr, y_te


def preprocess(
    X_train: np.ndarray,
    X_test: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """PCA → scale to [0, π]."""
    pca = PCA(n_components=N_FEATURES, random_state=42)
    scaler = MinMaxScaler(feature_range=(0.0, np.pi))

    X_train_pca = pca.fit_transform(X_train)
    X_test_pca = pca.transform(X_test)

    X_train_sc = scaler.fit_transform(X_train_pca)
    X_test_sc = scaler.transform(X_test_pca)

    print(f"  PCA variance explained: {pca.explained_variance_ratio_.sum():.3f}")
    return X_train_sc, X_test_sc


# ---------------------------------------------------------------------------
# VQC circuit
# ---------------------------------------------------------------------------

dev = qml.device("default.qubit", wires=N_QUBITS)


@qml.qnode(dev, interface="jax")
def vqc(features: jnp.ndarray, weights: jnp.ndarray) -> float:
    """
    4-qubit VQC.
    weights shape: (N_LAYERS, N_QUBITS, 2)  — [RY angle, RZ angle] per qubit per layer
    Returns: expectation value of PauliZ on qubit 0  ∈ [-1, +1]
    """
    # Feature encoding: angle embedding
    for i in range(N_QUBITS):
        qml.RY(features[i], wires=i)

    # Variational layers
    for layer in range(N_LAYERS):
        for i in range(N_QUBITS):
            qml.RY(weights[layer, i, 0], wires=i)
            qml.RZ(weights[layer, i, 1], wires=i)
        # CNOT entanglement ring
        for i in range(N_QUBITS - 1):
            qml.CNOT(wires=[i, i + 1])
        qml.CNOT(wires=[N_QUBITS - 1, 0])

    return qml.expval(qml.PauliZ(0))


# Vectorise over samples
vqc_batched = jax.vmap(vqc, in_axes=(0, None))


def cost_fn(weights: jnp.ndarray, X: jnp.ndarray, y: jnp.ndarray) -> jnp.ndarray:
    """MSE loss with labels mapped to ±1."""
    preds = vqc_batched(X, weights)
    labels = jnp.where(y == 1, 1.0, -1.0)
    return jnp.mean((preds - labels) ** 2)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> tuple[jnp.ndarray, list[float]]:
    rng = np.random.default_rng(0)
    weights = jnp.array(rng.uniform(-np.pi, np.pi, (N_LAYERS, N_QUBITS, 2)))

    grad_fn = jax.jit(jax.grad(cost_fn))
    forward_fn = jax.jit(cost_fn)

    # Adam
    lr = LEARNING_RATE
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    m = jnp.zeros_like(weights)
    v = jnp.zeros_like(weights)

    losses: list[float] = []
    n = len(X_train)

    for epoch in range(EPOCHS):
        idx = np.random.choice(n, min(BATCH_SIZE, n), replace=False)
        Xb = jnp.array(X_train[idx])
        yb = jnp.array(y_train[idx])

        loss = float(forward_fn(weights, Xb, yb))
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


def predict(weights: jnp.ndarray, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (binary predictions, raw scores)."""
    X_jax = jnp.array(X)
    raw = np.array(vqc_batched(X_jax, weights))
    preds = (raw > 0.0).astype(int)
    return preds, raw


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  Q28 QML — VQC Classifier (MNIST 0 vs 1)")
    print("=" * 60)

    train_csv = DATASETS_DIR / "mnist_train.csv"
    test_csv = DATASETS_DIR / "mnist_test.csv"

    X_tr_raw, X_te_raw, y_train, y_test = load_mnist_binary(train_csv, test_csv)
    X_train, X_test = preprocess(X_tr_raw, X_te_raw)

    print(f"\nTraining VQC ({N_QUBITS} qubits, {N_LAYERS} layers, {EPOCHS} epochs)...")
    t0 = time.perf_counter()
    weights, losses = train(X_train, y_train)
    train_time = time.perf_counter() - t0
    print(f"  Training done in {train_time:.1f}s")

    print("\nEvaluating on test set...")
    t0 = time.perf_counter()
    y_pred, raw_scores = predict(weights, X_test)
    predict_time = time.perf_counter() - t0

    acc = float(accuracy_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    cm = confusion_matrix(y_test, y_pred)
    try:
        auc = float(roc_auc_score(y_test, raw_scores))
    except Exception:
        auc = 0.0

    print(f"\nVQC Results (MNIST 0 vs 1):")
    print(f"  accuracy={acc:.4f}  f1={f1:.4f}  auc={auc:.4f}")
    print(f"  train_time={train_time:.1f}s  predict_time={predict_time:.3f}s")

    circuit_diagram = str(qml.draw(vqc)(
        jnp.array(X_train[0]),
        weights,
    ))

    result = {
        "model": "VQC-PennyLane",
        "task": "mnist-binary-0vs1",
        "n_qubits": N_QUBITS,
        "n_layers": N_LAYERS,
        "n_features_pca": N_FEATURES,
        "epochs": EPOCHS,
        "learning_rate": LEARNING_RATE,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "accuracy": acc,
        "f1": f1,
        "roc_auc": auc,
        "confusion_matrix": cm.tolist(),
        "train_time_s": round(train_time, 4),
        "predict_time_s": round(predict_time, 4),
        "loss_history": [round(float(l), 6) for l in losses],
        "classification_report": classification_report(
            y_test, y_pred, output_dict=True, zero_division=0
        ),
        "circuit_diagram": circuit_diagram,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as fh:
        json.dump(result, fh, indent=2)
    print(f"\nResults saved → {RESULTS_FILE}")
    return result


if __name__ == "__main__":
    main()
