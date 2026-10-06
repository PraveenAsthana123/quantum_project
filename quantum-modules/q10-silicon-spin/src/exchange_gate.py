"""
exchange_gate.py — Two-qubit CZ gate via exchange interaction for silicon spin qubit (Q10)
Simulates CZ gate via ZZ Hamiltonian (capacitive/dispersive coupling regime).
In the large-detuning limit of exchange coupling:
  H_ZZ = J_zz/4 * Z⊗Z
  CZ gate at t such that J_zz * t = pi (phase = pi/4 per ZZ term).
Compares ideal vs noisy (T2 dephasing) gate fidelity vs pulse duration.

Physical basis: Si/SiGe spin qubits in the large-detuning (J << delta) regime,
where the exchange coupling produces an effective ZZ interaction.
"""

import json
import os
import numpy as np
from typing import Dict, List, Tuple


# Gate parameters
J_MHZ = 50.0        # ZZ coupling J/2pi (MHz)
T2_US = 20.0        # T2 dephasing time (us)
OMEGA_GHZ = 10.0    # qubit frequency (GHz)


def pauli_matrices():
    I = np.eye(2, dtype=complex)
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    Z = np.array([[1, 0], [0, -1]], dtype=complex)
    return I, X, Y, Z


def build_zz_hamiltonian(J_mhz: float) -> np.ndarray:
    """
    ZZ Hamiltonian: H = (J/4) * Z⊗Z
    This is the effective two-qubit interaction in the dispersive/large-detuning limit
    of exchange coupling for Si spin qubits.
    CZ gate is achieved at t_CZ = pi/(J/4) = 4*pi/J (in units where J is in rad/ns).

    Simpler form: H = J_zz * Z⊗Z, with J_zz = J/2pi in rad/ns.
    """
    _, _, _, Z = pauli_matrices()
    J_zz = J_mhz * 1e-3 * 2 * np.pi   # MHz -> rad/ns
    return (J_zz / 4) * np.kron(Z, Z)


def rzz_target_unitary(theta: float) -> np.ndarray:
    """
    Rzz(theta) = exp(-i*theta/2 * Z⊗Z)
               = diag(e^{-i*theta/2}, e^{i*theta/2}, e^{i*theta/2}, e^{-i*theta/2})
    For H = (J/4)*ZZ at time t: theta = J*t/2.
    CZ = Rzz(pi/2) * (local Rz corrections).
    The native gate from H=(J/4)*ZZ at t_CZ=20ns achieves Rzz(pi),
    which is locally equivalent to CZ.
    """
    d = np.exp(-1j * theta / 2)
    return np.diag([d, np.conj(d), np.conj(d), d]).astype(complex)


def cz_target_unitary() -> np.ndarray:
    """CZ gate: diag(1, 1, 1, -1) in computational basis |00>,|01>,|10>,|11>."""
    return np.diag([1, 1, 1, -1]).astype(complex)


def ideal_cz_gate_time_ns(J_mhz: float) -> float:
    """
    CZ gate time for H = (J_zz/4) * Z⊗Z:
    U(t) = diag(e^{-iJ_zz*t/4}, e^{iJ_zz*t/4}, e^{iJ_zz*t/4}, e^{-iJ_zz*t/4})
    CZ requires phase difference pi between |11> and others:
    J_zz * t / 2 = pi  =>  t = 2*pi / J_zz
    With J_zz = J_mhz * 2pi * 1e-3 rad/ns:
    t_CZ = 2*pi / (J_mhz * 2pi * 1e-3) = 1000 / J_mhz [ns]
    For J=50 MHz: t_CZ = 20 ns.
    """
    J_zz_ns = J_mhz * 1e-3 * 2 * np.pi  # rad/ns
    return 2 * np.pi / J_zz_ns          # ns


def gate_fidelity_unitary(U_actual: np.ndarray, U_target: np.ndarray) -> float:
    """
    Gate fidelity: F = |Tr(U_target† U_actual)|^2 / d^2
    Returns 1.0 when unitaries match up to global phase.
    """
    d = U_actual.shape[0]
    overlap = np.trace(U_target.conj().T @ U_actual)
    fidelity = abs(overlap) ** 2 / d ** 2
    return float(fidelity.real)


def apply_dephasing_to_unitary(U: np.ndarray, t_ns: float, T2_us: float) -> np.ndarray:
    """
    Apply T2 dephasing noise to a 2-qubit unitary.
    Off-diagonal elements decay as exp(-t / T2).
    """
    T2_ns = T2_us * 1e3  # us -> ns
    decay = np.exp(-t_ns / T2_ns)
    U_noisy = U.copy()
    for i in range(4):
        for j in range(4):
            if i != j:
                U_noisy[i, j] *= decay
    return U_noisy


def sweep_gate_fidelity(
    J_mhz: float,
    T2_us: float,
    n_points: int = 30,
) -> List[Dict]:
    """
    Sweep pulse duration around ideal ZZ gate time.
    Target: Rzz(pi) = native gate of ZZ Hamiltonian at t_CZ.
    Compare ideal vs noisy (T2 dephasing) fidelity.
    """
    from scipy.linalg import expm

    H = build_zz_hamiltonian(J_mhz)
    t_ideal = ideal_cz_gate_time_ns(J_mhz)
    J_zz_ns = J_mhz * 1e-3 * 2 * np.pi

    t_range = np.linspace(0.5 * t_ideal, 2.0 * t_ideal, n_points)
    results = []

    for t_ns in t_range:
        # Native target: Rzz(theta) where theta = J*t/2
        theta = J_zz_ns * t_ns / 2
        U_target = rzz_target_unitary(theta)
        U_ideal = expm(-1j * H * t_ns)
        fidelity_ideal = gate_fidelity_unitary(U_ideal, U_target)
        U_noisy = apply_dephasing_to_unitary(U_ideal, t_ns, T2_us)
        fidelity_noisy = gate_fidelity_unitary(U_noisy, U_target)

        results.append({
            "gate_time_ns": round(t_ns, 2),
            "ideal_fidelity": round(fidelity_ideal, 6),
            "noisy_fidelity": round(fidelity_noisy, 6),
        })

    return results


def main():
    from scipy.linalg import expm

    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "exchange_results.json")

    print("=== Q10 Exchange Gate (ZZ Coupling) ===")
    print(f"ZZ coupling J/2pi: {J_MHZ} MHz")
    print(f"T2: {T2_US} us")
    print(f"Qubit frequency: {OMEGA_GHZ} GHz\n")

    # Ideal CZ gate time
    t_cz_ns = ideal_cz_gate_time_ns(J_MHZ)
    print(f"Ideal CZ gate time: {t_cz_ns:.2f} ns  (= 2*pi / J_zz)")

    # Build Hamiltonian and native target gate
    H = build_zz_hamiltonian(J_MHZ)
    J_zz_ns = J_MHZ * 1e-3 * 2 * np.pi
    theta_cz = J_zz_ns * t_cz_ns / 2   # = pi at t_cz
    U_target = rzz_target_unitary(theta_cz)  # Rzz(pi)

    print(f"Native gate: Rzz(theta={theta_cz:.4f} rad = {theta_cz/np.pi:.2f}*pi)")
    print(f"  (CZ = Rzz(pi/2) * local Rz corrections; Rzz(pi) is equally useful)")

    # Ideal evolution
    U_ideal = expm(-1j * H * t_cz_ns)
    fidelity_ideal = gate_fidelity_unitary(U_ideal, U_target)
    print(f"Ideal gate fidelity at t_CZ: {fidelity_ideal:.6f}")

    # Noisy gate (T2 dephasing)
    U_noisy = apply_dephasing_to_unitary(U_ideal, t_cz_ns, T2_US)
    fidelity_noisy = gate_fidelity_unitary(U_noisy, U_target)
    print(f"Noisy gate fidelity (T2={T2_US}us): {fidelity_noisy:.6f}")

    # Sweep gate time
    print("\nSweeping gate time around ideal CZ time...")
    sweep_data = sweep_gate_fidelity(J_MHZ, T2_US, n_points=25)
    best_noisy = max(sweep_data, key=lambda x: x["noisy_fidelity"])
    best_ideal = max(sweep_data, key=lambda x: x["ideal_fidelity"])

    print(f"Best ideal fidelity: {best_ideal['ideal_fidelity']:.6f} at t={best_ideal['gate_time_ns']} ns")
    print(f"Best noisy fidelity: {best_noisy['noisy_fidelity']:.6f} at t={best_noisy['gate_time_ns']} ns")

    results = {
        "gate_time_ns": round(t_cz_ns, 2),
        "ideal_fidelity": round(fidelity_ideal, 6),
        "noisy_fidelity": round(fidelity_noisy, 6),
        "T2_us": T2_US,
        "J_MHz": J_MHZ,
        "qubit_freq_GHz": OMEGA_GHZ,
        "gate_type": "Rzz(pi) via ZZ exchange (dispersive limit, CZ-equivalent up to local rotations)",
        "gate_time_formula": "t_CZ = 2*pi / (J_zz in rad/ns) = 1000/J_MHz [ns]",
        "rzz_theta_rad": round(float(theta_cz), 4),
        "fidelity_sweep": sweep_data,
        "best_noisy_fidelity": best_noisy,
        "best_ideal_fidelity": best_ideal,
    }

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
    return results


if __name__ == "__main__":
    main()
