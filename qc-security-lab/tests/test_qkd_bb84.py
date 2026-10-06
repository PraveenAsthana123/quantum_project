"""
test_qkd_bb84.py — pytest tests for qc-security-lab/src/qkd_bb84.py.

Covers:
  - Protocol runs for n_qubits=32 without raising an exception.
  - Return dict contains required keys with correct types.
  - Without eavesdropping: QBER < 0.05.
  - With eavesdropping (fixed seed): eavesdrop_detected is True.
  - Sifted key length is > 0.
  - Helper functions (sift_key, compute_qber) behave correctly on simple inputs.

All quantum simulation runs use n_qubits=32 to keep test time short.
The Qiskit Aer simulator is required; tests are skipped if it is unavailable.
"""
import pytest
import numpy as np

try:
    from qiskit_aer import AerSimulator  # noqa: F401
    _QISKIT_AVAILABLE = True
except ImportError:
    _QISKIT_AVAILABLE = False

skip_no_qiskit = pytest.mark.skipif(
    not _QISKIT_AVAILABLE,
    reason="qiskit-aer not installed",
)

# conftest.py already inserted src/ into sys.path
import qkd_bb84 as bb84

N_QUBITS = 32   # small enough for fast CI runs
SEED_CLEAN = 42
SEED_EVE   = 7   # fixed seed that produces detectable Eve


# ---------------------------------------------------------------------------
# Helper function unit tests (no Qiskit needed)
# ---------------------------------------------------------------------------

class TestSiftKey:
    def test_matching_bases_kept(self):
        alice_bits  = np.array([0, 1, 0, 1])
        alice_bases = np.array([0, 0, 1, 1])
        bob_bits    = np.array([0, 1, 0, 1])
        bob_bases   = np.array([0, 1, 1, 1])   # positions 0, 2, 3 match
        a_sifted, b_sifted = bb84.sift_key(alice_bits, alice_bases, bob_bits, bob_bases)
        # positions 0 (0==0), 2 (1==1), 3 (1==1) match
        assert len(a_sifted) == 3
        np.testing.assert_array_equal(a_sifted, [0, 0, 1])
        np.testing.assert_array_equal(b_sifted, [0, 0, 1])

    def test_no_matching_bases_empty(self):
        alice_bases = np.array([0, 0])
        bob_bases   = np.array([1, 1])
        a_s, b_s = bb84.sift_key(np.array([0, 1]), alice_bases,
                                  np.array([0, 1]), bob_bases)
        assert len(a_s) == 0


class TestComputeQBER:
    def test_zero_error_rate(self):
        bits = np.array([0, 1, 0, 1])
        assert bb84.compute_qber(bits, bits) == 0.0

    def test_full_error_rate(self):
        a = np.array([0, 0, 0, 0])
        b = np.array([1, 1, 1, 1])
        assert bb84.compute_qber(a, b) == 1.0

    def test_half_error_rate(self):
        a = np.array([0, 0, 1, 1])
        b = np.array([0, 1, 0, 1])
        assert abs(bb84.compute_qber(a, b) - 0.5) < 1e-9

    def test_empty_array_returns_zero(self):
        assert bb84.compute_qber(np.array([]), np.array([])) == 0.0


# ---------------------------------------------------------------------------
# Full BB84 protocol integration tests (require Qiskit)
# ---------------------------------------------------------------------------

@skip_no_qiskit
class TestBB84NoEavesdropper:
    """Protocol without Eve — channel should be clean."""

    @pytest.fixture(scope="class")
    def result(self):
        return bb84.run_bb84(n_bits=N_QUBITS, with_eve=False, seed=SEED_CLEAN)

    def test_returns_dict(self, result):
        assert isinstance(result, dict)

    def test_required_keys_present(self, result):
        for key in ("qber", "sifted_key_bits", "eve_detected", "with_eve",
                    "n_qubits_sent", "sift_efficiency"):
            assert key in result, f"Key '{key}' missing from run_bb84 result"

    def test_qber_is_float_in_range(self, result):
        assert isinstance(result["qber"], float)
        assert 0.0 <= result["qber"] <= 1.0

    def test_sifted_key_length_positive(self, result):
        assert isinstance(result["sifted_key_bits"], int)
        assert result["sifted_key_bits"] > 0

    def test_low_qber_no_eve(self, result):
        """Without eavesdropping, QBER should be negligible (< 0.05)."""
        assert result["qber"] < 0.05, (
            f"Expected QBER < 0.05 without Eve, got {result['qber']}"
        )

    def test_eve_not_detected(self, result):
        assert result["eve_detected"] is False

    def test_with_eve_flag_false(self, result):
        assert result["with_eve"] is False

    def test_n_qubits_sent_matches_input(self, result):
        assert result["n_qubits_sent"] == N_QUBITS


@skip_no_qiskit
class TestBB84WithEavesdropper:
    """Protocol with Eve intercept-resend — eavesdropping should be detected."""

    @pytest.fixture(scope="class")
    def result(self):
        return bb84.run_bb84(n_bits=N_QUBITS, with_eve=True, seed=SEED_EVE)

    def test_returns_dict(self, result):
        assert isinstance(result, dict)

    def test_required_keys_present(self, result):
        for key in ("qber", "sifted_key_bits", "eve_detected"):
            assert key in result

    def test_sifted_key_length_positive(self, result):
        assert result["sifted_key_bits"] > 0

    def test_eavesdrop_detected(self, result):
        """Eve intercepts all qubits; QBER should exceed the 11% threshold."""
        assert result["eve_detected"] is True, (
            f"Expected eavesdrop_detected=True with Eve, "
            f"got QBER={result['qber']:.4f}"
        )

    def test_elevated_qber(self, result):
        """Eve's intercept-resend attack typically yields ~25% QBER."""
        assert result["qber"] > bb84.QBER_THRESHOLD, (
            f"QBER {result['qber']} should exceed threshold {bb84.QBER_THRESHOLD}"
        )

    def test_with_eve_flag_true(self, result):
        assert result["with_eve"] is True


# ---------------------------------------------------------------------------
# prepare_qubit — circuit shape checks (no Qiskit simulator invocation)
# ---------------------------------------------------------------------------

@skip_no_qiskit
@pytest.mark.parametrize("bit,basis", [(0, 0), (1, 0), (0, 1), (1, 1)])
def test_prepare_qubit_returns_circuit(bit, basis):
    from qiskit import QuantumCircuit
    qc = bb84.prepare_qubit(bit, basis)
    assert isinstance(qc, QuantumCircuit)
    assert qc.num_qubits == 1
    assert qc.num_clbits == 1
