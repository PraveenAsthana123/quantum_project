"""
test_pqc_benchmark.py — pytest tests for qc-security-lab/src/pqc_benchmark.py.

Covers:
  - Classical RSA/ECDSA benchmark output shape and quantum_safe classification.
  - Pure-Python KEM/signature stub output shape and quantum_safe classification.
  - Timing values are positive floats.

All tests use the pure-Python stub path (n_runs=1 equivalent) so they run
fast without liboqs or GPU hardware.
"""
import importlib.util
from pathlib import Path
import pytest

# Load qc-security-lab's pqc_benchmark.py by absolute path to avoid name
# collision with pqc-control-tower/src/pqc_benchmark.py when both src/ dirs
# land on sys.path during a combined pytest run.
_SRC_FILE = Path(__file__).parent.parent / "src" / "pqc_benchmark.py"
_spec = importlib.util.spec_from_file_location("qcsec_pqc_benchmark", str(_SRC_FILE))
pb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pb)


# ---------------------------------------------------------------------------
# Helpers — temporarily override BENCH_RUNS to 1 for speed
# ---------------------------------------------------------------------------

def _quick_classical_rsa() -> dict:
    """Patch BENCH_RUNS to 1, run RSA benchmark, restore."""
    orig = pb.BENCH_RUNS
    pb.BENCH_RUNS = 1
    try:
        return pb._bench_classical_rsa()
    finally:
        pb.BENCH_RUNS = orig


def _quick_classical_ecdsa() -> dict:
    orig = pb.BENCH_RUNS
    pb.BENCH_RUNS = 1
    try:
        return pb._bench_classical_ecdsa()
    finally:
        pb.BENCH_RUNS = orig


def _quick_kem_stub(algo: str) -> dict:
    orig = pb.BENCH_RUNS
    pb.BENCH_RUNS = 1
    try:
        return pb._pure_python_kem_stub(algo, 192, "FIPS 203")
    finally:
        pb.BENCH_RUNS = orig


def _quick_sig_stub(algo: str) -> dict:
    orig = pb.BENCH_RUNS
    pb.BENCH_RUNS = 1
    try:
        return pb._pure_python_sig_stub(algo, 192, "FIPS 204")
    finally:
        pb.BENCH_RUNS = orig


# ---------------------------------------------------------------------------
# RSA-2048 classical benchmark
# ---------------------------------------------------------------------------

class TestClassicalRSA:
    def test_returns_expected_keys(self):
        r = _quick_classical_rsa()
        required = {"algorithm", "quantum_safe", "keygen_ms"}
        assert required.issubset(r.keys()), f"Missing keys: {required - r.keys()}"

    def test_quantum_vulnerable(self):
        r = _quick_classical_rsa()
        assert r["quantum_safe"] is False, "RSA-2048 must be quantum_safe=False"

    def test_algorithm_label_contains_rsa(self):
        r = _quick_classical_rsa()
        assert "RSA" in r["algorithm"].upper()

    def test_timing_positive(self):
        r = _quick_classical_rsa()
        if "keygen_ms" in r:
            assert r["keygen_ms"] > 0, "keygen_ms must be positive"
        if "sign_ms" in r:
            assert r["sign_ms"] > 0
        if "verify_ms" in r:
            assert r["verify_ms"] > 0


# ---------------------------------------------------------------------------
# ECDSA-P256 classical benchmark
# ---------------------------------------------------------------------------

class TestClassicalECDSA:
    def test_returns_expected_keys(self):
        r = _quick_classical_ecdsa()
        assert "quantum_safe" in r

    def test_quantum_vulnerable(self):
        r = _quick_classical_ecdsa()
        assert r["quantum_safe"] is False, "ECDSA-P256 must be quantum_safe=False"

    def test_timing_positive(self):
        r = _quick_classical_ecdsa()
        if "keygen_ms" in r:
            assert r["keygen_ms"] > 0


# ---------------------------------------------------------------------------
# ML-KEM-768 pure-Python stub
# ---------------------------------------------------------------------------

class TestMLKEMStub:
    ALGO = "ML-KEM-768"

    def test_returns_expected_keys(self):
        r = _quick_kem_stub(self.ALGO)
        for key in ("algorithm", "quantum_safe", "keygen_ms", "encap_ms", "decap_ms",
                    "pk_bytes", "ct_bytes", "ss_bytes"):
            assert key in r, f"Key '{key}' missing from stub result"

    def test_quantum_safe(self):
        r = _quick_kem_stub(self.ALGO)
        assert r["quantum_safe"] is True, "ML-KEM-768 must be quantum_safe=True"

    def test_algorithm_label(self):
        r = _quick_kem_stub(self.ALGO)
        assert r["algorithm"] == self.ALGO

    def test_key_sizes_positive(self):
        r = _quick_kem_stub(self.ALGO)
        assert r["pk_bytes"] > 0
        assert r["ct_bytes"] > 0
        assert r["ss_bytes"] > 0

    def test_timing_positive_floats(self):
        r = _quick_kem_stub(self.ALGO)
        assert isinstance(r["keygen_ms"], float)
        assert r["keygen_ms"] > 0
        assert r["encap_ms"] > 0
        assert r["decap_ms"] > 0

    def test_kem_verified_flag(self):
        r = _quick_kem_stub(self.ALGO)
        assert r.get("kem_verified") is True


# ---------------------------------------------------------------------------
# ML-DSA-65 pure-Python stub
# ---------------------------------------------------------------------------

class TestMLDSAStub:
    ALGO = "ML-DSA-65"

    def test_returns_expected_keys(self):
        r = _quick_sig_stub(self.ALGO)
        for key in ("algorithm", "quantum_safe", "keygen_ms", "sign_ms", "verify_ms",
                    "pk_bytes", "sig_bytes"):
            assert key in r, f"Key '{key}' missing from stub result"

    def test_quantum_safe(self):
        r = _quick_sig_stub(self.ALGO)
        assert r["quantum_safe"] is True

    def test_timing_positive(self):
        r = _quick_sig_stub(self.ALGO)
        assert r["keygen_ms"] > 0
        assert r["sign_ms"] > 0
        assert r["verify_ms"] > 0

    def test_verified_flag(self):
        r = _quick_sig_stub(self.ALGO)
        assert r.get("verified") is True


# ---------------------------------------------------------------------------
# Parametrised: every KEM stub must be quantum_safe=True
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("algo", ["ML-KEM-512", "ML-KEM-768", "ML-KEM-1024"])
def test_all_kem_stubs_quantum_safe(algo):
    orig = pb.BENCH_RUNS
    pb.BENCH_RUNS = 1
    try:
        r = pb._pure_python_kem_stub(algo, 128, "FIPS 203")
    finally:
        pb.BENCH_RUNS = orig
    assert r["quantum_safe"] is True, f"{algo} must report quantum_safe=True"


@pytest.mark.parametrize("algo", ["ML-DSA-44", "ML-DSA-65", "ML-DSA-87",
                                   "Falcon-512", "Falcon-1024"])
def test_all_sig_stubs_quantum_safe(algo):
    orig = pb.BENCH_RUNS
    pb.BENCH_RUNS = 1
    try:
        r = pb._pure_python_sig_stub(algo, 128, "FIPS 204")
    finally:
        pb.BENCH_RUNS = orig
    assert r["quantum_safe"] is True, f"{algo} must report quantum_safe=True"
