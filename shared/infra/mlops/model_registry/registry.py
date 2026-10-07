"""
Quantum Portal — Model Registry
=================================
Lightweight model registry backed by BigQuery. Tracks all classical and
quantum model versions with accuracy, fidelity, and artifact path.
Used by: retrain pipeline, API serving layer, benchmark runner.

Usage:
    from shared.infra.mlops.model_registry.registry import ModelRegistry

    reg = ModelRegistry(project_id="my-project")
    reg.register_model(
        name="fraud-vqc",
        version="1.0.3",
        accuracy=0.934,
        fidelity=0.87,
        artifact_path="gs://quantum-models/vqc/v1.0.3/",
        metadata={"n_qubits": 5, "n_layers": 3},
    )
    best = reg.get_latest_model("fraud-vqc")
    diff = reg.compare_models("fraud-vqc", "1.0.2", "1.0.3")
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class ModelVersion:
    name: str
    version: str
    accuracy: float
    fidelity: float
    artifact_path: str
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    stage: str = "staging"          # staging | production | archived
    model_type: str = "unknown"     # classical | quantum | hybrid
    framework: str = "unknown"      # xgboost | pennylane | qiskit | sklearn
    git_commit: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_bq_row(self) -> dict:
        row = asdict(self)
        row["metadata_json"] = json.dumps(row.pop("metadata"))
        return row

    @classmethod
    def from_bq_row(cls, row: dict) -> "ModelVersion":
        data = dict(row)
        metadata_json = data.pop("metadata_json", "{}")
        data["metadata"] = json.loads(metadata_json) if metadata_json else {}
        return cls(**data)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
class ModelRegistry:
    """
    BigQuery-backed model registry.
    Table: {project_id}.quantum_analytics_{env}.model_registry
    """

    TABLE_SCHEMA = [
        {"name": "name",           "type": "STRING",    "mode": "REQUIRED"},
        {"name": "version",        "type": "STRING",    "mode": "REQUIRED"},
        {"name": "accuracy",       "type": "FLOAT64",   "mode": "REQUIRED"},
        {"name": "fidelity",       "type": "FLOAT64",   "mode": "REQUIRED"},
        {"name": "artifact_path",  "type": "STRING",    "mode": "REQUIRED"},
        {"name": "registered_at",  "type": "TIMESTAMP", "mode": "REQUIRED"},
        {"name": "stage",          "type": "STRING",    "mode": "REQUIRED"},
        {"name": "model_type",     "type": "STRING",    "mode": "NULLABLE"},
        {"name": "framework",      "type": "STRING",    "mode": "NULLABLE"},
        {"name": "git_commit",     "type": "STRING",    "mode": "NULLABLE"},
        {"name": "metadata_json",  "type": "JSON",      "mode": "NULLABLE"},
    ]

    def __init__(
        self,
        project_id: str,
        env: str = "prod",
        dataset_id: str | None = None,
    ):
        self.project_id = project_id
        self.env = env
        self.dataset_id = dataset_id or f"quantum_analytics_{env}"
        self.table_id = f"{project_id}.{self.dataset_id}.model_registry"
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from google.cloud import bigquery
            self._client = bigquery.Client(project=self.project_id)
        return self._client

    def _ensure_table(self) -> None:
        """Create model_registry table if it does not exist."""
        from google.cloud import bigquery
        from google.cloud.exceptions import NotFound

        try:
            self.client.get_table(self.table_id)
        except NotFound:
            schema = [
                bigquery.SchemaField(col["name"], col["type"], mode=col["mode"])
                for col in self.TABLE_SCHEMA
            ]
            table = bigquery.Table(self.table_id, schema=schema)
            table.time_partitioning = bigquery.TimePartitioning(field="registered_at")
            self.client.create_table(table)
            logger.info("Created model_registry table: %s", self.table_id)

    def register_model(
        self,
        name: str,
        version: str,
        accuracy: float,
        fidelity: float,
        artifact_path: str,
        model_type: str = "unknown",
        framework: str = "unknown",
        git_commit: str = "",
        metadata: dict | None = None,
    ) -> ModelVersion:
        """
        Register a new model version. Existing (name, version) pairs are
        replaced (upsert) by deleting the old row first.

        Args:
            name:          Model family name, e.g. "fraud-vqc", "fraud-xgboost"
            version:       Semantic version string, e.g. "1.0.3"
            accuracy:      Validation accuracy (0–1)
            fidelity:      Quantum fidelity / classical proxy (0–1)
            artifact_path: GCS/S3 path to model artifact, e.g. "gs://..."
            model_type:    "classical" | "quantum" | "hybrid"
            framework:     Training framework, e.g. "pennylane", "xgboost"
            git_commit:    Git commit SHA for reproducibility
            metadata:      Free-form dict for extra fields (circuit depth, etc.)

        Returns:
            ModelVersion dataclass
        """
        self._ensure_table()

        mv = ModelVersion(
            name=name,
            version=version,
            accuracy=accuracy,
            fidelity=fidelity,
            artifact_path=artifact_path,
            model_type=model_type,
            framework=framework,
            git_commit=git_commit,
            metadata=metadata or {},
        )

        # Delete existing row with same (name, version) to avoid duplicates
        delete_query = f"""
            DELETE FROM `{self.table_id}`
            WHERE name = @name AND version = @version
        """
        from google.cloud.bigquery import ArrayQueryParameter, ScalarQueryParameter, QueryJobConfig
        job_config = QueryJobConfig(
            query_parameters=[
                ScalarQueryParameter("name", "STRING", name),
                ScalarQueryParameter("version", "STRING", version),
            ]
        )
        self.client.query(delete_query, job_config=job_config).result()

        # Insert new row
        errors = self.client.insert_rows_json(self.table_id, [mv.to_bq_row()])
        if errors:
            raise RuntimeError(f"BigQuery insert failed: {errors}")

        logger.info("Registered model %s v%s: accuracy=%.4f, fidelity=%.4f",
                    name, version, accuracy, fidelity)
        return mv

    def get_latest_model(
        self,
        name: str,
        stage: str = "production",
    ) -> ModelVersion | None:
        """
        Return the model version with the highest accuracy for the given name
        and stage. Returns None if no models are registered.

        Args:
            name:  Model family name
            stage: Stage filter: "staging" | "production" | "archived" | ""

        Returns:
            Best ModelVersion, or None if nothing registered
        """
        stage_filter = "AND stage = @stage" if stage else ""
        query = f"""
            SELECT *
            FROM `{self.table_id}`
            WHERE name = @name {stage_filter}
            ORDER BY accuracy DESC, registered_at DESC
            LIMIT 1
        """
        from google.cloud.bigquery import ScalarQueryParameter, QueryJobConfig
        params = [ScalarQueryParameter("name", "STRING", name)]
        if stage:
            params.append(ScalarQueryParameter("stage", "STRING", stage))

        rows = list(self.client.query(query, job_config=QueryJobConfig(query_parameters=params)).result())
        if not rows:
            return None
        return ModelVersion.from_bq_row(dict(rows[0]))

    def compare_models(
        self,
        name: str,
        v1: str,
        v2: str,
    ) -> dict[str, Any]:
        """
        Compare two versions of a model. Returns a diff table with
        accuracy delta, fidelity delta, registration timestamps.

        Args:
            name: Model family name
            v1:   First version string
            v2:   Second version string

        Returns:
            dict with keys: model_a, model_b, accuracy_delta, fidelity_delta,
            winner, metadata_diff
        """
        from google.cloud.bigquery import ArrayQueryParameter, ScalarQueryParameter, QueryJobConfig

        query = f"""
            SELECT * FROM `{self.table_id}`
            WHERE name = @name AND version IN UNNEST(@versions)
        """
        job_config = QueryJobConfig(
            query_parameters=[
                ScalarQueryParameter("name", "STRING", name),
                ArrayQueryParameter("versions", "STRING", [v1, v2]),
            ]
        )
        rows = {
            row["version"]: ModelVersion.from_bq_row(dict(row))
            for row in self.client.query(query, job_config=job_config).result()
        }

        if v1 not in rows:
            raise ValueError(f"Version {v1} not found for model {name}")
        if v2 not in rows:
            raise ValueError(f"Version {v2} not found for model {name}")

        m1, m2 = rows[v1], rows[v2]
        accuracy_delta = m2.accuracy - m1.accuracy
        fidelity_delta = m2.fidelity - m1.fidelity
        winner = v2 if m2.accuracy >= m1.accuracy else v1

        # Shallow diff of metadata dicts
        all_keys = set(m1.metadata) | set(m2.metadata)
        metadata_diff = {
            k: {"v1": m1.metadata.get(k), "v2": m2.metadata.get(k)}
            for k in all_keys
            if m1.metadata.get(k) != m2.metadata.get(k)
        }

        return {
            "model_name": name,
            "model_a": {"version": v1, "accuracy": m1.accuracy, "fidelity": m1.fidelity,
                        "stage": m1.stage, "registered_at": m1.registered_at},
            "model_b": {"version": v2, "accuracy": m2.accuracy, "fidelity": m2.fidelity,
                        "stage": m2.stage, "registered_at": m2.registered_at},
            "accuracy_delta": round(accuracy_delta, 6),
            "fidelity_delta": round(fidelity_delta, 6),
            "winner": winner,
            "metadata_diff": metadata_diff,
        }

    def list_models(
        self,
        name: str | None = None,
        stage: str | None = None,
        limit: int = 50,
    ) -> list[ModelVersion]:
        """
        List all registered models, optionally filtered by name and/or stage.
        Ordered by registered_at DESC.
        """
        from google.cloud.bigquery import ScalarQueryParameter, QueryJobConfig

        conditions = []
        params = []
        if name:
            conditions.append("name = @name")
            params.append(ScalarQueryParameter("name", "STRING", name))
        if stage:
            conditions.append("stage = @stage")
            params.append(ScalarQueryParameter("stage", "STRING", stage))

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT * FROM `{self.table_id}`
            {where}
            ORDER BY registered_at DESC
            LIMIT {limit}
        """
        rows = list(self.client.query(query, job_config=QueryJobConfig(query_parameters=params)).result())
        return [ModelVersion.from_bq_row(dict(r)) for r in rows]

    def promote(self, name: str, version: str, to_stage: str = "production") -> None:
        """
        Promote a model version to a new stage.
        Archives any existing production version for the same name.
        """
        from google.cloud.bigquery import ScalarQueryParameter, QueryJobConfig

        if to_stage == "production":
            # Archive all existing production versions for this model
            archive_query = f"""
                UPDATE `{self.table_id}`
                SET stage = 'archived'
                WHERE name = @name AND stage = 'production'
            """
            self.client.query(archive_query, job_config=QueryJobConfig(
                query_parameters=[ScalarQueryParameter("name", "STRING", name)]
            )).result()

        promote_query = f"""
            UPDATE `{self.table_id}`
            SET stage = @stage
            WHERE name = @name AND version = @version
        """
        self.client.query(promote_query, job_config=QueryJobConfig(
            query_parameters=[
                ScalarQueryParameter("name", "STRING", name),
                ScalarQueryParameter("version", "STRING", version),
                ScalarQueryParameter("stage", "STRING", to_stage),
            ]
        )).result()

        logger.info("Promoted %s v%s → %s", name, version, to_stage)
