"""
Flip-Chip Bonding Simulation
Models indium bump bonding parasitics and effect on qubit frequency and coherence.
"""
import numpy as np
import json
import os
from typing import Dict, List


# Physical constants
EPSILON_0 = 8.854187817e-12  # F/m
MU_0 = 4 * np.pi * 1e-7     # H/m


def bump_parasitic_inductance(
    bump_diameter_um: float,
    bump_height_um: float,
) -> float:
    """
    Parasitic inductance of a cylindrical bump.
    L ≈ μ₀ * h / (π * (d/2)²) for solid cylinder (low-freq approximation)
    More accurately: L ≈ (μ₀/2π) * h * [ln(2h/d) - 3/4]  (wire formula)
    Returns inductance in pH.
    """
    h_m = bump_height_um * 1e-6
    d_m = bump_diameter_um * 1e-6
    if d_m <= 0 or h_m <= 0:
        return 0.0
    # Neumann formula for a short cylindrical current element
    # Simplified: L ≈ (μ₀/2π) * h * (ln(2h/d) + 0.5)
    arg = 2 * h_m / d_m
    if arg <= 1:
        L_H = MU_0 * h_m / (2 * np.pi) * 0.5
    else:
        L_H = MU_0 * h_m / (2 * np.pi) * (np.log(arg) + 0.5)
    L_pH = L_H * 1e12
    return round(float(L_pH), 4)


def bump_parasitic_capacitance(
    bump_diameter_um: float,
    bump_height_um: float,
    epsilon_r: float = 3.9,   # SiO2 underfill relative permittivity
) -> float:
    """
    Parasitic capacitance of bump pad.
    Approximated as a parallel-plate cap: C = ε₀εᵣ * A / h
    where A = pad area, h = bump height.
    Returns capacitance in fF.
    """
    h_m = bump_height_um * 1e-6
    r_m = (bump_diameter_um / 2) * 1e-6
    A_m2 = np.pi * r_m ** 2
    if h_m <= 0:
        return 0.0
    C_F = EPSILON_0 * epsilon_r * A_m2 / h_m
    C_fF = C_F * 1e15
    return round(float(C_fF), 4)


def qubit_frequency_shift_from_parasitic(
    qubit_freq_GHz: float,
    qubit_capacitance_fF: float,
    qubit_inductance_pH: float,
    bump_inductance_pH: float,
    bump_capacitance_fF: float,
) -> Dict:
    """
    Estimate qubit frequency shift due to parasitic bump impedance.
    ω₀ = 1/√(LC) for LC oscillator model.
    Δω/ω ≈ -ΔL/(2L) - ΔC/(2C)
    """
    # Original frequency
    L_H = qubit_inductance_pH * 1e-12
    C_F = qubit_capacitance_fF * 1e-15
    omega_0 = 1.0 / np.sqrt(L_H * C_F)
    f0_GHz = omega_0 / (2 * np.pi * 1e9)

    # Perturbed
    L_new = (qubit_inductance_pH + bump_inductance_pH) * 1e-12
    C_new = (qubit_capacitance_fF + bump_capacitance_fF) * 1e-15
    omega_new = 1.0 / np.sqrt(L_new * C_new)
    f_new_GHz = omega_new / (2 * np.pi * 1e9)

    freq_shift_MHz = (f_new_GHz - f0_GHz) * 1000.0

    return {
        "original_freq_GHz": round(f0_GHz, 6),
        "perturbed_freq_GHz": round(f_new_GHz, 6),
        "freq_shift_MHz": round(float(freq_shift_MHz), 4),
        "relative_shift_ppm": round(float(freq_shift_MHz / f0_GHz * 1000), 2),
    }


def coherence_impact(
    bump_resistance_mohm: float,
    qubit_freq_GHz: float,
    qubit_capacitance_fF: float = 70.0,
) -> Dict:
    """
    Estimate T1 impact from bump resistive loss.
    Purcell-like loss: 1/T1 ∝ Re[Y(ω)] = G, where G is lossy conductance.
    For a resistor in series with bump: G ≈ R·ω²·C² (at high freq)
    """
    R_ohm = bump_resistance_mohm * 1e-3
    omega = 2 * np.pi * qubit_freq_GHz * 1e9
    C_F = qubit_capacitance_fF * 1e-15

    G_effective = R_ohm * (omega * C_F) ** 2
    if G_effective > 0:
        T1_limited_us = 1.0 / (G_effective * omega ** 2 / (2 * np.pi)) * 1e6
        # More direct: κ = ω² C² R → T1 = 1/κ
        kappa = (omega ** 2) * (C_F ** 2) * R_ohm
        T1_s = 1.0 / kappa if kappa > 0 else 1e6
        T1_us = T1_s * 1e6
    else:
        T1_us = 1e6

    return {
        "bump_resistance_mohm": bump_resistance_mohm,
        "T1_limit_from_bump_us": round(float(T1_us), 2),
    }


def sweep_bump_parameters() -> List[Dict]:
    """
    Sweep bump diameter and pitch, compute full parasitic characterization.
    """
    configs = [
        {"diameter_um": 10.0, "height_um": 5.0, "pitch_um": 50.0},
        {"diameter_um": 20.0, "height_um": 8.0, "pitch_um": 80.0},
        {"diameter_um": 30.0, "height_um": 10.0, "pitch_um": 100.0},
        {"diameter_um": 50.0, "height_um": 15.0, "pitch_um": 150.0},
        {"diameter_um": 100.0, "height_um": 20.0, "pitch_um": 250.0},
    ]

    # Qubit parameters
    qubit_freq_GHz = 5.0
    qubit_cap_fF = 70.0
    qubit_ind_pH = 10.0  # Josephson inductance ~10 pH

    results = []
    for c in configs:
        L_bump = bump_parasitic_inductance(c["diameter_um"], c["height_um"])
        C_bump = bump_parasitic_capacitance(c["diameter_um"], c["height_um"])
        freq_data = qubit_frequency_shift_from_parasitic(
            qubit_freq_GHz, qubit_cap_fF, qubit_ind_pH, L_bump, C_bump
        )
        t1_data = coherence_impact(0.1, qubit_freq_GHz, qubit_cap_fF)  # 0.1 mΩ bump resistance

        results.append({
            "bump_diameter_um": c["diameter_um"],
            "bump_pitch_um": c["pitch_um"],
            "bump_height_um": c["height_um"],
            "parasitic_inductance_pH": L_bump,
            "parasitic_capacitance_fF": C_bump,
            "freq_shift_MHz": freq_data["freq_shift_MHz"],
            "t1_limit_us": t1_data["T1_limit_from_bump_us"],
        })
    return results


def main():
    print("=" * 60)
    print("Flip-Chip Bonding Simulation")
    print("=" * 60)

    results = sweep_bump_parameters()

    print("\n[1] Bump Parasitic Parameters vs Diameter")
    print(f"  {'Diam(μm)':<10} {'Height(μm)':<12} {'L_bump(pH)':<12} {'C_bump(fF)':<12} {'Δf(MHz)'}")
    print("  " + "-" * 65)
    for r in results:
        print(f"  {r['bump_diameter_um']:<10.1f} {r['bump_height_um']:<12.1f} "
              f"{r['parasitic_inductance_pH']:<12.4f} {r['parasitic_capacitance_fF']:<12.4f} "
              f"{r['freq_shift_MHz']:.4f}")

    print("\n[2] T1 Impact from Bump Resistance")
    for r in results:
        print(f"  d={r['bump_diameter_um']:.0f}μm: T1 limit = {r['t1_limit_us']:.2f} μs")

    output = {
        "bump_diameter_um": [r["bump_diameter_um"] for r in results],
        "bump_pitch_um": [r["bump_pitch_um"] for r in results],
        "parasitic_inductance_pH": [r["parasitic_inductance_pH"] for r in results],
        "parasitic_capacitance_fF": [r["parasitic_capacitance_fF"] for r in results],
        "freq_shift_MHz": [r["freq_shift_MHz"] for r in results],
        "t1_limit_us": [r["t1_limit_us"] for r in results],
        "sweep_details": results,
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "flip_chip_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
