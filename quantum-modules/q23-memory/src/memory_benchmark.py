"""
Q23 — Quantum Memory
memory_benchmark.py

DLCZ (Duan-Lukin-Cirac-Zoller) quantum memory protocol benchmark.
Writes an entangled spin wave, retrieves after variable delay,
fits exponential decay of fidelity with storage time.

Reference: Duan et al., Nature 414, 413 (2001);
           Zhao et al., Nature Physics 5, 100 (2009).

Outputs: data/memory_benchmark_results.json
"""

import json
import math
import os
import random


# ---------------------------------------------------------------------------
# DLCZ physics
# ---------------------------------------------------------------------------

def dlcz_write_probability(chi: float) -> float:
    """
    Probability of exciting a spin wave during the write pulse.
    P_write ≈ chi  (weak coherent write pulse, single excitation regime).
    chi << 1 to suppress multi-photon events.
    """
    return min(1.0, max(0.0, chi))


def dlcz_retrieval_efficiency(optical_depth: float) -> float:
    """
    Efficiency of retrieving the spin-wave excitation as a photon.
    η_ret ≈ d / (d + 1)  (forward retrieval, optically thick ensemble).
    """
    return optical_depth / (optical_depth + 1.0)


def spin_wave_fidelity(storage_time_us: float, t1_us: float,
                        t2_us: float) -> float:
    """
    Fidelity of the stored spin wave after time t.
    Combines T1 (population decay) and T2 (dephasing):
      F(t) = 1/2 * (1 + exp(-t/T2) * exp(-t/T1))
    Simplified for single-excitation qubit in a Lambda system:
      F(t) ≈ exp(-t/T2)   (T2 < T1 dominated)
    """
    return math.exp(-storage_time_us / t2_us)


def dlcz_pair_rate(rep_rate_hz: float, chi: float,
                    eta_ret: float, eta_detector: float) -> float:
    """
    Rate at which Alice-Bob share a DLCZ entangled pair.
    R = rep_rate * p_write * eta_ret * eta_detector
    Note: both ends must detect; so R ∝ (p_write * eta_det)^2 for
    coincidence detection, but here we consider single-side detection.
    R_pair = rep_rate * chi * eta_ret^2 * eta_det^2  (coincidence)
    """
    return rep_rate_hz * chi * (eta_ret * eta_detector) ** 2


# ---------------------------------------------------------------------------
# Exponential decay fit (least-squares, no scipy needed)
# ---------------------------------------------------------------------------

def fit_exponential_decay(x_vals: list, y_vals: list) -> tuple:
    """
    Fit y = A * exp(-x / tau) using log-linear regression.
    Returns (A, tau) where tau is the decay constant.
    """
    if len(x_vals) < 2:
        return 1.0, float("inf")

    # Filter valid (y > 0) points
    pairs = [(x, y) for x, y in zip(x_vals, y_vals) if y > 1e-10]
    if len(pairs) < 2:
        return 1.0, 1.0

    # Log-linear: ln(y) = ln(A) - x/tau
    log_y = [math.log(p[1]) for p in pairs]
    xs = [p[0] for p in pairs]
    n = len(xs)
    mean_x = sum(xs) / n
    mean_ly = sum(log_y) / n

    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    ss_xy = sum((x - mean_x) * (ly - mean_ly) for x, ly in zip(xs, log_y))

    if abs(ss_xx) < 1e-30:
        return math.exp(mean_ly), float("inf")

    slope = ss_xy / ss_xx   # slope = -1/tau
    intercept = mean_ly - slope * mean_x  # intercept = ln(A)

    tau = -1.0 / slope if abs(slope) > 1e-12 else float("inf")
    A = math.exp(intercept)
    return A, tau


# ---------------------------------------------------------------------------
# DLCZ benchmark: fidelity vs storage time
# ---------------------------------------------------------------------------

def run_dlcz_benchmark(t2_us: float = 500.0,
                        t1_us: float = 2000.0,
                        optical_depth: float = 50.0,
                        chi: float = 0.05,
                        eta_detector: float = 0.85,
                        rep_rate_hz: float = 1e5,
                        storage_times_us=None,
                        noise_sigma: float = 0.01,
                        seed: int = 42) -> dict:
    """
    Simulate DLCZ protocol: write spin wave, retrieve after variable delay.
    Fits exponential decay of fidelity vs storage time.
    """
    if storage_times_us is None:
        storage_times_us = [0, 50, 100, 200, 300, 500, 750, 1000, 1500, 2000]

    random.seed(seed)

    eta_ret = dlcz_retrieval_efficiency(optical_depth)
    pair_rate = dlcz_pair_rate(rep_rate_hz, chi, eta_ret, eta_detector)

    fidelities = []
    for t in storage_times_us:
        f_ideal = spin_wave_fidelity(t, t1_us, t2_us)
        # Add small measurement noise
        noise = random.gauss(0.0, noise_sigma)
        f_meas = max(0.5, min(1.0, f_ideal + noise))
        fidelities.append(round(f_meas, 5))

    # Fit exponential decay
    A_fit, tau_fit = fit_exponential_decay(storage_times_us, fidelities)

    print(f"Fitted T1_memory : {tau_fit:.1f} µs  (input T2={t2_us} µs)")
    print(f"DLCZ pair rate   : {pair_rate:.2e} Hz")

    return {
        "storage_times_us": storage_times_us,
        "fidelities": fidelities,
        "t1_us": round(t1_us, 2),
        "t2_us": round(t2_us, 2),
        "fitted_tau_us": round(tau_fit, 2),
        "dlcz_rate_Hz": round(pair_rate, 4),
        "eta_retrieval": round(eta_ret, 4),
        "optical_depth": optical_depth,
        "chi": chi,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== DLCZ Quantum Memory Benchmark ===\n")

    results = run_dlcz_benchmark(
        t2_us=500.0,
        t1_us=2000.0,
        optical_depth=50.0,
        chi=0.05,
        eta_detector=0.85,
        rep_rate_hz=1e5,
    )

    print(f"\nStorage Time (µs)  Fidelity")
    for t, f in zip(results["storage_times_us"], results["fidelities"]):
        bar = "#" * int(f * 30)
        print(f"  {t:6.0f}           {f:.4f}  {bar}")

    print(f"\nFitted decay time  : {results['fitted_tau_us']:.1f} µs")
    print(f"DLCZ pair rate     : {results['dlcz_rate_Hz']:.4e} Hz")
    print(f"Retrieval eff.     : {results['eta_retrieval']:.4f}")

    os.makedirs("data", exist_ok=True)
    out_path = "data/memory_benchmark_results.json"
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
