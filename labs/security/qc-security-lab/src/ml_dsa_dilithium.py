#!/usr/bin/env python3
"""
QC-10: ML-DSA (Dilithium) — Pure Python simulation of Module Lattice-based Digital Signature.

Reference paper: Ducas et al., "CRYSTALS-Dilithium: A Lattice-Based Digital Signature Scheme",
arXiv:1705.01236 / NIST FIPS 204 (2024).

Implements Dilithium2 (ML-DSA-44) parameters for demonstration.

Parameters (Dilithium2 / ML-DSA-44):
  n = 256, q = 8380417, k = 4, l = 4
  γ1 = 2^17, γ2 = (q-1)/88
  η = 2, τ = 39, β = τ·η = 78
  ω = 80 (max ones in hint)
"""

import os
import time
import hashlib
import struct
from typing import Tuple, List, Optional

# ---------------------------------------------------------------------------
# Dilithium2 / ML-DSA-44 Parameters
# ---------------------------------------------------------------------------
N = 256
Q = 8380417         # 2^23 − 2^13 + 1 (NTT-friendly prime)
K = 4               # rows of A (output dimension)
L = 4               # cols of A (input dimension)
ETA = 2             # secret key coefficient range [-η, η]
TAU = 39            # number of ±1's in challenge polynomial
BETA = TAU * ETA    # = 78, bound for z = y + cs
GAMMA1 = 1 << 17    # = 131072, y-vector coefficient range
GAMMA2 = (Q - 1) // 88   # rounding range
OMEGA = 80          # max number of 1's in hint h


# ---------------------------------------------------------------------------
# Polynomial arithmetic over Zq[x]/(x^n+1)
# ---------------------------------------------------------------------------

def poly_add(a: List[int], b: List[int]) -> List[int]:
    return [(a[i] + b[i]) % Q for i in range(N)]


def poly_sub(a: List[int], b: List[int]) -> List[int]:
    return [(a[i] - b[i]) % Q for i in range(N)]


def poly_mul_naive(a: List[int], b: List[int]) -> List[int]:
    """Schoolbook multiplication mod x^n+1 over Zq (pedagogical, not NTT)."""
    res = [0] * N
    for i in range(N):
        for j in range(N):
            idx = (i + j) % N
            sign = -1 if (i + j) >= N else 1
            res[idx] = (res[idx] + sign * a[i] * b[j]) % Q
    return res


def vec_add(a: List[List[int]], b: List[List[int]]) -> List[List[int]]:
    return [poly_add(a[i], b[i]) for i in range(len(a))]


def mat_vec_mul(A: List[List[List[int]]], v: List[List[int]]) -> List[List[int]]:
    """Matrix-vector product: result[i] = sum_j A[i][j] * v[j]"""
    res = [[0] * N for _ in range(K)]
    for i in range(K):
        for j in range(L):
            prod = poly_mul_naive(A[i][j], v[j])
            res[i] = poly_add(res[i], prod)
    return res


def inner_product_kl(a: List[List[int]], b: List[List[int]], dim: int) -> List[int]:
    acc = [0] * N
    for i in range(dim):
        acc = poly_add(acc, poly_mul_naive(a[i], b[i]))
    return acc


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

def _xof(seed: bytes, nonce: int, length: int) -> bytes:
    """Deterministic byte stream (SHAKE-256 stand-in)."""
    data = b""
    ctr = 0
    while len(data) < length:
        data += hashlib.sha3_256(seed + bytes([nonce & 0xFF, (nonce >> 8) & 0xFF, ctr])).digest()
        ctr += 1
    return data[:length]


def sample_uniform_poly(seed: bytes, i: int, j: int) -> List[int]:
    """Sample uniform element of Rq."""
    stream = _xof(seed, i * 16 + j, N * 4)
    result = []
    idx = 0
    while len(result) < N:
        b0, b1, b2 = stream[idx % len(stream)], stream[(idx+1) % len(stream)], stream[(idx+2) % len(stream)]
        val = b0 | (b1 << 8) | ((b2 & 0x7F) << 16)
        if val < Q:
            result.append(val)
        idx += 3
    return result[:N]


def sample_eta(seed: bytes, nonce: int) -> List[int]:
    """Sample polynomial with coefficients uniform in [-η, η]."""
    stream = _xof(seed, nonce, N * 2)
    result = []
    for byte in stream:
        b0 = byte & 0x0F
        b1 = (byte >> 4) & 0x0F
        if b0 < 2 * ETA + 1:
            result.append((b0 - ETA) % Q)
        if b1 < 2 * ETA + 1 and len(result) < N:
            result.append((b1 - ETA) % Q)
        if len(result) >= N:
            break
    while len(result) < N:
        result.append(0)
    return result[:N]


def sample_gamma1(seed: bytes, nonce: int) -> List[int]:
    """Sample polynomial with coefficients uniform in (-γ1, γ1]."""
    stream = _xof(seed, nonce, N * 4)
    result = []
    idx = 0
    while len(result) < N:
        # 18-bit values (γ1 = 2^17)
        b0 = stream[idx % len(stream)]
        b1 = stream[(idx + 1) % len(stream)]
        b2 = stream[(idx + 2) % len(stream)]
        val = b0 | (b1 << 8) | ((b2 & 0x03) << 16)
        coeff = GAMMA1 - val
        result.append(coeff % Q)
        idx += 3
    return result[:N]


def sample_challenge(mu: bytes, rho_prime: bytes) -> List[int]:
    """Sample challenge polynomial c: exactly τ nonzero ±1 coefficients."""
    seed = hashlib.sha3_256(mu + rho_prime).digest()
    stream = _xof(seed, 0, N + TAU * 4)
    c = [0] * N
    # Place ±1's at pseudo-random positions
    placed = 0
    idx = 0
    positions = set()
    while placed < TAU:
        pos = stream[idx % len(stream)] % N
        if pos not in positions:
            positions.add(pos)
            sign = 1 if stream[(idx + 1) % len(stream)] & 1 else -1
            c[pos] = sign % Q
            placed += 1
        idx += 2
    return c


def gen_matrix(rho: bytes) -> List[List[List[int]]]:
    return [[sample_uniform_poly(rho, i, j) for j in range(L)] for i in range(K)]


# ---------------------------------------------------------------------------
# High / Low Bit decomposition and hints
# ---------------------------------------------------------------------------

def high_bits(r: int, alpha: int = 2 * GAMMA2) -> int:
    r_mod = r % Q
    r0 = r_mod % alpha
    if r0 > alpha // 2:
        r0 -= alpha
    if r_mod - r0 == Q - 1:
        return 0
    return (r_mod - r0) // alpha


def low_bits(r: int, alpha: int = 2 * GAMMA2) -> int:
    r_mod = r % Q
    r0 = r_mod % alpha
    if r0 > alpha // 2:
        r0 -= alpha
    return r0


def poly_high_bits(p: List[int]) -> List[int]:
    return [high_bits(x) for x in p]


def poly_low_bits(p: List[int]) -> List[int]:
    return [low_bits(x) for x in p]


def infinity_norm(v: List[List[int]]) -> int:
    """||v||_∞ computed as max of absolute values, centered at Q."""
    max_val = 0
    for poly in v:
        for coef in poly:
            c = coef % Q
            if c > Q // 2:
                c = Q - c
            max_val = max(max_val, c)
    return max_val


# ---------------------------------------------------------------------------
# ML-DSA Key Generation, Sign, Verify
# ---------------------------------------------------------------------------

def keygen(seed: bytes = None) -> Tuple[dict, dict]:
    """
    Generate Dilithium2 (ML-DSA-44) key pair.
    Returns (public_key, secret_key).
    """
    if seed is None:
        seed = os.urandom(32)

    d = hashlib.sha3_512(seed).digest()
    rho, rho_prime = d[:32], d[32:64]
    K_hash = hashlib.sha3_256(seed).digest()

    A = gen_matrix(rho)
    s1 = [sample_eta(rho_prime, i) for i in range(L)]
    s2 = [sample_eta(rho_prime, L + i) for i in range(K)]

    # t = A·s1 + s2
    As1 = mat_vec_mul(A, s1)
    t = vec_add(As1, s2)

    # High bits of t → public key component t1
    t1 = [poly_high_bits(t[i]) for i in range(K)]
    t0 = [poly_low_bits(t[i]) for i in range(K)]

    # tr = H(rho || t1)
    t1_bytes = bytes([coef for poly in t1 for coef in poly[:8]])  # abbreviated
    tr = hashlib.sha3_256(rho + t1_bytes).digest()

    pk = {"rho": rho.hex(), "t1": t1}
    sk = {
        "rho": rho.hex(),
        "K": K_hash.hex(),
        "tr": tr.hex(),
        "s1": s1,
        "s2": s2,
        "t0": t0,
        "pk": pk,
    }
    return pk, sk


def sign(sk: dict, message: bytes) -> dict:
    """
    Sign message using Dilithium2.
    Returns signature dict {c_tilde, z, h}.
    """
    rho = bytes.fromhex(sk["rho"])
    K_bytes = bytes.fromhex(sk["K"])
    tr = bytes.fromhex(sk["tr"])
    s1 = sk["s1"]
    s2 = sk["s2"]
    t0 = sk["t0"]

    A = gen_matrix(rho)
    mu = hashlib.sha3_256(tr + message).digest()

    rho_prime = hashlib.sha3_256(K_bytes + mu).digest()

    kappa = 0
    max_attempts = 1000

    for attempt in range(max_attempts):
        # Sample y ∈ [-γ1+1, γ1]^l
        y = [sample_gamma1(rho_prime, kappa * L + i) for i in range(L)]
        kappa += 1

        # w = A·y
        w = mat_vec_mul(A, y)
        w1 = [poly_high_bits(w[i]) for i in range(K)]

        # c = H(μ || w1)
        w1_bytes = bytes([coef & 0xFF for poly in w1 for coef in poly[:4]])
        c = sample_challenge(mu, w1_bytes)

        # z = y + c·s1
        cs1 = [poly_mul_naive(c, s1[i]) for i in range(L)]
        z = vec_add(y, cs1)

        # Check ||z||_∞ < γ1 - β
        if infinity_norm(z) >= GAMMA1 - BETA:
            continue  # reject

        # Check ||lowbits(w - cs2)||_∞ < γ2 - β
        cs2 = [poly_mul_naive(c, s2[i]) for i in range(K)]
        r0 = [poly_low_bits(poly_sub(w[i], cs2[i])) for i in range(K)]
        # Simplify r0 check
        r0_norm = max(abs(x) for poly in r0 for x in poly)
        if r0_norm >= GAMMA2 - BETA:
            continue

        # Success
        c_tilde = hashlib.sha3_256(mu + w1_bytes).hexdigest()
        return {"c_tilde": c_tilde, "z": z, "attempt": attempt + 1, "c": c}

    raise RuntimeError(f"Signing failed after {max_attempts} attempts")


def verify(pk: dict, message: bytes, signature: dict) -> bool:
    """
    Verify Dilithium2 signature.
    Returns True if valid.
    """
    rho = bytes.fromhex(pk["rho"])
    t1 = pk["t1"]
    z = signature["z"]
    c = signature.get("c", [])
    c_tilde = signature["c_tilde"]

    A = gen_matrix(rho)

    # Check ||z||_∞ < γ1 - β
    if infinity_norm(z) >= GAMMA1 - BETA:
        return False

    # Compute Az - ct1·2^d
    Az = mat_vec_mul(A, z)
    ct1 = [poly_mul_naive(c, t1[i]) for i in range(K)]
    # Scale ct1 by 2^13 (D=13 for Dilithium2)
    D_SHIFT = 13
    ct1_scaled = [[(x << D_SHIFT) % Q for x in poly] for poly in ct1]
    w_prime = [poly_sub(Az[i], ct1_scaled[i]) for i in range(K)]
    w1_prime = [poly_high_bits(w_prime[i]) for i in range(K)]

    # Recompute mu
    t1_bytes = bytes([coef & 0xFF for poly in t1 for coef in poly[:8]])
    tr = hashlib.sha3_256(rho + t1_bytes).digest()
    mu = hashlib.sha3_256(tr + message).digest()

    w1_bytes = bytes([coef & 0xFF for poly in w1_prime for coef in poly[:4]])
    c_tilde_check = hashlib.sha3_256(mu + w1_bytes).hexdigest()

    return c_tilde == c_tilde_check


# ---------------------------------------------------------------------------
# Benchmark & Comparison
# ---------------------------------------------------------------------------

def benchmark(rounds: int = 3):
    print("=" * 65)
    print("ML-DSA (Dilithium2) Pure Python Benchmark")
    print(f"Parameters: n={N}, q={Q}, k={K}, l={L}, η={ETA}, τ={TAU}, β={BETA}")
    print(f"Reference: Ducas et al. (2018), NIST FIPS 204 (2024)")
    print("=" * 65)

    kg_times, sign_times, verify_times = [], [], []
    sign_ok = verify_ok = 0
    msg = b"Quantum-safe digital signature test message 2024"

    for r in range(rounds):
        t0 = time.perf_counter()
        pk, sk = keygen()
        kg_times.append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        try:
            sig = sign(sk, msg)
            sign_ok += 1
        except RuntimeError as e:
            print(f"  [SIGN FAIL round {r}]: {e}")
            continue
        sign_times.append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        valid = verify(pk, msg, sig)
        verify_times.append(time.perf_counter() - t0)
        if valid:
            verify_ok += 1

    avg_kg = sum(kg_times) / len(kg_times) * 1000 if kg_times else 0
    avg_sg = sum(sign_times) / len(sign_times) * 1000 if sign_times else 0
    avg_vf = sum(verify_times) / len(verify_times) * 1000 if verify_times else 0

    print(f"\nResults over {rounds} rounds:")
    print(f"  Key Generation : {avg_kg:.1f} ms")
    print(f"  Signing        : {avg_sg:.1f} ms  (sign attempts: {sig.get('attempt','?')})")
    print(f"  Verification   : {avg_vf:.1f} ms")
    print(f"  Sign Success   : {sign_ok}/{rounds}")
    print(f"  Verify Correct : {verify_ok}/{sign_ok}")

    print("\nSize Comparison:")
    print(f"{'Scheme':<22} {'Public Key':>12} {'Secret Key':>12} {'Signature':>12}")
    print("-" * 62)
    print(f"{'ML-DSA-44 (Dil2)':<22} {'1312 B':>12} {'2528 B':>12} {'2420 B':>12}")
    print(f"{'ML-DSA-65 (Dil3)':<22} {'1952 B':>12} {'4000 B':>12} {'3293 B':>12}")
    print(f"{'ML-DSA-87 (Dil5)':<22} {'2592 B':>12} {'4864 B':>12} {'4595 B':>12}")
    print(f"{'ECDSA P-256':<22} {'64 B':>12} {'32 B':>12} {'72 B':>12}")
    print(f"{'RSA-2048 (PKCS1)':<22} {'256 B':>12} {'~1.2 KB':>12} {'256 B':>12}")
    print(f"{'RSA-4096 (PKCS1)':<22} {'512 B':>12} {'~2.4 KB':>12} {'512 B':>12}")

    print("\nQuantum Security:")
    print(f"{'ML-DSA-44':<22} NIST Level 2 — broken by Shor (no, lattice)")
    print(f"{'ML-DSA-65':<22} NIST Level 3 — post-quantum secure")
    print(f"{'ML-DSA-87':<22} NIST Level 5 — highest security")
    print(f"{'ECDSA P-256':<22} BROKEN by Shor's algorithm")
    print(f"{'RSA-2048':<22} BROKEN by Shor's algorithm")


if __name__ == "__main__":
    benchmark(rounds=2)
    print("\n[NOTE] Pedagogical implementation — not production-safe.")
    print("Production: use liboqs, pqcrypto, or oqs-provider for OpenSSL.")
