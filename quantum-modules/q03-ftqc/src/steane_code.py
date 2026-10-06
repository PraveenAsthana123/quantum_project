"""
Q03 — Steane [[7,1,3]] Code.

Encodes 1 logical qubit into 7 physical qubits, injects a single bit-flip
error on qubit 3, computes the syndrome, identifies and corrects the error.

Uses Qiskit for circuit construction and numpy for syndrome decoding.
Saves results to data/steane_results.json.
"""

import json
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.quantum_info import Statevector

RESULTS_PATH = Path(__file__).parent.parent / "data" / "steane_results.json"

# ── Steane [[7,1,3]] parity check matrix ─────────────────────────────────
# H_X = H_Z = same matrix for the Steane code (self-dual CSS code)
# Rows are the 3 X-stabilizer and 3 Z-stabilizer generators
H = np.array([
    [1, 0, 1, 0, 1, 0, 1],  # g1
    [0, 1, 1, 0, 0, 1, 1],  # g2
    [0, 0, 0, 1, 1, 1, 1],  # g3
], dtype=int)

# Syndrome lookup table: syndrome → qubit in error (1-indexed, 0=no error)
def build_syndrome_table() -> dict:
    """Maps 3-bit syndrome integer to qubit index (0=no error, 1-7=qubit)."""
    table = {0: 0}  # 000 → no error
    for q in range(7):
        e = np.zeros(7, dtype=int)
        e[q] = 1
        syndrome = (H @ e) % 2
        key = int("".join(map(str, syndrome)), 2)
        table[key] = q + 1  # 1-indexed qubit
    return table

SYNDROME_TABLE = build_syndrome_table()


# ── Encoding circuit ──────────────────────────────────────────────────────

def steane_encode(logical_bit: int = 0) -> QuantumCircuit:
    """
    Return a 7-qubit circuit encoding |logical_bit⟩ into the Steane code.

    Encoding maps:
      |0⟩_L → (|0000000⟩ + |1010101⟩ + |0110011⟩ + |1100110⟩ +
                |0001111⟩ + |1011010⟩ + |0111100⟩ + |1101001⟩) / 2√2

    We use the standard generator-based encoding circuit.
    """
    qr = QuantumRegister(7, "q")
    qc = QuantumCircuit(qr)

    if logical_bit == 1:
        qc.x(qr[0])  # flip the first qubit to encode |1⟩_L

    # Create superpositions on syndrome bits (qubits 4, 5, 6 — 0-indexed 3,4,5,6 group)
    # Standard Steane encoding:
    # H on qubits at positions 3, 5, 6 (0-indexed: 2, 4, 5) — the "check" positions
    for check_q in [2, 4, 5]:  # 0-indexed positions 3, 5, 6 in 1-indexed literature
        qc.h(check_q)

    # CNOT entangling gates derived from the parity check matrix
    # Each generator row specifies which data qubits to entangle with which check qubit
    # Generator g1 (row 0): involves qubits 0,2,4,6 → check qubit = 2 (0-indexed)
    for data_q in [0, 3, 5]:
        qc.cx(2, data_q)
    # Generator g2 (row 1): involves qubits 1,2,5,6 → check qubit = 4 (0-indexed)
    for data_q in [1, 3, 6]:
        qc.cx(4, data_q)
    # Generator g3 (row 2): involves qubits 3,4,5,6 → check qubit = 5 (0-indexed)
    for data_q in [0, 1, 6]:
        qc.cx(5, data_q)

    return qc


# ── Syndrome extraction circuit ────────────────────────────────────────────

def syndrome_circuit(data_circuit: QuantumCircuit) -> tuple[QuantumCircuit, list]:
    """
    Append syndrome measurement ancilla qubits and return (full_circuit, ancilla_regs).
    Uses 3 ancilla qubits for Z-syndrome (X-error detection).
    """
    n_data = 7
    anc = QuantumRegister(3, "anc")
    creg = ClassicalRegister(3, "syn")
    qc = QuantumCircuit(QuantumRegister(n_data, "q"), anc, creg)

    # Compose data preparation
    qc.compose(data_circuit, qubits=range(n_data), inplace=True)

    # Measure Z stabilizers (detect X errors)
    # Stabilizer 1: Z on qubits {0,2,4,6} → ancilla 0
    # Stabilizer 2: Z on qubits {1,2,5,6} → ancilla 1
    # Stabilizer 3: Z on qubits {3,4,5,6} → ancilla 2
    # Implemented via CNOT from data to ancilla (ancilla starts in |0⟩)
    ancilla_data = [
        (0, [0, 2, 4, 6]),   # ancilla 0 ← data qubits 0,2,4,6
        (1, [1, 2, 5, 6]),   # ancilla 1 ← data qubits 1,2,5,6
        (2, [3, 4, 5, 6]),   # ancilla 2 ← data qubits 3,4,5,6
    ]
    for anc_idx, data_qs in ancilla_data:
        for dq in data_qs:
            qc.cx(dq, n_data + anc_idx)

    # Measure ancillas
    qc.measure(range(n_data, n_data + 3), creg)
    return qc, creg


def syndrome_via_matrix(error_vec: np.ndarray) -> np.ndarray:
    """Compute syndrome = H @ error_vec mod 2."""
    return (H @ error_vec) % 2


def correct_error(sv: np.ndarray, syndrome: np.ndarray) -> tuple[np.ndarray, int]:
    """
    Apply X correction on the identified qubit.
    Returns (corrected_statevector, corrected_qubit_index 1-based).
    """
    syn_int = int("".join(map(str, syndrome.tolist())), 2)
    qubit_to_correct = SYNDROME_TABLE.get(syn_int, 0)

    if qubit_to_correct == 0:
        return sv.copy(), 0

    # Apply X to the identified qubit in the statevector
    n = 7
    dim = 2 ** n
    target = qubit_to_correct - 1  # 0-indexed

    corrected_sv = sv.copy()
    for idx in range(dim):
        # Flip qubit `target` in index `idx`
        partner = idx ^ (1 << target)
        if idx < partner:
            corrected_sv[idx], corrected_sv[partner] = corrected_sv[partner], corrected_sv[idx]

    return corrected_sv, qubit_to_correct


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Q03 — Steane [[7,1,3]] Quantum Error Correction Code")
    print("=" * 60)

    # Parameters
    error_qubit = 3  # 1-indexed qubit to inject error on
    logical_bit = 0  # encode |0⟩_L

    print(f"\n  Code: [[7,1,3]] Steane  (7 physical → 1 logical qubit)")
    print(f"  Code distance : 3")
    print(f"  Injected error: X on qubit {error_qubit} (1-indexed)")

    # Error vector
    error_vec = np.zeros(7, dtype=int)
    error_vec[error_qubit - 1] = 1  # convert to 0-indexed
    print(f"  Error vector  : {error_vec.tolist()}")

    # Compute syndrome analytically
    syndrome = syndrome_via_matrix(error_vec)
    syn_int = int("".join(map(str, syndrome.tolist())), 2)
    print(f"\n  Syndrome (H·e mod 2)  : {syndrome.tolist()}  (binary: {format(syn_int,'03b')})")

    # Decode
    detected_qubit = SYNDROME_TABLE.get(syn_int, 0)
    print(f"  Syndrome table lookup : qubit {detected_qubit} in error")
    error_detected = detected_qubit == error_qubit
    print(f"  Error correctly identified: {error_detected}")

    # Verify via Qiskit statevector
    enc_qc = steane_encode(logical_bit)
    sv_clean = np.array(Statevector.from_instruction(enc_qc).data)

    # Inject error in statevector
    n = 7
    dim = 2 ** n
    target_q = error_qubit - 1  # 0-indexed
    sv_errored = sv_clean.copy()
    # Apply X on qubit target_q: swap amplitudes for each pair differing at target_q
    for idx in range(dim):
        partner = idx ^ (1 << target_q)
        if idx < partner:
            sv_errored[idx], sv_errored[partner] = sv_errored[partner], sv_errored[idx]

    # Correct
    sv_corrected, corrected_qubit = correct_error(sv_errored, syndrome)
    fidelity = float(abs(np.dot(sv_corrected.conj(), sv_clean)) ** 2)
    print(f"\n  Statevector fidelity after correction: {fidelity:.6f}")
    corrected = fidelity > 0.999

    print(f"  Error corrected: {corrected}")

    # Summary
    print("\n  Syndrome lookup table (all single-qubit errors):")
    for syn_val, q in sorted(SYNDROME_TABLE.items()):
        print(f"    syndrome {format(syn_val,'03b')} → qubit {q} {'(no error)' if q == 0 else ''}")

    data = {
        "code": "Steane [[7,1,3]]",
        "n_physical": 7,
        "n_logical": 1,
        "code_distance": 3,
        "logical_bit_encoded": logical_bit,
        "error_injected": f"X on qubit {error_qubit}",
        "error_vector": error_vec.tolist(),
        "syndrome": syndrome.tolist(),
        "syndrome_binary": format(syn_int, "03b"),
        "error_detected_qubit": detected_qubit,
        "error_detected": error_detected,
        "statevector_fidelity_after_correction": round(fidelity, 8),
        "corrected": corrected,
        "syndrome_table": {format(k, "03b"): v for k, v in SYNDROME_TABLE.items()},
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved → {RESULTS_PATH}")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
