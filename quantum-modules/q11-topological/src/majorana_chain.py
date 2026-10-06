"""
Majorana Chain — Kitaev Chain Model
====================================
Implements the Kitaev chain Hamiltonian for a 1D p-wave superconductor:

    H = -μ Σ c†_j c_j  -  t Σ (c†_j c_{j+1} + h.c.)  +  Δ Σ (c_j c_{j+1} + h.c.)

Uses scipy sparse matrices for a 10-site chain.
Computes energy gap vs μ/t, identifying the topological phase transition at |μ| = 2t.
Saves results to data/majorana_results.json.
"""

import json
import os
import numpy as np
from pathlib import Path

try:
    from scipy import sparse
    from scipy.sparse.linalg import eigsh
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("[WARNING] scipy not available — falling back to numpy dense matrices")


# ---------------------------------------------------------------------------
# Hamiltonian construction
# ---------------------------------------------------------------------------

def build_kitaev_hamiltonian(n_sites: int, mu: float, t: float = 1.0, delta: float = 1.0):
    """
    Build the Kitaev chain BdG Hamiltonian in the Nambu basis (c, c†) of size 2n×2n.

    In the particle-hole (Bogoliubov–de Gennes) representation the Hamiltonian becomes:

        H_BdG = [  H_0    Δ  ]
                [ -Δ*  -H_0* ]

    where H_0 is the tight-binding part and Δ is the p-wave pairing.
    """
    dim = 2 * n_sites

    if SCIPY_AVAILABLE:
        H = sparse.lil_matrix((dim, dim), dtype=complex)
    else:
        H = np.zeros((dim, dim), dtype=complex)

    for j in range(n_sites):
        # On-site: -μ (c†c - 1/2) → chemical potential term in particle sector
        H[j, j] += -mu / 2.0
        H[j + n_sites, j + n_sites] += mu / 2.0

    for j in range(n_sites - 1):
        # Hopping: -t (c†_{j+1} c_j + h.c.)
        H[j, j + 1] += -t
        H[j + 1, j] += -t
        # Hole sector (opposite sign)
        H[j + n_sites, j + 1 + n_sites] += t
        H[j + 1 + n_sites, j + n_sites] += t

        # Pairing: Δ (c_j c_{j+1} + h.c.) — off-diagonal in Nambu space
        H[j, j + 1 + n_sites] += delta
        H[j + 1, j + n_sites] += -delta
        # Hermitian conjugate
        H[j + 1 + n_sites, j] += np.conj(delta)
        H[j + n_sites, j + 1] += -np.conj(delta)

    if SCIPY_AVAILABLE:
        return H.tocsr()
    return H


def compute_spectrum(n_sites: int, mu: float, t: float = 1.0, delta: float = 1.0) -> np.ndarray:
    """Return sorted eigenvalues of the BdG Hamiltonian."""
    H = build_kitaev_hamiltonian(n_sites, mu, t, delta)

    if SCIPY_AVAILABLE:
        H_dense = H.toarray()
    else:
        H_dense = H

    eigvals = np.linalg.eigvalsh(H_dense)
    return np.sort(eigvals)


def energy_gap(eigvals: np.ndarray) -> float:
    """
    Extract the quasiparticle gap: smallest positive eigenvalue.
    BdG spectrum is particle-hole symmetric, so eigenvalues come in ±E pairs.
    """
    positive = eigvals[eigvals > 1e-10]
    if len(positive) == 0:
        return 0.0
    return float(np.min(positive))


def zero_mode_energy(eigvals: np.ndarray, threshold: float = 1e-2) -> float:
    """Return the smallest |eigenvalue| — near-zero in topological phase."""
    return float(np.min(np.abs(eigvals)))


# ---------------------------------------------------------------------------
# Phase diagram scan
# ---------------------------------------------------------------------------

def scan_phase_diagram(
    n_sites: int = 10,
    t: float = 1.0,
    delta: float = 1.0,
    mu_min: float = -4.0,
    mu_max: float = 4.0,
    n_points: int = 81,
) -> dict:
    """
    Scan μ/t from mu_min to mu_max and record:
      - energy gap at each point
      - zero-mode energy
      - topological phase indicator (gap closes near |μ| = 2t)
    """
    mu_values = np.linspace(mu_min * t, mu_max * t, n_points)
    gaps = []
    zero_modes = []
    phases = []

    for mu in mu_values:
        eigvals = compute_spectrum(n_sites, mu, t, delta)
        gap = energy_gap(eigvals)
        zme = zero_mode_energy(eigvals)
        gaps.append(gap)
        zero_modes.append(zme)

        # Topological phase: |μ| < 2t  →  non-trivial (Majorana edge modes)
        is_topological = bool(abs(mu) < 2.0 * t - 0.05)
        phases.append("topological" if is_topological else "trivial")

    # Phase boundary: |μ| = 2t
    phase_boundary = 2.0 * t

    return {
        "chain_length": n_sites,
        "t": t,
        "delta": delta,
        "mu_values": mu_values.tolist(),
        "energy_gaps": gaps,
        "zero_mode_energies": zero_modes,
        "phases": phases,
        "topological_phase_boundary": phase_boundary,
        "topological_phase_boundary_description": "|mu| = 2t",
        "zero_mode_energy": float(np.min(zero_modes)),
        "gap_at_transition": float(gaps[n_points // 2]),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Kitaev Chain — Majorana Fermion Model")
    print("=" * 60)

    n_sites = 10
    t = 1.0
    delta = 1.0

    print(f"\nChain length : {n_sites} sites")
    print(f"Hopping      : t = {t}")
    print(f"Pairing      : Δ = {delta}")
    print(f"Phase boundary: |μ| = {2*t} (topological for |μ| < {2*t})")

    # Example spectrum at two representative points
    mu_topo = 0.0   # deep in topological phase
    mu_triv = 3.0   # trivial phase

    eigvals_topo = compute_spectrum(n_sites, mu_topo, t, delta)
    eigvals_triv = compute_spectrum(n_sites, mu_triv, t, delta)

    print(f"\nTopological phase (μ={mu_topo}):")
    print(f"  Energy gap     : {energy_gap(eigvals_topo):.6f}")
    print(f"  Zero-mode E    : {zero_mode_energy(eigvals_topo):.6f}")
    print(f"  Lowest 4 eigvals: {eigvals_topo[:4]}")

    print(f"\nTrivial phase (μ={mu_triv}):")
    print(f"  Energy gap     : {energy_gap(eigvals_triv):.6f}")
    print(f"  Zero-mode E    : {zero_mode_energy(eigvals_triv):.6f}")
    print(f"  Lowest 4 eigvals: {eigvals_triv[:4]}")

    # Full scan
    print("\nScanning phase diagram...")
    results = scan_phase_diagram(n_sites=n_sites, t=t, delta=delta)

    # Count phases
    n_topo = results["phases"].count("topological")
    n_triv = results["phases"].count("trivial")
    print(f"  Points in topological phase : {n_topo}")
    print(f"  Points in trivial phase     : {n_triv}")
    print(f"  Minimum gap (at transition) : {min(results['energy_gaps']):.6f}")

    # Save results
    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "majorana_results.json"

    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {out_path}")
    print("\nKitaev chain simulation complete.")


if __name__ == "__main__":
    main()
