"""
Wire Bond Parasitic Model
Models gold wire bond RF parasitics: inductance, capacitance,
self-resonance, and insertion loss vs frequency.
"""
import numpy as np
import json
import os
from typing import Dict, List


# Wire bond RF parameters (gold wire, typical ~25 μm diameter)
INDUCTANCE_PER_MM_NH = 1.0    # 1 nH/mm (rule of thumb)
CAPACITANCE_PF = 0.1           # ~0.1 pF total capacitance (pad + wire)
RESISTANCE_PER_MM_MOHM = 10.0  # ~10 mΩ/mm (Au wire, 25 μm diam)


def wire_bond_inductance(length_mm: float) -> float:
    """
    Wire bond inductance: L = L_per_mm * length
    Returns inductance in nH.
    More accurate: L = (μ₀/2π) * l * [ln(2l/d) - 3/4]
    """
    return round(INDUCTANCE_PER_MM_NH * length_mm, 4)


def wire_bond_resistance(length_mm: float) -> float:
    """Wire series resistance in mΩ."""
    return round(RESISTANCE_PER_MM_MOHM * length_mm, 4)


def self_resonance_frequency(inductance_nH: float, capacitance_pF: float) -> float:
    """
    Self-resonance: f_SRF = 1/(2π√(LC))
    Returns frequency in GHz.
    """
    L_H = inductance_nH * 1e-9
    C_F = capacitance_pF * 1e-12
    if L_H <= 0 or C_F <= 0:
        return np.inf
    f_SRF = 1.0 / (2 * np.pi * np.sqrt(L_H * C_F))
    return round(float(f_SRF / 1e9), 4)


def insertion_loss_db(
    frequency_GHz: float,
    inductance_nH: float,
    capacitance_pF: float,
    resistance_mohm: float,
    z0_ohm: float = 50.0,
) -> float:
    """
    Insertion loss of a series RLC wire bond model.
    S21 = 2*Z0 / (2*Z0 + Z_bond)
    Z_bond = R + jωL + 1/(jωC)
    IL = -20*log10(|S21|)
    """
    omega = 2 * np.pi * frequency_GHz * 1e9
    R = resistance_mohm * 1e-3
    L_H = inductance_nH * 1e-9
    C_F = capacitance_pF * 1e-12

    Z_bond = complex(R, omega * L_H - 1.0 / (omega * C_F))
    S21 = 2 * z0_ohm / (2 * z0_ohm + Z_bond)
    IL_dB = -20 * np.log10(abs(S21))
    return round(float(IL_dB), 4)


def quality_factor(
    frequency_GHz: float,
    inductance_nH: float,
    resistance_mohm: float,
) -> float:
    """
    Q = ωL / R for inductive element.
    Returns Q factor.
    """
    omega = 2 * np.pi * frequency_GHz * 1e9
    L_H = inductance_nH * 1e-9
    R_ohm = resistance_mohm * 1e-3
    if R_ohm <= 0:
        return np.inf
    return round(float(omega * L_H / R_ohm), 2)


def characterize_wire_bond(length_mm: float) -> Dict:
    """Full characterization of a wire bond at given length."""
    L_nH = wire_bond_inductance(length_mm)
    R_mohm = wire_bond_resistance(length_mm)
    f_SRF = self_resonance_frequency(L_nH, CAPACITANCE_PF)

    # Insertion loss vs frequency
    freqs_GHz = [0.1, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]
    il_values = [insertion_loss_db(f, L_nH, CAPACITANCE_PF, R_mohm) for f in freqs_GHz]
    q_values = [quality_factor(f, L_nH, R_mohm) for f in freqs_GHz]

    return {
        "length_mm": length_mm,
        "inductance_nH": L_nH,
        "capacitance_pF": CAPACITANCE_PF,
        "resistance_mohm": R_mohm,
        "self_resonance_GHz": f_SRF,
        "insertion_loss_dB_vs_freq": dict(zip(freqs_GHz, il_values)),
        "quality_factor_vs_freq": dict(zip(freqs_GHz, q_values)),
        "il_at_5GHz_dB": insertion_loss_db(5.0, L_nH, CAPACITANCE_PF, R_mohm),
        "Q_at_5GHz": quality_factor(5.0, L_nH, R_mohm),
    }


def main():
    print("=" * 60)
    print("Wire Bond Parasitic Model (Gold Wire)")
    print("=" * 60)

    wire_lengths_mm = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0]

    print("\n[1] Wire Bond Parameters vs Length")
    print(f"  {'Length(mm)':<12} {'L(nH)':<10} {'R(mΩ)':<10} {'SRF(GHz)':<12} {'IL@5GHz(dB)'}")
    print("  " + "-" * 60)

    all_results = []
    for L in wire_lengths_mm:
        data = characterize_wire_bond(L)
        all_results.append(data)
        print(f"  {L:<12.1f} {data['inductance_nH']:<10.4f} {data['resistance_mohm']:<10.4f} "
              f"{data['self_resonance_GHz']:<12.4f} {data['il_at_5GHz_dB']:.4f}")

    print("\n[2] Insertion Loss vs Frequency (1 mm wire)")
    ref = next(r for r in all_results if r["length_mm"] == 1.0)
    for f, il in ref["insertion_loss_dB_vs_freq"].items():
        flag = " <-- SRF region" if f >= ref["self_resonance_GHz"] * 0.8 else ""
        print(f"  f = {f:5.1f} GHz: IL = {il:.4f} dB{flag}")

    print("\n[3] Self-Resonance Warning")
    for r in all_results:
        if r["self_resonance_GHz"] < 10.0:
            print(f"  L={r['length_mm']:.1f} mm: SRF = {r['self_resonance_GHz']:.2f} GHz "
                  f"— use shorter bonds for multi-GHz applications")

    output = {
        "wire_lengths_mm": wire_lengths_mm,
        "inductances_nH": [r["inductance_nH"] for r in all_results],
        "self_resonance_GHz": [r["self_resonance_GHz"] for r in all_results],
        "insertion_loss_dB": [r["il_at_5GHz_dB"] for r in all_results],
        "capacitance_pF_assumed": CAPACITANCE_PF,
        "inductance_per_mm_nH": INDUCTANCE_PER_MM_NH,
        "wire_bond_details": all_results,
        "model_note": "L=1nH/mm, C=0.1pF, R=10mΩ/mm; gold wire 25μm diameter",
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "wire_bond_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
