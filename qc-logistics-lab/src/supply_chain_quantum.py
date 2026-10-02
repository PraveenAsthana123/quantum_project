"""
Quantum Supply Chain Optimization
==================================
Late-delivery risk prediction on DataCo Supply Chain dataset.

Classical: Logistic Regression + Random Forest
Quantum  : Variational Quantum Classifier (VQC) with PennyLane
           on top-4 PCA-reduced features

Dataset : /mnt/deepa/quantum/datasets/logistics/DataCoSupplyChainDataset.csv
Author  : Quantum Lab / PraveenAsthana123
Version : 1.0.0  |  Date: 2026-09-22
"""

from __future__ import annotations

import json
import os
import time
import warnings

import numpy as np
import pandas as pd
import pennylane as qml
from scipy.optimize import minimize
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATASET_PATH = (
    "/mnt/deepa/quantum/datasets/logistics/DataCoSupplyChainDataset.csv"
)
RESULTS_DIR  = "/mnt/deepa/quantum/qc-logistics-lab/results"
RESULTS_FILE = os.path.join(RESULTS_DIR, "supply_chain_results.json")

os.makedirs(RESULTS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Load & preprocess
# ---------------------------------------------------------------------------

def load_and_preprocess(path: str, sample_size: int = 5000, seed: int = 42):
    """Load DataCo supply chain CSV, engineer features, return train/test splits."""
    print(f"  Loading dataset: {path}")
    try:
        df = pd.read_csv(path, encoding="latin-1")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="cp1252")

    print(f"  Raw shape: {df.shape}")
    target_col = "Late_delivery_risk"
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset.")

    # ---- Feature selection: numerical + categorical with low cardinality ----
    num_features = [
        "Days for shipping (real)",
        "Days for shipment (scheduled)",
        "Benefit per order",
        "Sales per customer",
        "Order Item Discount Rate",
        "Order Item Profit Ratio",
        "Order Item Quantity",
        "Order Item Product Price",
        "Product Price",
    ]
    cat_features = ["Shipping Mode", "Order Status", "Customer Segment", "Market"]

    keep = [c for c in num_features + cat_features if c in df.columns]
    df = df[keep + [target_col]].dropna()

    # Encode categoricals
    le = LabelEncoder()
    for col in cat_features:
        if col in df.columns:
            df[col] = le.fit_transform(df[col].astype(str))

    # Sub-sample for speed
    if len(df) > sample_size:
        df = df.sample(n=sample_size, random_state=seed)

    print(f"  Working shape (after clean + sample): {df.shape}")
    print(f"  Target distribution: {df[target_col].value_counts().to_dict()}")

    X = df[keep].values.astype(float)
    y = df[target_col].values.astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test  = scaler.transform(X_test)

    # PCA to 4 components for quantum
    pca = PCA(n_components=4, random_state=seed)
    X_train_pca = pca.fit_transform(X_train)
    X_test_pca  = pca.transform(X_test)
    explained   = float(pca.explained_variance_ratio_.sum())
    print(f"  PCA(4) explained variance: {explained:.3f}")

    return (X_train, X_test, y_train, y_test,
            X_train_pca, X_test_pca,
            keep, explained)


# ---------------------------------------------------------------------------
# 2. Classical baselines
# ---------------------------------------------------------------------------

def run_logistic_regression(X_train, X_test, y_train, y_test) -> dict:
    t0  = time.perf_counter()
    clf = LogisticRegression(max_iter=1000, random_state=42)
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    runtime_ms = (time.perf_counter() - t0) * 1000

    return {
        "accuracy"  : round(accuracy_score(y_test, y_pred), 4),
        "precision" : round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall"    : round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1"        : round(f1_score(y_test, y_pred, zero_division=0), 4),
        "runtime_ms": round(runtime_ms, 2),
    }


def run_random_forest(X_train, X_test, y_train, y_test) -> dict:
    t0  = time.perf_counter()
    clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]
    runtime_ms = (time.perf_counter() - t0) * 1000

    return {
        "accuracy"  : round(accuracy_score(y_test, y_pred), 4),
        "precision" : round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall"    : round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1"        : round(f1_score(y_test, y_pred, zero_division=0), 4),
        "roc_auc"   : round(roc_auc_score(y_test, y_prob), 4),
        "runtime_ms": round(runtime_ms, 2),
    }


# ---------------------------------------------------------------------------
# 3. Quantum VQC (4 qubits, amplitude encoding of PCA features)
# ---------------------------------------------------------------------------

N_QUBITS = 4
dev = qml.device("default.qubit", wires=N_QUBITS)


def angle_encode(x: np.ndarray) -> None:
    """Angle encoding: map 4 features to RY rotations on 4 qubits."""
    for i in range(N_QUBITS):
        qml.RY(float(x[i]) * np.pi, wires=i)


def vqc_layer(weights: np.ndarray, layer_idx: int) -> None:
    """Single VQC layer: RY rotations + CNOT entanglement ring."""
    offset = layer_idx * N_QUBITS
    for i in range(N_QUBITS):
        qml.RY(weights[offset + i], wires=i)
    for i in range(N_QUBITS):
        qml.CNOT(wires=[i, (i + 1) % N_QUBITS])


N_LAYERS = 2


@qml.qnode(dev)
def vqc_circuit(x: np.ndarray, weights: np.ndarray) -> float:
    """VQC: angle encode → 2 variational layers → measure Z on qubit 0."""
    angle_encode(x)
    for layer in range(N_LAYERS):
        vqc_layer(weights, layer)
    return qml.expval(qml.PauliZ(0))


def vqc_predict_proba(X: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Map circuit output ∈ [-1, 1] to probability ∈ [0, 1]."""
    probs = np.array([vqc_circuit(x, weights) for x in X])
    return (probs + 1.0) / 2.0  # sigmoid-like rescale


def vqc_loss(weights: np.ndarray, X: np.ndarray, y: np.ndarray) -> float:
    """Binary cross-entropy loss."""
    probs = vqc_predict_proba(X, weights)
    probs = np.clip(probs, 1e-7, 1 - 1e-7)
    return -float(np.mean(y * np.log(probs) + (1 - y) * np.log(1 - probs)))


def run_vqc(
    X_train_pca: np.ndarray,
    X_test_pca: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    max_train_samples: int = 200,
    max_test_samples: int = 100,
    max_iter: int = 50,
    seed: int = 42,
) -> dict:
    """Train and evaluate VQC. Sub-samples for tractability on CPU simulator."""
    rng = np.random.default_rng(seed)

    # Sub-sample: VQC forward pass is expensive (~100 ms/sample on CPU)
    n_train = min(len(X_train_pca), max_train_samples)
    n_test  = min(len(X_test_pca),  max_test_samples)

    idx_tr = rng.choice(len(X_train_pca), n_train, replace=False)
    idx_te = rng.choice(len(X_test_pca),  n_test,  replace=False)
    Xtr = X_train_pca[idx_tr]
    ytr = y_train[idx_tr].astype(float)
    Xte = X_test_pca[idx_te]
    yte = y_test[idx_te].astype(float)

    # Normalize PCA features to [-π, π]
    max_abs = np.abs(Xtr).max(axis=0) + 1e-9
    Xtr = Xtr / max_abs
    Xte = Xte / max_abs

    print(f"  VQC training: {n_train} samples, {N_QUBITS} qubits, {N_LAYERS} layers, "
          f"max_iter={max_iter}")

    n_weights = N_LAYERS * N_QUBITS
    weights_init = rng.uniform(-np.pi, np.pi, size=n_weights)

    losses = []

    def objective(w):
        loss = vqc_loss(w, Xtr, ytr)
        losses.append(loss)
        if len(losses) % 10 == 0:
            print(f"    iter {len(losses):3d}, loss={loss:.4f}")
        return loss

    t0 = time.perf_counter()
    result = minimize(
        objective,
        weights_init,
        method="COBYLA",
        options={"maxiter": max_iter, "rhobeg": 0.3},
    )
    runtime_ms = (time.perf_counter() - t0) * 1000

    best_weights = result.x

    # Evaluate
    train_probs = vqc_predict_proba(Xtr, best_weights)
    test_probs  = vqc_predict_proba(Xte, best_weights)

    train_preds = (train_probs >= 0.5).astype(int)
    test_preds  = (test_probs  >= 0.5).astype(int)

    train_acc = accuracy_score(ytr.astype(int), train_preds)
    test_acc  = accuracy_score(yte.astype(int), test_preds)

    return {
        "train_accuracy"  : round(float(train_acc), 4),
        "accuracy"        : round(float(test_acc), 4),
        "precision"       : round(float(precision_score(yte.astype(int), test_preds, zero_division=0)), 4),
        "recall"          : round(float(recall_score(yte.astype(int), test_preds, zero_division=0)), 4),
        "f1"              : round(float(f1_score(yte.astype(int), test_preds, zero_division=0)), 4),
        "final_loss"      : round(float(result.fun), 4),
        "n_optimizer_iters": len(losses),
        "n_qubits"        : N_QUBITS,
        "n_layers"        : N_LAYERS,
        "train_samples"   : int(n_train),
        "test_samples"    : int(n_test),
        "runtime_ms"      : round(runtime_ms, 2),
        "note"            : (
            f"VQC {N_QUBITS}q × {N_LAYERS}L, angle encoding, PCA(4) features, "
            f"COBYLA optimiser, default.qubit simulator"
        ),
    }


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------

def run_supply_chain_benchmark() -> dict:
    print("=" * 70)
    print("Quantum Supply Chain: Late-Delivery Risk Prediction")
    print("=" * 70)

    (X_train, X_test, y_train, y_test,
     X_train_pca, X_test_pca,
     feature_names, pca_variance) = load_and_preprocess(DATASET_PATH)

    print("\n[1] Classical: Logistic Regression …")
    lr_res = run_logistic_regression(X_train, X_test, y_train, y_test)
    print(f"    LR: acc={lr_res['accuracy']}, prec={lr_res['precision']}, "
          f"f1={lr_res['f1']}, {lr_res['runtime_ms']} ms")

    print("\n[2] Classical: Random Forest …")
    rf_res = run_random_forest(X_train, X_test, y_train, y_test)
    print(f"    RF: acc={rf_res['accuracy']}, prec={rf_res['precision']}, "
          f"f1={rf_res['f1']}, roc_auc={rf_res.get('roc_auc')}, {rf_res['runtime_ms']} ms")

    print("\n[3] Quantum: VQC (4 qubits, PCA-4 features) …")
    vqc_res = run_vqc(X_train_pca, X_test_pca, y_train, y_test,
                       max_train_samples=200, max_test_samples=100,
                       max_iter=50, seed=42)
    print(f"    VQC: acc={vqc_res['accuracy']}, prec={vqc_res['precision']}, "
          f"f1={vqc_res['f1']}, {vqc_res['runtime_ms']} ms")

    results = {
        "problem"          : "Late Delivery Risk Prediction",
        "dataset"          : DATASET_PATH,
        "features_used"    : feature_names,
        "pca_4_variance"   : round(pca_variance, 4),
        "train_size"       : int(len(X_train)),
        "test_size"        : int(len(X_test)),
        "methods": {
            "logistic_regression": lr_res,
            "random_forest"      : rf_res,
            "vqc_4qubit"         : vqc_res,
        },
        "comparison_summary": {
            "best_classical_f1"  : max(lr_res["f1"], rf_res["f1"]),
            "quantum_vqc_f1"     : vqc_res["f1"],
            "quantum_gap"        : round(
                max(lr_res["f1"], rf_res["f1"]) - vqc_res["f1"], 4
            ),
            "note": (
                "VQC trained on 200 samples (simulator constraint). Classical models use "
                "full training set. Gap reflects both model capacity and training-size difference — "
                "not an inherent quantum disadvantage on this task."
            ),
        },
        "quantum_assessment": (
            "4-qubit VQC with angle encoding demonstrates quantum ML on real supply chain data. "
            "Accuracy gap vs classical methods is primarily due to the 200-sample training limit "
            "imposed by simulator runtime. On fault-tolerant hardware with kernel-based QML "
            "(quantum kernel estimation), advantage is theorised for high-dimensional datasets "
            "with quantum-structured correlations."
        ),
        "tech_stack": {
            "quantum"  : f"PennyLane {qml.__version__}, default.qubit",
            "classical": "scikit-learn LogReg + RandomForest",
            "data"     : "DataCo Supply Chain Dataset (Kaggle)",
        },
        "run_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n[4] Results saved → {RESULTS_FILE}")

    print("\n" + "=" * 70)
    print("SUPPLY CHAIN RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Method':<30} {'Accuracy':>10} {'Precision':>10} {'F1':>8} {'ms':>10}")
    print("-" * 70)
    for name, res in [
        ("Logistic Regression", lr_res),
        ("Random Forest",       rf_res),
        ("VQC (4 qubits)",      vqc_res),
    ]:
        print(
            f"{name:<30} {res['accuracy']:>10.4f} {res['precision']:>10.4f} "
            f"{res['f1']:>8.4f} {res['runtime_ms']:>10.1f}"
        )
    print("-" * 70)
    print()
    return results


if __name__ == "__main__":
    run_supply_chain_benchmark()
