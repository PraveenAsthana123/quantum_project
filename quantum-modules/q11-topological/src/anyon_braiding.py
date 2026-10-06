"""
Non-Abelian Anyon Braiding — Fibonacci Anyons
===============================================
Simulates Fibonacci anyon braiding in a simplified model.

Fibonacci anyons have two topological charges: {1, τ} with fusion rules:
    τ × τ = 1 + τ
    τ × 1 = τ
    1 × 1 = 1

The F-matrix (associativity moves) and R-matrix (braiding) are used to
construct the unitary gates implemented by braiding.

For 4 anyons in the total vacuum sector, the braid group B_3 is
represented by 2×2 matrices (one qubit of topological quantum information).

Key matrices (golden ratio φ = (1+√5)/2):
    F^{ττ}_{ττ}[τ] = [[φ^{-1}    φ^{-1/2}],
                       [φ^{-1/2} -φ^{-1} ]]

    R^τ_1 = exp(4πi/5)
    R^τ_τ = exp(-3πi/5)

Saves results to data/braiding_results.json.
"""

import json
import numpy as np
from pathlib import Path


# ---------------------------------------------------------------------------
# Fibonacci anyon algebra
# ---------------------------------------------------------------------------

PHI = (1 + np.sqrt(5)) / 2   # golden ratio ≈ 1.618

# F-matrix: F^{ττ}_{ττ}  (2×2, acts on fusion-channel Hilbert space)
def F_matrix() -> np.ndarray:
    """
    F^{ττ}_{ττ} relates the two associativity bases:
       (τ(ττ)) ↔ ((ττ)τ)
    Entries determined by consistency of Fibonacci anyon fusion algebra.
    """
    f11 = PHI ** (-1)
    f12 = PHI ** (-0.5)
    f21 = PHI ** (-0.5)
    f22 = -PHI ** (-1)
    return np.array([[f11, f12],
                     [f21, f22]], dtype=complex)


def R_matrix_diagonal() -> np.ndarray:
    """
    R-matrix for τ×τ fusion:
      R^τ_1 = exp(4πi/5)   (fusion to vacuum)
      R^τ_τ = exp(-3πi/5)  (fusion to τ)
    Returns diagonal [R^τ_1, R^τ_τ] as a 2×2 diagonal matrix.
    """
    R1 = np.exp(4j * np.pi / 5)
    Rtau = np.exp(-3j * np.pi / 5)
    return np.diag([R1, Rtau])


# ---------------------------------------------------------------------------
# Braid group generators for 4 anyons (qubit encoding)
# ---------------------------------------------------------------------------

def sigma1() -> np.ndarray:
    """
    Braid generator σ₁: exchanges anyons 1 and 2.
    σ₁ = F⁻¹ · R · F
    """
    F = F_matrix()
    R = R_matrix_diagonal()
    return F @ R @ np.linalg.inv(F)


def sigma2() -> np.ndarray:
    """
    Braid generator σ₂: exchanges anyons 2 and 3.
    σ₂ = R  (in the standard fusion basis)
    """
    return R_matrix_diagonal()


def braid_sequence_to_gate(braid: list) -> np.ndarray:
    """
    Convert a braid word (list of +/-1, +/-2) to a unitary 2×2 matrix.
    +k means σ_k,  -k means σ_k^{-1}.
    """
    s1 = sigma1()
    s2 = sigma2()
    s1_inv = np.linalg.inv(s1)
    s2_inv = np.linalg.inv(s2)

    gate = np.eye(2, dtype=complex)
    for b in braid:
        if b == 1:
            gate = s1 @ gate
        elif b == -1:
            gate = s1_inv @ gate
        elif b == 2:
            gate = s2 @ gate
        elif b == -2:
            gate = s2_inv @ gate
        else:
            raise ValueError(f"Unknown braid letter: {b}")
    return gate


# ---------------------------------------------------------------------------
# Gate fidelity
# ---------------------------------------------------------------------------

def gate_fidelity(U: np.ndarray, V: np.ndarray) -> float:
    """
    Average gate fidelity: F = |Tr(U†V)|² / d²
    where d is the dimension.
    """
    d = U.shape[0]
    return float(abs(np.trace(U.conj().T @ V)) ** 2 / d ** 2)


def nearest_clifford(U: np.ndarray) -> tuple:
    """
    Find the nearest single-qubit Clifford gate (from a small set) to U.
    Returns (name, matrix, fidelity).
    """
    cliffords = {
        "I":      np.eye(2, dtype=complex),
        "X":      np.array([[0, 1], [1, 0]], dtype=complex),
        "Y":      np.array([[0, -1j], [1j, 0]], dtype=complex),
        "Z":      np.array([[1, 0], [0, -1]], dtype=complex),
        "H":      np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2),
        "S":      np.array([[1, 0], [0, 1j]], dtype=complex),
        "T":      np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex),
        "Sdg":    np.array([[1, 0], [0, -1j]], dtype=complex),
    }
    best_name, best_fid = "I", -1.0
    for name, V in cliffords.items():
        fid = gate_fidelity(U, V)
        if fid > best_fid:
            best_fid = fid
            best_name = name
    return best_name, best_fid


# ---------------------------------------------------------------------------
# Standard braiding demonstrations
# ---------------------------------------------------------------------------

def demonstrate_braiding() -> list:
    """
    Demonstrate several standard braid sequences and the gates they implement.
    """
    demos = [
        {
            "name": "σ₁",
            "braid_sequence": [1],
            "description": "Single exchange of anyons 1,2",
        },
        {
            "name": "σ₂",
            "braid_sequence": [2],
            "description": "Single exchange of anyons 2,3",
        },
        {
            "name": "σ₁²",
            "braid_sequence": [1, 1],
            "description": "Double exchange (Dehn twist in channel 1)",
        },
        {
            "name": "σ₁σ₂",
            "braid_sequence": [1, 2],
            "description": "Two successive exchanges",
        },
        {
            "name": "σ₁σ₂σ₁",
            "braid_sequence": [1, 2, 1],
            "description": "Braid relation: σ₁σ₂σ₁ = σ₂σ₁σ₂",
        },
        {
            "name": "Approx NOT via σ₁³σ₂⁻¹",
            "braid_sequence": [1, 1, 1, -2],
            "description": "Approximate NOT gate from Fibonacci braiding",
        },
    ]

    results = []
    for d in demos:
        gate = braid_sequence_to_gate(d["braid_sequence"])
        nearest, fid = nearest_clifford(gate)
        is_unitary = bool(np.allclose(gate @ gate.conj().T, np.eye(2), atol=1e-10))
        results.append({
            "name": d["name"],
            "braid_sequence": d["braid_sequence"],
            "description": d["description"],
            "gate_real": gate.real.tolist(),
            "gate_imag": gate.imag.tolist(),
            "nearest_clifford": nearest,
            "fidelity_to_nearest_clifford": round(fid, 6),
            "is_unitary": is_unitary,
        })
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Non-Abelian Anyon Braiding — Fibonacci Anyons")
    print("=" * 60)

    phi = PHI
    print(f"\nGolden ratio φ = {phi:.6f}")
    print("Fusion rule: τ × τ = 1 + τ")
    print(f"Topological spin: h_τ = 3/5  (R^τ_τ = exp(-3πi/5))")

    F = F_matrix()
    R = R_matrix_diagonal()

    print(f"\nF-matrix F^{{ττ}}_{{ττ}}:")
    print(f"  [[{F[0,0].real:.6f}, {F[0,1].real:.6f}],")
    print(f"   [{F[1,0].real:.6f}, {F[1,1].real:.6f}]]")

    # Verify F² = I (involutory up to gauge) — F^4 = I for Fibonacci
    print(f"\nVerification |det(F)| = 1: {abs(np.linalg.det(F)):.6f}")
    print(f"F is unitary: {np.allclose(F @ F.conj().T, np.eye(2), atol=1e-10)}")

    # Pentagon and hexagon equations (consistency checks)
    # Pentagon: F_{12}^{34} * F_{13}^{24} = Σ_k F_{23}^{14}[k] * F_{12}^{k4} * F_{k3}^{24}
    # For Fibonacci: F*F*R*F*R = R*F*R  (hexagon)
    hexagon_lhs = F @ R @ F
    hexagon_rhs = R @ F @ R
    print(f"\nHexagon equation check (F·R·F ≈ R·F·R):")
    print(f"  Max deviation: {np.max(np.abs(hexagon_lhs - hexagon_rhs)):.6f}")

    print("\n" + "-" * 50)
    print("Braid sequence demonstrations:")
    print("-" * 50)

    demos = demonstrate_braiding()
    for d in demos:
        print(f"\n  {d['name']}: {d['description']}")
        print(f"    Braid word     : {d['braid_sequence']}")
        print(f"    Nearest gate   : {d['nearest_clifford']}")
        print(f"    Fidelity       : {d['fidelity_to_nearest_clifford']:.4f}")
        print(f"    Unitary        : {d['is_unitary']}")

    # Build full result
    s1 = sigma1()
    s2 = sigma2()

    results = {
        "anyon_type": "Fibonacci anyon τ",
        "fusion_rules": {"tau_x_tau": "1 + tau", "tau_x_1": "tau", "1_x_1": "1"},
        "golden_ratio_phi": phi,
        "F_matrix": {
            "name": "F^{ττ}_{ττ}",
            "real": F.real.tolist(),
            "imag": F.imag.tolist(),
            "is_unitary": bool(np.allclose(F @ F.conj().T, np.eye(2))),
        },
        "R_matrix_diagonal": {
            "R_tau_1":   {"value": complex(R[0, 0]), "angle_deg": float(np.angle(R[0, 0]) * 180 / np.pi)},
            "R_tau_tau": {"value": complex(R[1, 1]), "angle_deg": float(np.angle(R[1, 1]) * 180 / np.pi)},
        },
        "sigma1": {
            "real": s1.real.tolist(),
            "imag": s1.imag.tolist(),
            "is_unitary": bool(np.allclose(s1 @ s1.conj().T, np.eye(2))),
        },
        "sigma2": {
            "real": s2.real.tolist(),
            "imag": s2.imag.tolist(),
        },
        "braid_sequence": demos[4]["braid_sequence"],
        "resulting_gate": {
            "real": demos[4]["gate_real"],
            "imag": demos[4]["gate_imag"],
        },
        "gate_fidelity": demos[4]["fidelity_to_nearest_clifford"],
        "all_demonstrations": demos,
        "universality": (
            "Fibonacci anyons are computationally universal: "
            "any single-qubit gate can be approximated to arbitrary precision "
            "by a sufficiently long braid sequence."
        ),
        "hexagon_equation_max_error": float(np.max(np.abs(hexagon_lhs - hexagon_rhs))),
    }

    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "braiding_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to {out_path}")
    print("\nFibonacci anyon braiding simulation complete.")


if __name__ == "__main__":
    main()
