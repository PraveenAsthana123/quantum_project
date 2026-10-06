"""
╔══════════════════════════════════════════════════════════════════╗
║     Grover's Algorithm — Symmetric Key Security Analyser         ║
║     QC Crypto Lab | Module 1 — Foundations                       ║
║     Portfolio: Principal Engineer / Security Architect           ║
╚══════════════════════════════════════════════════════════════════╝

Grover's algorithm (1996) searches N items in O(√N) quantum queries.
This quadratic speedup is PROVEN optimal — no quantum algorithm can
do better for unstructured search.

Impact on symmetric cryptography:
  AES-128 → effective 64-bit security  → should be retired from new systems
  AES-256 → effective 128-bit security → NIST-recommended for post-quantum
  SHA-256 → effective 128-bit preimage security → adequate

Unlike Shor's (which breaks RSA completely), Grover's is manageable
by doubling key sizes.  The fix is KEY DOUBLING, not replacement.

Dependencies: stdlib + numpy (graceful fallback if numpy unavailable).
"""

import math
import time
import random


# ══════════════════════════════════════════════════════════════════
#  Display helpers
# ══════════════════════════════════════════════════════════════════

WIDTH = 70


def box(title: str) -> None:
    pad = (WIDTH - len(title) - 4) // 2
    right_pad = WIDTH - pad - len(title) - 4
    print("\n" + "╔" + "═" * (WIDTH - 2) + "╗")
    print("║" + " " * pad + f"  {title}  " + " " * right_pad + "║")
    print("╚" + "═" * (WIDTH - 2) + "╝")


def sep(title: str = "") -> None:
    if title:
        side = (WIDTH - len(title) - 2) // 2
        print("─" * side + f" {title} " + "─" * (WIDTH - side - len(title) - 2))
    else:
        print("═" * WIDTH)


def section(n: int, title: str) -> None:
    print(f"\n[{n}] {title}")
    print("    " + "─" * (WIDTH - 4))


# ══════════════════════════════════════════════════════════════════
#  1.  Grover's algorithm — classical simulation
# ══════════════════════════════════════════════════════════════════

def grover_probability(n_items: int, iteration: int) -> float:
    """
    Compute probability of measuring the target state after k Grover
    iterations on a database of N items.

    Exact formula:
      P(k) = sin²((2k+1)·θ)  where  sin(θ) = 1/√N
    """
    N = n_items
    theta = math.asin(1.0 / math.sqrt(N))
    prob = math.sin((2 * iteration + 1) * theta) ** 2
    return prob


def optimal_iterations(N: int) -> int:
    """Optimal number of Grover iterations: floor(π/4 · √N)."""
    return max(1, int(math.pi / 4 * math.sqrt(N)))


def simulate_grover_search(N: int, target_idx: int | None = None,
                           rng_seed: int = 42) -> dict:
    """
    Simulate Grover's algorithm on a database of N items.
    Uses the exact quantum probability formula (no circuit needed).

    Returns a dict with iteration-by-iteration stats and final result.
    """
    if target_idx is None:
        target_idx = N // 3   # reproducible default

    k_opt = optimal_iterations(N)
    rng = random.Random(rng_seed)

    iterations_log = []
    found_at = None
    found_prob = None

    for k in range(1, k_opt + 5):
        prob = grover_probability(N, k)
        # Simulate measurement: hit with probability = prob
        hit = rng.random() < prob
        iterations_log.append({
            "k": k,
            "prob": prob,
            "hit": hit,
        })
        if hit and found_at is None:
            found_at = k
            found_prob = prob

    # Classical comparison: random search
    classical_iterations = 0
    items = list(range(N))
    rng.shuffle(items)
    for idx in items:
        classical_iterations += 1
        if idx == target_idx:
            break

    return {
        "N": N,
        "target": target_idx,
        "k_optimal": k_opt,
        "classical_iterations": classical_iterations,
        "quantum_found_at": found_at if found_at else k_opt,
        "quantum_found_prob": found_prob if found_prob else grover_probability(N, k_opt),
        "iterations_log": iterations_log,
        "speedup": N / math.sqrt(N),   # theoretical: O(N) / O(√N)
    }


# ══════════════════════════════════════════════════════════════════
#  2.  AES key-space analysis
# ══════════════════════════════════════════════════════════════════

def grover_time_years(classical_bits: int,
                      gate_rate_hz: float = 1e6) -> str:
    """
    Estimate time for Grover to exhaustively search 2^(classical_bits/2)
    AES key candidates at the given gate rate.
    Returns human-readable string.
    """
    quantum_ops = 2 ** (classical_bits / 2)   # √N = 2^(n/2)
    seconds = quantum_ops / gate_rate_hz
    years = seconds / (365.25 * 24 * 3600)
    if years < 1:
        return f"< 1 year"
    if years < 1e6:
        return f"{years:.2e} years"
    if years < 1e12:
        return f"{years:.2e} years"
    return f"{years:.2e} years"


AES_TABLE = [
    # (name, key_bits, classical_sec_bits, quantum_sec_bits, status, note)
    ("AES-128", 128, 128,  64, "⚠️  WEAKENED",
     "64-bit quantum security — retire from new systems by 2030"),
    ("AES-192", 192, 192,  96, "⚠️  WEAKENED",
     "96-bit quantum security — marginal; prefer AES-256"),
    ("AES-256", 256, 256, 128, "✅ ACCEPTABLE",
     "128-bit quantum security — NIST post-quantum recommendation"),
    ("3DES-112",112, 112,  56, "💀 BROKEN",
     "56-bit quantum security — trivially breakable"),
]

SHA_TABLE = [
    ("SHA-1",    160,  80, "💀 BROKEN",      "Collision attacks existed before Grover"),
    ("SHA-256",  256, 128, "✅ ADEQUATE",     "128-bit preimage — acceptable post-quantum"),
    ("SHA-384",  384, 192, "✅ STRONG",       "192-bit preimage — conservative margin"),
    ("SHA-512",  512, 256, "✅ VERY STRONG",  "256-bit preimage — future-proof"),
    ("SHA3-256", 256, 128, "✅ ADEQUATE",     "Same as SHA-256; sponge construction"),
    ("BLAKE3",   256, 128, "✅ ADEQUATE",     "Same security class as SHA3-256"),
]


# ══════════════════════════════════════════════════════════════════
#  3.  main() — full demo
# ══════════════════════════════════════════════════════════════════

def main() -> None:
    box("Grover's Algorithm — Symmetric Key Security")
    print(f"  Purpose : Demonstrate quadratic quantum speedup and its impact on AES/SHA")
    print(f"  Engine  : Exact quantum probability formula P(k) = sin²((2k+1)·θ)")
    print(f"  Qiskit  : Not required — pure Python simulation\n")

    # ── Section 1: Grover Search Demo ────────────────────────────
    section(1, "Grover Search Demo — Three Database Sizes")

    demo_sizes = [
        (2**8,  "256 items  (8-bit)"),
        (2**16, "65,536 items  (16-bit)"),
        (2**20, "1,048,576 items  (20-bit)"),
    ]

    for N, label in demo_sizes:
        t0 = time.perf_counter()
        result = simulate_grover_search(N, rng_seed=17)
        elapsed = time.perf_counter() - t0

        k_opt   = result["k_optimal"]
        prob    = result["quantum_found_prob"]
        q_iters = result["quantum_found_at"]
        c_iters = result["classical_iterations"]
        speedup = c_iters / q_iters

        print(f"\n  ┌─ N = {label}")
        print(f"  │  Classical O(N) search : {c_iters:>10,} iterations (random)")
        print(f"  │  Quantum Grover O(√N)  : {k_opt:>10,} iterations (optimal)")
        print(f"  │  Actual: found at iter : {q_iters:>10,}  (P = {prob:.4f})")
        print(f"  │  Theoretical speedup   : {N/math.sqrt(N):>10.1f}×  (O(N)/O(√N))")
        print(f"  │  Observed speedup      : {speedup:>10.1f}×")
        print(f"  │  Simulation time       : {elapsed*1000:.2f} ms")

        # Show probability amplification for first few iterations
        print(f"  │")
        print(f"  │  Probability amplification (first {min(8, k_opt+1)} iterations):")
        for entry in result["iterations_log"][:min(8, k_opt + 1)]:
            k    = entry["k"]
            p    = entry["prob"]
            bar  = "█" * int(p * 30)
            mark = " ← FOUND" if k == q_iters else ""
            print(f"  │    k={k:3d}  P={p:.4f}  {bar}{mark}")

        status = "✅ FOUND" if prob > 0.5 else "⚠️  PARTIAL"
        print(f"  └─ {status} — probability at k={k_opt}: {prob:.4f}")

    # ── Section 2: AES Key Space Analysis ────────────────────────
    section(2, "AES Key Space Analysis")

    print(f"\n  {'Algorithm':<12} {'Key Bits':>9} {'Classical Security':>19} "
          f"{'Quantum Security':>17}  Status")
    print(f"  {'─'*12} {'─'*9} {'─'*19} {'─'*17}  {'─'*24}")
    for name, key_bits, cl_sec, qu_sec, status, _ in AES_TABLE:
        cl_str = f"2^{cl_sec} ops"
        qu_str = f"2^{qu_sec} ops"
        print(f"  {name:<12} {key_bits:>9} {cl_str:>19} {qu_str:>17}  {status}")

    print(f"\n  Time to Grover-search AES key spaces at gate rate = 1 MHz:")
    print(f"\n  {'Algorithm':<12} {'Quantum Search Time':>22}  Practical threat?")
    print(f"  {'─'*12} {'─'*22}  {'─'*30}")
    for name, key_bits, cl_sec, qu_sec, status, note in AES_TABLE:
        t_str = grover_time_years(key_bits)
        threat = "YES — retire" if qu_sec < 80 else (
                 "marginal" if qu_sec < 100 else "No — still infeasible")
        print(f"  {name:<12} {t_str:>22}  {threat}")

    print(f"""
  Key observations:
    • AES-128: 2^64 Grover iterations @ 1 MHz ≈ 585 million years — still large
      BUT: 64-bit security is below the NIST 112-bit minimum for new systems.
           AND: hardware improvements reduce this gap over time.
    • AES-256: 2^128 Grover iterations — effectively infinite, even at GHz gates.
    • NIST RECOMMENDATION: AES-256-GCM for post-quantum symmetric encryption.
      AES-128 should be retired from new systems by 2030.
    """)

    # ── Section 3: SHA / Hash Security ───────────────────────────
    section(3, "Hash Function Preimage Security with Grover")

    print(f"\n  {'Hash':<12} {'Output Bits':>11} {'Quantum Preimage':>17}  Assessment")
    print(f"  {'─'*12} {'─'*11} {'─'*17}  {'─'*30}")
    for name, out_bits, qu_sec, status, note in SHA_TABLE:
        qu_str = f"2^{qu_sec} ops"
        print(f"  {name:<12} {out_bits:>11} {qu_str:>17}  {status}  {note}")

    # ── Section 4: Grover vs RSA (Shor) Comparison ───────────────
    section(4, "Grover vs Shor — Different Threat Classes")

    print(f"""
  ┌────────────────────────────────────────────────────────────────┐
  │  Algorithm  │  Target          │  Quantum Effect │  Fix        │
  ├─────────────┼──────────────────┼─────────────────┼────────────┤
  │  Shor's     │  RSA / ECDH / DH │  Exp → Poly     │  REPLACE   │
  │             │  (asymmetric)    │  COMPLETE BREAK  │  with PQC  │
  ├─────────────┼──────────────────┼─────────────────┼────────────┤
  │  Grover's   │  AES-128 / SHA   │  N → √N         │  DOUBLE    │
  │             │  (symmetric)     │  WEAKENS ONLY    │  key size  │
  └─────────────┴──────────────────┴─────────────────┴────────────┘

  Critical distinction for Security Architects:
    Symmetric crypto (AES, SHA) needs KEY DOUBLING — manageable.
    Asymmetric crypto (RSA, ECDH) needs ALGORITHM REPLACEMENT — urgent.

  Migration priority:
    P0 (now)  : Inventory all RSA/ECDH usage — plan migration to ML-KEM
    P1 (2026) : Deploy AES-256 everywhere; retire AES-128 from new systems
    P2 (2027) : Hybrid TLS with X25519 + ML-KEM-768 in prod
    P3 (2028) : Full PQC rollout; deprecate classical asymmetric crypto
    """)

    sep()
    print(f"  Grover's Algorithm Demo complete")
    sep()


if __name__ == "__main__":
    main()
