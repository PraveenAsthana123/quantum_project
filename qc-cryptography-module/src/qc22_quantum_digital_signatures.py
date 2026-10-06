"""
QC-22: Quantum Digital Signatures (QDS)
Classical-quantum hybrid signature scheme based on no-cloning theorem.

stdlib + numpy only. Run directly to see results.
Exports run_scenario() -> dict.
"""

import math
import time
import hashlib
import numpy as np


# ---------------------------------------------------------------------------
# Simplified QDS scheme (Gottesman-Chuang 2001 style)
# ---------------------------------------------------------------------------

# Quantum public key: a quantum state |ψ_k⟩ encoding private key k
# No-cloning: cannot copy |ψ_k⟩ → cannot forge signature


class QuantumPublicKey:
    """
    Simplified representation of a quantum public key.
    In reality this is a quantum state (coherent superposition) sent over a quantum channel.
    Here we model it as a measurement outcome sequence.
    """
    def __init__(self, classical_key: int, n_qubits: int = 8, seed: int = 42):
        rng = np.random.default_rng(seed + classical_key)
        self.n_qubits = n_qubits
        self.classical_key = classical_key
        # Each qubit prepared in random basis; measurement outcome is hash of key
        self.basis_choices = rng.integers(0, 2, size=n_qubits).tolist()
        self.state_bits = [(classical_key >> i) & 1 for i in range(n_qubits)]
        # "Public" quantum state: honest measurement outcomes
        self.outcomes = [self.state_bits[i] ^ (1 if self.basis_choices[i] else 0)
                         for i in range(n_qubits)]


def qds_setup(n_recipients: int = 2, key_bits: int = 8, seed: int = 42) -> dict:
    """
    Alice generates quantum public keys for each recipient.
    One signing key per message bit (simplified: 1 key for demo).
    """
    rng = np.random.default_rng(seed)
    private_key = int(rng.integers(0, 2 ** key_bits))
    # Generate quantum public keys (one per recipient)
    qpks = {}
    for i in range(n_recipients):
        qpks[f"recipient_{i}"] = QuantumPublicKey(private_key, n_qubits=key_bits, seed=seed + i)
    return {
        "private_key": private_key,
        "quantum_public_keys": qpks,
        "n_recipients": n_recipients,
        "key_bits": key_bits,
    }


def qds_sign(private_key: int, message: str, key_bits: int = 8) -> dict:
    """
    Alice signs message: sends classical message + measurement results on |ψ_k⟩.
    Signature = private key measurements in chosen bases.
    """
    msg_hash = hashlib.sha256(message.encode()).hexdigest()
    # Simplified: signature = hash(private_key || message)
    sig_material = (private_key.to_bytes(key_bits // 8 + 1, "little") +
                    message.encode())
    signature = hashlib.sha256(sig_material).hexdigest()[:16]
    return {
        "message": message,
        "message_hash": msg_hash[:16] + "...",
        "signature": signature,
        "private_key_used": private_key,
    }


def qds_verify(qpk: QuantumPublicKey, message: str, signature: str,
               private_key_hint: int = None) -> dict:
    """
    Bob verifies signature using his copy of the quantum public key.
    In real QDS: Bob measures his quantum public key and checks consistency.
    """
    # Reconstruct what signature should be (Bob has qpk which encodes private_key)
    pk = qpk.classical_key  # In real QDS, this is derived from quantum measurements
    sig_material = (pk.to_bytes(qpk.n_qubits // 8 + 1, "little") + message.encode())
    expected_sig = hashlib.sha256(sig_material).hexdigest()[:16]
    valid = (signature == expected_sig)
    # No-cloning: Eve cannot copy |ψ_k⟩ to both Bob and Charlie simultaneously
    return {
        "message": message,
        "signature_presented": signature,
        "expected_signature": expected_sig,
        "valid": valid,
        "no_cloning_protection": "Bob's copy of |ψ_k⟩ was distributed privately; Eve cannot forge",
    }


def qds_forge_attempt(qpk: QuantumPublicKey, message: str) -> dict:
    """
    Eve attempts to forge a signature without the private key.
    Demonstrates security based on no-cloning theorem.
    """
    # Eve can measure qpk but gets random outcomes (cannot clone state)
    rng = np.random.default_rng(999)
    # Eve guesses the private key
    guessed_key = int(rng.integers(0, 2 ** qpk.n_qubits))
    sig_material = (guessed_key.to_bytes(qpk.n_qubits // 8 + 1, "little") + message.encode())
    forged_sig = hashlib.sha256(sig_material).hexdigest()[:16]
    return {
        "forged_signature": forged_sig,
        "guess_success": guessed_key == qpk.classical_key,
        "probability_of_correct_guess": f"1/2^{qpk.n_qubits} = {1/2**qpk.n_qubits:.2e}",
        "no_cloning_note": (
            "Eve measures the quantum public key but collapses its state. "
            "Cannot copy it to extract full private key information. "
            "Security: information-theoretic (holds even vs quantum computers)."
        ),
    }


# ---------------------------------------------------------------------------
# RSA vs QDS comparison
# ---------------------------------------------------------------------------

SIGNATURE_COMPARISON = [
    {
        "property": "Security basis",
        "rsa_2048": "Factoring hardness (NP-hard classically)",
        "ecdsa": "ECDLP (NP-hard classically)",
        "qds": "No-cloning theorem (physical law)",
    },
    {
        "property": "Quantum safe",
        "rsa_2048": "No (Shor breaks in ~55h on CRQC)",
        "ecdsa": "No (Shor breaks in ~8h on CRQC)",
        "qds": "Yes (information-theoretic security)",
    },
    {
        "property": "Signature size",
        "rsa_2048": "256 bytes",
        "ecdsa": "64 bytes",
        "qds": "Varies (classical+quantum channel)",
    },
    {
        "property": "Key type",
        "rsa_2048": "Mathematical (integer)",
        "ecdsa": "Mathematical (curve point)",
        "qds": "Quantum state |ψ_k⟩",
    },
    {
        "property": "Hardware required",
        "rsa_2048": "Classical (any CPU)",
        "ecdsa": "Classical (any CPU)",
        "qds": "Quantum channel + detectors",
    },
    {
        "property": "Deployment status",
        "rsa_2048": "Universal",
        "ecdsa": "Universal",
        "qds": "Experimental (NTT, Toshiba labs)",
    },
    {
        "property": "Non-repudiation",
        "rsa_2048": "Yes (with PKI)",
        "ecdsa": "Yes (with PKI)",
        "qds": "Yes (quantum-verified)",
    },
]


# ---------------------------------------------------------------------------
# run_scenario
# ---------------------------------------------------------------------------

def run_scenario() -> dict:
    t0 = time.perf_counter()

    setup = qds_setup(n_recipients=2, key_bits=16, seed=42)
    pk = setup["private_key"]
    qpk_bob = setup["quantum_public_keys"]["recipient_0"]
    qpk_charlie = setup["quantum_public_keys"]["recipient_1"]

    message = "Transfer $10,000 to account 42"
    sig_result = qds_sign(pk, message, key_bits=16)
    bob_verify = qds_verify(qpk_bob, message, sig_result["signature"])
    charlie_verify = qds_verify(qpk_charlie, message, sig_result["signature"])
    eve_forge = qds_forge_attempt(qpk_bob, message)

    result = {
        "scenario": "QC-22",
        "name": "Quantum Digital Signatures (QDS)",
        "category": "Primitive",
        "setup": {
            "private_key_hex": hex(setup["private_key"]),
            "n_recipients": setup["n_recipients"],
            "key_bits": setup["key_bits"],
        },
        "signing": sig_result,
        "bob_verification": bob_verify,
        "charlie_verification": charlie_verify,
        "eve_forgery_attempt": eve_forge,
        "signature_comparison": SIGNATURE_COMPARISON,
        "current_state": (
            "QDS is experimental. NTT and Toshiba demonstrated QDS over 90km fiber (2016). "
            "Not deployed at scale. Practical limitation: requires quantum channel + memory. "
            "For current PQ needs: use ML-DSA (FIPS 204) or SLH-DSA (FIPS 205)."
        ),
        "security_model": "Information-theoretic (unconditional security — no computational assumption)",
        "elapsed_s": round(time.perf_counter() - t0, 4),
    }
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    res = run_scenario()
    print("=" * 60)
    print(f"QC-22: {res['name']}")
    print("=" * 60)
    print(f"Setup: {res['setup']['n_recipients']} recipients, "
          f"{res['setup']['key_bits']}-bit keys")
    print(f"Message: \"{res['signing']['message']}\"")
    print(f"Signature: {res['signing']['signature']}")
    print()
    print(f"Bob verification:     {'✓ VALID' if res['bob_verification']['valid'] else '✗ INVALID'}")
    print(f"Charlie verification: {'✓ VALID' if res['charlie_verification']['valid'] else '✗ INVALID'}")
    print()
    print("Eve's forgery attempt:")
    e = res["eve_forgery_attempt"]
    print(f"  Guessed key correct: {e['guess_success']}")
    print(f"  Success probability: {e['probability_of_correct_guess']}")
    print(f"  Note: {e['no_cloning_note']}")
    print()
    print("Signature Comparison Table:")
    hdr = f"  {'Property':<24} {'RSA-2048':<28} {'ECDSA':<28} QDS"
    print(hdr)
    print("  " + "-" * 90)
    for row in res["signature_comparison"]:
        print(f"  {row['property']:<24} {row['rsa_2048']:<28} {row['ecdsa']:<28} {row['qds']}")
    print()
    print(f"Security: {res['security_model']}")
    print(f"Status: {res['current_state']}")
    print(f"Elapsed: {res['elapsed_s']}s")
