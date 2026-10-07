"""
Quantum Portal — LLM Cost + Quality Tracker
============================================
Tracks every LLM inference call: model, tokens, latency, cost.
Detects quality drift by comparing ROUGE scores against a baseline.
Backed by BigQuery for cross-session persistence.

Usage:
    from shared.infra.mlops.llmops.llm_metrics.tracker import LLMMetricsTracker

    tracker = LLMMetricsTracker(project_id="my-project")

    # Track a single inference call
    tracker.track_inference(
        model="gemma-2-9b-it",
        prompt_tokens=512,
        completion_tokens=256,
        latency_ms=340.5,
        cost_usd=0.000128,
        use_case="fraud_explanation",
        request_id="req-abc123",
    )

    # Get cost report for the last 7 days
    report = tracker.get_cost_report(days=7)

    # Check if ROUGE score drifted more than 10% vs baseline
    alert = tracker.detect_quality_drift("gemma-2-9b-it", recent_scores, baseline_scores)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pricing table (USD per 1K tokens)
# Approximate open-source hosting costs at GCP L4 rates (~$1.10/hr)
# Update periodically as cloud pricing changes.
# ---------------------------------------------------------------------------
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gemma-2-9b-it":           {"prompt": 0.00020, "completion": 0.00040},
    "llama-3.1-8b-instruct":   {"prompt": 0.00018, "completion": 0.00036},
    "qwen-2.5-7b-instruct":    {"prompt": 0.00015, "completion": 0.00030},
    "mistral-7b-instruct-v0.3":{"prompt": 0.00015, "completion": 0.00030},
    "phi-3.5-mini-instruct":   {"prompt": 0.00010, "completion": 0.00020},
    "llama-3.1-70b-instruct":  {"prompt": 0.00080, "completion": 0.00120},
    "qwen-2.5-72b-instruct":   {"prompt": 0.00075, "completion": 0.00110},
    # Cloud embedding APIs
    "text-embedding-004":      {"prompt": 0.00010, "completion": 0.00000},
    "default":                 {"prompt": 0.00030, "completion": 0.00060},
}

DRIFT_ALERT_THRESHOLD = 0.10  # 10% relative ROUGE-L drop triggers alert


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------
@dataclass
class InferenceRecord:
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    cost_usd: float
    use_case: str
    request_id: str
    timestamp: str
    session_id: str
    success: bool
    error_message: str


# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------
class LLMMetricsTracker:
    """
    BigQuery-backed LLM inference tracker.
    Table: {project_id}.quantum_analytics_{env}.llm_metrics
    """

    TABLE_SCHEMA = [
        {"name": "model",             "type": "STRING",    "mode": "REQUIRED"},
        {"name": "prompt_tokens",     "type": "INT64",     "mode": "REQUIRED"},
        {"name": "completion_tokens", "type": "INT64",     "mode": "REQUIRED"},
        {"name": "total_tokens",      "type": "INT64",     "mode": "REQUIRED"},
        {"name": "latency_ms",        "type": "FLOAT64",   "mode": "REQUIRED"},
        {"name": "cost_usd",          "type": "FLOAT64",   "mode": "REQUIRED"},
        {"name": "use_case",          "type": "STRING",    "mode": "NULLABLE"},
        {"name": "request_id",        "type": "STRING",    "mode": "NULLABLE"},
        {"name": "session_id",        "type": "STRING",    "mode": "NULLABLE"},
        {"name": "success",           "type": "BOOL",      "mode": "REQUIRED"},
        {"name": "error_message",     "type": "STRING",    "mode": "NULLABLE"},
        {"name": "timestamp",         "type": "TIMESTAMP", "mode": "REQUIRED"},
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
        self.table_id = f"{project_id}.{self.dataset_id}.llm_metrics"
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from google.cloud import bigquery
            self._client = bigquery.Client(project=self.project_id)
        return self._client

    @staticmethod
    def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Estimate inference cost based on the pricing table.
        Returns cost in USD. Uses "default" pricing if model not found.
        """
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
        cost = (prompt_tokens / 1000 * pricing["prompt"] +
                completion_tokens / 1000 * pricing["completion"])
        return round(cost, 8)

    def track_inference(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        cost_usd: float | None = None,
        use_case: str = "general",
        request_id: str = "",
        session_id: str = "",
        success: bool = True,
        error_message: str = "",
    ) -> float:
        """
        Record a single LLM inference call.

        Args:
            model:             Model name (must match models.yaml name field)
            prompt_tokens:     Number of prompt/input tokens
            completion_tokens: Number of generated/output tokens
            latency_ms:        End-to-end latency in milliseconds
            cost_usd:          Actual cost if known; estimated if None
            use_case:          Application use case label for cost attribution
            request_id:        Unique request identifier for trace correlation
            session_id:        Session/user identifier for per-session reporting
            success:           True if inference succeeded
            error_message:     Error detail if success=False

        Returns:
            cost_usd (estimated or actual)
        """
        if cost_usd is None:
            cost_usd = self.estimate_cost(model, prompt_tokens, completion_tokens)

        row = {
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "latency_ms": latency_ms,
            "cost_usd": cost_usd,
            "use_case": use_case,
            "request_id": request_id,
            "session_id": session_id,
            "success": success,
            "error_message": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            errors = self.client.insert_rows_json(self.table_id, [row])
            if errors:
                logger.warning("BigQuery insert errors: %s", errors)
        except Exception as exc:
            logger.error("Failed to track inference: %s", exc)

        return cost_usd

    def get_cost_report(
        self,
        days: int = 7,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Aggregate cost per model per day over the reporting period.

        Args:
            days:       Number of trailing days (ignored if start/end provided)
            start_date: ISO date string "YYYY-MM-DD" (inclusive)
            end_date:   ISO date string "YYYY-MM-DD" (inclusive)

        Returns:
            dict with keys: period, total_cost_usd, total_tokens,
            by_model (list of {model, cost, tokens, requests, avg_latency_ms}),
            by_day (list of {date, model, cost, tokens})
        """
        if start_date is None:
            end_dt = datetime.now(timezone.utc)
            start_dt = end_dt - timedelta(days=days)
            start_date = start_dt.strftime("%Y-%m-%d")
            end_date = end_dt.strftime("%Y-%m-%d")

        query = f"""
        SELECT
          model,
          DATE(timestamp) AS report_date,
          SUM(cost_usd)          AS total_cost,
          SUM(total_tokens)      AS total_tokens,
          COUNT(*)               AS request_count,
          AVG(latency_ms)        AS avg_latency_ms,
          COUNTIF(NOT success)   AS error_count
        FROM `{self.table_id}`
        WHERE DATE(timestamp) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY model, DATE(timestamp)
        ORDER BY report_date DESC, total_cost DESC
        """

        rows = list(self.client.query(query).result())

        by_model: dict[str, dict] = {}
        by_day: list[dict] = []
        total_cost = 0.0
        total_tokens = 0

        for row in rows:
            m = row["model"]
            cost = float(row["total_cost"])
            tokens = int(row["total_tokens"])
            total_cost += cost
            total_tokens += tokens

            if m not in by_model:
                by_model[m] = {"model": m, "cost_usd": 0.0, "total_tokens": 0,
                                "request_count": 0, "avg_latency_ms": 0.0, "error_count": 0}
            by_model[m]["cost_usd"] += cost
            by_model[m]["total_tokens"] += tokens
            by_model[m]["request_count"] += int(row["request_count"])
            by_model[m]["error_count"] += int(row["error_count"])
            # Simple running average (approximate for multi-day aggregate)
            by_model[m]["avg_latency_ms"] = float(row["avg_latency_ms"])

            by_day.append({
                "date": str(row["report_date"]),
                "model": m,
                "cost_usd": cost,
                "total_tokens": tokens,
                "request_count": int(row["request_count"]),
            })

        return {
            "period": {"start": start_date, "end": end_date, "days": days},
            "total_cost_usd": round(total_cost, 6),
            "total_tokens": total_tokens,
            "by_model": sorted(by_model.values(), key=lambda x: x["cost_usd"], reverse=True),
            "by_day": by_day,
        }

    def detect_quality_drift(
        self,
        model: str,
        recent_scores: list[float],
        baseline_scores: list[float],
        threshold: float = DRIFT_ALERT_THRESHOLD,
        metric_name: str = "rouge_l",
    ) -> dict[str, Any]:
        """
        Detect quality drift by comparing recent ROUGE-L scores to a baseline.
        Raises an alert if relative drop exceeds threshold.

        Args:
            model:           Model name
            recent_scores:   List of recent ROUGE-L (or other) scores
            baseline_scores: List of historical baseline scores
            threshold:       Relative drop threshold (0.10 = 10%)
            metric_name:     Metric label for reporting

        Returns:
            dict with: model, metric_name, baseline_mean, recent_mean,
            relative_drop, threshold, alert (bool), message
        """
        if not recent_scores:
            return {"alert": False, "message": "No recent scores provided", "model": model}
        if not baseline_scores:
            return {"alert": False, "message": "No baseline scores provided", "model": model}

        baseline_mean = sum(baseline_scores) / len(baseline_scores)
        recent_mean = sum(recent_scores) / len(recent_scores)

        if baseline_mean == 0:
            return {"alert": False, "message": "Baseline mean is zero; cannot compute relative drop",
                    "model": model}

        relative_drop = (baseline_mean - recent_mean) / baseline_mean
        alert = relative_drop > threshold

        result = {
            "model": model,
            "metric_name": metric_name,
            "baseline_mean": round(baseline_mean, 4),
            "recent_mean": round(recent_mean, 4),
            "relative_drop": round(relative_drop, 4),
            "threshold": threshold,
            "alert": alert,
            "message": (
                f"ALERT: {model} {metric_name} dropped {relative_drop:.1%} "
                f"(baseline={baseline_mean:.4f}, recent={recent_mean:.4f})"
                if alert else
                f"OK: {model} {metric_name} within tolerance "
                f"(drop={relative_drop:.1%}, threshold={threshold:.1%})"
            ),
        }

        if alert:
            logger.warning(result["message"])
            # Optionally write alert to BigQuery for dashboard visibility
            self._log_quality_alert(result)

        return result

    def _log_quality_alert(self, alert: dict) -> None:
        """Write a quality drift alert to BigQuery for ops dashboards."""
        try:
            alert_table = f"{self.project_id}.{self.dataset_id}.llm_quality_alerts"
            row = {
                **alert,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.client.insert_rows_json(alert_table, [row])
        except Exception as exc:
            logger.warning("Could not log quality alert to BigQuery: %s", exc)
