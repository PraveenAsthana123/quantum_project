"""
Q25 — Quantum Sensing
gravitational_sensing.py

Quantum gravimetry via atom interferometry (Mach-Zehnder).
Pulse sequence: π/2 → π → π/2 with Bragg pulses.
Calculates gravity sensitivity Δg/g.
Compares classical vs quantum-enhanced sensitivity.

Reference: Peters et al., Metrologia 38, 25 (2001);
           Kasevich & Chu, PRL 67, 181 (1991).

Outputs: data/gravimetry_results.json
"""

import json
import math
import os


# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

G_SI = 9.80665              # standard gravity [m/s²]
HBAR = 1.0546e-34           # J·s
M_RB87 = 1.443e-25          # kg (Rb-87)
K_EFFECTIVE = 2 * 2 * math.pi / 780e-9  # effective wave vector [m⁻¹] (2-photon Bragg)


# ---------------------------------------------------------------------------
# Mach-Zehnder atom interferometer
# ---------------------------------------------------------------------------

def mz_phase_shift(g: float, k_eff: float, T_s: float) -> float:
    """
    Phase shift of Mach-Zehnder atom interferometer due to gravity.
    Δφ = k_eff * g * T²
    where T is the pulse separation time.

    Reference: Kasevich & Chu (1991).
    """
    return k_eff * g * T_s ** 2


def transition_probability(phase: float) -> float:
    """P(|1>) = (1 + cos(Δφ)) / 2."""
    return (1.0 + math.cos(phase)) / 2.0


def gravity_from_phase(phase: float, k_eff: float, T_s: float) -> float:
    """Invert the phase relation to recover g."""
    if abs(k_eff * T_s ** 2) < 1e-30:
        return 0.0
    return phase / (k_eff * T_s ** 2)


# ---------------------------------------------------------------------------
# Sensitivity and noise
# ---------------------------------------------------------------------------

def shot_noise_limit(n_atoms: int, k_eff: float, T_s: float) -> float:
    """
    Δg_shot = 1 / (k_eff * T² * √N)    [m/s²]
    """
    return 1.0 / (k_eff * T_s ** 2 * math.sqrt(n_atoms))


def standard_quantum_limit(n_atoms: int, k_eff: float, T_s: float) -> float:
    """Alias for shot_noise_limit (coherent state probe)."""
    return shot_noise_limit(n_atoms, k_eff, T_s)


def heisenberg_limit(n_atoms: int, k_eff: float, T_s: float) -> float:
    """
    Δg_HL = 1 / (k_eff * T² * N)  — N-fold improvement over SNL.
    Requires highly entangled (N-particle) GHZ state.
    """
    return 1.0 / (k_eff * T_s ** 2 * n_atoms)


def vibration_noise(T_s: float, vibration_amplitude_m: float = 1e-8) -> float:
    """
    Phase noise from platform vibration: δφ_vib ≈ k_eff * a_vib * T²
    Convert to g-noise: δg_vib = δφ_vib / (k_eff * T²) = a_vib
    """
    return vibration_amplitude_m  # m/s² (vibration acceleration noise)


def classical_gravimeter_sensitivity_ug() -> float:
    """
    Typical classical (spring-mass) gravimeter sensitivity: ~1 µGal ≈ 10 nm/s²
    = 1e-8 m/s² ≈ 10^-9 g.
    Returns sensitivity in µg (micro-g = 9.8e-6 m/s²).
    """
    return 1.0  # µGal ≈ 1 nm/s²; in µg ≈ 0.1 µg


# ---------------------------------------------------------------------------
# Full gravimetry simulation
# ---------------------------------------------------------------------------

def simulate_gravimeter(
        free_fall_time_ms: float = 100.0,
        n_atoms: int = 1_000_000,
        g: float = G_SI,
        k_eff: float = K_EFFECTIVE,
        vibration_amp_m: float = 1e-8,
        n_measurements: int = 100) -> dict:
    """
    Simulate a Mach-Zehnder atom gravimeter.
    T = free_fall_time / 2 (pulse separation).
    """
    T_s = free_fall_time_ms * 1e-3 / 2.0  # pulse separation

    # Ideal phase shift
    delta_phi = mz_phase_shift(g, k_eff, T_s)

    # Sensitivity
    snl_ms2 = standard_quantum_limit(n_atoms, k_eff, T_s)
    hl_ms2 = heisenberg_limit(n_atoms, k_eff, T_s)
    vib_ms2 = vibration_noise(T_s, vibration_amp_m)

    # Convert to µg: 1 µg = G_SI * 1e-6 m/s²
    snl_ug = snl_ms2 / G_SI * 1e6
    hl_ug = hl_ms2 / G_SI * 1e6
    classical_ug = classical_gravimeter_sensitivity_ug()

    # Quantum enhancement factor
    sql_enhancement = classical_ug / snl_ug if snl_ug > 0 else 1.0

    # Simulate measurement sequence
    import random as rng_mod
    rng_mod.seed(42)
    g_measurements = []
    for _ in range(n_measurements):
        noise_phi = rng_mod.gauss(0.0, 1.0 / (k_eff * T_s ** 2 *
                                               math.sqrt(n_atoms)))
        g_meas = g + noise_phi
        g_measurements.append(g_meas)

    g_mean = sum(g_measurements) / len(g_measurements)
    g_std = math.sqrt(sum((x - g_mean) ** 2 for x in g_measurements)
                      / len(g_measurements))

    print(f"Free-fall time    : {free_fall_time_ms:.1f} ms")
    print(f"Pulse separation T: {T_s * 1000:.1f} ms")
    print(f"Phase shift       : {delta_phi:.4f} rad")
    print(f"N_atoms           : {n_atoms:.2e}")
    print(f"g (measured)      : {g_mean:.8f} m/s²")
    print(f"SNL sensitivity   : {snl_ug:.4f} µg")
    print(f"HL sensitivity    : {hl_ug:.6f} µg")
    print(f"Classical         : {classical_ug:.1f} µg")
    print(f"Quantum enhancement: {sql_enhancement:.1f}x over classical")

    return {
        "free_fall_time_ms": free_fall_time_ms,
        "pulse_separation_T_ms": round(T_s * 1000, 2),
        "gravity_ms2": round(g_mean, 8),
        "sensitivity_ug": round(snl_ug, 6),
        "shot_noise_limit_ug": round(snl_ug, 6),
        "heisenberg_limit_ug": round(hl_ug, 8),
        "sql_enhancement": round(sql_enhancement, 2),
        "classical_sensitivity_ug": classical_ug,
        "n_atoms": n_atoms,
        "phase_shift_rad": round(delta_phi, 6),
        "vibration_noise_ug": round(vib_ms2 / G_SI * 1e6, 6),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Quantum Gravimetry (Atom Interferometry) ===\n")

    results = simulate_gravimeter(
        free_fall_time_ms=100.0,
        n_atoms=1_000_000,
        g=G_SI,
    )

    os.makedirs("data", exist_ok=True)
    out_path = "data/gravimetry_results.json"
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
