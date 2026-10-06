"""
Neutral Atom QAOA with Rydberg Blockade
=========================================
Models a 1D array of 6 neutral atoms with Rydberg blockade interaction.

Rydberg blockade potential: V(r) = C₆ / r⁶
When V >> detuning/Rabi frequency, at most one atom can be in |r⟩ per blockade radius.

Implements QAOA-like pulses (parameterized by β, γ) to solve Max-Cut on
the interaction graph defined by the blockade constraint.

Saves results to data/neutral_atom_results.json.
"""

import json
import numpy as np
from pathlib import Path
from itertools import combinations
from scipy.optimize import minimize


# ---------------------------------------------------------------------------
# Physical constants and Rydberg parameters
# ---------------------------------------------------------------------------

C6_DEFAULT = 862690.0  # C₆ coefficient for Rb |70S⟩ state, in units of (MHz·μm⁶)
HBAR = 1.0  # natural units


# ---------------------------------------------------------------------------
# Atom array geometry and interaction graph
# ---------------------------------------------------------------------------

def atom_positions_1d(n_atoms: int, spacing_um: float = 5.0) -> np.ndarray:
    """1D chain of n_atoms separated by spacing_um micrometers."""
    return np.array([[i * spacing_um, 0.0] for i in range(n_atoms)], dtype=float)


def rydberg_interaction(pos: np.ndarray, C6: float = C6_DEFAULT) -> np.ndarray:
    """
    Compute pairwise Rydberg interactions V_{ij} = C6 / |r_i - r_j|^6.
    Returns n×n matrix of interaction strengths (MHz).
    """
    n = len(pos)
    V = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            r = np.linalg.norm(pos[i] - pos[j])
            v = C6 / r ** 6
            V[i, j] = v
            V[j, i] = v
    return V


def blockade_graph(V: np.ndarray, blockade_radius_um: float,
                   spacing_um: float, C6: float) -> list:
    """
    Build interaction graph edges: connect atoms within blockade radius.
    Blockade radius R_b: V(R_b) = Ω (set to 1 MHz threshold).
    """
    n = V.shape[0]
    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            dist = abs(i - j) * spacing_um
            if dist <= blockade_radius_um:
                edges.append((i, j, float(V[i, j])))
    return edges


def max_cut_value(bitstring: int, n: int, edges: list) -> float:
    """Compute Max-Cut value for a given bitstring (integer representation)."""
    bits = [(bitstring >> k) & 1 for k in range(n)]
    cut = sum(1 for i, j, _ in edges if bits[i] != bits[j])
    return float(cut)


def classical_max_cut(n: int, edges: list) -> dict:
    """Brute-force Max-Cut for small graphs."""
    best_cut = 0
    best_str = 0
    all_cuts = []
    for b in range(2 ** n):
        c = max_cut_value(b, n, edges)
        all_cuts.append(c)
        if c > best_cut:
            best_cut = c
            best_str = b
    return {
        "optimal_value": best_cut,
        "optimal_bitstring": bin(best_str)[2:].zfill(n),
        "optimal_int": best_str,
    }


# ---------------------------------------------------------------------------
# Quantum simulation of QAOA on atom array
# Using exact statevector simulation in the computational basis.
# ---------------------------------------------------------------------------

def cost_hamiltonian(n: int, edges: list) -> np.ndarray:
    """
    Max-Cut cost Hamiltonian:
    H_C = Σ_{(i,j)∈E} (1 - Z_i Z_j) / 2

    Diagonal in computational basis.
    """
    dim = 2 ** n
    H_C = np.zeros(dim)
    for k in range(dim):
        bits = [(k >> m) & 1 for m in range(n)]
        z = [1 - 2 * b for b in bits]  # Z eigenvalues: 0→+1, 1→-1
        val = sum((1 - z[i] * z[j]) / 2 for i, j, _ in edges)
        H_C[k] = val
    return H_C


def mixer_hamiltonian_apply(state: np.ndarray, n: int, beta: float) -> np.ndarray:
    """
    Apply exp(-i·β·H_B) where H_B = -Σ X_i.
    For each qubit: exp(i·β·X) rotation.
    """
    dim = 2 ** n
    result = state.copy()
    for q in range(n):
        new_state = np.zeros(dim, dtype=complex)
        cos_b = np.cos(beta)
        sin_b = np.sin(beta)
        for k in range(dim):
            bit = (k >> q) & 1
            k_flip = k ^ (1 << q)
            # exp(-i·β·X) = cos(β)·I - i·sin(β)·X
            new_state[k] += cos_b * result[k]
            new_state[k] -= 1j * sin_b * result[k_flip]
        result = new_state
    return result


def cost_unitary_apply(state: np.ndarray, H_C: np.ndarray, gamma: float) -> np.ndarray:
    """Apply exp(-i·γ·H_C) — diagonal in computational basis."""
    return state * np.exp(-1j * gamma * H_C)


def qaoa_circuit(n: int, edges: list, params: np.ndarray, p: int = 1) -> np.ndarray:
    """
    Run depth-p QAOA circuit.
    params = [γ_1, β_1, ..., γ_p, β_p]

    Initial state: |+⟩^n = H^⊗n |0⟩
    """
    dim = 2 ** n
    state = np.ones(dim, dtype=complex) / np.sqrt(dim)

    H_C = cost_hamiltonian(n, edges)

    for layer in range(p):
        gamma = params[2 * layer]
        beta = params[2 * layer + 1]
        state = cost_unitary_apply(state, H_C, gamma)
        state = mixer_hamiltonian_apply(state, n, beta)

    return state


def expected_cut(state: np.ndarray, n: int, edges: list) -> float:
    """Compute ⟨H_C⟩ = Σ_k |ψ_k|² · C(k)."""
    H_C = cost_hamiltonian(n, edges)
    probs = np.abs(state) ** 2
    return float(np.dot(probs, H_C))


def optimize_qaoa(n: int, edges: list, p: int = 2, seed: int = 42) -> dict:
    """Optimize QAOA parameters using scipy minimize."""
    rng = np.random.default_rng(seed)
    best_energy = -1e9
    best_params = None

    # Multiple random restarts
    for _ in range(5):
        x0 = rng.uniform(0, 2 * np.pi, size=2 * p)

        def objective(params):
            state = qaoa_circuit(n, edges, params, p)
            return -expected_cut(state, n, edges)

        res = minimize(objective, x0, method="COBYLA",
                       options={"maxiter": 500, "rhobeg": 0.5})
        if -res.fun > best_energy:
            best_energy = -res.fun
            best_params = res.x.tolist()

    # Final state with best params
    final_state = qaoa_circuit(n, edges, best_params, p)
    probs = np.abs(final_state) ** 2
    best_bitstring = int(np.argmax(probs))

    return {
        "optimal_params": best_params,
        "qaoa_energy": round(best_energy, 6),
        "best_bitstring": bin(best_bitstring)[2:].zfill(n),
        "best_bitstring_probability": round(float(probs[best_bitstring]), 6),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Neutral Atom QAOA with Rydberg Blockade")
    print("=" * 60)

    n_atoms = 6
    spacing_um = 5.0           # 5 μm spacing
    blockade_radius_um = 7.0   # blockade radius
    C6 = C6_DEFAULT

    print(f"\nAtoms          : {n_atoms}")
    print(f"Spacing        : {spacing_um} μm")
    print(f"Blockade radius: {blockade_radius_um} μm")
    print(f"C₆ coefficient : {C6:.0f} MHz·μm⁶")

    pos = atom_positions_1d(n_atoms, spacing_um)
    V = rydberg_interaction(pos, C6)
    edges = blockade_graph(V, blockade_radius_um, spacing_um, C6)

    print(f"\nInteraction graph edges (within blockade radius):")
    for i, j, v in edges:
        print(f"  ({i},{j}): V = {v:.2f} MHz")

    # Classical optimal
    print("\nClassical Max-Cut (brute force):")
    classical = classical_max_cut(n_atoms, edges)
    print(f"  Optimal cut value : {classical['optimal_value']}")
    print(f"  Optimal bitstring : {classical['optimal_bitstring']}")

    # QAOA optimization
    print("\nRunning QAOA optimization (p=2)...")
    qaoa_result = optimize_qaoa(n_atoms, edges, p=2)
    print(f"  QAOA energy       : {qaoa_result['qaoa_energy']:.4f}")
    print(f"  QAOA best string  : {qaoa_result['best_bitstring']}")
    print(f"  QAOA string prob  : {qaoa_result['best_bitstring_probability']:.4f}")

    approx_ratio = qaoa_result["qaoa_energy"] / max(classical["optimal_value"], 1e-10)
    print(f"  Approximation ratio: {approx_ratio:.4f}")

    results = {
        "n_atoms": n_atoms,
        "spacing_um": spacing_um,
        "blockade_radius_um": blockade_radius_um,
        "C6_coefficient": C6,
        "interaction_graph_edges": [(i, j, round(v, 4)) for i, j, v in edges],
        "qaoa_energy": qaoa_result["qaoa_energy"],
        "qaoa_best_bitstring": qaoa_result["best_bitstring"],
        "qaoa_params": qaoa_result["optimal_params"],
        "classical_optimal": classical["optimal_value"],
        "classical_bitstring": classical["optimal_bitstring"],
        "approximation_ratio": round(approx_ratio, 4),
        "n_edges_in_graph": len(edges),
        "physics_note": (
            "Rydberg blockade prevents two adjacent atoms from being simultaneously "
            "excited, implementing a hard-core constraint that maps directly to "
            "Maximum Independent Set / Max-Cut problems."
        ),
    }

    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "neutral_atom_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {out_path}")
    print("\nNeutral atom QAOA simulation complete.")


if __name__ == "__main__":
    main()
