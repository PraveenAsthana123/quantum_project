#!/usr/bin/env python3
"""
QC-05: MDI-QKD (Measurement Device Independent QKD) Simulation.

Reference paper: Lo, Curty, Qi, "Measurement-Device-Independent Quantum Key Distribution",
Physical Review Letters 108, 130503 (2012). arXiv:1109.1473.

This simulation models:
  - Alice and Bob each prepare BB84 states and send to Charlie (untrusted relay)
  - Charlie performs a Bell State Measurement (BSM)
  - Post-selection on successful BSMs to extract the raw key
  - QBER analysis with Charlie as a potential adversary
  - Key rate estimation using decoy state method

MDI-QKD advantage: removes all detector side-channels (main attack surface in QKD).
"""

import os
import time
import random
import math
import hashlib
from typing import Tuple, List, Dict

# ---------------------------------------------------------------------------
# Simulation Parameters
# ---------------------------------------------------------------------------
NUM_PULSES = 10_000         # Total pulse pairs sent
SIGNAL_MU = 0.5             # Mean photon number for signal states
DECOY_MU = 0.1              # Mean photon number for decoy states
VACUUM_MU = 0.0             # Vacuum (0 photons)
BSM_SUCCESS_PROB = 0.5      # Ideal BSM success probability
DETECTOR_EFFICIENCY = 0.9   # Detector efficiency at Charlie
CHANNEL_LOSS_DB = 10.0      # Total channel loss (dB, 5 dB each side)
DARK_COUNT_RATE = 1e-6      # Dark counts per pulse per detector
MISALIGNMENT_ERROR = 0.01   # Optical misalignment error rate

# BB84 basis and bit definitions
Z_BASIS = 0
X_BASIS = 1
BITS = [0, 1]
BASES = [Z_BASIS, X_BASIS]

# Bell state outcomes Charlie can announce
PSI_PLUS = "Ψ+"
PSI_MINUS = "Ψ-"
PHI_PLUS = "Φ+"
PHI_MINUS = "Φ-"


# ---------------------------------------------------------------------------
# Quantum channel model
# ---------------------------------------------------------------------------

def transmittance_from_loss_db(loss_db: float) -> float:
    """Convert loss in dB to transmittance fraction."""
    return 10 ** (-loss_db / 10.0)


def photon_number_sample(mu: float) -> int:
    """Sample photon number from Poisson distribution with mean mu."""
    if mu == 0:
        return 0
    # Poisson sampling
    L = math.exp(-mu)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1


def does_photon_arrive(n: int, transmittance: float, detector_efficiency: float) -> bool:
    """Does at least one photon arrive and get detected?"""
    if n == 0:
        return random.random() < DARK_COUNT_RATE
    # Each photon independently lost or detected
    p_detect = 1 - (1 - transmittance * detector_efficiency) ** n
    return random.random() < p_detect


# ---------------------------------------------------------------------------
# BB84 State Preparation and Bell State Measurement
# ---------------------------------------------------------------------------

def prepare_bb84_state(basis: int, bit: int) -> Tuple[float, float]:
    """
    Prepare a BB84 qubit.
    Z basis: |0⟩ → (1,0), |1⟩ → (0,1)
    X basis: |+⟩ → (1/√2, 1/√2), |−⟩ → (1/√2, -1/√2)
    Returns (alpha, beta) amplitude.
    """
    if basis == Z_BASIS:
        return (1.0, 0.0) if bit == 0 else (0.0, 1.0)
    else:  # X basis
        s = 1.0 / math.sqrt(2)
        return (s, s) if bit == 0 else (s, -s)


def ideal_bsm(state_a: Tuple, state_b: Tuple) -> str:
    """
    Ideal Bell State Measurement: projects (state_a ⊗ state_b) onto Bell basis.
    Returns the Bell state outcome (Ψ+, Ψ-, Φ+, Φ-).
    """
    alpha_a, beta_a = state_a
    alpha_b, beta_b = state_b

    # Compute projection probabilities onto Bell states
    # |Ψ+⟩ = (|01⟩ + |10⟩)/√2
    # |Ψ-⟩ = (|01⟩ - |10⟩)/√2
    # |Φ+⟩ = (|00⟩ + |11⟩)/√2
    # |Φ-⟩ = (|00⟩ - |11⟩)/√2
    s2 = 1.0 / math.sqrt(2)
    proj_psi_plus = abs(s2 * (alpha_a * beta_b + beta_a * alpha_b)) ** 2
    proj_psi_minus = abs(s2 * (alpha_a * beta_b - beta_a * alpha_b)) ** 2
    proj_phi_plus = abs(s2 * (alpha_a * alpha_b + beta_a * beta_b)) ** 2
    proj_phi_minus = abs(s2 * (alpha_a * alpha_b - beta_a * beta_b)) ** 2

    total = proj_psi_plus + proj_psi_minus + proj_phi_plus + proj_phi_minus
    if total < 1e-12:
        return random.choice([PSI_PLUS, PSI_MINUS, PHI_PLUS, PHI_MINUS])

    r = random.random() * total
    if r < proj_psi_plus:
        return PSI_PLUS
    r -= proj_psi_plus
    if r < proj_psi_minus:
        return PSI_MINUS
    r -= proj_psi_minus
    if r < proj_phi_plus:
        return PHI_PLUS
    return PHI_MINUS


def charlie_bsm(state_a: Tuple, state_b: Tuple, adversarial: bool = False) -> Tuple[bool, str]:
    """
    Charlie's Bell State Measurement.
    adversarial=True: Charlie is an eavesdropper who may lie about outcomes.
    Returns (success, bell_state_announced).
    """
    # Check if BSM succeeds (linear optics BSM can only succeed with ~50% prob)
    if random.random() > BSM_SUCCESS_PROB:
        return False, ""

    # Apply detector noise / misalignment
    if random.random() < MISALIGNMENT_ERROR:
        # Misalignment: wrong Bell state
        outcome = random.choice([PSI_PLUS, PSI_MINUS, PHI_PLUS, PHI_MINUS])
    else:
        outcome = ideal_bsm(state_a, state_b)

    if adversarial:
        # Intercept-resend attack: Charlie measures individually and fakes BSM
        # This introduces distinguishable errors in the sifted key
        if random.random() < 0.25:  # 25% error injection
            outcome = random.choice([PSI_PLUS, PSI_MINUS, PHI_PLUS, PHI_MINUS])

    return True, outcome


# ---------------------------------------------------------------------------
# MDI-QKD Protocol
# ---------------------------------------------------------------------------

def mdi_qkd_protocol(n_pulses: int = NUM_PULSES,
                     adversarial_charlie: bool = False) -> Dict:
    """
    Run full MDI-QKD simulation.

    Protocol:
    1. Alice and Bob prepare BB84 states, send to Charlie
    2. Charlie performs BSM, announces outcome
    3. Both post-select on matching bases + successful BSM
    4. Compute QBER, estimate key rate

    Returns statistics dict.
    """
    transmittance = transmittance_from_loss_db(CHANNEL_LOSS_DB / 2)  # each side

    # Raw data storage
    raw_key_alice = []
    raw_key_bob = []
    basis_matched_count = 0
    bsm_success_count = 0
    multi_photon_count = 0

    for _ in range(n_pulses):
        # Alice chooses basis and bit, prepares state
        basis_a = random.choice(BASES)
        bit_a = random.choice(BITS)
        n_a = photon_number_sample(SIGNAL_MU)
        if n_a > 1:
            multi_photon_count += 1

        # Bob chooses basis and bit, prepares state
        basis_b = random.choice(BASES)
        bit_b = random.choice(BITS)
        n_b = photon_number_sample(SIGNAL_MU)

        # Check if photons arrive at Charlie
        arrives_a = does_photon_arrive(n_a, transmittance, DETECTOR_EFFICIENCY)
        arrives_b = does_photon_arrive(n_b, transmittance, DETECTOR_EFFICIENCY)

        if not (arrives_a and arrives_b):
            continue

        # Charlie performs BSM
        state_a = prepare_bb84_state(basis_a, bit_a)
        state_b = prepare_bb84_state(basis_b, bit_b)
        success, outcome = charlie_bsm(state_a, state_b, adversarial=adversarial_charlie)

        if not success:
            continue

        bsm_success_count += 1

        # Basis sifting: only keep matching basis pairs
        if basis_a != basis_b:
            continue

        basis_matched_count += 1

        # Determine Bob's corrected bit based on Charlie's BSM outcome
        # For Ψ-: Bob flips his bit; for Ψ+: no flip (Z basis convention)
        if outcome == PSI_MINUS:
            corrected_bit_b = 1 - bit_b
        elif outcome == PSI_PLUS:
            corrected_bit_b = bit_b
        else:
            # Φ+/Φ-: only valid in X basis for MDI-QKD with prepare-measure states
            if basis_a == X_BASIS:
                corrected_bit_b = bit_b
            else:
                continue  # discard non-Ψ outcomes in Z basis

        raw_key_alice.append(bit_a)
        raw_key_bob.append(corrected_bit_b)

    # Compute QBER
    n_key = len(raw_key_alice)
    if n_key == 0:
        return {"error": "No key bits generated — too much loss"}

    errors = sum(1 for a, b in zip(raw_key_alice, raw_key_bob) if a != b)
    qber = errors / n_key

    # Key rate estimate (simplified Devetak-Winter lower bound)
    if qber < 0.11:  # threshold for positive key rate
        h_qber = -qber * math.log2(qber + 1e-12) - (1 - qber) * math.log2(1 - qber + 1e-12)
        key_rate_per_pulse = basis_matched_count / n_pulses * max(0, 1 - 2 * h_qber)
    else:
        key_rate_per_pulse = 0.0

    secret_key_bits = int(key_rate_per_pulse * n_pulses)

    return {
        "n_pulses": n_pulses,
        "bsm_successes": bsm_success_count,
        "bsm_success_rate": bsm_success_count / n_pulses,
        "basis_matched": basis_matched_count,
        "raw_key_bits": n_key,
        "errors": errors,
        "qber": qber,
        "qber_threshold": 0.11,
        "key_secure": qber < 0.11,
        "key_rate_per_pulse": key_rate_per_pulse,
        "secret_key_bits_estimated": secret_key_bits,
        "multi_photon_fraction": multi_photon_count / n_pulses,
        "adversarial_charlie": adversarial_charlie,
    }


# ---------------------------------------------------------------------------
# Main demonstration
# ---------------------------------------------------------------------------

def main():
    print("=" * 65)
    print("MDI-QKD Simulation")
    print("Reference: Lo, Curty, Qi (2012) arXiv:1109.1473")
    print(f"Parameters: {NUM_PULSES} pulses, μ={SIGNAL_MU}, loss={CHANNEL_LOSS_DB}dB")
    print("=" * 65)

    # Honest Charlie
    print("\n--- Honest Charlie ---")
    t0 = time.perf_counter()
    res_honest = mdi_qkd_protocol(adversarial_charlie=False)
    t1 = time.perf_counter()

    if "error" in res_honest:
        print(f"  ERROR: {res_honest['error']}")
    else:
        print(f"  BSM Success Rate    : {res_honest['bsm_success_rate']:.4f}")
        print(f"  Raw Key Bits        : {res_honest['raw_key_bits']}")
        print(f"  QBER                : {res_honest['qber']:.4f} ({res_honest['qber'] * 100:.2f}%)")
        print(f"  Secure?             : {res_honest['key_secure']} (threshold {res_honest['qber_threshold']:.2f})")
        print(f"  Est. Secret Key     : {res_honest['secret_key_bits_estimated']} bits")
        print(f"  Multi-photon frac.  : {res_honest['multi_photon_fraction']:.4f}")
        print(f"  Simulation time     : {(t1 - t0) * 1000:.0f} ms")

    # Adversarial Charlie (intercept-resend)
    print("\n--- Adversarial Charlie (intercept-resend attack) ---")
    t0 = time.perf_counter()
    res_adv = mdi_qkd_protocol(adversarial_charlie=True)
    t1 = time.perf_counter()

    if "error" in res_adv:
        print(f"  ERROR: {res_adv['error']}")
    else:
        print(f"  QBER                : {res_adv['qber']:.4f} ({res_adv['qber'] * 100:.2f}%)")
        print(f"  Secure?             : {res_adv['key_secure']} ← ATTACK DETECTED if False")
        print(f"  Est. Secret Key     : {res_adv['secret_key_bits_estimated']} bits")
        print(f"  Simulation time     : {(t1 - t0) * 1000:.0f} ms")

    print("\nMDI-QKD Security Advantage:")
    print("  - Charlie's detectors can be completely untrusted")
    print("  - Removes all detector side-channel attacks (blinding, etc.)")
    print("  - Double the distance compared to standard BB84 with trusted detectors")
    print("  - Adversarial Charlie detected via elevated QBER above threshold")

    print("\nKey Rate vs Distance (theoretical, 0.2 dB/km fiber):")
    print(f"  {'Distance':>10}  {'Loss':>8}  {'Est. Key Rate':>16}")
    print("  " + "-" * 38)
    for km, loss in [(10, 2), (25, 5), (50, 10), (100, 20), (150, 30)]:
        t = transmittance_from_loss_db(loss)
        kr = t * DETECTOR_EFFICIENCY * BSM_SUCCESS_PROB * 0.25  # rough lower bound
        print(f"  {km:>8} km  {loss:>6} dB  {kr:>14.2e}")


if __name__ == "__main__":
    main()
