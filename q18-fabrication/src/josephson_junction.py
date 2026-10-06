"""
Josephson Junction and Transmon Qubit Model
H = 4Ec(n-ng)² - EJ·cos(φ)
Computes qubit frequency, anharmonicity, and charge dispersion vs EJ/EC ratio.
"""
import numpy as np
import json
import os
from typing import Dict, List, Tuple


# Physical constants
H_PLANCK = 6.62607015e-34  # J·s
E_CHARGE = 1.602176634e-19  # C
GHZ_PER_JOULE = 1.0 / (H_PLANCK * 1e9)  # Convert Joules to GHz


def solve_transmon_hamiltonian(
    Ec_GHz: float,
    Ej_GHz: float,
    ng: float = 0.0,
    n_charge_states: int = 30,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Exact diagonalization of transmon Hamiltonian in charge basis.
    H = 4Ec(n-ng)² - EJ/2 * (|n><n+1| + |n+1><n|)
    Returns (eigenvalues_GHz, eigenvectors).
    """
    N = 2 * n_charge_states + 1
    n_vals = np.arange(-n_charge_states, n_charge_states + 1)

    # Diagonal: 4Ec(n - ng)²
    diag = 4 * Ec_GHz * (n_vals - ng) ** 2

    # Off-diagonal: -EJ/2
    off_diag = -Ej_GHz / 2.0 * np.ones(N - 1)

    H = np.diag(diag) + np.diag(off_diag, 1) + np.diag(off_diag, -1)
    eigenvalues, eigenvectors = np.linalg.eigh(H)

    return eigenvalues, eigenvectors


def compute_qubit_properties(
    Ec_GHz: float,
    Ej_GHz: float,
    ng: float = 0.0,
) -> Dict:
    """
    Compute qubit frequency, anharmonicity, and charge dispersion.
    ω₀₁ ≈ √(8·Ec·EJ) - Ec  (transmon approximation)
    α = E₁₂ - E₀₁  (anharmonicity, should be negative for transmon)
    """
    eigenvalues, _ = solve_transmon_hamiltonian(Ec_GHz, Ej_GHz, ng)

    E0, E1, E2 = eigenvalues[0], eigenvalues[1], eigenvalues[2]
    E01 = E1 - E0  # qubit frequency
    E12 = E2 - E1  # second transition
    anharmonicity = E12 - E01  # negative for transmon

    # Charge dispersion: max - min of E01 over ng ∈ [0, 0.5]
    ng_vals = np.linspace(0.0, 0.5, 20)
    e01_vals = []
    for ng_i in ng_vals:
        ev, _ = solve_transmon_hamiltonian(Ec_GHz, Ej_GHz, ng_i)
        e01_vals.append(ev[1] - ev[0])
    e01_arr = np.array(e01_vals)
    charge_dispersion = float(np.max(e01_arr) - np.min(e01_arr))  # GHz

    # Transmon approximation: ω₀₁ ≈ √(8EcEJ) - Ec
    approx_freq = np.sqrt(8 * Ec_GHz * Ej_GHz) - Ec_GHz

    return {
        "Ec_GHz": Ec_GHz,
        "Ej_GHz": Ej_GHz,
        "Ej_Ec_ratio": round(Ej_GHz / Ec_GHz, 2),
        "qubit_freq_GHz_exact": round(float(E01), 6),
        "qubit_freq_GHz_approx": round(float(approx_freq), 6),
        "anharmonicity_MHz": round(float(anharmonicity * 1000), 4),
        "charge_dispersion_MHz": round(float(charge_dispersion * 1000), 6),
    }


def sweep_ej_ec_ratios(
    Ec_GHz: float = 0.3,
    ratios: List[float] = None,
) -> List[Dict]:
    """
    Compute qubit properties for various EJ/EC ratios.
    Ratios: [1, 10, 50, 100] covering CPB → transmon regime.
    """
    if ratios is None:
        ratios = [1, 5, 10, 20, 50, 100]

    results = []
    for r in ratios:
        Ej = r * Ec_GHz
        props = compute_qubit_properties(Ec_GHz, Ej)
        props["regime"] = (
            "Cooper Pair Box" if r < 5
            else "intermediate" if r < 20
            else "transmon"
        )
        results.append(props)
    return results


def josephson_energy_from_room_temp(
    room_temp_resistance_kohm: float,
    delta_meV: float = 0.17,
) -> float:
    """
    Ambegaokar-Baratoff relation: EJ = (ℏ Δ)/(2e Rn) = π/(4e²Rn) * h*Δ
    For Al junctions: Δ ≈ 0.17 meV, Rn = normal resistance.
    Returns EJ in GHz.
    """
    delta_J = delta_meV * 1e-3 * E_CHARGE  # convert meV to J
    Rn_ohm = room_temp_resistance_kohm * 1e3
    Ej_J = np.pi * delta_J / (2 * E_CHARGE) * (H_PLANCK / (2 * E_CHARGE)) / Rn_ohm
    # Simplified: EJ (J) = π·Δ·h/(4e²·Rn)
    # Standard form: EJ = (h·Ic)/(4π·e) ≈ (h·Δ)/(4e²·Rn) using Ic = π·Δ/(2e·Rn)
    Ic_A = np.pi * delta_J / (2 * E_CHARGE * Rn_ohm)
    Ej_J2 = H_PLANCK * Ic_A / (4 * np.pi * E_CHARGE)
    Ej_GHz = Ej_J2 * GHZ_PER_JOULE
    return round(Ej_GHz, 4)


def main():
    print("=" * 60)
    print("Josephson Junction / Transmon Qubit Model")
    print("=" * 60)

    Ec_GHz = 0.3  # Typical transmon Ec ~ 200-300 MHz

    print(f"\n[1] EJ/EC Ratio Sweep (Ec = {Ec_GHz} GHz)")
    sweep = sweep_ej_ec_ratios(Ec_GHz=Ec_GHz, ratios=[1, 10, 50, 100])
    print(f"  {'EJ/EC':<8} {'f01(GHz)':<12} {'Anharm(MHz)':<14} {'Charge disp(MHz)':<20} {'Regime'}")
    print("  " + "-" * 70)
    for r in sweep:
        print(f"  {r['Ej_Ec_ratio']:<8} {r['qubit_freq_GHz_exact']:<12.4f} "
              f"{r['anharmonicity_MHz']:<14.2f} {r['charge_dispersion_MHz']:<20.6f} {r['regime']}")

    print("\n[2] Standard Transmon Design Point (EJ/EC = 50)")
    design = compute_qubit_properties(Ec_GHz=0.3, Ej_GHz=50 * 0.3)
    print(f"  Qubit frequency : {design['qubit_freq_GHz_exact']:.4f} GHz")
    print(f"  Anharmonicity   : {design['anharmonicity_MHz']:.2f} MHz")
    print(f"  Charge dispersion: {design['charge_dispersion_MHz']:.6f} MHz (suppressed in transmon regime)")

    print("\n[3] EJ from Junction Resistance (Ambegaokar-Baratoff)")
    for Rn_kohm in [5.0, 10.0, 20.0]:
        Ej = josephson_energy_from_room_temp(Rn_kohm)
        ratio = Ej / Ec_GHz
        print(f"  Rn = {Rn_kohm:5.1f} kΩ  →  EJ = {Ej:.4f} GHz, EJ/EC = {ratio:.1f}")

    # Full sweep for output
    full_sweep = sweep_ej_ec_ratios(Ec_GHz=Ec_GHz, ratios=[1, 10, 50, 100])
    output = {
        "ec_GHz": Ec_GHz,
        "ej_ec_ratios": [r["Ej_Ec_ratio"] for r in full_sweep],
        "qubit_freqs_GHz": [r["qubit_freq_GHz_exact"] for r in full_sweep],
        "anharmonicities_MHz": [r["anharmonicity_MHz"] for r in full_sweep],
        "charge_dispersions_MHz": [r["charge_dispersion_MHz"] for r in full_sweep],
        "regimes": [r["regime"] for r in full_sweep],
        "full_sweep": full_sweep,
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "jj_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
