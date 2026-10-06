"""
CUSTOMER DEMO PITCH — The No-Cloning Theorem
=============================================
The No-Cloning Theorem (Wootters & Zurek 1982) states that it is physically
impossible to create a perfect independent copy of an unknown quantum state.

This is not a limitation of technology — it is a fundamental consequence of the
linearity of quantum mechanics.

Why this matters for cryptography:
  - In BB84 QKD, Alice sends qubits in random bases.  Eve cannot copy those qubits
    and keep one while forwarding the other — the No-Cloning Theorem prevents this.
    Eve MUST measure, which causes an irreversible disturbance visible as elevated QBER.
  - This physical guarantee replaces the computational assumption in classical crypto:
    security does not rest on 'factoring is hard' but on the laws of physics.

Demo:
  We attempt the obvious 'copy' circuit (CNOT with ancilla |0⟩) and measure fidelity
  of the 'clone' vs original for four test states.  Basis states |0⟩ and |1⟩ are
  trivially cloned; superposition states |+⟩ and |R⟩ are NOT.

Audience: Security architects, cryptographers, interview panels.
Runtime: < 10 seconds on Aer simulator.
"""

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, state_fidelity
from qiskit_aer import AerSimulator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_sep(title: str = "") -> None:
    w = 62
    if title:
        p = (w - len(title) - 2) // 2
        print("=" * p + f" {title} " + "=" * (w - p - len(title) - 2))
    else:
        print("=" * w)


def naive_clone_circuit(state_prep: QuantumCircuit) -> QuantumCircuit:
    """
    Naive cloning attempt:
      qubit 0 = original (already prepared)
      qubit 1 = ancilla |0⟩
      CNOT(0→1) 'copies' qubit 0 into qubit 1 — works ONLY for basis states
    """
    qc = QuantumCircuit(2)
    # Compose state prep onto qubit 0 using index-based mapping (avoids
    # Qubit-not-in-circuit error when qargs come from a different register)
    qc.compose(state_prep, qubits=[0], inplace=True)
    qc.cx(0, 1)   # attempt to clone
    return qc


def prepare(name: str) -> QuantumCircuit:
    qc = QuantumCircuit(1)
    if name == "|0⟩":
        pass
    elif name == "|1⟩":
        qc.x(0)
    elif name == "|+⟩":
        qc.h(0)
    elif name == "|R⟩":    # |R⟩ = (|0⟩ + i|1⟩)/√2, S gate after H
        qc.h(0)
        qc.s(0)
    return qc


def ideal_clone_sv(name: str) -> Statevector:
    """The state we WISH the clone qubit to be in (= original)."""
    prep = prepare(name)
    sv = Statevector.from_instruction(prep)
    return sv


def clone_fidelity(name: str) -> float:
    """
    Run the naive CNOT clone circuit, extract the reduced density matrix of
    qubit 1 (the 'clone'), compare to the ideal original state.
    """
    prep = prepare(name)
    qc = naive_clone_circuit(prep)
    full_sv = Statevector.from_instruction(qc)

    # Partial trace: keep qubit 1 (the clone)
    rho_full = np.outer(full_sv.data, full_sv.data.conj())
    # Trace out qubit 0 (index 0 in Qiskit = least-significant)
    rho_1 = np.zeros((2, 2), dtype=complex)
    for i in range(2):
        for j in range(2):
            rho_1 += rho_full[2*i:2*i+2, 2*j:2*j+2] * np.eye(2)[i, j]
    # Wait — correct partial trace: trace over qubit 0
    rho_clone = np.array([
        [rho_full[0, 0] + rho_full[1, 1],   rho_full[0, 2] + rho_full[1, 3]],
        [rho_full[2, 0] + rho_full[3, 1],   rho_full[2, 2] + rho_full[3, 3]],
    ])

    # Fidelity = ⟨ψ|ρ|ψ⟩ where |ψ⟩ is the ideal state
    ideal = ideal_clone_sv(name).data
    fidelity = np.real(ideal.conj() @ rho_clone @ ideal)
    return float(fidelity)


# ---------------------------------------------------------------------------
# QKD disturbance demo
# ---------------------------------------------------------------------------

def qkd_disturbance_demo() -> None:
    """
    Show that measuring an unknown BB84 qubit introduces detectable errors.
    Eve picks a random basis; half the time it is wrong → 50% of those
    forwarded qubits have wrong state → QBER ≈ 25% on Bob's side.
    """
    np.random.seed(42)
    n_bits = 200
    alice_bits  = np.random.randint(0, 2, n_bits)   # 0 or 1
    alice_bases = np.random.randint(0, 2, n_bits)   # 0=Z, 1=X
    eve_bases   = np.random.randint(0, 2, n_bits)   # Eve guesses
    bob_bases   = np.random.randint(0, 2, n_bits)   # Bob also random

    errors = 0
    sifted = 0
    for i in range(n_bits):
        if alice_bases[i] == bob_bases[i]:   # sifted bit
            sifted += 1
            # If Eve guessed wrong basis, she introduces 50% error on this bit
            if eve_bases[i] != alice_bases[i]:
                error_this_bit = np.random.randint(0, 2)   # 50% chance
                if error_this_bit:
                    errors += 1

    qber = errors / sifted if sifted else 0.0
    return qber, sifted, errors


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    print_sep("NO-CLONING THEOREM DEMO")
    print("Purpose: Show why copying qubits is impossible for superposition states\n")

    test_states = ["|0⟩", "|1⟩", "|+⟩", "|R⟩"]

    print_sep("Fidelity of CNOT-based 'Clone' vs Ideal Original")
    print(f"  A CNOT with ancilla |0⟩ is the natural 'copy' attempt.")
    print(f"  Fidelity = 1.0 → perfect copy;  Fidelity < 1.0 → imperfect clone\n")
    print(f"  {'State':<8}  {'Fidelity':>10}  {'Verdict':>35}  Notes")
    print(f"  {'-'*8}  {'-'*10}  {'-'*35}  {'-'*30}")

    for name in test_states:
        fid = clone_fidelity(name)
        if fid > 0.999:
            verdict = "PERFECT CLONE  (basis state)"
            note    = "CNOT works for |0⟩,|1⟩ only"
        elif fid > 0.85:
            verdict = "PARTIAL CLONE  (degraded)"
            note    = "Information destroyed"
        else:
            verdict = "FAILED CLONE   (no-cloning)"
            note    = "Superposition cannot be copied"
        print(f"  {name:<8}  {fid:>10.4f}  {verdict:>35}  {note}")

    print()
    print_sep("QKD Eavesdrop Detection via No-Cloning")
    qber, sifted, errors = qkd_disturbance_demo()
    print(f"  Simulation: 200 BB84 qubits, Eve intercepts all, measures random basis")
    print(f"  Sifted bits (Alice & Bob same basis): {sifted}")
    print(f"  Errors introduced by Eve:             {errors}  ({100*qber:.1f}% QBER)")
    print(f"  Threshold for aborting session:        11% QBER  (BB84 security bound)")
    verdict2 = "SESSION ABORTED — Eve detected!" if qber > 0.11 else "Low traffic, session continues"
    print(f"  Verdict:                               {verdict2}\n")

    print_sep("Summary — Why No-Cloning Secures QKD")
    print("""
  Basis state |0⟩ or |1⟩:
    CNOT clone gives fidelity = 1.0 — trivially copyable.
    BUT Alice never sends known basis states alone; bases are secret.

  Superposition |+⟩ or |R⟩ (diagonal/circular bases):
    CNOT clone gives fidelity ≈ 0.5 — clone is maximally mixed, useless.
    Eve must MEASURE, destroying the superposition → error rate ~25%.

  Physical security guarantee:
    Eve cannot intercept-measure-retransmit without leaving a 25% QBER
    fingerprint.  This is guaranteed by quantum mechanics, NOT key length.
    Classical crypto: "breaking RSA-2048 costs 2^112 operations."
    QKD no-cloning:   "Eve CANNOT avoid disturbing the channel."
""")
    print_sep()


if __name__ == "__main__":
    main()
