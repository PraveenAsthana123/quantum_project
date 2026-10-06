"""
Q27 — Quantum Clocks
clock_synchronization.py

Quantum clock synchronization using entanglement.
Two nodes share N Bell pairs for time transfer.
Compares classical GPS (ns accuracy) vs quantum (ps accuracy).
Calculates synchronization accuracy vs N entangled pairs.

Reference: Jozsa et al., PRL 85, 2010 (2000);
           Giovannetti, Lloyd & Maccone, Nature 412, 417 (2001).

Outputs: data/sync_results.json
"""

import json
import math
import os
import random


# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

C_MS = 3.0e8        # speed of light in vacuum [m/s]
C_FIBER = 2.0e8     # speed of light in fibre [m/s]


# ---------------------------------------------------------------------------
# Classical synchronisation
# ---------------------------------------------------------------------------

def gps_accuracy_ns(n_satellites: int = 4,
                     ionospheric_correction: bool = True) -> float:
    """
    GPS clock synchronisation accuracy.
    Single-frequency: ~10–30 ns.
    Dual-frequency (ionospheric corrected): ~1–5 ns.
    Two-way satellite time transfer (TWSTT): ~0.3 ns.
    """
    if ionospheric_correction:
        base_ns = 2.0   # dual-frequency corrected
    else:
        base_ns = 15.0  # single-frequency
    # Improve slightly with more satellites (redundant averaging)
    return base_ns / math.sqrt(max(n_satellites, 1) / 4.0)


def classical_fiber_sync_ns(distance_km: float,
                              temperature_stability_C: float = 0.1) -> float:
    """
    Classical fibre-based synchronisation.
    Thermal expansion: ~40 ppm/°C → path length variation.
    1 km of fibre: ~0.2 ns delay instability per °C.
    Returns timing uncertainty in ns.
    """
    delay_ns_per_km_per_C = 0.2
    return delay_ns_per_km_per_C * distance_km * temperature_stability_C


# ---------------------------------------------------------------------------
# Quantum clock synchronisation
# ---------------------------------------------------------------------------

def quantum_sync_accuracy_ps(n_pairs: int,
                               t_coherence_us: float = 100.0,
                               clock_accuracy: float = 1e-17) -> float:
    """
    Quantum synchronisation accuracy via entangled pairs.

    Protocol (Giovannetti et al. 2001):
    - N entangled pairs → effective "tick" frequency scales as N
    - Timing resolution: Δt ≈ 1 / (N * ν_clock)  where ν_clock ≈ 1 PHz optical
    - Practical limit: coherence time T_2

    Δt_quantum = T_coherence * accuracy / (N * base_precision_factor)
    Simple model: Δt ∝ 1/N improvement.

    Returns accuracy in picoseconds.
    """
    # Base quantum timing: limited by optical clock frequency
    nu_optical = 4e14  # Hz (optical clock ~400 THz → 2.5 fs per tick)
    base_accuracy_s = 1.0 / (nu_optical * math.sqrt(max(n_pairs, 1)))

    # Degraded by coherence time limitation
    t_coh_s = t_coherence_us * 1e-6
    coherence_limited_s = base_accuracy_s * max(1.0, 1e-6 / t_coh_s)

    return coherence_limited_s * 1e12  # convert to ps


def entanglement_overhead(n_pairs: int,
                           generation_rate_Hz: float = 1e6,
                           distance_km: float = 100.0) -> dict:
    """
    Overhead for distributing N entangled pairs between two nodes.
    Returns time needed and resource cost.
    """
    # Fibre transmission at 1550 nm: η = 10^(-0.2*km/10)
    eta = 10 ** (-0.2 * distance_km / 10.0)
    p_pair = 0.1 * eta ** 2 * 0.85 ** 2  # pair_prob * fiber^2 * detector^2
    effective_rate = generation_rate_Hz * p_pair
    time_s = n_pairs / max(effective_rate, 1e-12)
    return {
        "n_pairs": n_pairs,
        "effective_rate_Hz": round(effective_rate, 4),
        "time_to_distribute_s": round(time_s, 4),
        "fiber_transmission": round(eta, 6),
    }


# ---------------------------------------------------------------------------
# Synchronisation accuracy vs N
# ---------------------------------------------------------------------------

def sync_accuracy_sweep(n_pair_values=None,
                         distance_km: float = 100.0,
                         t_coherence_us: float = 100.0) -> list:
    """Compute synchronisation accuracy vs N entangled pairs."""
    if n_pair_values is None:
        n_pair_values = [1, 4, 16, 64, 256, 1024, 4096, 16384]

    classical_acc_ns = gps_accuracy_ns(n_satellites=4)
    rows = []
    for n in n_pair_values:
        q_acc_ps = quantum_sync_accuracy_ps(n, t_coherence_us)
        overhead = entanglement_overhead(n, distance_km=distance_km)
        improvement = classical_acc_ns * 1e3 / max(q_acc_ps, 1e-12)
        rows.append({
            "n_pairs": n,
            "classical_accuracy_ns": round(classical_acc_ns, 4),
            "quantum_accuracy_ps": round(q_acc_ps, 6),
            "improvement_factor": round(improvement, 2),
            "distribution_time_s": overhead["time_to_distribute_s"],
            "entanglement_overhead": overhead,
        })
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Quantum Clock Synchronisation ===\n")

    distance_km = 100.0
    t_coherence_us = 100.0
    n_pair_values = [1, 4, 16, 64, 256, 1024, 4096]

    sweep = sync_accuracy_sweep(
        n_pair_values=n_pair_values,
        distance_km=distance_km,
        t_coherence_us=t_coherence_us,
    )

    classical_ns = gps_accuracy_ns()
    classical_fiber = classical_fiber_sync_ns(distance_km)
    print(f"Classical GPS accuracy     : {classical_ns:.2f} ns")
    print(f"Classical fibre sync (100km): {classical_fiber:.2f} ns")

    print(f"\n{'N_pairs':>8}  {'Classical [ns]':>14}  "
          f"{'Quantum [ps]':>12}  {'Improvement':>12}")
    print("-" * 55)
    for row in sweep:
        print(f"{row['n_pairs']:>8}  "
              f"{row['classical_accuracy_ns']:>14.3f}  "
              f"{row['quantum_accuracy_ps']:>12.4f}  "
              f"{row['improvement_factor']:>10.1f}x")

    result = {
        "n_pairs": n_pair_values,
        "classical_accuracy_ns": round(classical_ns, 4),
        "classical_fiber_accuracy_ns": round(classical_fiber, 4),
        "quantum_accuracy_ps": [round(r["quantum_accuracy_ps"], 6)
                                  for r in sweep],
        "improvement_factor": [r["improvement_factor"] for r in sweep],
        "entanglement_overhead": [r["entanglement_overhead"] for r in sweep],
        "distance_km": distance_km,
        "coherence_time_us": t_coherence_us,
        "sweep": sweep,
    }

    os.makedirs("data", exist_ok=True)
    out_path = "data/sync_results.json"
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=2)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
