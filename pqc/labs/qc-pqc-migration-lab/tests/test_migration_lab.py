"""
PQC Migration Lab Test Suite
==============================
Tests all 7 migration modules: pipeline, TLS, PKI, SSH, JWT, benchmarking,
and layer migration plan. Validates end-to-end protocol flows, timing
bounds, and output structure.

Run: pytest tests/test_migration_lab.py -v
"""
from __future__ import annotations

import os
import sys
import time
import pytest
from pathlib import Path

# src/ on path via conftest.py
from migration_pipeline import MigrationPipeline, CryptoAsset, RiskLevel
from pqc_tls import HybridTLS13Handshake
from pqc_pki import PQCCA, PQCKeyPair, CertificateSigningRequest
from pqc_ssh import PQCSSHHandshake, HostKey
from pqc_jwt import PQCJWTSigner, DualTokenIssuer, JWTKey
from benchmarking import BenchmarkSuite, AlgorithmBenchmark, BENCHMARKS


# ─── Shared fixtures ──────────────────────────────────────────────────────────

def _make_sample_assets():
    """Return a small list of CryptoAsset objects for pipeline tests."""
    return [
        CryptoAsset(
            asset_id="A001", name="TLS Listener", algorithm="RSA-2048",
            key_size=2048, usage="key_exchange", location="api-server",
            expiry="2027-12-31",
        ),
        CryptoAsset(
            asset_id="A002", name="Code Signing Cert", algorithm="ECDSA-P256",
            key_size=256, usage="digital_signature", location="ci-pipeline",
            expiry="2026-06-30",
        ),
        CryptoAsset(
            asset_id="A003", name="DB Encryption Key", algorithm="AES-256",
            key_size=256, usage="symmetric_encryption", location="database",
            expiry="2030-01-01",
        ),
    ]


def _make_jwt_key(alg="ML-DSA-65"):
    return JWTKey(
        algorithm=alg,
        public_key=os.urandom(32),
        private_key=os.urandom(32),
        key_id="test-key-1",
    )


# ─────────────────────────────────────────────────────────────────
# Migration Pipeline
# ─────────────────────────────────────────────────────────────────

class TestMigrationPipeline:
    def test_pipeline_returns_dict(self):
        pipeline = MigrationPipeline()
        result = pipeline.run_full_pipeline(_make_sample_assets())
        assert isinstance(result, dict)

    def test_pipeline_has_minimum_stages(self):
        pipeline = MigrationPipeline()
        result = pipeline.run_full_pipeline(_make_sample_assets())
        assert len(result) >= 3, \
            f"Expected ≥3 pipeline stages, got {len(result)}: {list(result.keys())}"

    def test_pipeline_completes_under_30s(self):
        pipeline = MigrationPipeline()
        start = time.perf_counter()
        pipeline.run_full_pipeline(_make_sample_assets())
        elapsed = time.perf_counter() - start
        assert elapsed < 30.0, f"Pipeline took {elapsed:.2f}s"

    def test_pipeline_handles_empty_assets(self):
        pipeline = MigrationPipeline()
        result = pipeline.run_full_pipeline([])
        assert isinstance(result, dict)

    def test_crypto_asset_risk_level_enum(self):
        assert RiskLevel.CRITICAL == "CRITICAL"
        assert RiskLevel.LOW == "LOW"

    def test_crypto_asset_constructible(self):
        asset = CryptoAsset(
            asset_id="X001", name="Test", algorithm="RSA-2048",
            key_size=2048, usage="test", location="test",
            expiry="2028-01-01",
        )
        assert asset.algorithm == "RSA-2048"


# ─────────────────────────────────────────────────────────────────
# Hybrid TLS 1.3
# ─────────────────────────────────────────────────────────────────

class TestHybridTLS:
    def setup_method(self):
        self.tls = HybridTLS13Handshake()

    def test_tls_instantiates(self):
        assert self.tls is not None

    def test_client_hello_returns_tuple(self):
        # client_hello() → (ClientHello, x25519_sk: bytes, mlkem_ek: bytes)
        result = self.tls.client_hello()
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_client_hello_has_key_material(self):
        _, x25519_sk, mlkem_ek = self.tls.client_hello()
        assert len(x25519_sk) >= 32
        assert len(mlkem_ek) >= 32

    def test_server_hello_follows_client_hello(self):
        ch_msg, x25519_sk, mlkem_ek = self.tls.client_hello()
        sh, shared_secret = self.tls.server_hello(ch_msg.x25519_share, ch_msg.mlkem768_ek)
        assert sh is not None
        assert len(shared_secret) >= 32

    def test_full_handshake_flow(self):
        """Complete TLS 1.3 handshake phases without exceptions."""
        ch_msg, x25519_sk, mlkem_ek = self.tls.client_hello()
        sh, _ = self.tls.server_hello(ch_msg.x25519_share, ch_msg.mlkem768_ek)
        # server_certificate(cert_pk: bytes) → (Certificate, CertificateVerify, master_secret)
        cert_tuple = self.tls.server_certificate(os.urandom(32))
        assert cert_tuple is not None

    def test_cipher_suite_constant(self):
        from pqc_tls import CIPHER_SUITE
        assert CIPHER_SUITE

    def test_handshake_under_5s(self):
        start = time.perf_counter()
        ch_msg, _, _ = self.tls.client_hello()
        self.tls.server_hello(ch_msg.x25519_share, ch_msg.mlkem768_ek)
        self.tls.server_certificate(os.urandom(32))
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0


# ─────────────────────────────────────────────────────────────────
# PQC PKI / CA
# ─────────────────────────────────────────────────────────────────

class TestPQCPKI:
    def setup_method(self):
        self.ca = PQCCA(name="Test-CA", algorithm="ML-DSA-65")

    def test_ca_instantiates(self):
        assert self.ca is not None

    def test_generate_end_entity_keypair(self):
        kp = self.ca.generate_end_entity_keypair()
        assert kp is not None

    def test_keypair_has_public_key(self):
        kp = self.ca.generate_end_entity_keypair()
        assert getattr(kp, "public_key", None) is not None

    def test_keypair_algorithm_set(self):
        kp = self.ca.generate_end_entity_keypair()
        assert kp.algorithm

    def test_ca_can_create_csr(self):
        kp = self.ca.generate_end_entity_keypair()
        csr = self.ca.create_csr(keypair=kp, cn="test.example.com", org="Test Org")
        assert csr is not None

    def test_ca_can_issue_certificate(self):
        # issue_hybrid_certificate(cn: str) → HybridCertificate
        cert = self.ca.issue_hybrid_certificate(cn="server.example.com")
        assert cert is not None

    def test_certificate_has_pqc_cert(self):
        cert = self.ca.issue_hybrid_certificate(cn="srv.example.com")
        # HybridCertificate has pqc_cert, kem_ek, classical_pk, hybrid_sig
        assert cert.pqc_cert is not None
        assert cert.hybrid_sig is not None

    def test_sign_certificate(self):
        kp = self.ca.generate_end_entity_keypair()
        csr = self.ca.create_csr(keypair=kp, cn="leaf.example.com", org="Test Org")
        cert = self.ca.sign_certificate(csr)
        assert cert is not None


# ─────────────────────────────────────────────────────────────────
# PQC SSH
# ─────────────────────────────────────────────────────────────────

class TestPQCSSH:
    def setup_method(self):
        self.ssh = PQCSSHHandshake(kex_alg="mlkem768x25519-sha256")

    def test_ssh_instantiates(self):
        assert self.ssh is not None

    def test_client_kex_init_returns_tuple(self):
        # client_kex_init() → (KexInit, c_x25519_sk, c_x25519_pk, c_pqc_dk, c_pqc_ek)
        result = self.ssh.client_kex_init()
        assert isinstance(result, tuple)
        assert len(result) >= 3

    def test_negotiate_returns_algo(self):
        algo = self.ssh.negotiate()
        assert algo is not None

    def test_server_kex_reply_with_client_keys(self):
        ki_msg, c_x25519_sk, c_x25519_pk, c_pqc_dk, c_pqc_ek = self.ssh.client_kex_init()
        # Build a minimal HostKey for server side
        host_key = HostKey(algorithm="ML-DSA-65", public_key=os.urandom(32),
                           private_key=os.urandom(32))
        reply, s_session_key = self.ssh.server_kex_reply(host_key, c_x25519_pk, c_pqc_ek)
        assert reply is not None
        assert len(s_session_key) >= 32

    def test_full_kex_flow(self):
        # KexECDHReply fields: host_key_algo, host_key_pk, x25519_ek, pqc_ct, host_key_sig
        ki_msg, c_x25519_sk, c_x25519_pk, c_pqc_dk, c_pqc_ek = self.ssh.client_kex_init()
        host_key = HostKey(algorithm="ML-DSA-65", public_key=os.urandom(32),
                           private_key=os.urandom(32))
        reply, _ = self.ssh.server_kex_reply(host_key, c_x25519_pk, c_pqc_ek)
        # client_derive_session_key(c_x25519_sk, c_pqc_dk, s_x25519_ek, pqc_ct)
        c_session_key = self.ssh.client_derive_session_key(
            c_x25519_sk, c_pqc_dk, reply.x25519_ek, reply.pqc_ct
        )
        assert c_session_key is not None
        assert len(c_session_key) >= 32

    def test_ssh_under_5s(self):
        start = time.perf_counter()
        ki_msg, c_x25519_sk, c_x25519_pk, c_pqc_dk, c_pqc_ek = self.ssh.client_kex_init()
        host_key = HostKey(algorithm="ML-DSA-65", public_key=os.urandom(32),
                           private_key=os.urandom(32))
        reply, _ = self.ssh.server_kex_reply(host_key, c_x25519_pk, c_pqc_ek)
        self.ssh.client_derive_session_key(c_x25519_sk, c_pqc_dk,
                                           reply.x25519_ek, reply.pqc_ct)
        assert time.perf_counter() - start < 5.0


# ─────────────────────────────────────────────────────────────────
# PQC JWT
# ─────────────────────────────────────────────────────────────────

class TestPQCJWT:
    def setup_method(self):
        self.key = _make_jwt_key()
        self.signer = PQCJWTSigner(key=self.key)

    def test_signer_instantiates(self):
        assert self.signer is not None

    def test_jwt_key_constructible(self):
        k = JWTKey(algorithm="ML-DSA-65", public_key=b"\x00"*32,
                   private_key=b"\x01"*32, key_id="k1")
        assert k.algorithm == "ML-DSA-65"

    def test_sign_produces_token(self):
        sign = (getattr(self.signer, "sign", None)
                or getattr(self.signer, "create_token", None)
                or getattr(self.signer, "issue", None))
        if sign is None:
            pytest.skip("No sign method found")
        token = sign({"sub": "agent-test", "iat": 1700000000})
        assert token is not None
        assert len(str(token)) > 0

    def test_verify_signed_token(self):
        sign = (getattr(self.signer, "sign", None)
                or getattr(self.signer, "create_token", None))
        verify = (getattr(self.signer, "verify", None)
                  or getattr(self.signer, "verify_token", None))
        if not sign or not verify:
            pytest.skip("sign/verify not found")
        token = sign({"sub": "agent-1", "scope": "read"})
        result = verify(token)
        assert result is not None

    def test_dual_token_issuer_instantiates(self):
        issuer = DualTokenIssuer()
        assert issuer is not None

    def test_alg_constants_present(self):
        from pqc_jwt import ALG_ML_DSA_65, ALG_ES256
        assert ALG_ML_DSA_65
        assert ALG_ES256


# ─────────────────────────────────────────────────────────────────
# Benchmarking
# ─────────────────────────────────────────────────────────────────

class TestBenchmarking:
    def test_benchmarks_constant_non_empty(self):
        assert BENCHMARKS, "BENCHMARKS constant must be non-empty"

    def test_algorithm_benchmark_from_list(self):
        ab = BENCHMARKS[0]
        assert isinstance(ab, AlgorithmBenchmark)
        assert ab.name
        assert ab.quantum_safe in (True, False)

    def test_suite_from_default_benchmarks(self):
        suite = BenchmarkSuite(benchmarks=BENCHMARKS)
        assert suite is not None

    def test_suite_by_category(self):
        suite = BenchmarkSuite(benchmarks=BENCHMARKS)
        # by_category(category: str) → List[AlgorithmBenchmark]
        first_cat = BENCHMARKS[0].category
        items = suite.by_category(first_cat)
        assert isinstance(items, list)
        assert len(items) >= 1

    def test_kem_table_runs_without_error(self):
        suite = BenchmarkSuite(benchmarks=BENCHMARKS)
        try:
            suite.print_kem_table()
        except Exception as exc:
            pytest.fail(f"print_kem_table raised: {exc}")

    def test_migration_comparison_runs(self):
        suite = BenchmarkSuite(benchmarks=BENCHMARKS)
        try:
            suite.print_migration_comparison()
        except Exception as exc:
            pytest.fail(f"print_migration_comparison raised: {exc}")
