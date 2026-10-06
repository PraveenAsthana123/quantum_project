"""
Thermal Anchoring Design for Qubit Chip at 20mK
Models heat conduction through indium solder, gold wire bonds, and sapphire substrate.
"""
import numpy as np
import json
import os
from typing import Dict, List


# ─────────────────────────────────────────────────────────────────────────────
# Thermal conductivity at 20 mK (μW / (mm·K)) — cryogenic values
# Bulk room-temperature values scale as κ ∝ T for metals (Wiedemann-Franz)
# ─────────────────────────────────────────────────────────────────────────────

# At 20 mK, thermal conductivities (W/m·K) — from cryogenic materials literature
THERMAL_CONDUCTIVITY = {
    "indium_solder": 0.081,        # W/(m·K) at 20 mK (In is superconducting below 3.4 K)
    "gold_wire": 0.30,             # W/(m·K) at 20 mK (reduced from 300 W/(m·K) at RT)
    "sapphire_substrate": 0.001,   # W/(m·K) at 20 mK (very low, insulating)
    "copper_clamp": 0.50,          # W/(m·K) at 20 mK (OFHC Cu, best thermal anchor)
    "silver_epoxy": 0.010,         # W/(m·K) at 20 mK
}


def thermal_conductance(
    material: str,
    cross_section_mm2: float,
    length_mm: float,
) -> float:
    """
    Thermal conductance: G = κ * A / L   (W/K → μW/K for cryogenic use)
    Returns conductance in μW/K.
    """
    kappa = THERMAL_CONDUCTIVITY.get(material, 0.0)
    A_m2 = cross_section_mm2 * 1e-6  # mm² → m²
    L_m = length_mm * 1e-3            # mm → m
    if L_m <= 0:
        return 0.0
    G_W_per_K = kappa * A_m2 / L_m
    G_uW_per_K = G_W_per_K * 1e6
    return round(float(G_uW_per_K), 6)


def qubit_chip_temperature(
    heat_load_nW: float,
    thermal_conductance_uW_per_K: float,
    cold_plate_mK: float = 20.0,
) -> float:
    """
    Qubit temperature: T_qubit = T_cold_plate + Q/G
    Q = heat load (nW = 1e-9 W), G = conductance (μW/K = 1e-6 W/K)
    Returns qubit temperature in mK.
    """
    Q_W = heat_load_nW * 1e-9
    G_W_per_K = thermal_conductance_uW_per_K * 1e-6
    if G_W_per_K <= 0:
        return np.inf
    delta_T_K = Q_W / G_W_per_K
    T_qubit_mK = cold_plate_mK + delta_T_K * 1000.0
    return round(float(T_qubit_mK), 4)


def model_thermal_chain() -> List[Dict]:
    """
    Full thermal chain from qubit chip to cold plate (mixing chamber).
    Chain: qubit chip → substrate → solder bumps/bonds → cold plate.
    """
    # Component geometries (approximate)
    components = [
        {
            "name": "sapphire_substrate",
            "material": "sapphire_substrate",
            "cross_section_mm2": 49.0,   # 7mm × 7mm chip
            "length_mm": 0.5,            # 500 μm substrate thickness
            "description": "Chip substrate thermal resistance",
        },
        {
            "name": "indium_bumps",
            "material": "indium_solder",
            "cross_section_mm2": 0.05,   # ~200 bumps × 0.25 μm² each
            "length_mm": 0.010,          # 10 μm bump height
            "description": "Flip-chip indium bump thermal path",
        },
        {
            "name": "gold_wire_bonds",
            "material": "gold_wire",
            "cross_section_mm2": 0.0005,  # 25 μm diameter wire, ~20 bonds
            "length_mm": 1.0,
            "description": "Gold wire bond thermal anchor",
        },
        {
            "name": "copper_clamp",
            "material": "copper_clamp",
            "cross_section_mm2": 100.0,  # Large Cu bracket
            "length_mm": 5.0,
            "description": "OFHC copper clamp to mixing chamber plate",
        },
    ]

    results = []
    for c in components:
        G = thermal_conductance(c["material"], c["cross_section_mm2"], c["length_mm"])
        results.append({
            "component": c["name"],
            "material": c["material"],
            "thermal_conductance_uW_per_K": G,
            "thermal_resistance_K_per_uW": round(1.0 / G, 6) if G > 0 else np.inf,
            "cross_section_mm2": c["cross_section_mm2"],
            "length_mm": c["length_mm"],
            "description": c["description"],
        })
    return results


def total_series_resistance(components: List[Dict]) -> float:
    """Total thermal resistance of series-connected path (K/μW)."""
    R_total = sum(c["thermal_resistance_K_per_uW"] for c in components if c["thermal_resistance_K_per_uW"] != np.inf)
    return round(R_total, 6)


def main():
    print("=" * 60)
    print("Thermal Anchoring Design — Qubit Chip at 20 mK")
    print("=" * 60)

    print("\n[1] Thermal Conductivities at 20 mK")
    for mat, k in THERMAL_CONDUCTIVITY.items():
        print(f"  {mat:<25}: κ = {k:.4f} W/(m·K)")

    print("\n[2] Thermal Conductance per Component")
    components = model_thermal_chain()
    print(f"  {'Component':<25} {'G (μW/K)':<14} {'R (K/μW)':<14} {'Material'}")
    print("  " + "-" * 70)
    for c in components:
        R_str = f"{c['thermal_resistance_K_per_uW']:.6f}" if c["thermal_resistance_K_per_uW"] != np.inf else "∞"
        print(f"  {c['component']:<25} {c['thermal_conductance_uW_per_K']:<14.6f} {R_str:<14} {c['material']}")

    R_total = total_series_resistance(components)
    G_total = 1.0 / R_total if R_total > 0 else 0
    print(f"\n  Total series resistance: {R_total:.6f} K/μW")
    print(f"  Total conductance      : {G_total:.6f} μW/K")

    print("\n[3] Qubit Temperature vs Heat Load")
    heat_loads_nW = [1.0, 5.0, 10.0, 50.0, 100.0, 500.0]
    for Q_nW in heat_loads_nW:
        T_qubit = qubit_chip_temperature(Q_nW, G_total)
        flag = " <-- significantly above base!" if T_qubit > 50 else ""
        print(f"  Q = {Q_nW:6.1f} nW → T_qubit = {T_qubit:.2f} mK{flag}")

    # Find max heat load for T_qubit < 30 mK
    for Q_nW in np.linspace(0.1, 1000, 10000):
        T = qubit_chip_temperature(Q_nW, G_total)
        if T > 30.0:
            print(f"\n  Max heat load for T<30mK: ~{Q_nW:.1f} nW")
            break

    output = {
        "materials": list(THERMAL_CONDUCTIVITY.keys()),
        "thermal_conductances_uW_per_K": [c["thermal_conductance_uW_per_K"] for c in components],
        "total_conductance_uW_per_K": round(G_total, 6),
        "qubit_temp_mK": {
            f"{Q_nW}nW": qubit_chip_temperature(Q_nW, G_total)
            for Q_nW in [1.0, 5.0, 10.0, 50.0, 100.0]
        },
        "heat_load_nW": heat_loads_nW,
        "component_chain": components,
        "cold_plate_temp_mK": 20.0,
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "thermal_anchor_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
