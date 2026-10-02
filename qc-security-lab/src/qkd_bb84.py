"""
BB84 Quantum Key Distribution simulation using Qiskit.

Simulates a complete BB84 QKD protocol including:
  1. Alice prepares qubits in random bases/states
  2. Eve (optional eavesdropper) intercepts and re-measures
  3. Bob measures in random bases
  4. Sifting — keep bits where Alice and Bob used the same basis
  5. Error rate estimation — QBER (Quantum Bit Error Rate)
  6. Eavesdropping detection via statistical test on QBER threshold

Saves results to data/qkd_results.json.
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import AerSimulator

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent / "data"
RESULTS_FILE = DATA_DIR / "qkd_results.json"

# BB84 parameters
N_KEY_BITS   = 256      # qubits exchanged (raw key length before sifting)
QBER_THRESHOLD = 0.11   # >11% QBER → eavesdropping likely (BB84 security bound)

# Basis symbols
RECTILINEAR = 0   # {|0⟩, |1⟩}  — Z basis
DIAGONAL    = 1   # {|+⟩, |−⟩}  — X basis


# ── BB84 helpers ──────────────────────────────────────────────────────────────

def prepare_qubit(bit: int, basis: int) -> QuantumCircuit:
    """
    Alice prepares one qubit.
      bit=0, basis=Z → |0⟩
      bit=1, basis=Z → |1⟩
      bit=0, basis=X → |+⟩  (H|0⟩)
      bit=1, basis=X → |−⟩  (H|1⟩ = HX|0⟩)
    """
    qr = QuantumRegister(1, "q")
    cr = ClassicalRegister(1, "c")
    qc = QuantumCircuit(qr, cr)
    if bit == 1:
        qc.x(0)              # flip to |1⟩
    if basis == DIAGONAL:
        qc.h(0)              # rotate to X basis
    return qc


def eve_measure_and_resend(qc: QuantumCircuit, eve_basis: int) -> QuantumCircuit:
    """
    Eve intercepts: measures in her chosen basis and re-prepares based on result.
    This collapses the state — introduces errors when Eve's basis ≠ Alice's basis.
    Returned circuit is a new preparation by Eve.
    """
    # Measure in Eve's basis
    if eve_basis == DIAGONAL:
        qc.h(0)
    qc.measure(0, 0)

    # Simulate to get Eve's measurement outcome
    sim = AerSimulator()
    job = sim.run(qc, shots=1)
    counts = job.result().get_counts()
    eve_bit = int(list(counts.keys())[0])

    # Eve re-prepares in her basis
    qr = QuantumRegister(1, "q")
    cr = ClassicalRegister(1, "c")
    new_qc = QuantumCircuit(qr, cr)
    if eve_bit == 1:
        new_qc.x(0)
    if eve_basis == DIAGONAL:
        new_qc.h(0)
    return new_qc


def bob_measure(qc: QuantumCircuit, bob_basis: int) -> int:
    """Bob measures the qubit in his chosen basis. Returns 0 or 1."""
    if bob_basis == DIAGONAL:
        qc.h(0)
    qc.measure(0, 0)
    sim = AerSimulator()
    job = sim.run(qc, shots=1)
    counts = job.result().get_counts()
    return int(list(counts.keys())[0])


# ── Vectorised simulation (build all circuits, batch-run for speed) ───────────

def _run_protocol_vectorised(
    n_bits: int,
    rng: np.random.Generator,
    with_eve: bool,
) -> dict:
    """
    Efficient BB84 simulation: build circuits for all n_bits, run in batch.
    Returns raw Alice/Bob bit arrays and basis arrays.
    """
    alice_bits   = rng.integers(0, 2, n_bits)
    alice_bases  = rng.integers(0, 2, n_bits)
    bob_bases    = rng.integers(0, 2, n_bits)
    eve_bases    = rng.integers(0, 2, n_bits) if with_eve else None

    sim = AerSimulator()
    bob_bits = np.zeros(n_bits, dtype=int)

    # Build all circuits
    circuits = []
    for i in range(n_bits):
        qr = QuantumRegister(1, "q")
        cr = ClassicalRegister(1, "c")
        qc = QuantumCircuit(qr, cr)

        # Alice prepares
        if alice_bits[i] == 1:
            qc.x(0)
        if alice_bases[i] == DIAGONAL:
            qc.h(0)

        # Eve intercepts (if present): measure + re-prepare in same circuit using
        # a reset gadget approximation — for pure simulation we use a mid-circuit
        # measurement barrier (deferred to separate mini-circuits for accuracy)
        if with_eve:
            # Save Alice's state by measuring Eve's basis then re-inject
            # Full mid-circuit measurement: use barrier as a conceptual divider;
            # real Eve re-sends a fresh qubit — we simulate this as two circuits.
            # For efficiency, approximate: if bases match, bit passes through;
            # if mismatch, bit is randomised (correct statistical behaviour).
            if eve_bases[i] != alice_bases[i]:
                # Eve measures in wrong basis → 50% chance of error on Bob's side
                # Simulate: flip alice_effective_bit with p=0.5
                if rng.random() < 0.5:
                    # Eve gets wrong bit, resends flipped
                    qc.reset(0)
                    effective_bit = 1 - alice_bits[i]
                    if effective_bit == 1:
                        qc.x(0)
                    if alice_bases[i] == DIAGONAL:
                        qc.h(0)

        # Bob measures
        if bob_bases[i] == DIAGONAL:
            qc.h(0)
        qc.measure(0, 0)
        circuits.append(qc)

    # Batch execution
    job  = sim.run(circuits, shots=1)
    res  = job.result()
    for i in range(n_bits):
        counts = res.get_counts(i)
        bob_bits[i] = int(list(counts.keys())[0])

    return {
        "alice_bits":  alice_bits,
        "alice_bases": alice_bases,
        "bob_bits":    bob_bits,
        "bob_bases":   bob_bases,
        "eve_bases":   eve_bases,
    }


# ── Sifting & QBER ────────────────────────────────────────────────────────────

def sift_key(alice_bits, alice_bases, bob_bits, bob_bases) -> tuple[np.ndarray, np.ndarray]:
    """Keep only bits where Alice and Bob used the same basis."""
    mask = alice_bases == bob_bases
    return alice_bits[mask], bob_bits[mask]


def compute_qber(alice_sifted: np.ndarray, bob_sifted: np.ndarray) -> float:
    """Quantum Bit Error Rate: fraction of mismatches in sifted key."""
    if len(alice_sifted) == 0:
        return 0.0
    return float(np.sum(alice_sifted != bob_sifted) / len(alice_sifted))


# ── Full BB84 run ─────────────────────────────────────────────────────────────

def run_bb84(n_bits: int = N_KEY_BITS, with_eve: bool = False, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    label = "BB84 with eavesdropper (Eve)" if with_eve else "BB84 no eavesdropper"

    print(f"\n  Running {label} — {n_bits} qubits...")
    t0 = time.perf_counter()

    data = _run_protocol_vectorised(n_bits, rng, with_eve)

    alice_sifted, bob_sifted = sift_key(
        data["alice_bits"], data["alice_bases"],
        data["bob_bits"],   data["bob_bases"],
    )
    runtime = time.perf_counter() - t0

    sift_rate = len(alice_sifted) / n_bits
    qber      = compute_qber(alice_sifted, bob_sifted)
    eve_detected = qber > QBER_THRESHOLD

    # Check key agreement on non-error bits
    matching = np.sum(alice_sifted == bob_sifted)
    key_len  = len(alice_sifted)

    print(f"    raw={n_bits}  sifted={key_len} ({sift_rate:.1%})  "
          f"QBER={qber:.2%}  "
          f"{'⚠ EVE DETECTED' if eve_detected else 'channel secure'}")

    # Sample shared secret (first 32 bits of agreed sifted key, or as many as available)
    agreed_mask = alice_sifted == bob_sifted
    agreed_bits = alice_sifted[agreed_mask]
    secret_bits = agreed_bits[:32] if len(agreed_bits) >= 32 else agreed_bits
    shared_secret_hex = ""
    if len(secret_bits) >= 8:
        n_bytes = len(secret_bits) // 8
        byte_arr = bytearray()
        for b in range(n_bytes):
            byte_val = int("".join(str(x) for x in secret_bits[b*8:(b+1)*8]), 2)
            byte_arr.append(byte_val)
        shared_secret_hex = byte_arr.hex()

    return {
        "scenario": label,
        "n_qubits_sent": n_bits,
        "sifted_key_bits": key_len,
        "sift_efficiency": round(sift_rate, 4),
        "qber": round(qber, 4),
        "qber_threshold": QBER_THRESHOLD,
        "eve_detected": eve_detected,
        "matching_bits": int(matching),
        "key_agreement_rate": round(float(matching / key_len) if key_len > 0 else 0.0, 4),
        "shared_secret_hex_sample": shared_secret_hex[:16] + "..." if len(shared_secret_hex) > 16 else shared_secret_hex,
        "runtime_s": round(runtime, 3),
        "with_eve": with_eve,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("BB84 Quantum Key Distribution (QKD) Simulation")
    print(f"  Qubits: {N_KEY_BITS}  |  QBER threshold: {QBER_THRESHOLD:.0%}")
    print("=" * 65)

    t_total = time.perf_counter()

    # Scenario 1: No eavesdropper — QBER should be ~0%
    result_clean = run_bb84(n_bits=N_KEY_BITS, with_eve=False, seed=42)

    # Scenario 2: Eve intercepts ~all qubits — QBER should be ~25%
    result_eve   = run_bb84(n_bits=N_KEY_BITS, with_eve=True,  seed=99)

    total_time = time.perf_counter() - t_total

    print(f"\nTotal simulation time: {total_time:.2f}s")
    print("\nSummary:")
    print(f"  No-Eve  QBER={result_clean['qber']:.2%}  "
          f"sifted={result_clean['sifted_key_bits']} bits  "
          f"detected={result_clean['eve_detected']}")
    print(f"  Eve     QBER={result_eve['qber']:.2%}  "
          f"sifted={result_eve['sifted_key_bits']} bits  "
          f"detected={result_eve['eve_detected']}")

    results = {
        "protocol": "BB84",
        "backend": "Qiskit Aer simulator",
        "n_qubits": N_KEY_BITS,
        "qber_threshold": QBER_THRESHOLD,
        "scenarios": [result_clean, result_eve],
        "total_runtime_s": round(total_time, 3),
        "security_notes": [
            "BB84 is information-theoretically secure against any eavesdropper.",
            "Eve's intercept-resend attack introduces ~25% QBER (detectable above 11% threshold).",
            "After sifting, remaining errors require privacy amplification (not simulated here).",
            "Practical QKD systems additionally run error correction before key use.",
        ],
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved → {RESULTS_FILE}")
    return results


if __name__ == "__main__":
    main()
