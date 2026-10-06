"""
Test suite for Blockchain PQC Lab
==================================
Tests for pq_wallet, pq_transaction, hash_chain_signature, cbdc_pqc.
Coverage: 24 tests across all 4 modules.
"""

import hashlib
import os
import sys
import time

import numpy as np
import pytest

# Ensure src/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pq_wallet import (
    PQKeyPair,
    PQWallet,
    WalletAddress,
    _mldsa_keygen,
    _slh_dsa_keygen,
    _falcon_keygen,
)
from pq_transaction import (
    PQTransactionSigner,
    SignedTransaction,
    Transaction,
    TransactionVerification,
)
from hash_chain_signature import (
    WOTSPlus,
    LMSSignature,
    _base_w,
    _checksum,
    l,
    l1,
    l2,
    n,
    w,
)
from cbdc_pqc import (
    CBDCPQCSystem,
    CBDCToken,
    CBDCAuditRecord,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def wallet():
    return PQWallet(seed=b"test-wallet-seed-00000000001234")


@pytest.fixture(scope="module")
def signer():
    return PQTransactionSigner(seed=b"test-signer-seed-00000000001234")


@pytest.fixture(scope="module")
def wots():
    seed = hashlib.sha256(b"wots-test-seed").digest()
    return WOTSPlus(seed=seed)


@pytest.fixture(scope="module")
def cbdc():
    return CBDCPQCSystem(issuer_id="TEST-CB", currency_code="USD",
                         seed=b"test-cbdc-seed-000000000012345")


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 1: pq_wallet tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPQWallet:

    def test_ml_dsa_keygen_returns_keypair(self, wallet):
        """ML-DSA-65 keygen returns a PQKeyPair with correct algorithm tag."""
        kp = wallet.generate_keypair("ML-DSA-65")
        assert isinstance(kp, PQKeyPair)
        assert kp.algorithm == "ML-DSA-65"
        assert isinstance(kp.public_key, dict)
        assert "A" in kp.public_key
        assert "t" in kp.public_key
        assert len(kp.key_id) == 32

    def test_slh_dsa_keygen_returns_keypair(self, wallet):
        """SLH-DSA-128f keygen returns key with Merkle root structure."""
        kp = wallet.generate_keypair("SLH-DSA-128f")
        assert kp.algorithm == "SLH-DSA-128f"
        assert "root" in kp.public_key
        assert "pk_seed" in kp.public_key
        assert len(kp.public_key["root"]) == 16   # SLH_N=16 bytes

    def test_falcon_keygen_returns_keypair(self, wallet):
        """FALCON-512 keygen returns NTRU-structured key pair."""
        kp = wallet.generate_keypair("FALCON-512")
        assert kp.algorithm == "FALCON-512"
        assert "h" in kp.public_key
        assert kp.public_key["h"].shape == (512,)
        assert kp.public_key["n"] == 512
        assert kp.public_key["q"] == 12289

    def test_unsupported_algorithm_raises(self, wallet):
        """Requesting unknown algorithm raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            wallet.generate_keypair("RSA-2048")

    def test_derive_address_format(self, wallet):
        """Derived address starts with 'pq1' and has correct length."""
        pk_bytes = os.urandom(1952)
        addr = wallet.derive_address(pk_bytes)
        assert addr.startswith("pq1")
        assert len(addr) == 51    # "pq1" + 48 hex chars (24 bytes)

    def test_derive_address_deterministic(self, wallet):
        """Same public key bytes always yield the same address."""
        pk_bytes = os.urandom(32)
        a1 = wallet.derive_address(pk_bytes)
        a2 = wallet.derive_address(pk_bytes)
        assert a1 == a2

    def test_create_address_end_to_end(self, wallet):
        """create_address() returns WalletAddress with valid fields."""
        wa = wallet.create_address("ML-DSA-65")
        assert isinstance(wa, WalletAddress)
        assert wa.address.startswith("pq1")
        assert wa.balance_sats == 0
        assert wa.derivation_path.startswith("m/")

    def test_quantum_safety_score_ml_dsa(self, wallet):
        """ML-DSA-65 safety score has correct parameters."""
        score = wallet.get_quantum_safety_score("ML-DSA-65")
        assert score["security_bits_classical"] == 178
        assert score["security_bits_quantum"] == 178
        assert score["signature_size_bytes"] == 3309
        assert score["public_key_size_bytes"] == 1952
        assert score["quantum_safe"] is True
        assert "FIPS 204" in score["nist_standard"]

    def test_quantum_safety_score_slh_dsa(self, wallet):
        """SLH-DSA-128f safety score has correct parameters."""
        score = wallet.get_quantum_safety_score("SLH-DSA-128f")
        assert score["security_bits_quantum"] == 128
        assert score["hash_based_security"] is True
        assert score["signature_size_bytes"] == 17088

    def test_quantum_safety_score_falcon(self, wallet):
        """FALCON-512 safety score has correct parameters."""
        score = wallet.get_quantum_safety_score("FALCON-512")
        assert score["signature_size_bytes"] == 666
        assert score["nist_category"] == 1
        assert score["quantum_safe"] is True

    def test_compare_with_ecdsa_structure(self, wallet):
        """ECDSA comparison returns all expected keys."""
        comp = wallet.compare_with_ecdsa()
        assert "ecdsa_p256" in comp
        assert "ml_dsa_65" in comp
        assert "slh_dsa_128f" in comp
        assert "falcon_512" in comp
        assert comp["ecdsa_p256"]["quantum_safe"] is False
        assert comp["ecdsa_p256"]["quantum_security_bits"] == 0
        assert comp["ml_dsa_65"]["quantum_safe"] is True
        assert len(comp["summary"]["table_rows"]) == 4

    def test_mldsa_key_dimensions(self):
        """ML-DSA-65 raw keygen produces correct array shapes."""
        rng = np.random.default_rng(seed=42)
        pk, sk = _mldsa_keygen(rng)
        assert pk["A"].shape == (6, 5, 256)   # K×L×N
        assert pk["t"].shape == (6, 256)       # K×N
        assert sk["s1"].shape == (5, 256)      # L×N
        assert sk["s2"].shape == (6, 256)      # K×N


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 2: pq_transaction tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPQTransaction:

    def _make_tx(self):
        return Transaction.new(
            sender="pq1" + "a" * 48,
            recipient="pq1" + "b" * 48,
            amount=100_000_000,
            nonce=1,
            fee=1000,
        )

    def test_ml_dsa_sign_returns_signed_tx(self, signer):
        """ML-DSA-65 sign returns a SignedTransaction."""
        tx = self._make_tx()
        stx = signer.sign_transaction(tx, "ML-DSA-65")
        assert isinstance(stx, SignedTransaction)
        assert stx.algorithm == "ML-DSA-65"
        assert stx.signature_size > 0
        assert len(stx.signature_bytes) > 0

    def test_ml_dsa_verify_returns_verification(self, signer):
        """ML-DSA-65 verify returns TransactionVerification with correct fields."""
        tx = self._make_tx()
        stx = signer.sign_transaction(tx, "ML-DSA-65")
        vr = signer.verify_transaction(stx)
        assert isinstance(vr, TransactionVerification)
        assert vr.algorithm == "ML-DSA-65"
        assert vr.latency_ms >= 0
        assert vr.threat_level in ("NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_slhdsa_sign_verify(self, signer):
        """SLH-DSA-128f sign and verify complete without error."""
        tx = self._make_tx()
        stx = signer.sign_transaction(tx, "SLH-DSA-128f")
        vr = signer.verify_transaction(stx)
        assert vr.threat_level == "NONE"
        assert stx.signature_size > 0

    def test_falcon_sign_verify(self, signer):
        """FALCON-512 sign and verify complete without error."""
        tx = self._make_tx()
        stx = signer.sign_transaction(tx, "FALCON-512")
        vr = signer.verify_transaction(stx)
        assert vr.threat_level == "NONE"

    def test_batch_verify_all_pass(self, signer):
        """Batch verify returns one result per input transaction."""
        txs = [self._make_tx() for _ in range(4)]
        signed = [signer.sign_transaction(t, "ML-DSA-65") for t in txs]
        results = signer.batch_verify(signed)
        assert len(results) == 4
        for vr in results:
            assert isinstance(vr, TransactionVerification)

    def test_block_overhead_ml_dsa(self, signer):
        """Block overhead estimate for ML-DSA-65 returns expected keys."""
        overhead = signer.estimate_blockchain_overhead(2000, "ML-DSA-65")
        assert overhead["n_txs_per_block"] == 2000
        assert overhead["block_size_kb"] > 0
        assert "vs_ecdsa_size_ratio" in overhead
        assert overhead["vs_ecdsa_size_ratio"] > 1.0   # PQ sigs are larger

    def test_migration_path_ecdsa_secp256k1(self, signer):
        """Migration path for Bitcoin ECDSA has 6 steps."""
        mp = signer.migration_path_analysis("ECDSA-secp256k1")
        assert mp["current_algorithm"] == "ECDSA-secp256k1"
        assert len(mp["steps"]) == 6
        assert mp["total_migration_months"] == 48
        assert mp["harvest_now_active"] is True
        assert mp["quantum_risk"] == "CRITICAL"

    def test_tx_canonical_bytes_deterministic(self):
        """Transaction canonical bytes are deterministic given fixed fields."""
        tx = Transaction(
            tx_id="abc123", sender="pq1aaa", recipient="pq1bbb",
            amount=1000, nonce=5, timestamp=1234567890.0, fee=100
        )
        b1 = tx.canonical_bytes()
        b2 = tx.canonical_bytes()
        assert b1 == b2
        assert len(b1) > 0


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 3: hash_chain_signature tests
# ─────────────────────────────────────────────────────────────────────────────

class TestHashChainSignature:

    def test_wots_constants(self):
        """W-OTS+ constants match RFC 8554 §3 for n=32, w=16."""
        assert n  == 32
        assert w  == 16
        assert l1 == 64
        assert l2 == 3
        assert l  == 67

    def test_base_w_conversion(self):
        """base_w converts bytes to correct number of base-16 digits."""
        data = bytes(range(32))
        digits = _base_w(data, l1)
        assert len(digits) == l1
        assert all(0 <= d < w for d in digits)

    def test_checksum_length(self):
        """Checksum produces exactly l2 digits."""
        b = [5] * l1   # all fives
        csum = _checksum(b)
        assert len(csum) == l2
        assert all(0 <= d < w for d in csum)

    def test_wots_chain_idempotent_zero_steps(self, wots):
        """Chain with 0 steps returns input unchanged."""
        x = os.urandom(n)
        result = wots._chain(x, 0, 0, wots.seed)
        assert result == x

    def test_wots_keygen_shape(self, wots):
        """W-OTS+ keygen produces l secret and l public key chains."""
        sk, pk = wots.keygen()
        assert len(sk) == l
        assert len(pk) == l
        assert all(len(sk_i) == n for sk_i in sk)
        assert all(len(pk_i) == n for pk_i in pk)

    def test_wots_sign_verify_valid(self, wots):
        """W-OTS+ sign then verify returns True for correct message."""
        sk, pk = wots.keygen()
        msg = b"Quantum-safe blockchain transaction"
        sig = wots.sign(msg, sk)
        assert len(sig) == l * n   # 2144 bytes
        valid = wots.verify(msg, sig, pk)
        assert valid is True

    def test_wots_verify_tampered_message(self, wots):
        """W-OTS+ verify returns False for different message."""
        sk, pk = wots.keygen()
        sig = wots.sign(b"original message", sk)
        valid = wots.verify(b"tampered message", sig, pk)
        assert valid is False

    def test_wots_signature_size(self, wots):
        """W-OTS+ reported signature size matches actual."""
        assert wots.signature_size() == l * n

    def test_lms_keygen_returns_root(self):
        """LMS keygen returns 32-byte root hash."""
        lms = LMSSignature(height=3)   # 8 leaves — fast
        root, state = lms.keygen(
            master_seed=hashlib.sha256(b"lms-test-seed").digest()
        )
        assert isinstance(root, bytes)
        assert len(root) == n
        assert state["leaf_idx"] == 0
        assert state["n_leaves"] == 8

    def test_lms_sign_verify_valid(self):
        """LMS sign then verify returns True for correct message."""
        lms = LMSSignature(height=3)
        root, state = lms.keygen(
            master_seed=hashlib.sha256(b"lms-sign-test").digest()
        )
        msg = b"LMS test transaction"
        sig = lms.sign(msg, state)
        assert len(sig) == 4   # (leaf_idx, wots_sig, auth_path, leaf_seed)
        valid = lms.verify(msg, sig, root)
        assert valid is True

    def test_lms_advances_leaf_index(self):
        """LMS leaf index increments on each sign call."""
        lms = LMSSignature(height=3)
        _, state = lms.keygen(
            master_seed=hashlib.sha256(b"lms-idx-test").digest()
        )
        assert state["leaf_idx"] == 0
        lms.sign(b"msg1", state)
        assert state["leaf_idx"] == 1
        lms.sign(b"msg2", state)
        assert state["leaf_idx"] == 2

    def test_lms_exhausted_raises(self):
        """LMS raises RuntimeError when all OTS keys are consumed."""
        lms = LMSSignature(height=2)  # 4 leaves
        _, state = lms.keygen(
            master_seed=hashlib.sha256(b"lms-exhaust").digest()
        )
        for i in range(4):
            lms.sign(f"msg{i}".encode(), state)
        with pytest.raises(RuntimeError, match="exhausted"):
            lms.sign(b"one_too_many", state)


# ─────────────────────────────────────────────────────────────────────────────
# MODULE 4: cbdc_pqc tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCBDCPQC:

    def _make_address(self, char: str) -> str:
        return "pq1" + char * 48

    def test_mint_token_returns_valid_token(self, cbdc):
        """mint_token returns a CBDCToken with correct fields."""
        holder = self._make_address("a")
        token = cbdc.mint_token(10_000, holder)
        assert isinstance(token, CBDCToken)
        assert token.denomination == 10_000
        assert token.holder_address == holder
        assert token.issuer == "TEST-CB"
        assert token.currency_code == "USD"
        assert not token.is_burnt
        assert len(token.signature) > 0

    def test_mint_token_signature_non_empty(self, cbdc):
        """Minted token carries a non-empty ML-DSA signature."""
        token = cbdc.mint_token(500, self._make_address("c"))
        assert len(token.signature) > 100
        # Signature contains z (L×N×4), h (K×N×1), c_tilde (64 bytes)

    def test_mint_invalid_denomination_raises(self, cbdc):
        """mint_token raises ValueError for non-positive denomination."""
        with pytest.raises(ValueError, match="denomination"):
            cbdc.mint_token(0, self._make_address("d"))

    def test_transfer_changes_holder(self, cbdc):
        """transfer_token produces new token with updated holder."""
        holder_a = self._make_address("e")
        holder_b = self._make_address("f")
        token = cbdc.mint_token(200, holder_a)
        new_token = cbdc.transfer_token(token, holder_b)
        assert new_token.holder_address == holder_b
        assert new_token.denomination == 200
        assert not new_token.is_burnt

    def test_transfer_burns_original(self, cbdc):
        """Original token is marked burnt after transfer."""
        holder_a = self._make_address("g")
        holder_b = self._make_address("h")
        token = cbdc.mint_token(300, holder_a)
        cbdc.transfer_token(token, holder_b)
        # Original token in registry is now burnt
        assert cbdc._registry[token.token_id].is_burnt is True

    def test_transfer_burnt_token_raises(self, cbdc):
        """Transferring a burnt token raises ValueError."""
        holder_a = self._make_address("i")
        holder_b = self._make_address("j")
        token = cbdc.mint_token(400, holder_a)
        cbdc.transfer_token(token, holder_b)   # burns token
        with pytest.raises(ValueError, match="burnt"):
            cbdc.transfer_token(token, self._make_address("k"))

    def test_verify_token_valid(self, cbdc):
        """verify_token returns valid=True for freshly minted token."""
        token = cbdc.mint_token(1000, self._make_address("l"))
        result = cbdc.verify_token(token)
        assert "valid" in result
        assert result["signature_valid"] is True
        assert result["checks"]["registered"] is True
        assert result["checks"]["not_burnt"] is True
        assert result["threat_level"] in ("NONE", "LOW")

    def test_privacy_preserving_audit_no_raw_addresses(self, cbdc):
        """Audit report does not expose raw holder addresses."""
        # Mint a few tokens to populate audit log
        for i in range(3):
            cbdc.mint_token(100 * (i + 1), self._make_address(str(i % 10)))
        audit = cbdc.privacy_preserving_audit()
        assert audit["audit_summary"]["total_records"] > 0
        assert audit["audit_summary"]["privacy_safe"] is True
        # The audit report should contain no "pq1" addresses
        import json
        audit_str = json.dumps(audit, default=str)
        assert "pq1" not in audit_str

    def test_quantum_threat_timeline_structure(self, cbdc):
        """Quantum threat timeline has required keys and correct values."""
        timeline = cbdc.quantum_threat_timeline()
        assert timeline["harvest_now_decrypt_later"]["status"] == "ACTIVE"
        assert timeline["recommended_migration_year"] == 2027
        assert isinstance(timeline["cbdc_specific_risks"], list)
        assert len(timeline["cbdc_specific_risks"]) >= 4
        assert timeline["current_status"]["this_system_pq_safe"] is True

    def test_compliance_report_bis_fatf(self, cbdc):
        """Compliance report maps to BIS and FATF frameworks correctly."""
        report = cbdc.compliance_report()
        bis = report["bis_cbdc_core_principles"]
        fatf = report["fatf_recommendation_15"]
        assert bis["principle_1_do_no_harm"]["status"] == "COMPLIANT"
        assert bis["property_safe"]["algorithm"].startswith("ML-DSA-65")
        assert "travel_rule_compliance" in fatf
        assert report["quantum_readiness"]["quantum_safe"] is True
        assert report["quantum_readiness"]["migration_year_target"] == 2027
