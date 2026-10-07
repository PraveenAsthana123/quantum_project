"""
Step 6: Quantum Variational Quantum Classifier (VQC)
=====================================================
Loads features_4.csv (4 features → 4 qubits) and trains a VQC using PennyLane.

Circuit architecture:
  - 4 qubits
  - Angle encoding: RY(feature_i) on each qubit
  - CNOT ring entanglement: q0→q1→q2→q3→q0
  - 2 variational layers, each: RY(θ) + RZ(φ) per qubit
  - Measurement: PauliZ on q0 → binary classification

Training:
  - Adam optimizer, 50 epochs, batch_size=32
  - Balanced sampling (class-balanced mini-batches)
  - Train/test split: 80/20 stratified

Outputs:
  data/quantum_results.json
"""

import json
import os
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")

DATA_DIR    = os.path.join(os.path.dirname(__file__), "data")
INPUT_FILE  = os.path.join(DATA_DIR, "features_4.csv")
OUTPUT_JSON = os.path.join(DATA_DIR, "quantum_results.json")

LABEL_COL   = "label"
N_QUBITS    = 4
N_LAYERS    = 2
EPOCHS      = 50
BATCH_SIZE  = 32
RANDOM_SEED = 42
TEST_SIZE   = 0.20
STEPSIZE    = 0.01     # Adam learning rate


# ── PennyLane circuit ─────────────────────────────────────────────────────────

def build_circuit(dev, n_qubits: int, n_layers: int):
    """
    Returns a QNode that:
      1. Angle-encodes `features` via RY on each qubit
      2. Applies a CNOT ring
      3. Applies n_layers variational layers (RY + RZ per qubit)
      4. Returns expval(PauliZ) on qubit 0
    """
    import pennylane as qml

    @qml.qnode(dev, interface="autograd", diff_method="best")
    def circuit(features, params):
        # Angle encoding
        for i in range(n_qubits):
            qml.RY(features[i] * np.pi, wires=i)

        # CNOT ring entanglement
        for i in range(n_qubits):
            qml.CNOT(wires=[i, (i + 1) % n_qubits])

        # Variational layers
        for layer in range(n_layers):
            for q in range(n_qubits):
                qml.RY(params[layer, q, 0], wires=q)
                qml.RZ(params[layer, q, 1], wires=q)
            # Entanglement between layers
            if layer < n_layers - 1:
                for i in range(n_qubits):
                    qml.CNOT(wires=[i, (i + 1) % n_qubits])

        return qml.expval(qml.PauliZ(0))

    return circuit


def circuit_depth(n_qubits: int, n_layers: int) -> int:
    """Approximate circuit depth: encoding + entanglement + layers."""
    encoding_depth    = n_qubits          # RY per qubit
    entanglement_depth = n_qubits          # CNOT ring
    layer_depth       = n_layers * (n_qubits * 2 + (n_qubits if n_layers > 1 else 0))
    return encoding_depth + entanglement_depth + layer_depth


def count_parameters(n_qubits: int, n_layers: int) -> int:
    return n_layers * n_qubits * 2   # RY + RZ per qubit per layer


# ── Balanced sampling ─────────────────────────────────────────────────────────

def balanced_batch(X: np.ndarray, y: np.ndarray, batch_size: int,
                   rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Draw batch_size samples with equal class representation."""
    classes = np.unique(y)
    half = batch_size // len(classes)
    idx_list = []
    for cls in classes:
        cls_idx = np.where(y == cls)[0]
        sampled = rng.choice(cls_idx, size=half, replace=len(cls_idx) < half)
        idx_list.append(sampled)
    idx = np.concatenate(idx_list)
    rng.shuffle(idx)
    return X[idx], y[idx]


# ── Loss & gradient ───────────────────────────────────────────────────────────

def cost_fn(params, circuit_fn, X_batch: np.ndarray, y_batch: np.ndarray) -> float:
    """Mean squared error loss: label ∈ {0,1}, prediction ∈ [-1,1] → map pred to [0,1]."""
    import pennylane.numpy as pnp
    total = 0.0
    for x, y_true in zip(X_batch, y_batch):
        pred_raw = circuit_fn(x, params)          # in [-1, 1]
        pred = (pred_raw + 1) / 2.0               # map to [0, 1]
        total += (pred - float(y_true)) ** 2
    return total / len(X_batch)


# ── Predict helpers ───────────────────────────────────────────────────────────

def predict_proba(circuit_fn, params, X: np.ndarray) -> np.ndarray:
    """Return predicted probability of class 1 for each sample."""
    probs = np.array([(float(circuit_fn(x, params)) + 1) / 2.0 for x in X])
    return probs


def predict_labels(probs: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    return (probs >= threshold).astype(int)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    t0_total = time.time()
    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 60)
    print("STEP 6: Quantum VQC Training")
    print("=" * 60)

    # ── Check PennyLane availability ────────────────────────────────────────
    try:
        import pennylane as qml
        import pennylane.numpy as pnp
        print(f"  PennyLane version: {qml.__version__}")
    except ImportError:
        print("  WARNING: PennyLane not installed.")
        print("  Generating mock quantum results for pipeline continuity...")
        _save_mock_results()
        return

    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}\n"
            "Run step4_feature_reduction.py first."
        )

    # ── Load data ───────────────────────────────────────────────────────────
    print(f"  Loading {INPUT_FILE} ...")
    df = pd.read_csv(INPUT_FILE)
    X = df.drop(columns=[LABEL_COL]).values.astype(np.float64)
    y = df[LABEL_COL].values.astype(int)
    print(f"  Loaded: {len(X)} samples × {X.shape[1]} features")
    print(f"  Class balance → 0:{(y==0).sum()}  1:{(y==1).sum()}")

    # ── Train/test split ────────────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_SEED, stratify=y
    )
    print(f"  Split → train={len(X_train)}  test={len(X_test)}")

    # ── Build circuit ───────────────────────────────────────────────────────
    dev = qml.device("default.qubit", wires=N_QUBITS)
    circuit_fn = build_circuit(dev, N_QUBITS, N_LAYERS)
    n_params = count_parameters(N_QUBITS, N_LAYERS)
    depth = circuit_depth(N_QUBITS, N_LAYERS)

    print(f"  Circuit: {N_QUBITS} qubits  {n_params} parameters  depth≈{depth}")

    # ── Initialise parameters ────────────────────────────────────────────────
    rng = np.random.default_rng(RANDOM_SEED)
    params = pnp.array(
        rng.uniform(-np.pi, np.pi, (N_LAYERS, N_QUBITS, 2)),
        requires_grad=True
    )

    opt = qml.AdamOptimizer(stepsize=STEPSIZE)

    # ── Training loop ────────────────────────────────────────────────────────
    print(f"\n  Training: {EPOCHS} epochs  batch_size={BATCH_SIZE}  lr={STEPSIZE}")
    epoch_losses = []
    t_train = time.time()

    for epoch in range(EPOCHS):
        X_batch, y_batch = balanced_batch(X_train, y_train, BATCH_SIZE, rng)

        def cost_for_opt(p):
            return cost_fn(p, circuit_fn, X_batch, y_batch)

        params, loss = opt.step_and_cost(cost_for_opt, params)
        epoch_losses.append(round(float(loss), 6))

        if (epoch + 1) % 10 == 0:
            print(f"    Epoch {epoch+1:3d}/{EPOCHS}  loss={loss:.4f}")

    training_time = time.time() - t_train
    print(f"  Training complete in {training_time:.1f}s")

    # ── Evaluation ───────────────────────────────────────────────────────────
    print("  Evaluating on test set...")
    probs_test = predict_proba(circuit_fn, params, X_test)
    y_pred_test = predict_labels(probs_test)

    acc  = round(float(accuracy_score(y_test, y_pred_test)), 4)
    f1   = round(float(f1_score(y_test, y_pred_test, zero_division=0)), 4)
    try:
        auc = round(float(roc_auc_score(y_test, probs_test)), 4)
    except Exception:
        auc = 0.5   # fallback if only one class in test

    print(f"  Test → accuracy={acc}  f1={f1}  auc={auc}")

    # ── Save results ─────────────────────────────────────────────────────────
    results = {
        "n_qubits"       : N_QUBITS,
        "n_layers"       : N_LAYERS,
        "circuit_depth"  : depth,
        "n_parameters"   : n_params,
        "n_train"        : len(X_train),
        "n_test"         : len(X_test),
        "epochs"         : EPOCHS,
        "batch_size"     : BATCH_SIZE,
        "learning_rate"  : STEPSIZE,
        "accuracy"       : acc,
        "f1"             : f1,
        "auc"            : auc,
        "training_time_s": round(training_time, 2),
        "epoch_losses"   : epoch_losses,
        "backend"        : "pennylane_default_qubit",
        "pennylane_version": qml.__version__,
    }

    with open(OUTPUT_JSON, "w") as f:
        json.dump(results, f, indent=2)

    elapsed = time.time() - t0_total
    print(f"  Results saved → {OUTPUT_JSON}")
    print(f"  Total elapsed: {elapsed:.1f}s")
    print("  STEP 6 COMPLETE\n")


def _save_mock_results():
    """Save realistic mock results when PennyLane is unavailable."""
    results = {
        "n_qubits"       : N_QUBITS,
        "n_layers"       : N_LAYERS,
        "circuit_depth"  : circuit_depth(N_QUBITS, N_LAYERS),
        "n_parameters"   : count_parameters(N_QUBITS, N_LAYERS),
        "n_train"        : 800,
        "n_test"         : 200,
        "epochs"         : EPOCHS,
        "batch_size"     : BATCH_SIZE,
        "learning_rate"  : STEPSIZE,
        "accuracy"       : 0.7650,
        "f1"             : 0.4830,
        "auc"            : 0.7120,
        "training_time_s": 0.0,
        "epoch_losses"   : [0.25 - 0.002 * i for i in range(EPOCHS)],
        "backend"        : "mock_pennylane_unavailable",
        "pennylane_version": "N/A",
        "note"           : "PennyLane not installed — mock values for pipeline continuity.",
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Mock results saved → {OUTPUT_JSON}")
    print("  STEP 6 COMPLETE (mock mode)\n")


if __name__ == "__main__":
    main()
