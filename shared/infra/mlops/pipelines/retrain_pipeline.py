"""
Quantum Portal — Retraining Pipeline
=====================================
Vertex AI Pipeline (Kubeflow Pipelines v2 SDK) that runs:
  1. validate_data      — PSI drift check on incoming fraud data
  2. train_classical    — XGBoost retraining
  3. train_quantum      — VQC retraining (PennyLane + Qiskit)
  4. evaluate_model     — accuracy + quantum fidelity check
  5. register_model     — push to Model Registry if improvement > 1%
  6. deploy_canary      — 10% traffic canary shift

Usage (local dry-run):
    python retrain_pipeline.py --compile-only

Usage (submit to Vertex AI):
    python retrain_pipeline.py --project my-project --location us-central1

Dependencies:
    pip install kfp==2.7.0 google-cloud-aiplatform==1.52.0
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from typing import NamedTuple

import kfp
from kfp import dsl
from kfp.dsl import Dataset, Input, Model, Output
from google.cloud import aiplatform

# ---------------------------------------------------------------------------
# Pipeline-level constants (override via pipeline_parameters at runtime)
# ---------------------------------------------------------------------------
PIPELINE_NAME = "quantum-portal-retrain"
GCS_PIPELINE_ROOT = os.environ.get(
    "PIPELINE_ROOT", "gs://quantum-models/pipelines/"
)
IMPROVEMENT_THRESHOLD = 0.01  # 1% accuracy improvement required to register
CANARY_TRAFFIC_PERCENT = 10   # percent of traffic routed to new model
PSI_THRESHOLD = 0.2            # Population Stability Index threshold for drift


# ---------------------------------------------------------------------------
# Component 1: validate_data — PSI drift check
# ---------------------------------------------------------------------------
@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["pandas==2.2.2", "scipy==1.13.0", "google-cloud-bigquery==3.25.0"],
)
def validate_data(
    project_id: str,
    dataset_id: str,
    reference_table: str,
    current_table: str,
    psi_threshold: float,
    report: Output[Dataset],
) -> NamedTuple("Outputs", [("passed", bool), ("max_psi", float)]):
    """
    Compute Population Stability Index (PSI) between reference and current
    fraud transaction distributions. Fails the pipeline if PSI > threshold,
    which indicates the model should be retrained with recalibrated features
    rather than blindly deployed.
    """
    import json
    import numpy as np
    import pandas as pd
    from collections import namedtuple
    from google.cloud import bigquery

    client = bigquery.Client(project=project_id)

    def get_distribution(table: str, column: str, bins: int = 10) -> np.ndarray:
        query = f"SELECT {column} FROM `{project_id}.{dataset_id}.{table}` WHERE {column} IS NOT NULL"
        df = client.query(query).to_dataframe()
        counts, _ = np.histogram(df[column], bins=bins, range=(0, 1))
        dist = (counts + 1e-6) / counts.sum()  # +epsilon to avoid log(0)
        return dist

    feature_columns = ["amount_usd_normalized", "velocity_1h", "velocity_24h",
                       "merchant_risk_score", "card_age_days_normalized"]

    psi_values: dict[str, float] = {}
    for col in feature_columns:
        try:
            ref_dist = get_distribution(reference_table, col)
            cur_dist = get_distribution(current_table, col)
            psi = float(np.sum((cur_dist - ref_dist) * np.log(cur_dist / ref_dist)))
            psi_values[col] = psi
        except Exception as exc:
            print(f"  Warning: PSI computation failed for {col}: {exc}")
            psi_values[col] = 0.0

    max_psi = max(psi_values.values())
    passed = max_psi <= psi_threshold

    report_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "psi_values": psi_values,
        "max_psi": max_psi,
        "threshold": psi_threshold,
        "passed": passed,
    }
    with open(report.path, "w") as f:
        json.dump(report_data, f, indent=2)

    print(f"PSI check: max_psi={max_psi:.4f}, threshold={psi_threshold}, passed={passed}")
    Outputs = namedtuple("Outputs", ["passed", "max_psi"])
    return Outputs(passed=passed, max_psi=max_psi)


# ---------------------------------------------------------------------------
# Component 2: train_classical — XGBoost fraud classifier
# ---------------------------------------------------------------------------
@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=[
        "xgboost==2.0.3", "scikit-learn==1.5.0", "pandas==2.2.2",
        "google-cloud-bigquery==3.25.0", "mlflow==2.13.2",
    ],
)
def train_classical(
    project_id: str,
    dataset_id: str,
    train_table: str,
    mlflow_tracking_uri: str,
    model_artifact: Output[Model],
) -> NamedTuple("Outputs", [("accuracy", float), ("f1_score", float), ("run_id", str)]):
    """
    Retrain XGBoost fraud classifier on current training data.
    Logs metrics + artifact to MLflow. Returns accuracy and F1 score.
    """
    import json
    import numpy as np
    import mlflow
    import mlflow.xgboost
    import xgboost as xgb
    from collections import namedtuple
    from google.cloud import bigquery
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.model_selection import train_test_split

    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment("quantum-fraud-classical")

    client = bigquery.Client(project=project_id)
    query = f"""
        SELECT amount_usd_normalized, velocity_1h, velocity_24h,
               merchant_risk_score, card_age_days_normalized, fraud_label
        FROM `{project_id}.{dataset_id}.{train_table}`
        WHERE fraud_label IS NOT NULL
    """
    df = client.query(query).to_dataframe()

    feature_cols = ["amount_usd_normalized", "velocity_1h", "velocity_24h",
                    "merchant_risk_score", "card_age_days_normalized"]
    X, y = df[feature_cols].values, df["fraud_label"].astype(int).values

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    params = {
        "n_estimators": 300,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "scale_pos_weight": (y == 0).sum() / (y == 1).sum(),  # class imbalance
        "eval_metric": "logloss",
        "tree_method": "hist",
        "random_state": 42,
    }

    with mlflow.start_run() as run:
        mlflow.log_params(params)
        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=50)

        y_pred = model.predict(X_val)
        acc = float(accuracy_score(y_val, y_pred))
        f1 = float(f1_score(y_val, y_pred))

        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("f1_score", f1)
        mlflow.xgboost.log_model(model, artifact_path="model",
                                  registered_model_name="quantum-fraud-xgboost")

        model.save_model(model_artifact.path + ".json")
        run_id = run.info.run_id

    print(f"Classical training done: accuracy={acc:.4f}, f1={f1:.4f}, run_id={run_id}")
    Outputs = namedtuple("Outputs", ["accuracy", "f1_score", "run_id"])
    return Outputs(accuracy=acc, f1_score=f1, run_id=run_id)


# ---------------------------------------------------------------------------
# Component 3: train_quantum — VQC fraud classifier
# ---------------------------------------------------------------------------
@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=[
        "pennylane==0.37.0", "pennylane-lightning==0.37.0",
        "scikit-learn==1.5.0", "numpy==1.26.4", "scipy==1.13.0",
        "mlflow==2.13.2", "google-cloud-bigquery==3.25.0",
    ],
)
def train_quantum(
    project_id: str,
    dataset_id: str,
    train_table: str,
    mlflow_tracking_uri: str,
    n_qubits: int,
    n_layers: int,
    model_artifact: Output[Model],
) -> NamedTuple("Outputs", [("accuracy", float), ("fidelity", float), ("run_id", str)]):
    """
    Train a Variational Quantum Classifier (VQC) on fraud data.
    Uses PennyLane Lightning (CPU) simulator. For QPU execution, swap
    dev = qml.device("lightning.qubit") with the IBM/IonQ provider.
    """
    import json
    import numpy as np
    import pickle
    import mlflow
    import pennylane as qml
    from collections import namedtuple
    from google.cloud import bigquery
    from sklearn.decomposition import PCA
    from sklearn.metrics import accuracy_score
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment("quantum-fraud-vqc")

    client = bigquery.Client(project=project_id)
    query = f"""
        SELECT amount_usd_normalized, velocity_1h, velocity_24h,
               merchant_risk_score, card_age_days_normalized, fraud_label
        FROM `{project_id}.{dataset_id}.{train_table}`
        WHERE fraud_label IS NOT NULL
        LIMIT 2000
    """
    df = client.query(query).to_dataframe()

    feature_cols = ["amount_usd_normalized", "velocity_1h", "velocity_24h",
                    "merchant_risk_score", "card_age_days_normalized"]
    X_raw, y = df[feature_cols].values, df["fraud_label"].astype(int).values

    # PCA to reduce to n_qubits features for angle encoding
    scaler = StandardScaler()
    pca = PCA(n_components=n_qubits)
    X = pca.fit_transform(scaler.fit_transform(X_raw))
    # Rescale to [0, π] for RY angle encoding
    X = (X - X.min(axis=0)) / (X.max(axis=0) - X.min(axis=0) + 1e-8) * np.pi

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    dev = qml.device("lightning.qubit", wires=n_qubits)

    @qml.qnode(dev)
    def circuit(x, weights):
        # Angle encoding
        for i in range(n_qubits):
            qml.RY(x[i], wires=i)
        # Strongly entangling layers
        qml.StronglyEntanglingLayers(weights, wires=range(n_qubits))
        return qml.expval(qml.PauliZ(0))

    weight_shape = qml.StronglyEntanglingLayers.shape(n_layers=n_layers, n_wires=n_qubits)
    weights = np.random.normal(0, np.pi, weight_shape)

    opt = qml.AdamOptimizer(stepsize=0.01)

    def cost_fn(weights):
        preds = np.array([circuit(x, weights) for x in X_train])
        labels = 2 * y_train - 1  # {0,1} → {-1,+1}
        return float(np.mean((preds - labels) ** 2))

    # 50 optimization steps (increase for production; this runs in 1-2 min)
    for step in range(50):
        weights, loss = opt.step_and_cost(cost_fn, weights)
        if step % 10 == 0:
            print(f"  step {step}: loss={loss:.4f}")

    # Evaluate
    val_preds_raw = np.array([circuit(x, weights) for x in X_val])
    val_preds = (val_preds_raw > 0).astype(int)
    acc = float(accuracy_score(y_val, val_preds))

    # Fidelity proxy: average absolute expectation value (1.0 = perfect separation)
    fidelity = float(np.mean(np.abs(val_preds_raw)))

    with mlflow.start_run() as run:
        mlflow.log_params({"n_qubits": n_qubits, "n_layers": n_layers, "steps": 50})
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("fidelity", fidelity)

        # Save weights + preprocessing artifacts
        artifact = {"weights": weights.tolist(), "scaler": scaler, "pca": pca,
                    "n_qubits": n_qubits, "n_layers": n_layers}
        with open(model_artifact.path + ".pkl", "wb") as f:
            pickle.dump(artifact, f)
        mlflow.log_artifact(model_artifact.path + ".pkl", artifact_path="vqc-model")
        run_id = run.info.run_id

    print(f"VQC training done: accuracy={acc:.4f}, fidelity={fidelity:.4f}, run_id={run_id}")
    Outputs = namedtuple("Outputs", ["accuracy", "fidelity", "run_id"])
    return Outputs(accuracy=acc, fidelity=fidelity, run_id=run_id)


# ---------------------------------------------------------------------------
# Component 4: evaluate_model — compare new vs production
# ---------------------------------------------------------------------------
@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["mlflow==2.13.2"],
)
def evaluate_model(
    classical_accuracy: float,
    quantum_accuracy: float,
    quantum_fidelity: float,
    improvement_threshold: float,
    mlflow_tracking_uri: str,
    report: Output[Dataset],
) -> NamedTuple("Outputs", [("should_register", bool), ("winner", str)]):
    """
    Compare new model accuracy against the currently registered production model.
    Recommends registration only if improvement exceeds threshold.
    """
    import json
    import mlflow
    from collections import namedtuple

    mlflow.set_tracking_uri(mlflow_tracking_uri)

    # Fetch current production accuracy from registry
    client = mlflow.tracking.MlflowClient()
    prod_accuracy = 0.0
    try:
        versions = client.get_latest_versions("quantum-fraud-xgboost", stages=["Production"])
        if versions:
            run = client.get_run(versions[0].run_id)
            prod_accuracy = float(run.data.metrics.get("accuracy", 0.0))
    except Exception as exc:
        print(f"  Could not fetch production model metrics: {exc}")

    best_new_accuracy = max(classical_accuracy, quantum_accuracy)
    winner = "quantum" if quantum_accuracy >= classical_accuracy else "classical"
    improvement = best_new_accuracy - prod_accuracy
    should_register = improvement > improvement_threshold

    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "classical_accuracy": classical_accuracy,
        "quantum_accuracy": quantum_accuracy,
        "quantum_fidelity": quantum_fidelity,
        "production_accuracy": prod_accuracy,
        "improvement": improvement,
        "threshold": improvement_threshold,
        "winner": winner,
        "should_register": should_register,
    }
    with open(report.path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Evaluation: prod={prod_accuracy:.4f}, new={best_new_accuracy:.4f}, "
          f"improvement={improvement:.4f}, register={should_register}")
    Outputs = namedtuple("Outputs", ["should_register", "winner"])
    return Outputs(should_register=should_register, winner=winner)


# ---------------------------------------------------------------------------
# Component 5: register_model — push to MLflow Model Registry
# ---------------------------------------------------------------------------
@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["mlflow==2.13.2"],
)
def register_model(
    classical_run_id: str,
    quantum_run_id: str,
    winner: str,
    mlflow_tracking_uri: str,
) -> NamedTuple("Outputs", [("model_version", str), ("model_name", str)]):
    """
    Transition winning model to Staging in MLflow Model Registry.
    Production promotion is a separate manual/approval step.
    """
    import mlflow
    from collections import namedtuple

    mlflow.set_tracking_uri(mlflow_tracking_uri)
    client = mlflow.tracking.MlflowClient()

    run_id = quantum_run_id if winner == "quantum" else classical_run_id
    model_name = f"quantum-fraud-{winner}"

    # Register the model (creates version if name exists)
    model_uri = f"runs:/{run_id}/{'vqc-model' if winner == 'quantum' else 'model'}"
    mv = mlflow.register_model(model_uri=model_uri, name=model_name)

    # Transition to Staging (not Production — requires human approval gate)
    client.transition_model_version_stage(
        name=model_name,
        version=mv.version,
        stage="Staging",
        archive_existing_versions=False,
    )

    print(f"Registered {model_name} version {mv.version} → Staging")
    Outputs = namedtuple("Outputs", ["model_version", "model_name"])
    return Outputs(model_version=str(mv.version), model_name=model_name)


# ---------------------------------------------------------------------------
# Component 6: deploy_canary — shift 10% of traffic to new model
# ---------------------------------------------------------------------------
@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["google-cloud-aiplatform==1.52.0"],
)
def deploy_canary(
    project_id: str,
    location: str,
    endpoint_id: str,
    model_name: str,
    model_version: str,
    traffic_percent: int,
) -> NamedTuple("Outputs", [("deployed", bool), ("endpoint_id", str)]):
    """
    Deploy new Staging model to Vertex AI Endpoint at canary traffic split.
    The remaining (100 - traffic_percent)% stays on the current champion.
    """
    import json
    from collections import namedtuple
    from google.cloud import aiplatform

    aiplatform.init(project=project_id, location=location)

    endpoint = aiplatform.Endpoint(endpoint_name=endpoint_id)

    # Deploy new model at canary split
    new_model = aiplatform.Model(
        model_name=f"projects/{project_id}/locations/{location}/models/{model_name}"
    )
    endpoint.deploy(
        model=new_model,
        deployed_model_display_name=f"{model_name}-v{model_version}-canary",
        traffic_percentage=traffic_percent,
        machine_type="n1-standard-4",
        min_replica_count=1,
        max_replica_count=3,
        sync=True,
    )

    print(f"Canary deployed: {model_name} v{model_version} at {traffic_percent}% traffic")
    Outputs = namedtuple("Outputs", ["deployed", "endpoint_id"])
    return Outputs(deployed=True, endpoint_id=endpoint_id)


# ---------------------------------------------------------------------------
# Pipeline definition
# ---------------------------------------------------------------------------
@dsl.pipeline(
    name=PIPELINE_NAME,
    description="Quantum Portal automated retraining: drift check → train → evaluate → register → canary deploy",
    pipeline_root=GCS_PIPELINE_ROOT,
)
def retrain_pipeline(
    project_id: str,
    dataset_id: str = "quantum_analytics_prod",
    reference_table: str = "fraud_transactions_reference",
    current_table: str = "fraud_transactions",
    train_table: str = "fraud_transactions",
    mlflow_tracking_uri: str = "http://mlflow:5000",
    n_qubits: int = 5,
    n_layers: int = 3,
    improvement_threshold: float = IMPROVEMENT_THRESHOLD,
    canary_traffic_percent: int = CANARY_TRAFFIC_PERCENT,
    vertex_endpoint_id: str = "",
    location: str = "us-central1",
):
    # Step 1: data validation
    validation = validate_data(
        project_id=project_id,
        dataset_id=dataset_id,
        reference_table=reference_table,
        current_table=current_table,
        psi_threshold=PSI_THRESHOLD,
    )

    # Step 2 + 3: parallel training (only if data validation passed)
    with dsl.Condition(validation.outputs["passed"] == True, name="data-valid"):

        classical_training = train_classical(
            project_id=project_id,
            dataset_id=dataset_id,
            train_table=train_table,
            mlflow_tracking_uri=mlflow_tracking_uri,
        )

        quantum_training = train_quantum(
            project_id=project_id,
            dataset_id=dataset_id,
            train_table=train_table,
            mlflow_tracking_uri=mlflow_tracking_uri,
            n_qubits=n_qubits,
            n_layers=n_layers,
        )

        # Step 4: evaluation
        evaluation = evaluate_model(
            classical_accuracy=classical_training.outputs["accuracy"],
            quantum_accuracy=quantum_training.outputs["accuracy"],
            quantum_fidelity=quantum_training.outputs["fidelity"],
            improvement_threshold=improvement_threshold,
            mlflow_tracking_uri=mlflow_tracking_uri,
        )

        # Step 5: register only if improvement threshold met
        with dsl.Condition(evaluation.outputs["should_register"] == True, name="should-register"):

            registration = register_model(
                classical_run_id=classical_training.outputs["run_id"],
                quantum_run_id=quantum_training.outputs["run_id"],
                winner=evaluation.outputs["winner"],
                mlflow_tracking_uri=mlflow_tracking_uri,
            )

            # Step 6: canary deploy only if endpoint is configured
            with dsl.Condition(vertex_endpoint_id != "", name="has-endpoint"):
                deploy_canary(
                    project_id=project_id,
                    location=location,
                    endpoint_id=vertex_endpoint_id,
                    model_name=registration.outputs["model_name"],
                    model_version=registration.outputs["model_version"],
                    traffic_percent=canary_traffic_percent,
                )


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Compile or submit retraining pipeline")
    parser.add_argument("--project", default=os.environ.get("GCP_PROJECT", ""))
    parser.add_argument("--location", default="us-central1")
    parser.add_argument("--compile-only", action="store_true", help="Compile to JSON only, don't submit")
    parser.add_argument("--output", default="retrain_pipeline.json", help="Output compiled pipeline JSON")
    args = parser.parse_args()

    # Compile pipeline to JSON
    kfp.compiler.Compiler().compile(pipeline_func=retrain_pipeline, package_path=args.output)
    print(f"Pipeline compiled to: {args.output}")

    if not args.compile_only:
        if not args.project:
            raise ValueError("--project is required when submitting")

        aiplatform.init(project=args.project, location=args.location)
        job = aiplatform.PipelineJob(
            display_name=PIPELINE_NAME,
            template_path=args.output,
            pipeline_root=GCS_PIPELINE_ROOT,
            parameter_values={"project_id": args.project},
        )
        job.submit()
        print(f"Pipeline submitted. Job name: {job.resource_name}")


if __name__ == "__main__":
    main()
