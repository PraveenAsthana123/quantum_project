"""
Transverse-Field Ising Model (TFIM) Simulation
H = -J·Σ σᵢᶻσᵢ₊₁ᶻ - h·Σ σᵢˣ
8-site chain, quantum phase transition at h/J = 1.
"""
import numpy as np
import json
import os
from typing import Dict, List, Tuple


# Pauli matrices
I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)


def kron_op_on_site(op: np.ndarray, site: int, n_sites: int) -> np.ndarray:
    """
    Embed a single-site operator on `site` in the n_sites Hilbert space.
    Returns (2^n_sites) × (2^n_sites) matrix.
    """
    ops = [I2] * n_sites
    ops[site] = op
    result = ops[0]
    for o in ops[1:]:
        result = np.kron(result, o)
    return result


def build_tfim_hamiltonian(n_sites: int, J: float, h: float) -> np.ndarray:
    """
    Build TFIM Hamiltonian: H = -J·Σᵢ σᵢᶻσᵢ₊₁ᶻ - h·Σᵢ σᵢˣ
    Periodic boundary conditions.
    """
    dim = 2 ** n_sites
    H = np.zeros((dim, dim), dtype=complex)

    # ZZ interaction terms
    for i in range(n_sites):
        j = (i + 1) % n_sites  # periodic BC
        Zi = kron_op_on_site(Z, i, n_sites)
        Zj = kron_op_on_site(Z, j, n_sites)
        H -= J * (Zi @ Zj)

    # Transverse field terms
    for i in range(n_sites):
        Xi = kron_op_on_site(X, i, n_sites)
        H -= h * Xi

    return H


def ground_state(H: np.ndarray) -> Tuple[float, np.ndarray]:
    """Return ground state energy and wavefunction."""
    eigenvalues, eigenvectors = np.linalg.eigh(H)
    return float(eigenvalues[0]), eigenvectors[:, 0]


def order_parameter(psi: np.ndarray, n_sites: int) -> float:
    """
    Ferromagnetic order parameter: m = (1/N) Σ ⟨σᵢᶻ⟩
    In ferromagnetic phase (h < J): m → nonzero.
    In paramagnetic phase (h > J): m → 0.
    """
    total_sz = 0.0
    for i in range(n_sites):
        Zi = kron_op_on_site(Z, i, n_sites)
        sz_i = float(np.real(psi.conj() @ Zi @ psi))
        total_sz += abs(sz_i)
    return round(total_sz / n_sites, 6)


def correlation_function(psi: np.ndarray, n_sites: int) -> Dict:
    """
    Compute connected correlation function: ⟨σᵢᶻσⱼᶻ⟩ for all pairs.
    Correlation length estimated from exponential decay.
    """
    corr_matrix = np.zeros((n_sites, n_sites))
    sz_exp = []

    # ⟨σᵢᶻ⟩
    for i in range(n_sites):
        Zi = kron_op_on_site(Z, i, n_sites)
        sz_exp.append(float(np.real(psi.conj() @ Zi @ psi)))

    # ⟨σᵢᶻσⱼᶻ⟩
    for i in range(n_sites):
        for j in range(i, n_sites):
            Zi = kron_op_on_site(Z, i, n_sites)
            Zj = kron_op_on_site(Z, j, n_sites)
            corr_matrix[i, j] = float(np.real(psi.conj() @ (Zi @ Zj) @ psi))
            corr_matrix[j, i] = corr_matrix[i, j]

    # Correlation from site 0: C(r) = ⟨σ₀ᶻσᵣᶻ⟩ - ⟨σ₀ᶻ⟩⟨σᵣᶻ⟩
    c0r = [corr_matrix[0, r] - sz_exp[0] * sz_exp[r] for r in range(n_sites)]

    # Estimate correlation length (fit to exp decay for r >= 1)
    corr_length = None
    abs_c = [abs(c) for c in c0r[1:]]
    if len(abs_c) > 2 and max(abs_c) > 1e-10:
        # log-linear fit
        try:
            rs = np.arange(1, n_sites)
            log_c = np.log(np.array(abs_c) + 1e-12)
            slope, _ = np.polyfit(rs, log_c, 1)
            if slope < 0:
                corr_length = round(-1.0 / slope, 4)
        except Exception:
            pass

    return {
        "sz_expectation": [round(s, 6) for s in sz_exp],
        "correlation_matrix_row0": [round(c, 6) for c in c0r],
        "correlation_length_sites": corr_length,
    }


def phase_transition_analysis(
    n_sites: int = 8,
    J: float = 1.0,
    h_j_ratios: List[float] = None,
) -> List[Dict]:
    """
    Sweep h/J ratios to find quantum phase transition.
    Transition at h/J = 1: order parameter vanishes, correlation length diverges.
    """
    if h_j_ratios is None:
        h_j_ratios = [0.1, 0.3, 0.5, 0.7, 1.0, 1.3, 1.5, 2.0, 3.0]

    results = []
    for ratio in h_j_ratios:
        h = ratio * J
        H = build_tfim_hamiltonian(n_sites, J, h)
        gs_energy, gs_vec = ground_state(H)
        m = order_parameter(gs_vec, n_sites)
        corr = correlation_function(gs_vec, n_sites)

        results.append({
            "h_j_ratio": ratio,
            "h": h,
            "J": J,
            "ground_state_energy": round(gs_energy, 8),
            "ground_state_energy_per_site": round(gs_energy / n_sites, 8),
            "order_parameter_m": m,
            "correlation_length_sites": corr["correlation_length_sites"],
            "sz_expectation_site0": corr["sz_expectation"][0] if corr["sz_expectation"] else 0.0,
        })

    return results


def main():
    print("=" * 60)
    print("Transverse-Field Ising Model (TFIM) — 8-site chain")
    print("=" * 60)

    n_sites = 8
    J = 1.0

    # Use fewer ratios for speed in demo; full set saved to JSON
    demo_ratios = [0.1, 0.5, 1.0, 1.5, 2.0, 3.0]
    full_ratios = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0, 1.1, 1.3, 1.5, 2.0, 3.0]

    print(f"\nN={n_sites} sites, J={J}")
    print(f"\n[1] Phase Transition Sweep h/J = {demo_ratios}")
    results = phase_transition_analysis(n_sites, J, demo_ratios)

    print(f"\n  {'h/J':<8} {'E/site':<14} {'Order m':<12} {'ξ (sites)':<12} {'Phase'}")
    print("  " + "-" * 60)
    for r in results:
        phase = "Ferromagnetic" if r["h_j_ratio"] < 1.0 else ("Critical" if r["h_j_ratio"] == 1.0 else "Paramagnetic")
        xi_str = f"{r['correlation_length_sites']:.2f}" if r["correlation_length_sites"] else "N/A"
        print(f"  {r['h_j_ratio']:<8.2f} {r['ground_state_energy_per_site']:<14.6f} "
              f"{r['order_parameter_m']:<12.6f} {xi_str:<12} {phase}")

    # Critical point
    print(f"\n[2] Phase Transition")
    print(f"  Exact critical point: h/J = 1.0 (1D TFIM, Onsager)")
    for r in results:
        if abs(r["h_j_ratio"] - 1.0) < 0.01:
            print(f"  At h/J=1.0: m = {r['order_parameter_m']:.6f} (should → 0 for large N)")

    # Full sweep for output
    full_results = phase_transition_analysis(n_sites, J, full_ratios)

    output = {
        "n_sites": n_sites,
        "h_j_ratios": [r["h_j_ratio"] for r in full_results],
        "order_parameters": [r["order_parameter_m"] for r in full_results],
        "correlation_lengths": [r["correlation_length_sites"] for r in full_results],
        "phase_transition_point": 1.0,
        "model": "H = -J Σ σᵢᶻσᵢ₊₁ᶻ - h Σ σᵢˣ, periodic BC",
        "full_results": full_results,
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "ising_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
