"""
Measurement-Based Feedback Control
====================================
Simulates mid-circuit measurement and real-time classical feedforward.

Implements the quantum teleportation protocol as a showcase of
measurement-based feedback:

1. Prepare Bell pair (|Φ+⟩) between qubits 1 and 2
2. Bell measurement on input qubit 0 + qubit 1
3. Classical feedforward:
   - If M_z = 1: apply Z to qubit 2
   - If M_x = 1: apply X to qubit 2
4. Qubit 2 now holds the teleported state

Compares:
  - With feedback: fidelity → 1
  - Without feedback: mixed state, fidelity = 0.5

Saves results to data/feedback_results.json.
"""

import json
import numpy as np
from pathlib import Path


# ---------------------------------------------------------------------------
# Qubit state representations
# ---------------------------------------------------------------------------

I2 = np.eye(2, dtype=complex)
X  = np.array([[0, 1], [1, 0]], dtype=complex)
Y  = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z  = np.array([[1, 0], [0, -1]], dtype=complex)
H_gate = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)

def kron3(A, B, C):
    return np.kron(np.kron(A, B), C)


# ---------------------------------------------------------------------------
# 3-qubit state vector teleportation circuit
# ---------------------------------------------------------------------------

def prepare_initial_state(theta: float, phi: float) -> np.ndarray:
    """
    Prepare qubit 0 in state |ψ⟩ = cos(θ/2)|0⟩ + e^{iφ} sin(θ/2)|1⟩.
    Qubits 1,2 in |00⟩.
    Full state: |ψ⟩ ⊗ |00⟩.
    """
    psi = np.array([np.cos(theta / 2), np.exp(1j * phi) * np.sin(theta / 2)], dtype=complex)
    zero = np.array([1.0, 0.0], dtype=complex)
    return np.kron(np.kron(psi, zero), zero)


def apply_cnot(state: np.ndarray, control: int, target: int, n: int = 3) -> np.ndarray:
    """Apply CNOT gate between control and target qubit."""
    dim = 2 ** n
    new_state = np.zeros(dim, dtype=complex)
    for k in range(dim):
        bits = [(k >> (n - 1 - q)) & 1 for q in range(n)]
        if bits[control] == 1:
            bits[target] ^= 1
        new_k = sum(bits[q] << (n - 1 - q) for q in range(n))
        new_state[new_k] += state[k]
    return new_state


def apply_single(state: np.ndarray, gate: np.ndarray,
                 qubit: int, n: int = 3) -> np.ndarray:
    """Apply a single-qubit gate to the specified qubit in an n-qubit state."""
    ops = [gate if q == qubit else I2 for q in range(n)]
    op = ops[0]
    for o in ops[1:]:
        op = np.kron(op, o)
    return op @ state


def measure_qubit(state: np.ndarray, qubit: int,
                  n: int = 3, rng=None) -> tuple:
    """
    Projective measurement of `qubit` in the Z basis.
    Returns (outcome {0,1}, post-measurement state normalized).
    """
    if rng is None:
        rng = np.random.default_rng(42)
    dim = 2 ** n
    prob_0 = 0.0
    for k in range(dim):
        bit = (k >> (n - 1 - qubit)) & 1
        if bit == 0:
            prob_0 += abs(state[k]) ** 2

    outcome = 0 if rng.random() < prob_0 else 1

    # Project
    new_state = np.zeros(dim, dtype=complex)
    for k in range(dim):
        bit = (k >> (n - 1 - qubit)) & 1
        if bit == outcome:
            new_state[k] = state[k]

    norm = np.linalg.norm(new_state)
    if norm > 1e-10:
        new_state /= norm
    return outcome, new_state


# ---------------------------------------------------------------------------
# Teleportation protocol
# ---------------------------------------------------------------------------

def teleport_with_feedback(theta: float, phi: float,
                            n_shots: int = 500, seed: int = 42) -> dict:
    """
    Run teleportation with classical feedforward for n_shots and compute
    average fidelity of the output state.
    """
    rng = np.random.default_rng(seed)
    fidelities = []

    # Target state |ψ⟩
    psi_target = np.array([np.cos(theta / 2),
                            np.exp(1j * phi) * np.sin(theta / 2)], dtype=complex)

    for _ in range(n_shots):
        # Step 1: Initialize |ψ⟩ ⊗ |00⟩
        state = prepare_initial_state(theta, phi)

        # Step 2: Create Bell pair on qubits 1,2: H on 1, CNOT(1→2)
        state = apply_single(state, H_gate, qubit=1)
        state = apply_cnot(state, control=1, target=2)

        # Step 3: Bell measurement on qubits 0,1
        # Apply CNOT(0→1), then H on 0
        state = apply_cnot(state, control=0, target=1)
        state = apply_single(state, H_gate, qubit=0)

        # Measure qubit 0 (m_z) and qubit 1 (m_x)
        m_z, state = measure_qubit(state, qubit=0, rng=rng)
        m_x, state = measure_qubit(state, qubit=1, rng=rng)

        # Step 4: Feedforward corrections on qubit 2
        if m_x == 1:
            state = apply_single(state, X, qubit=2)
        if m_z == 1:
            state = apply_single(state, Z, qubit=2)

        # Extract qubit 2 state.
        # After measuring qubits 0 and 1, the 3-qubit state has the form
        # |m_z, m_x⟩ ⊗ |ψ'⟩.  The amplitudes for qubit 2 are at indices
        # where bits (2-0) = m_z and (2-1) = m_x in our n=3, MSB-first encoding.
        # In our n=3 encoding: index k → bit q = (k >> (n-1-q)) & 1
        # qubit0=m_z, qubit1=m_x → base = m_z*4 + m_x*2
        base = m_z * 4 + m_x * 2
        amp0 = state[base]       # qubit2 = 0
        amp1 = state[base + 1]   # qubit2 = 1
        psi_out = np.array([amp0, amp1], dtype=complex)
        norm = np.linalg.norm(psi_out)
        if norm > 1e-10:
            psi_out /= norm

        fid = abs(np.dot(psi_target.conj(), psi_out)) ** 2
        fidelities.append(float(fid))

    return {
        "fidelities": fidelities,
        "mean_fidelity": float(np.mean(fidelities)),
        "std_fidelity": float(np.std(fidelities)),
    }


def teleport_without_feedback(theta: float, phi: float,
                               n_shots: int = 500, seed: int = 42) -> dict:
    """
    Run teleportation WITHOUT feedforward — qubit 2 remains mixed.
    Average fidelity ≈ 0.5 (classical limit).
    """
    rng = np.random.default_rng(seed)
    fidelities = []
    psi_target = np.array([np.cos(theta / 2),
                            np.exp(1j * phi) * np.sin(theta / 2)], dtype=complex)

    for _ in range(n_shots):
        state = prepare_initial_state(theta, phi)
        state = apply_single(state, H_gate, qubit=1)
        state = apply_cnot(state, control=1, target=2)
        state = apply_cnot(state, control=0, target=1)
        state = apply_single(state, H_gate, qubit=0)

        m_z, state = measure_qubit(state, qubit=0, rng=rng)
        m_x, state = measure_qubit(state, qubit=1, rng=rng)

        # NO feedforward — extract raw qubit 2 state
        base = m_z * 4 + m_x * 2
        amp0 = state[base]
        amp1 = state[base + 1]
        psi_out = np.array([amp0, amp1], dtype=complex)
        norm = np.linalg.norm(psi_out)
        if norm > 1e-10:
            psi_out /= norm

        fid = abs(np.dot(psi_target.conj(), psi_out)) ** 2
        fidelities.append(float(fid))

    return {
        "fidelities": fidelities,
        "mean_fidelity": float(np.mean(fidelities)),
        "std_fidelity": float(np.std(fidelities)),
    }


# ---------------------------------------------------------------------------
# Multiple input states
# ---------------------------------------------------------------------------

TEST_STATES = [
    {"name": "|+⟩",     "theta": np.pi/2, "phi": 0.0},
    {"name": "|0⟩",     "theta": 0.0,     "phi": 0.0},
    {"name": "|1⟩",     "theta": np.pi,   "phi": 0.0},
    {"name": "|y+⟩",    "theta": np.pi/2, "phi": np.pi/2},
    {"name": "general", "theta": np.pi/3, "phi": np.pi/4},
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Measurement-Based Feedback — Quantum Teleportation")
    print("=" * 60)

    n_shots = 300
    feedback_latency_ns = 100.0  # realistic classical feedback latency

    print(f"\nShots per state : {n_shots}")
    print(f"Feedback latency: {feedback_latency_ns} ns")
    print(f"\n{'State':>10} | {'With FB':>10} | {'Without FB':>12} | {'Gain':>8}")
    print("-" * 50)

    all_results = []
    for s in TEST_STATES:
        with_fb = teleport_with_feedback(s["theta"], s["phi"], n_shots=n_shots)
        without_fb = teleport_without_feedback(s["theta"], s["phi"], n_shots=n_shots)
        gain = with_fb["mean_fidelity"] - without_fb["mean_fidelity"]

        print(f"{s['name']:>10} | {with_fb['mean_fidelity']:>10.4f} | "
              f"{without_fb['mean_fidelity']:>12.4f} | {gain:>8.4f}")

        all_results.append({
            "state_name": s["name"],
            "theta": s["theta"],
            "phi": s["phi"],
            "fidelity_with_feedback": round(with_fb["mean_fidelity"], 6),
            "fidelity_without_feedback": round(without_fb["mean_fidelity"], 6),
            "fidelity_gain": round(gain, 6),
        })

    # Summary
    mean_with = np.mean([r["fidelity_with_feedback"] for r in all_results])
    mean_without = np.mean([r["fidelity_without_feedback"] for r in all_results])
    print(f"\nAverage with feedback   : {mean_with:.4f}")
    print(f"Average without feedback: {mean_without:.4f}")
    print(f"Classical bound (no FB) : ~0.5 (mixed state)")

    results = {
        "protocol": "Quantum teleportation with Bell measurement + classical feedforward",
        "fidelity_with_feedback": round(mean_with, 6),
        "fidelity_without_feedback": round(mean_without, 6),
        "feedback_latency_ns": feedback_latency_ns,
        "n_shots": n_shots,
        "test_states": all_results,
        "protocol_steps": [
            "1. Initialize |ψ⟩⊗|00⟩",
            "2. Create Bell pair on qubits 1,2 (H + CNOT)",
            "3. Bell measurement: CNOT(0→1), H(0), measure 0 and 1",
            "4. Classical communication of 2 bits to receiver",
            "5. Feedforward: apply X if m_x=1, apply Z if m_z=1",
            "6. Qubit 2 holds teleported state |ψ⟩",
        ],
    }

    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "feedback_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {out_path}")
    print("\nFeedback control simulation complete.")


if __name__ == "__main__":
    main()
