"""
QC-10: ML-DSA-65 (CRYSTALS-Dilithium) — Post-Quantum Digital Signature
========================================================================
Algorithm  : ML-DSA (Module Lattice Digital Signature Algorithm), NIST FIPS 204
Reference  : Ducas et al., "CRYSTALS-Dilithium: A Lattice-Based Digital
             Signature Scheme", TCHES 2018(1), pp. 238–268.
Complexity : KeyGen O(k·l·n log n); Sign O(iterations × k·l·n log n);
             Verify O(k·l·n log n)
Security   : EUF-CMA under Module-LWE + Module-SIS; 178-bit classical/quantum
             for ML-DSA-65
Quantum Adv: Secure against quantum Shor/Grover; signature = (z, h, c_tilde)
             No secret randomness required (deterministic signing possible)
"""

import time
import os
import hashlib
import numpy as np

# ── ML-DSA-65 parameters ────────────────────────────────────────────────────
N      = 256
Q      = 8380417     # prime, 2^23 - 2^13 + 1
K      = 6           # matrix rows
L      = 5           # matrix columns
ETA    = 4           # secret key polynomial bound
GAMMA1 = 1 << 17     # 2^17
GAMMA2 = (Q - 1) // 88  # ≈ 95232
BETA   = 120         # ||c·s1||_∞ + ||c·s2||_∞ bound (simplified)
TAU    = 49          # challenge weight (# of ±1 in challenge c)

RNG = np.random.default_rng(seed=42)


def _sample_uniform(shape: tuple, rng: np.random.Generator) -> np.ndarray:
    return rng.integers(0, Q, size=shape, dtype=np.int64)


def _sample_small(eta: int, shape: tuple, rng: np.random.Generator) -> np.ndarray:
    """Sample polynomial with coefficients in [-eta, eta]."""
    return rng.integers(-eta, eta + 1, size=shape, dtype=np.int64)


def _poly_mul(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Polynomial multiplication in Z_q[x]/(x^N + 1) using numpy."""
    c = np.convolve(a.astype(np.int64), b.astype(np.int64))
    result = np.zeros(N, dtype=np.int64)
    for i, coef in enumerate(c):
        if i < N:
            result[i] = (result[i] + coef) % Q
        else:
            result[i - N] = (result[i - N] - coef) % Q
    return result


def _mat_vec(A: np.ndarray, v: np.ndarray) -> np.ndarray:
    """K×L matrix times L-vector → K-vector of polynomials."""
    result = np.zeros((K, N), dtype=np.int64)
    for i in range(K):
        for j in range(L):
            p = _poly_mul(A[i, j], v[j])
            result[i] = (result[i] + p) % Q
    return result


def _vec_add(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    return (u + v) % Q


def _infinity_norm(poly_vec: np.ndarray) -> int:
    """Max absolute coefficient across all polynomials."""
    centered = poly_vec.copy()
    # Center coefficients: if c > Q//2, subtract Q
    centered[centered > Q // 2] -= Q
    return int(np.max(np.abs(centered)))


def _challenge_from_hash(mu: bytes, w1: np.ndarray) -> np.ndarray:
    """
    Sample challenge polynomial c with exactly TAU ±1 coefficients.
    H(mu || w1_packed) → sparse ternary polynomial.
    """
    packed = mu + w1.tobytes()
    h = hashlib.shake_256(packed).digest(32)
    seed = int.from_bytes(h, "big")
    rng_ch = np.random.default_rng(seed)

    c = np.zeros(N, dtype=np.int64)
    positions = rng_ch.choice(N, size=TAU, replace=False)
    signs = rng_ch.choice([-1, 1], size=TAU)
    for pos, sign in zip(positions, signs):
        c[pos] = sign
    return c


def _poly_vec_mul_challenge(c: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Multiply challenge polynomial c by each polynomial in vector v."""
    result = np.zeros_like(v)
    for i in range(len(v)):
        result[i] = _poly_mul(c, v[i]) % Q
    return result


def _high_bits(r: np.ndarray, alpha: int = None) -> np.ndarray:
    """Extract high bits of polynomial coefficients."""
    if alpha is None:
        alpha = 2 * GAMMA2
    centered = r.copy().astype(np.int64)
    centered = (centered + Q // 2) % Q - Q // 2  # center
    return (centered + (alpha // 2)) // alpha


def ml_dsa_keygen(rng: np.random.Generator) -> tuple[dict, dict]:
    """
    ML-DSA key generation:
      A ← R^(k×l)_q (uniform)
      s1 ← S^l_η, s2 ← S^k_η
      t = A·s1 + s2
    pk = (A_seed, t); sk = (A_seed, t, s1, s2)
    """
    A_seed = rng.integers(0, 256, size=32, dtype=np.uint8).tobytes()
    A = _sample_uniform((K, L, N), rng)

    s1 = _sample_small(ETA, (L, N), rng)
    s2 = _sample_small(ETA, (K, N), rng)

    t_raw = _mat_vec(A, s1)
    t = _vec_add(t_raw, s2)

    pk = {"A": A, "t": t, "seed": A_seed}
    sk = {"A": A, "t": t, "s1": s1, "s2": s2}
    return pk, sk


def ml_dsa_sign(sk: dict, message: bytes,
                rng: np.random.Generator) -> dict:
    """
    ML-DSA signing (simplified Fiat-Shamir with aborts):
      y ~ S^l_{γ1-1}
      w = A·y; w1 = HighBits(w)
      c_tilde = H(μ, w1)
      z = y + c·s1
      If ||z||_∞ ≥ γ1 - β: restart
      σ = (z, h, c_tilde)
    """
    A = sk["A"]
    s1 = sk["s1"]
    s2 = sk["s2"]
    t = sk["t"]

    mu = hashlib.sha3_256(message).digest()

    max_retries = 100
    for attempt in range(max_retries):
        # Sample y
        y = rng.integers(-GAMMA1 + 1, GAMMA1, size=(L, N), dtype=np.int64)

        # w = A·y
        w = _mat_vec(A, y)

        # w1 = HighBits(w)
        w1 = np.array([_high_bits(w[i]) for i in range(K)], dtype=np.int64)

        # Challenge c
        c = _challenge_from_hash(mu, w1)

        # z = y + c·s1
        cs1 = _poly_vec_mul_challenge(c, s1)
        z = (y + cs1) % Q

        # Rejection: check ||z||_∞ < γ1 - β
        z_norm = _infinity_norm(z)
        if z_norm < GAMMA1 - BETA:
            # Compute hints h (simplified: all zeros for demo)
            h = np.zeros((K, N), dtype=np.int64)
            c_tilde = hashlib.sha3_256(mu + w1.tobytes()).hexdigest()[:64]
            return {
                "z": z,
                "h": h,
                "c_tilde": c_tilde,
                "c": c,        # store challenge for simplified verify
                "w1": w1,      # store w1 for simplified verify
                "retries": attempt + 1,
            }

    # Fallback (should rarely happen in real param sets)
    return {"z": y, "h": np.zeros((K, N)), "c_tilde": "rejected",
            "c": np.zeros(N, dtype=np.int64), "w1": np.zeros((K, N), dtype=np.int64),
            "retries": max_retries}


def ml_dsa_verify(pk: dict, message: bytes, sigma: dict) -> bool:
    """
    ML-DSA verification (simplified):
      Recompute w' = A·z - c·t  (using stored challenge c)
      w'1 = HighBits(w')
      Accept if c_tilde == H(μ, w'1) and ||z||_∞ < γ1 - β

    Note: production ML-DSA encodes c as a bit-string in the signature;
    here we store it directly for the educational simulation.
    """
    A  = pk["A"]
    t  = pk["t"]
    z  = sigma["z"]
    c  = sigma.get("c", np.zeros(N, dtype=np.int64))
    c_tilde_given = sigma["c_tilde"]

    mu = hashlib.sha3_256(message).digest()

    # Recompute w' = A·z - c·t
    Az     = _mat_vec(A, z)
    ct     = _poly_vec_mul_challenge(c, t)   # c·t  (K-vector of polys)
    w_prime = (Az - ct) % Q

    # w'1 = HighBits(w')
    w1_prime = np.array([_high_bits(w_prime[i]) for i in range(K)], dtype=np.int64)

    # Recompute c_tilde
    c_tilde_computed = hashlib.sha3_256(mu + w1_prime.tobytes()).hexdigest()[:64]

    # Norm check
    z_norm = _infinity_norm(z)
    norm_ok = z_norm < GAMMA1 - BETA

    return (c_tilde_given == c_tilde_computed) and norm_ok


def run_scenario() -> dict:
    rng = np.random.default_rng(seed=42)
    t_start = time.perf_counter()

    pk, sk = ml_dsa_keygen(rng)
    t_keygen = time.perf_counter() - t_start

    msg = b"Quantum-safe transaction: Alice pays Bob 1 BTC at block 900000"

    t_sign_start = time.perf_counter()
    sigma = ml_dsa_sign(sk, msg, rng)
    t_sign = time.perf_counter() - t_sign_start

    t_verify_start = time.perf_counter()
    valid = ml_dsa_verify(pk, msg, sigma)
    t_verify = time.perf_counter() - t_verify_start

    # Test with tampered message
    tampered = ml_dsa_verify(pk, b"tampered message", sigma)

    total_ms = (time.perf_counter() - t_start) * 1000

    output = {
        "scenario_id": "QC-10",
        "algorithm": "ML-DSA-65 (CRYSTALS-Dilithium)",
        "sign_verify_valid": valid,
        "tampered_msg_rejected": not tampered,
        "signing_retries": sigma.get("retries", 1),
        "challenge_c_tilde": sigma.get("c_tilde", "")[:32] + "...",
        "keygen_time_ms": round(t_keygen * 1000, 2),
        "sign_time_ms": round(t_sign * 1000, 2),
        "verify_time_ms": round(t_verify * 1000, 2),
        "total_sim_time_ms": round(total_ms, 2),
        "security_model": "EUF-CMA under Module-LWE + Module-SIS",
        "quantum_safe": True,
        "status": "PASS" if valid and not tampered else "FAIL",
    }
    return output


def _print_table(results: dict) -> None:
    print("\n" + "=" * 70)
    print("QC-10  ML-DSA-65 (CRYSTALS-Dilithium) — Post-Quantum Signatures")
    print("=" * 70)
    for k, v in results.items():
        print(f"  {k:<45} {v}")
    print()
    print("  Signature size comparison (NIST FIPS 204 / standard specs):")
    print(f"  {'Scheme':<18} {'Sig (B)':>9} {'PK (B)':>9} {'Security':>12} {'Quantum Safe':>13}")
    print("  " + "-" * 65)
    rows = [
        ("RSA-2048 PSS",  256,  256, "112-bit", "No"),
        ("ECDSA P-256",    64,   64, "128-bit", "No"),
        ("ML-DSA-44",    2420, 1312, "128-bit", "Yes"),
        ("ML-DSA-65",    3309, 1952, "178-bit", "Yes"),
        ("ML-DSA-87",    4627, 2592, "256-bit", "Yes"),
    ]
    for scheme, sig, pk_, sec, qs in rows:
        print(f"  {scheme:<18} {sig:>9} {pk_:>9} {sec:>12} {qs:>13}")
    print("=" * 70)


if __name__ == "__main__":
    res = run_scenario()
    _print_table(res)
