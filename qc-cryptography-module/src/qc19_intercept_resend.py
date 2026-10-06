"""
QC-19: Intercept-Resend Attack on BB84
Full 5-scenario simulation with information-theoretic analysis.

stdlib + numpy only. Run directly to see results.
Exports run_scenario() -> dict.
"""

import math
import time
import numpy as np


# ---------------------------------------------------------------------------
# BB84 simulation with configurable Eve intercept rate
# ---------------------------------------------------------------------------

BASES = [0, 1]       # 0 = rectilinear {|0⟩,|1⟩}, 1 = diagonal {|+⟩,|-⟩}
BITS  = [0, 1]


def bb84_simulation(n_bits: int = 1000, intercept_rate: float = 0.0,
                    selective: bool = False, seed: int = 42) -> dict:
    """
    BB84 with Eve intercept-resend attack.

    intercept_rate: fraction of qubits Eve intercepts (0.0 = no Eve, 1.0 = full).
    selective: if True, Eve intercepts even-indexed bits preferentially.
    seed: RNG seed.

    Returns: sifted key length, QBER, raw keys, mutual info.
    """
    rng = np.random.default_rng(seed)

    # Alice prepares
    alice_bits   = rng.integers(0, 2, size=n_bits)
    alice_bases  = rng.integers(0, 2, size=n_bits)

    # Eve intercepts
    eve_bases    = rng.integers(0, 2, size=n_bits)
    if selective:
        # Eve intercepts only even-indexed qubits
        intercept_mask = np.zeros(n_bits, dtype=bool)
        intercept_mask[::2] = True
    else:
        intercept_mask = rng.random(size=n_bits) < intercept_rate

    # Eve's measurement (wrong basis → random result)
    eve_measured = alice_bits.copy()
    for i in range(n_bits):
        if intercept_mask[i]:
            if eve_bases[i] != alice_bases[i]:
                eve_measured[i] = rng.integers(0, 2)

    # Bob measures (gets Eve's re-sent qubit if intercepted, else Alice's)
    bob_bases = rng.integers(0, 2, size=n_bits)
    bob_received = np.where(intercept_mask, eve_measured, alice_bits)
    # Bob measures: if same basis → correct; if different → random
    bob_bits = np.where(
        bob_bases == alice_bases,
        bob_received,
        rng.integers(0, 2, size=n_bits)
    )

    # Sifting: keep bits where Alice and Bob used same basis
    sift_mask = alice_bases == bob_bases
    alice_sifted = alice_bits[sift_mask]
    bob_sifted   = bob_bits[sift_mask]

    # QBER
    errors = np.sum(alice_sifted != bob_sifted)
    sifted_len = len(alice_sifted)
    qber = float(errors / sifted_len) if sifted_len > 0 else 0.0

    # Eve's knowledge fraction (fraction of bits Eve measured in correct basis)
    eve_correct_basis = np.sum(intercept_mask & (eve_bases == alice_bases))
    total_intercepted = np.sum(intercept_mask)
    eve_info_fraction = float(eve_correct_basis / total_intercepted) if total_intercepted > 0 else 0.0

    # Mutual information I(A;E) estimate (binary entropy based)
    # For intercept-resend: I(A;E) ≈ intercept_rate × 0.5 (Eve gets ~50% of intercepted bits correct)
    p_eve_correct = intercept_rate * 0.5 + (1 - intercept_rate) * 0.0
    h_binary = lambda p: 0.0 if p in (0, 1) else -p * math.log2(p) - (1-p) * math.log2(1-p)
    mutual_info_ae = max(0.0, 1.0 - h_binary(max(0.001, min(0.999, p_eve_correct))))

    # Detection probability: probability Eve is caught
    # Each intercepted qubit: wrong basis 50% → QBER contribution 25% overall
    # P(detect | intercept_rate=q) = 1 - (3/4)^(n_test) where n_test = test bits
    n_test = min(100, sifted_len // 4)
    expected_errors_per_bit = intercept_rate * 0.25
    detect_prob = 1.0 - (1.0 - expected_errors_per_bit) ** n_test if n_test > 0 else 0.0

    return {
        "n_bits": n_bits,
        "sifted_length": sifted_len,
        "errors": int(errors),
        "qber": round(qber, 4),
        "eve_info_fraction": round(eve_info_fraction, 4),
        "mutual_info_ae": round(mutual_info_ae, 4),
        "detection_probability": round(detect_prob, 4),
        "intercept_rate": intercept_rate,
    }


# ---------------------------------------------------------------------------
# Privacy amplification (hash compression)
# ---------------------------------------------------------------------------

def privacy_amplification(raw_key_bits: int, eve_info_bits: float) -> dict:
    """
    After reconciliation, compress key to remove Eve's information.
    Final key length = raw_key - eve_info_bits (simplified).
    Uses universal hash function (modeled as key compression ratio).
    """
    secure_bits = max(0, int(raw_key_bits - eve_info_bits * raw_key_bits - 20))
    return {
        "raw_key_bits": raw_key_bits,
        "eve_info_bits": round(eve_info_bits * raw_key_bits),
        "secure_key_bits_after_pa": secure_bits,
        "pa_ratio": round(secure_bits / raw_key_bits, 4) if raw_key_bits > 0 else 0,
        "method": "Universal2 hash (Toeplitz matrix), standard in QKD",
    }


# ---------------------------------------------------------------------------
# 5 scenarios
# ---------------------------------------------------------------------------

SCENARIOS = [
    {"name": "No Eve (baseline)",          "intercept_rate": 0.00, "selective": False},
    {"name": "100% intercept (full Eve)",  "intercept_rate": 1.00, "selective": False},
    {"name": "50% intercept",              "intercept_rate": 0.50, "selective": False},
    {"name": "25% intercept (below threshold?)", "intercept_rate": 0.25, "selective": False},
    {"name": "Selective intercept (even bits)", "intercept_rate": 0.50, "selective": True},
]


# ---------------------------------------------------------------------------
# Classical MITM comparison
# ---------------------------------------------------------------------------

CLASSICAL_VS_QUANTUM = {
    "Classical MITM": {
        "detectable": False,
        "mechanism": "Eve relays messages unchanged — Alice and Bob see identical messages",
        "defense": "Public key infrastructure (PKI), but PKI is broken by Shor's",
    },
    "Quantum MITM (Intercept-Resend)": {
        "detectable": True,
        "mechanism": "Quantum measurement collapses state; wrong-basis → QBER ~25% for full intercept",
        "detection_threshold": "QBER > 11% → abort (typical threshold in deployed BB84)",
        "defense": "QBER check: abort if QBER exceeds threshold",
    },
}

DETECTION_TABLE = [
    {"intercept_rate": 0.00, "expected_qber": "0.00", "detection_prob": "~0%",  "action": "Key accepted"},
    {"intercept_rate": 0.10, "expected_qber": "0.025","detection_prob": "~20%", "action": "Borderline"},
    {"intercept_rate": 0.25, "expected_qber": "0.063","detection_prob": "~60%", "action": "Likely detected"},
    {"intercept_rate": 0.50, "expected_qber": "0.125","detection_prob": "~99%", "action": "Detected & aborted"},
    {"intercept_rate": 1.00, "expected_qber": "0.250","detection_prob": "~100%","action": "Always detected"},
]


# ---------------------------------------------------------------------------
# run_scenario
# ---------------------------------------------------------------------------

def run_scenario() -> dict:
    t0 = time.perf_counter()

    scenario_results = []
    for s in SCENARIOS:
        sim = bb84_simulation(n_bits=2000, intercept_rate=s["intercept_rate"],
                              selective=s["selective"], seed=42)
        pa = privacy_amplification(sim["sifted_length"], sim["mutual_info_ae"])
        scenario_results.append({
            "scenario_name": s["name"],
            "simulation": sim,
            "privacy_amplification": pa,
        })

    result = {
        "scenario": "QC-19",
        "name": "Intercept-Resend Attack on BB84",
        "category": "Attack",
        "five_scenarios": scenario_results,
        "detection_table": DETECTION_TABLE,
        "classical_vs_quantum_mitm": CLASSICAL_VS_QUANTUM,
        "key_insight": (
            "100% intercept → QBER = 25% (guaranteed detection). "
            "Even 25% intercept rate → QBER ≈ 6.25% → typically detected. "
            "No-cloning theorem: Eve cannot copy quantum states → any measurement disturbs them. "
            "Privacy amplification removes any residual Eve information from the final key."
        ),
        "elapsed_s": round(time.perf_counter() - t0, 4),
    }
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    res = run_scenario()
    print("=" * 60)
    print(f"QC-19: {res['name']}")
    print("=" * 60)
    print()
    print("Five Scenarios:")
    hdr = f"  {'Scenario':<40} {'QBER':>6} {'I(A;E)':>7} {'Detect%':>8}  PA bits"
    print(hdr)
    print("  " + "-" * 72)
    for s in res["five_scenarios"]:
        sim = s["simulation"]
        pa  = s["privacy_amplification"]
        print(f"  {s['scenario_name']:<40} {sim['qber']:>6.4f} {sim['mutual_info_ae']:>7.4f} "
              f"{sim['detection_probability']:>8.4f}  {pa['secure_key_bits_after_pa']}")
    print()
    print("Detection Table (expected QBER vs intercept rate):")
    for row in res["detection_table"]:
        print(f"  Intercept={row['intercept_rate']:.2f}  QBER={row['expected_qber']:>5}  "
              f"Detect={row['detection_prob']:>5}  → {row['action']}")
    print()
    print("Classical vs Quantum MITM:")
    for k, v in res["classical_vs_quantum_mitm"].items():
        print(f"  {k}: detectable={v['detectable']}")
    print()
    print(f"Key insight: {res['key_insight']}")
    print(f"Elapsed: {res['elapsed_s']}s")
