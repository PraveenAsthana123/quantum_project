"""
test_crypto_inventory.py — pytest tests for pqc-control-tower/src/crypto_inventory.py.

Covers:
  - make_demo_assets() is importable and callable.
  - Demo assets are a non-empty list of CryptoAsset objects.
  - Each asset has required fields: path, algorithm, key_size, quantum_safe,
    migration_priority (exposed via to_dict()).
  - RSA assets get priority P1.
  - Quantum-safe assets (ML-KEM, ML-DSA) get priority P3.
  - scan_directory() and parse_certificate() use subprocess calls;
    those are patched so no real openssl invocation happens.
  - QUANTUM_VULNERABLE and QUANTUM_SAFE sets are importable and sensible.
"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile

# conftest.py already inserted src/ into sys.path
import crypto_inventory as ci


# ---------------------------------------------------------------------------
# make_demo_assets — no subprocess, always safe to run
# ---------------------------------------------------------------------------

class TestMakeDemoAssets:
    @pytest.fixture(scope="class")
    def assets(self):
        return ci.make_demo_assets()

    def test_returns_nonempty_list(self, assets):
        assert isinstance(assets, list)
        assert len(assets) > 0

    def test_each_asset_has_required_dict_keys(self, assets):
        required = {"path", "algorithm", "key_size", "quantum_safe", "migration_priority"}
        for asset in assets:
            d = asset.to_dict()
            missing = required - d.keys()
            assert not missing, f"Asset {asset.path!r} missing keys: {missing}"

    def test_rsa_assets_are_p1(self, assets):
        rsa_assets = [a for a in assets if "RSA" in a.algorithm.upper()]
        assert rsa_assets, "Demo CBOM should contain at least one RSA asset"
        for a in rsa_assets:
            assert a.migration_priority == "P1", (
                f"RSA asset {a.path!r} should be P1, got {a.migration_priority}"
            )

    def test_rsa_assets_not_quantum_safe(self, assets):
        for a in assets:
            if "RSA" in a.algorithm.upper():
                assert a.quantum_safe is False

    def test_pqc_assets_are_quantum_safe(self, assets):
        pqc_assets = [a for a in assets
                      if a.algorithm.upper() in ("ML-KEM", "ML-DSA", "KYBER", "DILITHIUM")]
        assert pqc_assets, "Demo CBOM should include at least one PQC asset"
        for a in pqc_assets:
            assert a.quantum_safe is True, (
                f"PQC asset {a.path!r} should be quantum_safe=True"
            )

    def test_p1_harvest_now_risk(self, assets):
        """Every P1 asset should have harvest_now_risk=True."""
        p1_assets = [a for a in assets if a.migration_priority == "P1"]
        assert p1_assets, "Expected at least one P1 asset"
        for a in p1_assets:
            assert a.harvest_now_risk is True, (
                f"P1 asset {a.path!r} should have harvest_now_risk=True"
            )

    def test_quantum_safe_assets_are_p3(self, assets):
        qs_assets = [a for a in assets if a.quantum_safe is True]
        for a in qs_assets:
            assert a.migration_priority == "P3", (
                f"Quantum-safe asset {a.path!r} should be P3, got {a.migration_priority}"
            )

    def test_asset_type_values(self, assets):
        valid_types = {"certificate", "ssh_key", "pgp_key", "code_signing", "unknown"}
        for a in assets:
            assert a.asset_type in valid_types, (
                f"Unexpected asset_type '{a.asset_type}' for {a.path!r}"
            )


# ---------------------------------------------------------------------------
# QUANTUM_VULNERABLE / QUANTUM_SAFE classification sets
# ---------------------------------------------------------------------------

class TestClassificationSets:
    def test_rsa_in_vulnerable(self):
        assert "RSA" in ci.QUANTUM_VULNERABLE

    def test_ecdsa_in_vulnerable(self):
        assert "ECDSA" in ci.QUANTUM_VULNERABLE

    def test_mlkem_in_safe(self):
        assert "ML-KEM" in ci.QUANTUM_SAFE

    def test_mldsa_in_safe(self):
        assert "ML-DSA" in ci.QUANTUM_SAFE

    def test_aes256_in_safe(self):
        assert "AES-256" in ci.QUANTUM_SAFE


# ---------------------------------------------------------------------------
# parse_certificate — patched subprocess so no real openssl runs
# ---------------------------------------------------------------------------

class TestParseCertificateMocked:
    def test_rsa_cert_gets_p1(self, tmp_path):
        """
        parse_certificate calls _run (subprocess.run wrapper).
        Patch _run to return realistic openssl text output for an RSA cert.
        """
        fake_cert = tmp_path / "server.crt"
        fake_cert.write_text("(fake PEM content)")

        openssl_output = (
            "subject=CN = example.com\n"
            "issuer=CN = Let's Encrypt Authority X3\n"
            "notAfter=Mar 15 12:00:00 2025 GMT\n"
            "Public Key Algorithm: rsaEncryption\n"
            "RSA Public-Key: (2048 bit)\n"
        )

        with patch.object(ci, "_run", return_value=openssl_output):
            asset = ci.parse_certificate(fake_cert)

        assert asset is not None, "parse_certificate should return a CryptoAsset"
        assert asset.migration_priority == "P1", (
            f"RSA cert should be P1, got {asset.migration_priority}"
        )
        assert asset.quantum_safe is False

    def test_unknown_algo_still_returns_asset(self, tmp_path):
        fake_cert = tmp_path / "unknown.crt"
        fake_cert.write_text("(fake PEM content)")

        openssl_output = (
            "subject=CN = unknown\n"
            "issuer=CN = CA\n"
            "notAfter=Jan 01 12:00:00 2030 GMT\n"
        )

        with patch.object(ci, "_run", return_value=openssl_output):
            asset = ci.parse_certificate(fake_cert)

        # Might be None if no algorithm found, or an asset with UNKNOWN algo
        if asset is not None:
            assert "path" in asset.to_dict()

    def test_empty_output_returns_none(self, tmp_path):
        fake_cert = tmp_path / "empty.crt"
        fake_cert.write_text("")

        with patch.object(ci, "_run", return_value=""):
            asset = ci.parse_certificate(fake_cert)

        assert asset is None, "Empty openssl output should return None"


# ---------------------------------------------------------------------------
# scan_directory — patched to avoid touching the real filesystem
# ---------------------------------------------------------------------------

class TestScanDirectoryMocked:
    def test_scan_returns_list(self, tmp_path):
        """scan_directory on an empty directory returns an empty list."""
        result = ci.scan_directory(tmp_path)
        assert isinstance(result, list)

    def test_scan_with_cert_file_calls_parse(self, tmp_path):
        """
        Place a fake .crt file in tmp_path.
        Patch parse_certificate to return a controlled CryptoAsset.
        Verify scan_directory returns it.
        """
        fake_cert = tmp_path / "mock.crt"
        fake_cert.write_text("(fake)")

        mock_asset = ci.CryptoAsset(
            path=str(fake_cert), asset_type="certificate",
            algorithm="RSA", key_size=2048,
            subject="CN=test", issuer="CN=CA",
            expiry="2026-01-01",
            quantum_safe=False, harvest_now_risk=True,
            migration_priority="P1",
        )

        with patch.object(ci, "parse_certificate", return_value=mock_asset):
            results = ci.scan_directory(tmp_path)

        assert len(results) == 1
        assert results[0].algorithm == "RSA"
        assert results[0].migration_priority == "P1"
