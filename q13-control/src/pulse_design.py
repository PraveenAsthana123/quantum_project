"""
DRAG Pulse Design for Single-Qubit X Gate
==========================================
Implements DRAG (Derivative Removal via Adiabatic Gate) pulse to suppress
leakage to the |2⟩ state in a transmon qubit.

Transmon Hamiltonian (in rotating frame, 3-level truncation):
    H(t) = Ω(t)/2 · σ_x(01) + η/2 · |2⟩⟨2| + (sqrt(2) Ω(t)/2) · σ_x(12)

where:
    Ω(t) = pulse envelope (Gaussian or DRAG)
    η    = anharmonicity (typically -150 to -300 MHz)

DRAG correction:
    Ω_DRAG(t) = Ω(t)  +  i · λ · dΩ/dt / η

The imaginary (Q) component suppresses leakage by canceling transitions to |2⟩.

Saves results to data/pulse_results.json.
"""

import json
import numpy as np
from pathlib import Path
from scipy.integrate import solve_ivp
from scipy.linalg import expm


# ---------------------------------------------------------------------------
# Transmon parameters
# ---------------------------------------------------------------------------

ANHARMONICITY_MHZ = -200.0     # η in MHz
PULSE_DURATION_NS = 40.0       # gate duration in nanoseconds
RABI_FREQ_MHZ = 25.0           # Ω₀/2π in MHz


# ---------------------------------------------------------------------------
# Pulse shapes
# ---------------------------------------------------------------------------

def gaussian_pulse(t: np.ndarray, t_gate: float, sigma: float,
                   amplitude: float) -> np.ndarray:
    """
    Gaussian pulse envelope:
        Ω(t) = A · exp(-(t - t_gate/2)² / (2σ²))
    Truncated at ±2σ and subtracted to enforce zero at boundaries.
    """
    t0 = t_gate / 2
    env = amplitude * np.exp(-((t - t0) ** 2) / (2 * sigma ** 2))
    # DRAG correction: subtract base value
    env_base = amplitude * np.exp(-(t0 ** 2) / (2 * sigma ** 2))
    env = env - env_base
    return env


def drag_pulse(t: np.ndarray, t_gate: float, sigma: float,
               amplitude: float, eta_MHz: float,
               drag_coeff: float = 1.0) -> tuple:
    """
    DRAG pulse: I (in-phase) + Q (quadrature) components.

    I(t) = Ω_gauss(t)
    Q(t) = -λ · (dΩ_gauss/dt) / η

    where λ = drag_coeff (typically ≈ 0.5).

    Returns (I_env, Q_env) in same units as amplitude.
    """
    t0 = t_gate / 2
    I = amplitude * np.exp(-((t - t0) ** 2) / (2 * sigma ** 2))
    I_base = amplitude * np.exp(-(t0 ** 2) / (2 * sigma ** 2))
    I = I - I_base

    # Derivative of Gaussian
    dI_dt = amplitude * (-(t - t0) / sigma ** 2) * np.exp(-((t - t0) ** 2) / (2 * sigma ** 2))

    # DRAG Q component: Q = -λ · dI/dt / η
    Q = -drag_coeff * dI_dt / eta_MHz

    return I, Q


# ---------------------------------------------------------------------------
# 3-level transmon Hamiltonian in rotating frame
# ---------------------------------------------------------------------------

def transmon_hamiltonian(omega_I: float, omega_Q: float,
                          eta_MHz: float) -> np.ndarray:
    """
    3-level Hamiltonian at a single time point.
    States: |0⟩, |1⟩, |2⟩

    H = (omega_I/2) · (|0⟩⟨1| + |1⟩⟨0| + √2|1⟩⟨2| + √2|2⟩⟨1|)
      + (omega_Q/2) · (-i|0⟩⟨1| + i|1⟩⟨0| - i√2|1⟩⟨2| + i√2|2⟩⟨1|)
      + eta/2 · |2⟩⟨2|

    In 2π·MHz units.
    """
    H = np.zeros((3, 3), dtype=complex)

    # I component (cos-drive)
    H[0, 1] += omega_I / 2
    H[1, 0] += omega_I / 2
    H[1, 2] += omega_I * np.sqrt(2) / 2
    H[2, 1] += omega_I * np.sqrt(2) / 2

    # Q component (sin-drive)
    H[0, 1] += -1j * omega_Q / 2
    H[1, 0] += 1j * omega_Q / 2
    H[1, 2] += -1j * omega_Q * np.sqrt(2) / 2
    H[2, 1] += 1j * omega_Q * np.sqrt(2) / 2

    # Anharmonicity term (energy offset of |2⟩)
    H[2, 2] += eta_MHz

    return H


def propagator_step(H: np.ndarray, dt: float) -> np.ndarray:
    """Compute U(dt) = exp(-i H dt) for a single time step."""
    return expm(-1j * H * dt)


def simulate_gate(I_env: np.ndarray, Q_env: np.ndarray,
                  times: np.ndarray, eta_MHz: float) -> np.ndarray:
    """
    Simulate the unitary propagator U(T) = Π_k exp(-i H(t_k) dt).
    Returns final 3×3 unitary matrix.
    """
    dt = times[1] - times[0] if len(times) > 1 else 1.0
    U = np.eye(3, dtype=complex)

    for k in range(len(times)):
        H = transmon_hamiltonian(float(I_env[k]), float(Q_env[k]), eta_MHz)
        U_step = propagator_step(H, dt)
        U = U_step @ U

    return U


# ---------------------------------------------------------------------------
# Gate metrics
# ---------------------------------------------------------------------------

def gate_fidelity_3level(U: np.ndarray, target_2level: np.ndarray) -> float:
    """
    Compute gate fidelity between the achieved 3-level unitary
    and the target 2-level gate (embedded in 3-level space).

    F = |Tr(U†_target · U_2level)|² / d²
    where U_2level is the 2×2 subspace block of U and d=2.
    """
    U_2 = U[0:2, 0:2]
    d = 2
    overlap = np.trace(target_2level.conj().T @ U_2)
    return float(abs(overlap) ** 2 / d ** 2)


def leakage_to_2(U: np.ndarray) -> float:
    """
    Compute leakage probability to |2⟩ state when starting from |0⟩ or |1⟩.
    L = (|U_{20}|² + |U_{21}|²) / 2
    """
    return float((abs(U[2, 0]) ** 2 + abs(U[2, 1]) ** 2) / 2)


# ---------------------------------------------------------------------------
# Target gate: X on qubits {0,1}
# ---------------------------------------------------------------------------

X_TARGET = np.array([[0, 1], [1, 0]], dtype=complex)

# Calibrate pulse area: integral(Ω dt) = π for an X gate (π-pulse)
def calibrate_amplitude(t_gate: float, sigma: float) -> float:
    """
    Find amplitude such that ∫Ω(t)dt = π (π-pulse condition).
    For Gaussian: integral ≈ A·σ·√(2π).
    """
    # Numerical integration
    n = 1000
    t = np.linspace(0, t_gate, n)
    dt = t_gate / n
    env = np.abs(gaussian_pulse(t, t_gate, sigma, amplitude=1.0))
    area = np.sum(env) * dt
    if area < 1e-10:
        return RABI_FREQ_MHZ
    return np.pi / area


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("DRAG Pulse Design — Transmon X Gate")
    print("=" * 60)

    t_gate = PULSE_DURATION_NS   # ns
    eta = ANHARMONICITY_MHZ      # MHz
    sigma = t_gate / 4           # Gaussian width
    drag_coeff = 0.5

    n_steps = 200
    times = np.linspace(0, t_gate, n_steps)
    dt = t_gate / n_steps

    # Calibrate amplitude for π-pulse
    amp = calibrate_amplitude(t_gate, sigma)
    print(f"\nPulse duration   : {t_gate} ns")
    print(f"Anharmonicity η  : {eta} MHz")
    print(f"Gaussian σ       : {sigma:.1f} ns")
    print(f"Calibrated amp   : {amp:.4f} MHz")
    print(f"DRAG coefficient : {drag_coeff}")

    # Gaussian pulse
    I_gauss = gaussian_pulse(times, t_gate, sigma, amp)
    Q_gauss = np.zeros_like(I_gauss)

    # DRAG pulse
    I_drag, Q_drag = drag_pulse(times, t_gate, sigma, amp, eta, drag_coeff)

    print("\nSimulating Gaussian pulse...")
    U_gauss = simulate_gate(I_gauss, Q_gauss, times, eta)
    fid_gauss = gate_fidelity_3level(U_gauss, X_TARGET)
    leak_gauss = leakage_to_2(U_gauss)
    print(f"  Gate fidelity : {fid_gauss:.6f}")
    print(f"  Leakage to |2⟩: {leak_gauss:.6f}")

    print("\nSimulating DRAG pulse...")
    U_drag = simulate_gate(I_drag, Q_drag, times, eta)
    fid_drag = gate_fidelity_3level(U_drag, X_TARGET)
    leak_drag = leakage_to_2(U_drag)
    print(f"  Gate fidelity : {fid_drag:.6f}")
    print(f"  Leakage to |2⟩: {leak_drag:.6f}")

    print(f"\nLeakage suppression: {leak_gauss/max(leak_drag, 1e-12):.1f}× improvement with DRAG")

    # Pulse profiles (first 10 points)
    pulse_profiles = {
        "gaussian": {
            "I": I_gauss[:20].tolist(),
            "Q": Q_gauss[:20].tolist(),
        },
        "drag": {
            "I": I_drag[:20].tolist(),
            "Q": Q_drag[:20].tolist(),
        },
    }

    results = [
        {
            "pulse_type": "Gaussian",
            "gate_fidelity": round(fid_gauss, 8),
            "leakage_rate": round(leak_gauss, 8),
            "pulse_duration_ns": t_gate,
            "anharmonicity_MHz": eta,
        },
        {
            "pulse_type": "DRAG",
            "gate_fidelity": round(fid_drag, 8),
            "leakage_rate": round(leak_drag, 8),
            "pulse_duration_ns": t_gate,
            "anharmonicity_MHz": eta,
            "drag_coefficient": drag_coeff,
        },
    ]

    out_results = {
        "pulse_type": "DRAG",
        "target_gate": "X",
        "gaussian_fidelity": round(fid_gauss, 8),
        "drag_fidelity": round(fid_drag, 8),
        "gaussian_leakage": round(leak_gauss, 8),
        "drag_leakage": round(leak_drag, 8),
        "gate_fidelity": round(fid_drag, 8),
        "leakage_rate": round(leak_drag, 8),
        "pulse_duration_ns": t_gate,
        "anharmonicity_MHz": eta,
        "drag_coefficient": drag_coeff,
        "leakage_suppression_ratio": round(leak_gauss / max(leak_drag, 1e-12), 2),
        "detailed": results,
        "pulse_profiles_sample": pulse_profiles,
    }

    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "pulse_results.json"
    with open(out_path, "w") as f:
        json.dump(out_results, f, indent=2)

    print(f"\nResults saved to {out_path}")
    print("\nDRAG pulse simulation complete.")


if __name__ == "__main__":
    main()
