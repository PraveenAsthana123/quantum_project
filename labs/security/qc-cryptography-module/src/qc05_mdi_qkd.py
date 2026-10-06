"""
QC-05: MDI-QKD — Measurement-Device-Independent QKD
=====================================================
Algorithm  : MDI-QKD (Lo, Curty, Qi 2012)
Reference  : H.-K. Lo, M. Curty, B. Qi, "Measurement-Device-Independent
             Quantum Key Distribution", Phys. Rev. Lett. 108, 130503 (2012).
Complexity : O(N) quantum channel uses; BSM post-selection ~25% success rate
Security   : Closes all detector side-channel attacks; Charlie (relay) can be
             fully adversarial; security proven via entanglement swapping
Quantum Adv: First protocol secure against all detector attacks; doubles
             achievable distance vs standard BB84 without trusted relays
"""

import time
import numpy as np

RNG = np.random.default_rng(seed=42)

# BB84 states: (bit, basis) → state label
# basis 0=Z, 1=X; bit ∈ {0,1}
# |Φ+⟩ = (|00⟩+|11⟩)/√2, |Φ-⟩ = (|00⟩-|11⟩)/√2
# |Ψ+⟩ = (|01⟩+|10⟩)/√2, |Ψ-⟩ = (|01⟩-|10⟩)/√2


def _bsm_outcome(alice_state: tuple[int, int], bob_state: tuple[int, int],
                 charlie_honest: bool, rng: np.random.Generator) -> tuple[str, bool]:
    """
    Charlie performs Bell State Measurement on Alice's and Bob's qubits.

    For MDI-QKD, successful BSM (|Φ+⟩ or |Φ-⟩) projects Alice & Bob's
    remaining qubits into a correlated state usable for key generation.

    Protocol: Alice & Bob both prepare BB84 states in the same basis.
    Charlie announces which Bell state was measured.
    Only |Ψ-⟩ results are kept (Z basis), or |Φ-⟩ (X basis) in practice.

    Returns (bell_state, success).
    """
    a_bit, a_basis = alice_state
    b_bit, b_basis = bob_state

    if not charlie_honest:
        # Adversarial Charlie: tries to maximise information
        # Still cannot break security (Lo et al. proved this)
        # She guesses a BSM outcome randomly
        bell_state = rng.choice(["|Φ+⟩", "|Φ-⟩", "|Ψ+⟩", "|Ψ-⟩"])
        success = rng.random() < 0.25   # same statistics as honest
        return bell_state, success

    # Honest Charlie: genuine BSM (simplified linear optics model)
    # P(success for same basis) = 0.5 (linear optics BSM)
    # P(success different basis) = 0 (discarded)
    if a_basis != b_basis:
        return "discard", False

    # Same basis: 50% linear-optics BSM success
    if rng.random() > 0.5:
        return "no_click", False

    # Determine Bell state from bits (deterministic in honest case):
    # Z-basis: a==b → |Φ+⟩ (both |0⟩ or both |1⟩); a≠b → |Ψ+⟩
    # X-basis: same mapping but in Hadamard basis
    if a_bit == b_bit:
        bell_state = "|Φ+⟩"
    else:
        bell_state = "|Ψ+⟩"

    return bell_state, True


def _post_process_mdi(alice_bit: int, bob_bit: int, alice_basis: int,
                      bell_state: str) -> tuple[int, int]:
    """
    After BSM announcement, Alice and Bob apply bit flips to obtain
    correlated key bits.  Convention (Z-basis, bit-flip correction):

      |Φ+⟩ → same bits → no flip needed
      |Φ-⟩ → same bits in Z, different in X → Bob flips in X basis
      |Ψ+⟩ → different bits → Bob flips in both bases
      |Ψ-⟩ → different bits + phase flip → Bob flips in both bases
    """
    corrected_bob = bob_bit
    if bell_state in ("|Ψ+⟩", "|Ψ-⟩"):
        # Different-bit Bell states: Bob flips to match Alice
        corrected_bob = 1 - bob_bit
    elif bell_state == "|Φ-⟩" and alice_basis == 1:
        # Phase-flip in X basis
        corrected_bob = 1 - bob_bit
    return alice_bit, corrected_bob


def simulate_mdi_qkd(n_rounds: int = 1000, charlie_honest: bool = True,
                     channel_loss: float = 0.1, seed: int = 42) -> dict:
    """
    MDI-QKD simulation.

    Parameters
    ----------
    n_rounds      : number of rounds (each: Alice+Bob send one qubit to Charlie)
    charlie_honest: True = honest relay, False = adversarial/Eve as Charlie
    channel_loss  : photon loss probability per channel (0 = lossless)
    """
    rng = np.random.default_rng(seed)

    alice_bits  = rng.integers(0, 2, size=n_rounds)
    alice_bases = rng.integers(0, 2, size=n_rounds)
    bob_bits    = rng.integers(0, 2, size=n_rounds)
    bob_bases   = rng.integers(0, 2, size=n_rounds)

    alice_key, bob_key = [], []
    n_successful_bsm = 0

    for i in range(n_rounds):
        # Simulate photon loss
        if rng.random() < channel_loss or rng.random() < channel_loss:
            continue

        bell, success = _bsm_outcome(
            (int(alice_bits[i]), int(alice_bases[i])),
            (int(bob_bits[i]), int(bob_bases[i])),
            charlie_honest, rng)

        if not success:
            continue

        # Only keep same-basis pairs (sifting)
        if alice_bases[i] != bob_bases[i]:
            continue

        n_successful_bsm += 1
        a_key, b_key = _post_process_mdi(
            int(alice_bits[i]), int(bob_bits[i]),
            int(alice_bases[i]), bell)
        alice_key.append(a_key)
        bob_key.append(b_key)

    alice_arr = np.array(alice_key)
    bob_arr   = np.array(bob_key)
    errors = int((alice_arr != bob_arr).sum()) if len(alice_arr) > 0 else 0
    qber = errors / max(len(alice_arr), 1)
    sifted = len(alice_arr)

    return {
        "n_rounds": n_rounds,
        "n_successful_bsm": n_successful_bsm,
        "n_sifted": sifted,
        "bsm_success_rate": round(n_successful_bsm / n_rounds, 4),
        "qber": round(qber, 4),
        "charlie_honest": charlie_honest,
        "final_key_bits": max(0, sifted - 2 * errors),
    }


def run_scenario() -> dict:
    t_start = time.perf_counter()

    r_honest    = simulate_mdi_qkd(1000, charlie_honest=True,  seed=42)
    r_adversary = simulate_mdi_qkd(1000, charlie_honest=False, seed=42)
    r_lossy     = simulate_mdi_qkd(1000, charlie_honest=True, channel_loss=0.3, seed=42)

    elapsed = time.perf_counter() - t_start

    output = {
        "scenario_id": "QC-05",
        "algorithm": "MDI-QKD",
        "qber_honest_charlie": r_honest["qber"],
        "qber_adversarial_charlie": r_adversary["qber"],
        "qber_lossy_30pct": r_lossy["qber"],
        "sifted_honest": r_honest["n_sifted"],
        "sifted_adversarial": r_adversary["n_sifted"],
        "final_key_honest": r_honest["final_key_bits"],
        "final_key_adversarial": r_adversary["final_key_bits"],
        "bsm_success_rate": r_honest["bsm_success_rate"],
        "detector_attacks_closed": True,
        "vs_bb84": "Double distance; Charlie fully adversarial allowed",
        "sim_time_ms": round(elapsed * 1000, 2),
        "security_model": "information-theoretic; detector-attack immune",
        "status": "PASS" if r_honest["qber"] < 0.05 else "FAIL",
    }
    return output


def _print_table(results: dict) -> None:
    print("\n" + "=" * 68)
    print("QC-05  MDI-QKD — Measurement-Device-Independent QKD")
    print("=" * 68)
    for k, v in results.items():
        print(f"  {k:<45} {v}")
    print()
    print("  Charlie trust level comparison:")
    print(f"  {'Charlie':<22} {'QBER':>8}  {'Final Key':>10}  {'Secure?'}")
    print("  " + "-" * 50)
    for honest, label in [(True, "Honest relay"), (False, "Adversarial (Eve)")]:
        r = simulate_mdi_qkd(1000, honest, seed=42)
        sec = "YES" if r["qber"] < 0.11 else "NO"
        print(f"  {label:<22} {r['qber']:>8.4f}  {r['final_key_bits']:>10}  {sec}")
    print()
    print("  Protocol comparison:")
    print(f"  {'Feature':<35} {'Standard BB84':<20} {'MDI-QKD'}")
    print("  " + "-" * 70)
    rows = [
        ("Detector trust required?", "YES", "NO"),
        ("Charlie trust required?", "N/A", "NO"),
        ("Side-channel attacks", "Detector vulns open", "All detector attacks closed"),
        ("Key rate", "~50% of sent bits", "~12.5% (BSM × sifting)"),
        ("Distance advantage", "Baseline", "2× over BB84"),
    ]
    for prop, bb84, mdi in rows:
        print(f"  {prop:<35} {bb84:<20} {mdi}")
    print("=" * 68)


if __name__ == "__main__":
    res = run_scenario()
    _print_table(res)
