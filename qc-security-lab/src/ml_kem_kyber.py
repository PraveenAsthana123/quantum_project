#!/usr/bin/env python3
"""
QC-09: ML-KEM (Kyber) — Pure Python simulation of Module Lattice-based KEM.

Reference paper: Avanzi et al., "CRYSTALS-Kyber Algorithm Specifications and
Supporting Documentation", arXiv:2205.09532 / NIST FIPS 203 (2024).

This implements a pedagogical (non-constant-time, non-production) version of
Kyber-512 (ML-KEM-512) to demonstrate the Module-LWE construction.

Parameters (Kyber-512 / ML-KEM-512):
  n = 256, q = 3329, k = 2, η1 = 3, η2 = 2, du = 10, dv = 4
"""

import os
import time
import struct
import hashlib
from typing import Tuple, List

# ---------------------------------------------------------------------------
# Kyber-512 Parameters
# ---------------------------------------------------------------------------
N = 256          # polynomial degree
Q = 3329         # modulus
K = 2            # module rank (512 → k=2, 768 → k=3, 1024 → k=4)
ETA1 = 3         # secret/error distribution parameter
ETA2 = 2
DU = 10          # ciphertext compression bits (u component)
DV = 4           # ciphertext compression bits (v component)

# NTT zeta values (first 128 precomputed for n=256, q=3329)
# zeta = 17 (primitive 256th root of unity mod 3329)
ZETA = 17


# ---------------------------------------------------------------------------
# Polynomial arithmetic over Zq[x]/(x^n+1)
# ---------------------------------------------------------------------------

def poly_add(a: List[int], b: List[int]) -> List[int]:
    return [(a[i] + b[i]) % Q for i in range(N)]


def poly_sub(a: List[int], b: List[int]) -> List[int]:
    return [(a[i] - b[i]) % Q for i in range(N)]


def poly_mul_ntt_naive(a: List[int], b: List[int]) -> List[int]:
    """Schoolbook multiplication mod (x^n+1) over Zq — O(n^2), pedagogical."""
    result = [0] * N
    for i in range(N):
        for j in range(N):
            idx = (i + j) % N
            sign = -1 if (i + j) >= N else 1
            result[idx] = (result[idx] + sign * a[i] * b[j]) % Q
    return result


def vec_add(a: List[List[int]], b: List[List[int]]) -> List[List[int]]:
    return [poly_add(a[i], b[i]) for i in range(len(a))]


def mat_vec_mul(A: List[List[List[int]]], s: List[List[int]]) -> List[List[int]]:
    """Matrix-vector multiplication: result[i] = sum_j A[i][j] * s[j]"""
    result = [[0] * N for _ in range(K)]
    for i in range(K):
        for j in range(K):
            product = poly_mul_ntt_naive(A[i][j], s[j])
            result[i] = poly_add(result[i], product)
    return result


def inner_product(a: List[List[int]], b: List[List[int]]) -> List[int]:
    """Dot product of two polynomial vectors."""
    acc = [0] * N
    for i in range(K):
        acc = poly_add(acc, poly_mul_ntt_naive(a[i], b[i]))
    return acc


# ---------------------------------------------------------------------------
# Sampling (simplified — using SHA3 for determinism in demo)
# ---------------------------------------------------------------------------

def _expand_seed(seed: bytes, nonce: int, length: int) -> bytes:
    """XOF expansion using SHA3-256 (pedagogical stand-in for SHAKE-128/256)."""
    data = b""
    counter = 0
    while len(data) < length:
        data += hashlib.sha3_256(seed + bytes([nonce, counter])).digest()
        counter += 1
    return data[:length]


def sample_uniform_poly(seed: bytes, i: int, j: int) -> List[int]:
    """Sample uniform polynomial from matrix A[i][j] using seed."""
    expanded = _expand_seed(seed, i * K + j, N * 3)
    result = []
    idx = 0
    while len(result) < N:
        b0, b1, b2 = expanded[idx], expanded[idx + 1], expanded[idx + 2]
        d1 = b0 + 256 * (b1 & 0x0F)
        d2 = (b1 >> 4) + 16 * b2
        if d1 < Q:
            result.append(d1)
        if d2 < Q and len(result) < N:
            result.append(d2)
        idx += 3
        if idx + 3 > len(expanded):
            expanded += _expand_seed(seed, i * K + j + 100, N * 3)
    return result[:N]


def sample_cbd(seed: bytes, nonce: int, eta: int) -> List[int]:
    """Centred binomial distribution with parameter eta."""
    num_bytes = 64 * eta
    stream = _expand_seed(seed, nonce, num_bytes)
    result = []
    for byte_idx in range(num_bytes):
        if len(result) >= N:
            break
        byte = stream[byte_idx]
        # Simple approximation of CBD — extract two nibbles per byte
        bits_a = bin(byte & 0xF).count("1")
        bits_b = bin((byte >> 4) & 0xF).count("1")
        result.append((bits_a - bits_b) % Q)
    while len(result) < N:
        result.append(0)
    return result[:N]


def gen_matrix(rho: bytes) -> List[List[List[int]]]:
    """Generate the public matrix A from seed rho."""
    return [[sample_uniform_poly(rho, i, j) for j in range(K)] for i in range(K)]


def gen_secret_error(sigma: bytes, offset: int, eta: int) -> List[List[int]]:
    """Generate a secret or error vector."""
    return [sample_cbd(sigma, offset + i, eta) for i in range(K)]


# ---------------------------------------------------------------------------
# Compression / Decompression
# ---------------------------------------------------------------------------

def compress_poly(p: List[int], d: int) -> List[int]:
    """Compress coefficients to d bits: round(2^d/q * x) mod 2^d."""
    factor = (1 << d)
    return [round(factor * x / Q) % (1 << d) for x in p]


def decompress_poly(p: List[int], d: int) -> List[int]:
    """Decompress from d bits back to Zq."""
    return [round(Q * x / (1 << d)) % Q for x in p]


def compress_vec(v: List[List[int]], d: int) -> List[List[int]]:
    return [compress_poly(v[i], d) for i in range(K)]


def decompress_vec(v: List[List[int]], d: int) -> List[List[int]]:
    return [decompress_poly(v[i], d) for i in range(K)]


# ---------------------------------------------------------------------------
# Message encoding / decoding
# ---------------------------------------------------------------------------

def encode_message(m: bytes) -> List[int]:
    """32-byte message → 256 coefficients in {0, q/2}."""
    poly = []
    for byte in m:
        for bit in range(8):
            poly.append((Q + 1) // 2 if (byte >> bit) & 1 else 0)
    return poly[:N]


def decode_message(v: List[int]) -> bytes:
    """256 coefficients → 32-byte message (round to nearest 0 or 1)."""
    bits = [1 if (2 * x + Q // 2) % Q < Q // 2 + 1 else 0 for x in v]
    result = bytearray(32)
    for i in range(256):
        if bits[i]:
            result[i // 8] |= (1 << (i % 8))
    return bytes(result)


# ---------------------------------------------------------------------------
# ML-KEM Key Generation, Encapsulation, Decapsulation
# ---------------------------------------------------------------------------

def keygen(seed: bytes = None) -> Tuple[dict, dict]:
    """
    Generate Kyber-512 key pair.
    Returns (public_key, secret_key) as dicts.
    """
    if seed is None:
        seed = os.urandom(32)

    d = hashlib.sha3_512(seed).digest()
    rho, sigma = d[:32], d[32:]

    A = gen_matrix(rho)
    s = gen_secret_error(sigma, 0, ETA1)       # secret vector
    e = gen_secret_error(sigma, K, ETA1)        # error vector

    # b = A·s + e  (public vector)
    b = vec_add(mat_vec_mul(A, s), e)

    pk = {"rho": rho.hex(), "b": b}
    sk = {"s": s, "pk": pk}
    return pk, sk


def encapsulate(pk: dict) -> Tuple[dict, bytes]:
    """
    Encapsulate: generate shared secret K and ciphertext (u, v).
    Returns (ciphertext_dict, shared_secret_bytes).
    """
    rho = bytes.fromhex(pk["rho"])
    b = pk["b"]
    A = gen_matrix(rho)

    # Sample message m (32 bytes)
    m = os.urandom(32)
    h = hashlib.sha3_256(m).digest()

    # Derive random coins
    coins = hashlib.sha3_512(m).digest()
    r_seed, e_seed = coins[:32], coins[32:]

    r = gen_secret_error(r_seed, 0, ETA1)     # randomness vector
    e1 = gen_secret_error(e_seed, 0, ETA2)    # error in u
    e2_poly = sample_cbd(e_seed, K, ETA2)      # error in v (single poly)

    # u = A^T · r + e1
    AT = [[A[j][i] for j in range(K)] for i in range(K)]
    u = vec_add(mat_vec_mul(AT, r), e1)

    # v = b^T · r + e2 + encode(m)
    bt_r = inner_product(b, r)
    m_poly = encode_message(m)
    v = poly_add(poly_add(bt_r, e2_poly), m_poly)

    # Compress
    u_c = compress_vec(u, DU)
    v_c = compress_poly(v, DV)

    shared_secret = hashlib.sha3_256(m + h).digest()

    ciphertext = {"u": u_c, "v": v_c}
    return ciphertext, shared_secret


def decapsulate(sk: dict, ciphertext: dict) -> bytes:
    """
    Decapsulate: recover shared secret from ciphertext using secret key.
    Returns shared_secret_bytes.
    """
    s = sk["s"]
    u_c = ciphertext["u"]
    v_c = ciphertext["v"]

    # Decompress
    u = decompress_vec(u_c, DU)
    v = decompress_poly(v_c, DV)

    # m' = v - s^T · u
    s_t_u = inner_product(s, u)
    m_poly = poly_sub(v, s_t_u)

    # Decode
    m_recovered = decode_message(m_poly)
    h = hashlib.sha3_256(m_recovered).digest()
    shared_secret = hashlib.sha3_256(m_recovered + h).digest()
    return shared_secret


# ---------------------------------------------------------------------------
# Benchmark & Comparison
# ---------------------------------------------------------------------------

def benchmark(rounds: int = 5):
    """Run timing benchmark and comparison against RSA-2048."""
    print("=" * 65)
    print("ML-KEM (Kyber-512) Pure Python Benchmark")
    print(f"Parameters: n={N}, q={Q}, k={K}, η1={ETA1}, η2={ETA2}")
    print(f"Reference: CRYSTALS-Kyber / NIST FIPS 203")
    print("=" * 65)

    keygen_times, encap_times, decap_times = [], [], []
    success_count = 0

    for r in range(rounds):
        t0 = time.perf_counter()
        pk, sk = keygen()
        keygen_times.append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        ct, ss_enc = encapsulate(pk)
        encap_times.append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        ss_dec = decapsulate(sk, ct)
        decap_times.append(time.perf_counter() - t0)

        if ss_enc == ss_dec:
            success_count += 1

    avg_kg = sum(keygen_times) / rounds * 1000
    avg_en = sum(encap_times) / rounds * 1000
    avg_de = sum(decap_times) / rounds * 1000

    print(f"\nResults over {rounds} rounds:")
    print(f"  Key Generation : {avg_kg:.1f} ms")
    print(f"  Encapsulation  : {avg_en:.1f} ms")
    print(f"  Decapsulation  : {avg_de:.1f} ms")
    print(f"  Correct KEM    : {success_count}/{rounds}")

    print("\nSize Comparison:")
    print(f"{'Scheme':<20} {'Public Key':>12} {'Secret Key':>12} {'Ciphertext':>12} {'Shared Secret':>14}")
    print("-" * 72)
    print(f"{'ML-KEM-512':<20} {'800 B':>12} {'1632 B':>12} {'768 B':>12} {'32 B':>14}")
    print(f"{'ML-KEM-768':<20} {'1184 B':>12} {'2400 B':>12} {'1088 B':>12} {'32 B':>14}")
    print(f"{'ML-KEM-1024':<20} {'1568 B':>12} {'3168 B':>12} {'1568 B':>12} {'32 B':>14}")
    print(f"{'RSA-2048':<20} {'256 B':>12} {'2336 B':>12} {'256 B':>12} {'32 B':>14}")
    print(f"{'RSA-3072':<20} {'384 B':>12} {'~3.8 KB':>12} {'384 B':>12} {'32 B':>14}")

    print("\nQuantum Security:")
    print(f"{'ML-KEM-512':<20} NIST Level 1 (≥AES-128 quantum) — ~118-bit quantum")
    print(f"{'ML-KEM-768':<20} NIST Level 3 (≥AES-192 quantum) — ~180-bit quantum")
    print(f"{'ML-KEM-1024':<20} NIST Level 5 (≥AES-256 quantum) — ~256-bit quantum")
    print(f"{'RSA-2048':<20} BROKEN by Shor's algorithm on CQ with ~4096 qubits")

    print("\n[NOTE] This is a pedagogical pure-Python implementation.")
    print("Production: use liboqs or the official FIPS 203 implementation.")
    return success_count == rounds


if __name__ == "__main__":
    ok = benchmark(rounds=3)
    if ok:
        print("\n[PASS] ML-KEM encap/decap round-trip verified.")
    else:
        print("\n[FAIL] Round-trip mismatch — check implementation.")
