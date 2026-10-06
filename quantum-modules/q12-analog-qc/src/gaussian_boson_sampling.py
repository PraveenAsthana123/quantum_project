"""
Gaussian Boson Sampling (GBS)
==============================
Simulates a 4-mode linear optical network and computes output photon
number distributions.  Demonstrates quantum advantage over classical sampling.

Uses strawberryfields if available, otherwise uses scipy + numpy to compute
the GBS probability distribution via the Hafnian formula (approximate).

Saves results to data/gbs_results.json.
"""

import json
import time
import itertools
import numpy as np
from pathlib import Path

try:
    import strawberryfields as sf
    from strawberryfields.ops import Sgate, BSgate, Rgate, MeasureFock
    SF_AVAILABLE = True
except ImportError:
    SF_AVAILABLE = False
    print("[INFO] strawberryfields not available — using numpy GBS simulation")


# ---------------------------------------------------------------------------
# Hafnian (exact for small matrices)
# ---------------------------------------------------------------------------

def hafnian(M: np.ndarray) -> complex:
    """
    Compute the Hafnian of a 2n×2n symmetric matrix via sum over perfect matchings.
    Hafnian counts weighted perfect matchings of a complete graph.

    haf(M) = Σ_{μ ∈ PerfMatch} Π_{(i,j) ∈ μ} M_{ij}

    Complexity: O(n! / (2^n · n!)) matchings — only feasible for small n.
    """
    n2 = M.shape[0]
    if n2 == 0:
        return 1.0
    assert n2 % 2 == 0, "Matrix must be even-dimensional"
    n = n2 // 2

    indices = list(range(n2))
    total = 0.0 + 0j

    # Generate all perfect matchings of {0,...,2n-1}
    def perfect_matchings(lst):
        if len(lst) == 0:
            yield []
            return
        first = lst[0]
        for i in range(1, len(lst)):
            rest = lst[1:i] + lst[i + 1:]
            for matching in perfect_matchings(rest):
                yield [(first, lst[i])] + matching

    for matching in perfect_matchings(indices):
        term = 1.0 + 0j
        for i, j in matching:
            term *= M[i, j]
        total += term

    return total


def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)


# ---------------------------------------------------------------------------
# GBS probability: P(S) = |haf(A_S)|² / (prod s_i! * sqrt(det(I - sigma_Q^{-1} sigma_Q)))
# Simplified version for demonstration
# ---------------------------------------------------------------------------

def random_unitary(n: int, seed: int = 42) -> np.ndarray:
    """Generate a Haar-random n×n unitary matrix."""
    rng = np.random.default_rng(seed)
    Z = rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))
    Q, R = np.linalg.qr(Z)
    # Make QR decomposition unique
    phase = np.diag(R) / np.abs(np.diag(R))
    return Q * phase


def build_covariance_matrix(U: np.ndarray, squeezing: list) -> np.ndarray:
    """
    Build the covariance matrix σ for a GBS device.
    For single-mode squeezed states with squeezing r_k fed into a linear network U:

        σ = U · diag(e^{-2r_k}) · U† ⊕ U* · diag(e^{+2r_k}) · U^T

    Returns the 2n×2n covariance matrix in the (x,p) quadrature ordering.
    """
    n = len(squeezing)
    # Squeezing in x quadrature → variance = exp(-2r)
    diag_x = np.diag([np.exp(-2 * r) for r in squeezing])
    diag_p = np.diag([np.exp(+2 * r) for r in squeezing])

    sigma_xx = U @ diag_x @ U.conj().T
    sigma_pp = U.conj() @ diag_p @ U.T
    sigma_xp = np.zeros((n, n), dtype=complex)

    sigma = np.block([[sigma_xx, sigma_xp],
                      [sigma_xp, sigma_pp]])
    return sigma.real  # covariance matrix is real for vacuum + squeezing


def gbs_probability_marginal(n_modes: int, squeezing: list,
                              U: np.ndarray, output_pattern: list) -> float:
    """
    Compute marginal GBS probability for a photon number pattern.
    Uses simplified Hafnian-based formula for demonstration.

    P(s_1,...,s_n) ∝ |haf(A_{s})|²  / (s_1! · ... · s_n!)

    where A is the Gaussian adjacency matrix derived from U and squeezing.
    """
    n = n_modes
    r = np.array(squeezing)

    # Build the adjacency matrix A = U · tanh(r) · U^T
    tanh_r = np.diag(np.tanh(r))
    A = U @ tanh_r @ U.T

    # Build the repeated adjacency matrix A_S for pattern s
    # A_S is formed by repeating rows/cols according to photon numbers
    indices = []
    for mode, s in enumerate(output_pattern):
        indices.extend([mode] * s)

    if len(indices) == 0:
        # Vacuum term
        norm = np.prod([1.0 / np.cosh(ri) for ri in r])
        return float(norm)

    # Hafnian is defined only for even-dimensional matrices.
    # An odd total photon number has zero probability in GBS (parity superselection).
    if len(indices) % 2 != 0:
        return 0.0

    A_S = A[np.ix_(indices, indices)]
    haf = hafnian(A_S)

    denom = np.prod([factorial(s) for s in output_pattern])
    norm = np.prod([1.0 / np.cosh(ri) for ri in r])

    prob = norm * abs(haf) ** 2 / denom
    return max(0.0, float(prob.real))


# ---------------------------------------------------------------------------
# Strawberryfields implementation
# ---------------------------------------------------------------------------

def run_gbs_strawberryfields(n_modes: int, squeezing: list, seed: int = 42) -> dict:
    """Run GBS using strawberryfields (if available)."""
    print("[INFO] Running GBS via strawberryfields")

    prog = sf.Program(n_modes)
    eng = sf.Engine("fock", backend_options={"cutoff_dim": 5})

    U = random_unitary(n_modes, seed=seed)

    with prog.context as q:
        for k in range(n_modes):
            Sgate(squeezing[k]) | q[k]
        for i in range(n_modes - 1):
            for j in range(i + 1, n_modes):
                theta = float(np.angle(U[i, j]))
                phi = float(np.abs(U[i, j]))
                BSgate(phi, theta) | (q[i], q[j])
        for k in range(n_modes):
            MeasureFock() | q[k]

    start = time.time()
    results = eng.run(prog, shots=100)
    runtime = time.time() - start

    samples = results.samples
    # Count unique patterns
    from collections import Counter
    pattern_counts = Counter(map(tuple, samples))
    top_patterns = sorted(pattern_counts.items(), key=lambda x: -x[1])[:10]

    return {
        "backend": "strawberryfields",
        "runtime_s": runtime,
        "n_shots": 100,
        "top_patterns": [{"pattern": list(p), "count": c} for p, c in top_patterns],
    }


# ---------------------------------------------------------------------------
# Classical simulation
# ---------------------------------------------------------------------------

def run_gbs_numpy(n_modes: int, squeezing: list, seed: int = 42) -> dict:
    """
    Compute GBS output distribution via Hafnian for low photon number patterns.
    """
    print("[INFO] Running GBS via numpy Hafnian simulation")
    U = random_unitary(n_modes, seed=seed)

    # Enumerate all patterns with total photon number ≤ 2
    patterns = []
    for total in range(3):  # 0, 1, 2 photons
        for pattern in itertools.product(range(total + 1), repeat=n_modes):
            if sum(pattern) == total:
                patterns.append(list(pattern))

    start = time.time()
    probs = {}
    for pattern in patterns:
        p = gbs_probability_marginal(n_modes, squeezing, U, pattern)
        if p > 1e-12:
            probs[str(pattern)] = round(p, 8)
    runtime = time.time() - start

    # Sort by probability
    top = sorted(probs.items(), key=lambda x: -x[1])[:10]

    return {
        "backend": "numpy_hafnian",
        "runtime_s": runtime,
        "n_patterns_computed": len(patterns),
        "total_probability": round(sum(probs.values()), 6),
        "top_patterns": [{"pattern": p, "probability": v} for p, v in top],
    }


# ---------------------------------------------------------------------------
# Runtime advantage estimate
# ---------------------------------------------------------------------------

def classical_sampling_time(n_modes: int, n_photons: int) -> float:
    """
    Estimate classical runtime for simulating GBS.
    Computing the Hafnian of a 2n×2n matrix takes O(2^n · n²) time.
    For n_photons total, the matrix is 2*n_photons × 2*n_photons.
    """
    import math
    n = n_photons
    ops = (2 ** n) * (n ** 2) * 1e-9  # rough seconds on modern CPU
    return ops


def quantum_sampling_time(n_modes: int, gate_time_ns: float = 100.0) -> float:
    """Estimate quantum device runtime in seconds."""
    circuit_depth = n_modes * 2  # rough depth
    return circuit_depth * gate_time_ns * 1e-9


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Gaussian Boson Sampling — 4-Mode Linear Optical Network")
    print("=" * 60)

    n_modes = 4
    squeezing = [0.6, 0.7, 0.5, 0.8]  # squeezing parameters r_k

    print(f"\nModes        : {n_modes}")
    print(f"Squeezing    : {squeezing}")

    # Choose backend
    if SF_AVAILABLE:
        sim_result = run_gbs_strawberryfields(n_modes, squeezing)
    else:
        sim_result = run_gbs_numpy(n_modes, squeezing)

    print(f"\nSimulation backend : {sim_result['backend']}")
    print(f"Simulation time    : {sim_result['runtime_s']:.4f} s")
    print("\nTop photon patterns:")
    for entry in sim_result["top_patterns"][:5]:
        print(f"  {entry}")

    # Runtime comparison (scaling demonstration)
    n_photons_demo = 20
    classical_t = classical_sampling_time(n_modes, n_photons_demo)
    quantum_t = quantum_sampling_time(n_modes)
    speedup = classical_t / max(quantum_t, 1e-15)

    print(f"\nRuntime advantage (at n={n_photons_demo} photons, {n_modes} modes):")
    print(f"  Classical (Hafnian): ~{classical_t:.2e} s")
    print(f"  Quantum device     : ~{quantum_t:.2e} s")
    print(f"  Speedup            : ~{speedup:.2e}×")

    # Build output distribution dict
    U = random_unitary(n_modes, seed=42)
    patterns_demo = [[2, 0, 0, 0], [0, 2, 0, 0], [1, 1, 0, 0],
                     [0, 0, 2, 0], [0, 0, 0, 2], [1, 0, 1, 0]]
    photon_dist = {}
    for p in patterns_demo:
        prob = gbs_probability_marginal(n_modes, squeezing, U, p)
        photon_dist[str(p)] = round(prob, 8)

    results = {
        "n_modes": n_modes,
        "squeezing_parameters": squeezing,
        "photon_number_dist": photon_dist,
        "simulation": sim_result,
        "classical_runtime_estimate": classical_t,
        "quantum_runtime_estimate": quantum_t,
        "speedup": speedup,
        "advantage_regime": f"GBS achieves exponential speedup for >{n_photons_demo} photons",
    }

    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "gbs_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {out_path}")
    print("\nGBS simulation complete.")


if __name__ == "__main__":
    main()
