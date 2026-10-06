"""
rabi_oscillation.py — Rabi oscillation simulation for silicon spin qubit (Q10)
Drives a spin qubit with microwave pulse and shows |0>/<->|1> population oscillations.
Fits Rabi frequency from oscillation data.
Parameters match Si/SiGe experimental values.
"""

import json
import os
import numpy as np
from typing import Dict, List, Tuple


# Physical parameters
QUBIT_FREQ_GHZ = 10.0       # electron spin resonance frequency (GHz)
DRIVE_FREQ_GHZ = 10.0       # microwave drive frequency (resonant)
RABI_FREQ_MHZ = 10.0        # Rabi oscillation frequency (MHz) -> period ~100 ns
T2_US = 20.0                # T2* coherence time (us)

# Time axis: 0 to 200 ns (covers ~2 Rabi cycles at 10 MHz)
T_MAX_NS = 200.0
DT_NS = 0.1   # 0.1 ns step for numerical stability


def pauli_matrices():
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    Z = np.array([[1, 0], [0, -1]], dtype=complex)
    I = np.eye(2, dtype=complex)
    return I, X, Y, Z


def simulate_rabi(
    qubit_freq_ghz: float,
    drive_freq_ghz: float,
    rabi_freq_mhz: float,
    T2_us: float,
    t_max_ns: float,
    dt_ns: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Simulate Rabi oscillations using the rotating wave approximation (RWA).
    In the rotating frame at drive frequency:

    H_rot = (delta/2) * sigma_z + (Omega_R/2) * sigma_x

    where delta = omega_qubit - omega_drive (detuning)
          Omega_R = Rabi frequency (rad/ns)

    Lindblad dephasing with rate Gamma_2 = 1/T2.

    Returns: (t_array, P1_array) — time and |1> population.
    """
    I, X, Y, Z = pauli_matrices()

    # Convert units to rad/ns
    omega_q = qubit_freq_ghz * 2 * np.pi       # rad/ns
    omega_d = drive_freq_ghz * 2 * np.pi        # rad/ns
    delta = omega_q - omega_d                    # detuning (rad/ns)
    Omega_R = rabi_freq_mhz * 1e-3 * 2 * np.pi # MHz -> GHz -> rad/ns

    # Lindblad dephasing
    Gamma_2 = 1.0 / (T2_us * 1e3)  # 1/(us * 1000 ns/us) = 1/ns
    L_phi = np.sqrt(Gamma_2) * Z / 2

    # Rotating frame Hamiltonian
    H_rot = (delta / 2) * Z + (Omega_R / 2) * X

    # Initial state: |0> = [1, 0]
    psi0 = np.array([1.0, 0.0], dtype=complex)
    rho = np.outer(psi0, psi0.conj())

    t_array = np.arange(0, t_max_ns + dt_ns, dt_ns)
    P1_array = np.zeros(len(t_array))

    # Use scipy solve_ivp for accuracy instead of Euler
    from scipy.integrate import solve_ivp

    def drho_dt(t_scalar, rho_flat):
        rho_2d = rho_flat[:4].reshape(2, 2) + 1j * rho_flat[4:].reshape(2, 2)
        commutator = -1j * (H_rot @ rho_2d - rho_2d @ H_rot)
        deph = L_phi @ rho_2d @ L_phi.conj().T - 0.5 * (
            L_phi.conj().T @ L_phi @ rho_2d + rho_2d @ L_phi.conj().T @ L_phi
        )
        d = commutator + deph
        return np.concatenate([d.real.flatten(), d.imag.flatten()])

    rho0_flat = np.concatenate([rho.real.flatten(), rho.imag.flatten()])
    sol = solve_ivp(
        drho_dt, [0, t_max_ns],
        rho0_flat,
        t_eval=t_array,
        method="RK45",
        rtol=1e-8, atol=1e-10,
    )

    P1_array = np.zeros(len(t_array))
    coherence = np.zeros(len(t_array))
    for i in range(len(t_array)):
        rho_re = sol.y[:4, i].reshape(2, 2)
        rho_im = sol.y[4:, i].reshape(2, 2)
        rho_t = rho_re + 1j * rho_im
        P1_array[i] = max(0.0, min(1.0, rho_t[1, 1].real))
        coherence[i] = abs(rho_t[0, 1])

    return t_array, P1_array


def fit_rabi_frequency(t_ns: np.ndarray, P1: np.ndarray) -> Dict:
    """
    Fit Rabi frequency from oscillation data.
    Model: P1(t) = A * sin^2(pi * f_R * t) * exp(-t/T2_eff) + B
         = A/2 * [1 - cos(2*pi*f_R*t) * exp(-t/T2_eff)] + B
    """
    from scipy.optimize import curve_fit
    from scipy.signal import find_peaks

    def rabi_model(t, A, f_R, phi, T2_eff, B):
        return A * np.sin(np.pi * f_R * t + phi) ** 2 * np.exp(-t / T2_eff) + B

    # Initial guess from first peak (pi pulse time)
    peaks, props = find_peaks(P1, height=0.5)
    if len(peaks) >= 1:
        pi_pulse_guess_ns = t_ns[peaks[0]]
        f_R_guess = 1.0 / (2 * pi_pulse_guess_ns)   # GHz (t in ns, f in GHz)
    else:
        f_R_guess = RABI_FREQ_MHZ * 1e-3  # 10 MHz -> 0.01 GHz

    try:
        popt, pcov = curve_fit(
            rabi_model, t_ns, P1,
            p0=[0.99, f_R_guess, 0.0, T2_US * 1e3, 0.001],
            bounds=([0.5, f_R_guess*0.1, -np.pi, 100.0, 0], [1.0, f_R_guess*10, np.pi, 1e7, 0.1]),
            maxfev=10000,
        )
        A, f_R_fit, phi, T2_eff, B = popt
        f_R_mhz = f_R_fit * 1e3  # GHz -> MHz
        # Pi pulse time: half Rabi period
        pi_pulse_ns = 1.0 / (2 * f_R_fit)  # ns

        return {
            "rabi_freq_MHz": round(f_R_mhz, 3),
            "pi_pulse_time_ns": round(pi_pulse_ns, 2),
            "amplitude": round(A, 4),
            "phase_rad": round(phi, 4),
            "T2_eff_ns": round(T2_eff, 1),
            "fitted": True,
        }
    except Exception as e:
        # Fallback: estimate from theory
        return {
            "rabi_freq_MHz": RABI_FREQ_MHZ,
            "pi_pulse_time_ns": round(1000.0 / (2 * RABI_FREQ_MHZ), 2),
            "fitted": False,
            "fit_error": str(e),
        }


def main():
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "rabi_results.json")

    print("=== Q10 Rabi Oscillation Simulation ===")
    print(f"Qubit frequency: {QUBIT_FREQ_GHZ} GHz")
    print(f"Drive frequency: {DRIVE_FREQ_GHZ} GHz (resonant)")
    print(f"Rabi frequency: {RABI_FREQ_MHZ} MHz")
    print(f"T2: {T2_US} us\n")

    # Simulate Rabi oscillations
    t_ns, P1 = simulate_rabi(
        qubit_freq_ghz=QUBIT_FREQ_GHZ,
        drive_freq_ghz=DRIVE_FREQ_GHZ,
        rabi_freq_mhz=RABI_FREQ_MHZ,
        T2_us=T2_US,
        t_max_ns=T_MAX_NS,
        dt_ns=DT_NS,
    )

    print(f"Simulated {len(t_ns)} time points (0 to {T_MAX_NS} ns)")
    print(f"P1 max: {P1.max():.4f}, P1 min: {P1.min():.4f}")

    # Fit Rabi frequency
    fit = fit_rabi_frequency(t_ns, P1)
    print(f"Fitted Rabi frequency: {fit.get('rabi_freq_MHz', '?')} MHz")
    print(f"Pi pulse time: {fit.get('pi_pulse_time_ns', '?')} ns")

    # Build oscillation data (sample every 2 ns to keep JSON manageable)
    step = max(1, len(t_ns) // 100)
    oscillation_data = [
        {"time_ns": round(float(t_ns[i]), 1), "P1": round(float(P1[i]), 4)}
        for i in range(0, len(t_ns), step)
    ]

    results = {
        "drive_freq_GHz": DRIVE_FREQ_GHZ,
        "qubit_freq_GHz": QUBIT_FREQ_GHZ,
        "rabi_freq_MHz": fit.get("rabi_freq_MHz", RABI_FREQ_MHZ),
        "pi_pulse_time_ns": fit.get("pi_pulse_time_ns", 50.0),
        "T2_us": T2_US,
        "simulation_duration_ns": T_MAX_NS,
        "dt_ns": DT_NS,
        "fit_details": fit,
        "P1_max": round(float(P1.max()), 4),
        "P1_min": round(float(P1.min()), 4),
        "oscillation_data": oscillation_data,
    }

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path} ({len(oscillation_data)} data points)")
    return results


if __name__ == "__main__":
    main()
