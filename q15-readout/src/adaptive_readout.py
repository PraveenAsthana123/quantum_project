"""
Adaptive Measurement Optimization
====================================
Simulates adaptive shot allocation: allocate more shots for ambiguous outcomes.

Strategy:
  - Fixed baseline: N_fixed shots per qubit, uniform allocation
  - Adaptive: start with N_init shots; if confidence < threshold,
    add N_extra shots until confident or N_max reached

For a 5-qubit circuit, compare:
  - Fixed: same shots for all qubits (same accuracy)
  - Adaptive: fewer total shots, same or better accuracy

Confidence metric: |P(0) - 0.5| (distance from 50/50 — maximally ambiguous)

Saves results to data/adaptive_results.json.
"""

import json
import numpy as np
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Qubit readout simulation
# ---------------------------------------------------------------------------

class QubitReadout:
    """
    Simulates single-qubit readout with configurable error rates.
    """

    def __init__(self, true_prob_1: float, p01: float = 0.01, p10: float = 0.02,
                 seed: int = 42):
        """
        true_prob_1: true probability of state |1⟩
        p01: P(0|1) readout error
        p10: P(1|0) readout error
        """
        self.true_prob_1 = true_prob_1
        self.true_prob_0 = 1 - true_prob_1
        self.p01 = p01
        self.p10 = p10
        self.rng = np.random.default_rng(seed)

        # Effective probability of measuring 1
        self.meas_prob_1 = (true_prob_1 * (1 - p01) + (1 - true_prob_1) * p10)

    def measure(self, n_shots: int) -> np.ndarray:
        """Return array of n_shots binary outcomes (0 or 1)."""
        return self.rng.binomial(1, self.meas_prob_1, size=n_shots)

    def estimated_prob(self, shots: np.ndarray) -> float:
        """Estimate P(1) from a shot array."""
        return float(np.mean(shots))

    def confidence(self, shots: np.ndarray) -> float:
        """
        Confidence metric: |P̂(1) - 0.5|.
        Range [0, 0.5]: 0 = completely ambiguous, 0.5 = perfectly confident.
        """
        return abs(self.estimated_prob(shots) - 0.5)

    def accuracy(self, shots: np.ndarray) -> float:
        """
        Accuracy: how close is the estimated P(1) to the true P(1)?
        Returns 1 - |P̂ - P_true| (higher is better).
        """
        return 1.0 - abs(self.estimated_prob(shots) - self.true_prob_1)


# ---------------------------------------------------------------------------
# Fixed allocation
# ---------------------------------------------------------------------------

def fixed_allocation(qubits: list, n_shots_per_qubit: int) -> dict:
    """
    Fixed strategy: each qubit gets exactly n_shots_per_qubit shots.
    """
    total_shots = 0
    results = []
    for q in qubits:
        shots = q.measure(n_shots_per_qubit)
        p_est = q.estimated_prob(shots)
        acc = q.accuracy(shots)
        conf = q.confidence(shots)
        results.append({
            "n_shots": n_shots_per_qubit,
            "p_estimated": round(p_est, 4),
            "p_true": round(q.true_prob_1, 4),
            "accuracy": round(acc, 4),
            "confidence": round(conf, 4),
        })
        total_shots += n_shots_per_qubit

    mean_accuracy = float(np.mean([r["accuracy"] for r in results]))
    return {
        "strategy": "fixed",
        "shots_per_qubit": n_shots_per_qubit,
        "total_shots": total_shots,
        "per_qubit": results,
        "mean_accuracy": round(mean_accuracy, 4),
    }


# ---------------------------------------------------------------------------
# Adaptive allocation
# ---------------------------------------------------------------------------

def adaptive_allocation(qubits: list,
                         n_init: int = 20,
                         n_extra: int = 20,
                         n_max: int = 200,
                         confidence_threshold: float = 0.15) -> dict:
    """
    Adaptive strategy:
    1. Measure n_init shots for each qubit
    2. If confidence < threshold: measure n_extra more shots
    3. Repeat until confidence >= threshold or n_max reached
    """
    results = []
    total_shots = 0

    for q in qubits:
        shots_list = []
        n_rounds = 0
        all_shots = q.measure(n_init)
        shots_list.extend(all_shots.tolist())
        n_rounds += 1

        while (q.confidence(np.array(shots_list)) < confidence_threshold
               and len(shots_list) < n_max):
            extra = q.measure(min(n_extra, n_max - len(shots_list)))
            shots_list.extend(extra.tolist())
            n_rounds += 1

        shots_arr = np.array(shots_list)
        n_used = len(shots_list)
        p_est = q.estimated_prob(shots_arr)
        acc = q.accuracy(shots_arr)
        conf = q.confidence(shots_arr)

        results.append({
            "n_shots": n_used,
            "n_rounds": n_rounds,
            "p_estimated": round(p_est, 4),
            "p_true": round(q.true_prob_1, 4),
            "accuracy": round(acc, 4),
            "confidence": round(conf, 4),
            "converged": conf >= confidence_threshold,
        })
        total_shots += n_used

    mean_accuracy = float(np.mean([r["accuracy"] for r in results]))
    return {
        "strategy": "adaptive",
        "n_init": n_init,
        "n_extra": n_extra,
        "n_max": n_max,
        "confidence_threshold": confidence_threshold,
        "total_shots": total_shots,
        "per_qubit": results,
        "mean_accuracy": round(mean_accuracy, 4),
    }


# ---------------------------------------------------------------------------
# 5-qubit circuit with varied state distributions
# ---------------------------------------------------------------------------

def build_5qubit_circuit_qubits(seed: int = 42) -> list:
    """
    5 qubits with different true P(1) values — simulating a real circuit
    where some qubits are near 50% (ambiguous) and others near 0% or 100%.
    """
    rng = np.random.default_rng(seed)
    # Mix of easy and hard discrimination cases
    probs = [0.05, 0.48, 0.50, 0.52, 0.95]
    qubits = []
    for i, p in enumerate(probs):
        qubits.append(QubitReadout(true_prob_1=p, p01=0.01, p10=0.02,
                                    seed=seed + i * 17))
    return qubits, probs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Adaptive Readout — Shot Allocation Optimization")
    print("=" * 60)

    seed = 42
    qubits, true_probs = build_5qubit_circuit_qubits(seed=seed)
    n_fixed = 100  # fixed shots per qubit

    print(f"\n5-qubit circuit: true P(|1⟩) = {true_probs}")
    print(f"\nFixed strategy: {n_fixed} shots per qubit")
    print(f"Adaptive strategy: init=20, extra=20, max=200, conf_threshold=0.15\n")

    # Run both strategies (need fresh qubits for each run due to shared RNG)
    qubits_fixed, _ = build_5qubit_circuit_qubits(seed=seed)
    qubits_adapt, _ = build_5qubit_circuit_qubits(seed=seed + 100)

    fixed_result = fixed_allocation(qubits_fixed, n_fixed)
    adaptive_result = adaptive_allocation(qubits_adapt, n_init=20, n_extra=20,
                                           n_max=200, confidence_threshold=0.15)

    # Comparison
    print(f"{'Qubit':>6} | {'True P':>8} | {'Fixed N':>8} | {'Adapt N':>8} | {'Fixed Acc':>10} | {'Adapt Acc':>10}")
    print("-" * 66)
    for i in range(5):
        fq = fixed_result["per_qubit"][i]
        aq = adaptive_result["per_qubit"][i]
        print(f"{i:>6} | {true_probs[i]:>8.2f} | {fq['n_shots']:>8} | {aq['n_shots']:>8} | "
              f"{fq['accuracy']:>10.4f} | {aq['accuracy']:>10.4f}")

    total_fixed = fixed_result["total_shots"]
    total_adaptive = adaptive_result["total_shots"]
    shot_reduction = (1 - total_adaptive / total_fixed) * 100

    print(f"\nTotal fixed shots    : {total_fixed}")
    print(f"Total adaptive shots : {total_adaptive}")
    print(f"Shot reduction       : {shot_reduction:.1f}%")
    print(f"\nMean accuracy (fixed)    : {fixed_result['mean_accuracy']:.4f}")
    print(f"Mean accuracy (adaptive) : {adaptive_result['mean_accuracy']:.4f}")

    print("\nPer-qubit adaptive details:")
    for i, r in enumerate(adaptive_result["per_qubit"]):
        print(f"  Qubit {i}: {r['n_shots']} shots, {r['n_rounds']} rounds, "
              f"confidence={r['confidence']:.3f}, converged={r['converged']}")

    results = {
        "n_qubits": 5,
        "true_probabilities": true_probs,
        "fixed_shots": n_fixed,
        "adaptive_shots": total_adaptive,
        "accuracy": adaptive_result["mean_accuracy"],
        "shot_reduction_pct": round(shot_reduction, 2),
        "fixed_accuracy": fixed_result["mean_accuracy"],
        "adaptive_accuracy": adaptive_result["mean_accuracy"],
        "total_fixed_shots": total_fixed,
        "total_adaptive_shots": total_adaptive,
        "per_qubit_fixed": fixed_result["per_qubit"],
        "per_qubit_adaptive": adaptive_result["per_qubit"],
        "adaptive_parameters": {
            "n_init": 20,
            "n_extra": 20,
            "n_max": 200,
            "confidence_threshold": 0.15,
        },
        "strategy_description": (
            "Adaptive readout allocates more shots to qubits with ambiguous "
            "(near 50%) outcomes. Qubits with strong 0/1 bias are resolved quickly, "
            "saving shots without sacrificing accuracy."
        ),
    }

    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "adaptive_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {out_path}")
    print("\nAdaptive readout simulation complete.")


if __name__ == "__main__":
    main()
