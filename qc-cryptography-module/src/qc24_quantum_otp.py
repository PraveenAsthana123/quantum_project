"""
QC-24: Quantum One-Time Pad (QOTP)
Encrypt quantum states using random Pauli operators.

stdlib + numpy only. Run directly to see results.
Exports run_scenario() -> dict.
"""

import math
import time
import numpy as np
import hashlib


# ---------------------------------------------------------------------------
# Pauli operators
# ---------------------------------------------------------------------------

I2 = np.eye(2, dtype=complex)
X  = np.array([[0, 1], [1, 0]], dtype=complex)
Y  = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z  = np.array([[1, 0], [0, -1]], dtype=complex)
PAULIS = [I2, X, Y, Z]
PAULI_NAMES = ["I", "X", "Y", "Z"]


def tensor(*ops) -> np.ndarray:
    result = ops[0]
    for op in ops[1:]:
        result = np.kron(result, op)
    return result


# ---------------------------------------------------------------------------
# Single-qubit state as density matrix
# ---------------------------------------------------------------------------

def ket_to_dm(ket: np.ndarray) -> np.ndarray:
    """Convert ket |ψ⟩ to density matrix ρ = |ψ⟩⟨ψ|."""
    return np.outer(ket, ket.conj())


def mixed_state(n_qubits: int = 1) -> np.ndarray:
    """Completely mixed state ρ = I/2^n."""
    d = 2 ** n_qubits
    return np.eye(d, dtype=complex) / d


# ---------------------------------------------------------------------------
# QOTP encryption / decryption (n-qubit)
# ---------------------------------------------------------------------------

def qotp_encrypt(rho: np.ndarray, key_ab: list[tuple[int, int]]) -> np.ndarray:
    """
    Quantum OTP: E(ρ) = Σ_{a,b} p_{a,b} (X^a Z^b) ρ (X^a Z^b)†
    With uniform key (a,b) ∈ {0,1}^2 for each qubit:
    E(ρ) = I/2^n (completely mixed state — perfect security).

    key_ab: list of (a, b) pairs — one per qubit.
    """
    n = len(key_ab)
    # Build n-qubit Pauli operator from key
    ops = []
    for a, b in key_ab:
        # X^a Z^b
        op = np.linalg.matrix_power(X.copy().astype(complex), a % 2) @ \
             np.linalg.matrix_power(Z.copy().astype(complex), b % 2)
        ops.append(op)
    # Tensor product of all single-qubit operators
    U = ops[0]
    for op in ops[1:]:
        U = np.kron(U, op)
    # Encrypt: E(ρ) = U ρ U†
    encrypted = U @ rho @ U.conj().T
    return encrypted


def qotp_decrypt(encrypted_rho: np.ndarray, key_ab: list[tuple[int, int]]) -> np.ndarray:
    """Decrypt using same key (Pauli operators are self-inverse for XZ: (XZ)†=ZX→need careful order)."""
    n = len(key_ab)
    ops = []
    for a, b in key_ab:
        op = np.linalg.matrix_power(X.copy().astype(complex), a % 2) @ \
             np.linalg.matrix_power(Z.copy().astype(complex), b % 2)
        # Inverse = conjugate transpose
        ops.append(op.conj().T)
    U_inv = ops[0]
    for op in ops[1:]:
        U_inv = np.kron(U_inv, op)
    return U_inv @ encrypted_rho @ U_inv.conj().T


def generate_quantum_otp_key(n_qubits: int, rng: np.random.Generator) -> list[tuple[int, int]]:
    """Random (a,b) key pairs for QOTP."""
    return [(int(rng.integers(0, 2)), int(rng.integers(0, 2))) for _ in range(n_qubits)]


# ---------------------------------------------------------------------------
# Uniformity verification: uniform key → completely mixed state
# ---------------------------------------------------------------------------

def verify_qotp_security(rho: np.ndarray, n_qubits: int = 1) -> dict:
    """
    Show that averaging over all Pauli keys gives the completely mixed state.
    For 1 qubit: (1/4) Σ_{a,b} X^a Z^b ρ (X^a Z^b)† = I/2
    """
    d = 2 ** n_qubits
    avg = np.zeros((d, d), dtype=complex)
    count = 0
    for a in range(2):
        for b in range(2):
            key = [(a, b)] * n_qubits
            enc = qotp_encrypt(rho, key)
            avg += enc
            count += 1
    avg /= count
    ideal_mixed = np.eye(d, dtype=complex) / d
    max_diff = float(np.max(np.abs(avg - ideal_mixed)))
    return {
        "average_encrypted_state": avg.tolist(),
        "ideal_mixed_state": ideal_mixed.tolist(),
        "max_deviation": round(max_diff, 12),
        "is_perfectly_mixed": max_diff < 1e-10,
    }


# ---------------------------------------------------------------------------
# BB84 + OTP combination
# ---------------------------------------------------------------------------

def bb84_otp_demo(n_bits: int = 16, seed: int = 42) -> dict:
    """
    BB84 distributes OTP key, then use for classical message encryption.
    Key reuse: forbidden (OTP security requires one key per message).
    """
    rng = np.random.default_rng(seed)
    # QKD distributes key (simulated)
    key_bits = rng.integers(0, 2, size=n_bits).tolist()
    # Message
    message_bits = rng.integers(0, 2, size=n_bits).tolist()
    # Classical OTP: ciphertext = message XOR key
    ciphertext = [int(m ^ k) for m, k in zip(message_bits, key_bits)]
    # Decryption
    decrypted = [int(c ^ k) for c, k in zip(ciphertext, key_bits)]
    return {
        "key_bits": key_bits,
        "message_bits": message_bits,
        "ciphertext": ciphertext,
        "decrypted": decrypted,
        "correct": decrypted == message_bits,
        "otp_property": "Key used once; ciphertext is statistically independent of message",
    }


# ---------------------------------------------------------------------------
# 4-qubit QOTP demo
# ---------------------------------------------------------------------------

def qotp_4qubit_demo(seed: int = 42) -> dict:
    """Encrypt and decrypt a 4-qubit state using QOTP."""
    rng = np.random.default_rng(seed)
    n_qubits = 4
    d = 2 ** n_qubits  # 16

    # Prepare a non-trivial 4-qubit state: tensor of |+⟩^⊗4
    ket_plus = np.array([1.0, 1.0], dtype=complex) / math.sqrt(2)
    ket_4 = ket_plus
    for _ in range(n_qubits - 1):
        ket_4 = np.kron(ket_4, ket_plus)
    rho_orig = np.outer(ket_4, ket_4.conj())

    # Generate random QOTP key
    key = generate_quantum_otp_key(n_qubits, rng)

    # Encrypt
    rho_enc = qotp_encrypt(rho_orig, key)

    # Decrypt
    rho_dec = qotp_decrypt(rho_enc, key)

    # Check: decrypted should match original (up to floating point)
    max_diff = float(np.max(np.abs(rho_dec - rho_orig)))

    # Check encrypted state: should be close to mixed if key is "random"
    enc_trace = float(np.real(np.trace(rho_enc)))

    security = verify_qotp_security(rho_orig[:2, :2], n_qubits=1)  # 1-qubit check

    return {
        "n_qubits": n_qubits,
        "key_used": key,
        "key_str": "".join(f"X^{a}Z^{b}" for a, b in key),
        "encrypt_decrypt_fidelity": round(1.0 - max_diff, 8),
        "encrypted_trace": round(enc_trace, 6),
        "decrypt_correct": max_diff < 1e-10,
        "security_verification": security,
    }


# ---------------------------------------------------------------------------
# OTP comparison table
# ---------------------------------------------------------------------------

OTP_COMPARISON = [
    {
        "scheme": "Classical OTP",
        "key_reuse": "No (security breaks)",
        "security": "Perfect (Shannon 1949)",
        "key_distribution": "Courier / pre-share",
    },
    {
        "scheme": "AES-256",
        "key_reuse": "Yes (safe up to 2^68 blocks)",
        "security": "Computational (128-bit post-quantum)",
        "key_distribution": "Easy (any channel)",
    },
    {
        "scheme": "Quantum OTP",
        "key_reuse": "No",
        "security": "Perfect (info-theoretic for quantum states)",
        "key_distribution": "QKD or pre-shared quantum key",
    },
    {
        "scheme": "BB84 + OTP",
        "key_reuse": "No",
        "security": "Perfect (provable, information-theoretic)",
        "key_distribution": "QKD distributes OTP key",
    },
]


# ---------------------------------------------------------------------------
# run_scenario
# ---------------------------------------------------------------------------

def run_scenario() -> dict:
    t0 = time.perf_counter()

    qotp_4q = qotp_4qubit_demo(seed=42)
    bb84_demo = bb84_otp_demo(n_bits=16, seed=42)

    # Security proof sketch
    security_proof = {
        "classical_shannon": (
            "Shannon (1949): OTP is perfectly secret iff key is uniformly random, "
            "same length as message, used only once. I(M;C) = 0."
        ),
        "quantum_otp": (
            "Quantum OTP (Boykin & Roychowdhury 2003): "
            "For uniform key (a,b), Σ_{a,b} (X^a Z^b) ρ (X^a Z^b)† / 4 = I/2 "
            "(completely mixed state). Eve sees I/2 regardless of ρ. "
            "Information-theoretic security: I(ρ; encrypted) = 0."
        ),
        "pauli_group_property": (
            "The single-qubit Pauli group {I, X, Y, Z} forms an error basis. "
            "Uniform distribution over Paulis depolarizes any qubit to I/2. "
            "For n qubits: requires 2n bits of key (a_1,b_1,...,a_n,b_n)."
        ),
    }

    result = {
        "scenario": "QC-24",
        "name": "Quantum One-Time Pad (QOTP)",
        "category": "Primitive",
        "qotp_4qubit_demo": qotp_4q,
        "bb84_otp_demo": bb84_demo,
        "security_proof": security_proof,
        "otp_comparison": OTP_COMPARISON,
        "key_insight": (
            "Classical OTP: C = M XOR K — perfectly secret but key distribution hard. "
            "Quantum OTP: E(ρ) = X^a Z^b ρ (X^a Z^b)† — encrypts quantum states. "
            "With uniform key, encrypted state = I/2 (completely mixed) — "
            "Eve learns nothing, regardless of her quantum computing power. "
            "BB84 + OTP: QKD distributes the OTP key securely → combined perfect secrecy."
        ),
        "elapsed_s": round(time.perf_counter() - t0, 4),
    }
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    res = run_scenario()
    print("=" * 60)
    print(f"QC-24: {res['name']}")
    print("=" * 60)
    print()
    d = res["qotp_4qubit_demo"]
    print(f"4-qubit QOTP demo:")
    print(f"  Key applied: {d['key_str']}")
    print(f"  Decrypt fidelity: {d['encrypt_decrypt_fidelity']:.8f}")
    print(f"  Decrypt correct:  {'✓' if d['decrypt_correct'] else '✗'}")
    sec = d["security_verification"]
    print(f"  Security check: average encryption = I/2 "
          f"(max deviation={sec['max_deviation']:.2e}, "
          f"perfectly_mixed={sec['is_perfectly_mixed']})")
    print()
    b = res["bb84_otp_demo"]
    print(f"BB84 + OTP demo ({len(b['key_bits'])}-bit):")
    print(f"  Message:     {b['message_bits']}")
    print(f"  Key:         {b['key_bits']}")
    print(f"  Ciphertext:  {b['ciphertext']}")
    print(f"  Decrypted:   {b['decrypted']}  {'✓' if b['correct'] else '✗'}")
    print()
    print("OTP Comparison:")
    hdr = f"  {'Scheme':<20} {'Key reuse':<16} {'Security':<40}  Key distribution"
    print(hdr)
    print("  " + "-" * 95)
    for row in res["otp_comparison"]:
        print(f"  {row['scheme']:<20} {row['key_reuse']:<16} {row['security']:<40}  {row['key_distribution']}")
    print()
    print(f"Key insight: {res['key_insight']}")
    print(f"Elapsed: {res['elapsed_s']}s")
