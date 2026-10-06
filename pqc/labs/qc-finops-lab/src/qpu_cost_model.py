"""
QPU FinOps: Resource Cost Modeler
===================================
Purpose   : Model and optimize QPU job costs across cloud providers (IBM Quantum,
            AWS Braket, Azure Quantum, Google Cirq/internal).
Reference : IBM Quantum pricing model (Eagle $1.60/1000 shots, Heron $3.00/1000
            shots); AWS Braket per-task $0.30 + per-shot $0.00035; Azure Quantum
            IonQ $0.00003/gate, Quantinuum $0.065/shot; Google internal research
            queue penalty model.
Complexity: O(n_jobs × n_providers) for cost sweep; O(n_jobs) for monthly plan.

Providers modelled
------------------
  IBM Quantum   – Eagle r3 (127 q), Heron r2 (133 q); shot-based + task fee
  AWS Braket    – per-task flat + per-shot; IonQ/Rigetti/OQC back-ends
  Azure Quantum – IonQ gate-based; Quantinuum H2 shot-based
  Google Cirq   – internal research; $0/shot but stochastic queue penalty

Cost drivers captured
---------------------
  circuit_depth, n_qubits, n_shots, gate_count, error_rate →
  raw_cost_usd, latency_ms, queue_depth, fidelity_score

Usage
-----
    from qpu_cost_model import QPUJob, QPUCostModeler
    job = QPUJob(circuit_depth=20, n_qubits=10, n_shots=8192,
                 gate_count=120, error_rate=0.001)
    modeler = QPUCostModeler()
    estimates = modeler.compare_providers(job)
    for e in estimates:
        print(f"{e.provider}: ${e.cost_usd:.4f}  latency={e.latency_ms:.0f}ms")
"""
from __future__ import annotations

import math
import time
import json
import os
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class QPUJob:
    """Describes a single QPU job to be priced."""
    circuit_depth: int          # number of layers / moments
    n_qubits: int               # width of the circuit
    n_shots: int                # measurement repetitions
    gate_count: int             # total gate operations (single + two-qubit)
    error_rate: float           # physical gate error rate (0.001 = 0.1 %)
    two_qubit_fraction: float = 0.30   # fraction of gates that are 2-qubit
    algorithm_tag: str = "unknown"     # e.g. "VQE", "QAOA", "Grover"

    def __post_init__(self) -> None:
        if self.circuit_depth <= 0:
            raise ValueError("circuit_depth must be positive")
        if self.n_qubits < 1:
            raise ValueError("n_qubits must be >= 1")
        if self.n_shots < 1:
            raise ValueError("n_shots must be >= 1")
        if not (0.0 < self.error_rate < 1.0):
            raise ValueError("error_rate must be in (0, 1)")
        if not (0.0 <= self.two_qubit_fraction <= 1.0):
            raise ValueError("two_qubit_fraction must be in [0, 1]")

    @property
    def two_qubit_gates(self) -> int:
        return max(1, int(self.gate_count * self.two_qubit_fraction))

    @property
    def single_qubit_gates(self) -> int:
        return self.gate_count - self.two_qubit_gates

    def circuit_volume(self) -> int:
        """Quantum volume proxy: min(n_qubits, circuit_depth) ** 2."""
        return min(self.n_qubits, self.circuit_depth) ** 2


@dataclass
class CostEstimate:
    """Pricing result for a single provider + job combination."""
    provider: str
    backend: str
    cost_usd: float
    latency_ms: float           # wall-clock turnaround (queue + exec)
    queue_depth: int            # estimated jobs ahead in queue
    fidelity_score: float       # 0-1; estimated output fidelity
    breakdown: Dict[str, float] = field(default_factory=dict)
    notes: str = ""

    def __lt__(self, other: "CostEstimate") -> bool:   # for sorting
        return self.cost_usd < other.cost_usd

    def summary(self) -> str:
        return (
            f"{self.provider}/{self.backend}: ${self.cost_usd:.4f} USD  "
            f"latency={self.latency_ms:.0f} ms  fidelity={self.fidelity_score:.3f}"
        )


# ---------------------------------------------------------------------------
# Provider constants
# ---------------------------------------------------------------------------

# IBM Quantum 2024/2025 list pricing (USD)
IBM_EAGLE_SHOT_PRICE    = 1.60 / 1_000      # per shot on Eagle r3
IBM_HERON_SHOT_PRICE    = 3.00 / 1_000      # per shot on Heron r2
IBM_TASK_FEE            = 0.0               # no per-task fee on IBM
IBM_EAGLE_MAX_QUBITS    = 127
IBM_HERON_MAX_QUBITS    = 133
IBM_EAGLE_ERROR_RATE    = 0.0010            # typical 2-q gate error
IBM_HERON_ERROR_RATE    = 0.0005            # improved calibration

# AWS Braket 2024 list pricing (USD)
AWS_TASK_FEE            = 0.30              # per-task flat fee
AWS_SHOT_PRICE          = 0.00035          # per shot
AWS_SIMULATOR_TASK_FEE  = 0.075            # SV1 simulator per-task
AWS_SIMULATOR_SHOT_PRICE = 0.000175        # per shot on SV1
AWS_IONQ_GATE_PRICE     = 0.00003          # per gate on IonQ via Braket

# Azure Quantum (IonQ + Quantinuum) 2024 list pricing (USD)
AZURE_IONQ_GATE_PRICE   = 0.00003          # per gate operation
AZURE_IONQ_TASK_FEE     = 0.0
AZURE_QUANT_SHOT_PRICE  = 0.065            # Quantinuum H2 per shot
AZURE_QUANT_TASK_FEE    = 0.0

# Google Cirq / QPU research (internal; no public pricing)
GOOGLE_SHOT_PRICE       = 0.0              # research partner = free
GOOGLE_QUEUE_PENALTY_MS = 3600_000         # 1 hour avg stochastic wait

# Fidelity decay model: F_n = (1 - p_2q)^(n_2q) × (1 - p_1q)^(n_1q)
IBM_EAGLE_2Q_ERROR      = 0.0010
IBM_EAGLE_1Q_ERROR      = 0.0001
IBM_HERON_2Q_ERROR      = 0.0005
IBM_HERON_1Q_ERROR      = 0.00005
IONQ_2Q_ERROR           = 0.0050
IONQ_1Q_ERROR           = 0.0003
QUANTINUUM_2Q_ERROR     = 0.0020
QUANTINUUM_1Q_ERROR     = 0.0001
GOOGLE_2Q_ERROR         = 0.0015
GOOGLE_1Q_ERROR         = 0.00015


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _fidelity(job: QPUJob, two_q_err: float, one_q_err: float) -> float:
    """Estimate output state fidelity using independent depolarising error model."""
    f = (1.0 - two_q_err) ** job.two_qubit_gates
    f *= (1.0 - one_q_err) ** job.single_qubit_gates
    return max(0.0, min(1.0, f))


def _queue_latency_ibm(n_qubits: int, backend: str) -> Tuple[int, float]:
    """
    Heuristic IBM queue model based on qubit count and backend popularity.
    Returns (queue_depth, exec_latency_ms).
    """
    # Eagle is more popular → deeper queue; Heron is premium → shorter
    base_queue = 40 if backend == "Eagle" else 12
    exec_us_per_shot = 0.1 + 0.002 * n_qubits   # microseconds per shot
    # execution in ms (shots × us/shot / 1000)
    return base_queue, exec_us_per_shot


def _exec_latency_ms(job: QPUJob, exec_us_per_shot: float,
                     queue_depth: int, avg_job_exec_ms: float = 250.0) -> float:
    """Total wall-clock latency = queue wait + execution."""
    exec_ms = job.n_shots * exec_us_per_shot / 1_000.0
    queue_wait_ms = queue_depth * avg_job_exec_ms
    return queue_wait_ms + exec_ms


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class QPUCostModeler:
    """
    Estimates QPU job costs across multiple cloud quantum providers and
    provides budget planning and optimisation recommendations.
    """

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self._history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Provider estimators
    # ------------------------------------------------------------------

    def estimate_ibm_quantum(self, job: QPUJob) -> CostEstimate:
        """
        IBM Quantum pricing for Eagle r3 or Heron r2.

        Pricing model (2024):
          Eagle r3:  $1.60 / 1000 shots, max 127 qubits
          Heron r2:  $3.00 / 1000 shots, max 133 qubits
        Backend selection: use Heron if job.n_qubits > 65 or error_rate < 0.0006.
        """
        use_heron = (job.n_qubits > 65) or (job.error_rate < IBM_HERON_ERROR_RATE * 1.5)
        if use_heron:
            backend = "Heron_r2"
            shot_price = IBM_HERON_SHOT_PRICE
            two_q_err, one_q_err = IBM_HERON_2Q_ERROR, IBM_HERON_1Q_ERROR
            base_queue, exec_us = 12, 0.08 + 0.0015 * job.n_qubits
            max_q = IBM_HERON_MAX_QUBITS
        else:
            backend = "Eagle_r3"
            shot_price = IBM_EAGLE_SHOT_PRICE
            two_q_err, one_q_err = IBM_EAGLE_2Q_ERROR, IBM_EAGLE_1Q_ERROR
            base_queue, exec_us = 40, 0.10 + 0.002 * job.n_qubits
            max_q = IBM_EAGLE_MAX_QUBITS

        if job.n_qubits > max_q:
            return CostEstimate(
                provider="IBM_Quantum", backend=backend,
                cost_usd=float("inf"), latency_ms=float("inf"),
                queue_depth=0, fidelity_score=0.0,
                notes=f"Job requires {job.n_qubits} qubits; {backend} max={max_q}"
            )

        shot_cost = job.n_shots * shot_price
        task_fee = IBM_TASK_FEE
        total_cost = shot_cost + task_fee

        fid = _fidelity(job, two_q_err, one_q_err)
        latency = _exec_latency_ms(job, exec_us, base_queue)

        breakdown = {
            "shot_cost_usd": round(shot_cost, 6),
            "task_fee_usd": task_fee,
            "total_usd": round(total_cost, 6),
        }
        est = CostEstimate(
            provider="IBM_Quantum", backend=backend,
            cost_usd=round(total_cost, 6),
            latency_ms=round(latency, 1),
            queue_depth=base_queue,
            fidelity_score=round(fid, 6),
            breakdown=breakdown,
            notes=f"Shot-based pricing; {job.n_shots} shots × ${shot_price:.5f}"
        )
        self._record(job, est)
        return est

    def estimate_aws_braket(self, job: QPUJob) -> CostEstimate:
        """
        AWS Braket pricing model (2024):
          Per-task fee: $0.30 (hardware)
          Per-shot fee: $0.00035
          IonQ alternative: $0.00003/gate (min 1 qubit)
        Chooses cheaper of shot-based vs IonQ-gate-based for the given job.
        """
        # Shot-based QPU (Rigetti / OQC)
        shot_cost = job.n_shots * AWS_SHOT_PRICE
        task_fee = AWS_TASK_FEE
        shot_total = shot_cost + task_fee

        # IonQ gate-based alternative available via Braket
        ionq_gate_cost = job.gate_count * AWS_IONQ_GATE_PRICE
        ionq_total = ionq_gate_cost + task_fee   # same task fee

        if ionq_gate_cost < shot_total:
            backend = "IonQ_via_Braket"
            cost = round(ionq_total, 6)
            two_q_err, one_q_err = IONQ_2Q_ERROR, IONQ_1Q_ERROR
            queue_depth = 8
            exec_us = 0.50
            breakdown = {
                "ionq_gate_cost_usd": round(ionq_gate_cost, 6),
                "task_fee_usd": task_fee,
                "total_usd": cost,
            }
            notes = f"IonQ gate model; {job.gate_count} gates × ${AWS_IONQ_GATE_PRICE}"
        else:
            backend = "Rigetti_Aspen_M3"
            cost = round(shot_total, 6)
            two_q_err, one_q_err = 0.0200, 0.0030   # Rigetti typical errors
            queue_depth = 15
            exec_us = 0.30
            breakdown = {
                "task_fee_usd": task_fee,
                "shot_cost_usd": round(shot_cost, 6),
                "total_usd": cost,
            }
            notes = f"Shot-based; {job.n_shots} shots × ${AWS_SHOT_PRICE} + ${task_fee} task"

        fid = _fidelity(job, two_q_err, one_q_err)
        latency = _exec_latency_ms(job, exec_us, queue_depth)

        est = CostEstimate(
            provider="AWS_Braket", backend=backend,
            cost_usd=cost, latency_ms=round(latency, 1),
            queue_depth=queue_depth, fidelity_score=round(fid, 6),
            breakdown=breakdown, notes=notes
        )
        self._record(job, est)
        return est

    def estimate_azure_quantum(self, job: QPUJob) -> CostEstimate:
        """
        Azure Quantum pricing (2024):
          IonQ Aria/Forte: $0.00003/gate operation
          Quantinuum H2:   $0.065/shot
        Chooses based on whether shot-count or gate-count is the dominant cost driver.
        """
        # IonQ via Azure (gate-based)
        ionq_cost = job.gate_count * AZURE_IONQ_GATE_PRICE
        ionq_total = ionq_cost + AZURE_IONQ_TASK_FEE

        # Quantinuum H2 (shot-based; very accurate, very expensive)
        quant_cost = job.n_shots * AZURE_QUANT_SHOT_PRICE
        quant_total = quant_cost + AZURE_QUANT_TASK_FEE

        if ionq_total <= quant_total:
            backend = "IonQ_Forte"
            cost = round(ionq_total, 6)
            two_q_err, one_q_err = IONQ_2Q_ERROR, IONQ_1Q_ERROR
            queue_depth = 6
            exec_us = 0.40
            breakdown = {
                "gate_cost_usd": round(ionq_cost, 6),
                "task_fee_usd": AZURE_IONQ_TASK_FEE,
                "total_usd": cost,
            }
            notes = f"IonQ Forte; {job.gate_count} gates × ${AZURE_IONQ_GATE_PRICE}"
        else:
            backend = "Quantinuum_H2"
            cost = round(quant_total, 6)
            two_q_err, one_q_err = QUANTINUUM_2Q_ERROR, QUANTINUUM_1Q_ERROR
            queue_depth = 3    # premium capacity, shorter queue
            exec_us = 1.50     # trapped-ion is slower per shot
            breakdown = {
                "shot_cost_usd": round(quant_cost, 6),
                "task_fee_usd": AZURE_QUANT_TASK_FEE,
                "total_usd": cost,
            }
            notes = f"Quantinuum H2; {job.n_shots} shots × ${AZURE_QUANT_SHOT_PRICE}"

        fid = _fidelity(job, two_q_err, one_q_err)
        latency = _exec_latency_ms(job, exec_us, queue_depth, avg_job_exec_ms=600.0)

        est = CostEstimate(
            provider="Azure_Quantum", backend=backend,
            cost_usd=cost, latency_ms=round(latency, 1),
            queue_depth=queue_depth, fidelity_score=round(fid, 6),
            breakdown=breakdown, notes=notes
        )
        self._record(job, est)
        return est

    def estimate_google_cirq(self, job: QPUJob) -> CostEstimate:
        """
        Google Quantum AI / Cirq — internal research partner pricing.
        Cost = $0/shot but stochastic queue penalty applies.
        Queue model: log-normal distribution with μ=ln(3600s), σ=0.8.
        Jobs > 72 qubits routed to Willow (105 q); otherwise Sycamore (54 q).
        """
        SYCAMORE_MAX_Q = 54
        WILLOW_MAX_Q   = 105

        if job.n_qubits > WILLOW_MAX_Q:
            return CostEstimate(
                provider="Google_Cirq", backend="N/A",
                cost_usd=float("inf"), latency_ms=float("inf"),
                queue_depth=0, fidelity_score=0.0,
                notes=f"{job.n_qubits} qubits exceeds Willow max ({WILLOW_MAX_Q})"
            )

        backend = "Willow" if job.n_qubits > SYCAMORE_MAX_Q else "Sycamore"
        two_q_err, one_q_err = GOOGLE_2Q_ERROR, GOOGLE_1Q_ERROR

        # Stochastic wait: sample from log-normal to get expected queue wait
        rng = np.random.default_rng(seed=hash(job.circuit_depth + job.n_qubits) % 2**32)
        queue_wait_s = rng.lognormal(mean=math.log(3600), sigma=0.8)
        exec_us = 0.05 + 0.001 * job.n_qubits
        exec_ms = job.n_shots * exec_us / 1_000.0
        latency_ms = queue_wait_s * 1_000.0 + exec_ms

        # Approximate queue depth from wait time / avg_job_time
        avg_job_ms = 200.0
        queue_depth = max(1, int(queue_wait_s * 1000.0 / avg_job_ms))

        fid = _fidelity(job, two_q_err, one_q_err)

        breakdown = {
            "compute_cost_usd": 0.0,
            "queue_wait_s": round(queue_wait_s, 1),
            "exec_ms": round(exec_ms, 3),
        }
        est = CostEstimate(
            provider="Google_Cirq", backend=backend,
            cost_usd=0.0, latency_ms=round(latency_ms, 1),
            queue_depth=queue_depth, fidelity_score=round(fid, 6),
            breakdown=breakdown,
            notes="Research partner pricing; stochastic queue delay applies"
        )
        self._record(job, est)
        return est

    # ------------------------------------------------------------------
    # Aggregated / planning methods
    # ------------------------------------------------------------------

    def compare_providers(self, job: QPUJob) -> List[CostEstimate]:
        """
        Run cost estimates across all four providers and return sorted by
        cost_usd ascending (inf = infeasible at end).
        """
        estimates = [
            self.estimate_ibm_quantum(job),
            self.estimate_aws_braket(job),
            self.estimate_azure_quantum(job),
            self.estimate_google_cirq(job),
        ]
        feasible   = [e for e in estimates if math.isfinite(e.cost_usd)]
        infeasible = [e for e in estimates if not math.isfinite(e.cost_usd)]
        feasible.sort()
        return feasible + infeasible

    def monthly_budget_plan(
        self,
        jobs_per_day: float,
        budget_usd: float,
        representative_job: Optional[QPUJob] = None
    ) -> Dict[str, Any]:
        """
        Project monthly spend and provider utilisation for a given workload.

        Parameters
        ----------
        jobs_per_day     : average QPU jobs submitted per calendar day
        budget_usd       : total monthly budget in USD
        representative_job : job used for unit cost; defaults to a modest VQE job

        Returns
        -------
        dict with keys: monthly_jobs, cheapest_provider, provider_breakdown,
                        utilisation_pct, budget_surplus_usd, recommendation
        """
        if representative_job is None:
            representative_job = QPUJob(
                circuit_depth=15, n_qubits=12, n_shots=4096,
                gate_count=80, error_rate=0.001, algorithm_tag="VQE_default"
            )

        DAYS_PER_MONTH = 30.44
        monthly_jobs = jobs_per_day * DAYS_PER_MONTH

        estimates = self.compare_providers(representative_job)
        feasible = [e for e in estimates if math.isfinite(e.cost_usd)]

        breakdown: Dict[str, Any] = {}
        for est in feasible:
            monthly_cost = est.cost_usd * monthly_jobs
            utilisation  = min(1.0, budget_usd / monthly_cost) if monthly_cost > 0 else 1.0
            breakdown[f"{est.provider}/{est.backend}"] = {
                "unit_cost_usd":      round(est.cost_usd, 6),
                "monthly_total_usd":  round(monthly_cost, 2),
                "monthly_jobs_feasible": int(budget_usd / est.cost_usd) if est.cost_usd > 0 else int(1e9),
                "utilisation_pct":    round(utilisation * 100, 1),
                "fidelity_score":     est.fidelity_score,
            }

        cheapest = feasible[0] if feasible else None
        monthly_spend = cheapest.cost_usd * monthly_jobs if cheapest else float("inf")
        surplus = budget_usd - monthly_spend

        return {
            "monthly_jobs":         round(monthly_jobs),
            "jobs_per_day":         jobs_per_day,
            "budget_usd":           budget_usd,
            "cheapest_provider":    f"{cheapest.provider}/{cheapest.backend}" if cheapest else "N/A",
            "cheapest_unit_cost":   round(cheapest.cost_usd, 6) if cheapest else None,
            "projected_spend_usd":  round(monthly_spend, 2),
            "budget_surplus_usd":   round(surplus, 2),
            "provider_breakdown":   breakdown,
            "recommendation":       self._budget_recommendation(surplus, budget_usd, cheapest),
        }

    def circuit_cost_optimization(self, job: QPUJob) -> Dict[str, Any]:
        """
        Analyse a job and suggest concrete optimisations that reduce cost.

        Strategies considered
        ---------------------
        1. Shot count reduction  – Chebyshev bound for target precision ε
        2. Circuit depth compression – parallelize single-qubit layers
        3. Provider arbitrage    – switch to cheapest feasible provider
        4. Simulator offloading  – use SV1 for small circuits
        5. Batch discounting     – combine small jobs into a single task

        Returns a dict with each suggestion, its estimated savings, and
        the resulting modified job parameters.
        """
        base_estimates = self.compare_providers(job)
        cheapest_base  = next((e for e in base_estimates if math.isfinite(e.cost_usd)), None)
        base_cost      = cheapest_base.cost_usd if cheapest_base else float("inf")

        suggestions: List[Dict[str, Any]] = []

        # 1. Shot reduction: Chebyshev ε=0.05 → shots_needed = 1/(2ε²)
        eps = 0.05
        min_shots_chebyshev = math.ceil(1.0 / (2 * eps ** 2))
        if job.n_shots > min_shots_chebyshev:
            reduced_job = QPUJob(
                circuit_depth=job.circuit_depth, n_qubits=job.n_qubits,
                n_shots=min_shots_chebyshev, gate_count=job.gate_count,
                error_rate=job.error_rate, two_qubit_fraction=job.two_qubit_fraction
            )
            r_est = self.compare_providers(reduced_job)
            r_cost = next((e.cost_usd for e in r_est if math.isfinite(e.cost_usd)), base_cost)
            savings = base_cost - r_cost
            if savings > 0:
                suggestions.append({
                    "strategy": "shot_reduction",
                    "description": (
                        f"Reduce shots {job.n_shots} → {min_shots_chebyshev} "
                        f"(Chebyshev ε=5% guarantee)"
                    ),
                    "new_shots":         min_shots_chebyshev,
                    "savings_usd":       round(savings, 6),
                    "savings_pct":       round(100 * savings / base_cost, 1) if base_cost else 0,
                })

        # 2. Depth compression via gate parallelization (heuristic: 20% reduction)
        PARALLELIZATION_GAIN = 0.20
        compressed_depth = max(1, int(job.circuit_depth * (1 - PARALLELIZATION_GAIN)))
        compressed_gates  = max(1, int(job.gate_count  * (1 - PARALLELIZATION_GAIN * 0.5)))
        if compressed_depth < job.circuit_depth:
            # depth doesn't directly lower cost on shot-based providers,
            # but reduces gate count → lower Azure/IonQ cost
            compressed_job = QPUJob(
                circuit_depth=compressed_depth, n_qubits=job.n_qubits,
                n_shots=job.n_shots, gate_count=compressed_gates,
                error_rate=job.error_rate, two_qubit_fraction=job.two_qubit_fraction
            )
            c_est = self.compare_providers(compressed_job)
            c_cost = next((e.cost_usd for e in c_est if math.isfinite(e.cost_usd)), base_cost)
            savings = base_cost - c_cost
            suggestions.append({
                "strategy": "circuit_compression",
                "description": (
                    f"Parallelize gates: depth {job.circuit_depth} → {compressed_depth}, "
                    f"gates {job.gate_count} → {compressed_gates}"
                ),
                "new_depth":         compressed_depth,
                "new_gate_count":    compressed_gates,
                "savings_usd":       round(max(0, savings), 6),
                "savings_pct":       round(100 * max(0, savings) / base_cost, 1) if base_cost else 0,
            })

        # 3. AWS simulator for small circuits (≤ 24 qubits, depth ≤ 30)
        if job.n_qubits <= 24 and job.circuit_depth <= 30:
            sim_task = AWS_SIMULATOR_TASK_FEE
            sim_shot = job.n_shots * AWS_SIMULATOR_SHOT_PRICE
            sim_cost = round(sim_task + sim_shot, 6)
            savings  = base_cost - sim_cost
            suggestions.append({
                "strategy": "simulator_offload",
                "description": (
                    f"Use AWS SV1 simulator (circuit ≤24q ≤depth 30): "
                    f"${sim_task} task + {job.n_shots}×${AWS_SIMULATOR_SHOT_PRICE}"
                ),
                "sim_cost_usd":  sim_cost,
                "savings_usd":   round(max(0, savings), 6),
                "savings_pct":   round(100 * max(0, savings) / base_cost, 1) if base_cost else 0,
                "caveat":        "Noiseless simulation; no fidelity degradation"
            })

        # 4. Provider arbitrage summary
        if len(base_estimates) >= 2:
            most_expensive = max(
                (e for e in base_estimates if math.isfinite(e.cost_usd)),
                key=lambda e: e.cost_usd, default=None
            )
            if most_expensive and cheapest_base and most_expensive.provider != cheapest_base.provider:
                arbitrage_savings = most_expensive.cost_usd - cheapest_base.cost_usd
                suggestions.append({
                    "strategy": "provider_arbitrage",
                    "description": (
                        f"Switch from {most_expensive.provider} "
                        f"(${most_expensive.cost_usd:.4f}) to "
                        f"{cheapest_base.provider} (${cheapest_base.cost_usd:.4f})"
                    ),
                    "savings_usd": round(arbitrage_savings, 6),
                    "savings_pct": round(
                        100 * arbitrage_savings / most_expensive.cost_usd, 1
                    ) if most_expensive.cost_usd else 0,
                })

        suggestions.sort(key=lambda s: s.get("savings_usd", 0), reverse=True)

        return {
            "job_summary": {
                "circuit_depth": job.circuit_depth,
                "n_qubits":      job.n_qubits,
                "n_shots":       job.n_shots,
                "gate_count":    job.gate_count,
                "algorithm_tag": job.algorithm_tag,
            },
            "base_cost_usd":      round(base_cost, 6),
            "cheapest_provider":  cheapest_base.provider if cheapest_base else "N/A",
            "suggestions":        suggestions,
            "max_savings_usd":    round(sum(s.get("savings_usd", 0) for s in suggestions), 6),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record(self, job: QPUJob, est: CostEstimate) -> None:
        if self.verbose:
            self._history.append({
                "timestamp": time.time(),
                "job":       job.__dict__,
                "estimate":  {
                    "provider":       est.provider,
                    "backend":        est.backend,
                    "cost_usd":       est.cost_usd,
                    "latency_ms":     est.latency_ms,
                    "fidelity_score": est.fidelity_score,
                },
            })

    def _budget_recommendation(
        self,
        surplus: float,
        budget: float,
        cheapest: Optional[CostEstimate],
    ) -> str:
        if cheapest is None:
            return "No feasible provider for the given job parameters."
        # When cheapest provider has $0 cost (Google research), spending is
        # always within budget regardless of volume.
        if cheapest.cost_usd == 0.0:
            return (
                f"{cheapest.provider} has no per-job charge (research partner). "
                f"Budget is effectively unlimited for this provider; "
                f"queue latency is the binding constraint."
            )
        util = 1.0 - (surplus / budget) if budget else 1.0
        if surplus < 0:
            overage_pct = abs(surplus) / budget * 100
            return (
                f"Budget exceeded by {overage_pct:.1f}%. "
                f"Consider reducing shots or using {cheapest.provider} exclusively."
            )
        if util > 0.85:
            return (
                f"Budget {util*100:.0f}% utilised. Healthy workload on "
                f"{cheapest.provider}/{cheapest.backend}."
            )
        if util <= 0:
            return (
                f"{cheapest.provider} has zero cost; budget fully available. "
                f"Queue latency is the only constraint."
            )
        return (
            f"Budget only {util*100:.0f}% utilised. "
            f"You can increase throughput by {1/util:.1f}× within budget."
        )

    def get_history(self) -> List[Dict[str, Any]]:
        """Return the full pricing history (only populated when verbose=True)."""
        return list(self._history)
