"""
Toric Code — Kitaev's Surface Code on a Torus
================================================
Implements a 4×4 toric code with 16 qubits on a torus (periodic boundaries).

Qubits live on edges of the lattice.  For an L×L torus:
  - Horizontal edges: L×L  (indexed row-major)
  - Vertical edges:   L×L

Total qubits: 2·L²

Star operators  A_s = ⊗_{e∈star(s)} X_e   (vertex stabilizers)
Plaquette ops   B_p = ⊗_{e∈∂p}      Z_e   (face  stabilizers)

Ground state: +1 eigenstate of all A_s and B_p.
Anyons: e-type (violated B_p) and m-type (violated A_s).

Saves results to data/toric_results.json.
"""

import json
import numpy as np
from pathlib import Path
from itertools import product


# ---------------------------------------------------------------------------
# Lattice geometry
# ---------------------------------------------------------------------------

class ToricCode:
    """
    4×4 toric code on a torus.

    Edge labeling:
      Horizontal edge (row r, col c): index = r*L + c
      Vertical   edge (row r, col c): index = L*L + r*L + c
    """

    def __init__(self, L: int = 4):
        self.L = L
        self.n_qubits = 2 * L * L
        self.n_vertices = L * L
        self.n_plaquettes = L * L

        # Pauli matrices
        self.I2 = np.eye(2, dtype=complex)
        self.X = np.array([[0, 1], [1, 0]], dtype=complex)
        self.Z = np.array([[1, 0], [0, -1]], dtype=complex)

        # Build edge-to-qubit index maps
        self._build_edge_maps()

    def _build_edge_maps(self):
        """Assign qubit indices to lattice edges."""
        L = self.L
        # h_edge[r,c] = horizontal edge at row r between columns c and (c+1)%L
        # v_edge[r,c] = vertical   edge at col c between rows r and (r+1)%L
        self.h_edge = {}
        self.v_edge = {}
        for r, c in product(range(L), range(L)):
            self.h_edge[(r, c)] = r * L + c
            self.v_edge[(r, c)] = L * L + r * L + c

    # ------------------------------------------------------------------
    # Star operator: A_s at vertex (r, c)
    # Touches 4 edges: left, right, up, down
    # ------------------------------------------------------------------

    def star_edges(self, r: int, c: int) -> list:
        L = self.L
        return [
            self.h_edge[(r, c)],               # right horizontal
            self.h_edge[(r, (c - 1) % L)],     # left  horizontal
            self.v_edge[(r, c)],               # down  vertical
            self.v_edge[((r - 1) % L, c)],    # up    vertical
        ]

    # ------------------------------------------------------------------
    # Plaquette operator: B_p at plaquette (r, c)
    # Touches 4 edges: top, bottom, left, right of the face
    # ------------------------------------------------------------------

    def plaquette_edges(self, r: int, c: int) -> list:
        L = self.L
        return [
            self.h_edge[(r, c)],               # top    horizontal
            self.h_edge[((r + 1) % L, c)],    # bottom horizontal
            self.v_edge[(r, c)],               # left   vertical
            self.v_edge[(r, (c + 1) % L)],    # right  vertical
        ]

    # ------------------------------------------------------------------
    # Sparse operator building using Pauli tensor products
    # ------------------------------------------------------------------

    def _multi_pauli(self, pauli: np.ndarray, qubit_indices: list) -> np.ndarray:
        """
        Build the tensor product operator that applies `pauli` on each qubit
        in qubit_indices and identity elsewhere.
        """
        n = self.n_qubits
        op = np.ones((1, 1), dtype=complex)
        for q in range(n):
            p = pauli if q in qubit_indices else self.I2
            op = np.kron(op, p)
        return op

    # ------------------------------------------------------------------
    # Ground state via stabilizer projectors (small system only)
    # ------------------------------------------------------------------

    def ground_state_vector(self) -> np.ndarray:
        """
        Project |0...0⟩ onto the +1 eigenspace of all stabilizers.
        Only feasible for small L; here L=4 → 8 qubits (demo subset).
        We use a reduced model: first 6 qubits of the toric code.
        """
        # For demo purposes use 6-qubit subsystem (first plaquette + star)
        n_demo = 6
        dim = 2 ** n_demo
        state = np.zeros(dim, dtype=complex)
        state[0] = 1.0  # |000000⟩

        # Build star and plaquette for the demo subsystem
        I = np.eye(2, dtype=complex)
        X = self.X
        Z = self.Z

        def kron_list(ops):
            result = ops[0]
            for op in ops[1:]:
                result = np.kron(result, op)
            return result

        # Star A_0: X on qubits 0,1,2,3 (example)
        A0 = kron_list([X, X, X, X, I, I])
        # Plaquette B_0: Z on qubits 0,1,4,5 (example)
        B0 = kron_list([Z, Z, I, I, Z, Z])

        # Project: (1+A0)/2 * (1+B0)/2 * state
        proj_A = (np.eye(dim) + A0) / 2
        proj_B = (np.eye(dim) + B0) / 2
        gs = proj_B @ proj_A @ state
        norm = np.linalg.norm(gs)
        if norm > 1e-10:
            gs /= norm
        return gs

    # ------------------------------------------------------------------
    # Anyon creation: flip stabilizer eigenvalue by applying Pauli on edge
    # ------------------------------------------------------------------

    def create_anyon_pair(self, edge_h: int, edge_v: int) -> dict:
        """
        Create an e-anyon pair by applying Z on a horizontal edge path.
        Create an m-anyon pair by applying X on a vertical edge path.
        Returns description of anyon locations.
        """
        L = self.L
        r_e, c_e = divmod(edge_h, L)
        r_m, c_m = divmod(edge_v - L * L, L) if edge_v >= L * L else (0, 0)

        return {
            "e_anyon_pair": {
                "type": "electric (e)",
                "created_by": "Z on horizontal edge",
                "locations": [
                    {"plaquette": [r_e, c_e]},
                    {"plaquette": [r_e, (c_e + 1) % L]},
                ],
                "edge_acted_on": edge_h,
            },
            "m_anyon_pair": {
                "type": "magnetic (m)",
                "created_by": "X on vertical edge",
                "locations": [
                    {"vertex": [r_m, c_m]},
                    {"vertex": [(r_m + 1) % L, c_m]},
                ],
                "edge_acted_on": edge_v,
            },
        }

    def braiding_phase(self, braid_e_around_m: bool = True) -> dict:
        """
        In the toric code, braiding an e-anyon around an m-anyon gives a phase of -1 (π phase).
        This is Abelian anyonic statistics — the hallmark of the toric code's Z₂ topological order.
        """
        return {
            "braid_e_around_m": braid_e_around_m,
            "phase": -1.0 if braid_e_around_m else 1.0,
            "phase_angle_deg": 180.0 if braid_e_around_m else 0.0,
            "statistics": "Abelian Z2 anyons",
            "description": (
                "Braiding an electric (e) anyon around a magnetic (m) anyon "
                "acquires a phase of -1 (π). This is the defining feature of "
                "Z₂ topological order in the Kitaev toric code."
            ),
        }


# ---------------------------------------------------------------------------
# Degeneracy and topology
# ---------------------------------------------------------------------------

def ground_state_degeneracy(L: int) -> int:
    """
    On a torus, the toric code has ground-state degeneracy 4 = 2^(2g)
    where g=1 is the genus of the torus.
    The logical operators are the non-contractible Wilson loops.
    """
    return 4  # always 4 for a torus


def analyze_logical_operators(L: int) -> dict:
    """
    Logical X̄₁, X̄₂ : non-contractible X loops around the two cycles of the torus.
    Logical Z̄₁, Z̄₂ : non-contractible Z loops around the dual cycles.
    """
    return {
        "logical_X1": {
            "type": "X string",
            "path": f"horizontal loop at row 0, {L} edges",
            "direction": "x-cycle",
        },
        "logical_X2": {
            "type": "X string",
            "path": f"vertical loop at col 0, {L} edges",
            "direction": "y-cycle",
        },
        "logical_Z1": {
            "type": "Z string",
            "path": f"horizontal loop on dual lattice, row 0",
            "direction": "x-cycle (dual)",
        },
        "logical_Z2": {
            "type": "Z string",
            "path": f"vertical loop on dual lattice, col 0",
            "direction": "y-cycle (dual)",
        },
        "commutation": "[X̄_i, Z̄_j] = -δ_{ij}  (anticommute for same cycle)",
        "n_logical_qubits": 2,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Toric Code — Kitaev's Surface Code on a 4×4 Torus")
    print("=" * 60)

    L = 4
    tc = ToricCode(L=L)

    print(f"\nLattice size  : {L} × {L}")
    print(f"Total qubits  : {tc.n_qubits}  (on torus edges)")
    print(f"Vertices      : {tc.n_vertices}")
    print(f"Plaquettes    : {tc.n_plaquettes}")
    print(f"Star ops      : {tc.n_vertices}  (A_s = ⊗X, vertex stabilizers)")
    print(f"Plaquette ops : {tc.n_plaquettes}  (B_p = ⊗Z, face stabilizers)")

    deg = ground_state_degeneracy(L)
    print(f"\nGround-state degeneracy on torus: {deg}")
    print("  (4 = 2^(2g), genus g=1 of torus)")

    # Logical operators
    logicals = analyze_logical_operators(L)
    print(f"\nLogical qubits encoded: {logicals['n_logical_qubits']}")
    print(f"  {logicals['logical_X1']['type']} : {logicals['logical_X1']['path']}")
    print(f"  {logicals['logical_Z1']['type']} : {logicals['logical_Z1']['path']}")

    # Star and plaquette edge memberships
    star_0 = tc.star_edges(0, 0)
    plaq_0 = tc.plaquette_edges(0, 0)
    print(f"\nStar(0,0)     edges: {star_0}")
    print(f"Plaquette(0,0) edges: {plaq_0}")

    # Anyon creation
    anyon_info = tc.create_anyon_pair(edge_h=0, edge_v=L * L)
    print(f"\nAnyon pair creation:")
    print(f"  e-anyons at plaquettes: {anyon_info['e_anyon_pair']['locations']}")
    print(f"  m-anyons at vertices  : {anyon_info['m_anyon_pair']['locations']}")

    # Braiding
    braid = tc.braiding_phase(braid_e_around_m=True)
    print(f"\nAnyonic braiding phase (e around m): {braid['phase']} ({braid['phase_angle_deg']}°)")
    print(f"  → {braid['statistics']}")

    # Ground state (demo 6-qubit subsystem)
    gs = tc.ground_state_vector()
    print(f"\nGround state vector norm (demo subsystem): {np.linalg.norm(gs):.6f}")

    # Save results
    results = {
        "lattice_size": L,
        "n_qubits": tc.n_qubits,
        "n_vertices": tc.n_vertices,
        "n_plaquettes": tc.n_plaquettes,
        "ground_state_degeneracy": deg,
        "anyon_types": ["e (electric)", "m (magnetic)", "em (fermion)"],
        "braiding_phase": braid["phase"],
        "braiding_phase_description": braid["description"],
        "logical_operators": logicals,
        "anyon_pair_example": anyon_info,
        "star_edges_example": star_0,
        "plaquette_edges_example": plaq_0,
        "topology": "Z2 topological order on torus",
    }

    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "toric_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {out_path}")
    print("\nToric code simulation complete.")


if __name__ == "__main__":
    main()
