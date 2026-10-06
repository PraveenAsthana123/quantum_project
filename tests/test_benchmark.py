"""
Performance Benchmark Suite
==============================
Measures and asserts timing bounds for critical operations.
Reports: algorithm | operation | time_ms | status

All benchmarks use direct in-process calls (no subprocess overhead).
Timing thresholds are conservative: 2-5x the reference NIST/IETF figures
to account for CI/CD environment variance and Python simulation overhead.

Run: pytest tests/test_benchmark.py -v -s
"""
from __future__ import annotations

import sys
import os
import time
import warnings
from typing import List, Tuple

import numpy as np
import pytest

warnings.filterwarnings("ignore")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Add lab src dirs (conftest.py already handles this; belt-and-suspenders)
for _subdir in [
    "qc-cryptography-module/src",
    "qc-pqc-migration-lab/src",
    "qc-finops-lab/src",
]:
    _p = os.path.join(_ROOT, _subdir)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)


# ============================================================================
# Benchmark result collector
# ============================================================================

_RESULTS: List[Tuple[str, str, float, bool]] = []   # (algo, op, time_ms, passed)


def _record(algo: str, op: str, time_ms: float, passed: bool) -> None:
    _RESULTS.append((algo, op, time_ms, passed))


def _bench(fn, *, runs: int = 1):
    """Time a callable, return (result, elapsed_ms). Uses best of `runs` times."""
    best_ms = float("inf")
    result = None
    for _ in range(runs):
        t0 = time.perf_counter()
        result = fn()
        ms = (time.perf_counter() - t0) * 1000
        if ms < best_ms:
            best_ms = ms
    return result, best_ms


# ============================================================================
# ML-KEM-768 benchmarks
# ============================================================================

class TestMlKemBenchmarks:
    """Benchmark ML-KEM-768 keygen, encapsulate, and decapsulate."""

    @pytest.fixture(scope="class")
    def mlkem_keys(self):
        from qc09_ml_kem import ml_kem_keygen
        rng = np.random.default_rng(42)
        pk, sk = ml_kem_keygen(rng)
        return pk, sk, rng

    def test_mlkem_keygen_under_500ms(self):
        """ML-KEM-768 keygen must complete in under 500 ms."""
        from qc09_ml_kem import ml_kem_keygen
        rng = np.random.default_rng(1)
        result, ms = _bench(lambda: ml_kem_keygen(rng))
        passed = ms < 500
        _record("ML-KEM-768", "keygen", ms, passed)
        assert passed, f"ML-KEM-768 keygen {ms:.1f} ms exceeds 500 ms limit"

    def test_mlkem_encap_under_500ms(self, mlkem_keys):
        """ML-KEM-768 encapsulate must complete in under 500 ms."""
        from qc09_ml_kem import ml_kem_encapsulate
        pk, sk, rng = mlkem_keys
        result, ms = _bench(lambda: ml_kem_encapsulate(pk, rng))
        passed = ms < 500
        _record("ML-KEM-768", "encap", ms, passed)
        assert passed, f"ML-KEM-768 encap {ms:.1f} ms exceeds 500 ms limit"

    def test_mlkem_decap_under_500ms(self, mlkem_keys):
        """ML-KEM-768 decapsulate must complete in under 500 ms."""
        from qc09_ml_kem import ml_kem_encapsulate, ml_kem_decapsulate
        pk, sk, rng = mlkem_keys
        ct, _ = ml_kem_encapsulate(pk, rng)
        result, ms = _bench(lambda: ml_kem_decapsulate(ct, sk, pk))
        passed = ms < 500
        _record("ML-KEM-768", "decap", ms, passed)
        assert passed, f"ML-KEM-768 decap {ms:.1f} ms exceeds 500 ms limit"


# ============================================================================
# ML-DSA-65 benchmarks
# ============================================================================

class TestMlDsaBenchmarks:
    """Benchmark ML-DSA-65 keygen, sign, and verify."""

    _MSG = b"Benchmark test message for ML-DSA-65 timing"

    @pytest.fixture(scope="class")
    def mldsa_keys(self):
        from qc10_ml_dsa import ml_dsa_keygen
        rng = np.random.default_rng(42)
        pk, sk = ml_dsa_keygen(rng)
        return pk, sk, rng

    def test_mldsa_keygen_under_1000ms(self):
        """ML-DSA-65 keygen must complete in under 1000 ms."""
        from qc10_ml_dsa import ml_dsa_keygen
        rng = np.random.default_rng(2)
        result, ms = _bench(lambda: ml_dsa_keygen(rng))
        passed = ms < 1000
        _record("ML-DSA-65", "keygen", ms, passed)
        assert passed, f"ML-DSA-65 keygen {ms:.1f} ms exceeds 1000 ms limit"

    def test_mldsa_sign_under_1000ms(self, mldsa_keys):
        """ML-DSA-65 sign must complete in under 1000 ms."""
        from qc10_ml_dsa import ml_dsa_sign
        pk, sk, rng = mldsa_keys
        result, ms = _bench(lambda: ml_dsa_sign(sk, self._MSG, rng=rng))
        passed = ms < 1000
        _record("ML-DSA-65", "sign", ms, passed)
        assert passed, f"ML-DSA-65 sign {ms:.1f} ms exceeds 1000 ms limit"

    def test_mldsa_verify_under_1000ms(self, mldsa_keys):
        """ML-DSA-65 verify must complete in under 1000 ms."""
        from qc10_ml_dsa import ml_dsa_sign, ml_dsa_verify
        pk, sk, rng = mldsa_keys
        sigma = ml_dsa_sign(sk, self._MSG, rng=rng)
        result, ms = _bench(lambda: ml_dsa_verify(pk, self._MSG, sigma))
        passed = ms < 1000
        _record("ML-DSA-65", "verify", ms, passed)
        assert passed, f"ML-DSA-65 verify {ms:.1f} ms exceeds 1000 ms limit"


# ============================================================================
# SLH-DSA / SPHINCS+ (W-OTS+) benchmarks
# ============================================================================

class TestSlhDsaBenchmarks:
    """Benchmark SLH-DSA-128f keygen, sign, and verify."""

    _MSG = b"W-OTS+ / SPHINCS+ benchmark test message"

    @pytest.fixture(scope="class")
    def slhdsa_keys(self):
        from qc11_slh_dsa import slh_dsa_keygen
        rng = np.random.default_rng(42)
        pk, sk = slh_dsa_keygen(rng)
        return pk, sk

    def test_slhdsa_keygen_under_2000ms(self):
        """SLH-DSA-128f keygen must complete in under 2000 ms."""
        from qc11_slh_dsa import slh_dsa_keygen
        rng = np.random.default_rng(5)
        result, ms = _bench(lambda: slh_dsa_keygen(rng))
        passed = ms < 2000
        _record("SLH-DSA-128f", "keygen", ms, passed)
        assert passed, f"SLH-DSA-128f keygen {ms:.1f} ms exceeds 2000 ms limit"

    def test_slhdsa_sign_under_2000ms(self, slhdsa_keys):
        """SLH-DSA-128f sign must complete in under 2000 ms."""
        from qc11_slh_dsa import slh_dsa_sign
        pk, sk = slhdsa_keys
        result, ms = _bench(lambda: slh_dsa_sign(sk, self._MSG))
        passed = ms < 2000
        _record("SLH-DSA-128f", "sign", ms, passed)
        assert passed, f"SLH-DSA-128f sign {ms:.1f} ms exceeds 2000 ms limit"

    def test_slhdsa_verify_under_2000ms(self, slhdsa_keys):
        """SLH-DSA-128f verify must complete in under 2000 ms."""
        from qc11_slh_dsa import slh_dsa_sign, slh_dsa_verify
        pk, sk = slhdsa_keys
        sigma = slh_dsa_sign(sk, self._MSG)
        result, ms = _bench(lambda: slh_dsa_verify(pk, self._MSG, sigma))
        passed = ms < 2000
        _record("SLH-DSA-128f", "verify", ms, passed)
        assert passed, f"SLH-DSA-128f verify {ms:.1f} ms exceeds 2000 ms limit"


# ============================================================================
# QPU cost model benchmark
# ============================================================================

class TestQpuCostBenchmarks:
    """Benchmark QPUCostModeler.compare_providers and QPUScheduler."""

    def test_qpu_compare_providers_under_100ms(self):
        """compare_providers for a single job across all providers must finish under 100 ms."""
        from qpu_cost_model import QPUCostModeler, QPUJob

        modeler = QPUCostModeler(verbose=False)
        # QPUJob fields: circuit_depth, n_qubits, n_shots, gate_count, error_rate
        job = QPUJob(
            circuit_depth=50,
            n_qubits=20,
            n_shots=1_000,
            gate_count=100,
            error_rate=0.001,
        )
        result, ms = _bench(lambda: modeler.compare_providers(job))
        passed = ms < 100
        _record("QPU-CostModel", "compare_providers(5 providers)", ms, passed)
        assert passed, f"compare_providers took {ms:.1f} ms (limit 100 ms)"

    def test_qpu_compare_providers_for_5_jobs(self):
        """compare_providers called for 5 jobs must complete in under 100 ms total."""
        from qpu_cost_model import QPUCostModeler, QPUJob

        modeler = QPUCostModeler(verbose=False)
        jobs = [
            QPUJob(circuit_depth=20 + i * 10, n_qubits=10 + i * 5,
                   n_shots=500, gate_count=50 + i * 20, error_rate=0.001)
            for i in range(5)
        ]
        t0 = time.perf_counter()
        for job in jobs:
            modeler.compare_providers(job)
        ms = (time.perf_counter() - t0) * 1000
        passed = ms < 100
        _record("QPU-CostModel", "compare_providers×5 jobs", ms, passed)
        assert passed, f"5 × compare_providers took {ms:.1f} ms (limit 100 ms)"

    def test_qpu_scheduler_submit_100_and_schedule_under_1000ms(self):
        """Submit 100 jobs and call schedule_next 100 times — total under 1000 ms."""
        from qpu_scheduler import QPUScheduler, Priority
        from qpu_cost_model import QPUJob

        scheduler = QPUScheduler(max_concurrency=200)

        jobs = [
            QPUJob(
                circuit_depth=10 + (i % 40),
                n_qubits=5 + (i % 20),
                n_shots=100,
                gate_count=20 + (i % 30),
                error_rate=0.001,
            )
            for i in range(100)
        ]

        t0 = time.perf_counter()
        for job in jobs:
            scheduler.submit(job, priority=Priority.NORMAL)

        scheduled = 0
        for _ in range(100):
            sj = scheduler.schedule_next()
            if sj is not None:
                scheduled += 1

        ms = (time.perf_counter() - t0) * 1000
        passed = ms < 1000
        _record("QPU-Scheduler", "submit×100 + schedule_next×100", ms, passed)
        assert passed, f"QPU scheduler 100-job benchmark took {ms:.1f} ms (limit 1000 ms)"
        assert scheduled >= 1, "schedule_next never returned a job"


# ============================================================================
# Crypto agility scan benchmark (Stage1Discovery)
# ============================================================================

class TestCryptoAgilityScan:
    """Benchmark Stage1Discovery scan over a dict of 20 CryptoAsset entries."""

    def _make_assets(self, n: int = 20):
        """Build a list of CryptoAsset instances.

        CryptoAsset requires: asset_id, name, algorithm, key_size, usage, location, expiry
        """
        from migration_pipeline import CryptoAsset

        algorithms = [
            ("RSA-2048", 2048), ("RSA-4096", 4096), ("ECDSA-P256", 256),
            ("ECDH-P256", 256), ("AES-256-GCM", 256), ("AES-128", 128),
            ("SHA-256", 256), ("Ed25519", 255), ("X25519", 255),
            ("DH-2048", 2048), ("ECDSA-P384", 384), ("RSA-1024", 1024),
            ("AES-256-XTS", 256), ("ChaCha20", 256), ("HMAC-SHA256", 256),
            ("PBKDF2-SHA256", 256), ("bcrypt", 256), ("argon2id", 256),
            ("ECDH-P384", 384), ("secp256k1", 256),
        ]
        assets = [
            CryptoAsset(
                asset_id=f"ASSET-{i:02d}",
                name=f"{alg} usage in service-{i % 5}",
                algorithm=alg,
                key_size=bits,
                usage="TLS cert" if i % 3 == 0 else "signing" if i % 3 == 1 else "key exchange",
                location=f"service-{i % 5}",
                expiry="2027-01-01" if i % 2 == 0 else None,
            )
            for i, (alg, bits) in enumerate(algorithms[:n])
        ]
        return assets

    def test_crypto_agility_scan_under_100ms(self):
        """Stage1Discovery.run over 20 CryptoAssets must complete under 100 ms."""
        from migration_pipeline import Stage1Discovery

        assets = self._make_assets(20)
        stage = Stage1Discovery()
        result, ms = _bench(lambda: stage.run(assets))
        passed = ms < 100
        _record("CryptoAgility", "Stage1Discovery.run×20 assets", ms, passed)
        assert passed, f"Crypto agility scan took {ms:.1f} ms (limit 100 ms)"

    def test_crypto_agility_scan_finds_vulnerabilities(self):
        """Stage1Discovery must flag at least one VULNERABLE asset in the 20-asset set."""
        from migration_pipeline import Stage1Discovery

        assets = self._make_assets(20)
        stage = Stage1Discovery()
        result = stage.run(assets)
        vulnerable = [f for f in result.get("findings", [])
                      if f.get("status") == "VULNERABLE"]
        assert len(vulnerable) >= 1, (
            f"Expected at least 1 VULNERABLE finding, got 0. "
            f"All statuses: {[f.get('status') for f in result.get('findings', [])]}"
        )


# ============================================================================
# Print benchmark table at end of session
# ============================================================================

def pytest_sessionfinish(session, exitstatus):
    """Print a formatted benchmark summary table after all tests complete."""
    if not _RESULTS:
        return
    print("\n")
    print("=" * 62)
    print("  BENCHMARK SUMMARY")
    print("=" * 62)
    print(f"  {'Algorithm':<20} {'Operation':<25} {'Time (ms)':>10}  {'Status'}")
    print("  " + "-" * 58)
    for algo, op, ms, passed in sorted(_RESULTS, key=lambda r: r[0]):
        status = "PASS" if passed else "FAIL"
        print(f"  {algo:<20} {op:<25} {ms:>10.1f}ms  {status}")
    print("=" * 62)
