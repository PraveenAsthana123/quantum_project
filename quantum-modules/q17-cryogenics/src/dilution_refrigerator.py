"""
Dilution Refrigerator Thermal Model
Models heat loads at each stage, cooling powers, and maximum qubit capacity.
"""
import numpy as np
import json
import os
from typing import Dict, List


# Physical constants
KB = 1.380649e-23  # J/K


# ─────────────────────────────────────────────────────────────────────────────
# Dilution fridge stage parameters
# Based on commercially available systems (e.g., Bluefors LD/XLD, Oxford Triton)
# ─────────────────────────────────────────────────────────────────────────────

STAGES = [
    {
        "name": "77K",
        "temperature_K": 77.0,
        # Liquid nitrogen precooling stage
        "cooling_power_uW": 1e9,   # essentially unlimited (LN2 bath, ~1 kW capacity)
        "typical_heat_load_uW": 5e7,  # radiation + conduction from room temperature
        "description": "LN2 precooling / radiation shield",
    },
    {
        "name": "4K",
        "temperature_K": 4.2,
        # Pulse tube cooler first stage
        "cooling_power_uW": 4e6,   # ~4 W typical pulse tube 1st stage
        "typical_heat_load_uW": 5e5,  # ~0.5 W: coaxial cable conduction + radiation
        "description": "Pulse tube 1st stage",
    },
    {
        "name": "1K",
        "temperature_K": 0.9,
        # Pulse tube cooler second stage
        "cooling_power_uW": 4e4,   # ~40 mW typical PT 2nd stage
        "typical_heat_load_uW": 2e3,  # ~2 mW
        "description": "Pulse tube 2nd stage / 4He pot",
    },
    {
        "name": "100mK",
        "temperature_K": 0.1,
        # Still of the dilution unit
        "cooling_power_uW": 400.0,  # ~400 μW
        "typical_heat_load_uW": 50.0,
        "description": "Dilution still (~700 mK operating)",
    },
    {
        "name": "20mK",
        "temperature_K": 0.020,
        # Mixing chamber base temperature
        "cooling_power_uW": 20.0,   # ~20 μW at 20 mK for large systems
        "typical_heat_load_uW": 5.0,
        "description": "Mixing chamber (base temperature)",
    },
]

# Heat per qubit at base temperature (estimated)
# Sources: control wiring (~0.1 μW/line), readout (~0.05 μW/qubit), stray radiation
HEAT_PER_QUBIT_UW = 0.15   # μW per qubit at 20 mK stage
SAFETY_MARGIN = 0.5         # Use only 50% of cooling power to maintain stability


def compute_cooling_power_vs_temperature(
    t_min_mK: float = 10.0,
    t_max_mK: float = 200.0,
    n_points: int = 50,
) -> Dict:
    """
    Model cooling power of 3He-4He dilution as function of temperature.
    Q_mix ≈ 84 * n_dot * T²  (μW), where n_dot is 3He circulation rate (mmol/s).
    For a typical DR: n_dot ~ 0.3 mmol/s → Q_mix ≈ 25 * T² μW (T in K).
    """
    n_dot_mmol_s = 0.3  # typical 3He circulation rate
    coeff = 84 * n_dot_mmol_s  # μW / K²

    temps_K = np.linspace(t_min_mK * 1e-3, t_max_mK * 1e-3, n_points)
    cooling_powers_uW = coeff * temps_K ** 2

    return {
        "temperatures_mK": [round(t * 1000, 2) for t in temps_K.tolist()],
        "cooling_powers_uW": [round(p, 4) for p in cooling_powers_uW.tolist()],
        "coeff_uW_per_K2": round(coeff, 2),
        "n_dot_mmol_s": n_dot_mmol_s,
    }


def estimate_max_qubits(
    base_cooling_power_uW: float = 20.0,
    heat_per_qubit_uW: float = HEAT_PER_QUBIT_UW,
    safety_margin: float = SAFETY_MARGIN,
) -> Dict:
    """
    Estimate maximum number of qubits supportable at base temperature.
    Available power = safety_margin * cooling_power
    n_qubits = floor(available_power / heat_per_qubit)
    """
    available_uW = safety_margin * base_cooling_power_uW
    max_qubits = int(available_uW / heat_per_qubit_uW)

    breakdown = {
        "base_cooling_power_uW": base_cooling_power_uW,
        "safety_margin": safety_margin,
        "available_power_uW": round(available_uW, 4),
        "heat_per_qubit_uW": heat_per_qubit_uW,
        "max_qubits_estimate": max_qubits,
        "notes": (
            "Heat includes control line conduction (~0.1 μW) + readout (~0.05 μW). "
            "Larger systems (e.g. Bluefors XLD) may have 40+ μW at 20 mK → 130+ qubits."
        ),
    }
    return breakdown


def analyze_stages() -> List[Dict]:
    """Analyze margin and status at each temperature stage."""
    stage_results = []
    for s in STAGES:
        margin_uW = s["cooling_power_uW"] - s["typical_heat_load_uW"]
        margin_pct = 100.0 * margin_uW / s["cooling_power_uW"]
        stage_results.append({
            "stage": s["name"],
            "temperature_K": s["temperature_K"],
            "cooling_power_uW": s["cooling_power_uW"],
            "heat_load_uW": s["typical_heat_load_uW"],
            "margin_uW": round(margin_uW, 4),
            "margin_pct": round(margin_pct, 2),
            "status": "OK" if margin_pct > 20 else "MARGINAL" if margin_pct > 0 else "OVERLOADED",
            "description": s["description"],
        })
    return stage_results


def main():
    print("=" * 60)
    print("Dilution Refrigerator Thermal Model")
    print("=" * 60)

    # Stage analysis
    stage_results = analyze_stages()
    print(f"\n{'Stage':<8} {'Temp(K)':<10} {'Cool(μW)':<14} {'Load(μW)':<12} {'Margin%':<10} {'Status'}")
    print("  " + "-" * 65)
    for s in stage_results:
        print(f"  {s['stage']:<8} {s['temperature_K']:<10.3f} {s['cooling_power_uW']:<14.1f} "
              f"{s['heat_load_uW']:<12.1f} {s['margin_pct']:<10.1f} {s['status']}")

    # Cooling power curve
    print("\n[2] Cooling Power vs Temperature (20 mK → 200 mK)")
    cool_curve = compute_cooling_power_vs_temperature()
    for i in range(0, 50, 10):
        t = cool_curve["temperatures_mK"][i]
        p = cool_curve["cooling_powers_uW"][i]
        print(f"  T = {t:6.1f} mK  →  Q_cool = {p:.3f} μW")

    # Max qubits
    print("\n[3] Maximum Qubit Estimate at 20 mK")
    qubit_est = estimate_max_qubits()
    print(f"  Available cooling power: {qubit_est['available_power_uW']} μW "
          f"({int(SAFETY_MARGIN*100)}% of {qubit_est['base_cooling_power_uW']} μW)")
    print(f"  Heat per qubit         : {qubit_est['heat_per_qubit_uW']} μW")
    print(f"  Max qubits estimate    : {qubit_est['max_qubits_estimate']}")

    # Assemble output
    output = {
        "stages": [s["stage"] for s in stage_results],
        "temperatures_K": [s["temperature_K"] for s in stage_results],
        "cooling_powers_uW": [s["cooling_power_uW"] for s in stage_results],
        "heat_loads_uW": [s["heat_load_uW"] for s in stage_results],
        "max_qubits_estimate": qubit_est["max_qubits_estimate"],
        "qubit_heat_budget": qubit_est,
        "cooling_power_curve": cool_curve,
        "stage_analysis": stage_results,
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "dilution_fridge_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
