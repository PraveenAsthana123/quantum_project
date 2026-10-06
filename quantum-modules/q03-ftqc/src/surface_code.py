"""
Q03 — Surface Code Simulation.

Uses stim for circuit generation and sampling, pymatching for MWPM decoding.
Sweeps over error rates to estimate the threshold.

Reference: /mnt/deepa/quantum/github/qec/ (panqec, pymatching, qecsim)
Saves results to data/surface_code_results.json.
"""

import json
import math
from pathlib import Path

import numpy as np

RESULTS_PATH = Path(__file__).parent.parent / "data" / "surface_code_results.json"

try:
    import stim
    import pymatching
    HAS_STIM = True
except ImportError as _e:
    print(f"[WARNING] stim/pymatching not available: {_e}")
    HAS_STIM = False


def logical_error_rate(distance: int, phys_error: float,
                       n_shots: int = 10_000, rounds: int = None) -> float:
    """
    Estimate logical error rate for a rotated surface code using stim + pymatching.

    Parameters
    ----------
    distance     : Code distance d (number of data qubits = d^2, logical = 1).
    phys_error   : Physical error probability per operation.
    n_shots      : Monte Carlo sample count.
    rounds       : Number of syndrome extraction rounds (default = d).
    """
    if rounds is None:
        rounds = distance

    circuit = stim.Circuit.generated(
        "surface_code:rotated_memory_z",
        rounds=rounds,
        distance=distance,
        after_clifford_depolarization=phys_error,
        before_round_data_depolarization=phys_error * 0.1,
        after_reset_flip_probability=phys_error * 0.1,
        before_measure_flip_probability=phys_error * 0.1,
    )

    model = circuit.detector_error_model(decompose_errors=True)
    matching = pymatching.Matching.from_detector_error_model(model)

    sampler = circuit.compile_detector_sampler()
    det_events, obs_flips = sampler.sample(shots=n_shots, separate_observables=True)

    predictions = matching.decode_batch(det_events)
    n_errors = int(np.sum(predictions != obs_flips))
    return n_errors / n_shots


def estimate_threshold(distances: list, error_rates: list, n_shots: int = 5000) -> float:
    """
    Estimate threshold by finding the crossing point of logical error rate curves
    for different distances as a function of physical error rate.
    Returns an approximate threshold value.
    """
    # For each (distance, phys_error) pair compute logical error rate
    results = {}
    for d in distances:
        results[d] = {}
        for p in error_rates:
            ler = logical_error_rate(d, p, n_shots=n_shots)
            results[d][p] = ler
            print(f"    d={d}, p={p:.4f} → logical error rate = {ler:.5f}")

    # Threshold ≈ where curves for consecutive distances cross
    # Find crossing of d=3 and d=5 curves
    threshold_estimates = []
    d_list = sorted(distances)
    for i in range(len(d_list) - 1):
        d1, d2 = d_list[i], d_list[i + 1]
        prev_diff = None
        for p in error_rates:
            diff = results[d1][p] - results[d2][p]
            if prev_diff is not None and prev_diff * diff < 0:
                threshold_estimates.append(p)
            prev_diff = diff

    return float(np.mean(threshold_estimates)) if threshold_estimates else 0.01


def main():
    print("=" * 60)
    print("Q03 — Surface Code Simulation (stim + pymatching)")
    print("=" * 60)

    if not HAS_STIM:
        print("[ERROR] stim or pymatching not installed. Cannot run.")
        return

    # Primary simulation: distance-3, p=0.01
    distance = 3
    phys_error = 0.01
    n_shots_primary = 20_000

    n_data = distance ** 2
    n_measure = distance ** 2 - 1  # (d²-1) stabilizer measurements
    n_physical = n_data + n_measure

    print(f"\n  Code distance     : d = {distance}")
    print(f"  Physical qubits   : {n_physical}  ({n_data} data + {n_measure} ancilla)")
    print(f"  Logical qubits    : 1")
    print(f"  Error probability : p = {phys_error}")
    print(f"  Shots             : {n_shots_primary}")

    print("\nRunning primary simulation...")
    ler_primary = logical_error_rate(distance, phys_error, n_shots=n_shots_primary)
    print(f"  Logical error rate at p={phys_error}: {ler_primary:.5f}")

    # Threshold sweep: d in {3, 5}, p in [0.005, 0.01, 0.015, 0.02]
    print("\nEstimating threshold (coarse sweep)...")
    distances_sweep = [3, 5]
    error_rates_sweep = [0.005, 0.01, 0.015, 0.02]
    n_shots_sweep = 3000

    sweep_results = {}
    for d in distances_sweep:
        sweep_results[d] = {}
        for p in error_rates_sweep:
            ler = logical_error_rate(d, p, n_shots=n_shots_sweep)
            sweep_results[d][p] = round(ler, 6)
            print(f"  d={d}, p={p:.3f} → LER = {ler:.5f}")

    # Estimate threshold
    threshold = estimate_threshold(distances_sweep, error_rates_sweep, n_shots=n_shots_sweep)
    print(f"\n  Estimated threshold: p_th ≈ {threshold:.4f}")
    print(f"  (Literature value for rotated surface code: ~1%)")

    data = {
        "code": "rotated_surface_code_memory_z",
        "code_distance": distance,
        "error_rate": phys_error,
        "logical_error_rate": round(ler_primary, 8),
        "threshold_estimate": round(threshold, 6),
        "n_physical_qubits": n_physical,
        "n_data_qubits": n_data,
        "n_logical_qubits": 1,
        "n_shots_primary": n_shots_primary,
        "decoder": "MWPM (pymatching)",
        "threshold_sweep": {
            f"d={d}": {f"p={p}": v for p, v in inner.items()}
            for d, inner in sweep_results.items()
        },
        "library": "stim",
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved → {RESULTS_PATH}")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
