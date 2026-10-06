"""
Q27 — Quantum Clocks
time_transfer.py

Optical time transfer over a fibre link.
Signal path: clock → fibre link (1000 km) → remote clock.
Noise sources: thermal expansion, Doppler shift, turbulence.
Active noise cancellation via phase-conjugate reflection.

Reference: Predehl et al., Science 336, 441 (2012);
           Droste et al., PRL 111, 110801 (2013).

Outputs: data/time_transfer_results.json
"""

import json
import math
import os
import random


# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

C = 3.0e8              # speed of light [m/s]
C_FIBER = C / 1.467    # speed in silica fibre at 1550 nm [m/s]
THERMAL_EXPANSION_SILICA = 5.5e-7   # relative: ΔL/L per °C


# ---------------------------------------------------------------------------
# Noise sources
# ---------------------------------------------------------------------------

def thermal_noise_fs(fiber_length_km: float,
                      temperature_rms_C: float = 0.01) -> float:
    """
    Timing noise from thermal expansion of fibre.
    ΔL = α * L * ΔT → Δt = ΔL / c_fiber = α * L * ΔT / c_fiber

    Returned in femtoseconds (fs).
    """
    delta_L = THERMAL_EXPANSION_SILICA * fiber_length_km * 1e3 * temperature_rms_C  # m
    delta_t_s = delta_L / C_FIBER
    return delta_t_s * 1e15  # fs


def doppler_noise_fs(fiber_length_km: float,
                      vibration_velocity_m_per_s: float = 1e-6) -> float:
    """
    Doppler noise from acoustic vibrations causing path-length modulation.
    Δν/ν = v/c → Δt = Δν * t_prop / ν ≈ (v/c) * (L/c)

    Returns timing noise in fs.
    """
    t_prop_s = fiber_length_km * 1e3 / C_FIBER
    delta_t_s = (vibration_velocity_m_per_s / C) * t_prop_s
    return delta_t_s * 1e15  # fs


def turbulence_noise_fs(fiber_length_km: float,
                         n_splices: int = None) -> float:
    """
    Index-of-refraction fluctuations from turbulence and pressure.
    δn ≈ 1e-9 per km typical; Δt = δn * L / c.
    Also includes splice-point scattering.
    """
    if n_splices is None:
        n_splices = int(fiber_length_km / 4)  # ~1 splice per 4 km
    delta_n = 1e-9  # typical rms fluctuation
    delta_t_s = delta_n * fiber_length_km * 1e3 / C_FIBER
    splice_noise_s = n_splices * 5e-18  # ~5 as per splice
    return (delta_t_s + splice_noise_s) * 1e15  # fs


def total_noise_without_cancellation(fiber_length_km: float) -> float:
    """Total uncancelled noise in quadrature."""
    thermal = thermal_noise_fs(fiber_length_km)
    doppler = doppler_noise_fs(fiber_length_km)
    turb = turbulence_noise_fs(fiber_length_km)
    return math.sqrt(thermal ** 2 + doppler ** 2 + turb ** 2)


# ---------------------------------------------------------------------------
# Active noise cancellation
# ---------------------------------------------------------------------------

def cancellation_efficiency(fiber_length_km: float,
                              bandwidth_Hz: float = 1e4,
                              servo_gain: float = 1e4) -> float:
    """
    Active phase-noise cancellation efficiency.

    The servo corrects fast noise up to bandwidth f_BW.
    Residual noise ≈ noise_0 / servo_gain for f < f_BW.
    High-frequency noise (f > f_BW) is uncancelled.
    Typical state-of-art: >40 dB suppression → 99%+ for dominant terms.

    Returns fraction of noise cancelled (0–1).
    """
    # Round-trip delay limits bandwidth: f_max = c/(2L)
    f_max_Hz = C_FIBER / (2.0 * fiber_length_km * 1e3)
    usable_BW = min(bandwidth_Hz, f_max_Hz)

    # Efficiency degrades for very long links (bandwidth-delay product)
    efficiency = min(0.9999, 1.0 - 1.0 / servo_gain)
    if usable_BW < 1:
        efficiency *= usable_BW  # graceful degradation
    return efficiency


def residual_noise_after_cancellation(
        fiber_length_km: float,
        servo_gain: float = 1e4,
        bandwidth_Hz: float = 1e4) -> float:
    """
    Residual timing noise after active cancellation [fs].
    """
    raw_noise = total_noise_without_cancellation(fiber_length_km)
    eta = cancellation_efficiency(fiber_length_km, bandwidth_Hz, servo_gain)
    return raw_noise * (1.0 - eta)


# ---------------------------------------------------------------------------
# Record-level comparison
# ---------------------------------------------------------------------------

RECORD_ACCURACY_FS = 19.0   # Predehl et al. 2012: 19 fs over 920 km


def compare_to_record(final_accuracy_fs: float,
                       fiber_length_km: float) -> dict:
    """Compare simulated result to published record."""
    return {
        "record_fs": RECORD_ACCURACY_FS,
        "record_distance_km": 920.0,
        "simulated_fs": round(final_accuracy_fs, 2),
        "simulated_distance_km": fiber_length_km,
        "within_order": abs(math.log10(max(final_accuracy_fs, 1e-3) / RECORD_ACCURACY_FS)) < 2.0,
    }


# ---------------------------------------------------------------------------
# Full simulation
# ---------------------------------------------------------------------------

def simulate_time_transfer(
        fiber_length_km: float = 1000.0,
        temperature_rms_C: float = 0.01,
        vibration_velocity_m_s: float = 1e-6,
        servo_gain: float = 1e4,
        bandwidth_Hz: float = 1e4,
        seed: int = 42) -> dict:
    """
    Simulate optical time transfer over a fibre link.
    """
    random.seed(seed)

    # Individual noise sources
    thermal = thermal_noise_fs(fiber_length_km, temperature_rms_C)
    doppler = doppler_noise_fs(fiber_length_km, vibration_velocity_m_s)
    turb = turbulence_noise_fs(fiber_length_km)
    total_uncancelled = math.sqrt(thermal ** 2 + doppler ** 2 + turb ** 2)

    # After cancellation
    eta = cancellation_efficiency(fiber_length_km, bandwidth_Hz, servo_gain)
    final_accuracy = residual_noise_after_cancellation(
        fiber_length_km, servo_gain, bandwidth_Hz)

    record_comparison = compare_to_record(final_accuracy, fiber_length_km)

    print(f"Fibre length          : {fiber_length_km:.0f} km")
    print(f"Thermal noise         : {thermal:.4f} fs")
    print(f"Doppler noise         : {doppler:.4f} fs")
    print(f"Turbulence noise      : {turb:.4f} fs")
    print(f"Total (uncancelled)   : {total_uncancelled:.4f} fs")
    print(f"Cancellation eff.     : {eta*100:.3f}%")
    print(f"Final accuracy        : {final_accuracy:.4f} fs")
    print(f"Record (Predehl 2012) : {RECORD_ACCURACY_FS:.0f} fs @ 920 km")

    return {
        "fiber_length_km": fiber_length_km,
        "thermal_noise_fs": round(thermal, 4),
        "doppler_noise_fs": round(doppler, 4),
        "turbulence_noise_fs": round(turb, 4),
        "total_uncancelled_fs": round(total_uncancelled, 4),
        "cancellation_efficiency": round(eta, 6),
        "final_accuracy_fs": round(final_accuracy, 4),
        "record_accuracy_fs": RECORD_ACCURACY_FS,
        "servo_gain": servo_gain,
        "bandwidth_Hz": bandwidth_Hz,
        "record_comparison": record_comparison,
    }


# ---------------------------------------------------------------------------
# Distance sweep
# ---------------------------------------------------------------------------

def distance_sweep(distances_km=None) -> list:
    """Final accuracy vs fibre length."""
    if distances_km is None:
        distances_km = [100, 250, 500, 920, 1000, 1500, 2000]
    rows = []
    for d in distances_km:
        acc = residual_noise_after_cancellation(d)
        rows.append({
            "distance_km": d,
            "final_accuracy_fs": round(acc, 4),
        })
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Optical Time Transfer via Fibre ===\n")

    results = simulate_time_transfer(fiber_length_km=1000.0)

    print("\n--- Distance sweep ---")
    sweep = distance_sweep()
    for row in sweep:
        print(f"  {row['distance_km']:5.0f} km  →  "
              f"{row['final_accuracy_fs']:.4f} fs")

    results["distance_sweep"] = sweep

    os.makedirs("data", exist_ok=True)
    out_path = "data/time_transfer_results.json"
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
