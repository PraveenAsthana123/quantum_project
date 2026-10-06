"""
CUSTOMER DEMO PITCH — E91 Protocol (Ekert 1991)
================================================
E91 is the entanglement-based QKD protocol.  Instead of Alice preparing and
sending qubits, a central source distributes Bell pairs to Alice and Bob.
Security relies on the violation of Bell's CHSH inequality — a violation means
the correlations are genuinely quantum and cannot be explained by any classical
shared secret (or classical eavesdropper injection).

Key insight: If Eve intercepts or tampers with the entangled pairs, she breaks
the entanglement → CHSH value drops from 2√2 ≈ 2.828 toward the classical
limit of 2 → session aborted.

Measurement settings:
  Alice: a1 = 0°, a2 = 45°, a3 = 90°
  Bob:   b1 = 45°, b2 = 90°, b3 = 135°
  Key bits: when Alice uses a3 and Bob uses b1 (same effective basis, correlated).
  CHSH test: the other angle combinations.

Audience: Security architects, physicists, interview panels.
Runtime: < 10 seconds.
"""

import math
import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


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
# CHSH correlator via quantum circuit
# ---------------------------------------------------------------------------

def correlator_qc(alice_angle_deg: float, bob_angle_deg: float,
                  shots: int = 4000, eve_noise: float = 0.0) -> float:
    """
    Compute E(a, b) = ⟨A_a ⊗ B_b⟩ for |Φ+⟩ Bell pair.
    alice/bob angles are measurement basis angles (degrees from Z axis).

    Theoretical value: E(a,b) = -cos(alice_angle - bob_angle) for |Φ+⟩
                               (anti-correlation convention)

    eve_noise: fraction of qubits replaced by classical random bits (Eve's tampering).
    """
    sim = AerSimulator()
    qc  = QuantumCircuit(2)

    # Create |Φ+⟩ Bell pair
    qc.h(0)
    qc.cx(0, 1)

    # Apply Eve's depolarizing noise (simplified: mix with identity)
    if eve_noise > 0:
        from qiskit_aer.noise import NoiseModel, depolarizing_error
        noise_model = NoiseModel()
        err = depolarizing_error(eve_noise, 1)
        noise_model.add_all_qubit_quantum_error(err, ['h', 'rx'])
    else:
        noise_model = None

    # Rotate Alice's qubit by alice_angle around Y axis (Ry = basis rotation)
    qc.ry(-2 * math.radians(alice_angle_deg), 0)

    # Rotate Bob's qubit
    qc.ry(-2 * math.radians(bob_angle_deg), 1)

    qc.measure_all()
    result = sim.run(qc, shots=shots, noise_model=noise_model).result()
    counts = result.get_counts()

    # Compute ⟨A ⊗ B⟩:  +1 for same, -1 for different
    E = 0.0
    for outcome, cnt in counts.items():
        b_qubit = int(outcome[0])    # qubit 1 (Bob)
        a_qubit = int(outcome[-1])   # qubit 0 (Alice)
        sign = +1 if a_qubit == b_qubit else -1
        E += sign * cnt
    return E / shots


def chsh_S(correlators: dict) -> float:
    """
    S = E(a1,b1) - E(a1,b3) + E(a3,b1) + E(a3,b3)
    E91 measurement angles: a1=0°, a3=90°; b1=45°, b3=135°
    """
    return (correlators["E(a1,b1)"] - correlators["E(a1,b3)"] +
            correlators["E(a3,b1)"] + correlators["E(a3,b3)"])


# E91 angle assignments
ALICE_ANGLES = {"a1": 0, "a2": 45, "a3": 90}
BOB_ANGLES   = {"b1": 45, "b2": 90, "b3": 135}


# ---------------------------------------------------------------------------
# Key sifting from E91
# ---------------------------------------------------------------------------

def e91_key_sifting(n_pairs: int, rng: np.random.Generator,
                    eve_on: bool = False) -> dict:
    """
    Simulate E91 sifting.
    Alice uses a2=45° and Bob uses b2=90° for key bits (anti-correlated → flip Bob's bit).
    Other angle pairs used for CHSH test.
    """
    alice_choices = rng.integers(0, 3, n_pairs)   # 0,1,2 → a1,a2,a3
    bob_choices   = rng.integers(0, 3, n_pairs)   # 0,1,2 → b1,b2,b3

    alice_angle_list = [0, 45, 90]
    bob_angle_list   = [45, 90, 135]

    # For each pair: determine if key bit (a2, b2 both chosen) or CHSH test
    key_alice = []
    key_bob   = []

    for i in range(n_pairs):
        ac = alice_choices[i]
        bc = bob_choices[i]
        aa = alice_angle_list[ac]
        ba = bob_angle_list[bc]

        # Simulate measurement outcome: P(same) = sin²((aa-ba)/2) for |Φ+⟩
        diff_rad = math.radians(aa - ba)
        p_same   = math.sin(diff_rad / 2) ** 2
        same     = rng.random() < p_same
        if eve_on:
            # Eve breaks entanglement: random independent outcomes
            same = rng.random() < 0.5

        alice_bit = int(rng.integers(0, 2))
        bob_bit   = alice_bit if same else 1 - alice_bit

        if ac == 1 and bc == 1:   # a2=45°, b2=90° — key pair
            key_alice.append(alice_bit)
            key_bob.append(1 - bob_bit)   # flip Bob's bit (anti-correlation → correlated)

    errors  = sum(1 for a, b in zip(key_alice, key_bob) if a != b)
    n_key   = len(key_alice)
    qber    = errors / n_key if n_key else 0.0
    return {"key_alice": key_alice[:16], "key_bob": key_bob[:16],
            "n_key": n_key, "qber": qber}


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    rng   = np.random.default_rng(42)
    SHOTS = 3000

    print_sep("E91 PROTOCOL DEMO (Ekert 1991)")
    print("Purpose: Entanglement-based QKD, CHSH inequality eavesdrop detection\n")

    # Compute CHSH correlators — no Eve
    print_sep("CHSH Correlators — No Eavesdropper")
    print(f"  Computing 4 correlators × {SHOTS} shots each...")
    angles = [
        ("E(a1,b1)", 0,   45),
        ("E(a1,b3)", 0,  135),
        ("E(a3,b1)", 90,  45),
        ("E(a3,b3)", 90, 135),
    ]
    corr = {}
    print(f"\n  {'Correlator':<12}  {'Alice°':>7}  {'Bob°':>7}  {'E(a,b)':>8}  {'Theory':>8}")
    print(f"  {'-'*12}  {'-'*7}  {'-'*7}  {'-'*8}  {'-'*8}")
    for name, aa, ba in angles:
        E = correlator_qc(aa, ba, shots=SHOTS)
        theory = -math.cos(math.radians(aa - ba))
        corr[name] = E
        print(f"  {name:<12}  {aa:>7}  {ba:>7}  {E:>+8.4f}  {theory:>+8.4f}")

    S_no_eve = chsh_S(corr)
    S_theory = 2 * math.sqrt(2)
    print(f"\n  CHSH S = {S_no_eve:+.4f}  (theory: {S_theory:.4f}, classical limit: 2.0000)")
    verdict  = "QUANTUM SECURITY VERIFIED ✓" if S_no_eve > 2.0 else "CLASSICAL — ABORT"
    print(f"  Verdict: {verdict}\n")

    # With Eve (noise model)
    print_sep("CHSH Correlators — With Eavesdropper (depolarizing noise)")
    corr_eve = {}
    print(f"  Eve applies 20% depolarizing noise to each qubit...")
    print(f"\n  {'Correlator':<12}  {'E(a,b) with Eve':>16}  {'Drop from ideal':>16}")
    print(f"  {'-'*12}  {'-'*16}  {'-'*16}")
    for name, aa, ba in angles:
        E_eve = correlator_qc(aa, ba, shots=SHOTS, eve_noise=0.20)
        drop  = corr[name] - E_eve
        corr_eve[name] = E_eve
        print(f"  {name:<12}  {E_eve:>+16.4f}  {drop:>+16.4f}")

    S_eve = chsh_S(corr_eve)
    print(f"\n  CHSH S (with Eve) = {S_eve:+.4f}")
    verdict_eve = "EVE DETECTED — ABORT" if abs(S_eve) < 2.0 else "Noise low — continue"
    print(f"  Verdict: {verdict_eve}\n")

    # Key sifting
    print_sep("E91 Key Sifting — No Eve (2000 pairs)")
    kr = e91_key_sifting(2000, rng, eve_on=False)
    print(f"  Pairs generating key bits (a2,b2): {kr['n_key']}")
    print(f"  Key QBER: {kr['qber']*100:.2f}%")
    print(f"  Alice[0:16]: {' '.join(str(b) for b in kr['key_alice'])}")
    print(f"  Bob  [0:16]: {' '.join(str(b) for b in kr['key_bob'])}")
    print()

    # Summary table
    print_sep("E91 vs BB84 Summary")
    rows = [
        ("Qubit source",       "Entangled pairs",    "Alice prepares+sends"),
        ("Source trust",       "Untrusted OK",       "Alice must be trusted"),
        ("Eavesdrop detector", "CHSH inequality",    "QBER threshold"),
        ("Security basis",     "Bell inequality",    "No-Cloning + info theory"),
        ("Key sifting rate",   "~1/9 pairs",         "~50% qubits"),
        ("Device-independent", "Yes (Bell test)",    "No"),
    ]
    print(f"  {'Feature':<28}  {'E91':>22}  {'BB84':>22}")
    print(f"  {'-'*28}  {'-'*22}  {'-'*22}")
    for f, e91, bb84 in rows:
        print(f"  {f:<28}  {e91:>22}  {bb84:>22}")

    print()
    print_sep("Key Takeaway")
    print(f"""
  E91 replaces Alice's active qubit preparation with a passive entanglement check.
  The CHSH inequality is the eavesdrop detector:
    S ≈ 2.828  →  channel is genuinely quantum, no classical spoofing possible
    S ≤ 2.000  →  entanglement destroyed — Eve present — abort session

  This gives E91 a unique property: DEVICE-INDEPENDENT security.
  Even if Alice's and Bob's measurement devices are untrusted (possibly
  compromised), a sufficiently large CHSH violation certifies security.
  Classical protocols (RSA, AES key exchange) have no equivalent guarantee.
""")
    print_sep()


if __name__ == "__main__":
    main()
