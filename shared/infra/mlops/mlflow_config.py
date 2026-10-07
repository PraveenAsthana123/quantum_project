"""
Quantum Portal — MLflow Experiment Tracking Configuration
=========================================================
Provides helpers for tracking quantum ML experiments with MLflow:
- Structured experiment setup per quantum project (q01–q30)
- Typed parameter logging (n_qubits, n_layers, shots, backend, encoding)
- Typed metric logging (accuracy, AUC, F1, circuit_depth, fidelity, runtime_ms)
- Artifact logging (circuit diagrams, confusion matrices, model weights, reports)
- Model registry with staging/production promotion logic
- Auto-logging for scikit-learn + custom quantum metric wrappers
"""

from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

import mlflow
import mlflow.sklearn
from mlflow.entities import Run
from mlflow.exceptions import MlflowException
from mlflow.models import infer_signature
from mlflow.tracking import MlflowClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI", "http://localhost:5000"
)
MLFLOW_S3_ENDPOINT_URL = os.getenv(
    "MLFLOW_S3_ENDPOINT_URL", "http://localhost:9000"
)

# Canonical experiment names — one per quantum project domain
EXPERIMENT_NAMES: Dict[str, str] = {
    "fraud_detection":    "quantum-fraud-detection",
    "portfolio_opt":      "quantum-portfolio-optimization",
    "credit_scoring":     "quantum-credit-scoring",
    "anomaly_detection":  "quantum-anomaly-detection",
    "q01_algorithms":     "q01-quantum-algorithms",
    "q02_error_mit":      "q02-error-mitigation",
    "q03_ftqc":           "q03-fault-tolerant-qc",
    "q20_chemistry":      "q20-quantum-chemistry",
    "q25_sensing":        "q25-quantum-sensing",
    "benchmark":          "quantum-benchmarks",
}

# Tag keys enforced on every run
REQUIRED_TAGS = {
    "platform": "quantum-portal",
    "backend_type": "simulator",  # override with 'qpu' for real hardware
}


# ---------------------------------------------------------------------------
# Dataclasses for typed parameter / metric sets
# ---------------------------------------------------------------------------

@dataclass
class QuantumRunParams:
    """Hyperparameters logged for every quantum experiment run."""
    # Circuit configuration
    n_qubits: int
    n_layers: int
    shots: int
    backend: str                  # e.g. "aer_simulator", "ibm_brisbane", "sv1"
    encoding: str                 # e.g. "angle", "amplitude", "iqp", "zz_feature_map"

    # Optimization
    optimizer: str = "COBYLA"
    max_iterations: int = 100
    learning_rate: float = 0.01
    entanglement: str = "linear"  # "linear", "full", "circular"

    # Data
    n_features: int = 8
    n_samples_train: int = 1000
    n_samples_test: int = 200
    random_seed: int = 42

    # Error mitigation
    error_mitigation: str = "none"   # "none", "zne", "m3", "pec"
    noise_model: str = "none"

    # Classical baseline comparison
    classical_model: str = "random_forest"
    classical_n_estimators: int = 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_qubits": self.n_qubits,
            "n_layers": self.n_layers,
            "shots": self.shots,
            "backend": self.backend,
            "encoding": self.encoding,
            "optimizer": self.optimizer,
            "max_iterations": self.max_iterations,
            "learning_rate": self.learning_rate,
            "entanglement": self.entanglement,
            "n_features": self.n_features,
            "n_samples_train": self.n_samples_train,
            "n_samples_test": self.n_samples_test,
            "random_seed": self.random_seed,
            "error_mitigation": self.error_mitigation,
            "noise_model": self.noise_model,
            "classical_model": self.classical_model,
            "classical_n_estimators": self.classical_n_estimators,
        }


@dataclass
class QuantumRunMetrics:
    """Metrics logged at the end of a quantum experiment run."""
    # Classification quality
    accuracy: float
    auc: float
    f1: float
    precision: float = 0.0
    recall: float = 0.0

    # Quantum circuit quality
    circuit_depth: int = 0
    gate_count: int = 0
    fidelity: float = 0.0         # state / process fidelity from tomography
    expressibility: float = 0.0  # circuit expressibility score (0–1)
    entanglement_capability: float = 0.0

    # Runtime performance
    runtime_ms: float = 0.0       # total wall-clock time in ms
    transpile_time_ms: float = 0.0
    execution_time_ms: float = 0.0
    optimizer_iterations: int = 0

    # Classical baseline (for comparison)
    classical_accuracy: float = 0.0
    classical_auc: float = 0.0
    classical_f1: float = 0.0
    classical_runtime_ms: float = 0.0

    # Advantage metrics
    quantum_advantage_ratio: float = field(init=False)

    def __post_init__(self) -> None:
        if self.classical_accuracy > 0:
            self.quantum_advantage_ratio = self.accuracy / self.classical_accuracy
        else:
            self.quantum_advantage_ratio = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "accuracy": self.accuracy,
            "auc": self.auc,
            "f1": self.f1,
            "precision": self.precision,
            "recall": self.recall,
            "circuit_depth": self.circuit_depth,
            "gate_count": self.gate_count,
            "fidelity": self.fidelity,
            "expressibility": self.expressibility,
            "entanglement_capability": self.entanglement_capability,
            "runtime_ms": self.runtime_ms,
            "transpile_time_ms": self.transpile_time_ms,
            "execution_time_ms": self.execution_time_ms,
            "optimizer_iterations": self.optimizer_iterations,
            "classical_accuracy": self.classical_accuracy,
            "classical_auc": self.classical_auc,
            "classical_f1": self.classical_f1,
            "classical_runtime_ms": self.classical_runtime_ms,
            "quantum_advantage_ratio": self.quantum_advantage_ratio,
        }


# ---------------------------------------------------------------------------
# MLflow client setup
# ---------------------------------------------------------------------------

def configure_mlflow(tracking_uri: Optional[str] = None) -> MlflowClient:
    """
    Set the MLflow tracking URI and return a configured MlflowClient.
    Also configures S3/MinIO artifact storage credentials from environment.
    """
    uri = tracking_uri or MLFLOW_TRACKING_URI
    mlflow.set_tracking_uri(uri)

    # Point boto3 (used by MLflow's S3 artifact store) at MinIO/S3
    os.environ.setdefault("MLFLOW_S3_ENDPOINT_URL", MLFLOW_S3_ENDPOINT_URL)

    client = MlflowClient(tracking_uri=uri)
    logger.info("MLflow configured: tracking_uri=%s", uri)
    return client


def get_or_create_experiment(
    name: str,
    artifact_location: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> str:
    """
    Return an existing experiment ID, or create a new one.
    Returns the experiment ID string.
    """
    client = MlflowClient()
    exp = client.get_experiment_by_name(name)
    if exp is not None:
        return exp.experiment_id

    loc = artifact_location or f"s3://quantum-mlflow/artifacts/{name}"
    exp_tags = {**REQUIRED_TAGS, **(tags or {})}
    exp_id = mlflow.create_experiment(
        name=name,
        artifact_location=loc,
        tags=exp_tags,
    )
    logger.info("Created MLflow experiment '%s' (id=%s)", name, exp_id)
    return exp_id


# ---------------------------------------------------------------------------
# Context manager for quantum experiment runs
# ---------------------------------------------------------------------------

@contextmanager
def quantum_run(
    experiment_name: str,
    run_name: str,
    params: QuantumRunParams,
    tags: Optional[Dict[str, str]] = None,
) -> Generator[Run, None, None]:
    """
    Context manager wrapping an MLflow run for a quantum experiment.
    Logs params on entry; caller logs metrics + artifacts inside the block;
    run is ended (with FAILED status on exception) on exit.

    Usage::

        with quantum_run("quantum-fraud-detection", "vqc_run_001", params) as run:
            # ... training ...
            log_quantum_metrics(run.info.run_id, metrics)
            log_circuit_artifact(run.info.run_id, circuit, "vqc_circuit")
    """
    exp_id = get_or_create_experiment(experiment_name)
    run_tags = {**REQUIRED_TAGS, "run_name": run_name, **(tags or {})}

    with mlflow.start_run(
        experiment_id=exp_id,
        run_name=run_name,
        tags=run_tags,
    ) as active_run:
        try:
            # Log all parameters up front
            mlflow.log_params(params.to_dict())
            logger.info(
                "Started run '%s' in experiment '%s' (run_id=%s)",
                run_name, experiment_name, active_run.info.run_id,
            )
            yield active_run
        except Exception:
            mlflow.set_tag("run_status", "FAILED")
            logger.exception("Run '%s' failed", run_name)
            raise


def log_quantum_metrics(
    run_id: str,
    metrics: QuantumRunMetrics,
    step: Optional[int] = None,
) -> None:
    """Log a complete QuantumRunMetrics snapshot to the active or named run."""
    client = MlflowClient()
    timestamp = int(time.time() * 1000)
    for key, value in metrics.to_dict().items():
        client.log_metric(
            run_id=run_id,
            key=key,
            value=float(value),
            timestamp=timestamp,
            step=step or 0,
        )


def log_step_metrics(
    run_id: str,
    step: int,
    loss: float,
    accuracy: float,
    circuit_fidelity: float = 0.0,
) -> None:
    """Log per-optimizer-step metrics for training curves."""
    client = MlflowClient()
    ts = int(time.time() * 1000)
    for key, val in [
        ("train_loss", loss),
        ("train_accuracy", accuracy),
        ("circuit_fidelity", circuit_fidelity),
    ]:
        client.log_metric(run_id=run_id, key=key, value=val, timestamp=ts, step=step)


# ---------------------------------------------------------------------------
# Artifact logging helpers
# ---------------------------------------------------------------------------

def log_circuit_diagram(
    run_id: str,
    circuit_str: str,
    name: str = "circuit",
    subfolder: str = "circuits",
) -> None:
    """
    Log a circuit diagram (ASCII/text representation) as an artifact.
    For real Qiskit circuits pass circuit.draw(output='text') as circuit_str.
    """
    tmp = Path(f"/tmp/mlflow_artifacts/{run_id}")
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / f"{name}.txt"
    path.write_text(circuit_str, encoding="utf-8")
    mlflow.log_artifact(str(path), artifact_path=subfolder)
    logger.debug("Logged circuit diagram artifact: %s/%s.txt", subfolder, name)


def log_confusion_matrix(
    run_id: str,
    y_true: List[int],
    y_pred: List[int],
    labels: Optional[List[str]] = None,
    name: str = "confusion_matrix",
) -> None:
    """
    Compute and log a confusion matrix as both a JSON artifact and a PNG (if matplotlib available).
    """
    from sklearn.metrics import confusion_matrix

    cm = confusion_matrix(y_true, y_pred).tolist()
    tmp = Path(f"/tmp/mlflow_artifacts/{run_id}")
    tmp.mkdir(parents=True, exist_ok=True)

    json_path = tmp / f"{name}.json"
    json_path.write_text(
        json.dumps({"confusion_matrix": cm, "labels": labels or []}, indent=2),
        encoding="utf-8",
    )
    mlflow.log_artifact(str(json_path), artifact_path="evaluation")

    try:
        import matplotlib.pyplot as plt
        import seaborn as sns

        fig, ax = plt.subplots(figsize=(6, 5))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                    xticklabels=labels or range(len(cm)),
                    yticklabels=labels or range(len(cm)), ax=ax)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("True")
        ax.set_title(f"{name.replace('_', ' ').title()}")
        png_path = tmp / f"{name}.png"
        fig.savefig(str(png_path), dpi=150, bbox_inches="tight")
        plt.close(fig)
        mlflow.log_artifact(str(png_path), artifact_path="evaluation")
    except ImportError:
        logger.debug("matplotlib/seaborn not available; skipped PNG confusion matrix")


def log_model_weights(
    run_id: str,
    weights: Any,
    name: str = "quantum_weights",
) -> None:
    """
    Log variational circuit parameter weights as a JSON artifact.
    weights must be serializable (e.g. numpy array .tolist() or plain list/dict).
    """
    import numpy as np

    if hasattr(weights, "tolist"):
        weights = weights.tolist()

    tmp = Path(f"/tmp/mlflow_artifacts/{run_id}")
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / f"{name}.json"
    path.write_text(json.dumps({"weights": weights}, indent=2), encoding="utf-8")
    mlflow.log_artifact(str(path), artifact_path="weights")


def log_sklearn_model(
    model: Any,
    artifact_path: str = "classical_baseline",
    input_example: Optional[Any] = None,
    registered_name: Optional[str] = None,
) -> mlflow.models.model.ModelInfo:
    """
    Log a fitted scikit-learn model with auto-inferred signature.
    Optionally register in the model registry.
    """
    signature = None
    if input_example is not None:
        import numpy as np
        signature = infer_signature(input_example, model.predict(input_example))

    info = mlflow.sklearn.log_model(
        sk_model=model,
        artifact_path=artifact_path,
        signature=signature,
        input_example=input_example,
        registered_model_name=registered_name,
    )
    logger.info("Logged sklearn model to artifact_path='%s'", artifact_path)
    return info


# ---------------------------------------------------------------------------
# Model Registry — staging / production promotion
# ---------------------------------------------------------------------------

class QuantumModelRegistry:
    """
    Wraps MLflow model registry operations for quantum portal models.
    Enforces minimum quality gates before stage promotion.
    """

    # Minimum metric thresholds for stage promotion
    STAGING_MIN_AUC = 0.70
    PRODUCTION_MIN_AUC = 0.75
    PRODUCTION_MIN_FIDELITY = 0.80
    PRODUCTION_MIN_ACCURACY = 0.75

    def __init__(self, client: Optional[MlflowClient] = None) -> None:
        self.client = client or MlflowClient()

    def register(
        self,
        run_id: str,
        artifact_path: str,
        model_name: str,
        description: Optional[str] = None,
    ) -> mlflow.entities.model_registry.ModelVersion:
        """Register a model from a completed run."""
        model_uri = f"runs:/{run_id}/{artifact_path}"
        try:
            self.client.create_registered_model(
                name=model_name,
                description=description or f"Quantum ML model — {model_name}",
                tags={**REQUIRED_TAGS},
            )
        except MlflowException:
            pass  # Model already exists in registry

        version = mlflow.register_model(model_uri=model_uri, name=model_name)
        logger.info(
            "Registered model '%s' version %s from run %s",
            model_name, version.version, run_id,
        )
        return version

    def promote_to_staging(
        self,
        model_name: str,
        version: int,
        run_id: str,
    ) -> bool:
        """
        Promote a model version to Staging if it meets the minimum AUC threshold.
        Returns True if promoted, False if gate not cleared.
        """
        auc = self._get_metric(run_id, "auc")
        if auc is None or auc < self.STAGING_MIN_AUC:
            logger.warning(
                "Model '%s' v%s NOT promoted to Staging: auc=%.4f < %.4f",
                model_name, version, auc or 0.0, self.STAGING_MIN_AUC,
            )
            return False

        self.client.transition_model_version_stage(
            name=model_name,
            version=str(version),
            stage="Staging",
            archive_existing_versions=False,
        )
        self.client.update_model_version(
            name=model_name,
            version=str(version),
            description=f"Promoted to Staging: auc={auc:.4f}",
        )
        logger.info("Promoted '%s' v%s to Staging (auc=%.4f)", model_name, version, auc)
        return True

    def promote_to_production(
        self,
        model_name: str,
        version: int,
        run_id: str,
    ) -> bool:
        """
        Promote a model version to Production if it clears all three quality gates:
        AUC >= PRODUCTION_MIN_AUC, fidelity >= PRODUCTION_MIN_FIDELITY,
        and accuracy >= PRODUCTION_MIN_ACCURACY.
        Archives the current Production version first.
        """
        auc = self._get_metric(run_id, "auc") or 0.0
        fidelity = self._get_metric(run_id, "fidelity") or 0.0
        accuracy = self._get_metric(run_id, "accuracy") or 0.0

        gates = {
            "auc": (auc, self.PRODUCTION_MIN_AUC),
            "fidelity": (fidelity, self.PRODUCTION_MIN_FIDELITY),
            "accuracy": (accuracy, self.PRODUCTION_MIN_ACCURACY),
        }
        failed = {k: v for k, v in gates.items() if v[0] < v[1]}
        if failed:
            logger.warning(
                "Model '%s' v%s NOT promoted to Production: failed gates %s",
                model_name, version, failed,
            )
            return False

        self.client.transition_model_version_stage(
            name=model_name,
            version=str(version),
            stage="Production",
            archive_existing_versions=True,  # archive previous Production
        )
        self.client.update_model_version(
            name=model_name,
            version=str(version),
            description=(
                f"Production: auc={auc:.4f}, "
                f"fidelity={fidelity:.4f}, accuracy={accuracy:.4f}"
            ),
        )
        logger.info(
            "Promoted '%s' v%s to Production (auc=%.4f, fidelity=%.4f, acc=%.4f)",
            model_name, version, auc, fidelity, accuracy,
        )
        return True

    def archive(self, model_name: str, version: int) -> None:
        """Move a model version to Archived."""
        self.client.transition_model_version_stage(
            name=model_name,
            version=str(version),
            stage="Archived",
        )
        logger.info("Archived '%s' v%s", model_name, version)

    def get_production_model(self, model_name: str) -> Optional[Any]:
        """Load the current Production version of a model. Returns None if not found."""
        versions = self.client.get_latest_versions(model_name, stages=["Production"])
        if not versions:
            logger.warning("No Production version found for '%s'", model_name)
            return None
        uri = f"models:/{model_name}/Production"
        return mlflow.sklearn.load_model(uri)

    def _get_metric(self, run_id: str, key: str) -> Optional[float]:
        """Retrieve the last-logged value of a metric from a run."""
        try:
            history = self.client.get_metric_history(run_id=run_id, key=key)
            return history[-1].value if history else None
        except MlflowException:
            return None


# ---------------------------------------------------------------------------
# Auto-logging setup
# ---------------------------------------------------------------------------

def enable_autologging(
    log_models: bool = True,
    log_input_examples: bool = False,
    silent: bool = True,
) -> None:
    """
    Enable MLflow auto-logging for scikit-learn.
    Call once at the start of a training script before fitting any model.
    """
    mlflow.sklearn.autolog(
        log_models=log_models,
        log_input_examples=log_input_examples,
        log_model_signatures=True,
        log_post_training_metrics=True,
        silent=silent,
        max_tuning_runs=5,
    )
    logger.info("MLflow sklearn auto-logging enabled")


# ---------------------------------------------------------------------------
# Benchmark comparison helper
# ---------------------------------------------------------------------------

def log_quantum_vs_classical(
    run_id: str,
    quantum_metrics: QuantumRunMetrics,
    classical_metrics: Dict[str, float],
) -> Dict[str, float]:
    """
    Log a side-by-side quantum vs classical comparison and return the delta dict.
    classical_metrics must contain: accuracy, auc, f1, runtime_ms
    """
    client = MlflowClient()
    ts = int(time.time() * 1000)

    q = quantum_metrics.to_dict()
    deltas: Dict[str, float] = {}

    for key in ("accuracy", "auc", "f1"):
        c_val = classical_metrics.get(key, 0.0)
        q_val = float(q.get(key, 0.0))
        delta = q_val - c_val
        deltas[f"delta_{key}"] = delta
        client.log_metric(run_id=run_id, key=f"delta_{key}", value=delta, timestamp=ts)

    # Speed delta: negative means quantum is faster (rare in NISQ era)
    c_rt = classical_metrics.get("runtime_ms", 0.0)
    q_rt = float(q.get("runtime_ms", 0.0))
    deltas["delta_runtime_ms"] = q_rt - c_rt
    client.log_metric(
        run_id=run_id, key="delta_runtime_ms",
        value=deltas["delta_runtime_ms"], timestamp=ts,
    )

    logger.info(
        "Quantum vs Classical — Δacc=%.4f, Δauc=%.4f, Δf1=%.4f",
        deltas.get("delta_accuracy", 0),
        deltas.get("delta_auc", 0),
        deltas.get("delta_f1", 0),
    )
    return deltas


# ---------------------------------------------------------------------------
# Module-level convenience: pre-configure on import if env var is set
# ---------------------------------------------------------------------------

if MLFLOW_TRACKING_URI:
    configure_mlflow(MLFLOW_TRACKING_URI)
