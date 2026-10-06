"""
╔══════════════════════════════════════════════════════════════════╗
║     Intercept-Resend Attack on BB84                              ║
║     QC Crypto Lab | Module 3 — Attacks                           ║
║     Portfolio: Principal Engineer / Security Architect           ║
╚══════════════════════════════════════════════════════════════════╝

The intercept-resend attack is the most straightforward eavesdropping
strategy against QKD.  Eve intercepts each qubit, measures it in a
randomly chosen basis, and resends her measured state to Bob.

Result:
  • When Eve guesses Alice's basis correctly (50%): no disturbance.
  • When Eve guesses wrong (50%): state is disturbed → Bob errors 50%.
  • Net QBER from full intercept-resend: 25%.
  • BB84 security threshold: 11% QBER.

This simulation shows:
  [1] Baseline BB84 without Eve.
  [2] Full intercept-resend (100% of qubits).
  [3] Partial intercept (50% of qubits).
  [4] Information-theoretic security analysis (Shannon entropy + privacy amp).

Dependencies: stdlib + numpy.
"""

import math
import random
import time

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


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
#  1.  BB84 simulation engine
# ══════════════════════════════════════════════════════════════════

def _rand_bits(n: int, rng: random.Random) -> list[int]:
    return [rng.randint(0, 1) for _ in range(n)]


def simulate_bb84(n_qubits: int,
                  eve_fraction: float,
                  seed: int = 42,
                  noise_rate: float = 0.01) -> dict:
    """
    Simulate BB84 with a specified Eve intercept fraction.

    Parameters
    ----------
    n_qubits    : Total qubits transmitted by Alice.
    eve_fraction: Fraction of qubits Eve intercepts (0.0 – 1.0).
    seed        : RNG seed for reproducibility.
    noise_rate  : Channel noise QBER (without Eve).

    Returns
    -------
    dict with simulation statistics and per-qubit trace (first 20).
    """
    rng = random.Random(seed)

    # Alice
    alice_bits  = _rand_bits(n_qubits, rng)
    alice_bases = _rand_bits(n_qubits, rng)   # 0=Z, 1=X

    # Bob's measurement bases
    bob_bases = _rand_bits(n_qubits, rng)

    # Eve's intercept decision + bases
    eve_intercepts = [rng.random() < eve_fraction for _ in range(n_qubits)]
    eve_bases      = _rand_bits(n_qubits, rng)

    # Compute transmitted state after Eve
    tx_bits  = alice_bits[:]
    tx_bases = alice_bases[:]

    for i in range(n_qubits):
        if eve_intercepts[i]:
            if eve_bases[i] == alice_bases[i]:
                # Correct basis: Eve measures correctly and resends
                tx_bits[i]  = alice_bits[i]
                tx_bases[i] = eve_bases[i]
            else:
                # Wrong basis: Eve gets random bit, resends in wrong basis
                tx_bits[i]  = rng.randint(0, 1)
                tx_bases[i] = eve_bases[i]

    # Bob measures
    bob_bits = []
    for i in range(n_qubits):
        if bob_bases[i] == tx_bases[i]:
            # Same basis → correct bit (plus channel noise)
            if rng.random() < noise_rate:
                bob_bits.append(1 - tx_bits[i])
            else:
                bob_bits.append(tx_bits[i])
        else:
            # Different basis → random result
            bob_bits.append(rng.randint(0, 1))

    # Sifting: keep only where Alice and Bob used same basis
    sifted_alice = []
    sifted_bob   = []
    sifted_idx   = []
    for i in range(n_qubits):
        if alice_bases[i] == bob_bases[i]:
            sifted_alice.append(alice_bits[i])
            sifted_bob.append(bob_bits[i])
            sifted_idx.append(i)

    n_sifted = len(sifted_alice)
    errors   = sum(a != b for a, b in zip(sifted_alice, sifted_bob))
    qber     = errors / n_sifted if n_sifted > 0 else 0.0

    # Eve's information (fraction of sifted bits she has correctly)
    eve_correct = 0
    for i in sifted_idx:
        if eve_intercepts[i] and eve_bases[i] == alice_bases[i]:
            eve_correct += 1
    eve_info = eve_correct / n_sifted if n_sifted > 0 else 0.0

    # Per-qubit trace for display (first 20)
    trace = []
    for i in range(min(20, n_qubits)):
        trace.append({
            "i":         i,
            "a_bit":     alice_bits[i],
            "a_base":    "Z" if alice_bases[i] == 0 else "X",
            "eve_int":   eve_intercepts[i],
            "e_base":    "Z" if eve_bases[i] == 0 else "X",
            "tx_bit":    tx_bits[i],
            "tx_base":   "Z" if tx_bases[i] == 0 else "X",
            "b_base":    "Z" if bob_bases[i] == 0 else "X",
            "b_bit":     bob_bits[i],
            "sifted":    alice_bases[i] == bob_bases[i],
            "error":     alice_bases[i] == bob_bases[i] and alice_bits[i] != bob_bits[i],
        })

    return {
        "n_qubits":    n_qubits,
        "n_sifted":    n_sifted,
        "errors":      errors,
        "qber":        qber,
        "secure":      qber < 0.11,
        "eve_fraction":eve_fraction,
        "eve_info":    eve_info,
        "trace":       trace,
    }


# ══════════════════════════════════════════════════════════════════
#  2.  Information-theoretic analysis helpers
# ══════════════════════════════════════════════════════════════════

def binary_entropy(p: float) -> float:
    """Shannon binary entropy H(p) = -p log2 p - (1-p) log2(1-p)."""
    if p <= 0 or p >= 1:
        return 0.0
    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)


def eve_mutual_info(qber: float) -> float:
    """
    Eve's mutual information I(A;E) for intercept-resend attack.
    At QBER δ: I(A;E) ≈ 1 - H(0.5) + H(δ) is a simplification;
    the tighter bound uses the Csiszár-Körner theorem.

    For intercept-resend at QBER = 0.25:
      Eve knows Alice's bit for every intercept in correct basis → I = 1 bit.
    At threshold QBER = 0.11:
      After privacy amplification, I(A;E) → 0.
    """
    if qber >= 0.25:
        return 1.0   # Eve has full information
    # Linear interpolation for demo clarity
    return qber / 0.25


def privacy_amplification_ratio(qber: float) -> float:
    """
    Fraction of sifted key bits that survive privacy amplification.
    Secure key rate (per sifted bit) = 1 - H(qber) - H(eve_info).
    """
    h_qber = binary_entropy(qber)
    i_eve  = eve_mutual_info(qber)
    rate = 1.0 - h_qber - i_eve
    return max(0.0, rate)


def detection_probability(eve_fraction: float, n_sample: int = 100) -> float:
    """
    P(detect Eve) given she intercepts `eve_fraction` of qubits.
    Uses normal approximation to binomial for the QBER test.

    QBER = 0.25 × eve_fraction.
    Threshold = 0.11.
    P(detect) = P(measured QBER > threshold | true QBER = eve_QBER).
    """
    qber_true = 0.25 * eve_fraction
    if qber_true <= 0:
        return 0.0
    if qber_true >= 0.11:
        # Above threshold on expectation; use normal approx
        mu  = qber_true * n_sample
        sig = math.sqrt(qber_true * (1 - qber_true) * n_sample)
        thr = 0.11 * n_sample
        if sig < 1e-12:
            return 1.0 if qber_true > 0.11 else 0.0
        z = (thr - mu) / sig
        # P(Z > z) using complementary error function
        return 0.5 * math.erfc(z / math.sqrt(2))
    else:
        # Below threshold on expectation; still some detection probability
        mu  = qber_true * n_sample
        sig = math.sqrt(max(qber_true, 0.001) * (1 - qber_true) * n_sample)
        thr = 0.11 * n_sample
        z = (thr - mu) / sig
        return 0.5 * math.erfc(z / math.sqrt(2))


# ══════════════════════════════════════════════════════════════════
#  3.  main() — full demo
# ══════════════════════════════════════════════════════════════════

def main() -> None:
    N = 1000
    THRESHOLD = 0.11

    box("Intercept-Resend Attack on BB84")
    print(f"  Purpose  : Demonstrate eavesdropper detection via QBER elevation")
    print(f"  Protocol : BB84 (Bennett & Brassard, 1984)")
    print(f"  Qubits   : {N} per simulation")
    print(f"  Threshold: QBER > {THRESHOLD*100:.0f}% → eavesdropper detected\n")

    # ── Section 1: Baseline (no Eve) ─────────────────────────────
    section(1, "Baseline BB84 (No Eavesdropping)")

    r0 = simulate_bb84(N, eve_fraction=0.0, seed=42, noise_rate=0.008)
    sifted_pct = r0["n_sifted"] / N * 100
    status_str = "✅ SECURE — QBER below threshold" if r0["secure"] else "❌ ABORT"

    print(f"\n  Alice bits  : {N} random qubits transmitted")
    print(f"  Basis match : {r0['n_sifted']} / {N}  ({sifted_pct:.1f}%)  [~50% expected]")
    print(f"  Sifted key  : {r0['n_sifted']} bits")
    print(f"  Errors      : {r0['errors']} (channel noise only)")
    print(f"  QBER        : {r0['qber']*100:.2f}%  (noise only)")
    print(f"  Security    : {status_str}")
    print(f"\n  Privacy amplification ratio: {privacy_amplification_ratio(r0['qber']):.3f}")
    print(f"  Final secure key size      : ~{int(r0['n_sifted'] * privacy_amplification_ratio(r0['qber']))} bits")

    # ── Section 2: Full intercept-resend ─────────────────────────
    section(2, "Full Intercept-Resend Attack (Eve Intercepts 100%)")

    r1 = simulate_bb84(N, eve_fraction=1.0, seed=99, noise_rate=0.008)
    actual_qber   = r1["qber"]
    expected_qber = 0.25    # theoretical
    eve_info_bits = eve_mutual_info(actual_qber)

    print(f"\n  Eve intercepts : {N}/{N} qubits (100%)")
    print(f"  Eve correct basis prob : ~50% ({r1['n_sifted']//4} qubits correctly read)")
    print(f"  Qubits disturbed by Eve: ~{N//4} (25% of total)")
    print(f"")
    print(f"  Sifted key      : {r1['n_sifted']} bits")
    print(f"  Errors observed : {r1['errors']}")
    print(f"  Alice-Bob QBER  : {actual_qber*100:.2f}%  (expected ~{expected_qber*100:.0f}%)")
    print(f"  Threshold       : {THRESHOLD*100:.0f}%")

    detection_status = "⚠️  EAVESDROPPER DETECTED" if not r1["secure"] else "❌ NOT DETECTED"
    print(f"\n  {detection_status} — QBER = {actual_qber*100:.2f}% >> {THRESHOLD*100:.0f}% threshold")
    print(f"  Action: ABORT key exchange, discard all bits, retry on clean channel")
    print(f"\n  Eve's information per sifted bit : I(A;E) ≈ {eve_info_bits:.3f} bits")
    print(f"  (At QBER=25%, Eve holds maximum information — 1 bit per sifted bit)")

    # Show per-qubit trace for first 12 qubits
    print(f"\n  Per-qubit trace (first 12 qubits):")
    print(f"  {'#':>3}  {'Alice':>7}  {'Eve':>8}  {'TX':>6}  {'Bob':>6}  {'Sifted':>7}  {'Error':>6}")
    print(f"  {'─'*3}  {'─'*7}  {'─'*8}  {'─'*6}  {'─'*6}  {'─'*7}  {'─'*6}")
    for t in r1["trace"][:12]:
        eve_str = f"INT/{t['e_base']}" if t["eve_int"] else "skip"
        print(f"  {t['i']:>3}  {t['a_bit']}/{t['a_base']:>2}      "
              f"{eve_str:>8}  "
              f"{t['tx_bit']}/{t['tx_base']:>2}   "
              f"{t['b_bit']}/{t['b_base']:>2}   "
              f"{'YES' if t['sifted'] else 'no':>7}  "
              f"{'ERR' if t['error'] else 'ok':>6}")

    # ── Section 3: Partial intercept ─────────────────────────────
    section(3, "Partial Intercept Attack (Eve Intercepts 50%)")

    r2 = simulate_bb84(N, eve_fraction=0.5, seed=77, noise_rate=0.008)
    p_detect_50 = detection_probability(0.5, n_sample=r2["n_sifted"] // 5)

    print(f"\n  Eve intercepts : {N // 2}/{N} qubits (~50%)")
    print(f"  Expected QBER  : {0.25*0.5*100:.1f}%  (= 0.25 × intercept_fraction)")
    print(f"  Measured QBER  : {r2['qber']*100:.2f}%")
    print(f"  Threshold      : {THRESHOLD*100:.0f}%")

    det_status = "⚠️  EAVESDROPPER LIKELY DETECTED" if r2["qber"] > THRESHOLD else "⚠️  DETECTION UNCERTAIN"
    print(f"\n  {det_status} — QBER = {r2['qber']*100:.2f}% {'>' if r2['qber'] > THRESHOLD else '≤'} {THRESHOLD*100:.0f}% threshold")
    print(f"  Detection probability at 50% intercept: {p_detect_50*100:.1f}%")

    # Detection probability sweep
    print(f"\n  Detection probability vs Eve's intercept fraction:")
    print(f"\n  {'Eve %':>6}  {'Exp QBER':>9}  {'Detected?':>10}  {'P(detect)':>10}  Notes")
    print(f"  {'─'*6}  {'─'*9}  {'─'*10}  {'─'*10}  {'─'*25}")
    fractions = [0.0, 0.10, 0.20, 0.44, 0.50, 0.75, 1.00]
    for f in fractions:
        eq = 0.25 * f
        detected = "YES ⚠️ " if eq > THRESHOLD else "no"
        p_d = detection_probability(f, n_sample=500)
        note = "← BB84 threshold" if abs(f - 0.44) < 0.01 else (
               "← Full intercept" if f == 1.0 else "")
        print(f"  {f*100:>5.0f}%  {eq*100:>8.2f}%  {detected:>10}  {p_d:>10.4f}  {note}")

    # ── Section 4: Information-theoretic security ─────────────────
    section(4, "Information-Theoretic Security Analysis")

    print(f"""
  BB84 vs Classical TLS — Fundamental Security Class Comparison:

  ┌──────────────────────────────────────────────────────────────┐
  │  Property                │  BB84 / QKD       │  RSA/TLS       │
  ├──────────────────────────┼───────────────────┼────────────────┤
  │  Security basis          │  Physics (HUP)    │  Math (factor) │
  │  Eavesdrop detectable?   │  YES (always)     │  NO            │
  │  Passive intercept?      │  Impossible       │  Trivial       │
  │  Security class          │  Information-theo  │  Computational │
  │  Broken by quantum?      │  NO               │  YES (Shor's)  │
  └──────────────────────────┴───────────────────┴────────────────┘

  Shannon entropy analysis:
    H(QBER=0.00) = {binary_entropy(0.001):.4f} bits  — no disturbance (ideal)
    H(QBER=0.11) = {binary_entropy(0.11):.4f} bits  — BB84 threshold
    H(QBER=0.25) = {binary_entropy(0.25):.4f} bits  — full intercept-resend

  Eve's mutual information I(A;E) per sifted bit:
    Full intercept (QBER=25%) : I(A;E) ≈ 1.000 bit  — Eve knows everything
    At threshold  (QBER=11%) : I(A;E) ≈ 0.440 bits
    After PA      (QBER=11%) : I(A;E) → 0.000 bits  — privacy amplification works

  Privacy amplification (per sifted bit):
    QBER=0.0%  → key rate = {privacy_amplification_ratio(0.001):.3f}  (near perfect)
    QBER=5.0%  → key rate = {privacy_amplification_ratio(0.05):.3f}
    QBER=11.0% → key rate = {privacy_amplification_ratio(0.11):.3f}  (threshold — minimal gain)
    QBER=25.0% → key rate = {privacy_amplification_ratio(0.25):.3f}  (abort — no secure key possible)

  Physical guarantee (Heisenberg Uncertainty Principle):
    A qubit in superposition cannot be measured without disturbing it.
    Eve CANNOT "look without touching" — unlike a classical packet sniffer.

  Conclusion:
    BB84 is information-theoretically secure under the laws of physics.
    RSA/TLS is computationally secure — breakable given sufficient compute.
    → Quantum crypto is PROVABLY more secure than RSA for key distribution.
    """)

    sep()
    print(f"  Intercept-Resend Attack Demo complete — 3 scenarios simulated")
    sep()


if __name__ == "__main__":
    main()
