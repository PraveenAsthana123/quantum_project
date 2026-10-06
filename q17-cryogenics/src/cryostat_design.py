"""
Cryostat Wiring Design for 50-Qubit System
Models coaxial lines, DC lines, connectors, and heat loads at each stage.
"""
import numpy as np
import json
import os
from typing import Dict, List


# ─────────────────────────────────────────────────────────────────────────────
# Wire/line type heat load coefficients
# Heat load per line at 20mK stage (μW) — from literature and vendor specs
# ─────────────────────────────────────────────────────────────────────────────

# Coaxial line (UT-085 stainless/NbTi cryo coax): ~0.05 μW per line at base
COAX_HEAT_LOAD_BASE_UW = 0.05
# DC bias line (twisted pair, phosphor bronze): ~0.02 μW per line at base
DC_LINE_HEAT_LOAD_BASE_UW = 0.02
# Readout coax (semi-rigid, higher conduction): ~0.1 μW per line at base
READOUT_COAX_HEAT_LOAD_BASE_UW = 0.10

# Lines per qubit
CONTROL_COAX_PER_QUBIT = 2   # XY control + Z/flux
READOUT_COAX_PER_QUBIT = 2   # input + output (shared per pair often)
DC_LINES_PER_QUBIT = 1        # DC flux bias

# SMA connectors per coax line (one at each stage cross-through)
SMA_PER_COAX = 5  # one per temperature stage boundary


def compute_wiring(n_qubits: int) -> Dict:
    """
    Compute total wire counts for n_qubits.
    """
    control_coax = n_qubits * CONTROL_COAX_PER_QUBIT
    readout_coax = n_qubits * READOUT_COAX_PER_QUBIT
    dc_lines = n_qubits * DC_LINES_PER_QUBIT
    total_coax = control_coax + readout_coax
    total_sma = total_coax * SMA_PER_COAX

    return {
        "n_qubits": n_qubits,
        "control_coax_lines": control_coax,
        "readout_coax_lines": readout_coax,
        "total_coax_lines": total_coax,
        "dc_lines": dc_lines,
        "sma_connectors": total_sma,
    }


def compute_heat_loads_per_stage(wiring: Dict) -> List[Dict]:
    """
    Estimate heat load contribution from wiring at each cryostat stage.
    Heat load scales with temperature gradient: roughly proportional to T_stage / T_base.
    Base (20 mK) has the smallest heat load per line; 4K stage has highest.
    """
    stages = [
        {"name": "77K",   "T_K": 77.0,   "scale": 50.0},  # relative to base
        {"name": "4K",    "T_K": 4.0,    "scale": 10.0},
        {"name": "1K",    "T_K": 0.9,    "scale": 3.0},
        {"name": "100mK", "T_K": 0.1,    "scale": 1.5},
        {"name": "20mK",  "T_K": 0.020,  "scale": 1.0},  # base case
    ]

    n_coax = wiring["total_coax_lines"]
    n_dc = wiring["dc_lines"]
    n_readout = wiring["readout_coax_lines"]

    results = []
    for s in stages:
        sc = s["scale"]
        coax_heat = n_coax * COAX_HEAT_LOAD_BASE_UW * sc
        dc_heat = n_dc * DC_LINE_HEAT_LOAD_BASE_UW * sc
        readout_heat = n_readout * READOUT_COAX_HEAT_LOAD_BASE_UW * sc
        total_heat = coax_heat + dc_heat + readout_heat

        results.append({
            "stage": s["name"],
            "temperature_K": s["T_K"],
            "coax_heat_load_mW": round(coax_heat / 1000, 4),
            "dc_heat_load_mW": round(dc_heat / 1000, 4),
            "readout_heat_load_mW": round(readout_heat / 1000, 4),
            "total_heat_load_mW": round(total_heat / 1000, 4),
            "total_heat_load_uW": round(total_heat, 2),
        })
    return results


def recommend_wiring_strategy(n_qubits: int, heat_loads: List[Dict]) -> str:
    """
    Check if the heat load at 20 mK exceeds typical DR capacity and recommend strategy.
    """
    base_stage = next(s for s in heat_loads if s["stage"] == "20mK")
    base_heat_uW = base_stage["total_heat_load_uW"]

    # Typical mixing chamber cooling power at 20 mK
    TYPICAL_COOLING_POWER_UW = 20.0

    lines = []
    if base_heat_uW > TYPICAL_COOLING_POWER_UW:
        lines.append(
            f"WARNING: Wiring heat load ({base_heat_uW:.1f} μW) exceeds typical "
            f"mixing chamber cooling power ({TYPICAL_COOLING_POWER_UW} μW)."
        )
        lines.append("Recommendations:")
        lines.append("  1. Use NbTi/NbTiN superconducting coax below 4K (near-zero thermal conduction)")
        lines.append("  2. Install in-line attenuators at 4K, 1K, 20mK stages")
        lines.append("  3. Use cryogenic switches/multiplexers to reduce physical line count")
        lines.append("  4. Consider larger DR system (e.g., Bluefors XLD with 40+ μW capacity)")
    else:
        lines.append(
            f"OK: Wiring heat load ({base_heat_uW:.1f} μW) is within "
            f"typical mixing chamber capacity ({TYPICAL_COOLING_POWER_UW} μW)."
        )
    return "\n".join(lines)


def main():
    print("=" * 60)
    print("Cryostat Wiring Design — 50-Qubit System")
    print("=" * 60)

    n_qubits = 50
    wiring = compute_wiring(n_qubits)

    print(f"\n[1] Wiring Count for {n_qubits} qubits")
    print(f"  Control coax lines  : {wiring['control_coax_lines']}")
    print(f"  Readout coax lines  : {wiring['readout_coax_lines']}")
    print(f"  Total coax lines    : {wiring['total_coax_lines']}")
    print(f"  DC bias lines       : {wiring['dc_lines']}")
    print(f"  SMA connectors      : {wiring['sma_connectors']}")

    heat_loads = compute_heat_loads_per_stage(wiring)

    print(f"\n[2] Heat Loads per Stage")
    print(f"  {'Stage':<10} {'Temp(K)':<10} {'Coax(mW)':<12} {'DC(mW)':<10} {'Total(mW)':<12} {'Total(μW)'}")
    print("  " + "-" * 65)
    for s in heat_loads:
        print(f"  {s['stage']:<10} {s['temperature_K']:<10.3f} {s['coax_heat_load_mW']:<12.4f} "
              f"{s['dc_heat_load_mW']:<10.4f} {s['total_heat_load_mW']:<12.4f} {s['total_heat_load_uW']:.2f}")

    rec = recommend_wiring_strategy(n_qubits, heat_loads)
    print(f"\n[3] Recommendation\n{rec}")

    # Recommended stages (standard DR topology)
    recommended_stages = ["77K", "4K", "1K", "100mK", "20mK"]

    output = {
        "n_qubits": n_qubits,
        "coax_lines": wiring["total_coax_lines"],
        "dc_lines": wiring["dc_lines"],
        "sma_connectors": wiring["sma_connectors"],
        "total_heat_load_mW": heat_loads[-1]["total_heat_load_mW"],
        "recommended_stages": recommended_stages,
        "wiring_details": wiring,
        "heat_loads_by_stage": heat_loads,
        "recommendation": rec,
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "cryostat_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
