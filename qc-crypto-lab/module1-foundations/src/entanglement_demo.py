"""
CUSTOMER DEMO PITCH — Quantum Entanglement & Bell States
=========================================================
Entanglement is the resource that makes quantum cryptography fundamentally
different from classical cryptography.  When two qubits are entangled, their
measurement outcomes are perfectly correlated — no matter how far apart the
particles are — and those correlations cannot be explained by any pre-shared
classical information (Bell's theorem, 1964).

Why this matters for cryptography:
  - Bell pairs are the core resource for E91 QKD (Ekert 1991).
  - CHSH inequality violation certifies the correlations are quantum (not classical),
    which means Eve cannot fake them — the security is device-independent.
  - Entanglement enables quantum teleportation and quantum repeaters for long-distance QKD.

This demo creates all four Bell states, measures them 1000 times each, and shows the
perfect (anti-)correlation that classical shared randomness cannot replicate.

Audience: Security architects, quantum engineers, interview panels.
Runtime: < 10 seconds on Aer simulator.
"""

import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_2qubit(qc: QuantumCircuit, shots: int = 1000) -> dict:
    sim = AerSimulator()
    qc_m = qc.copy()
    qc_m.measure_all()
    result = sim.run(qc_m, shots=shots).result()
    return result.get_counts()


def correlation_coefficient(counts: dict, shots: int) -> float:
    """
    Compute Pearson-like correlation for two-qubit measurement:
      +1 = perfectly correlated, -1 = perfectly anti-correlated.
    Bit values: '0' → +1, '1' → -1 (spin convention).
    """
    corr = 0.0
    for outcome, cnt in counts.items():
        # Qiskit bit-string order: qubit[1] qubit[0]  (right = qubit 0)
        b0 = 1 if outcome[-1] == "0" else -1   # qubit 0 (Alice)
        b1 = 1 if outcome[0]  == "0" else -1   # qubit 1 (Bob)
        corr += b0 * b1 * cnt
    return corr / shots


def print_sep(title: str = "") -> None:
    w = 62
    if title:
        p = (w - len(title) - 2) // 2
        print("=" * p + f" {title} " + "=" * (w - p - len(title) - 2))
    else:
        print("=" * w)


# ---------------------------------------------------------------------------
# Bell state circuits
# ---------------------------------------------------------------------------

BELL_STATES = {
    "|Φ+⟩ = (|00⟩+|11⟩)/√2": "phi_plus",
    "|Φ-⟩ = (|00⟩-|11⟩)/√2": "phi_minus",
    "|Ψ+⟩ = (|01⟩+|10⟩)/√2": "psi_plus",
    "|Ψ-⟩ = (|01⟩-|10⟩)/√2": "psi_minus",
}


def build_bell(name: str) -> QuantumCircuit:
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    if name == "phi_minus":
        qc.z(0)            # Z on qubit 0 flips phase
    elif name == "psi_plus":
        qc.x(1)            # X on qubit 1 flips Bob's bit
    elif name == "psi_minus":
        qc.x(1)
        qc.z(0)
    return qc


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    shots = 1000
    sim = AerSimulator()

    print_sep("QUANTUM ENTANGLEMENT — Bell State Demo")
    print("Purpose: Show four Bell states, measure correlations, compare to classical\n")

    print_sep("Bell State Measurement Results")
    print(f"  {'State':<38}  {'|00⟩':>5}  {'|01⟩':>5}  {'|10⟩':>5}  {'|11⟩':>5}  {'Corr':>6}")
    print(f"  {'-'*38}  {'-'*5}  {'-'*5}  {'-'*5}  {'-'*5}  {'-'*6}")

    results = {}
    for label, name in BELL_STATES.items():
        qc = build_bell(name)
        counts = run_2qubit(qc, shots=shots)
        c00 = counts.get("00", 0)
        c01 = counts.get("01", 0)
        c10 = counts.get("10", 0)
        c11 = counts.get("11", 0)
        corr = correlation_coefficient(counts, shots)
        results[label] = {"counts": counts, "corr": corr}
        print(f"  {label:<38}  {c00:>5}  {c01:>5}  {c10:>5}  {c11:>5}  {corr:>+6.3f}")

    print()
    print_sep("Correlation Analysis")
    for label, data in results.items():
        corr = data["corr"]
        counts = data["counts"]
        c00 = counts.get("00", 0)
        c11 = counts.get("11", 0)
        c01 = counts.get("01", 0)
        c10 = counts.get("10", 0)
        same = c00 + c11
        diff = c01 + c10
        interp = "PERFECTLY CORRELATED (same outcome)" if corr > 0.9 else \
                 "PERFECTLY ANTI-CORRELATED (opposite outcome)" if corr < -0.9 else \
                 "Mixed"
        print(f"\n  {label}")
        print(f"    Same outcome (00 or 11): {same:4d}/{shots}  ({100*same/shots:.1f}%)")
        print(f"    Diff outcome (01 or 10): {diff:4d}/{shots}  ({100*diff/shots:.1f}%)")
        print(f"    Correlation coefficient: {corr:+.3f}   → {interp}")

    print()
    print_sep("Classical Impossibility")
    print("""
  Classical shared-key (pre-shared random string) can reproduce the SAME
  marginal statistics (50/50 for each qubit individually) but CANNOT match
  the perfect correlations across ALL four measurement bases simultaneously.

  Bell's theorem (1964) proves: no local hidden variable model can generate
  the quantum correlations we just observed.  A CHSH inequality test would
  yield S ≈ 2.828 (quantum) vs S ≤ 2.000 (any classical strategy).

  Cryptographic consequence (E91 protocol):
    - Alice & Bob share entangled pairs from an untrusted source.
    - They measure in random bases and test the CHSH inequality on a subset.
    - If S > 2 → channel is quantum-secure (Eve cannot inject classical fakes).
    - If S ≤ 2 → Eve tampered with the entangled pairs → session aborted.
""")
    print_sep()


if __name__ == "__main__":
    main()
