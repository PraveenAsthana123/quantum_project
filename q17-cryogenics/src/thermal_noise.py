"""
Thermal Noise and Decoherence Model
Calculates thermal occupation, T1 limits from thermal radiation,
and shows the ~100 mK transition where thermal noise begins to dominate.
"""
import numpy as np
import json
import os
from typing import Dict, List


# Physical constants
KB = 1.380649e-23   # J/K
HBAR = 1.054571817e-34  # J·s


def thermal_occupation(freq_GHz: float, temperature_K: float) -> float:
    """
    Bose-Einstein thermal occupation: nₜₕ = 1/(exp(ℏω/kT) - 1)
    Returns 0 for T=0 or extremely high frequency.
    """
    if temperature_K <= 0:
        return 0.0
    omega = 2 * np.pi * freq_GHz * 1e9
    exponent = HBAR * omega / (KB * temperature_K)
    if exponent > 500:
        return 0.0
    if exponent < 1e-10:
        return KB * temperature_K / (HBAR * omega)  # classical limit
    return 1.0 / (np.expm1(exponent))


def t1_thermal_limit(
    freq_GHz: float,
    temperature_K: float,
    gamma_0_MHz: float = 0.01,
) -> float:
    """
    T1 limited by thermal excitation.
    Total relaxation rate: Γ₁ = (nₜₕ+1)·γ + nₜₕ·γ = (2nₜₕ+1)·γ
    where γ = γ₀ is the zero-temperature spontaneous emission rate.
    T1 = 1/Γ₁  (in μs)
    """
    nth = thermal_occupation(freq_GHz, temperature_K)
    gamma_0_Hz = gamma_0_MHz * 1e6
    gamma_total_Hz = (2 * nth + 1) * gamma_0_Hz
    if gamma_total_Hz <= 0:
        return np.inf
    t1_us = 1.0 / gamma_total_Hz * 1e6  # convert to μs
    return float(t1_us)


def compute_thermal_dominated_threshold(freq_GHz: float, nth_threshold: float = 0.01) -> float:
    """
    Find temperature above which thermal noise is 'dominant' (nth > threshold).
    Binary search in temperature space.
    """
    lo, hi = 1e-3, 5.0  # 1 mK to 5 K
    for _ in range(60):
        mid = (lo + hi) / 2
        if thermal_occupation(freq_GHz, mid) < nth_threshold:
            lo = mid
        else:
            hi = mid
    return round(hi * 1000, 2)  # return in mK


def sweep_frequencies_and_temperatures() -> List[Dict]:
    """
    Full sweep: qubit frequencies 3-8 GHz × temperatures 10-1000 mK.
    """
    freqs_GHz = [3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    temps_mK = [10, 20, 50, 100, 150, 200, 300, 500, 1000]

    results = []
    for T_mK in temps_mK:
        T_K = T_mK * 1e-3
        row = {
            "temperature_mK": T_mK,
            "temperature_K": T_K,
            "data_by_freq": [],
        }
        for f in freqs_GHz:
            nth = thermal_occupation(f, T_K)
            t1 = t1_thermal_limit(f, T_K)
            row["data_by_freq"].append({
                "freq_GHz": f,
                "nth": float(f"{nth:.4e}"),
                "t1_thermal_us": round(t1, 4) if t1 < 1e6 else ">>1M",
            })
        results.append(row)
    return results


def compute_t1_summary(
    freqs_GHz: List[float],
    temperatures_mK: List[float],
    gamma_0_MHz: float = 0.01,
) -> Dict:
    """Build summary tables for JSON output."""
    nth_table = []
    t1_table = []

    for f in freqs_GHz:
        nth_row = {"freq_GHz": f}
        t1_row = {"freq_GHz": f}
        for T_mK in temperatures_mK:
            T_K = T_mK * 1e-3
            nth = thermal_occupation(f, T_K)
            t1 = t1_thermal_limit(f, T_K, gamma_0_MHz)
            nth_row[f"T_{T_mK}mK"] = float(f"{nth:.4e}")
            t1_row[f"T_{T_mK}mK_us"] = round(t1, 3) if t1 < 1e5 else 1e5
        nth_table.append(nth_row)
        t1_table.append(t1_row)

    return {"nth_table": nth_table, "t1_table": t1_table}


def main():
    print("=" * 60)
    print("Thermal Noise and Decoherence Model")
    print("=" * 60)

    freqs_GHz = [3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    temps_mK = [10, 20, 50, 100, 150, 200, 300, 500, 1000]

    print("\n[1] Thermal Occupation nₜₕ(T) for 5 GHz qubit")
    print(f"  {'T (mK)':<10} {'n_th':<16} {'T1 limit (μs)':<18} {'Note'}")
    print("  " + "-" * 60)
    for T_mK in temps_mK:
        T_K = T_mK * 1e-3
        nth = thermal_occupation(5.0, T_K)
        t1 = t1_thermal_limit(5.0, T_K)
        note = "thermal noise dominates" if nth > 0.01 else ""
        t1_str = f"{t1:.2f}" if t1 < 1e5 else ">100,000"
        print(f"  {T_mK:<10} {nth:<16.4e} {t1_str:<18} {note}")

    print("\n[2] Thermal Dominance Threshold (nₜₕ > 0.01)")
    for f in freqs_GHz:
        T_thresh_mK = compute_thermal_dominated_threshold(f, nth_threshold=0.01)
        print(f"  f = {f:.1f} GHz  →  thermal noise dominates above T ~ {T_thresh_mK:.1f} mK")

    print("\n[3] T1 Limits from Thermal Radiation")
    print("  (γ₀ = 0.01 MHz spontaneous emission rate)")
    for f in [5.0]:
        for T_mK in [20, 100, 200]:
            T_K = T_mK * 1e-3
            t1 = t1_thermal_limit(f, T_K)
            print(f"  T={T_mK} mK, f={f} GHz → T1_thermal = {t1:.2f} μs")

    # Build JSON output
    summary = compute_t1_summary(freqs_GHz, temps_mK)
    sweep = sweep_frequencies_and_temperatures()

    output = {
        "frequencies_GHz": freqs_GHz,
        "temperatures_mK": temps_mK,
        "gamma_0_MHz": 0.01,
        "thermal_occupations": summary["nth_table"],
        "t1_limited_us": summary["t1_table"],
        "full_sweep": sweep,
        "thermal_dominance_thresholds_mK": {
            f"{f}GHz": compute_thermal_dominated_threshold(f)
            for f in freqs_GHz
        },
        "note": (
            "Above ~100 mK, thermal photon number nₜₕ > 0.01 for typical GHz qubits, "
            "limiting T1 and causing significant thermal excitation errors. "
            "Γ₁ = (2nₜₕ+1)·γ₀ with γ₀ = 0.01 MHz."
        ),
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "thermal_noise_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
