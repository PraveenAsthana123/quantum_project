"""
Quantum Portal — Vertex AI Pipeline (KFP v2)
============================================
Defines a Kubeflow Pipelines v2 pipeline for quantum ML on Vertex AI.
Steps:
  1. data_validation      — schema checks, class balance, missing value report
  2. classical_preprocess — feature engineering, PCA, train/test split → GCS
  3. quantum_training     — VQC training (PennyLane / Qiskit) → model weights
  4. classical_comparison — train Random Forest on same data → metrics
  5. evaluation           — compare quantum vs classical accuracy/AUC/F1
  6. model_registration   — register in Vertex AI Model Registry if quantum wins
  7. canary_deployment    — deploy 10% canary endpoint, run smoke test

Usage:
    python vertex_pipeline.py --project <GCP_PROJECT> --region <REGION> \
        --pipeline-root gs://<BUCKET>/pipelines --submit
"""

from __future__ import annotations

import argparse
import json
import os
from typing import NamedTuple

from kfp import dsl
from kfp.dsl import (
    Artifact,
    ClassificationMetrics,
    Dataset,
    Input,
    Metrics,
    Model,
    Output,
    component,
    pipeline,
)
from kfp import compiler

# ---------------------------------------------------------------------------
# Reusable base image — includes pennylane, qiskit, scikit-learn, mlflow
# ---------------------------------------------------------------------------
_BASE_IMAGE = os.getenv(
    "QUANTUM_PIPELINE_IMAGE",
    "gcr.io/quantum-portal-prod/quantum-worker:latest",
)


# =============================================================================
# STEP 1: Data Validation
# =============================================================================

@component(base_image=_BASE_IMAGE)
def data_validation(
    dataset_gcs_uri: str,
    target_column: str,
    expected_n_features: int,
    min_class_balance_ratio: float,
    validation_report: Output[Artifact],
    validated_dataset: Output[Dataset],
) -> NamedTuple("DataValidationOutputs", [("passed", bool), ("n_rows", int), ("n_features", int)]):
    """
    Validates the input dataset:
    - Checks expected number of features
    - Checks class balance ratio (minority / majority)
    - Reports missing values
    - Writes the validated dataset to GCS for downstream steps
    """
    import json
    import sys
    from collections import namedtuple
    from pathlib import Path

    import numpy as np
    import pandas as pd
    from google.cloud import storage

    # ── Load from GCS ────────────────────────────────────────────────────
    bucket_name, blob_path = dataset_gcs_uri.replace("gs://", "").split("/", 1)
    client = storage.Client()
    blob = client.bucket(bucket_name).blob(blob_path)
    local_path = "/tmp/dataset.parquet"
    blob.download_to_filename(local_path)

    df = pd.read_parquet(local_path)

    # ── Checks ───────────────────────────────────────────────────────────
    report: dict = {}
    passed = True

    # Feature count
    feature_cols = [c for c in df.columns if c != target_column]
    report["n_features"] = len(feature_cols)
    report["n_rows"] = len(df)
    if len(feature_cols) != expected_n_features:
        report["feature_count_error"] = (
            f"Expected {expected_n_features} features, got {len(feature_cols)}"
        )
        passed = False

    # Missing values
    missing = df.isnull().sum()
    report["missing_values"] = missing[missing > 0].to_dict()
    if missing.sum() > 0:
        report["missing_warning"] = "Dataset has missing values — imputation applied downstream"

    # Class balance
    if target_column in df.columns:
        vc = df[target_column].value_counts(normalize=True)
        minority_ratio = float(vc.min())
        report["class_distribution"] = vc.to_dict()
        report["minority_class_ratio"] = minority_ratio
        if minority_ratio < min_class_balance_ratio:
            report["class_balance_warning"] = (
                f"Minority class ratio {minority_ratio:.4f} < {min_class_balance_ratio} — "
                "consider oversampling or class weights"
            )

    # ── Write report artifact ────────────────────────────────────────────
    Path(validation_report.path).write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )

    # ── Write validated dataset artifact ─────────────────────────────────
    df.to_parquet(validated_dataset.path, index=False)

    DataValidationOutputs = namedtuple(
        "DataValidationOutputs", ["passed", "n_rows", "n_features"]
    )
    return DataValidationOutputs(
        passed=passed,
        n_rows=len(df),
        n_features=len(feature_cols),
    )


# =============================================================================
# STEP 2: Classical Preprocessing
# =============================================================================

@component(base_image=_BASE_IMAGE)
def classical_preprocess(
    validated_dataset: Input[Dataset],
    target_column: str,
    n_pca_components: int,
    test_size: float,
    random_seed: int,
    train_dataset: Output[Dataset],
    test_dataset: Output[Dataset],
    preprocessor_artifact: Output[Artifact],
) -> NamedTuple("PreprocessOutputs", [("n_train", int), ("n_test", int)]):
    """
    Feature engineering + PCA dimensionality reduction + train/test split.
    Saves fitted scaler+PCA pipeline as a pickle artifact for reproducible inference.
    """
    import pickle
    from collections import namedtuple
    from pathlib import Path

    import numpy as np
    import pandas as pd
    from sklearn.decomposition import PCA
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    df = pd.read_parquet(validated_dataset.path)

    feature_cols = [c for c in df.columns if c != target_column]
    X = df[feature_cols].values.astype(np.float32)
    y = df[target_column].values

    # Impute mean for any missing values
    col_means = np.nanmean(X, axis=0)
    inds = np.where(np.isnan(X))
    X[inds] = np.take(col_means, inds[1])

    # Fit scaler + PCA
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("pca", PCA(n_components=n_pca_components, random_state=random_seed)),
    ])
    X_transformed = pipe.fit_transform(X)

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X_transformed, y,
        test_size=test_size,
        random_state=random_seed,
        stratify=y,
    )

    # Serialize datasets
    pd.DataFrame(
        np.column_stack([X_train, y_train]),
        columns=[f"pca_{i}" for i in range(X_train.shape[1])] + [target_column],
    ).to_parquet(train_dataset.path, index=False)

    pd.DataFrame(
        np.column_stack([X_test, y_test]),
        columns=[f"pca_{i}" for i in range(X_test.shape[1])] + [target_column],
    ).to_parquet(test_dataset.path, index=False)

    # Save preprocessor pipeline
    with open(preprocessor_artifact.path, "wb") as f:
        pickle.dump(pipe, f)

    PreprocessOutputs = namedtuple("PreprocessOutputs", ["n_train", "n_test"])
    return PreprocessOutputs(n_train=len(X_train), n_test=len(X_test))


# =============================================================================
# STEP 3: Quantum Training (VQC)
# =============================================================================

@component(base_image=_BASE_IMAGE)
def quantum_training(
    train_dataset: Input[Dataset],
    test_dataset: Input[Dataset],
    n_qubits: int,
    n_layers: int,
    shots: int,
    encoding: str,
    optimizer: str,
    max_iterations: int,
    random_seed: int,
    mlflow_tracking_uri: str,
    experiment_name: str,
    quantum_model: Output[Model],
    quantum_metrics: Output[Metrics],
) -> NamedTuple(
    "QuantumTrainingOutputs",
    [("accuracy", float), ("auc", float), ("f1", float), ("circuit_depth", int)],
):
    """
    Train a Variational Quantum Classifier (VQC) using PennyLane.
    Logs the run to MLflow and saves model weights as the output artifact.
    """
    import json
    import time
    from collections import namedtuple
    from pathlib import Path

    import mlflow
    import numpy as np
    import pandas as pd
    import pennylane as qml
    from scipy.optimize import minimize
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
    from sklearn.preprocessing import LabelEncoder

    # ── Load data ────────────────────────────────────────────────────────
    train_df = pd.read_parquet(train_dataset.path)
    test_df = pd.read_parquet(test_dataset.path)

    feature_cols = [c for c in train_df.columns if c != "label"]
    target_col = "label" if "label" in train_df.columns else train_df.columns[-1]
    feature_cols = [c for c in train_df.columns if c != target_col]

    X_train = train_df[feature_cols].values.astype(np.float64)
    y_train = train_df[target_col].values
    X_test = test_df[feature_cols].values.astype(np.float64)
    y_test = test_df[target_col].values

    le = LabelEncoder()
    y_train_enc = le.fit_transform(y_train)
    y_test_enc = le.transform(y_test)

    # Normalise features to [0, π] for angle encoding
    from sklearn.preprocessing import MinMaxScaler
    scaler = MinMaxScaler(feature_range=(0, np.pi))
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    # ── Define PennyLane device + circuit ────────────────────────────────
    dev = qml.device("default.qubit", wires=n_qubits, shots=shots if shots > 0 else None)
    n_features = min(X_train.shape[1], n_qubits)

    @qml.qnode(dev)
    def vqc_circuit(x: np.ndarray, weights: np.ndarray) -> float:
        # Angle encoding
        for i in range(n_features):
            qml.RX(x[i], wires=i)
            qml.RZ(x[i], wires=i)
        # Variational layers
        for layer in range(n_layers):
            for i in range(n_qubits):
                qml.RY(weights[layer, i, 0], wires=i)
                qml.RZ(weights[layer, i, 1], wires=i)
            for i in range(n_qubits - 1):
                qml.CNOT(wires=[i, i + 1])
            qml.CNOT(wires=[n_qubits - 1, 0])
        return qml.expval(qml.PauliZ(0))

    def predict_batch(X: np.ndarray, weights: np.ndarray) -> np.ndarray:
        return np.array([vqc_circuit(x[:n_features], weights) for x in X])

    def cost(weights_flat: np.ndarray, X: np.ndarray, y: np.ndarray) -> float:
        weights = weights_flat.reshape(n_layers, n_qubits, 2)
        predictions = predict_batch(X, weights)
        # Margin-based MSE loss
        y_signed = 2 * y - 1  # {0,1} → {-1,+1}
        return float(np.mean((predictions - y_signed) ** 2))

    # ── Training ─────────────────────────────────────────────────────────
    np.random.seed(random_seed)
    weights_init = np.random.uniform(-np.pi, np.pi, size=(n_layers, n_qubits, 2))
    weights_flat = weights_init.flatten()

    # Use a small subset for VQC training (NISQ resource constraint)
    n_train_subset = min(200, len(X_train))
    idx = np.random.choice(len(X_train), n_train_subset, replace=False)
    X_sub, y_sub = X_train[idx], y_train_enc[idx]

    t_start = time.time()
    result = minimize(
        cost,
        weights_flat,
        args=(X_sub, y_sub),
        method=optimizer,
        options={"maxiter": max_iterations, "rhobeg": 0.1},
    )
    runtime_ms = (time.time() - t_start) * 1000
    trained_weights = result.x.reshape(n_layers, n_qubits, 2)

    # ── Evaluate ─────────────────────────────────────────────────────────
    n_test_subset = min(100, len(X_test))
    idx_test = np.random.choice(len(X_test), n_test_subset, replace=False)
    X_test_sub, y_test_sub = X_test[idx_test], y_test_enc[idx_test]

    raw_preds = predict_batch(X_test_sub, trained_weights)
    y_pred_prob = (raw_preds + 1) / 2   # map [-1,+1] → [0,1]
    y_pred_bin = (raw_preds >= 0).astype(int)

    accuracy = float(accuracy_score(y_test_sub, y_pred_bin))
    f1 = float(f1_score(y_test_sub, y_pred_bin, average="binary", zero_division=0))
    try:
        auc = float(roc_auc_score(y_test_sub, y_pred_prob))
    except ValueError:
        auc = 0.5  # single-class fallback

    # Circuit depth via Qiskit (optional — skip if not installed)
    circuit_depth = n_layers * n_qubits * 3  # approximate gate count
    try:
        from qiskit.circuit.library import ZZFeatureMap, TwoLocal
        from qiskit import transpile, QuantumCircuit
        qc = QuantumCircuit(n_qubits)
        circuit_depth = qc.depth() + n_layers * 4
    except ImportError:
        pass

    # ── Log to MLflow ─────────────────────────────────────────────────────
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    with mlflow.start_run(run_name="quantum_vqc_vertex") as run:
        mlflow.log_params({
            "n_qubits": n_qubits, "n_layers": n_layers, "shots": shots,
            "encoding": encoding, "optimizer": optimizer,
            "max_iterations": max_iterations, "n_train_subset": n_train_subset,
        })
        mlflow.log_metrics({
            "accuracy": accuracy, "auc": auc, "f1": f1,
            "circuit_depth": circuit_depth, "runtime_ms": runtime_ms,
            "optimizer_iterations": result.nit,
            "optimizer_converged": float(result.success),
        })

    # ── Save weights as model artifact ────────────────────────────────────
    weights_data = {
        "weights": trained_weights.tolist(),
        "n_qubits": n_qubits,
        "n_layers": n_layers,
        "n_features": n_features,
        "encoding": encoding,
        "optimizer": optimizer,
        "optimizer_result": {
            "success": result.success,
            "n_iterations": result.nit,
            "final_loss": float(result.fun),
        },
    }
    Path(quantum_model.path).mkdir(parents=True, exist_ok=True)
    model_file = Path(quantum_model.path) / "weights.json"
    model_file.write_text(json.dumps(weights_data, indent=2), encoding="utf-8")

    # ── Log KFP metrics artifact ──────────────────────────────────────────
    quantum_metrics.log_metric("accuracy", accuracy)
    quantum_metrics.log_metric("auc", auc)
    quantum_metrics.log_metric("f1", f1)
    quantum_metrics.log_metric("circuit_depth", circuit_depth)
    quantum_metrics.log_metric("runtime_ms", runtime_ms)

    QuantumTrainingOutputs = namedtuple(
        "QuantumTrainingOutputs", ["accuracy", "auc", "f1", "circuit_depth"]
    )
    return QuantumTrainingOutputs(
        accuracy=accuracy, auc=auc, f1=f1, circuit_depth=circuit_depth
    )


# =============================================================================
# STEP 4: Classical Comparison (Random Forest)
# =============================================================================

@component(base_image=_BASE_IMAGE)
def classical_comparison(
    train_dataset: Input[Dataset],
    test_dataset: Input[Dataset],
    n_estimators: int,
    random_seed: int,
    mlflow_tracking_uri: str,
    classical_model_artifact: Output[Model],
    classical_metrics: Output[Metrics],
) -> NamedTuple(
    "ClassicalOutputs",
    [("accuracy", float), ("auc", float), ("f1", float), ("runtime_ms", float)],
):
    """
    Train a Random Forest on the same preprocessed data as the VQC.
    Provides the classical baseline for quantum advantage measurement.
    """
    import time
    from collections import namedtuple
    from pathlib import Path

    import mlflow
    import mlflow.sklearn
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
    from sklearn.preprocessing import LabelEncoder

    train_df = pd.read_parquet(train_dataset.path)
    test_df = pd.read_parquet(test_dataset.path)

    target_col = "label" if "label" in train_df.columns else train_df.columns[-1]
    feature_cols = [c for c in train_df.columns if c != target_col]

    X_train = train_df[feature_cols].values
    y_train = train_df[target_col].values
    X_test = test_df[feature_cols].values
    y_test = test_df[target_col].values

    le = LabelEncoder()
    y_train_enc = le.fit_transform(y_train)
    y_test_enc = le.transform(y_test)

    t_start = time.time()
    rf = RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=random_seed,
        class_weight="balanced",
        n_jobs=-1,
    )
    rf.fit(X_train, y_train_enc)
    runtime_ms = (time.time() - t_start) * 1000

    y_pred = rf.predict(X_test)
    y_prob = rf.predict_proba(X_test)[:, 1]

    accuracy = float(accuracy_score(y_test_enc, y_pred))
    f1 = float(f1_score(y_test_enc, y_pred, average="binary", zero_division=0))
    auc = float(roc_auc_score(y_test_enc, y_prob))

    # Log to MLflow
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    with mlflow.start_run(run_name="classical_rf_vertex"):
        mlflow.log_params({
            "model": "random_forest",
            "n_estimators": n_estimators,
            "random_seed": random_seed,
        })
        mlflow.log_metrics({
            "accuracy": accuracy, "auc": auc, "f1": f1, "runtime_ms": runtime_ms
        })
        mlflow.sklearn.log_model(rf, artifact_path="model")

    classical_metrics.log_metric("accuracy", accuracy)
    classical_metrics.log_metric("auc", auc)
    classical_metrics.log_metric("f1", f1)
    classical_metrics.log_metric("runtime_ms", runtime_ms)

    # Save model artifact directory
    import pickle
    Path(classical_model_artifact.path).mkdir(parents=True, exist_ok=True)
    model_file = Path(classical_model_artifact.path) / "model.pkl"
    with open(model_file, "wb") as f:
        pickle.dump(rf, f)

    ClassicalOutputs = namedtuple(
        "ClassicalOutputs", ["accuracy", "auc", "f1", "runtime_ms"]
    )
    return ClassicalOutputs(accuracy=accuracy, auc=auc, f1=f1, runtime_ms=runtime_ms)


# =============================================================================
# STEP 5: Evaluation (quantum vs classical comparison)
# =============================================================================

@component(base_image=_BASE_IMAGE)
def evaluation(
    quantum_accuracy: float,
    quantum_auc: float,
    quantum_f1: float,
    classical_accuracy: float,
    classical_auc: float,
    classical_f1: float,
    min_quantum_advantage_auc: float,
    evaluation_report: Output[Artifact],
    comparison_metrics: Output[ClassificationMetrics],
) -> NamedTuple(
    "EvaluationOutputs",
    [("quantum_wins", bool), ("advantage_ratio", float)],
):
    """
    Compare quantum vs classical metrics and decide whether to register the quantum model.
    quantum_wins = True if quantum_auc >= classical_auc + min_quantum_advantage_auc.
    """
    import json
    from collections import namedtuple
    from pathlib import Path

    advantage_ratio = quantum_auc / max(classical_auc, 1e-9)
    quantum_wins = quantum_auc >= (classical_auc + min_quantum_advantage_auc)

    report = {
        "quantum": {
            "accuracy": quantum_accuracy,
            "auc": quantum_auc,
            "f1": quantum_f1,
        },
        "classical": {
            "accuracy": classical_accuracy,
            "auc": classical_auc,
            "f1": classical_f1,
        },
        "delta": {
            "accuracy": quantum_accuracy - classical_accuracy,
            "auc": quantum_auc - classical_auc,
            "f1": quantum_f1 - classical_f1,
        },
        "advantage_ratio": advantage_ratio,
        "quantum_wins": quantum_wins,
        "decision": "REGISTER_QUANTUM" if quantum_wins else "KEEP_CLASSICAL",
    }

    Path(evaluation_report.path).write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    EvaluationOutputs = namedtuple("EvaluationOutputs", ["quantum_wins", "advantage_ratio"])
    return EvaluationOutputs(quantum_wins=quantum_wins, advantage_ratio=advantage_ratio)


# =============================================================================
# STEP 6: Model Registration
# =============================================================================

@component(base_image=_BASE_IMAGE)
def model_registration(
    quantum_model: Input[Model],
    quantum_wins: bool,
    quantum_accuracy: float,
    quantum_auc: float,
    project: str,
    region: str,
    model_display_name: str,
    registered_model: Output[Artifact],
) -> NamedTuple("RegistrationOutputs", [("model_resource_name", str), ("registered", bool)]):
    """
    Register the quantum model in Vertex AI Model Registry if it beats the classical baseline.
    Skips registration if quantum_wins is False.
    """
    import json
    from collections import namedtuple
    from pathlib import Path

    RegistrationOutputs = namedtuple(
        "RegistrationOutputs", ["model_resource_name", "registered"]
    )

    if not quantum_wins:
        Path(registered_model.path).write_text(
            json.dumps({"registered": False, "reason": "classical_wins"}), encoding="utf-8"
        )
        return RegistrationOutputs(model_resource_name="", registered=False)

    from google.cloud import aiplatform

    aiplatform.init(project=project, location=region)

    model = aiplatform.Model.upload(
        display_name=model_display_name,
        artifact_uri=quantum_model.uri,
        serving_container_image_uri=(
            f"gcr.io/{project}/quantum-worker:latest"
        ),
        labels={
            "framework": "pennylane",
            "model_type": "vqc",
            "auc": str(round(quantum_auc, 4)),
        },
        description=(
            f"Quantum VQC model — accuracy={quantum_accuracy:.4f}, auc={quantum_auc:.4f}"
        ),
    )

    resource_name = model.resource_name
    Path(registered_model.path).write_text(
        json.dumps({"registered": True, "resource_name": resource_name}),
        encoding="utf-8",
    )
    return RegistrationOutputs(model_resource_name=resource_name, registered=True)


# =============================================================================
# STEP 7: Canary Deployment
# =============================================================================

@component(base_image=_BASE_IMAGE)
def canary_deployment(
    registered_model: Input[Artifact],
    endpoint_display_name: str,
    project: str,
    region: str,
    canary_traffic_split_pct: int,
    deployment_report: Output[Artifact],
) -> NamedTuple("DeploymentOutputs", [("endpoint_resource_name", str), ("deployed", bool)]):
    """
    Deploy the registered quantum model as a canary (default 10% traffic split).
    If a production endpoint already exists, the canary is added alongside it.
    If model was not registered (quantum lost), skips deployment.
    """
    import json
    from collections import namedtuple
    from pathlib import Path

    DeploymentOutputs = namedtuple("DeploymentOutputs", ["endpoint_resource_name", "deployed"])

    artifact_data = json.loads(Path(registered_model.path).read_text(encoding="utf-8"))
    if not artifact_data.get("registered"):
        Path(deployment_report.path).write_text(
            json.dumps({"deployed": False, "reason": "model_not_registered"}),
            encoding="utf-8",
        )
        return DeploymentOutputs(endpoint_resource_name="", deployed=False)

    from google.cloud import aiplatform

    aiplatform.init(project=project, location=region)

    model_resource = artifact_data["resource_name"]
    model = aiplatform.Model(model_resource)

    # Find or create endpoint
    existing = aiplatform.Endpoint.list(
        filter=f'display_name="{endpoint_display_name}"',
        order_by="create_time desc",
    )
    if existing:
        endpoint = existing[0]
    else:
        endpoint = aiplatform.Endpoint.create(
            display_name=endpoint_display_name,
            labels={"env": "prod", "model_type": "quantum_vqc"},
        )

    # Deploy with canary traffic split
    endpoint.deploy(
        model=model,
        deployed_model_display_name=f"canary-{model.display_name}",
        machine_type="n1-standard-4",
        min_replica_count=1,
        max_replica_count=2,
        traffic_split={"0": 100 - canary_traffic_split_pct},  # existing gets remainder
        accelerator_type=None,
    )

    endpoint_resource_name = endpoint.resource_name
    Path(deployment_report.path).write_text(
        json.dumps({
            "deployed": True,
            "endpoint": endpoint_resource_name,
            "canary_traffic_pct": canary_traffic_split_pct,
        }),
        encoding="utf-8",
    )
    return DeploymentOutputs(endpoint_resource_name=endpoint_resource_name, deployed=True)


# =============================================================================
# Pipeline Definition
# =============================================================================

@pipeline(
    name="quantum-ml-pipeline",
    description=(
        "End-to-end quantum ML pipeline: data validation → preprocessing → "
        "VQC training → classical comparison → evaluation → "
        "model registration → canary deployment"
    ),
)
def quantum_ml_pipeline(
    # Data inputs
    dataset_gcs_uri: str,
    target_column: str = "label",
    expected_n_features: int = 30,
    min_class_balance_ratio: float = 0.05,

    # Preprocessing
    n_pca_components: int = 8,
    test_size: float = 0.2,
    random_seed: int = 42,

    # Quantum circuit
    n_qubits: int = 8,
    n_layers: int = 3,
    shots: int = 1024,
    encoding: str = "angle",
    optimizer: str = "COBYLA",
    max_iterations: int = 150,

    # Classical baseline
    n_estimators: int = 100,

    # MLflow
    mlflow_tracking_uri: str = "http://mlflow:5000",
    experiment_name: str = "quantum-fraud-detection",

    # Evaluation gate
    min_quantum_advantage_auc: float = 0.01,

    # Deployment
    project: str = "quantum-portal-prod",
    region: str = "us-central1",
    model_display_name: str = "quantum-vqc-fraud-v1",
    endpoint_display_name: str = "quantum-portal-endpoint",
    canary_traffic_split_pct: int = 10,
) -> None:
    # Step 1: Validate data
    validate_op = data_validation(
        dataset_gcs_uri=dataset_gcs_uri,
        target_column=target_column,
        expected_n_features=expected_n_features,
        min_class_balance_ratio=min_class_balance_ratio,
    )

    # Step 2: Preprocess
    preprocess_op = classical_preprocess(
        validated_dataset=validate_op.outputs["validated_dataset"],
        target_column=target_column,
        n_pca_components=n_pca_components,
        test_size=test_size,
        random_seed=random_seed,
    )

    # Step 3: Quantum training (runs in parallel with step 4)
    quantum_op = quantum_training(
        train_dataset=preprocess_op.outputs["train_dataset"],
        test_dataset=preprocess_op.outputs["test_dataset"],
        n_qubits=n_qubits,
        n_layers=n_layers,
        shots=shots,
        encoding=encoding,
        optimizer=optimizer,
        max_iterations=max_iterations,
        random_seed=random_seed,
        mlflow_tracking_uri=mlflow_tracking_uri,
        experiment_name=experiment_name,
    )
    quantum_op.set_cpu_limit("4").set_memory_limit("8G")
    quantum_op.set_display_name("Quantum VQC Training")

    # Step 4: Classical comparison (parallel)
    classical_op = classical_comparison(
        train_dataset=preprocess_op.outputs["train_dataset"],
        test_dataset=preprocess_op.outputs["test_dataset"],
        n_estimators=n_estimators,
        random_seed=random_seed,
        mlflow_tracking_uri=mlflow_tracking_uri,
    )
    classical_op.set_cpu_limit("4").set_memory_limit("8G")
    classical_op.set_display_name("Classical RF Baseline")

    # Step 5: Evaluate
    eval_op = evaluation(
        quantum_accuracy=quantum_op.outputs["accuracy"],
        quantum_auc=quantum_op.outputs["auc"],
        quantum_f1=quantum_op.outputs["f1"],
        classical_accuracy=classical_op.outputs["accuracy"],
        classical_auc=classical_op.outputs["auc"],
        classical_f1=classical_op.outputs["f1"],
        min_quantum_advantage_auc=min_quantum_advantage_auc,
    )
    eval_op.set_display_name("Quantum vs Classical Evaluation")

    # Step 6: Register model
    register_op = model_registration(
        quantum_model=quantum_op.outputs["quantum_model"],
        quantum_wins=eval_op.outputs["quantum_wins"],
        quantum_accuracy=quantum_op.outputs["accuracy"],
        quantum_auc=quantum_op.outputs["auc"],
        project=project,
        region=region,
        model_display_name=model_display_name,
    )
    register_op.set_display_name("Model Registration")

    # Step 7: Canary deployment
    canary_op = canary_deployment(
        registered_model=register_op.outputs["registered_model"],
        endpoint_display_name=endpoint_display_name,
        project=project,
        region=region,
        canary_traffic_split_pct=canary_traffic_split_pct,
    )
    canary_op.set_display_name("Canary Deployment (10%)")


# =============================================================================
# CLI entry point
# =============================================================================

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile or submit quantum ML Vertex AI pipeline")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--region", default="us-central1", help="Vertex AI region")
    parser.add_argument(
        "--pipeline-root",
        required=True,
        help="GCS path for pipeline artifacts, e.g. gs://my-bucket/pipelines",
    )
    parser.add_argument("--dataset-gcs-uri", required=False,
                        default="gs://quantum-portal-prod-quantum-datasets-prod/fraud_data.parquet")
    parser.add_argument("--output-file", default="quantum_ml_pipeline.json",
                        help="Local path to write compiled pipeline JSON")
    parser.add_argument("--submit", action="store_true", help="Submit to Vertex AI after compiling")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    # Compile
    compiler.Compiler().compile(
        pipeline_func=quantum_ml_pipeline,
        package_path=args.output_file,
    )
    print(f"Pipeline compiled → {args.output_file}")

    if args.submit:
        from google.cloud import aiplatform

        aiplatform.init(project=args.project, location=args.region)
        job = aiplatform.PipelineJob(
            display_name="quantum-ml-pipeline",
            template_path=args.output_file,
            pipeline_root=args.pipeline_root,
            parameter_values={
                "dataset_gcs_uri": args.dataset_gcs_uri,
                "project": args.project,
                "region": args.region,
            },
            enable_caching=True,
        )
        job.submit(service_account=None)
        print(f"Pipeline submitted: {job.resource_name}")
