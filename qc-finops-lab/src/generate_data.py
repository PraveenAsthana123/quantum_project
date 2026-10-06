"""
QPU FinOps Synthetic Data Generator
=====================================
Purpose   : Generate a realistic QPU job history dataset (500 jobs) for cost
            analysis, scheduler benchmarking, and FinOps dashboard demos.
Providers : IBM Quantum (Eagle/Heron), AWS Braket, Azure Quantum, Google Cirq
Outputs   : data/qpu_jobs.csv  |  data/qpu_monthly_summary.json

Cost models used
----------------
  IBM Eagle  : n_shots / 1000 * 1.60   (≤50 qubits)
  IBM Heron  : n_shots / 1000 * 3.00   (>50 qubits)
  AWS Braket : 0.30 + n_shots * 0.00035
  Azure      : n_shots * 0.065
  Google     : $0.00 (research partner; queue latency modelled separately)

Usage
-----
    python generate_data.py
    # → writes qpu_jobs.csv and qpu_monthly_summary.json to ../data/
"""
from __future__ import annotations

import csv
import json
import math
import os
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

# ── Reproducible seed ────────────────────────────────────────────────────────
random.seed(42)

# ── Paths ────────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(_SCRIPT_DIR, "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

JOBS_CSV         = os.path.join(DATA_DIR, "qpu_jobs.csv")
MONTHLY_JSON     = os.path.join(DATA_DIR, "qpu_monthly_summary.json")

# ── Constants ─────────────────────────────────────────────────────────────────
N_JOBS = 500

ALGORITHMS  = ["Shor", "Grover", "VQE", "QAOA", "QKD"]
PROVIDERS   = ["IBM", "AWS", "Azure", "Google"]
PRIORITIES  = ["CRITICAL", "HIGH", "NORMAL", "LOW"]

# Algorithm qubit / depth / shot profiles (min, max)
ALGO_PROFILES: Dict[str, Dict[str, Any]] = {
    "Shor" : {"qubits": (20, 100), "depth": (200, 1000), "shots": (1024,  8192)},
    "Grover":{"qubits": (10, 50),  "depth": (50,  400),  "shots": (4096,  32768)},
    "VQE"  : {"qubits": (5,  30),  "depth": (10,  200),  "shots": (8192,  100000)},
    "QAOA" : {"qubits": (8,  40),  "depth": (20,  300),  "shots": (4096,  50000)},
    "QKD"  : {"qubits": (5,  20),  "depth": (10,  100),  "shots": (100,   2048)},
}

# Months in scope (2026-01 through 2026-10)
MONTHS = [f"2026-{m:02d}" for m in range(1, 11)]


# ── Cost models ───────────────────────────────────────────────────────────────

def _ibm_cost(n_qubits: int, n_shots: int) -> float:
    """IBM Eagle ($1.60/1k) for ≤50 qubits; Heron ($3.00/1k) for >50 qubits."""
    rate = 3.00 if n_qubits > 50 else 1.60
    return round(n_shots / 1000.0 * rate, 4)


def _aws_cost(n_shots: int) -> float:
    """AWS Braket: $0.30 task fee + $0.00035/shot."""
    return round(0.30 + n_shots * 0.00035, 4)


def _azure_cost(n_shots: int) -> float:
    """Azure Quantum (Quantinuum H2): $0.065/shot."""
    return round(n_shots * 0.065, 4)


def _google_cost() -> float:
    """Google research partner: $0.00 compute cost."""
    return 0.0


def _queue_time(provider: str, priority: str) -> int:
    """Heuristic queue wait in seconds."""
    base = {"IBM": 900, "AWS": 600, "Azure": 300, "Google": 3600}[provider]
    mult = {"CRITICAL": 0.3, "HIGH": 0.6, "NORMAL": 1.0, "LOW": 1.8}[priority]
    jitter = random.uniform(0.5, 1.5)
    return max(10, int(base * mult * jitter))


def _run_time(n_qubits: int, n_shots: int, provider: str) -> int:
    """Heuristic execution time in seconds."""
    # trapped-ion (Azure/Google) is slower per shot
    us_per_shot = {"IBM": 0.12, "AWS": 0.35, "Azure": 1.50, "Google": 0.08}[provider]
    base_ms = n_shots * us_per_shot / 1000.0 + n_qubits * 0.5
    return max(1, min(300, int(base_ms)))


# ── Row generator ─────────────────────────────────────────────────────────────

def _make_job(idx: int) -> Dict[str, Any]:
    algo     = random.choice(ALGORITHMS)
    provider = random.choice(PROVIDERS)
    priority = random.choices(PRIORITIES, weights=[5, 20, 55, 20])[0]
    profile  = ALGO_PROFILES[algo]

    n_qubits     = random.randint(*profile["qubits"])
    circuit_depth= random.randint(*profile["depth"])
    n_shots      = random.randint(*profile["shots"])
    month        = random.choice(MONTHS)

    # Assign a random day within the month
    year, mon = int(month[:4]), int(month[5:])
    day  = random.randint(1, 28)
    ts   = datetime(year, mon, day, random.randint(0, 23), random.randint(0, 59))

    # Cost
    cost_map = {
        "IBM":    _ibm_cost(n_qubits, n_shots),
        "AWS":    _aws_cost(n_shots),
        "Azure":  _azure_cost(n_shots),
        "Google": _google_cost(),
    }
    cost_usd = cost_map[provider]

    queue_time_s = _queue_time(provider, priority)
    run_time_s   = _run_time(n_qubits, n_shots, provider)
    success      = 1 if random.random() < 0.90 else 0

    return {
        "job_id":        f"JOB-{uuid.uuid4().hex[:10].upper()}",
        "algorithm":     algo,
        "n_qubits":      n_qubits,
        "circuit_depth": circuit_depth,
        "n_shots":       n_shots,
        "provider":      provider,
        "cost_usd":      cost_usd,
        "queue_time_s":  queue_time_s,
        "run_time_s":    run_time_s,
        "success":       success,
        "month":         month,
        "timestamp":     ts.isoformat(),
        "priority":      priority,
    }


# ── Monthly aggregation ───────────────────────────────────────────────────────

def _monthly_summary(jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_month: Dict[str, Dict[str, Any]] = {}
    for job in jobs:
        m = job["month"]
        if m not in by_month:
            by_month[m] = {"jobs": 0, "total_cost_usd": 0.0,
                           "success_count": 0, "providers": {}}
        rec = by_month[m]
        rec["jobs"] += 1
        rec["total_cost_usd"] = round(rec["total_cost_usd"] + job["cost_usd"], 4)
        rec["success_count"] += job["success"]
        p = job["provider"]
        rec["providers"][p] = rec["providers"].get(p, 0) + 1

    # Enrich
    for m, rec in by_month.items():
        rec["avg_cost_usd"] = round(rec["total_cost_usd"] / rec["jobs"], 4)
        rec["success_rate"] = round(rec["success_count"] / rec["jobs"], 4)

    return {"generated_at": datetime.utcnow().isoformat() + "Z",
            "n_jobs": N_JOBS, "months": by_month}


# ── Entry point ───────────────────────────────────────────────────────────────

def generate(n: int = N_JOBS) -> List[Dict[str, Any]]:
    """Generate n synthetic QPU jobs and write CSV + JSON."""
    jobs = [_make_job(i) for i in range(n)]

    # Write CSV
    fieldnames = list(jobs[0].keys())
    with open(JOBS_CSV, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(jobs)

    # Write monthly summary JSON
    summary = _monthly_summary(jobs)
    with open(MONTHLY_JSON, "w") as fh:
        json.dump(summary, fh, indent=2)

    print(f"[generate_data] Wrote {n} jobs → {JOBS_CSV}")
    print(f"[generate_data] Wrote monthly summary → {MONTHLY_JSON}")
    return jobs


if __name__ == "__main__":
    generate()
