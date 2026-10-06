"""
Q22 — Quantum Repeaters
entanglement_swapping.py

Simulate a 3-node quantum repeater chain: Alice — Repeater — Bob.
Alice-Repeater share a Bell pair; Repeater-Bob share a Bell pair.
The Repeater performs a Bell State Measurement (BSM) to create
end-to-end Alice-Bob entanglement via entanglement swapping.

Outputs: data/swapping_results.json
"""

import json
import math
import os
import random


# ---------------------------------------------------------------------------
# Physical constants and helpers
# ---------------------------------------------------------------------------

def bell_state_fidelity(f1: float, f2: float) -> float:
    """
    Fidelity of the swapped Bell state given two Werner-state segments.
    Werner state: rho = F|Φ+><Φ+| + (1-F)/4 * I
    After perfect BSM: F_out = F1*F2 + (1-F1)(1-F2)/3
    Reference: Briegel et al., PRL 81, 5932 (1998).
    """
    f_out = f1 * f2 + (1.0 - f1) * (1.0 - f2) / 3.0
    return f_out


def decoherence_factor(t_storage_s: float, t2_s: float) -> float:
    """Exponential dephasing: F -> F * exp(-t/T2)."""
    return math.exp(-t_storage_s / t2_s)


def photon_detection_efficiency(eta_detector: float, eta_fiber: float,
                                 distance_km: float,
                                 fiber_loss_db_per_km: float = 0.2) -> float:
    """Combined detection probability including fiber transmission."""
    fiber_transmission = 10 ** (-fiber_loss_db_per_km * distance_km / 10.0)
    return eta_detector * eta_fiber * fiber_transmission


# ---------------------------------------------------------------------------
# Node model
# ---------------------------------------------------------------------------

class QuantumNode:
    """Minimal quantum memory node."""

    def __init__(self, name: str, memory_t2_us: float = 1000.0):
        self.name = name
        self.t2_s = memory_t2_us * 1e-6  # convert µs → s

    def __repr__(self):
        return f"Node({self.name}, T2={self.t2_s * 1e6:.0f}µs)"


# ---------------------------------------------------------------------------
# Bell-pair source
# ---------------------------------------------------------------------------

class BellPairSource:
    """
    Heralded entanglement source between two adjacent nodes.
    Models probabilistic photon-pair generation and detection.
    """

    def __init__(self, repetition_rate_hz: float = 1e6,
                 photon_pair_prob: float = 0.1,
                 eta_detector: float = 0.85,
                 eta_fiber: float = 0.95):
        self.rep_rate = repetition_rate_hz
        self.p_pair = photon_pair_prob
        self.eta_d = eta_detector
        self.eta_f = eta_fiber

    def link_generation_rate(self, distance_km: float,
                              fiber_loss_db_per_km: float = 0.2) -> float:
        """Expected heralded link-generation rate [Hz]."""
        eta = photon_detection_efficiency(
            self.eta_d, self.eta_f, distance_km, fiber_loss_db_per_km)
        # Both photons must arrive: p_link = p_pair * eta^2
        p_link = self.p_pair * eta ** 2
        return self.rep_rate * p_link

    def initial_fidelity(self, distance_km: float,
                          fiber_loss_db_per_km: float = 0.2) -> float:
        """
        Approximate initial Bell-pair fidelity degraded by multi-photon
        emission (probability ~ p_pair) and small depolarising from fiber.
        Simple model: F = 1 - p_pair/2 - alpha*distance
        """
        alpha = 0.0005  # fidelity loss per km (rough)
        f = 1.0 - self.p_pair / 2.0 - alpha * distance_km
        return max(0.5, f)


# ---------------------------------------------------------------------------
# BSM (Bell State Measurement)
# ---------------------------------------------------------------------------

def bsm_success_probability(eta_bsm: float = 0.5) -> float:
    """
    Linear-optics BSM distinguishes 2 of 4 Bell states → max 50 % success
    with ideal photon indistinguishability. eta_bsm <= 0.5.
    """
    return min(eta_bsm, 0.5)


# ---------------------------------------------------------------------------
# Three-node entanglement swapping simulation
# ---------------------------------------------------------------------------

def simulate_entanglement_swapping(
        segment_length_km: float = 50.0,
        memory_t2_us: float = 1000.0,
        fiber_loss_db_per_km: float = 0.2,
        rep_rate_hz: float = 1e6,
        photon_pair_prob: float = 0.1,
        eta_detector: float = 0.85,
        eta_bsm: float = 0.45,
        n_trials: int = 10_000,
        seed: int = 42) -> dict:
    """
    Monte-Carlo simulation of 3-node entanglement swapping.

    Returns a dict suitable for JSON serialisation.
    """
    random.seed(seed)

    alice = QuantumNode("Alice", memory_t2_us)
    repeater = QuantumNode("Repeater", memory_t2_us)
    bob = QuantumNode("Bob", memory_t2_us)
    nodes = [alice.name, repeater.name, bob.name]

    source = BellPairSource(
        repetition_rate_hz=rep_rate_hz,
        photon_pair_prob=photon_pair_prob,
        eta_detector=eta_detector,
    )

    seg_rate = source.link_generation_rate(segment_length_km, fiber_loss_db_per_km)
    seg_fidelity_0 = source.initial_fidelity(segment_length_km, fiber_loss_db_per_km)
    p_bsm = bsm_success_probability(eta_bsm)

    # Time per trial (one repetition clock cycle)
    t_trial = 1.0 / rep_rate_hz  # s

    successes = 0
    fidelities = []

    # Each "trial" models one complete heralding attempt at the segment rate.
    # We draw waiting times geometrically from the link generation rate.
    # Expected number of attempts to get one link: 1/p_link_per_attempt.
    # For efficient simulation, we directly draw waiting times from the
    # geometric distribution: P(first success at attempt k) = (1-p)^{k-1} * p.

    # To avoid extremely long loops when p is tiny, model the expected
    # wait time analytically and use normal-distributed jitter around it.
    mean_wait_ar = 1.0 / max(seg_rate, 1e-12)  # seconds
    mean_wait_rb = 1.0 / max(seg_rate, 1e-12)

    for _ in range(n_trials):
        # Draw waiting times from exponential distribution (continuous approx)
        # of a geometric distribution with rate = seg_rate.
        t_ar = random.expovariate(max(seg_rate, 1e-12))  # s
        t_rb = random.expovariate(max(seg_rate, 1e-12))  # s

        # The segment that arrives first waits for the other
        t_wait_s = abs(t_ar - t_rb)  # memory holdtime for the faster segment

        f_ar = seg_fidelity_0 * decoherence_factor(t_wait_s, alice.t2_s)
        f_rb = seg_fidelity_0 * decoherence_factor(t_wait_s, repeater.t2_s)

        # BSM at repeater
        if random.random() > p_bsm:
            continue  # BSM failed

        f_e2e = bell_state_fidelity(f_ar, f_rb)
        successes += 1
        fidelities.append(f_e2e)

    # success_prob here = BSM success fraction (both segments always arrive,
    # but BSM may fail). Effective entanglement rate = seg_rate * p_bsm.
    success_prob = successes / n_trials
    mean_fidelity = (sum(fidelities) / len(fidelities)) if fidelities else 0.0
    effective_rate_hz = seg_rate * p_bsm  # analytical rate estimate

    result = {
        "nodes": nodes,
        "segment_length_km": segment_length_km,
        "segment_fidelity": round(seg_fidelity_0, 4),
        "bsm_success_prob": round(p_bsm, 4),
        "end_to_end_fidelity": round(mean_fidelity, 4),
        "effective_rate_Hz": round(effective_rate_hz, 2),
        "n_trials": n_trials,
        "successes": successes,
        "seg_generation_rate_Hz": round(seg_rate, 2),
        "memory_t2_us": memory_t2_us,
    }
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Entanglement Swapping Simulation ===")
    results = simulate_entanglement_swapping(
        segment_length_km=50.0,
        memory_t2_us=1000.0,
        rep_rate_hz=1e6,
        n_trials=20_000,
    )

    print(f"Nodes            : {' — '.join(results['nodes'])}")
    print(f"Segment length   : {results['segment_length_km']} km")
    print(f"Segment fidelity : {results['segment_fidelity']:.4f}")
    print(f"BSM success prob : {results['bsm_success_prob']:.4f}")
    print(f"E2E fidelity     : {results['end_to_end_fidelity']:.4f}")
    print(f"Effective rate   : {results['effective_rate_Hz']:.2f} Hz")

    os.makedirs("data", exist_ok=True)
    out_path = "data/swapping_results.json"
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
