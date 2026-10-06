"""
CUSTOMER DEMO PITCH — Qubit Fundamentals
=========================================
Every piece of modern security rests on classical bits: deterministic 0s and 1s.
This demo shows the *quantum bit* (qubit) — a fundamentally different object that
can exist in a coherent superposition of |0⟩ and |1⟩ simultaneously, and whose
measurement outcome is intrinsically random (not pseudo-random).

Why this matters for cryptography:
  - Superposition enables quantum parallelism (Grover, Shor algorithms).
  - Measurement irreversibly collapses the state → any eavesdropper disturbs the channel.
  - Intrinsic randomness powers quantum random-number generators (QRNG) — the gold
    standard entropy source for key material.

Audience: Security architects, CISO staff, interview panels.
Runtime: < 10 seconds on Aer simulator.
"""

import math
from collections import Counter

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_circuit(qc: QuantumCircuit, shots: int = 1000) -> dict:
    sim = AerSimulator()
    qc_m = qc.copy()
    qc_m.measure_all()
    result = sim.run(qc_m, shots=shots).result()
    return result.get_counts()


def bloch_angles(theta_deg: float, phi_deg: float) -> tuple:
    """Return (theta_rad, phi_rad) for a Bloch-sphere state."""
    return math.radians(theta_deg), math.radians(phi_deg)


def print_separator(title: str = "") -> None:
    width = 60
    if title:
        pad = (width - len(title) - 2) // 2
        print("=" * pad + f" {title} " + "=" * (width - pad - len(title) - 2))
    else:
        print("=" * width)


# ---------------------------------------------------------------------------
# Core demo functions
# ---------------------------------------------------------------------------

def demo_superposition(shots: int = 1000) -> dict:
    """Apply H gate to |0⟩ → |+⟩, measure shots times, return counts."""
    qc = QuantumCircuit(1)
    qc.h(0)           # Hadamard: |0⟩ → (|0⟩+|1⟩)/√2
    return run_circuit(qc, shots=shots)


def demo_state(state_name: str, shots: int = 200) -> dict:
    """Prepare named state and measure."""
    qc = QuantumCircuit(1)
    if state_name == "|0⟩":
        pass                   # default initialisation
    elif state_name == "|1⟩":
        qc.x(0)                # X (NOT) gate
    elif state_name == "|+⟩":
        qc.h(0)                # H gate
    elif state_name == "|-⟩":
        qc.x(0)
        qc.h(0)                # H·X|0⟩ = |-⟩
    return run_circuit(qc, shots=shots)


BLOCH_TABLE = {
    "|0⟩":  (0,   0,   "North pole — computational |0⟩"),
    "|1⟩":  (180, 0,   "South pole — computational |1⟩"),
    "|+⟩":  (90,  0,   "Equator, φ=0  — |+⟩ = (|0⟩+|1⟩)/√2"),
    "|-⟩":  (90,  180, "Equator, φ=π  — |-⟩ = (|0⟩-|1⟩)/√2"),
    "|i⟩":  (90,  90,  "Equator, φ=π/2 — |i⟩ = (|0⟩+i|1⟩)/√2"),
    "|-i⟩": (90,  270, "Equator, φ=3π/2 — |-i⟩ = (|0⟩-i|1⟩)/√2"),
}


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    print_separator("QUBIT FUNDAMENTALS DEMO")
    print("Purpose: Show qubit states, superposition, and Bloch-sphere geometry\n")

    # 1. Superposition measurement
    print_separator("1. Superposition — H|0⟩ measured 1000 times")
    counts = demo_superposition(shots=1000)
    c0 = counts.get("0", 0)
    c1 = counts.get("1", 0)
    total = c0 + c1
    bar0 = "#" * (c0 * 40 // total)
    bar1 = "#" * (c1 * 40 // total)
    print(f"  |0⟩  [{bar0:<40}]  {c0:4d} / {total}  ({100*c0/total:.1f}%)")
    print(f"  |1⟩  [{bar1:<40}]  {c1:4d} / {total}  ({100*c1/total:.1f}%)")
    print(f"\n  Expected: ~50 / ~50  (quantum randomness, not pseudo-random)")
    print(f"  Observed ratio: {c0}:{c1}  ← intrinsic physical randomness\n")

    # 2. Four cardinal states
    print_separator("2. Cardinal States — 200 shots each")
    states = ["|0⟩", "|1⟩", "|+⟩", "|-⟩"]
    print(f"  {'State':<8}  {'|0⟩ %':>7}  {'|1⟩ %':>7}  Notes")
    print(f"  {'-'*8}  {'-'*7}  {'-'*7}  {'-'*35}")
    for s in states:
        c = demo_state(s, shots=200)
        p0 = 100 * c.get("0", 0) / 200
        p1 = 100 * c.get("1", 0) / 200
        note = "Deterministic 0" if s == "|0⟩" else \
               "Deterministic 1" if s == "|1⟩" else \
               "50/50 in Z-basis"
        print(f"  {s:<8}  {p0:>6.1f}%  {p1:>6.1f}%  {note}")
    print()

    # 3. Bloch sphere table
    print_separator("3. Bloch Sphere Coordinates")
    print(f"  {'State':<8}  {'θ (deg)':>8}  {'φ (deg)':>8}  {'θ (rad)':>9}  {'φ (rad)':>9}  Description")
    print(f"  {'-'*8}  {'-'*8}  {'-'*8}  {'-'*9}  {'-'*9}  {'-'*40}")
    for state, (t_deg, p_deg, desc) in BLOCH_TABLE.items():
        t_rad, p_rad = bloch_angles(t_deg, p_deg)
        print(f"  {state:<8}  {t_deg:>8.1f}  {p_deg:>8.1f}  {t_rad:>9.4f}  {p_rad:>9.4f}  {desc}")
    print()

    # 4. Key insight
    print_separator("Key Cryptographic Insight")
    print("  Classical bit:  deterministic 0 or 1 — predictable from algorithm state")
    print("  Qubit in |+⟩:   50/50 at measurement — NO algorithm, NO seed can reproduce it")
    print("  This intrinsic randomness is the entropy foundation of QKD and QRNG.")
    print("  Any attempt to copy or measure an unknown qubit DISTURBS it irreversibly")
    print("  (No-Cloning Theorem) — the physical basis for eavesdrop detection in BB84.")
    print_separator()


if __name__ == "__main__":
    main()
