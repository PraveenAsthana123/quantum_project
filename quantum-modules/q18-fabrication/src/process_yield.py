"""
Fabrication Yield Model using Murphy's Law
Y = [(1 - exp(-A·D)) / (A·D)]²
Models quantum chip yield vs chip size and defect density.
"""
import numpy as np
import json
import os
from typing import Dict, List, Tuple


def murphy_yield(chip_area_mm2: float, defect_density_per_cm2: float) -> float:
    """
    Murphy's yield model: Y = [(1 - exp(-A·D)) / (A·D)]²
    A = chip area (cm²), D = defect density (defects/cm²)
    Returns yield as a fraction 0–1.
    """
    A_cm2 = chip_area_mm2 / 100.0  # mm² → cm²
    D = defect_density_per_cm2
    AD = A_cm2 * D
    if AD < 1e-12:
        return 1.0
    yield_val = ((1.0 - np.exp(-AD)) / AD) ** 2
    return float(yield_val)


def poisson_yield(chip_area_mm2: float, defect_density_per_cm2: float) -> float:
    """
    Simpler Poisson model: Y = exp(-A·D)
    Lower bound vs Murphy's model.
    """
    A_cm2 = chip_area_mm2 / 100.0
    return float(np.exp(-A_cm2 * defect_density_per_cm2))


def find_optimal_chip_size(
    defect_density_per_cm2: float,
    target_yield: float = 0.50,
    size_range_mm2: Tuple[float, float] = (0.5, 200.0),
    n_points: int = 1000,
) -> float:
    """
    Find largest chip size meeting target yield for a given defect density.
    Binary search on chip area.
    """
    lo, hi = size_range_mm2
    for _ in range(60):
        mid = (lo + hi) / 2
        if murphy_yield(mid, defect_density_per_cm2) >= target_yield:
            lo = mid
        else:
            hi = mid
    return round(lo, 3)


def yield_surface(
    chip_sizes_mm2: List[float],
    defect_densities: List[float],
) -> List[Dict]:
    """
    Compute yield surface over chip sizes × defect densities.
    """
    rows = []
    for D in defect_densities:
        row = {"defect_density_per_cm2": D, "murphy_yields_pct": [], "poisson_yields_pct": []}
        for A in chip_sizes_mm2:
            row["murphy_yields_pct"].append(round(murphy_yield(A, D) * 100, 2))
            row["poisson_yields_pct"].append(round(poisson_yield(A, D) * 100, 2))
        rows.append(row)
    return rows


def quantum_chip_yield_analysis() -> Dict:
    """
    Specific analysis for quantum processor chips.
    Quantum chips face additional yield killers vs classical:
    - Junction resistance variation (target ±5%)
    - TLS (two-level system) defects at interfaces
    - Qubit frequency spread
    """
    print("\n  Quantum-specific yield analysis:")

    # Typical defect densities for quantum chip fab
    # Source: academic reports on superconducting qubit fabrication
    defect_scenarios = {
        "advanced_fab_D01": 0.1,    # 0.1 defects/cm² (state-of-the-art)
        "mature_fab_D05": 0.5,      # 0.5 defects/cm² (good fab)
        "standard_fab_D20": 2.0,    # 2.0 defects/cm² (standard CMOS)
        "early_process_D50": 5.0,   # 5.0 defects/cm² (early development)
    }

    # Chip sizes for various qubit counts (rule of thumb: ~0.5 mm²/qubit)
    qubit_configs = {
        "5_qubit": 5.0,
        "10_qubit": 10.0,
        "27_qubit_falcon": 27.0,
        "65_qubit_hummingbird": 65.0,
        "127_qubit_eagle": 127.0,
    }

    results = []
    for config_name, chip_area in qubit_configs.items():
        for fab_name, D in defect_scenarios.items():
            y = murphy_yield(chip_area, D)
            results.append({
                "config": config_name,
                "chip_area_mm2": chip_area,
                "defect_density": D,
                "fab": fab_name,
                "yield_pct": round(y * 100, 2),
            })
            if "advanced" in fab_name:
                print(f"    {config_name} ({chip_area} mm²), D={D}: Y = {y*100:.1f}%")

    return {"quantum_yield_matrix": results}


def main():
    print("=" * 60)
    print("Fabrication Yield Model (Murphy's Law)")
    print("=" * 60)

    chip_sizes_mm2 = [1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 150.0, 200.0]
    defect_densities = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]  # defects/cm²

    print("\n[1] Murphy's Yield vs Chip Size (defect density = 1.0 /cm²)")
    print(f"  {'Chip Area (mm²)':<18} {'Murphy Y%':<14} {'Poisson Y%'}")
    print("  " + "-" * 50)
    for A in chip_sizes_mm2:
        Ym = murphy_yield(A, 1.0) * 100
        Yp = poisson_yield(A, 1.0) * 100
        print(f"  {A:<18.1f} {Ym:<14.2f} {Yp:.2f}")

    print("\n[2] Optimal Chip Size for 50% Yield")
    for D in [0.1, 0.5, 1.0, 2.0, 5.0]:
        opt = find_optimal_chip_size(D, target_yield=0.50)
        print(f"  D = {D:.1f} /cm² → max chip size for 50% yield: {opt} mm²")

    print("\n[3] Yield Surface — full matrix")
    surface = yield_surface(chip_sizes_mm2, defect_densities)
    for row in surface[:3]:
        D = row["defect_density_per_cm2"]
        print(f"  D={D}: {row['murphy_yields_pct'][:4]} ... (first 4 sizes)")

    qc_analysis = quantum_chip_yield_analysis()

    optimal_chip_sizes = {
        f"D_{D}": find_optimal_chip_size(D, target_yield=0.50)
        for D in defect_densities
    }

    output = {
        "chip_sizes_mm2": chip_sizes_mm2,
        "defect_densities": defect_densities,
        "yields_pct": [[murphy_yield(A, D) * 100 for A in chip_sizes_mm2] for D in defect_densities],
        "optimal_chip_size_mm2": optimal_chip_sizes,
        "yield_surface": surface,
        "quantum_analysis": qc_analysis,
        "model": "Murphy: Y = [(1-exp(-AD))/(AD)]²",
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "yield_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
