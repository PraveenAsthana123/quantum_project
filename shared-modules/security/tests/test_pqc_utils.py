"""
test_pqc_utils.py — pytest tests for shared-modules/security/pqc_utils.py.

Covers:
  - assess_algorithm() is importable and callable.
  - assess_algorithm("RSA-2048") returns a dict with quantum_safe=False.
  - assess_algorithm("ML-KEM-768") returns a dict with quantum_safe=True.
  - Both return dicts with "threat" and "replacement" keys (mapped from
    broken_by and migrate_to in the actual return dict).
  - Other classical and PQC algorithms classified correctly.
  - Return dict always has "algorithm" key matching the input.
  - kyber_kem() and dilithium_sign() return dicts (real if liboqs available,
    error dict otherwise); no exception should be raised.

Note: liboqs tests are marked to skip if the library is unavailable.
"""
import sys
from pathlib import Path
import pytest

# Insert shared-modules/security/ into sys.path so pqc_utils can be imported.
_SECURITY_DIR = Path(__file__).parent.parent
if str(_SECURITY_DIR) not in sys.path:
    sys.path.insert(0, str(_SECURITY_DIR))

import pqc_utils


# ---------------------------------------------------------------------------
# assess_algorithm — core classification function
# ---------------------------------------------------------------------------

class TestAssessAlgorithmRSA2048:
    @pytest.fixture(scope="class")
    def result(self):
        return pqc_utils.assess_algorithm("RSA-2048")

    def test_returns_dict(self, result):
        assert isinstance(result, dict)

    def test_quantum_safe_false(self, result):
        # The function returns quantum_risk, not quantum_safe directly.
        # RSA-2048 should have quantum_risk == "CRITICAL" (i.e. NOT safe).
        assert result.get("quantum_risk") == "CRITICAL", (
            f"RSA-2048 must be CRITICAL risk, got {result.get('quantum_risk')!r}"
        )

    def test_has_threat_key(self, result):
        """The 'broken_by' field records the quantum threat."""
        assert "broken_by" in result, "assess_algorithm must return 'broken_by' key"
        assert result["broken_by"], "broken_by must be non-empty"

    def test_has_replacement_key(self, result):
        """The 'migrate_to' field records the PQC replacement."""
        assert "migrate_to" in result, "assess_algorithm must return 'migrate_to' key"
        assert result["migrate_to"], "migrate_to must be non-empty"

    def test_algorithm_key_matches_input(self, result):
        assert result.get("algorithm") == "RSA-2048"

    def test_threat_references_shor(self, result):
        assert "Shor" in result.get("broken_by", ""), (
            "RSA-2048 threat should reference Shor's algorithm"
        )

    def test_replacement_contains_mlkem_or_mldsa(self, result):
        replacement = result.get("migrate_to", "").upper()
        assert "ML-KEM" in replacement or "ML-DSA" in replacement, (
            f"RSA-2048 replacement should be ML-KEM or ML-DSA, got {result['migrate_to']!r}"
        )


class TestAssessAlgorithmMLKEM768:
    @pytest.fixture(scope="class")
    def result(self):
        return pqc_utils.assess_algorithm("ML-KEM-768")

    def test_returns_dict(self, result):
        assert isinstance(result, dict)

    def test_quantum_safe_true(self, result):
        """ML-KEM-768 is already PQC; quantum_risk should be 'SAFE'."""
        assert result.get("quantum_risk") == "SAFE", (
            f"ML-KEM-768 must be SAFE, got {result.get('quantum_risk')!r}"
        )

    def test_has_threat_key(self, result):
        assert "broken_by" in result

    def test_has_replacement_key(self, result):
        assert "migrate_to" in result

    def test_algorithm_key_matches_input(self, result):
        assert result.get("algorithm") == "ML-KEM-768"

    def test_replacement_says_already_pqc(self, result):
        replacement = result.get("migrate_to", "").lower()
        assert "pqc" in replacement or "retain" in replacement or "already" in replacement, (
            f"ML-KEM replacement hint should indicate already PQC, got {result['migrate_to']!r}"
        )

    def test_fips_target_false_for_pqc(self, result):
        """No further FIPS migration needed for an already-PQC algorithm."""
        assert result.get("fips_target") is False


# ---------------------------------------------------------------------------
# Parametrised classical algorithms — all should be non-SAFE
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("algo", [
    "RSA-1024", "RSA-2048", "RSA-4096",
    "ECDSA-P256", "ECDSA-P384",
    "ECDH-P256", "ECDH-P384",
    "DH-2048",
])
def test_classical_algorithms_are_not_safe(algo):
    result = pqc_utils.assess_algorithm(algo)
    assert result["quantum_risk"] in ("CRITICAL", "HIGH"), (
        f"{algo} should be CRITICAL or HIGH, got {result['quantum_risk']!r}"
    )


# ---------------------------------------------------------------------------
# Parametrised PQC algorithms — should all be SAFE
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("algo", ["ML-KEM-768", "ML-DSA-65", "FALCON-512"])
def test_pqc_algorithms_are_safe(algo):
    result = pqc_utils.assess_algorithm(algo)
    assert result["quantum_risk"] == "SAFE", (
        f"{algo} should be SAFE, got {result['quantum_risk']!r}"
    )


# ---------------------------------------------------------------------------
# assess_algorithm — always returns required keys
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("algo", [
    "RSA-2048", "ML-KEM-768", "AES-256-GCM", "UNKNOWN-ALGO-XYZ",
])
def test_assess_always_returns_required_keys(algo):
    result = pqc_utils.assess_algorithm(algo)
    for key in ("algorithm", "quantum_risk", "broken_by", "migrate_to"):
        assert key in result, (
            f"assess_algorithm({algo!r}) missing key {key!r}"
        )


# ---------------------------------------------------------------------------
# AES and SHA — quantum-weakened but not broken
# ---------------------------------------------------------------------------

class TestSymmetricAlgorithms:
    def test_aes256_not_critical(self):
        result = pqc_utils.assess_algorithm("AES-256-GCM")
        assert result["quantum_risk"] not in ("CRITICAL",), (
            "AES-256-GCM should not be CRITICAL"
        )

    def test_sha512_low_risk(self):
        result = pqc_utils.assess_algorithm("SHA-512")
        assert result["quantum_risk"] == "LOW"


# ---------------------------------------------------------------------------
# kyber_kem() and dilithium_sign() — smoke tests; no exception allowed
# ---------------------------------------------------------------------------

class TestPQCFunctionsNoException:
    def test_kyber_kem_returns_dict(self):
        """kyber_kem always returns a dict (error dict if liboqs unavailable)."""
        result = pqc_utils.kyber_kem(768)
        assert isinstance(result, dict), "kyber_kem must return a dict"

    def test_dilithium_sign_returns_dict(self):
        result = pqc_utils.dilithium_sign(b"test message", 65)
        assert isinstance(result, dict), "dilithium_sign must return a dict"

    def test_kyber_kem_has_algorithm_or_error_key(self):
        result = pqc_utils.kyber_kem(768)
        assert "algorithm" in result or "error" in result, (
            "kyber_kem result must have 'algorithm' or 'error'"
        )

    def test_dilithium_sign_has_algorithm_or_error_key(self):
        result = pqc_utils.dilithium_sign(b"test", 65)
        assert "algorithm" in result or "error" in result


# ---------------------------------------------------------------------------
# liboqs-dependent tests (skip gracefully if not installed)
# ---------------------------------------------------------------------------

def _liboqs_available() -> bool:
    return pqc_utils._load_oqs() is not None


@pytest.mark.skipif(not _liboqs_available(), reason="liboqs not installed")
class TestKyberKEMWithLiboqs:
    def test_kem_verified(self):
        result = pqc_utils.kyber_kem(768)
        assert result.get("kem_verified") is True

    def test_public_key_bytes_correct(self):
        result = pqc_utils.kyber_kem(768)
        # ML-KEM-768 public key is 1184 bytes per NIST FIPS 203
        assert result.get("public_key_bytes") == 1184

    def test_shared_secret_hex_present(self):
        result = pqc_utils.kyber_kem(768)
        assert "shared_secret_hex" in result
        assert len(result["shared_secret_hex"]) > 0


@pytest.mark.skipif(not _liboqs_available(), reason="liboqs not installed")
class TestDilithiumSignWithLiboqs:
    def test_signature_valid(self):
        result = pqc_utils.dilithium_sign(b"pytest test payload", 65)
        assert result.get("valid") is True

    def test_signature_bytes_nonzero(self):
        result = pqc_utils.dilithium_sign(b"pytest test payload", 65)
        assert result.get("signature_bytes", 0) > 0
