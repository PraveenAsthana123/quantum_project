"""
backend_selector.py — QPU backend selection logic for Q07
Scores 5 simulated backends by qubit count, error rate, queue time, and cost.
Selects optimal backend for a given circuit requirement.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional


@dataclass
class BackendSpec:
    name: str
    provider: str
    qubit_count: int
    cx_error_rate: float       # average 2-qubit gate error (0-1)
    readout_error: float       # measurement error (0-1)
    queue_time_min: float      # estimated queue wait in minutes
    cost_per_shot: float       # USD per shot
    max_shots: int
    basis_gates: List[str]
    connectivity: str          # "all-to-all" | "linear" | "heavy-hex" | "ring"


# 5 simulated backends representative of real cloud QPU offerings
BACKENDS = [
    BackendSpec(
        name="ibm_falcon_r5",
        provider="IBM",
        qubit_count=27,
        cx_error_rate=0.008,
        readout_error=0.018,
        queue_time_min=5.0,
        cost_per_shot=0.00,     # IBM free tier
        max_shots=20000,
        basis_gates=["cx", "id", "rz", "sx", "x"],
        connectivity="heavy-hex",
    ),
    BackendSpec(
        name="ibm_eagle_r3",
        provider="IBM",
        qubit_count=127,
        cx_error_rate=0.006,
        readout_error=0.012,
        queue_time_min=25.0,
        cost_per_shot=0.00,
        max_shots=20000,
        basis_gates=["cx", "id", "rz", "sx", "x", "ecr"],
        connectivity="heavy-hex",
    ),
    BackendSpec(
        name="ionq_harmony",
        provider="IonQ",
        qubit_count=11,
        cx_error_rate=0.004,
        readout_error=0.005,
        queue_time_min=60.0,
        cost_per_shot=0.00097,   # $0.00097 per task gate-shot
        max_shots=10000,
        basis_gates=["xx", "ry", "rz", "x", "y", "z", "h", "s", "t", "cnot"],
        connectivity="all-to-all",
    ),
    BackendSpec(
        name="rigetti_aspen_m3",
        provider="Rigetti",
        qubit_count=79,
        cx_error_rate=0.025,
        readout_error=0.030,
        queue_time_min=15.0,
        cost_per_shot=0.00035,
        max_shots=100000,
        basis_gates=["cz", "rx", "rz", "xy", "measure"],
        connectivity="ring",
    ),
    BackendSpec(
        name="aws_sv1_simulator",
        provider="AWS",
        qubit_count=34,
        cx_error_rate=0.0,       # ideal simulator
        readout_error=0.0,
        queue_time_min=0.5,
        cost_per_shot=0.00035,   # $0.00035/task + $0.000145/shot
        max_shots=100000,
        basis_gates=["all"],
        connectivity="all-to-all",
    ),
]


@dataclass
class CircuitRequirement:
    n_qubits: int
    circuit_depth: int
    n_shots: int
    prefer_real_qpu: bool = True
    budget_usd: Optional[float] = None


def score_backend(backend: BackendSpec, req: CircuitRequirement) -> Dict:
    """
    Score a backend for a given circuit requirement.
    Returns a dict with sub-scores and total weighted score (higher = better).

    Scoring dimensions (each 0-1, then weighted):
    - qubit_fit: does it have enough qubits?
    - error_quality: lower error = higher score
    - queue_score: shorter queue = higher score
    - cost_score: lower cost = higher score
    """
    # Qubit fit: must have >= required qubits; bonus for headroom
    if backend.qubit_count < req.n_qubits:
        return {
            "backend": backend.name,
            "eligible": False,
            "reason": f"Insufficient qubits: {backend.qubit_count} < {req.n_qubits}",
            "total_score": -1.0,
        }

    # Check shot capacity
    if backend.max_shots < req.n_shots:
        return {
            "backend": backend.name,
            "eligible": False,
            "reason": f"Max shots {backend.max_shots} < requested {req.n_shots}",
            "total_score": -1.0,
        }

    # Budget check
    total_cost = backend.cost_per_shot * req.n_shots
    if req.budget_usd is not None and total_cost > req.budget_usd:
        return {
            "backend": backend.name,
            "eligible": False,
            "reason": f"Cost ${total_cost:.4f} exceeds budget ${req.budget_usd:.2f}",
            "total_score": -1.0,
        }

    # Simulator penalty if real QPU preferred
    is_simulator = "simulator" in backend.name.lower()
    if req.prefer_real_qpu and is_simulator:
        sim_penalty = 0.3
    else:
        sim_penalty = 0.0

    # Qubit fit score: 1.0 if exactly fits, decays slowly with excess
    qubit_ratio = req.n_qubits / backend.qubit_count
    qubit_score = min(1.0, qubit_ratio + 0.2)  # prefer backends that are not overkill

    # Error quality score: invert the combined error
    combined_error = backend.cx_error_rate * 0.7 + backend.readout_error * 0.3
    error_score = max(0.0, 1.0 - combined_error * 20)  # scale: 5% error -> score 0

    # Queue score: 0 min -> 1.0, 120 min -> 0.0
    queue_score = max(0.0, 1.0 - backend.queue_time_min / 120.0)

    # Cost score: $0 -> 1.0, $1 (for this run) -> 0.0
    cost_score = max(0.0, 1.0 - total_cost / 1.0)

    # Weights
    w_qubit, w_error, w_queue, w_cost = 0.20, 0.40, 0.25, 0.15
    total_score = (
        w_qubit * qubit_score
        + w_error * error_score
        + w_queue * queue_score
        + w_cost * cost_score
        - sim_penalty
    )

    return {
        "backend": backend.name,
        "provider": backend.provider,
        "eligible": True,
        "is_simulator": is_simulator,
        "qubit_count": backend.qubit_count,
        "cx_error_rate": backend.cx_error_rate,
        "queue_time_min": backend.queue_time_min,
        "total_cost_usd": round(total_cost, 6),
        "qubit_score": round(qubit_score, 3),
        "error_score": round(error_score, 3),
        "queue_score": round(queue_score, 3),
        "cost_score": round(cost_score, 3),
        "total_score": round(total_score, 4),
    }


def select_backend(req: CircuitRequirement) -> Dict:
    """Score all backends and return the best match with full score matrix."""
    score_matrix = [score_backend(b, req) for b in BACKENDS]
    eligible = [s for s in score_matrix if s["eligible"]]

    if not eligible:
        return {
            "circuit_qubits": req.n_qubits,
            "circuit_depth": req.circuit_depth,
            "selected_backend": None,
            "reason": "No eligible backends found for this circuit requirement",
            "score_matrix": score_matrix,
        }

    best = max(eligible, key=lambda s: s["total_score"])

    return {
        "circuit_qubits": req.n_qubits,
        "circuit_depth": req.circuit_depth,
        "n_shots": req.n_shots,
        "selected_backend": best["backend"],
        "selected_provider": best["provider"],
        "reason": (
            f"Highest composite score {best['total_score']:.4f}: "
            f"error_rate={best['cx_error_rate']}, "
            f"queue={best['queue_time_min']}min, "
            f"cost=${best['total_cost_usd']:.4f}"
        ),
        "score_matrix": score_matrix,
    }


def main():
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "backend_selection.json")

    # Example: 5-qubit circuit, depth 20, 8192 shots, prefer real QPU
    req = CircuitRequirement(
        n_qubits=5,
        circuit_depth=20,
        n_shots=8192,
        prefer_real_qpu=True,
        budget_usd=5.0,
    )

    print("=== Q07 Backend Selector ===")
    print(f"Circuit: {req.n_qubits} qubits, depth={req.circuit_depth}, shots={req.n_shots}")
    print(f"Prefer real QPU: {req.prefer_real_qpu}, Budget: ${req.budget_usd}")
    print()

    results = select_backend(req)

    print("Score Matrix:")
    print(f"{'Backend':<22} {'Eligible':<9} {'Q.Score':<9} {'Err.Score':<11} {'Queue':<8} {'Cost':<8} {'Total':<8}")
    print("-" * 80)
    for s in results["score_matrix"]:
        if s["eligible"]:
            print(
                f"{s['backend']:<22} {'YES':<9} {s['qubit_score']:<9.3f} "
                f"{s['error_score']:<11.3f} {s['queue_score']:<8.3f} "
                f"{s['cost_score']:<8.3f} {s['total_score']:<8.4f}"
            )
        else:
            print(f"{s['backend']:<22} {'NO':<9} -- {s['reason']}")

    print(f"\nSelected: {results['selected_backend']}")
    print(f"Reason: {results['reason']}")

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
    return results


if __name__ == "__main__":
    main()
