"""
QC-17: Grover's Algorithm on AES
Quantum key search reduces AES security by half the key size.

stdlib + numpy only. Run directly to see results.
Exports run_scenario() -> dict.
"""

import math
import time
import os
import importlib.util
import numpy as np

_EXISTING_GROVERS = "/mnt/deepa/quantum/qc-crypto-lab/module1-foundations/src/grovers_algorithm.py"


def _load_existing_grovers():
    if os.path.exists(_EXISTING_GROVERS):
        spec = importlib.util.spec_from_file_location("grovers_existing", _EXISTING_GROVERS)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


# ---------------------------------------------------------------------------
# Grover's iteration count
# ---------------------------------------------------------------------------

def grover_iterations(key_bits: int) -> float:
    """
    Optimal Grover iterations: π/4 × √(2^k) for k-bit key space.
    Assumes single marked item.
    """
    return (math.pi / 4) * math.sqrt(2 ** key_bits)


def quantum_security_bits(key_bits: int) -> int:
    """After Grover's: effective security = key_bits / 2."""
    return key_bits // 2


# ---------------------------------------------------------------------------
# AES oracle (conceptual description)
# ---------------------------------------------------------------------------

AES_ORACLE_DESCRIPTION = """
AES Grover Oracle Construction (Grassl et al. 2016):
1. Reversible AES circuit: implement AES_key(plaintext) as unitary U_AES
2. Oracle marks states where AES_key(P) = C (known P,C pair)
3. Grover diffusion amplifies amplitude of correct key
4. Repeat π/4 × √(2^k) times
5. Measure → correct key with high probability

Key insight: AES must be implemented as a reversible (unitary) quantum circuit.
This requires ancilla qubits to store intermediate values without discarding them.
Grassl et al. (2016) estimate 2953 qubits for AES-128 using T-gate optimized circuits.
"""


# ---------------------------------------------------------------------------
# AES quantum resource table (Grassl et al. 2016)
# ---------------------------------------------------------------------------

AES_ATTACK_TABLE = [
    {
        "variant": "AES-128",
        "key_bits": 128,
        "classical_ops": "2¹²⁸",
        "grover_ops": "2⁶⁴",
        "qubits": 2953,
        "time_at_1mhz": "~10¹⁹ years",
        "quantum_security_bits": 64,
        "assessment": "Requires 64-bit quantum security — below NIST 128-bit threshold",
        "nist_recommendation": "Use AES-256 for post-quantum; AES-128 gives only 64-bit quantum security",
    },
    {
        "variant": "AES-192",
        "key_bits": 192,
        "classical_ops": "2¹⁹²",
        "grover_ops": "2⁹⁶",
        "qubits": 4449,
        "time_at_1mhz": "~10²⁸ years",
        "quantum_security_bits": 96,
        "assessment": "96-bit quantum security — borderline",
        "nist_recommendation": "Acceptable but AES-256 preferred",
    },
    {
        "variant": "AES-256",
        "key_bits": 256,
        "classical_ops": "2²⁵⁶",
        "grover_ops": "2¹²⁸",
        "qubits": 6681,
        "time_at_1mhz": "~10³⁸ years",
        "quantum_security_bits": 128,
        "assessment": "128-bit quantum security — QUANTUM SAFE",
        "nist_recommendation": "Recommended for post-quantum symmetric encryption",
    },
    {
        "variant": "3DES",
        "key_bits": 112,    # effective 3DES security
        "classical_ops": "2¹¹²",
        "grover_ops": "2⁵⁶",
        "qubits": 2503,
        "time_at_1mhz": "~decades",
        "quantum_security_bits": 56,
        "assessment": "56-bit quantum security — PRACTICALLY BREAKABLE on CRQC",
        "nist_recommendation": "DEPRECATED. Use AES-256.",
    },
]


# ---------------------------------------------------------------------------
# Simulated Grover's search (small demo: 4-bit key)
# ---------------------------------------------------------------------------

def grover_search_demo(target_key: int = 11, key_bits: int = 4) -> dict:
    """
    Simulate Grover's algorithm on a 4-bit key space.
    State vector simulation with amplitude amplification.
    """
    N = 2 ** key_bits
    # Initial uniform superposition
    amplitudes = np.ones(N, dtype=complex) / math.sqrt(N)

    # Oracle: flip phase of target
    def oracle(amps, target):
        result = amps.copy()
        result[target] *= -1
        return result

    # Grover diffusion: 2|ψ⟩⟨ψ| - I
    def diffusion(amps):
        mean_amp = np.mean(amps)
        return 2 * mean_amp - amps

    n_iters = max(1, round(math.pi / 4 * math.sqrt(N)))
    for _ in range(n_iters):
        amplitudes = oracle(amplitudes, target_key)
        amplitudes = diffusion(amplitudes)

    probs = np.abs(amplitudes) ** 2
    measured = int(np.argmax(probs))
    success_prob = float(probs[target_key])

    return {
        "key_bits": key_bits,
        "N": N,
        "target_key": target_key,
        "grover_iterations": n_iters,
        "measured_key": measured,
        "success_probability": round(success_prob, 4),
        "correct": measured == target_key,
    }


# ---------------------------------------------------------------------------
# run_scenario
# ---------------------------------------------------------------------------

def run_scenario() -> dict:
    t0 = time.perf_counter()

    existing_mod = _load_existing_grovers()
    demo = grover_search_demo(target_key=11, key_bits=4)

    # Compute iteration counts for AES key sizes
    grover_iters = {
        "AES-128": f"π/4 × 2⁶⁴ ≈ {(math.pi/4):.4f} × 2⁶⁴ iterations",
        "AES-192": f"π/4 × 2⁹⁶",
        "AES-256": f"π/4 × 2¹²⁸",
    }

    result = {
        "scenario": "QC-17",
        "name": "Grover's Algorithm on AES",
        "category": "Attack",
        "existing_module_found": os.path.exists(_EXISTING_GROVERS),
        "grover_demo_4bit": demo,
        "aes_oracle_description": AES_ORACLE_DESCRIPTION.strip(),
        "aes_attack_table": AES_ATTACK_TABLE,
        "grover_iterations_formula": grover_iters,
        "conclusion": (
            "AES-256 is quantum-safe (128-bit quantum security). "
            "AES-128 provides only 64-bit quantum security — below NIST threshold. "
            "3DES: ~56-bit Grover security — practically breakable on a CRQC. "
            "Recommendation: migrate all AES-128 → AES-256; deprecate 3DES immediately."
        ),
        "reference": "Grassl, M. et al. (2016). Applying Grover's algorithm to AES. PQCrypto 2016.",
        "elapsed_s": round(time.perf_counter() - t0, 4),
    }
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    res = run_scenario()
    print("=" * 60)
    print(f"QC-17: {res['name']}")
    print("=" * 60)
    print(f"Existing grovers_algorithm.py found: {res['existing_module_found']}")
    print()
    d = res["grover_demo_4bit"]
    print(f"Demo Grover search ({d['key_bits']}-bit key space, N={d['N']}):")
    print(f"  Target key: {d['target_key']}")
    print(f"  Iterations: {d['grover_iterations']}")
    print(f"  Measured:   {d['measured_key']}  {'✓' if d['correct'] else '✗'}")
    print(f"  Success probability: {d['success_probability']:.4f}")
    print()
    print("AES Quantum Attack Table (Grassl et al. 2016):")
    hdr = f"  {'Variant':<10} {'Key bits':>8} {'Grover ops':>12} {'Qubits':>8} {'Q-Security':>12}  Assessment"
    print(hdr)
    print("  " + "-" * 80)
    for row in res["aes_attack_table"]:
        print(f"  {row['variant']:<10} {row['key_bits']:>8} {row['grover_ops']:>12} "
              f"{row['qubits']:>8} {row['quantum_security_bits']:>10}b  {row['assessment']}")
    print()
    print(f"Conclusion: {res['conclusion']}")
    print(f"Reference: {res['reference']}")
    print(f"Elapsed: {res['elapsed_s']}s")
