"""
qc-finops-lab — QPU FinOps & Scheduling Lab
=============================================
Exports the four main classes for easy import:

    from qc_finops_lab import QPUCostModeler, QPUScheduler, ResourceEstimator, FinOpsDashboard
"""
from __future__ import annotations

from qpu_cost_model   import QPUCostModeler, QPUJob, CostEstimate
from qpu_scheduler    import QPUScheduler, Priority, JobStatus, ScheduledJob
from resource_estimator import ResourceEstimator
from finops_dashboard import FinOpsDashboard, JobRecord

__all__ = [
    "QPUCostModeler",
    "QPUJob",
    "CostEstimate",
    "QPUScheduler",
    "Priority",
    "JobStatus",
    "ScheduledJob",
    "ResourceEstimator",
    "FinOpsDashboard",
    "JobRecord",
]

__version__ = "1.0.0"
__author__  = "Quantum FinOps Lab"
