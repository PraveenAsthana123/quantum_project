"""
CUSTOMER DEMO PITCH — Grover's Algorithm Applied to AES Key Search
===================================================================
Grover's algorithm provides a quadratic speedup for unstructured search.
Applied to AES, it searches the 2^128 (or 2^256) key space in ~2^64 (or 2^128)
quantum operations — halving the effective security level.

This demo implements a 3-qubit Grover to find a 'key' in an 8-element toy space
(analogous to the oracle that checks if a key decrypts a known plaintext-ciphertext pair).
It then extrapolates the attack to AES-128 and AES-256 and provides
NIST-recommended migration guidance.

Audience: Security engineers, CISOs, interview panels.
Runtime: < 10 seconds.
"""

import math
import time

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_sep(title: str = "") -> None:
    w = 66
    if title:
        p = (w - len(title) - 2) // 2
        print("=" * p + f" {title} " + "=" * (w - p - len(title) - 2))
    else:
        print("=" * w)


# ---------------------------------------------------------------------------
# 3-qubit Grover: find target in 8-element space
# ---------------------------------------------------------------------------

def build_oracle_3q(target: int) -> QuantumCircuit:
    """Phase oracle: flip phase of |target⟩ in 3-qubit space."""
    qc = QuantumCircuit(3)
    target_bits = format(target, "03b")
    for i, bit in enumerate(reversed(target_bits)):
        if bit == "0":
            qc.x(i)
    qc.h(2)
    qc.ccx(0, 1, 2)
    qc.h(2)
    for i, bit in enumerate(reversed(target_bits)):
        if bit == "0":
            qc.x(i)
    return qc


def build_diffuser_3q() -> QuantumCircuit:
    """3-qubit Grover diffusion operator."""
    qc = QuantumCircuit(3)
    qc.h(range(3))
    qc.x(range(3))
    qc.h(2)
    qc.ccx(0, 1, 2)
    qc.h(2)
    qc.x(range(3))
    qc.h(range(3))
    return qc


def grover_3q(target: int, iterations: int, shots: int = 2048) -> dict:
    """Run Grover search on 3-qubit register."""
    qc = QuantumCircuit(3)
    qc.h(range(3))
    oracle   = build_oracle_3q(target)
    diffuser = build_diffuser_3q()
    for _ in range(iterations):
        qc.compose(oracle,   inplace=True)
        qc.compose(diffuser, inplace=True)
    qc.measure_all()
    sim    = AerSimulator()
    result = sim.run(qc, shots=shots).result()
    counts = result.get_counts()
    return counts


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    N       = 8         # 2^3 = 8-element search space (toy AES analogy)
    target  = 5         # 'key' index we're looking for
    shots   = 2048
    opt_itr = max(1, round(math.pi / 4 * math.sqrt(N)))

    print_sep("GROVER'S AES ATTACK DEMO — 3-qubit toy key search")
    print(f"  Search space: N={N} keys  (3 qubits, analogous to AES key search)")
    print(f"  Target 'key': index {target}  (binary: {target:03b})")
    print(f"  Optimal Grover iterations: {opt_itr}  (π/4·√{N} ≈ {math.pi/4*math.sqrt(N):.2f})\n")

    # Classical search
    print_sep("Classical Exhaustive Key Search")
    t_cl = time.perf_counter()
    cl_queries = 0
    for i in range(N):
        cl_queries += 1
        if i == target:
            break
    t_cl = time.perf_counter() - t_cl
    print(f"  Keys checked: {cl_queries}  (O(N) worst case)")
    print(f"  Average:      {N//2} queries  (N/2)")
    print(f"  Time:         {t_cl*1e6:.1f} µs\n")

    # Grover iterations table
    print_sep("Quantum Probability Amplification over Iterations")
    print(f"  {'Iter':>5}  {'P(target)':>10}  {'Found/2048':>11}  Query bar")
    print(f"  {'-'*5}  {'-'*10}  {'-'*11}  {'-'*30}")
    for iters in range(0, opt_itr + 2):
        counts = grover_3q(target, iters, shots=shots)
        tgt_str = format(target, "03b")
        found   = counts.get(tgt_str, 0)
        prob    = found / shots
        bar     = "#" * int(prob * 30)
        print(f"  {iters:>5}  {prob:>10.4f}  {found:>11}  {bar}")
    print()

    # Run optimal iteration
    print_sep(f"Optimal Result ({opt_itr} iteration(s))")
    counts_opt = grover_3q(target, opt_itr, shots=shots)
    tgt_str    = format(target, "03b")
    p_found    = counts_opt.get(tgt_str, 0) / shots
    print(f"  Top-3 outcomes:")
    for outcome, cnt in sorted(counts_opt.items(), key=lambda x: -x[1])[:3]:
        mark = " ← TARGET" if int(outcome, 2) == target else ""
        print(f"    |{outcome}⟩ (key={int(outcome,2)})  {cnt:4d}/{shots}  "
              f"({100*cnt/shots:.1f}%){mark}")
    print(f"\n  Classical queries needed:  {N//2} average")
    print(f"  Quantum queries needed:    {opt_itr} ({opt_itr}× Grover oracle calls)")
    print(f"  Speedup:                   {(N//2)/opt_itr:.1f}×  (quadratic: O(√N)/O(N))\n")

    # AES extrapolation
    print_sep("AES Key Space — Grover Attack Extrapolation")
    print(f"  {'Cipher':>12}  {'Key bits':>9}  {'Classical queries':>18}  "
          f"{'Grover queries':>15}  {'Effective bits':>14}  {'Status'}")
    print(f"  {'-'*12}  {'-'*9}  {'-'*18}  {'-'*15}  {'-'*14}  {'-'*25}")

    aes_schemes = [
        ("AES-128", 128),
        ("AES-192", 192),
        ("AES-256", 256),
        ("3DES-112", 112),
        ("ChaCha20-256", 256),
    ]
    for name, k in aes_schemes:
        cl_q   = f"2^{k}"
        gr_q   = f"2^{k//2}"
        eff    = k // 2
        status = "Safe (PQ)" if eff >= 128 else \
                 "Marginal" if eff >= 100 else \
                 "INSUFFICIENT — upgrade"
        print(f"  {name:>12}  {k:>9}  {cl_q:>18}  {gr_q:>15}  {eff:>14}  {status}")

    print()
    print_sep("Quantum Query Budget at Scale")
    print(f"  AES-128 Grover attack requires ~2^64 quantum oracle calls.")
    print(f"  Each oracle call = 1 AES circuit evaluation on quantum hardware.")
    print()
    print(f"  Timeline estimate:")
    print(f"    2024 NISQ machines:  ~1,000 qubits, ~1% error → AES Grover infeasible")
    print(f"    Fault-tolerant QC (est. 2033-2038): AES-128 Grover MAY become relevant")
    print(f"    AES-256 Grover: 2^128 queries even with fault-tolerant QC → safe")
    print()

    # NIST recommendations
    print_sep("NIST Post-Quantum Migration Recommendations (NIST IR 8413)")
    recs = [
        ("AES-128",     "Upgrade to AES-256",       "Grover: 64-bit effective security"),
        ("AES-256",     "Keep — PQ secure",          "Grover: 128-bit effective security"),
        ("SHA-256",     "Keep — adequate",           "Grover: 128-bit preimage security"),
        ("SHA-512",     "Keep — strong",             "Grover: 256-bit preimage security"),
        ("HMAC-SHA256", "Keep with AES-256",         "Depends on key length"),
        ("RSA-2048",    "Replace with ML-KEM NOW",   "Shor: breaks completely"),
        ("ECDH P-256",  "Replace with ML-KEM NOW",   "Shor: breaks completely"),
        ("ECDSA",       "Replace with ML-DSA NOW",   "Shor: breaks completely"),
    ]
    print(f"  {'Scheme':<16}  {'Recommendation':<28}  Notes")
    print(f"  {'-'*16}  {'-'*28}  {'-'*40}")
    for scheme, rec, note in recs:
        print(f"  {scheme:<16}  {rec:<28}  {note}")

    print()
    print_sep("Key Takeaway")
    print("""
  Grover's algorithm provides a quadratic speedup for key search:
    Classical: O(N) queries
    Quantum:   O(√N) queries

  For symmetric cryptography (AES, SHA):
    → Double the key/output length to maintain security post-quantum.
    → AES-256 and SHA-384/512 are safe. AES-128 needs upgrade.
    → This is manageable — no full replacement of symmetric infrastructure.

  For asymmetric cryptography (RSA, ECDH, ECDSA):
    → Shor's algorithm COMPLETELY BREAKS these (exponential → polynomial).
    → No key length increase helps. Must REPLACE with ML-KEM/ML-DSA.
    → Migration should start NOW — harvest-now-decrypt-later attacks are real.
""")
    print_sep()


if __name__ == "__main__":
    main()
