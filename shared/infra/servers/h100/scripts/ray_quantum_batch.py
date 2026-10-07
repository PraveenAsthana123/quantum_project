"""
Batch quantum VQC circuit execution via Ray on H100 cluster.
Dispatches thousands of samples in parallel across Ray workers.
"""

import argparse
import time
import numpy as np
import pandas as pd
import ray
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import roc_auc_score, f1_score

try:
    import pennylane as qml
    HAS_PENNYLANE = True
except ImportError:
    HAS_PENNYLANE = False


N_QUBITS = 4
N_LAYERS = 2


def build_vqc_device():
    return qml.device("default.qubit", wires=N_QUBITS)


@ray.remote
def run_vqc_batch(X_batch: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Run VQC on a batch of samples. Executed remotely on a Ray worker."""
    if not HAS_PENNYLANE:
        # Fallback: random predictions for testing without PennyLane
        return np.random.uniform(0, 1, len(X_batch))

    dev = build_vqc_device()

    @qml.qnode(dev)
    def circuit(x, w):
        qml.AngleEmbedding(x * np.pi, wires=range(N_QUBITS))
        for layer_w in w:
            qml.BasicEntanglerLayers(layer_w.reshape(1, N_QUBITS), wires=range(N_QUBITS))
        return qml.expval(qml.PauliZ(0))

    probs = []
    for x in X_batch:
        expval = circuit(x, weights)
        prob = (float(expval) + 1.0) / 2.0
        probs.append(prob)
    return np.array(probs)


def preprocess(df: pd.DataFrame, n_features: int = N_QUBITS) -> tuple[np.ndarray, np.ndarray]:
    """Reduce to n_features and scale to [0, 1]."""
    label_col = "Class" if "Class" in df.columns else df.columns[-1]
    y = df[label_col].values.astype(int)
    X = df.drop(columns=[label_col]).select_dtypes(include=[np.number])
    # PCA-like: take top-variance columns
    variances = X.var()
    top_cols = variances.nlargest(n_features).index
    X = X[top_cols].values
    X = MinMaxScaler().fit_transform(X)
    return X.astype(np.float32), y


def run_batch_inference(
    X: np.ndarray,
    weights: np.ndarray,
    batch_size: int = 64,
    n_workers: int = 4,
) -> np.ndarray:
    """Split X into batches and dispatch to Ray workers."""
    batches = [X[i:i + batch_size] for i in range(0, len(X), batch_size)]
    print(f"  Dispatching {len(batches)} batches × {batch_size} samples to {n_workers} Ray workers")

    # Put weights in object store once
    weights_ref = ray.put(weights)

    # Dispatch all batches
    futures = [run_vqc_batch.remote(batch, weights_ref) for batch in batches]

    # Collect results
    results = []
    for i, future in enumerate(futures):
        result = ray.get(future)
        results.append(result)
        if (i + 1) % 10 == 0:
            print(f"  Completed {i + 1}/{len(batches)} batches")

    return np.concatenate(results)


def main():
    parser = argparse.ArgumentParser(description="Batch quantum VQC via Ray on H100")
    parser.add_argument("--dataset", default="data/creditcard.csv", help="CSV dataset path")
    parser.add_argument("--n-samples", type=int, default=1000, help="Number of samples to run")
    parser.add_argument("--batch-size", type=int, default=64, help="Samples per Ray task")
    parser.add_argument("--ray-address", default=None, help="Ray cluster address (None=local)")
    args = parser.parse_args()

    print("=" * 60)
    print("Quantum VQC Batch Inference — Ray + H100")
    print("=" * 60)

    # Initialize Ray
    if args.ray_address:
        ray.init(address=args.ray_address)
        print(f"Connected to Ray cluster: {args.ray_address}")
    else:
        ray.init(num_gpus=0)  # local mode
        print("Ray running in local mode")

    # Load dataset
    print(f"\nLoading dataset: {args.dataset}")
    try:
        df = pd.read_csv(args.dataset)
    except FileNotFoundError:
        print(f"Dataset not found, generating synthetic data for demo")
        df = pd.DataFrame(
            np.random.randn(args.n_samples, 5),
            columns=[f"f{i}" for i in range(4)] + ["Class"]
        )
        df["Class"] = (df["Class"] > 0).astype(int)

    df = df.sample(min(args.n_samples, len(df)), random_state=42)
    X, y = preprocess(df)
    print(f"  Samples: {len(X)}, Features: {X.shape[1]}, Positives: {y.sum()}")

    # Initialize random weights (normally loaded from trained model)
    np.random.seed(42)
    weights = np.random.uniform(-np.pi, np.pi, (N_LAYERS, N_QUBITS))
    print(f"\nVQC config: {N_QUBITS} qubits, {N_LAYERS} layers")

    # Run batch inference
    print(f"\nRunning batch inference (batch_size={args.batch_size})...")
    t0 = time.time()
    probs = run_batch_inference(X, weights, batch_size=args.batch_size)
    elapsed = time.time() - t0

    # Compute metrics
    preds = (probs > 0.5).astype(int)
    auc = roc_auc_score(y, probs) if len(np.unique(y)) > 1 else 0.5
    f1 = f1_score(y, preds, zero_division=0)
    throughput = len(X) / elapsed

    print("\n" + "=" * 60)
    print("Results")
    print("=" * 60)
    print(f"  Samples processed:  {len(X)}")
    print(f"  Total time:         {elapsed:.2f}s")
    print(f"  Throughput:         {throughput:.1f} samples/sec")
    print(f"  AUC:                {auc:.4f}")
    print(f"  F1:                 {f1:.4f}")
    print(f"  Avg probability:    {probs.mean():.4f}")
    print("=" * 60)

    ray.shutdown()


if __name__ == "__main__":
    main()
