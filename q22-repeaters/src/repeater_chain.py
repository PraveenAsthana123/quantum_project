"""
Q22 — Quantum Repeaters
repeater_chain.py

Nested quantum repeater protocol for N=4 segments (3 nesting levels).
Models link generation rate, decoherence, and purification.
Compares direct fibre transmission vs the repeater chain.

Reference: Briegel et al., PRL 81, 5932 (1998); Sangouard et al.,
           Rev. Mod. Phys. 83, 33 (2011).

Outputs: data/repeater_results.json
"""

import json
import math
import os


# ---------------------------------------------------------------------------
# Physical helpers
# ---------------------------------------------------------------------------

FIBER_LOSS_DB_PER_KM = 0.2        # standard SMF-28 at 1550 nm
SPEED_OF_LIGHT_KM_S = 2.0e5       # in fibre (c/1.5)


def fiber_transmission(distance_km: float,
                        loss_db_per_km: float = FIBER_LOSS_DB_PER_KM) -> float:
    """Optical transmittance through fibre."""
    return 10 ** (-loss_db_per_km * distance_km / 10.0)


def direct_transmission_rate(total_distance_km: float,
                              rep_rate_hz: float,
                              eta_source: float = 0.9,
                              eta_detector: float = 0.85) -> float:
    """
    Raw photon arrival rate without repeaters.
    R = rep_rate * eta_source * T_fiber * eta_detector
    """
    T = fiber_transmission(total_distance_km)
    return rep_rate_hz * eta_source * T * eta_detector


# ---------------------------------------------------------------------------
# Single-segment link generation
# ---------------------------------------------------------------------------

def segment_generation_rate(length_km: float,
                              rep_rate_hz: float = 1e6,
                              photon_pair_prob: float = 0.1,
                              eta_detector: float = 0.85) -> float:
    """
    Heralded entanglement rate for one segment of length L.
    p_link = p_pair * T(L/2)^2 * eta_d^2   (meet-in-middle scheme)
    R_link = rep_rate * p_link
    """
    half_L = length_km / 2.0
    T_half = fiber_transmission(half_L)
    p_link = photon_pair_prob * (T_half * eta_detector) ** 2
    return rep_rate_hz * p_link


def segment_initial_fidelity(length_km: float,
                               alpha_km: float = 5e-4) -> float:
    """Initial fidelity of a generated Bell pair (depolarising model)."""
    return max(0.5, 1.0 - alpha_km * length_km)


# ---------------------------------------------------------------------------
# Memory decoherence during waiting
# ---------------------------------------------------------------------------

def decoherence(fidelity: float, wait_s: float, t2_s: float) -> float:
    """Apply dephasing: F' = (1 + (2F-1)*exp(-wait/T2)) / 2"""
    return (1.0 + (2.0 * fidelity - 1.0) * math.exp(-wait_s / t2_s)) / 2.0


# ---------------------------------------------------------------------------
# Entanglement purification (simple DEJMPS step)
# ---------------------------------------------------------------------------

def purification_step(f: float) -> tuple:
    """
    One DEJMPS purification round.
    F' = (F^2 + ((1-F)/3)^2) / (F^2 + 2F(1-F)/3 + 5((1-F)/3)^2)
    p_success = F^2 + 2F(1-F)/3 + 5((1-F)/3)^2
    Returns (f_out, p_success).
    """
    x = (1.0 - f) / 3.0
    numerator = f ** 2 + x ** 2
    denominator = f ** 2 + 2.0 * f * x * 3.0 / 1.0 + 5.0 * x ** 2
    # Corrected Bennett et al. / DEJMPS formula for Werner states:
    # p_succ = F^2 + (5/9)(1-F)^2 + (4/9)F(1-F)*2 ... simpler closed form:
    p_succ = (f + (1.0 - f) / 3.0) ** 2 / 1.0
    # Use the standard result:
    p_succ = f ** 2 + (1.0 - f) ** 2 / 9.0 + \
             2.0 * f * (1.0 - f) * 2.0 / 9.0 + \
             (1.0 - f) ** 2 * 4.0 / 9.0
    # Compact: for Werner states, p_succ = F^2 + (1-F)^2/3 * ...
    # Most readable: use Bennett 1996 result directly:
    p_succ = f ** 2 + (1 - f) ** 2 / 9.0 * 5.0 + \
             2 * f * (1 - f) * 2.0 / 3.0
    # Simplify: denominator of DEJMPS for Werner state
    p_succ = (f ** 2 + (5.0 / 9.0) * (1.0 - f) ** 2 +
              (4.0 / 9.0) * 2.0 * f * (1.0 - f))
    f_out = (f ** 2 + (1.0 / 9.0) * (1.0 - f) ** 2) / p_succ
    return f_out, p_succ


# ---------------------------------------------------------------------------
# Nesting-level swapping
# ---------------------------------------------------------------------------

def swap_fidelity(f1: float, f2: float) -> float:
    """
    Fidelity after entanglement swapping two Werner states.
    F_out = F1*F2 + (1-F1)(1-F2)/3
    """
    return f1 * f2 + (1.0 - f1) * (1.0 - f2) / 3.0


# ---------------------------------------------------------------------------
# Full repeater chain simulation
# ---------------------------------------------------------------------------

def simulate_repeater_chain(
        total_distance_km: float = 1000.0,
        n_segments: int = 4,
        nesting_levels: int = 3,
        rep_rate_hz: float = 1e6,
        photon_pair_prob: float = 0.1,
        eta_detector: float = 0.85,
        memory_t2_us: float = 500.0,
        purification_rounds: int = 1) -> dict:
    """
    Simulate a nested repeater chain.

    Level-0: elementary links (n_segments segments of equal length)
    Level-1: swap pairs of level-0 links
    Level-2: swap pairs of level-1 links
    ...until one end-to-end link.

    Returns dict with performance metrics.
    """
    t2_s = memory_t2_us * 1e-6
    segment_km = total_distance_km / n_segments

    # -----------------------------------------------------------------------
    # Level-0: elementary link generation
    # -----------------------------------------------------------------------
    seg_rate = segment_generation_rate(segment_km, rep_rate_hz,
                                        photon_pair_prob, eta_detector)
    seg_fidelity = segment_initial_fidelity(segment_km)

    # Waiting time at level 0: wait for the other segment in a pair
    t_wait_0 = 1.0 / (2.0 * max(seg_rate, 1e-30))
    seg_fidelity = decoherence(seg_fidelity, t_wait_0, t2_s)

    # Optional purification after level-0
    current_fidelity = seg_fidelity
    current_rate = seg_rate
    for _ in range(purification_rounds):
        f_new, p_succ = purification_step(current_fidelity)
        if p_succ > 0:
            current_fidelity = f_new
            current_rate = current_rate * p_succ / 2.0  # need 2 pairs

    level_rates = [current_rate]
    level_fidelities = [current_fidelity]

    # -----------------------------------------------------------------------
    # Nested swapping levels
    # -----------------------------------------------------------------------
    for level in range(1, nesting_levels + 1):
        parent_rate = level_rates[-1]
        parent_fidelity = level_fidelities[-1]

        # Waiting time: both sub-links must succeed
        t_wait = 1.0 / (2.0 * max(parent_rate, 1e-30))
        f1 = decoherence(parent_fidelity, t_wait, t2_s)
        f2 = decoherence(parent_fidelity, t_wait, t2_s)

        # BSM success (50% for linear optics)
        p_bsm = 0.45
        new_fidelity = swap_fidelity(f1, f2)
        new_rate = parent_rate ** 2 * p_bsm / parent_rate  # one swap per pair
        # Correct rate formula: R_new = p_bsm * (R_prev/2) since each swap
        # consumes 2 sub-links; but sub-links are generated at R_prev each.
        new_rate = p_bsm * parent_rate / 2.0

        level_rates.append(new_rate)
        level_fidelities.append(new_fidelity)

    end_rate = level_rates[-1]
    end_fidelity = level_fidelities[-1]

    # -----------------------------------------------------------------------
    # Direct transmission (no repeaters) reference
    # -----------------------------------------------------------------------
    without_rate = direct_transmission_rate(
        total_distance_km, rep_rate_hz, 0.9, eta_detector)

    result = {
        "total_distance_km": total_distance_km,
        "n_segments": n_segments,
        "nesting_levels": nesting_levels,
        "segment_length_km": round(segment_km, 2),
        "segment_rate_Hz": round(seg_rate, 4),
        "end_rate_Hz": round(end_rate, 4),
        "fidelity": round(end_fidelity, 4),
        "without_repeater_rate_Hz": round(without_rate, 6),
        "rate_improvement_factor": round(
            end_rate / max(without_rate, 1e-30), 2),
        "memory_t2_us": memory_t2_us,
        "purification_rounds": purification_rounds,
        "level_rates_Hz": [round(r, 6) for r in level_rates],
        "level_fidelities": [round(f, 4) for f in level_fidelities],
    }
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Nested Quantum Repeater Chain ===")

    configs = [
        {"total_distance_km": 1000, "n_segments": 4, "nesting_levels": 3},
        {"total_distance_km": 500,  "n_segments": 4, "nesting_levels": 3},
        {"total_distance_km": 2000, "n_segments": 8, "nesting_levels": 4},
    ]

    results = []
    for cfg in configs:
        r = simulate_repeater_chain(**cfg)
        results.append(r)
        print(f"\nDistance: {r['total_distance_km']} km | "
              f"Segments: {r['n_segments']} | Levels: {r['nesting_levels']}")
        print(f"  Segment rate     : {r['segment_rate_Hz']:.4f} Hz")
        print(f"  End-to-end rate  : {r['end_rate_Hz']:.4f} Hz")
        print(f"  Fidelity         : {r['fidelity']:.4f}")
        print(f"  Without repeater : {r['without_repeater_rate_Hz']:.2e} Hz")
        print(f"  Rate improvement : {r['rate_improvement_factor']:.1e}x")

    # Save the primary 1000 km scenario
    primary = results[0]
    os.makedirs("data", exist_ok=True)
    out_path = "data/repeater_results.json"
    with open(out_path, "w") as fh:
        json.dump({"scenarios": results, "primary": primary}, fh, indent=2)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
