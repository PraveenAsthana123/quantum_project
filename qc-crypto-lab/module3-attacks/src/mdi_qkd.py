"""
CUSTOMER DEMO PITCH — Measurement-Device-Independent QKD (MDI-QKD)
===================================================================
MDI-QKD (Lo, Curty & Qi, 2012) eliminates ALL detector side-channel attacks —
including the Trojan Horse attack and blinding attacks — by moving all detectors
to an UNTRUSTED relay node (Charlie) controlled by the adversary.

Protocol:
  1. Alice and Bob independently prepare BB84-like qubits and BOTH send them to Charlie.
  2. Charlie performs a Bell State Measurement (BSM) on the two incoming qubits.
  3. Charlie announces which Bell state he measured (over a public classical channel).
  4. Alice and Bob post-process their records to extract a correlated key.

Why this eliminates detector attacks:
  - Charlie has the detectors — even if Eve IS Charlie, all she can do is
    announce BSM results. She cannot gain information about Alice's or Bob's bits
    without also disturbing Alice-Bob correlations in a detectable way.
  - The security reduces to the SOURCES (Alice and Bob) which remain trusted,
    but decoy state protocols can handle weak-coherent-pulse sources.

Audience: QKD hardware vendors, security architects, interview panels.
Runtime: < 5 seconds.
"""

import numpy as np
import math


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
# MDI-QKD Simulation (classical probabilistic model)
# ---------------------------------------------------------------------------

BELL_STATES = {
    "Phi+": "Φ+  (|00⟩+|11⟩)/√2",
    "Phi-": "Φ-  (|00⟩-|11⟩)/√2",
    "Psi+": "Ψ+  (|01⟩+|10⟩)/√2",
    "Psi-": "Ψ-  (|01⟩-|10⟩)/√2",
}


def charlie_bsm(alice_basis: int, alice_bit: int,
                bob_basis:   int, bob_bit:   int,
                rng: np.random.Generator) -> str:
    """
    Simulate Charlie's Bell State Measurement.
    Returns which Bell state was 'detected' (simplified model).

    In a real optical MDI-QKD implementation:
      - Two photons enter Charlie's beam splitter.
      - Charlie can distinguish Ψ+ and Ψ- with linear optics (50% BSM efficiency).
      - He announces: 'Ψ+' or 'Ψ-' or 'no click'.

    This model: when bases match, Charlie announces a Bell state correlated
    with the XOR of Alice's and Bob's bits. When bases differ, Charlie's
    announcement is uncorrelated → post-processing discards these.
    """
    if alice_basis == bob_basis:
        # Bases match: Charlie can make a meaningful BSM announcement
        xor_bit = alice_bit ^ bob_bit
        # For Z-basis (0): same bits → Phi+, different bits → Phi-
        # For X-basis (1): same bits → Psi+, different bits → Psi-
        if alice_basis == 0:
            state = "Phi+" if xor_bit == 0 else "Phi-"
        else:
            state = "Psi+" if xor_bit == 0 else "Psi-"
    else:
        # Bases differ → Charlie's result is random (sifted out later)
        state = rng.choice(["Phi+", "Phi-", "Psi+", "Psi-"])
    return state


def post_process_mdi(alice_bit: int, alice_basis: int,
                     bob_basis: int, charlie_result: str) -> tuple:
    """
    Bob post-processes his bit using Charlie's announcement.
    For matching bases:
      - Bob applies a Pauli correction based on the Bell state announced.
      - Result: Bob's corrected bit should match Alice's bit.
    """
    if alice_basis != bob_basis:
        return None, None   # discard

    # Correction: for Phi-/Psi- Bob flips his bit
    if charlie_result in ("Phi+", "Psi+"):
        bob_corrected_factor = 0   # no flip
    else:
        bob_corrected_factor = 1   # flip

    return alice_basis, bob_corrected_factor


def simulate_mdi_qkd(n_pulses: int, rng: np.random.Generator,
                     charlie_is_eve: bool = False) -> dict:
    """
    Simulate MDI-QKD protocol.
    charlie_is_eve: if True, Charlie deliberately announces wrong Bell states.
    """
    alice_bits   = rng.integers(0, 2, n_pulses)
    alice_bases  = rng.integers(0, 2, n_pulses)
    bob_bits     = rng.integers(0, 2, n_pulses)
    bob_bases    = rng.integers(0, 2, n_pulses)

    sifted_alice = []
    sifted_bob   = []
    charlie_results = []
    n_clicks     = 0

    for i in range(n_pulses):
        # Charlie performs BSM
        if charlie_is_eve:
            # Malicious Charlie: random announcement → introduces errors
            result = rng.choice(["Phi+", "Phi-", "Psi+", "Psi-"])
        else:
            result = charlie_bsm(
                int(alice_bases[i]), int(alice_bits[i]),
                int(bob_bases[i]),   int(bob_bits[i]),  rng)

        # Charlie announces result (even if Eve, he announces)
        # Alice and Bob sift: keep only matching-basis pulses
        if alice_bases[i] == bob_bases[i]:
            n_clicks += 1
            charlie_results.append(result)
            # Bob corrects his bit based on Charlie's announcement
            flip = 1 if result in ("Phi-", "Psi-") else 0
            bob_corrected = int(bob_bits[i]) ^ flip
            sifted_alice.append(int(alice_bits[i]))
            sifted_bob.append(bob_corrected)

    n_sifted = len(sifted_alice)
    errors   = sum(a != b for a, b in zip(sifted_alice, sifted_bob))
    qber     = errors / n_sifted if n_sifted else 0.0

    return {
        "n_pulses":      n_pulses,
        "n_sifted":      n_sifted,
        "errors":        errors,
        "qber":          qber,
        "sifted_alice":  sifted_alice[:12],
        "sifted_bob":    sifted_bob[:12],
        "charlie_results": charlie_results[:12],
    }


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    rng = np.random.default_rng(42)
    N   = 2000

    print_sep("MDI-QKD — MEASUREMENT-DEVICE-INDEPENDENT QKD")
    print("Purpose: Show how MDI-QKD eliminates detector side-channel attacks\n")

    # Protocol steps
    print_sep("Protocol Overview")
    print("""
  Step 1: Alice and Bob independently prepare qubits.
            Alice: bit=0,1 in Z or X basis  →  |0⟩, |1⟩, |+⟩, |-⟩
            Bob:   bit=0,1 in Z or X basis  →  same set

  Step 2: Both send qubits to CHARLIE (untrusted relay).

  Step 3: Charlie performs Bell State Measurement (BSM) on the 2 incoming photons.
            Charlie announces: Φ+, Φ-, Ψ+, Ψ- (or no-click).
            BSM efficiency ≈ 50% with linear optics.

  Step 4: Alice and Bob keep only cases where they chose the same basis.
            Bob applies a Pauli correction based on Charlie's announcement.

  Step 5: Standard QKD post-processing: sifting → QBER estimation → EC → PA.
""")

    # Scenario 1: Honest Charlie
    print_sep("Scenario 1: Honest Charlie")
    r1 = simulate_mdi_qkd(N, rng, charlie_is_eve=False)
    print(f"  Pulses sent by Alice and Bob: {r1['n_pulses']:5d} each")
    print(f"  Sifted pairs (same basis):    {r1['n_sifted']:5d}  (~50%)")
    print(f"  Errors:                       {r1['errors']:5d}")
    print(f"  QBER:                         {r1['qber']*100:.2f}%")
    print(f"  Verdict:                      {'SECURE ✓' if r1['qber'] < 0.11 else 'ABORT'}")
    print()

    # First 12 sifted bits detail
    print("  First 12 sifted results (Alice | Charlie BSM | Bob corrected):")
    print(f"  {'#':>4}  {'Alice':>6}  {'Charlie BSM':>12}  {'Bob':>6}  {'Match?':>7}")
    print(f"  {'-'*4}  {'-'*6}  {'-'*12}  {'-'*6}  {'-'*7}")
    for i in range(min(12, len(r1["sifted_alice"]))):
        a = r1["sifted_alice"][i]
        b = r1["sifted_bob"][i]
        cr = r1["charlie_results"][i] if i < len(r1["charlie_results"]) else "?"
        print(f"  {i:>4}  {a:>6}  {cr:>12}  {b:>6}  {'✓' if a==b else '✗':>7}")
    print()

    # Scenario 2: Malicious Charlie (detector attack attempt)
    print_sep("Scenario 2: Malicious Charlie (attempts to disrupt/inject)")
    rng2 = np.random.default_rng(77)
    r2 = simulate_mdi_qkd(N, rng2, charlie_is_eve=True)
    print(f"  Charlie announces RANDOM Bell states (active attack).")
    print(f"  Sifted pairs:  {r2['n_sifted']:5d}")
    print(f"  Errors:        {r2['errors']:5d}")
    print(f"  QBER:          {r2['qber']*100:.2f}%  (expected: ~50% with random BSM)")
    verdict2 = "MALICIOUS CHARLIE DETECTED — ABORT ✗" if r2['qber'] > 0.11 else "Pass"
    print(f"  Verdict:       {verdict2}")
    print()

    # Comparison: MDI-QKD vs BB84 vs DI-QKD
    print_sep("MDI-QKD vs BB84 vs DI-QKD Security Comparison")
    rows = [
        ("Trusted source needed",  "Alice+Bob", "Alice",   "No (weakly)"),
        ("Trusted detector needed","No (Charlie can be Eve)", "Yes (Bob's)", "No"),
        ("Detector attacks",       "IMMUNE",    "Vulnerable","IMMUNE"),
        ("Trojan Horse attack",    "Not applicable to detectors", "Vulnerable", "Not applicable"),
        ("Key rate (vs BB84)",     "~1/2× (BSM 50% eff.)", "Baseline", "Much lower"),
        ("Implementation complexity", "Higher", "Baseline", "Very high"),
        ("Requires entanglement",  "No",        "No",       "Yes"),
        ("QBER threshold",         "~11%",      "~11%",     "~7%"),
    ]
    print(f"  {'Property':<35}  {'MDI-QKD':>22}  {'BB84':>12}  {'DI-QKD':>12}")
    print(f"  {'-'*35}  {'-'*22}  {'-'*12}  {'-'*12}")
    for feat, mdi, bb84, di in rows:
        print(f"  {feat:<35}  {mdi:>22}  {bb84:>12}  {di:>12}")

    print()
    print_sep("Why Detector Attacks Become Impossible in MDI-QKD")
    print("""
  In BB84, Bob has detectors. Eve can:
    - Blind Bob's APDs with bright light (Makarov 2010).
    - Inject Trojan Horse probes to read Bob's basis.
    - Time-shift Bob's detection window.
    Each attack reads Bob's measurement device → gains key information.

  In MDI-QKD, CHARLIE has all detectors. Even if Eve controls Charlie:
    - Charlie can only ANNOUNCE BSM results over a public classical channel.
    - Any deviation from honest BSM shows up as elevated QBER (just like BB84 Eve).
    - Charlie has NO KNOWLEDGE of Alice's or Bob's individual bits —
      only of the XOR/Bell correlation between them.
    - Alice and Bob's individual bits are revealed only after sifting,
      and the sifted information is insufficient for Eve to reconstruct the key.

  This is a cryptographic proof, not just a claim — see Lo, Curty & Qi (PRL 2012).
""")
    print_sep()


if __name__ == "__main__":
    main()
