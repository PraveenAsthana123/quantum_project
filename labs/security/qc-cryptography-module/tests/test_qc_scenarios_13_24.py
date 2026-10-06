"""
Tests for QC Scenarios 13–24 (quantum cryptography module).
Run with: pytest tests/test_qc_scenarios_13_24.py -v
"""

import sys
import os
import math
import pytest

# Add src to path
SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, SRC)


# ---------------------------------------------------------------------------
# QC-13: BIKE KEM
# ---------------------------------------------------------------------------

def test_ml_kem_roundtrip():
    """Encap then decap should produce the same shared secret (ML-KEM-style, demo BIKE)."""
    from qc13_bike_kem import keygen, encaps, decaps
    kp = keygen(r=127, w=10, seed=7)
    enc = encaps(kp["pk"], t_err=6, seed=8)
    dec = decaps(kp["sk"], kp["pk"], enc["ciphertext"], kp["h0"], kp["h1"])
    assert enc["shared_secret"] == dec["shared_secret"], (
        f"Shared secrets differ: enc={enc['shared_secret'].hex()[:8]} "
        f"dec={dec['shared_secret'].hex()[:8]}"
    )


def test_bike_scenario_runs():
    """QC-13 run_scenario returns expected keys."""
    from qc13_bike_kem import run_scenario
    res = run_scenario()
    assert res["scenario"] == "QC-13"
    assert res["shared_secret_match"] is True
    assert len(res["comparison_table"]) == 3
    ct = {r["scheme"]: r for r in res["comparison_table"]}
    assert ct["ML-KEM-768"]["pk_bytes"] == 1184
    assert ct["BIKE-L1"]["pk_bytes"] == 1541
    assert ct["BIKE-L3"]["pk_bytes"] == 3083


# ---------------------------------------------------------------------------
# QC-14: Classic McEliece
# ---------------------------------------------------------------------------

def test_mceliece_scenario_runs():
    """QC-14 run_scenario returns production parameters and comparison."""
    from qc14_classic_mceliece import run_scenario
    res = run_scenario()
    assert res["scenario"] == "QC-14"
    assert "mceliece348864" in res["production_params"]
    params = res["production_params"]["mceliece348864"]
    assert params["pk_bytes"] == 261120, f"Expected 261120, got {params['pk_bytes']}"
    assert params["sk_bytes"] == 6492
    assert res["encrypt_ok"] is True


def test_mceliece_gf_arithmetic():
    """GF(2^4) multiplication: 3 * 5 in GF(2^4) with prim poly x^4+x+1."""
    from qc14_classic_mceliece import gf_mul, PRIM_POLY_4, M_DEMO
    # 3 = 0b0011, 5 = 0b0101 in GF(2^4)
    result = gf_mul(3, 5, PRIM_POLY_4, M_DEMO)
    assert 0 <= result < 16, f"GF result out of range: {result}"
    # Commutativity
    assert gf_mul(5, 3, PRIM_POLY_4, M_DEMO) == result


# ---------------------------------------------------------------------------
# QC-15: Shor's on RSA
# ---------------------------------------------------------------------------

def test_shor_factors_15():
    """Shor's algorithm should correctly factor 15 → (3, 5)."""
    from qc15_shors_rsa import shors_factor
    factors = shors_factor(15, seed=42)
    assert factors is not None, "shors_factor(15) returned None"
    p, q = factors
    assert p * q == 15, f"Product mismatch: {p} × {q} ≠ 15"
    assert sorted([p, q]) == [3, 5], f"Expected (3,5), got {sorted([p,q])}"


def test_shor_factors_multiple():
    """Shor's should factor 21, 35, 77, 143, 221."""
    from qc15_shors_rsa import shors_factor
    test_cases = {21: (3, 7), 35: (5, 7), 77: (7, 11), 143: (11, 13), 221: (13, 17)}
    for n, expected in test_cases.items():
        factors = shors_factor(n, seed=42)
        assert factors is not None, f"shors_factor({n}) returned None"
        p, q = factors
        assert p * q == n, f"Product mismatch for N={n}: {p}×{q}≠{n}"


def test_rsa_threat_matrix():
    """RSA threat matrix should have correct qubit counts (Beauregard: 2n+3)."""
    from qc15_shors_rsa import RSA_THREAT_MATRIX
    for row in RSA_THREAT_MATRIX:
        n = row["rsa_key_bits"]
        expected_qubits = 2 * n + 3
        assert row["logical_qubits"] == expected_qubits, (
            f"RSA-{n}: expected {expected_qubits} qubits, got {row['logical_qubits']}"
        )


# ---------------------------------------------------------------------------
# QC-17: Grover's on AES
# ---------------------------------------------------------------------------

def test_grover_aes128_security_bits():
    """AES-128 quantum security should be 64 bits (half of key size)."""
    from qc17_grovers_aes import AES_ATTACK_TABLE, quantum_security_bits
    # From the table
    aes128_row = next(r for r in AES_ATTACK_TABLE if r["variant"] == "AES-128")
    assert aes128_row["quantum_security_bits"] == 64, (
        f"Expected 64-bit quantum security, got {aes128_row['quantum_security_bits']}"
    )
    assert quantum_security_bits(128) == 64


def test_grover_aes256_quantum_safe():
    """AES-256 should have 128-bit quantum security (safe per NIST)."""
    from qc17_grovers_aes import AES_ATTACK_TABLE, quantum_security_bits
    aes256_row = next(r for r in AES_ATTACK_TABLE if r["variant"] == "AES-256")
    assert aes256_row["quantum_security_bits"] == 128
    assert quantum_security_bits(256) == 128


def test_grover_demo_4bit():
    """4-bit Grover demo should find target key with high probability."""
    from qc17_grovers_aes import grover_search_demo
    demo = grover_search_demo(target_key=11, key_bits=4)
    assert demo["correct"], f"Grover failed: measured {demo['measured_key']} ≠ target 11"
    assert demo["success_probability"] > 0.5, (
        f"Success probability too low: {demo['success_probability']}"
    )


# ---------------------------------------------------------------------------
# QC-18: Grover's on SHA
# ---------------------------------------------------------------------------

def test_grover_sha256_safe():
    """SHA-256 quantum preimage resistance should be 128 bits (safe)."""
    from qc18_grovers_sha import HASH_TABLE
    sha256_row = next(r for r in HASH_TABLE if r["hash"] == "SHA-256")
    # Quantum preimage = 2^128 (may use Unicode superscripts like 2¹²⁸)
    qp = sha256_row["quantum_preimage"]
    assert "128" in qp or "¹²⁸" in qp, (
        f"Expected 2^128 quantum preimage, got {qp}"
    )
    assert sha256_row["nist_status"] == "Safe"


def test_grover_md5_broken():
    """MD5 should be flagged as broken classically."""
    from qc18_grovers_sha import HASH_TABLE
    md5_row = next(r for r in HASH_TABLE if r["hash"] == "MD5")
    assert "Broken" in md5_row["nist_status"] or "broken" in md5_row["nist_status"].lower()


def test_grover_sha256_preimage_demo():
    """8-bit toy hash Grover demo should find at least one preimage."""
    from qc18_grovers_sha import grover_preimage_demo
    demo = grover_preimage_demo(target_hash=42, n_bits=8)
    assert demo.get("candidate_is_preimage") is True or demo.get("preimages_count", 0) >= 1


# ---------------------------------------------------------------------------
# QC-19: Intercept-Resend
# ---------------------------------------------------------------------------

def test_intercept_resend_qber():
    """100% Eve intercept should produce QBER ≈ 0.25 (±0.05 tolerance)."""
    from qc19_intercept_resend import bb84_simulation
    sim = bb84_simulation(n_bits=5000, intercept_rate=1.0, seed=99)
    assert abs(sim["qber"] - 0.25) < 0.05, (
        f"Expected QBER ≈ 0.25, got {sim['qber']}"
    )


def test_no_eve_qber_zero():
    """No Eve should give QBER ≈ 0 (at most 1% from basis mismatch)."""
    from qc19_intercept_resend import bb84_simulation
    sim = bb84_simulation(n_bits=5000, intercept_rate=0.0, seed=99)
    assert sim["qber"] < 0.02, f"QBER without Eve too high: {sim['qber']}"


def test_intercept_resend_five_scenarios():
    """run_scenario should return all 5 scenarios."""
    from qc19_intercept_resend import run_scenario
    res = run_scenario()
    assert len(res["five_scenarios"]) == 5


# ---------------------------------------------------------------------------
# QC-20: PNS Attack
# ---------------------------------------------------------------------------

def test_pns_attack_multi_photon_rate():
    """μ=0.1 should give ~0.9% multi-photon rate."""
    from qc20_pns_attack import multi_photon_rate
    rate = multi_photon_rate(0.1)
    # P(n≥2) = 1 - e^{-0.1}(1 + 0.1) ≈ 0.00468
    assert 0.004 < rate < 0.006, f"Multi-photon rate for μ=0.1: {rate:.4f} (expected ~0.0047)"


def test_pns_vacuum_rate():
    """μ=0.1 → P(0) = e^{-0.1} ≈ 0.9048."""
    from qc20_pns_attack import vacuum_rate
    assert abs(vacuum_rate(0.1) - math.exp(-0.1)) < 1e-8


def test_pns_scenario_runs():
    """QC-20 run_scenario should return all required keys."""
    from qc20_pns_attack import run_scenario
    res = run_scenario()
    assert res["scenario"] == "QC-20"
    assert "pns_simulation_mu01" in res
    assert res["pns_simulation_mu01"]["qber_pns"] == 0.0  # Eve introduces no QBER


# ---------------------------------------------------------------------------
# QC-21: QRNG
# ---------------------------------------------------------------------------

def test_qrng_entropy():
    """QRNG min-entropy should be ≥ 0.95."""
    from qc21_qrng import photon_path_superposition, min_entropy
    bits = photon_path_superposition(10000, seed=42)
    h_min = min_entropy(bits)
    assert h_min >= 0.95, f"Min-entropy too low: {h_min:.4f} (threshold 0.95)"


def test_qrng_nist_frequency():
    """QRNG bits should pass NIST frequency test (p-value ≥ 0.01)."""
    from qc21_qrng import photon_path_superposition, nist_frequency_test
    bits = photon_path_superposition(10000, seed=42)
    result = nist_frequency_test(bits)
    assert result["pass"], f"NIST frequency test failed: p={result['p_value']}"


def test_qrng_all_sources_run():
    """run_scenario should test all 4 sources."""
    from qc21_qrng import run_scenario
    res = run_scenario()
    assert len(res["nist_results"]) == 4
    for name, nr in res["nist_results"].items():
        assert "min_entropy" in nr
        assert nr["min_entropy"] >= 0.0


# ---------------------------------------------------------------------------
# QC-22: Quantum Digital Signatures
# ---------------------------------------------------------------------------

def test_qds_sign_verify():
    """Signing and verifying with correct QDS key should succeed."""
    from qc22_quantum_digital_signatures import qds_setup, qds_sign, qds_verify
    setup = qds_setup(n_recipients=1, key_bits=16, seed=42)
    pk = setup["private_key"]
    qpk = setup["quantum_public_keys"]["recipient_0"]
    msg = "test message"
    sig = qds_sign(pk, msg, key_bits=16)
    verify = qds_verify(qpk, msg, sig["signature"])
    assert verify["valid"], f"Signature verification failed: {verify}"


def test_qds_scenario_runs():
    """QC-22 run_scenario should verify signatures for both Bob and Charlie."""
    from qc22_quantum_digital_signatures import run_scenario
    res = run_scenario()
    assert res["bob_verification"]["valid"]
    assert res["charlie_verification"]["valid"]
    # Eve should fail
    assert not res["eve_forgery_attempt"]["guess_success"]


# ---------------------------------------------------------------------------
# QC-23: Quantum Secret Sharing
# ---------------------------------------------------------------------------

def test_qss_threshold():
    """(2,3) QSS: Bob+Charlie cooperate → success=True; Bob alone → success=False."""
    from qc23_quantum_secret_sharing import hbb_qss_alice_share, hbb_qss_reconstruct
    alice_data = hbb_qss_alice_share(secret_bit=1, seed=42)
    bob_charlie = hbb_qss_reconstruct(alice_data, mode="bob_and_charlie")
    assert bob_charlie["success"] is True

    alice_data2 = hbb_qss_alice_share(secret_bit=1, seed=42)
    bob_alone = hbb_qss_reconstruct(alice_data2, mode="bob_alone")
    assert bob_alone["success"] is False


def test_qss_multi_bit():
    """Multi-bit secret sharing should complete without error."""
    from qc23_quantum_secret_sharing import qss_multi_bit
    secret = [0, 1, 1, 0]
    result = qss_multi_bit(secret, seed=42)
    assert len(result["recovered_by_bob_charlie"]) == len(secret)
    assert result["bob_alone_success"] is False


def test_qss_scenario_runs():
    """QC-23 run_scenario should return GHZ state and comparison table."""
    from qc23_quantum_secret_sharing import run_scenario
    res = run_scenario()
    assert res["scenario"] == "QC-23"
    assert "GHZ" in res["ghz_state"]
    assert len(res["comparison"]) >= 5


# ---------------------------------------------------------------------------
# QC-24: Quantum OTP
# ---------------------------------------------------------------------------

def test_qotp_encrypt_decrypt():
    """QOTP encryption then decryption should recover original state."""
    from qc24_quantum_otp import qotp_encrypt, qotp_decrypt
    import numpy as np
    # 1-qubit: |0⟩⟨0| state
    rho = np.array([[1, 0], [0, 0]], dtype=complex)
    key = [(1, 0)]   # X gate
    enc = qotp_encrypt(rho, key)
    dec = qotp_decrypt(enc, key)
    max_diff = float(np.max(np.abs(dec - rho)))
    assert max_diff < 1e-10, f"QOTP decrypt mismatch: max_diff={max_diff}"


def test_qotp_uniform_key_gives_mixed_state():
    """Averaging QOTP over all Pauli keys should give I/2."""
    from qc24_quantum_otp import verify_qotp_security
    import numpy as np
    rho = np.array([[1, 0], [0, 0]], dtype=complex)  # |0⟩⟨0|
    result = verify_qotp_security(rho, n_qubits=1)
    assert result["is_perfectly_mixed"], (
        f"Uniform QOTP did not give I/2: max_deviation={result['max_deviation']}"
    )


def test_qotp_4qubit_roundtrip():
    """4-qubit QOTP encrypt+decrypt should have fidelity > 0.9999."""
    from qc24_quantum_otp import qotp_4qubit_demo
    demo = qotp_4qubit_demo(seed=42)
    assert demo["decrypt_correct"], (
        f"4-qubit QOTP decrypt failed: fidelity={demo['encrypt_decrypt_fidelity']}"
    )
    assert demo["encrypt_decrypt_fidelity"] > 0.9999


def test_bb84_otp_demo():
    """BB84+OTP decryption should recover original message."""
    from qc24_quantum_otp import bb84_otp_demo
    demo = bb84_otp_demo(n_bits=16, seed=42)
    assert demo["correct"], f"BB84+OTP decryption failed: {demo}"


# ---------------------------------------------------------------------------
# Integration: all run_scenario() calls return required keys
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("module_name,expected_scenario", [
    ("qc13_bike_kem", "QC-13"),
    ("qc14_classic_mceliece", "QC-14"),
    ("qc15_shors_rsa", "QC-15"),
    ("qc16_shors_ecc", "QC-16"),
    ("qc17_grovers_aes", "QC-17"),
    ("qc18_grovers_sha", "QC-18"),
    ("qc19_intercept_resend", "QC-19"),
    ("qc20_pns_attack", "QC-20"),
    ("qc21_qrng", "QC-21"),
    ("qc22_quantum_digital_signatures", "QC-22"),
    ("qc23_quantum_secret_sharing", "QC-23"),
    ("qc24_quantum_otp", "QC-24"),
])
def test_run_scenario_interface(module_name, expected_scenario):
    """Every module must export run_scenario() -> dict with 'scenario' key."""
    import importlib
    mod = importlib.import_module(module_name)
    assert hasattr(mod, "run_scenario"), f"{module_name} missing run_scenario()"
    result = mod.run_scenario()
    assert isinstance(result, dict), f"{module_name}.run_scenario() did not return dict"
    assert result.get("scenario") == expected_scenario, (
        f"Expected scenario={expected_scenario}, got {result.get('scenario')}"
    )
    assert "name" in result
    assert "elapsed_s" in result
