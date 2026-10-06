"""
Cryogenic Electronics Interface Model
Models signal attenuation from 300K to 20mK across 4 temperature stages,
Johnson-Nyquist noise, and thermal photon occupancy.
"""
import numpy as np
import json
import os
from typing import Dict, List


# Physical constants
KB = 1.380649e-23   # Boltzmann constant (J/K)
H_PLANCK = 6.62607015e-34  # Planck constant (J·s)
HBAR = H_PLANCK / (2 * np.pi)


# Standard dilution refrigerator temperature stages (K)
TEMPERATURE_STAGES = {
    "room_temp_K": 300.0,
    "cryo_cooler_K": 77.0,
    "4K_plate_K": 4.0,
    "still_K": 0.7,
    "cold_plate_K": 0.1,
    "base_mK": 0.020,
}

# Attenuation per stage (dB) on input coaxial lines
# Deliberately attenuate to reduce thermal noise photons traveling to qubit
STAGE_ATTENUATION_DB = {
    "300K_to_77K": 20.0,   # 20 dB attenuator + cable loss
    "77K_to_4K": 10.0,
    "4K_to_still": 20.0,
    "still_to_cold": 10.0,
    "cold_to_base": 20.0,
}

# Bandwidth for noise calculation (Hz)
BW_HZ = 1e9  # 1 GHz measurement bandwidth


def johnson_nyquist_noise_power(temperature_K: float, bandwidth_Hz: float) -> float:
    """
    Johnson-Nyquist noise power: P_noise = k_B * T * B  (classical limit)
    Valid when k_B*T >> h*f (true for f ~ GHz at T > 0.1 K approximately).
    Returns noise power in watts.
    """
    return KB * temperature_K * bandwidth_Hz


def noise_temperature_from_power(power_W: float, bandwidth_Hz: float) -> float:
    """Convert noise power to equivalent noise temperature in Kelvin."""
    return power_W / (KB * bandwidth_Hz)


def thermal_photon_number(freq_GHz: float, temperature_K: float) -> float:
    """
    Thermal photon occupation: nₜₕ = 1 / (exp(ℏω / k_B T) - 1)
    For T → 0 or very high frequency, nₜₕ → 0.
    """
    if temperature_K < 1e-6:
        return 0.0
    omega = 2 * np.pi * freq_GHz * 1e9
    exponent = HBAR * omega / (KB * temperature_K)
    if exponent > 700:
        return 0.0
    return 1.0 / (np.exp(exponent) - 1.0)


def db_to_linear(db: float) -> float:
    return 10 ** (db / 10.0)


def linear_to_db(linear: float) -> float:
    if linear <= 0:
        return -np.inf
    return 10 * np.log10(linear)


def compute_cascaded_noise(stages: List[Dict]) -> float:
    """
    Friis formula for cascaded noise: T_total = T1 + T2/G1 + T3/(G1*G2) + ...
    Each stage dict: {'T_noise_K': float, 'gain_linear': float}
    """
    t_total = stages[0]["T_noise_K"]
    cumulative_gain = stages[0]["gain_linear"]
    for stage in stages[1:]:
        t_total += stage["T_noise_K"] / cumulative_gain
        cumulative_gain *= stage["gain_linear"]
    return t_total


def simulate_attenuation_chain() -> Dict:
    """
    Model the full attenuation chain from 300K to 20mK.
    Returns per-stage attenuation, noise temperature, thermal photons, SNR.
    """
    qubit_freq_ghz = 5.0  # typical transmon frequency
    input_power_dBm = -20.0  # input drive power at room temperature

    stages = []
    temps = [300.0, 77.0, 4.0, 0.7, 0.1, 0.020]
    stage_names = ["300K", "77K", "4K", "700mK", "100mK", "20mK"]
    atts = [0.0, 20.0, 10.0, 20.0, 10.0, 20.0]  # dB attenuation at each boundary

    cumulative_attenuation_db = 0.0
    signal_power_dbm = input_power_dBm

    for i, (T, name, att) in enumerate(zip(temps, stage_names, atts)):
        cumulative_attenuation_db += att
        signal_power_dbm -= att

        noise_power_W = johnson_nyquist_noise_power(T, BW_HZ)
        noise_temp_K = noise_temperature_from_power(noise_power_W, BW_HZ)
        n_th = thermal_photon_number(qubit_freq_ghz, T)

        # SNR: signal vs thermal noise
        signal_power_W = 10 ** ((signal_power_dbm - 30) / 10.0)
        snr_db = linear_to_db(signal_power_W / noise_power_W) if noise_power_W > 0 else 100.0

        stages.append({
            "stage": name,
            "temperature_K": T,
            "cumulative_attenuation_dB": round(cumulative_attenuation_db, 1),
            "signal_power_dBm": round(signal_power_dbm, 2),
            "noise_power_W": float(f"{noise_power_W:.3e}"),
            "noise_temperature_K": round(noise_temp_K, 4),
            "thermal_photons_nth": float(f"{n_th:.4e}"),
            "snr_dB": round(float(snr_db), 2),
        })

    return {
        "qubit_frequency_GHz": qubit_freq_ghz,
        "input_power_dBm": input_power_dBm,
        "bandwidth_Hz": BW_HZ,
        "temperature_stages": [s["stage"] for s in stages],
        "temperatures_K": [s["temperature_K"] for s in stages],
        "attenuation_dB": [s["cumulative_attenuation_dB"] for s in stages],
        "noise_temperature_K": [s["noise_temperature_K"] for s in stages],
        "thermal_photons": [s["thermal_photons_nth"] for s in stages],
        "snr_dB": [s["snr_dB"] for s in stages],
        "stage_details": stages,
    }


def compute_thermal_photon_sweep() -> List[Dict]:
    """
    Compute thermal photon number for qubit frequencies 3-8 GHz at multiple temperatures.
    Shows clearly: above ~100mK thermal noise becomes significant for GHz qubits.
    """
    freqs_ghz = [3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    temps_mK = [20.0, 50.0, 100.0, 200.0, 500.0, 1000.0]  # mK

    results = []
    for T_mK in temps_mK:
        T_K = T_mK * 1e-3
        row = {"temperature_mK": T_mK}
        for f in freqs_ghz:
            nth = thermal_photon_number(f, T_K)
            row[f"nth_at_{f}GHz"] = float(f"{nth:.4e}")
        results.append(row)
    return results


def main():
    print("=" * 60)
    print("Cryogenic Electronics Interface Simulation")
    print("=" * 60)

    print("\n[1] Attenuation Chain: 300K → 20mK")
    chain = simulate_attenuation_chain()
    print(f"  {'Stage':<12} {'Temp(K)':<10} {'Atten(dB)':<12} {'Noise_T(K)':<14} {'n_th':<12} {'SNR(dB)':<10}")
    print("  " + "-" * 70)
    for s in chain["stage_details"]:
        print(f"  {s['stage']:<12} {s['temperature_K']:<10.3f} {s['cumulative_attenuation_dB']:<12.1f} "
              f"{s['noise_temperature_K']:<14.4f} {s['thermal_photons_nth']:<12.2e} {s['snr_dB']:<10.2f}")

    print("\n[2] Thermal Photon Occupancy vs Temperature (5 GHz qubit)")
    for T_mK in [20, 50, 100, 200, 500]:
        nth = thermal_photon_number(5.0, T_mK * 1e-3)
        flag = " <-- thermal noise dominates" if nth > 0.01 else ""
        print(f"  T={T_mK:4d} mK : n_th = {nth:.4e}{flag}")

    print("\n[3] Thermal Photon Sweep (all frequencies vs temperatures)")
    sweep = compute_thermal_photon_sweep()
    for row in sweep:
        t = row["temperature_mK"]
        nth_5ghz = row.get("nth_at_5.0GHz", row.get("nth_at_5GHz", "N/A"))
        print(f"  T={t:6.1f} mK, n_th(5GHz) = {nth_5ghz:.3e}")

    # Build output
    output = {
        "temperature_stages": chain["temperature_stages"],
        "attenuation_dB": chain["attenuation_dB"],
        "noise_temperature_K": chain["noise_temperature_K"],
        "thermal_photons": chain["thermal_photons"],
        "snr_dB": chain["snr_dB"],
        "thermal_photon_sweep": sweep,
        "chain_details": chain,
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "cryo_electronics_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
