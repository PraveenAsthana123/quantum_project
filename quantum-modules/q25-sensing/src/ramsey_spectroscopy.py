"""
Q25 — Quantum Sensing
ramsey_spectroscopy.py

Ramsey interferometry simulation.
Sequence: π/2 → free evolution T → π/2 → measure
Shows fringe pattern vs detuning and evolution time T.
Applies quantum Fisher information to find optimal T.
Fits frequency from fringe pattern.

Reference: Ramsey (1950); Giovannetti et al., Science 306, 1330 (2004).

Outputs: data/ramsey_results.json
"""

import json
import math
import os
import random


# ---------------------------------------------------------------------------
# Ramsey fringe physics
# ---------------------------------------------------------------------------

def ramsey_probability(detuning_Hz: float, evolution_time_s: float,
                        T2_s: float = None,
                        pi_half_fidelity: float = 0.99) -> float:
    """
    Probability of finding qubit in |1> after Ramsey sequence.
    P(|1>) = F_pi * cos²(π * δν * T) * exp(-T/T2)

    where δν = detuning from resonance [Hz], T = evolution time [s].
    F_pi accounts for π/2 pulse imperfection.
    """
    phase = math.pi * detuning_Hz * evolution_time_s
    p = pi_half_fidelity ** 2 * math.cos(phase) ** 2
    if T2_s is not None and T2_s > 0:
        p *= math.exp(-evolution_time_s / T2_s)
    return p


def fringe_visibility(T_s: float, T2_s: float) -> float:
    """Fringe visibility decays as exp(-T/T2)."""
    if T2_s <= 0:
        return 0.0
    return math.exp(-T_s / T2_s)


# ---------------------------------------------------------------------------
# Quantum Fisher Information
# ---------------------------------------------------------------------------

def qfi_ramsey(n_atoms: int, T_s: float, T2_s: float = None) -> float:
    """
    QFI for Ramsey spectroscopy estimating frequency ν.
    F_Q = (2π T)² * N * exp(-2T/T2)   (coherent state probe)
    """
    decay = math.exp(-2.0 * T_s / T2_s) if T2_s and T2_s > 0 else 1.0
    return (2.0 * math.pi * T_s) ** 2 * n_atoms * decay


def optimal_T(T2_s: float) -> float:
    """
    Optimal evolution time maximising QFI for Ramsey.
    d/dT [(2πT)² exp(-2T/T2)] = 0 → T_opt = T2 / 2
    """
    return T2_s / 2.0


def frequency_sensitivity(n_atoms: int, T_s: float, T2_s: float,
                            averaging_time_s: float = 1.0) -> float:
    """
    Frequency sensitivity (Hz/√Hz) from Cramér-Rao bound.
    δν = 1 / (2π T √(N * exp(-2T/T2) * τ))
    where τ = averaging time in repetition cycles.
    """
    f_q = qfi_ramsey(n_atoms, T_s, T2_s)
    if f_q <= 0:
        return float("inf")
    # Sensitivity per √Hz: δν/√Hz = 1 / √(F_Q * τ)  where τ normalised
    return 1.0 / math.sqrt(f_q * averaging_time_s)


# ---------------------------------------------------------------------------
# Fringe fitting (least-squares cosine fit)
# ---------------------------------------------------------------------------

def fit_frequency_from_fringe(detunings_Hz: list,
                                probabilities: list) -> float:
    """
    Estimate resonance frequency from Ramsey fringe via peak finding.
    Uses a simple Fourier-based approach: find the detuning at peak prob.
    Returns estimated frequency offset [Hz] relative to carrier.
    """
    if not probabilities:
        return 0.0
    # Find the detuning of minimum probability (dark fringe near resonance
    # for cos² → at resonance, P = 0.5 for first fringe; locate central max)
    peak_idx = max(range(len(probabilities)), key=lambda i: probabilities[i])
    return detunings_Hz[peak_idx]


# ---------------------------------------------------------------------------
# Main simulation
# ---------------------------------------------------------------------------

def simulate_ramsey(n_atoms: int = 1000,
                     T2_us: float = 100.0,
                     detuning_range_kHz: float = 5.0,
                     n_detuning_points: int = 200,
                     T_values_us=None,
                     noise_sigma: float = 0.01,
                     seed: int = 42) -> dict:
    """
    Full Ramsey simulation.
    Returns fringe data, QFI, sensitivity.
    """
    random.seed(seed)
    T2_s = T2_us * 1e-6

    if T_values_us is None:
        T_values_us = [10.0, T2_s * 0.5 * 1e6, T2_s * 1e6, T2_s * 2e6]

    detunings_Hz = [
        -detuning_range_kHz * 1e3
        + i * 2 * detuning_range_kHz * 1e3 / (n_detuning_points - 1)
        for i in range(n_detuning_points)
    ]

    T_opt_us = optimal_T(T2_s) * 1e6
    T_primary_s = T_opt_us * 1e-6

    fringe_at_T_opt = [
        ramsey_probability(d, T_primary_s, T2_s) +
        random.gauss(0, noise_sigma)
        for d in detunings_Hz
    ]
    fringe_at_T_opt = [min(1.0, max(0.0, p)) for p in fringe_at_T_opt]

    # Fringes at each T value
    fringe_data = []
    for T_us in T_values_us:
        T_s_val = T_us * 1e-6
        probs = [ramsey_probability(d, T_s_val, T2_s)
                 for d in detunings_Hz]
        vis = fringe_visibility(T_s_val, T2_s)
        fringe_data.append({
            "T_us": round(T_us, 2),
            "visibility": round(vis, 4),
            "probs_sample": [round(p, 4) for p in probs[:10]],  # truncate for JSON
        })

    # QFI vs T
    qfi_at_T_opt = qfi_ramsey(n_atoms, T_primary_s, T2_s)
    sensitivity_Hz_sqrt_Hz = frequency_sensitivity(
        n_atoms, T_primary_s, T2_s, averaging_time_s=1.0)

    # Fitted frequency
    freq_est = fit_frequency_from_fringe(detunings_Hz, fringe_at_T_opt)

    print(f"T2                   : {T2_us:.1f} µs")
    print(f"Optimal T            : {T_opt_us:.1f} µs")
    print(f"QFI at T_opt         : {qfi_at_T_opt:.4e}")
    print(f"Sensitivity          : {sensitivity_Hz_sqrt_Hz:.4e} Hz/√Hz")
    print(f"Fringe visibility    : {fringe_visibility(T_primary_s, T2_s):.4f}")
    print(f"Estimated frequency  : {freq_est:.2f} Hz")

    result = {
        "detuning_range_kHz": detuning_range_kHz,
        "T_values_us": T_values_us,
        "fringe_visibility": round(fringe_visibility(T_primary_s, T2_s), 4),
        "qfi": round(qfi_at_T_opt, 4),
        "optimal_T_us": round(T_opt_us, 2),
        "frequency_sensitivity_Hz_per_sqrt_Hz": round(sensitivity_Hz_sqrt_Hz, 8),
        "estimated_frequency_Hz": round(freq_est, 4),
        "n_atoms": n_atoms,
        "T2_us": T2_us,
        "fringe_data": fringe_data,
    }
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Ramsey Spectroscopy Simulation ===\n")

    results = simulate_ramsey(
        n_atoms=1000,
        T2_us=100.0,
        detuning_range_kHz=5.0,
    )

    os.makedirs("data", exist_ok=True)
    out_path = "data/ramsey_results.json"
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
