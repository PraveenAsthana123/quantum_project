"""
Quantum Intrusion Detection System (Q-IDS) using a Variational Quantum Classifier.

Uses PennyLane with angle encoding on 4–6 qubits to perform binary classification
(normal vs. attack) on NSL-KDD network traffic data.

Architecture:
  • PCA → N_QUBITS components (feature compression)
  • MinMaxScaler → [0, π] (angle encoding range)
  • Circuit: angle-encode features with RY gates, then alternating
    RY/RZ rotation layers + CNOT ring entanglement
  • Optimise with Adam gradient descent (JAX backend)
  • Saves results to data/quantum_ids_results.json
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
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

import jax
import jax.numpy as jnp
import pennylane as qml

jax.config.update("jax_enable_x64", True)
warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data"
RESULTS_FILE = DATA_DIR / "quantum_ids_results.json"

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

# ── Hyperparameters ────────────────────────────────────────────────────────────
N_QUBITS   = 6      # qubits (PCA components)
N_LAYERS   = 2      # variational layers
EPOCHS     = 40
LEARNING_RATE = 0.08
TRAIN_SAMPLES = 500   # balanced subset kept small for demo speed
TEST_SAMPLES  = 200


# ── Quantum device + circuit ───────────────────────────────────────────────────
dev = qml.device("default.qubit", wires=N_QUBITS)


@qml.qnode(dev, interface="jax")
def vqc_ids(features, weights):
    """
    Angle-encoding VQC for intrusion detection.
    features : shape (N_QUBITS,) — already in [0, π]
    weights  : shape (N_LAYERS * N_QUBITS * 2,)
    Returns  : expectation value of Z on qubit 0  ∈ [-1, +1]
    """
    # ── Encoding layer ────────────────────────────────────────────────────────
    for i in range(N_QUBITS):
        qml.RY(features[i], wires=i)

    # ── Variational layers ────────────────────────────────────────────────────
    for layer in range(N_LAYERS):
        for i in range(N_QUBITS):
            base = layer * N_QUBITS * 2 + i * 2
            qml.RY(weights[base],     wires=i)
            qml.RZ(weights[base + 1], wires=i)
        # CNOT ring entanglement
        for i in range(N_QUBITS - 1):
            qml.CNOT(wires=[i, i + 1])
        qml.CNOT(wires=[N_QUBITS - 1, 0])

    return qml.expval(qml.PauliZ(0))


vqc_ids_batched = jax.vmap(vqc_ids, in_axes=(0, None))


def cost_fn(weights, X, y):
    """MSE loss: labels in {-1, +1}."""
    preds  = vqc_ids_batched(X, weights)
    labels = jnp.array([1.0 if yi == 1 else -1.0 for yi in y])
    return jnp.mean((preds - labels) ** 2)


# ── Data loading ───────────────────────────────────────────────────────────────

def load_balanced_subset() -> tuple[np.ndarray, np.ndarray]:
    """Load NSL-KDD, binary-encode labels, balance classes, PCA + scale."""
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
        print(f"Loading NSL-KDD from {txt_path}")
        df = pd.read_csv(txt_path, header=None, names=NSL_KDD_COLUMNS)
        y_all = (df["label"].str.strip().str.lower() != "normal").astype(int).values
        for col in CATEGORICAL_COLS:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
        feature_cols = [c for c in df.columns if c not in ("label", "difficulty")]
        X_all = df[feature_cols].values.astype(float)
    else:
        print("NSL-KDD not found — generating demo data")
        rng = np.random.default_rng(42)
        n = 1000
        X_all = rng.standard_normal((n, 41))
        y_all = (rng.random(n) < 0.5).astype(int)

    # Balance: equal normal + attack, cap at TRAIN_SAMPLES + TEST_SAMPLES
    n_want = (TRAIN_SAMPLES + TEST_SAMPLES) // 2
    rng = np.random.default_rng(42)
    idx0 = np.where(y_all == 0)[0]
    idx1 = np.where(y_all == 1)[0]
    k = min(n_want, len(idx0), len(idx1))
    idx0 = rng.choice(idx0, k, replace=False)
    idx1 = rng.choice(idx1, k, replace=False)
    idx  = np.concatenate([idx0, idx1])
    rng.shuffle(idx)
    X_bal, y_bal = X_all[idx], y_all[idx]

    # PCA → N_QUBITS components, scale to [0, π] for angle encoding
    pca    = PCA(n_components=N_QUBITS)
    scaler = MinMaxScaler(feature_range=(0, np.pi))
    X_pca    = pca.fit_transform(X_bal)
    X_scaled = scaler.fit_transform(X_pca)

    print(f"  Balanced subset: {len(X_scaled)} samples  "
          f"(attack rate={y_bal.mean():.0%}  qubits={N_QUBITS})")
    return X_scaled, y_bal


# ── Training loop (Adam) ───────────────────────────────────────────────────────

def train(X_train: np.ndarray, y_train: np.ndarray) -> tuple[jnp.ndarray, list[float]]:
    n_params = N_LAYERS * N_QUBITS * 2
    rng      = np.random.default_rng(0)
    weights  = jnp.array(rng.uniform(-np.pi, np.pi, n_params))

    grad_fn = jax.grad(cost_fn)
    losses: list[float] = []
    lr = LEARNING_RATE
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    m = jnp.zeros_like(weights)
    v = jnp.zeros_like(weights)

    batch_size = min(32, len(X_train))

    for epoch in range(EPOCHS):
        idx  = np.random.default_rng(epoch).choice(len(X_train), batch_size, replace=False)
        Xb   = jnp.array(X_train[idx])
        yb   = y_train[idx]

        loss = float(cost_fn(weights, Xb, yb))
        g    = grad_fn(weights, Xb, yb)

        t     = epoch + 1
        m     = beta1 * m + (1 - beta1) * g
        v     = beta2 * v + (1 - beta2) * g ** 2
        m_hat = m / (1 - beta1 ** t)
        v_hat = v / (1 - beta2 ** t)
        weights = weights - lr * m_hat / (jnp.sqrt(v_hat) + eps)

        losses.append(loss)
        if (epoch + 1) % 10 == 0:
            print(f"  epoch {epoch+1:3d}/{EPOCHS}  loss={loss:.4f}")

    return weights, losses


def predict(weights: jnp.ndarray, X: np.ndarray) -> np.ndarray:
    raw = np.array(vqc_ids_batched(jnp.array(X), weights))
    return (raw > 0.0).astype(int)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Quantum Intrusion Detection System (Q-IDS)")
    print(f"  {N_QUBITS} qubits  |  {N_LAYERS} variational layers  |  {EPOCHS} epochs")
    print("=" * 60)

    X, y = load_balanced_subset()

    n_train = min(TRAIN_SAMPLES, int(len(X) * 0.8))
    n_test  = min(TEST_SAMPLES,  len(X) - n_train)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        train_size=n_train,
        test_size=n_test,
        random_state=42,
        stratify=y,
    )
    print(f"\nSplit  →  train={len(X_train)}  test={len(X_test)}")

    print(f"\nTraining VQC...")
    t0 = time.perf_counter()
    weights, losses = train(X_train, y_train)
    train_time = time.perf_counter() - t0

    print("\nEvaluating on test set...")
    t0 = time.perf_counter()
    y_pred = predict(weights, X_test)
    predict_time = time.perf_counter() - t0

    acc = float(accuracy_score(y_test, y_pred))
    f1  = float(f1_score(y_test, y_pred, zero_division=0))
    try:
        raw_scores = np.array(vqc_ids_batched(jnp.array(X_test), weights))
        auc = float(roc_auc_score(y_test, raw_scores))
    except Exception:
        auc = 0.0

    print(f"\n  accuracy={acc:.4f}  f1={f1:.4f}  auc={auc:.4f}")
    print(f"  train_time={train_time:.1f}s  predict_time={predict_time:.3f}s")

    # Circuit diagram for the first test sample
    circuit_diagram = str(qml.draw(vqc_ids)(X_test[0], weights))

    result = {
        "model": "Q-IDS VQC (PennyLane)",
        "task": "network intrusion detection — binary (normal vs. attack)",
        "dataset": "NSL-KDD",
        "n_qubits": N_QUBITS,
        "n_layers": N_LAYERS,
        "n_params": N_LAYERS * N_QUBITS * 2,
        "epochs": EPOCHS,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "accuracy": acc,
        "f1": f1,
        "roc_auc": auc,
        "train_time_s": round(train_time, 4),
        "predict_time_s": round(predict_time, 4),
        "loss_history": [round(l, 6) for l in losses],
        "circuit_diagram": circuit_diagram,
        "encoding": "angle encoding — RY gates from PCA-compressed features scaled to [0, π]",
        "entanglement": "CNOT ring",
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as fh:
        json.dump(result, fh, indent=2)
    print(f"\nResults saved → {RESULTS_FILE}")
    return result


if __name__ == "__main__":
    main()
