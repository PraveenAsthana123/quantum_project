"""
Q26 — Quantum Metrology
parameter_estimation.py

Quantum parameter estimation via phase estimation.
Compares: standard quantum limit (SQL) vs Heisenberg limit (HL).
Shows N-qubit GHZ gives √N improvement over N independent qubits.

Reference: Giovannetti, Lloyd & Maccone, PRL 96, 010401 (2006);
           Demkowicz-Dobrzanski et al., Prog. Opt. 60, 345 (2015).

Outputs: data/estimation_results.json
"""

import json
import math
import os
import random


# ---------------------------------------------------------------------------
# Phase estimation physics
# ---------------------------------------------------------------------------

def phase_error_sql(n: int, n_shots: int = 1) -> float:
    """
    Standard quantum limit for phase estimation.
    N independent single-qubit measurements (unentangled probe):
    Δφ_SQL = 1 / √(N * n_shots)
    """
    return 1.0 / math.sqrt(max(n, 1) * max(n_shots, 1))


def phase_error_heisenberg(n: int, n_shots: int = 1) -> float:
    """
    Heisenberg limit (maximally entangled N-qubit probe):
    Δφ_HL = 1 / (N * √n_shots)
    """
    return 1.0 / (max(n, 1) * math.sqrt(max(n_shots, 1)))


def phase_error_ghz(n: int, n_shots: int = 1) -> float:
    """
    N-qubit GHZ state: phase error = 1/(N * √n_shots) = Heisenberg limit.
    """
    return phase_error_heisenberg(n, n_shots)


def phase_error_squeezed(n: int, squeezing_db: float = 6.0,
                          n_shots: int = 1) -> float:
    """
    Spin-squeezed state phase error:
    Δφ_sq = exp(-r) / √N  where r = squeezing_dB * ln(10) / 20
    Improves over SQL by exp(-r) but stays above HL.
    """
    r = squeezing_db * math.log(10.0) / 20.0  # convert dB to neper
    return math.exp(-r) / (math.sqrt(max(n, 1)) * math.sqrt(max(n_shots, 1)))


def improvement_factor_ghz_vs_sql(n: int) -> float:
    """
    Improvement factor of N-qubit GHZ over N independent qubits.
    = Δφ_SQL / Δφ_GHZ = √N
    """
    return math.sqrt(n)


# ---------------------------------------------------------------------------
# Monte-Carlo phase estimation simulation
# ---------------------------------------------------------------------------

def simulate_phase_estimation(true_phase: float,
                                n_qubits: int,
                                probe_type: str = "ghz",
                                n_shots: int = 1000,
                                squeezing_db: float = 6.0,
                                seed: int = 42) -> dict:
    """
    Simulate phase estimation experiment for a given probe state.
    Draws n_shots samples from the measurement distribution and
    computes mean phase estimate and standard deviation.

    Returns dict with estimated phase, std, and theoretical bound.
    """
    random.seed(seed)

    # Theoretical error
    if probe_type == "coherent":
        theory_err = phase_error_sql(n_qubits, n_shots)
    elif probe_type in ("ghz", "noon"):
        theory_err = phase_error_ghz(n_qubits, n_shots)
    elif probe_type == "squeezed":
        theory_err = phase_error_squeezed(n_qubits, squeezing_db, n_shots)
    else:
        theory_err = phase_error_sql(n_qubits, n_shots)

    # Simulated measurement samples
    estimated_phases = [
        true_phase + random.gauss(0.0, theory_err * math.sqrt(n_shots))
        for _ in range(n_shots)
    ]

    mean_est = sum(estimated_phases) / len(estimated_phases)
    variance = sum((x - mean_est) ** 2 for x in estimated_phases) / len(estimated_phases)
    std_est = math.sqrt(variance) / math.sqrt(n_shots)  # std of the mean

    return {
        "probe_type": probe_type,
        "n_qubits": n_qubits,
        "n_shots": n_shots,
        "true_phase": true_phase,
        "estimated_phase": round(mean_est, 6),
        "std_deviation": round(std_est, 8),
        "theoretical_error": round(theory_err, 8),
        "bias": round(abs(mean_est - true_phase), 8),
    }


# ---------------------------------------------------------------------------
# Comparison sweep
# ---------------------------------------------------------------------------

def compare_all_probes(n_values: list = None,
                        n_shots: int = 1000,
                        squeezing_db: float = 6.0) -> dict:
    """
    Compute phase error for all probe types vs N.
    """
    if n_values is None:
        n_values = [1, 2, 4, 8, 16, 32, 64, 128, 256]

    probes = {
        "coherent": lambda n: phase_error_sql(n, n_shots),
        "GHZ": lambda n: phase_error_ghz(n, n_shots),
        "NOON": lambda n: phase_error_ghz(n, n_shots),
        "squeezed": lambda n: phase_error_squeezed(n, squeezing_db, n_shots),
    }

    results = {
        "n_qubits": n_values,
        "n_shots": n_shots,
        "squeezing_db": squeezing_db,
    }

    probe_results = {}
    for name, fn in probes.items():
        errors = [fn(n) for n in n_values]
        probe_results[name] = {
            "phase_errors": [round(e, 10) for e in errors],
        }

    results["probe_states"] = probe_results
    results["sql_scaling"] = [round(phase_error_sql(n, n_shots), 10)
                               for n in n_values]
    results["heisenberg_scaling"] = [round(phase_error_heisenberg(n, n_shots), 10)
                                      for n in n_values]
    results["improvement_factor"] = [round(improvement_factor_ghz_vs_sql(n), 4)
                                      for n in n_values]
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Quantum Parameter Estimation ===\n")

    n_values = [1, 2, 4, 8, 16, 32, 64, 100, 256, 1024]
    comparison = compare_all_probes(n_values=n_values, n_shots=1000)

    print(f"{'N':>6}  {'SQL':>14}  {'GHZ/HL':>14}  "
          f"{'Squeezed':>14}  {'√N improv':>10}")
    print("-" * 65)
    for i, n in enumerate(n_values):
        sql = comparison["sql_scaling"][i]
        hl = comparison["heisenberg_scaling"][i]
        sq = comparison["probe_states"]["squeezed"]["phase_errors"][i]
        imp = comparison["improvement_factor"][i]
        print(f"{n:>6}  {sql:>14.4e}  {hl:>14.4e}  {sq:>14.4e}  {imp:>10.2f}x")

    # Detailed simulation for N=16, GHZ
    print("\n--- Detailed simulation: N=16 GHZ state ---")
    sim = simulate_phase_estimation(
        true_phase=math.pi / 4,
        n_qubits=16,
        probe_type="ghz",
        n_shots=5000,
    )
    print(f"  True phase     : {sim['true_phase']:.6f}")
    print(f"  Estimated      : {sim['estimated_phase']:.6f}")
    print(f"  Std deviation  : {sim['std_deviation']:.2e}")
    print(f"  Theory error   : {sim['theoretical_error']:.2e}")
    print(f"  Bias           : {sim['bias']:.2e}")

    output = {
        "n_qubits": n_values,
        "probe_states": list(comparison["probe_states"].keys()),
        "phase_errors": {
            name: comparison["probe_states"][name]["phase_errors"]
            for name in comparison["probe_states"]
        },
        "sql_scaling": comparison["sql_scaling"],
        "heisenberg_scaling": comparison["heisenberg_scaling"],
        "improvement_factor": comparison["improvement_factor"],
        "simulation_example": sim,
    }

    os.makedirs("data", exist_ok=True)
    out_path = "data/estimation_results.json"
    with open(out_path, "w") as fh:
        json.dump(output, fh, indent=2)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
