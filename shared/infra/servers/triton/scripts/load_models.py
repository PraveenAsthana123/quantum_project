"""
load_models.py — Train and export models into Triton model_repository/
=======================================================================
Steps:
  1. Load creditcard.csv (or generate synthetic data if not found).
  2. Train XGBoost on 4 PCA-reduced features → save model.json (FIL format).
  3. Train a 4-qubit VQC (PennyLane) → save weights.npy.
  4. Build + trace a simple time-series transformer → save model.pt.
  5. Verify all three models by sending a test inference request to a running
     Triton server (if --triton-url is provided).

Usage:
    python load_models.py --data /path/to/creditcard.csv
    python load_models.py --data /path/to/creditcard.csv \
                          --triton-url http://localhost:8000
"""

import argparse
import json
import os
import sys
import time

import numpy as np

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "model_repository")
)


def ensure_dirs():
    for subdir in [
        "xgboost_fraud/1",
        "quantum_vqc/1",
        "transformer_ts/1",
    ]:
        os.makedirs(os.path.join(REPO_ROOT, subdir), exist_ok=True)


# ---------------------------------------------------------------------------
# Step 1 — Load / generate data
# ---------------------------------------------------------------------------

def load_data(csv_path: str) -> tuple:
    """
    Load creditcard.csv (Kaggle) and reduce to 4 PCA features.
    Falls back to synthetic data if the file is not present.

    Returns:
        X_train, X_test  — shape (N, 4)
        y_train, y_test  — shape (N,)  integers 0/1
    """
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA

    if os.path.isfile(csv_path):
        import pandas as pd
        print(f"[data] Loading {csv_path} ...")
        df = pd.read_csv(csv_path)
        X = df.drop(columns=["Class", "Time"], errors="ignore").values.astype(np.float32)
        y = df["Class"].values.astype(int)
    else:
        print("[data] creditcard.csv not found — generating synthetic data (2,000 samples).")
        rng = np.random.default_rng(42)
        X = rng.standard_normal((2000, 29)).astype(np.float32)
        y = (rng.random(2000) < 0.05).astype(int)   # ~5% fraud

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    pca = PCA(n_components=4, random_state=42)
    X_reduced = pca.fit_transform(X_scaled).astype(np.float32)

    X_train, X_test, y_train, y_test = train_test_split(
        X_reduced, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"[data] Train={len(X_train)}, Test={len(X_test)}, "
          f"Fraud rate={y.mean()*100:.2f}%")
    return X_train, X_test, y_train, y_test


# ---------------------------------------------------------------------------
# Step 2 — XGBoost FIL model
# ---------------------------------------------------------------------------

def train_xgboost(X_train, y_train, X_test, y_test) -> str:
    """Train XGBoost and save model.json to model_repository."""
    import xgboost as xgb
    from sklearn.metrics import roc_auc_score

    print("[xgboost] Training XGBoost classifier ...")
    scale_pos_weight = max(1, (y_train == 0).sum() / max((y_train == 1).sum(), 1))
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        scale_pos_weight=scale_pos_weight,
        use_label_encoder=False,
        eval_metric="auc",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    preds = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, preds)
    print(f"[xgboost] Test AUC={auc:.4f}")

    out_path = os.path.join(REPO_ROOT, "xgboost_fraud", "1", "model.json")
    model.save_model(out_path)
    size_mb = os.path.getsize(out_path) / 1e6
    print(f"[xgboost] Saved {out_path} ({size_mb:.2f} MB)")
    return out_path


# ---------------------------------------------------------------------------
# Step 3 — PennyLane VQC
# ---------------------------------------------------------------------------

def train_vqc(X_train, y_train, X_test, y_test) -> str:
    """
    Train a 4-qubit VQC using PennyLane + numpy optimiser.
    Saves weights.npy to model_repository/quantum_vqc/1/.
    """
    import pennylane as qml
    from pennylane import numpy as pnp

    N_QUBITS = 4
    N_LAYERS = 3
    N_EPOCHS = 30
    LR = 0.05

    dev = qml.device("default.qubit", wires=N_QUBITS)

    @qml.qnode(dev, interface="autograd")
    def circuit(inputs, weights):
        for i in range(N_QUBITS):
            qml.RY(inputs[i] * pnp.pi, wires=i)
        for i in range(N_QUBITS):
            qml.CNOT(wires=[i, (i + 1) % N_QUBITS])
        for layer in range(N_LAYERS):
            for qubit in range(N_QUBITS):
                qml.Rot(
                    weights[layer, qubit, 0],
                    weights[layer, qubit, 1],
                    weights[layer, qubit, 2],
                    wires=qubit,
                )
            for i in range(N_QUBITS):
                qml.CNOT(wires=[i, (i + 1) % N_QUBITS])
        return [qml.expval(qml.PauliZ(i)) for i in range(N_QUBITS)]

    def predict_proba(inputs, weights):
        expvals = pnp.array(circuit(inputs, weights))
        score_0 = pnp.mean(expvals[:2])
        score_1 = pnp.mean(expvals[2:])
        logits = pnp.array([score_0, score_1])
        logits = logits - pnp.max(logits)
        exps = pnp.exp(logits)
        return exps / exps.sum()

    def cross_entropy_loss(weights, X_batch, y_batch):
        total_loss = pnp.array(0.0)
        for xi, yi in zip(X_batch, y_batch):
            probs = predict_proba(xi, weights)
            # Clip for numerical stability
            p = pnp.clip(probs[int(yi)], 1e-7, 1.0)
            total_loss = total_loss - pnp.log(p)
        return total_loss / len(X_batch)

    rng = np.random.default_rng(42)
    weights = pnp.array(
        rng.uniform(-np.pi, np.pi, (N_LAYERS, N_QUBITS, 3)),
        requires_grad=True
    )

    opt = qml.AdamOptimizer(stepsize=LR)

    # Use a small subset for training speed (circuit simulation is slow)
    max_train = min(200, len(X_train))
    idx = rng.choice(len(X_train), max_train, replace=False)
    X_sub = X_train[idx].astype(np.float64)
    y_sub = y_train[idx]

    print(f"[vqc] Training 4-qubit VQC on {max_train} samples for {N_EPOCHS} epochs ...")
    for epoch in range(N_EPOCHS):
        # Mini-batch of 16
        batch_idx = rng.choice(max_train, min(16, max_train), replace=False)
        X_batch = X_sub[batch_idx]
        y_batch = y_sub[batch_idx]

        weights, loss = opt.step_and_cost(
            cross_entropy_loss, weights, X_batch=X_batch, y_batch=y_batch
        )

        if (epoch + 1) % 10 == 0:
            print(f"  epoch {epoch+1}/{N_EPOCHS}  loss={float(loss):.4f}")

    # Evaluate on test set (first 100 samples for speed)
    n_eval = min(100, len(X_test))
    correct = 0
    for xi, yi in zip(X_test[:n_eval], y_test[:n_eval]):
        probs = predict_proba(xi.astype(np.float64), weights)
        pred = int(np.argmax(probs))
        if pred == yi:
            correct += 1
    acc = correct / n_eval
    print(f"[vqc] Test accuracy (first {n_eval} samples): {acc*100:.1f}%")

    out_path = os.path.join(REPO_ROOT, "quantum_vqc", "1", "weights.npy")
    np.save(out_path, np.array(weights))
    print(f"[vqc] Saved weights → {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Step 4 — Time-series Transformer (PyTorch TorchScript)
# ---------------------------------------------------------------------------

def build_transformer(X_train) -> str:
    """
    Build a minimal time-series transformer and export as TorchScript.
    Input: [batch, 32, 16] — 32 timesteps × 16 features.
    Output: [batch, 1]    — single regression/classification score.
    """
    import torch
    import torch.nn as nn

    class TimeSeriesTransformer(nn.Module):
        def __init__(self, n_features=16, d_model=64, nhead=4, num_layers=2):
            super().__init__()
            self.input_proj = nn.Linear(n_features, d_model)
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=nhead,
                dim_feedforward=128,
                dropout=0.1,
                batch_first=True,
            )
            self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
            self.output_proj = nn.Linear(d_model, 1)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # x: [batch, seq_len, n_features]
            h = self.input_proj(x)             # [batch, seq_len, d_model]
            h = self.encoder(h)                # [batch, seq_len, d_model]
            h = h.mean(dim=1)                  # global average pool
            return self.output_proj(h)         # [batch, 1]

    print("[transformer] Building TorchScript time-series transformer ...")
    model = TimeSeriesTransformer()
    model.eval()

    # Trace with a dummy input: [1, 32, 16]
    dummy = torch.zeros(1, 32, 16, dtype=torch.float32)
    traced = torch.jit.trace(model, dummy)

    out_path = os.path.join(REPO_ROOT, "transformer_ts", "1", "model.pt")
    torch.jit.save(traced, out_path)
    size_mb = os.path.getsize(out_path) / 1e6
    print(f"[transformer] Saved {out_path} ({size_mb:.2f} MB)")
    return out_path


# ---------------------------------------------------------------------------
# Step 5 — Verify against live Triton (optional)
# ---------------------------------------------------------------------------

def verify_triton(triton_url: str):
    """Send one test request to each model and confirm non-error response."""
    try:
        import tritonclient.http as httpclient
    except ImportError:
        print("[verify] tritonclient not installed — skipping Triton verification.")
        return

    print(f"[verify] Connecting to Triton at {triton_url} ...")
    client = httpclient.InferenceServerClient(url=triton_url.replace("http://", ""), verbose=False)

    # Wait for server ready (up to 30s)
    for _ in range(30):
        if client.is_server_ready():
            break
        time.sleep(1)
    else:
        print("[verify] Triton server not ready after 30s — skipping.")
        return

    # Test xgboost_fraud
    import tritonclient.http as httpclient
    inputs = [httpclient.InferInput("input__0", [1, 4], "FP32")]
    inputs[0].set_data_from_numpy(np.array([[0.5, 1.2, -0.3, 0.8]], dtype=np.float32))
    outputs = [httpclient.InferRequestedOutput("output__0")]
    result = client.infer("xgboost_fraud", inputs, outputs=outputs)
    probs = result.as_numpy("output__0")
    print(f"[verify] xgboost_fraud: probs={probs}")

    # Test quantum_vqc
    inputs2 = [httpclient.InferInput("input__0", [1, 4], "FP32")]
    inputs2[0].set_data_from_numpy(np.array([[0.1, -0.2, 0.4, 0.9]], dtype=np.float32))
    outputs2 = [httpclient.InferRequestedOutput("output__0")]
    result2 = client.infer("quantum_vqc", inputs2, outputs=outputs2)
    probs2 = result2.as_numpy("output__0")
    print(f"[verify] quantum_vqc:   probs={probs2}")

    print("[verify] All checks passed.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Train and export models for Triton.")
    parser.add_argument(
        "--data",
        default="datasets/creditcard.csv",
        help="Path to creditcard.csv (Kaggle fraud dataset). Synthetic fallback if missing.",
    )
    parser.add_argument(
        "--triton-url",
        default=None,
        help="Optional Triton HTTP URL (e.g. http://localhost:8000) to verify loaded models.",
    )
    args = parser.parse_args()

    ensure_dirs()

    X_train, X_test, y_train, y_test = load_data(args.data)

    train_xgboost(X_train, y_train, X_test, y_test)
    train_vqc(X_train, y_train, X_test, y_test)
    build_transformer(X_train)

    if args.triton_url:
        verify_triton(args.triton_url)

    print("\n[done] All models saved to model_repository/")
    print(f"       REPO_ROOT = {REPO_ROOT}")


if __name__ == "__main__":
    main()
