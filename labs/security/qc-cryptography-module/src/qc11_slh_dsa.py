"""
QC-11: SLH-DSA-128f (SPHINCS+) — Hash-Based Stateless Signature
=================================================================
Algorithm  : SLH-DSA (Stateless Hash-based Digital Signature), NIST FIPS 205
Reference  : Bernstein et al., "SPHINCS+: Stateless Hash-based Signatures",
             NIST PQC Round 3 Submission (2022); NIST FIPS 205 (2024).
Complexity : Sign O(h·n·w) for WOTS+; Verify O(h·n·w); fast-verify variant
Security   : EUF-CMA; security reduces purely to hash function properties
             (pre-image resistance, second pre-image resistance, collision)
Quantum Adv: Conservative security: no algebraic structure (unlike lattice
             schemes); security relies only on hash functions; provably post-quantum
"""

import time
import os
import hashlib
import struct
import numpy as np

# ── SLH-DSA-128f parameters (from FIPS 205 Table 2) ─────────────────────────
N       = 16    # security parameter (bytes) — 128f uses n=16
H       = 66    # total tree height
D       = 22    # number of XMSS layers (HT levels)
A       = 6     # FORS tree height
K       = 33    # FORS trees per signature
W       = 16    # WOTS+ Winternitz parameter
LOG_W   = 4     # log2(W) = 4
LEN1    = (8 * N + LOG_W - 1) // LOG_W  # = 32 WOTS+ b-bit blocks
LEN2    = 3     # extra checksum blocks
LEN     = LEN1 + LEN2   # = 35 WOTS+ values per signature

# For demo we use smaller tree depth to keep runtime feasible
DEMO_D  = 3     # demo tree depth (vs 22 in real SLH-DSA-128f)

RNG = np.random.default_rng(seed=42)


def _hash_n(data: bytes, n: int = N) -> bytes:
    """Hash to n bytes using SHA3-256 truncated."""
    return hashlib.sha3_256(data).digest()[:n]


def _prf(seed: bytes, adrs: bytes) -> bytes:
    """Pseudorandom function: H(seed || adrs)."""
    return _hash_n(seed + adrs)


def _thash(pk_seed: bytes, adrs: bytes, msg: bytes) -> bytes:
    """Tweakable hash function T_l for SPHINCS+."""
    return _hash_n(pk_seed + adrs + msg)


def _adrs(layer: int, tree: int, type_: int, keypair: int = 0,
          chain: int = 0, hash_: int = 0) -> bytes:
    """Construct ADRS (address) structure (simplified, 32 bytes)."""
    return struct.pack(">IIIIII", layer, tree % (2**32), type_,
                       keypair % (2**32), chain, hash_)[:N]


# ── WOTS+ ─────────────────────────────────────────────────────────────────────

def _wots_chain(x: bytes, start: int, steps: int,
                pk_seed: bytes, adrs_base: bytes) -> bytes:
    """Compute WOTS+ chain: F^steps(x)."""
    result = x
    for i in range(start, start + steps):
        adrs_i = adrs_base[:6] + struct.pack(">HH", i, 0)[:N - 6]
        result = _thash(pk_seed, adrs_i, result)
    return result


def _wots_keygen(sk_seed: bytes, pk_seed: bytes, adrs_base: bytes) -> tuple[list, list]:
    """
    WOTS+ key generation.
    sk = [F^0(sk_i)] for i in 0..LEN-1
    pk = [F^{w-1}(sk_i)] for i in 0..LEN-1
    """
    sk, pk = [], []
    for i in range(LEN):
        adrs_i = adrs_base[:6] + struct.pack(">HH", 0, i)[:N - 6]
        sk_i = _prf(sk_seed, adrs_i + bytes([i]))
        pk_i = _wots_chain(sk_i, 0, W - 1, pk_seed, adrs_i)
        sk.append(sk_i)
        pk.append(pk_i)
    return sk, pk


def _wots_sign(msg_hash: bytes, sk: list, pk_seed: bytes, adrs_base: bytes) -> list:
    """
    WOTS+ signature: for each nibble (base-W digit) of message hash + checksum,
    compute partial chain F^b(sk_i).
    """
    # Convert message to base-W digits
    digits = []
    for byte in msg_hash[:LEN1 // 2]:
        digits.append((byte >> 4) & 0xF)  # high nibble
        digits.append(byte & 0xF)          # low nibble
    digits = digits[:LEN1]

    # Checksum
    checksum = sum(W - 1 - d for d in digits)
    cs_bytes = struct.pack(">I", checksum)
    for byte in cs_bytes:
        digits.append((byte >> 4) & 0xF)
        digits.append(byte & 0xF)
    digits = digits[:LEN]

    sig = []
    for i, b in enumerate(digits):
        adrs_i = adrs_base[:6] + struct.pack(">HH", 0, i)[:N - 6]
        sig_i = _wots_chain(sk[i], 0, b, pk_seed, adrs_i)
        sig.append(sig_i)
    return sig


def _wots_verify(msg_hash: bytes, sig: list, pk_pub: list,
                 pk_seed: bytes, adrs_base: bytes) -> bool:
    """Verify WOTS+ signature by completing the chain and comparing to pk."""
    digits = []
    for byte in msg_hash[:LEN1 // 2]:
        digits.append((byte >> 4) & 0xF)
        digits.append(byte & 0xF)
    digits = digits[:LEN1]

    checksum = sum(W - 1 - d for d in digits)
    cs_bytes = struct.pack(">I", checksum)
    for byte in cs_bytes:
        digits.append((byte >> 4) & 0xF)
        digits.append(byte & 0xF)
    digits = digits[:LEN]

    for i, b in enumerate(digits):
        adrs_i = adrs_base[:6] + struct.pack(">HH", 0, i)[:N - 6]
        expected_pk = _wots_chain(sig[i], b, W - 1 - b, pk_seed, adrs_i)
        if expected_pk != pk_pub[i]:
            return False
    return True


# ── XMSS tree (demo depth D=3) ───────────────────────────────────────────────

def _xmss_tree(sk_seed: bytes, pk_seed: bytes, depth: int = DEMO_D) -> tuple[list, bytes]:
    """
    Build an XMSS tree of depth d.
    Leaves: WOTS+ public keys (hashed to N bytes).
    Internal nodes: tweakable hash of children.
    Returns (auth_paths_for_all_leaves, root).
    """
    n_leaves = 1 << depth  # 2^d leaves

    # Generate leaf nodes (WOTS+ PK hashes)
    leaves = []
    all_pk = []
    for i in range(n_leaves):
        adrs_b = _adrs(0, 0, 1, keypair=i)
        _, pk = _wots_keygen(sk_seed, pk_seed, adrs_b)
        pk_bytes = b"".join(pk)
        leaf = _hash_n(pk_bytes)
        leaves.append(leaf)
        all_pk.append(pk)

    # Build tree bottom-up
    tree_nodes = [leaves]
    current = leaves
    for lvl in range(depth):
        next_level = []
        for j in range(0, len(current), 2):
            parent = _thash(pk_seed,
                            struct.pack(">II", lvl, j // 2)[:N],
                            current[j] + current[j + 1])
            next_level.append(parent)
        tree_nodes.append(next_level)
        current = next_level

    root = current[0]

    # Build auth path for leaf 0
    auth_path = []
    idx = 0
    for lvl in range(depth):
        sibling = idx ^ 1
        auth_path.append(tree_nodes[lvl][sibling])
        idx >>= 1

    return auth_path, root, all_pk


def _xmss_verify_auth(leaf: bytes, auth_path: list, idx: int,
                      pk_seed: bytes, depth: int = DEMO_D) -> bytes:
    """Compute root from leaf + authentication path."""
    node = leaf
    for lvl, sibling in enumerate(auth_path):
        if (idx >> lvl) & 1 == 0:
            node = _thash(pk_seed,
                          struct.pack(">II", lvl, idx >> (lvl + 1))[:N],
                          node + sibling)
        else:
            node = _thash(pk_seed,
                          struct.pack(">II", lvl, idx >> (lvl + 1))[:N],
                          sibling + node)
    return node


def slh_dsa_keygen(rng: np.random.Generator) -> tuple[dict, dict]:
    """SLH-DSA key generation (simplified demo version)."""
    sk_seed = rng.integers(0, 256, size=N, dtype=np.uint8).tobytes()
    pk_seed = rng.integers(0, 256, size=N, dtype=np.uint8).tobytes()

    auth_path, root, all_pk = _xmss_tree(sk_seed, pk_seed)

    pk = {"pk_seed": pk_seed, "root": root}
    sk = {"sk_seed": sk_seed, "pk_seed": pk_seed, "root": root,
          "auth_path": auth_path, "all_pk": all_pk}
    return pk, sk


def slh_dsa_sign(sk: dict, message: bytes) -> dict:
    """SLH-DSA signing (simplified: sign with leaf 0 WOTS+)."""
    sk_seed  = sk["sk_seed"]
    pk_seed  = sk["pk_seed"]
    auth_path = sk["auth_path"]
    all_pk   = sk["all_pk"]

    msg_hash = _hash_n(message)
    leaf_idx = 0

    adrs_b = _adrs(0, 0, 1, keypair=leaf_idx)
    wots_pk = all_pk[leaf_idx]
    wots_sk, _ = _wots_keygen(sk_seed, pk_seed, adrs_b)
    wots_sig = _wots_sign(msg_hash, wots_sk, pk_seed, adrs_b)

    leaf_hash = _hash_n(b"".join(wots_pk))

    return {
        "wots_sig": wots_sig,
        "auth_path": auth_path,
        "leaf_idx": leaf_idx,
        "msg_hash": msg_hash,
    }


def slh_dsa_verify(pk: dict, message: bytes, sigma: dict) -> bool:
    """SLH-DSA verification."""
    pk_seed   = pk["pk_seed"]
    root      = pk["root"]
    wots_sig  = sigma["wots_sig"]
    auth_path = sigma["auth_path"]
    leaf_idx  = sigma["leaf_idx"]
    msg_hash  = sigma["msg_hash"]

    # Verify msg_hash
    if _hash_n(message) != msg_hash:
        return False

    adrs_b = _adrs(0, 0, 1, keypair=leaf_idx)

    # Recover WOTS+ PK from signature
    # We need to reconstruct the pk from sig (simplified: use stored pk from sk for demo)
    # In real SLH-DSA, WOTS+ verification computes pk from sig directly
    reconstructed_pk = []
    digits = []
    for byte in msg_hash[:LEN1 // 2]:
        digits.append((byte >> 4) & 0xF)
        digits.append(byte & 0xF)
    digits = digits[:LEN1]
    checksum = sum(W - 1 - d for d in digits)
    cs_bytes = struct.pack(">I", checksum)
    for byte in cs_bytes:
        digits.append((byte >> 4) & 0xF)
        digits.append(byte & 0xF)
    digits = digits[:LEN]

    for i, b in enumerate(digits):
        adrs_i = adrs_b[:6] + struct.pack(">HH", 0, i)[:N - 6]
        pk_i = _wots_chain(wots_sig[i], b, W - 1 - b, pk_seed, adrs_i)
        reconstructed_pk.append(pk_i)

    leaf_hash = _hash_n(b"".join(reconstructed_pk))

    # Verify auth path
    computed_root = _xmss_verify_auth(leaf_hash, auth_path, leaf_idx, pk_seed)
    return computed_root == root


def run_scenario() -> dict:
    rng = np.random.default_rng(seed=42)
    t_start = time.perf_counter()

    pk, sk = slh_dsa_keygen(rng)
    t_keygen = time.perf_counter() - t_start

    msg = b"Quantum-safe firmware update: version 3.14.159 signed by OEM"

    t_sign_start = time.perf_counter()
    sigma = slh_dsa_sign(sk, msg)
    t_sign = time.perf_counter() - t_sign_start

    t_verify_start = time.perf_counter()
    valid = slh_dsa_verify(pk, msg, sigma)
    t_verify = time.perf_counter() - t_verify_start

    tampered = slh_dsa_verify(pk, b"tampered firmware", sigma)

    total_ms = (time.perf_counter() - t_start) * 1000

    output = {
        "scenario_id": "QC-11",
        "algorithm": "SLH-DSA-128f (SPHINCS+)",
        "sign_verify_valid": valid,
        "tampered_rejected": not tampered,
        "demo_tree_depth": DEMO_D,
        "full_params_h": H,
        "full_params_d": D,
        "full_params_k": K,
        "full_params_w": W,
        "keygen_time_ms": round(t_keygen * 1000, 2),
        "sign_time_ms": round(t_sign * 1000, 2),
        "verify_time_ms": round(t_verify * 1000, 2),
        "total_sim_time_ms": round(total_ms, 2),
        "security_model": "EUF-CMA; hash-function security only (no algebraic assumptions)",
        "use_cases": "Firmware signing, code signing, certificate revocation",
        "status": "PASS" if valid and not tampered else "FAIL",
    }
    return output


def _print_table(results: dict) -> None:
    print("\n" + "=" * 70)
    print("QC-11  SLH-DSA-128f (SPHINCS+) — Hash-Based Stateless Signatures")
    print("=" * 70)
    for k, v in results.items():
        print(f"  {k:<45} {v}")
    print()
    print("  SLH-DSA variant comparison (NIST FIPS 205):")
    print(f"  {'Variant':<22} {'Sig (B)':>9} {'PK (B)':>9} {'Speed':>10} {'Security':>10}")
    print("  " + "-" * 65)
    rows = [
        ("SLH-DSA-128s",  7856, 32, "Slow",    "128-bit"),
        ("SLH-DSA-128f", 17088, 32, "Fast",    "128-bit"),
        ("SLH-DSA-192s", 16224, 48, "Slow",    "192-bit"),
        ("SLH-DSA-192f", 35664, 48, "Fast",    "192-bit"),
        ("SLH-DSA-256s", 29792, 64, "Slow",    "256-bit"),
        ("SLH-DSA-256f", 49856, 64, "Fastest", "256-bit"),
    ]
    for name, sig, pk_, spd, sec in rows:
        print(f"  {name:<22} {sig:>9} {pk_:>9} {spd:>10} {sec:>10}")
    print()
    print("  Use cases: firmware signing (cosign), certificate revocation (OCSP),")
    print("  code signing, long-term document integrity (100-year archives)")
    print("=" * 70)


if __name__ == "__main__":
    res = run_scenario()
    _print_table(res)
