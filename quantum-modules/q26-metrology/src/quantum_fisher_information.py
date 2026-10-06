"""
Q26 — Quantum Metrology
quantum_fisher_information.py

Quantum Fisher Information (QFI) and Cramér-Rao bound.
Compares probe states:
  - Coherent state: F = N (shot noise limit / SQL)
  - GHZ state:      F = N² (Heisenberg limit)
  - NOON state:     F = N²
  - Squeezed state: F = N·exp(2r)  (r = squeezing parameter)

Shows precision vs N for each state type.

Reference: Braunstein & Caves, PRL 72, 3439 (1994);
           Giovannetti, Lloyd & Maccone, Science 306, 1330 (2004).

Outputs: data/qfi_results.json
"""

import json
import math
import os


# ---------------------------------------------------------------------------
# QFI for different probe states
# ---------------------------------------------------------------------------

def qfi_coherent(n: int) -> float:
    """
    Coherent state (product state, separable) → SQL.
    F_Q = N  (for phase estimation)
    Precision: Δθ = 1/√N  (standard quantum limit)
    """
    return float(n)


def qfi_ghz(n: int) -> float:
    """
    GHZ (Greenberger-Horne-Zeilinger) state → Heisenberg limit.
    F_Q = N²
    Precision: Δθ = 1/N
    """
    return float(n ** 2)


def qfi_noon(n: int) -> float:
    """
    NOON state: (|N,0⟩ + |0,N⟩)/√2 → Heisenberg scaling.
    F_Q = N²  (same as GHZ for phase estimation)
    """
    return float(n ** 2)


def qfi_squeezed(n: int, squeezing_r: float = 1.0) -> float:
    """
    Spin-squeezed state with squeezing parameter r.
    F_Q = N · exp(2r)   [for r < ln(√N), i.e. moderate squeezing]
    When r → ½ ln(N): F_Q → N² (Heisenberg limit approached).

    Reference: Wineland et al., PRA 46, R6797 (1992).
    """
    return n * math.exp(2.0 * squeezing_r)


# ---------------------------------------------------------------------------
# Standard sensitivity limits
# ---------------------------------------------------------------------------

def sql_precision(n: int) -> float:
    """Standard quantum limit (SQL): Δθ_SQL = 1/√N."""
    return 1.0 / math.sqrt(max(n, 1))


def heisenberg_limit(n: int) -> float:
    """Heisenberg limit: Δθ_HL = 1/N."""
    return 1.0 / max(n, 1)


def precision_from_qfi(qfi: float) -> float:
    """Cramér-Rao bound: Δθ_CRB = 1/√F_Q."""
    if qfi <= 0:
        return float("inf")
    return 1.0 / math.sqrt(qfi)


def advantage_factor(qfi: float, n: int) -> float:
    """Quantum advantage = F_Q / F_SQL = F_Q / N."""
    return qfi / max(n, 1)


# ---------------------------------------------------------------------------
# Multi-N sweep
# ---------------------------------------------------------------------------

def qfi_vs_n(n_values: list,
              squeezing_r: float = 1.0) -> dict:
    """
    Compute QFI and precision for all probe states vs N.
    Returns nested dict keyed by state name.
    """
    states = {
        "coherent": qfi_coherent,
        "GHZ": qfi_ghz,
        "NOON": qfi_noon,
        "squeezed": lambda n: qfi_squeezed(n, squeezing_r),
    }

    results = {
        "n_values": n_values,
        "states": {},
        "sql": [round(sql_precision(n), 8) for n in n_values],
        "heisenberg": [round(heisenberg_limit(n), 8) for n in n_values],
    }

    for name, fn in states.items():
        qfi_vals = [fn(n) for n in n_values]
        precision_vals = [precision_from_qfi(f) for f in qfi_vals]
        adv_vals = [advantage_factor(f, n) for f, n in zip(qfi_vals, n_values)]

        results["states"][name] = {
            "qfi": [round(f, 4) for f in qfi_vals],
            "precision": [round(p, 8) for p in precision_vals],
            "advantage_over_sql": [round(a, 4) for a in adv_vals],
        }

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Quantum Fisher Information & Cramér-Rao Bound ===\n")

    n_values = [1, 2, 4, 8, 16, 32, 64, 100, 256, 1024]
    squeezing_r = 1.0  # 1 e-fold squeezing ≈ 8.7 dB

    data = qfi_vs_n(n_values, squeezing_r=squeezing_r)

    print(f"{'N':>6}  {'Coherent':>12}  {'GHZ':>12}  {'NOON':>12}  {'Squeezed':>12}")
    print("-" * 60)
    for i, n in enumerate(n_values):
        f_c = data["states"]["coherent"]["qfi"][i]
        f_g = data["states"]["GHZ"]["qfi"][i]
        f_n = data["states"]["NOON"]["qfi"][i]
        f_s = data["states"]["squeezed"]["qfi"][i]
        print(f"{n:>6}  {f_c:>12.2f}  {f_g:>12.2f}  {f_n:>12.2f}  {f_s:>12.4f}")

    print("\nPrecision (Δθ) comparison at N=100:")
    n100_idx = n_values.index(100)
    for name in ["coherent", "GHZ", "NOON", "squeezed"]:
        p = data["states"][name]["precision"][n100_idx]
        a = data["states"][name]["advantage_over_sql"][n100_idx]
        print(f"  {name:10s}: Δθ = {p:.2e}  (advantage = {a:.2f}x)")

    # Summary row for JSON
    summary = {
        "n_qubits": n_values,
        "states": list(data["states"].keys()),
        "qfi_values": {
            name: data["states"][name]["qfi"]
            for name in data["states"]
        },
        "sensitivities": {
            name: data["states"][name]["precision"]
            for name in data["states"]
        },
        "heisenberg_limit": data["heisenberg"],
        "sql": data["sql"],
        "advantage_factor": {
            name: data["states"][name]["advantage_over_sql"]
            for name in data["states"]
        },
        "squeezing_r": squeezing_r,
    }

    os.makedirs("data", exist_ok=True)
    out_path = "data/qfi_results.json"
    with open(out_path, "w") as fh:
        json.dump(summary, fh, indent=2)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
