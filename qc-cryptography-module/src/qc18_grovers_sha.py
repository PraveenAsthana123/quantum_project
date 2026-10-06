"""
QC-18: Grover's Algorithm on SHA Hash Functions
Quantum preimage and collision attacks on hash functions.

stdlib + numpy only. Run directly to see results.
Exports run_scenario() -> dict.
"""

import math
import time
import hashlib
import numpy as np


# ---------------------------------------------------------------------------
# Hash security analysis
# ---------------------------------------------------------------------------

HASH_TABLE = [
    {
        "hash": "MD5",
        "output_bits": 128,
        "classical_preimage": "2¹²⁸",
        "quantum_preimage": "2⁶⁴",
        "quantum_collision": "2⁴³",   # BHT: 2^(n/3)
        "nist_status": "Broken classically (Wang 2004)",
        "quantum_assessment": "Also broken quantum; both attacks trivial",
    },
    {
        "hash": "SHA-1",
        "output_bits": 160,
        "classical_preimage": "2¹⁶⁰",
        "quantum_preimage": "2⁸⁰",
        "quantum_collision": "2⁵³",
        "nist_status": "Deprecated (2011)",
        "quantum_assessment": "80-bit quantum preimage — insufficient",
    },
    {
        "hash": "SHA-256",
        "output_bits": 256,
        "classical_preimage": "2²⁵⁶",
        "quantum_preimage": "2¹²⁸",
        "quantum_collision": "2⁸⁵",
        "nist_status": "Safe",
        "quantum_assessment": "128-bit quantum preimage — SAFE",
    },
    {
        "hash": "SHA-384",
        "output_bits": 384,
        "classical_preimage": "2³⁸⁴",
        "quantum_preimage": "2¹⁹²",
        "quantum_collision": "2¹²⁸",
        "nist_status": "Safe",
        "quantum_assessment": "192-bit quantum preimage — SAFE",
    },
    {
        "hash": "SHA-512",
        "output_bits": 512,
        "classical_preimage": "2⁵¹²",
        "quantum_preimage": "2²⁵⁶",
        "quantum_collision": "2¹⁷⁰",
        "nist_status": "Safe",
        "quantum_assessment": "256-bit quantum preimage — SAFE",
    },
    {
        "hash": "SHA3-256",
        "output_bits": 256,
        "classical_preimage": "2²⁵⁶",
        "quantum_preimage": "2¹²⁸",
        "quantum_collision": "2⁸⁵",
        "nist_status": "Safe",
        "quantum_assessment": "128-bit quantum preimage — SAFE (sponge construction)",
    },
    {
        "hash": "BLAKE3-256",
        "output_bits": 256,
        "classical_preimage": "2²⁵⁶",
        "quantum_preimage": "2¹²⁸",
        "quantum_collision": "2⁸⁵",
        "nist_status": "Safe",
        "quantum_assessment": "128-bit quantum preimage — SAFE",
    },
]


# ---------------------------------------------------------------------------
# Grover's preimage attack formulation
# ---------------------------------------------------------------------------

def grover_preimage_ops(n_bits: int) -> dict:
    """Compute Grover oracle calls for preimage attack on n-bit hash."""
    quantum_ops = 2 ** (n_bits // 2)
    classical_ops = 2 ** n_bits
    speedup = classical_ops / quantum_ops
    return {
        "n_bits": n_bits,
        "classical_ops": f"2^{n_bits}",
        "quantum_ops": f"2^{n_bits//2}",
        "quadratic_speedup_factor": f"2^{n_bits - n_bits//2}",
    }


def bht_collision_ops(n_bits: int) -> dict:
    """
    Brassard-Høyer-Tapp quantum collision attack.
    Quantum: O(2^{n/3}) vs classical O(2^{n/2}) birthday.
    """
    return {
        "n_bits": n_bits,
        "classical_birthday": f"2^{n_bits//2}",
        "quantum_bht": f"2^{n_bits//3}",
        "speedup_note": "BHT provides cubic speedup for collision finding",
    }


# ---------------------------------------------------------------------------
# Demo: Grover preimage on 8-bit "toy hash" (sum mod 256)
# ---------------------------------------------------------------------------

def toy_hash(msg: bytes, n_bits: int = 8) -> int:
    """Toy hash: sum of bytes mod 2^n_bits."""
    return sum(msg) % (2 ** n_bits)


def grover_preimage_demo(target_hash: int = 42, n_bits: int = 8) -> dict:
    """
    Grover's preimage on 8-bit toy hash (N=256 states).
    Show amplitude amplification finding a preimage.
    """
    N = 2 ** n_bits
    # Build lookup: all 1-byte preimages
    preimages = [b for b in range(N) if toy_hash(bytes([b]), n_bits) == target_hash]
    M = len(preimages)   # number of marked states
    if M == 0:
        return {"found": False}

    # Grover with M marked states: π/4 × √(N/M) iterations
    n_iters = max(1, round((math.pi / 4) * math.sqrt(N / M)))

    # Simulate
    amplitudes = np.ones(N, dtype=complex) / math.sqrt(N)
    marked = set(preimages)

    def oracle(amps):
        a = amps.copy()
        for idx in marked:
            a[idx] *= -1
        return a

    def diffusion(amps):
        mean_amp = np.mean(amps)
        return 2 * mean_amp * np.ones(N, dtype=complex) - amps

    for _ in range(n_iters):
        amplitudes = oracle(amplitudes)
        amplitudes = diffusion(amplitudes)

    probs = np.abs(amplitudes) ** 2
    best = int(np.argmax(probs))
    success_prob = float(sum(probs[p] for p in preimages))

    return {
        "target_hash": target_hash,
        "preimages_count": M,
        "grover_iterations": n_iters,
        "best_candidate": best,
        "candidate_is_preimage": best in marked,
        "total_success_probability": round(success_prob, 4),
        "classical_expected_ops": N // M,
        "grover_expected_ops": n_iters,
    }


# ---------------------------------------------------------------------------
# Password hashing with quantum consideration
# ---------------------------------------------------------------------------

PASSWORD_HASHING = {
    "Argon2id": {
        "description": "Memory-hard function resists Grover's via memory bandwidth bottleneck",
        "quantum_ops_256bit": "2^128 (memory hardness prevents quantum speedup)",
        "why_safe": (
            "Grover's requires quantum RAM (QRAM) with O(√N) memory operations. "
            "For memory-hard functions, quantum speedup is severely limited by "
            "QRAM access costs. Argon2id with 256-bit output retains ~128-bit quantum security."
        ),
    }
}


# ---------------------------------------------------------------------------
# run_scenario
# ---------------------------------------------------------------------------

def run_scenario() -> dict:
    t0 = time.perf_counter()

    demo = grover_preimage_demo(target_hash=42, n_bits=8)
    preimage_analysis = {k: grover_preimage_ops(row["output_bits"])
                         for k, row in {r["hash"]: r for r in HASH_TABLE}.items()}
    collision_analysis = {r["hash"]: bht_collision_ops(r["output_bits"]) for r in HASH_TABLE}

    # Real SHA-256 demo
    msg = b"quantum"
    sha256_digest = hashlib.sha256(msg).hexdigest()
    sha3_256_digest = hashlib.sha3_256(msg).hexdigest()

    result = {
        "scenario": "QC-18",
        "name": "Grover's Algorithm on SHA Hash Functions",
        "category": "Attack",
        "hash_security_table": HASH_TABLE,
        "grover_demo_8bit": demo,
        "preimage_analysis": preimage_analysis,
        "collision_analysis": collision_analysis,
        "password_hashing": PASSWORD_HASHING,
        "real_hash_demo": {
            "message": msg.decode(),
            "sha256": sha256_digest,
            "sha3_256": sha3_256_digest,
        },
        "recommendation": (
            "SHA-256 and SHA3-256 are quantum-safe for preimage resistance (128-bit). "
            "No immediate migration needed for hashing. "
            "For signatures: migrate from ECDSA (uses SHA-256 + broken ECC) → ML-DSA. "
            "Password hashing: Argon2id retains ~128-bit quantum security. "
            "MD5 and SHA-1 already broken classically — replace immediately."
        ),
        "reference": (
            "Brassard, G., Høyer, P., Tapp, A. (1998). Quantum cryptanalysis of hash and "
            "claw-free functions. LNCS 1380."
        ),
        "elapsed_s": round(time.perf_counter() - t0, 4),
    }
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    res = run_scenario()
    print("=" * 60)
    print(f"QC-18: {res['name']}")
    print("=" * 60)
    print()
    d = res["grover_demo_8bit"]
    print(f"Demo: Grover preimage on 8-bit toy hash, target={d['target_hash']}")
    print(f"  Preimages count:       {d['preimages_count']}")
    print(f"  Grover iterations:     {d['grover_iterations']}")
    print(f"  Classical expected:    {d['classical_expected_ops']} ops")
    print(f"  Best candidate:        {d['best_candidate']} "
          f"({'is preimage' if d['candidate_is_preimage'] else 'NOT preimage'})")
    print(f"  Total success prob:    {d['total_success_probability']:.4f}")
    print()
    print("Hash Security Table:")
    hdr = f"  {'Hash':<12} {'Bits':>5} {'Q-Preimage':>12} {'Q-Collision':>13}  Status"
    print(hdr)
    print("  " + "-" * 66)
    for row in res["hash_security_table"]:
        print(f"  {row['hash']:<12} {row['output_bits']:>5} "
              f"{row['quantum_preimage']:>12} {row['quantum_collision']:>13}  {row['nist_status']}")
    print()
    r = res["real_hash_demo"]
    print(f"SHA-256('{r['message']}') = {r['sha256'][:32]}...")
    print(f"SHA3-256('{r['message']}') = {r['sha3_256'][:32]}...")
    print()
    print(f"Recommendation: {res['recommendation']}")
    print(f"Reference: {res['reference']}")
    print(f"Elapsed: {res['elapsed_s']}s")
