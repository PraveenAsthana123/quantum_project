"""
CUSTOMER DEMO PITCH — QKD Information-Theoretic Security Proof Concepts
========================================================================
Classical cryptography (RSA, ECDH, AES) relies on COMPUTATIONAL security:
breaking it is believed to be hard, but there's no proof it's impossible,
and Shor's algorithm removes the hardness assumption for public-key crypto.

QKD achieves INFORMATION-THEORETIC security (ITS):
  The security proof is based on Shannon entropy and the laws of physics,
  not on unproven computational assumptions.

This demo shows:
  1. Shannon entropy — quantifying information and uncertainty.
  2. Mutual information I(A;B) vs I(A;E) — the security gap.
  3. Secret key capacity: r = I(A;B) - I(A;E) (Csiszár-Körner, 1978).
  4. Comparison: ITS vs computational security.

Audience: CISOs, security architects, board-level briefings, interview panels.
Runtime: < 3 seconds (numpy only).
"""

import math
import numpy as np


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


def h2(p: float) -> float:
    """Binary entropy function H(p)."""
    if p <= 0 or p >= 1:
        return 0.0
    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)


def shannon_entropy(probs: list) -> float:
    """Shannon entropy H(X) = -Σ p_i log₂(p_i)."""
    return -sum(p * math.log2(p) for p in probs if p > 0)


def mutual_information(H_X: float, H_X_given_Y: float) -> float:
    """I(X;Y) = H(X) - H(X|Y)."""
    return max(0.0, H_X - H_X_given_Y)


# ---------------------------------------------------------------------------
# BB84 information-theoretic model
# ---------------------------------------------------------------------------

def bb84_security_analysis(
    qber:             float,   # Quantum Bit Error Rate (Alice-Bob)
    eve_intercept:    float,   # Fraction of qubits Eve intercepts
) -> dict:
    """
    Model the BB84 information-theoretic security.

    H(A)    = 1 bit (uniform key bits)
    H(A|B)  = h(QBER)   (reconciliation removes this)
    I(A;B)  = 1 - h(QBER)

    Eve's information (intercept-resend model):
      For each intercepted qubit, Eve learns the bit with prob. 0.5
      (she guesses the right basis 50% of the time).
    I(A;E) ≈ eve_intercept × 0.5

    Key rate after Privacy Amplification:
      r = I(A;B) - I(A;E)
    """
    H_A     = 1.0
    H_A_B   = h2(qber)          # conditional entropy: errors between Alice and Bob
    I_AB    = H_A - H_A_B       # mutual information Alice-Bob

    # Eve's mutual information (per intercepted bit, she gets 0.5 bits on average)
    I_AE    = eve_intercept * 0.5

    r_secure = max(0.0, I_AB - I_AE)
    return {
        "H_A":     H_A,
        "H_A_B":   H_A_B,
        "I_AB":    I_AB,
        "I_AE":    I_AE,
        "r_secure": r_secure,
        "qber":    qber,
    }


# ---------------------------------------------------------------------------
# Security comparison table
# ---------------------------------------------------------------------------

SECURITY_TABLE = [
    # name, type, threat, mitigation, ITS?
    ("RSA-2048",    "Computational", "Shor's (QC breaks in polynomial time)",
     "Replace with ML-KEM/ML-DSA", "No"),
    ("ECDH P-256",  "Computational", "Shor's (QC breaks in polynomial time)",
     "Replace with ML-KEM",         "No"),
    ("AES-256",     "Computational", "Grover (2^128 effective bits remain)",
     "Keep, already PQ-resistant",  "No"),
    ("SHA-256",     "Computational", "Grover (2^128 preimage security)",
     "Keep, already PQ-resistant",  "No"),
    ("BB84 QKD",    "Information-Theoretic", "None (physics, not math)",
     "No replacement needed",       "Yes"),
    ("E91 QKD",     "Information-Theoretic", "None (Bell inequality certifies)",
     "No replacement needed",       "Yes"),
    ("One-Time Pad","Information-Theoretic", "None (Shannon 1949)",
     "Key distribution is the hard problem", "Yes"),
]


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    print_sep("QKD INFORMATION-THEORETIC SECURITY DEMO")
    print("Purpose: Contrast ITS (QKD) with computational security (RSA/AES)\n")

    # Shannon entropy examples
    print_sep("1. Shannon Entropy — Quantifying Uncertainty")
    examples = [
        ("Uniform coin (fair)",       [0.5, 0.5]),
        ("Biased coin (p=0.9)",       [0.9, 0.1]),
        ("Deterministic (p=1.0)",     [1.0, 0.0]),
        ("4-symbol uniform",          [0.25, 0.25, 0.25, 0.25]),
        ("8-symbol uniform (3-bit)",  [1/8]*8),
    ]
    print(f"  {'Distribution':<35}  {'H(X) bits':>10}  {'Max bits':>10}  Notes")
    print(f"  {'-'*35}  {'-'*10}  {'-'*10}  {'-'*25}")
    for name, probs in examples:
        H  = shannon_entropy(probs)
        mx = math.log2(len(probs))
        frac = H / mx if mx > 0 else 1.0
        note = "maximum entropy" if abs(frac - 1.0) < 0.01 else f"{100*frac:.0f}% of maximum"
        print(f"  {name:<35}  {H:>10.4f}  {mx:>10.4f}  {note}")

    print()

    # BB84 security analysis at various QBER / Eve levels
    print_sep("2. BB84 Information-Theoretic Analysis")
    print(f"  {'QBER%':>6}  {'Eve%':>5}  {'H(A)':>6}  {'H(A|B)':>8}  "
          f"{'I(A;B)':>8}  {'I(A;E)':>8}  {'r_secure':>10}  Status")
    print(f"  {'-'*6}  {'-'*5}  {'-'*6}  {'-'*8}  "
          f"{'-'*8}  {'-'*8}  {'-'*10}  {'-'*20}")
    scenarios = [
        (0.01, 0.00, "No Eve, good channel"),
        (0.03, 0.05, "Slight noise + minor Eve"),
        (0.05, 0.10, "Moderate noise + 10% Eve"),
        (0.10, 0.20, "High noise + aggressive Eve"),
        (0.11, 0.25, "Near threshold"),
        (0.15, 0.30, "Exceeds BB84 security bound"),
        (0.25, 1.00, "Full intercept-resend attack"),
    ]
    for qber, eve_frac, note in scenarios:
        a = bb84_security_analysis(qber, eve_frac)
        secure = "SECURE ✓" if a["r_secure"] > 0 else "ABORT ✗"
        print(f"  {qber*100:>5.1f}%  {eve_frac*100:>4.0f}%  "
              f"{a['H_A']:>6.4f}  {a['H_A_B']:>8.4f}  "
              f"{a['I_AB']:>8.4f}  {a['I_AE']:>8.4f}  {a['r_secure']:>10.4f}  "
              f"{secure}  ({note})")

    print()

    # Key rate vs QBER (no Eve)
    print_sep("3. Shor-Preskill Key Rate: r = 1 - 2·h(QBER)")
    print("   (Asymptotic single-photon BB84, perfect reconciliation)")
    print(f"\n  {'QBER%':>6}  {'r (bits/bit)':>14}  Interpretation")
    print(f"  {'-'*6}  {'-'*14}  {'-'*40}")
    for qber in [0.0, 0.01, 0.03, 0.05, 0.07, 0.09, 0.10, 0.11, 0.13, 0.15]:
        r = max(0.0, 1 - 2 * h2(qber))
        note = "Maximum key rate" if qber == 0 else \
               "Typical lab channel" if qber <= 0.03 else \
               "Acceptable" if qber < 0.11 else \
               "BB84 security threshold" if abs(qber - 0.11) < 0.01 else \
               "Abort session"
        print(f"  {qber*100:>5.1f}%  {r:>14.6f}  {note}")

    print()

    # Security comparison
    print_sep("4. Security Model Comparison")
    print(f"  {'Scheme':<18}  {'Type':<24}  {'Quantum Threat':<35}  {'ITS?'}")
    print(f"  {'-'*18}  {'-'*24}  {'-'*35}  {'-'*5}")
    for name, stype, threat, mitigation, its in SECURITY_TABLE:
        print(f"  {name:<18}  {stype:<24}  {threat:<35}  {its}")

    print()
    print_sep("5. The Core Security Argument")
    print("""
  Classical cryptography (computational security):
    Security claim: "Breaking this requires 2^128 operations."
    Weakness: This is a CONJECTURE. No proof exists that P ≠ NP.
              Shor's algorithm PROVED RSA can be broken in polynomial time
              on a quantum computer — the hardness assumption collapsed.

  QKD (information-theoretic security):
    Security claim: "Eve cannot gain any information without disturbing
                    the channel in a detectable way."
    Basis: Shannon's information theory + no-cloning theorem + linearity of QM.
           These are PROVEN laws of physics, not computational conjectures.

  Key equation (Csiszár-Körner, 1978):
    r_secure = I(A;B) - I(A;E)

    If r_secure > 0:  Alice and Bob can distill a key that is provably
    secret even against an adversary with unlimited computing power.

  This is fundamentally different from RSA, where a sufficiently powerful
  quantum computer (Shor) provides the "unlimited computing power" Eve needs.
""")
    print_sep()


if __name__ == "__main__":
    main()
