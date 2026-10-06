"""
5-Qubit Chip Layout Design (IBM Falcon / Cross Topology)
Defines qubit positions, resonator coupling strengths, and readout frequencies.
"""
import numpy as np
import json
import os
from typing import Dict, List, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Chip layout: 5-qubit cross topology
# Q0 - Q1 - Q2
#      |
#      Q3
#      |
#      Q4
# IBM Falcon has this topology but here we use a clean "+" cross:
#       Q1
#       |
#  Q0 - Q2 - Q4
#       |
#       Q3
# ─────────────────────────────────────────────────────────────────────────────

CHIP_WIDTH_MM = 7.0
CHIP_HEIGHT_MM = 7.0
QUBIT_SPACING_MM = 2.0  # center-to-center


def define_qubit_layout() -> Dict:
    """
    Define 5-qubit cross topology positions on chip.
    Units: mm from bottom-left corner.
    """
    cx, cy = CHIP_WIDTH_MM / 2, CHIP_HEIGHT_MM / 2
    d = QUBIT_SPACING_MM

    qubits = [
        {"id": 0, "label": "Q0", "x_mm": cx - d, "y_mm": cy, "role": "data"},
        {"id": 1, "label": "Q1", "x_mm": cx,     "y_mm": cy + d, "role": "data"},
        {"id": 2, "label": "Q2", "x_mm": cx,     "y_mm": cy, "role": "center_coupler"},
        {"id": 3, "label": "Q3", "x_mm": cx,     "y_mm": cy - d, "role": "data"},
        {"id": 4, "label": "Q4", "x_mm": cx + d, "y_mm": cy, "role": "data"},
    ]
    return qubits


def compute_coupling_strength(
    qubit_i: Dict,
    qubit_j: Dict,
    coupling_capacitance_fF: float = 5.0,
    qubit_capacitance_fF: float = 70.0,
) -> float:
    """
    Estimate transverse coupling strength g between adjacent qubits.
    g/2π ≈ (Cc / 2C_q) * sqrt(ω_i * ω_j) [simplified capacitive model]
    Returns coupling in MHz.
    """
    dx = qubit_i["x_mm"] - qubit_j["x_mm"]
    dy = qubit_i["y_mm"] - qubit_j["y_mm"]
    dist_mm = np.sqrt(dx ** 2 + dy ** 2)

    if dist_mm > QUBIT_SPACING_MM * 1.5:  # Not adjacent
        return 0.0

    # Coupling decays with distance beyond nearest neighbor
    g_base_MHz = 10.0  # typical nearest-neighbor coupling ~10 MHz
    g_MHz = g_base_MHz * (QUBIT_SPACING_MM / dist_mm) ** 2
    return round(float(g_MHz), 3)


def assign_qubit_frequencies() -> List[Dict]:
    """
    Assign qubit frequencies with frequency spacing to avoid spectator errors.
    Target: ~5 GHz center, ±200 MHz spacing to prevent ZZ crosstalk.
    """
    base_freq = 5.0  # GHz
    # Alternating frequency pattern to minimize crosstalk
    frequency_offsets = [-0.2, +0.2, 0.0, -0.15, +0.15]  # GHz offsets

    qubits = define_qubit_layout()
    for i, q in enumerate(qubits):
        q["frequency_GHz"] = round(base_freq + frequency_offsets[i], 3)
        q["anharmonicity_MHz"] = -300.0  # typical transmon anharmonicity
    return qubits


def design_readout_resonators(qubits: List[Dict]) -> List[Dict]:
    """
    Assign readout resonator frequencies (dispersive readout).
    Resonator: ω_r = ω_q + Δ, where Δ >> g²/Δ (dispersive limit)
    Typical: resonator ~200–300 MHz above qubit frequency.
    """
    resonators = []
    readout_offsets_GHz = [0.25, 0.30, 0.28, 0.27, 0.26]  # resonator above qubit

    for i, q in enumerate(qubits):
        f_r = q["frequency_GHz"] + readout_offsets_GHz[i]
        chi_MHz = 1.0  # dispersive shift ~1 MHz (typical)
        resonators.append({
            "qubit_id": q["id"],
            "resonator_freq_GHz": round(f_r, 4),
            "coupling_g_MHz": 80.0,  # qubit-resonator coupling
            "dispersive_shift_MHz": chi_MHz,
            "readout_fidelity_pct": 99.0,  # target readout fidelity
        })
    return resonators


def compute_all_couplings(qubits: List[Dict]) -> List[Dict]:
    """Compute coupling matrix for all qubit pairs."""
    couplings = []
    for i in range(len(qubits)):
        for j in range(i + 1, len(qubits)):
            g = compute_coupling_strength(qubits[i], qubits[j])
            if g > 0:
                couplings.append({
                    "qubit_i": qubits[i]["label"],
                    "qubit_j": qubits[j]["label"],
                    "coupling_MHz": g,
                    "connected": True,
                })
    return couplings


def main():
    print("=" * 60)
    print("5-Qubit Chip Layout Design (Cross Topology)")
    print("=" * 60)

    qubits = assign_qubit_frequencies()

    print("\n[1] Qubit Positions and Frequencies")
    print(f"  {'Label':<6} {'x(mm)':<8} {'y(mm)':<8} {'freq(GHz)':<12} {'Role'}")
    print("  " + "-" * 50)
    for q in qubits:
        print(f"  {q['label']:<6} {q['x_mm']:<8.2f} {q['y_mm']:<8.2f} {q['frequency_GHz']:<12.3f} {q['role']}")

    couplings = compute_all_couplings(qubits)
    print("\n[2] Qubit Coupling Strengths")
    for c in couplings:
        print(f"  {c['qubit_i']} -- {c['qubit_j']}: {c['coupling_MHz']} MHz")

    resonators = design_readout_resonators(qubits)
    print("\n[3] Readout Resonators")
    for r in resonators:
        print(f"  Q{r['qubit_id']}: f_r = {r['resonator_freq_GHz']:.4f} GHz, "
              f"g = {r['coupling_g_MHz']} MHz, χ = {r['dispersive_shift_MHz']} MHz")

    # Build adjacency from couplings
    topology_edges = [[c["qubit_i"], c["qubit_j"]] for c in couplings]

    output = {
        "n_qubits": len(qubits),
        "topology": "cross",
        "chip_size_mm": {"width": CHIP_WIDTH_MM, "height": CHIP_HEIGHT_MM},
        "qubit_positions": [{"label": q["label"], "x_mm": q["x_mm"], "y_mm": q["y_mm"]} for q in qubits],
        "qubit_frequencies_GHz": [q["frequency_GHz"] for q in qubits],
        "coupling_strengths_MHz": [c["coupling_MHz"] for c in couplings],
        "coupling_pairs": topology_edges,
        "readout_freqs_GHz": [r["resonator_freq_GHz"] for r in resonators],
        "qubit_details": qubits,
        "coupling_details": couplings,
        "resonator_details": resonators,
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "layout_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
