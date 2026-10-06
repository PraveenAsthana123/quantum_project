"""
Q25 — Quantum Sensing
magnetometry.py

Quantum magnetometry using NV centers in diamond.
Models ODMR (Optically Detected Magnetic Resonance) spectrum,
Ramsey-based DC magnetometry, and sensitivity calculation.

Reference: Taylor et al., Nature Physics 4, 810 (2008);
           Rondin et al., Rep. Prog. Phys. 77, 056503 (2014).

Outputs: data/magnetometry_results.json
"""

import json
import math
import os
import random


# ---------------------------------------------------------------------------
# NV center physics
# ---------------------------------------------------------------------------

GAMMA_NV_HZ_PER_T = 28.024e9   # NV gyromagnetic ratio [Hz/T] ≈ 28 GHz/T
D_GS = 2.87e9                   # zero-field splitting [Hz]
ELECTRON_GYROMAGNET = GAMMA_NV_HZ_PER_T


def nv_resonance_frequency(B_T: float, m_s: int = +1) -> float:
    """
    NV spin-transition frequency including Zeeman shift.
    ν = D_GS + m_s * γ_NV * B
    m_s = ±1 for the two spin sublevels.
    """
    return D_GS + m_s * GAMMA_NV_HZ_PER_T * B_T


def odmr_spectrum(B_field_T: float, mw_freqs_Hz: list,
                   linewidth_Hz: float = 2e6,
                   contrast: float = 0.03,
                   background: float = 1.0) -> list:
    """
    ODMR fluorescence spectrum: dip at each spin-transition frequency.
    Lorentzian lineshape.

    Returns PL (photoluminescence) normalised to background.
    """
    f_plus  = nv_resonance_frequency(B_field_T, m_s=+1)
    f_minus = nv_resonance_frequency(B_field_T, m_s=-1)

    spectrum = []
    for f in mw_freqs_Hz:
        # Two Lorentzian dips (m_s = +1 and m_s = -1)
        half_lw = linewidth_Hz / 2.0
        dip_plus  = contrast * half_lw ** 2 / ((f - f_plus) ** 2 + half_lw ** 2)
        dip_minus = contrast * half_lw ** 2 / ((f - f_minus) ** 2 + half_lw ** 2)
        pl = background - dip_plus - dip_minus
        spectrum.append(max(0.0, pl))
    return spectrum


# ---------------------------------------------------------------------------
# Ramsey-based DC magnetometry
# ---------------------------------------------------------------------------

def ramsey_magnetometry_sensitivity(T2_us: float,
                                     interrogation_time_us: float,
                                     n_nv: int = 1) -> float:
    """
    Minimum detectable field (sensitivity) for DC magnetometry.
    η = δB * √τ  [T/√Hz]

    For a single NV Ramsey experiment:
    η = 1 / (γ_NV * T2) * 1/√N_NV   (optimal sensing time T ≈ T2)

    For finite interrogation time τ_int < T2:
    η = 1 / (γ_NV * τ_int * √(τ_int/T_cycle))

    Returns η in T/√Hz, then converts to nT/√Hz.
    """
    T2_s = T2_us * 1e-6
    t_int_s = interrogation_time_us * 1e-6

    # Sensitivity for a single NV in Ramsey config
    # η = Δν_linewidth / (slope * √(N_NV * photons_per_shot))
    # Simplified: η ≈ 1/(γ_NV * √(T2 * t_int))
    if T2_s <= 0 or t_int_s <= 0:
        return float("inf")

    eta_T_per_sqrtHz = 1.0 / (GAMMA_NV_HZ_PER_T * math.sqrt(T2_s * t_int_s * n_nv))
    return eta_T_per_sqrtHz * 1e9  # convert to nT/√Hz


def ac_magnetometry_sensitivity(T2_us: float, n_nv: int = 1) -> float:
    """
    AC (dynamic) field sensitivity at optimal sensing time T = T2/π.
    η_AC = 1 / (γ_NV * T2) / √N
    """
    T2_s = T2_us * 1e-6
    if T2_s <= 0:
        return float("inf")
    eta = 1.0 / (GAMMA_NV_HZ_PER_T * T2_s * math.sqrt(n_nv))
    return eta * 1e9  # nT/√Hz


# ---------------------------------------------------------------------------
# Full magnetometry simulation
# ---------------------------------------------------------------------------

def simulate_nv_magnetometry(
        b_field_range_mT: float = 5.0,
        n_b_points: int = 100,
        T2_us: float = 100.0,
        interrogation_time_us: float = 50.0,
        n_nv: int = 1,
        linewidth_Hz: float = 2e6,
        contrast: float = 0.03,
        noise_sigma: float = 0.001,
        seed: int = 42) -> dict:
    """
    Simulate NV magnetometry: ODMR spectrum + Ramsey sensitivity.
    """
    random.seed(seed)

    B_field_T = 1e-4  # 0.1 mT reference field

    # Frequency range around zero-field splitting (2.87 GHz ± 200 MHz)
    bw = 200e6  # Hz
    n_pts = 200
    freqs_Hz = [D_GS - bw + i * 2 * bw / (n_pts - 1) for i in range(n_pts)]

    # ODMR spectrum
    spectrum = odmr_spectrum(B_field_T, freqs_Hz,
                              linewidth_Hz=linewidth_Hz,
                              contrast=contrast)
    # Add noise
    spectrum_noisy = [
        max(0.0, s + random.gauss(0.0, noise_sigma)) for s in spectrum
    ]

    # Sensitivity
    eta_dc = ramsey_magnetometry_sensitivity(T2_us, interrogation_time_us, n_nv)
    eta_ac = ac_magnetometry_sensitivity(T2_us, n_nv)

    # B-field sweep: ODMR dip positions
    b_values_mT = [i * b_field_range_mT / (n_b_points - 1)
                   for i in range(n_b_points)]
    dip_positions = [
        nv_resonance_frequency(b * 1e-3, m_s=+1) / 1e9   # GHz
        for b in b_values_mT
    ]

    print(f"T2                    : {T2_us:.1f} µs")
    print(f"Interrogation time    : {interrogation_time_us:.1f} µs")
    print(f"DC sensitivity η      : {eta_dc:.3f} nT/√Hz")
    print(f"AC sensitivity η      : {eta_ac:.3f} nT/√Hz")
    print(f"NV resonance (0.1mT)  : {nv_resonance_frequency(B_field_T, +1)/1e9:.4f} GHz")

    result = {
        "b_field_range_mT": b_field_range_mT,
        "odmr_spectrum": {
            "freqs_GHz": [round(f / 1e9, 6) for f in freqs_Hz[:20]],  # sample
            "pl_sample": [round(p, 5) for p in spectrum_noisy[:20]],
        },
        "sensitivity_nT_per_sqrt_Hz": round(eta_dc, 4),
        "ac_sensitivity_nT_per_sqrt_Hz": round(eta_ac, 4),
        "t2_us": T2_us,
        "interrogation_time_us": interrogation_time_us,
        "n_nv_centers": n_nv,
        "linewidth_Hz": linewidth_Hz,
        "zero_field_splitting_GHz": D_GS / 1e9,
        "resonance_at_01mT_GHz": round(nv_resonance_frequency(B_field_T, +1) / 1e9, 6),
        "dip_positions_GHz_sample": [round(d, 6) for d in dip_positions[:10]],
    }
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== NV-Center Quantum Magnetometry ===\n")

    results = simulate_nv_magnetometry(
        b_field_range_mT=5.0,
        T2_us=100.0,
        interrogation_time_us=50.0,
        n_nv=1,
    )

    os.makedirs("data", exist_ok=True)
    out_path = "data/magnetometry_results.json"
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
