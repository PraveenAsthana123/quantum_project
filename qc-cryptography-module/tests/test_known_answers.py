"""Known-answer tests (KAT) for crypto implementations.

These tests verify that outputs match expected security properties for fixed inputs.
Function signatures match the real implementations in src/.

QP-20: BB84 QBER threshold, ML-KEM roundtrip, ML-DSA sign/verify/tamper,
       E91 CHSH classical-bound, Grover target-found.
"""
import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# BB84 — QKD QBER threshold
# ---------------------------------------------------------------------------

def test_bb84_qber_below_threshold():
    """BB84 with no eavesdropper must have QBER < 11%."""
    from src.qc01_bb84 import simulate_bb84
    result = simulate_bb84(n_bits=500, eve_fraction=0.0, seed=42)
    assert result["qber"] < 0.11, f"QBER {result['qber']} exceeds 11% threshold"


def test_bb84_eve_detected():
    """BB84 with full eavesdropper must trigger detection (QBER > 11%)."""
    from src.qc01_bb84 import simulate_bb84
    result = simulate_bb84(n_bits=500, eve_fraction=1.0, seed=42)
    assert result["qber"] > 0.11, f"Eve not detected: QBER={result['qber']}"


# ---------------------------------------------------------------------------
# ML-KEM — encap/decap roundtrip
# ---------------------------------------------------------------------------

def test_ml_kem_roundtrip():
    """ML-KEM encap/decap must recover same shared secret."""
    from src.qc09_ml_kem import ml_kem_keygen, ml_kem_encapsulate, ml_kem_decapsulate
    rng = np.random.default_rng(seed=0)
    pk, sk = ml_kem_keygen(rng)
    ct, ss1 = ml_kem_encapsulate(pk, rng)
    ss2 = ml_kem_decapsulate(ct, sk, pk)
    assert ss1 == ss2, "ML-KEM decapsulation failed — shared secrets differ"


# ---------------------------------------------------------------------------
# ML-DSA — sign/verify and tamper rejection
# ---------------------------------------------------------------------------

def test_ml_dsa_sign_verify():
    """ML-DSA sign/verify must succeed on a fixed message."""
    from src.qc10_ml_dsa import ml_dsa_keygen, ml_dsa_sign, ml_dsa_verify
    rng = np.random.default_rng(seed=0)
    pk, sk = ml_dsa_keygen(rng)
    msg = b"test message for signature"
    sig = ml_dsa_sign(sk, msg, rng)
    assert ml_dsa_verify(pk, msg, sig), "ML-DSA signature verification failed"


def test_ml_dsa_tamper_rejected():
    """ML-DSA must reject tampered message."""
    from src.qc10_ml_dsa import ml_dsa_keygen, ml_dsa_sign, ml_dsa_verify
    rng = np.random.default_rng(seed=0)
    pk, sk = ml_dsa_keygen(rng)
    sig = ml_dsa_sign(sk, b"original", rng)
    assert not ml_dsa_verify(pk, b"tampered", sig), "Tampered message incorrectly verified"


# ---------------------------------------------------------------------------
# E91 — CHSH exceeds classical bound
# ---------------------------------------------------------------------------

def test_e91_chsh_exceeds_classical():
    """E91 CHSH value must exceed classical bound of 2.0."""
    from src.qc02_e91 import simulate_e91
    result = simulate_e91(n_pairs=1000, eve_mode="none", seed=42)
    chsh = result["chsh_score_S"]
    assert chsh > 2.0, f"CHSH S={chsh} does not exceed classical bound"


# ---------------------------------------------------------------------------
# Grover's — finds marked target
# ---------------------------------------------------------------------------

def test_grover_finds_target():
    """Grover's algorithm must find the marked element."""
    from src.qc18_grovers_sha import run_scenario
    result = run_scenario()
    demo = result.get("grover_demo_8bit", {})
    found = demo.get("candidate_is_preimage", False)
    assert found, f"Grover did not find target; demo={demo}"
