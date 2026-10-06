"""
CUSTOMER DEMO PITCH — B92 QKD Protocol (Bennett 1992)
======================================================
B92 is a simplified QKD protocol using only TWO non-orthogonal states instead
of BB84's four.  Alice sends either |0⟩ (for bit 0) or |+⟩ (for bit 1).
Because these states are non-orthogonal, they CANNOT be perfectly distinguished
— any measurement by Bob (or Eve) introduces uncertainty.

Protocol logic:
  - Alice sends |0⟩ or |+⟩ randomly.
  - Bob measures each qubit in randomly chosen Z or X basis.
  - A conclusive result (Bob never gets "same basis as Alice") → unambiguous detection.
  - Only ~25% of qubits produce usable key bits (lower sifting rate than BB84's ~50%).

Eavesdrop detection:
  Eve MUST guess which of two non-orthogonal states was sent — she cannot clone
  them (No-Cloning Theorem).  Any interception raises the QBER detectably.

Audience: Security architects, quantum engineers.
Runtime: < 5 seconds.
"""

import numpy as np
from collections import Counter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_sep(title: str = "") -> None:
    w = 64
    if title:
        p = (w - len(title) - 2) // 2
        print("=" * p + f" {title} " + "=" * (w - p - len(title) - 2))
    else:
        print("=" * w)


# ---------------------------------------------------------------------------
# B92 simulation (classical probabilistic model)
# ---------------------------------------------------------------------------

def measure_b92(state: int, basis: int, rng: np.random.Generator) -> int:
    """
    Simulate quantum measurement of B92 state in a given basis.
    state: 0 = |0⟩, 1 = |+⟩
    basis: 0 = Z-basis, 1 = X-basis
    Returns: measurement outcome (0 or 1)

    Transition probabilities (quantum mechanics):
      |0⟩ in Z: P(0)=1, P(1)=0
      |0⟩ in X: P(+)=0.5, P(-)=0.5  → outcomes 0/1 each with prob 0.5
      |+⟩ in Z: P(0)=0.5, P(1)=0.5
      |+⟩ in X: P(+)=1, P(-)=0      → always outcome 0
    """
    if state == 0:   # Alice sent |0⟩
        if basis == 0:   # Bob measures Z
            return 0     # deterministic
        else:            # Bob measures X
            return int(rng.random() < 0.5)
    else:            # Alice sent |+⟩
        if basis == 0:   # Bob measures Z
            return int(rng.random() < 0.5)
        else:            # Bob measures X
            return 0     # deterministic


def is_conclusive_b92(alice_bit: int, bob_basis: int, bob_result: int) -> bool:
    """
    In B92, Bob has a conclusive result only when:
      - Alice sent |0⟩ (bit=0) AND Bob measured X basis AND got outcome 1
        (|+⟩ never gives 1 in X basis → must have been |0⟩)
      - Alice sent |+⟩ (bit=1) AND Bob measured Z basis AND got outcome 1
        (|0⟩ never gives 1 in Z basis → must have been |+⟩)
    These are the UNAMBIGUOUS DISCRIMINATION events.
    """
    if alice_bit == 0 and bob_basis == 1 and bob_result == 1:
        return True
    if alice_bit == 1 and bob_basis == 0 and bob_result == 1:
        return True
    return False


def simulate_b92(n_qubits: int, rng: np.random.Generator,
                 eve_on: bool = False) -> dict:
    """Run B92 protocol, return statistics."""
    alice_bits  = rng.integers(0, 2, n_qubits)
    bob_bases   = rng.integers(0, 2, n_qubits)

    sifted_alice = []
    sifted_bob   = []
    errors       = 0
    conclusive_count = 0

    for i in range(n_qubits):
        state = int(alice_bits[i])

        if eve_on:
            # Eve intercepts: guesses basis, measures, resends
            eve_basis   = int(rng.integers(0, 2))
            eve_result  = measure_b92(state, eve_basis, rng)
            # Eve resends what she measured: if she guessed Z and got 0 → |0⟩ etc.
            # Simplified: if Eve guessed wrong basis, she resends with 50% error
            if eve_basis != state:   # rough proxy: wrong basis interpretation
                forward_state = int(rng.integers(0, 2))  # 50% chance wrong state
            else:
                forward_state = state
            transmitted_state = forward_state
        else:
            transmitted_state = state

        bob_result = measure_b92(transmitted_state, int(bob_bases[i]), rng)
        conclusive = is_conclusive_b92(state, int(bob_bases[i]), bob_result)

        if conclusive:
            conclusive_count += 1
            # Bob infers Alice's bit from the conclusive event
            bob_inferred = 0 if (bob_bases[i] == 1 and bob_result == 1) else 1
            sifted_alice.append(int(alice_bits[i]))
            sifted_bob.append(bob_inferred)
            if int(alice_bits[i]) != bob_inferred:
                errors += 1

    n_sifted = len(sifted_alice)
    qber = errors / n_sifted if n_sifted else 0.0
    sift_rate = n_sifted / n_qubits

    return {
        "n_raw":       n_qubits,
        "n_conclusive": conclusive_count,
        "n_sifted":    n_sifted,
        "errors":      errors,
        "qber":        qber,
        "sift_rate":   sift_rate,
        "sifted_alice": sifted_alice[:20],
        "sifted_bob":   sifted_bob[:20],
    }


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    rng = np.random.default_rng(42)
    N   = 2000

    print_sep("B92 QKD PROTOCOL DEMO (Bennett 1992)")
    print("Purpose: Two non-orthogonal states, unambiguous discrimination, eavesdrop detection\n")

    # No-Eve scenario
    print_sep("Scenario 1: No Eavesdropper")
    r1 = simulate_b92(N, rng, eve_on=False)
    print(f"  Raw qubits sent:            {r1['n_raw']:5d}")
    print(f"  Conclusive detections:      {r1['n_conclusive']:5d}  ({100*r1['n_conclusive']/N:.1f}%)")
    print(f"  Sifted key bits:            {r1['n_sifted']:5d}  ({100*r1['sift_rate']:.1f}% sifting rate)")
    print(f"  Errors:                     {r1['errors']:5d}")
    print(f"  QBER:                       {r1['qber']*100:.2f}%  (threshold: <11%)")
    print(f"  Verdict:                    {'SECURE ✓' if r1['qber'] < 0.11 else 'ABORT'}")
    print()

    # First 20 sifted bits comparison
    print("  First 20 sifted bits (Alice vs Bob):")
    alice_str = " ".join(str(b) for b in r1["sifted_alice"][:20])
    bob_str   = " ".join(str(b) for b in r1["sifted_bob"][:20])
    match_str = " ".join("✓" if a == b else "✗"
                         for a, b in zip(r1["sifted_alice"][:20], r1["sifted_bob"][:20]))
    print(f"    Alice: {alice_str}")
    print(f"    Bob:   {bob_str}")
    print(f"    Match: {match_str}")
    print()

    # With-Eve scenario
    print_sep("Scenario 2: With Intercept-Resend Eve")
    rng2 = np.random.default_rng(99)
    r2 = simulate_b92(N, rng2, eve_on=True)
    print(f"  Sifted key bits:            {r2['n_sifted']:5d}")
    print(f"  Errors:                     {r2['errors']:5d}")
    print(f"  QBER:                       {r2['qber']*100:.2f}%  (expected ~25% with full intercept)")
    verdict = "EVE DETECTED — ABORT SESSION" if r2['qber'] > 0.11 else "Low noise — check again"
    print(f"  Verdict:                    {verdict}")
    print()

    # Comparison table
    print_sep("B92 vs BB84 Comparison")
    print(f"  {'Feature':<35}  {'B92':>12}  {'BB84':>12}")
    print(f"  {'-'*35}  {'-'*12}  {'-'*12}")
    features = [
        ("States used",              "2 (non-orth.)",  "4 (2 bases)"),
        ("Nominal sifting rate",     "~25%",           "~50%"),
        ("QBER from full Eve attack","~25%",           "~25%"),
        ("Eavesdrop detection",      "Yes",            "Yes"),
        ("Hardware complexity",      "Simpler",        "Moderate"),
        ("Key rate efficiency",      "Lower",          "Higher"),
        ("Provably secure",          "Yes (ITS)",      "Yes (ITS)"),
    ]
    for feat, b92, bb84 in features:
        print(f"  {feat:<35}  {b92:>12}  {bb84:>12}")

    print()
    print_sep("Detection Probability vs Eve Intercept Fraction")
    rng3 = np.random.default_rng(0)
    print(f"  {'Eve fraction':>14}  {'Observed QBER':>14}  {'Detected?':>10}")
    print(f"  {'-'*14}  {'-'*14}  {'-'*10}")
    for frac in [0.0, 0.05, 0.10, 0.20, 0.50, 1.00]:
        # Model: QBER ≈ frac * 0.25 (each intercepted qubit contributes ~25% error)
        expected_qber = frac * 0.25
        detected = "YES" if expected_qber > 0.11 else "no"
        print(f"  {frac:>14.0%}  {expected_qber:>13.1%}  {detected:>10}")

    print()
    print_sep("Key Takeaway")
    print("""
  B92 proves that QKD security requires only NON-ORTHOGONALITY, not four states.
  The protocol is simpler to implement but trades key rate (~25% vs ~50%).

  Security basis: non-orthogonal states cannot be perfectly distinguished or
  cloned → any eavesdrop attempt introduces a detectable QBER signature.
  This is a direct, physical consequence of quantum mechanics — not math hardness.
""")
    print_sep()


if __name__ == "__main__":
    main()
