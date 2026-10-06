"""
QC-15: Shor's Algorithm on RSA
Quantum period-finding breaks integer factoring → breaks RSA.

stdlib + numpy only. Run directly to see results.
Exports run_scenario() -> dict.
"""

import math
import time
import random
import numpy as np

# Check for existing shors_algorithm.py in qc-crypto-lab
import importlib.util, sys, os

_EXISTING_SHORS = "/mnt/deepa/quantum/qc-crypto-lab/module1-foundations/src/shors_algorithm.py"


def _load_existing_shors():
    if os.path.exists(_EXISTING_SHORS):
        spec = importlib.util.spec_from_file_location("shors_existing", _EXISTING_SHORS)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


# ---------------------------------------------------------------------------
# Classical factoring methods
# ---------------------------------------------------------------------------

def trial_division(n: int) -> tuple[int, int] | None:
    """Factor n by trial division. Returns (p, q) or None."""
    if n % 2 == 0:
        return (2, n // 2)
    i = 3
    while i * i <= n:
        if n % i == 0:
            return (i, n // i)
        i += 2
    return None


def pollard_rho(n: int, seed: int = 2) -> int:
    """Pollard's rho algorithm. Returns a non-trivial factor."""
    if n % 2 == 0:
        return 2
    x = seed
    y = seed
    c = 1
    d = 1
    while d == 1:
        x = (x * x + c) % n
        y = (y * y + c) % n
        y = (y * y + c) % n
        d = math.gcd(abs(x - y), n)
    return d if d != n else None


# ---------------------------------------------------------------------------
# Simulated quantum period finding (classical simulation of order-finding)
# ---------------------------------------------------------------------------

def quantum_order_finding(a: int, n: int) -> int:
    """
    Classical simulation of quantum order-finding (used in Shor's).
    Finds smallest r > 0 such that a^r ≡ 1 (mod n).
    In a real quantum computer this uses QPE on the unitary U|y⟩ = |ay mod n⟩.
    """
    r = 1
    val = a % n
    while val != 1:
        val = (val * a) % n
        r += 1
        if r > n:
            return 0
    return r


def shors_factor(n: int, max_attempts: int = 20, seed: int = 42) -> tuple[int, int] | None:
    """
    Shor's algorithm (simulated quantum period-finding).
    Returns (p, q) factors of n, or None.
    """
    rng = random.Random(seed)
    if n % 2 == 0:
        return (2, n // 2)
    for _ in range(max_attempts):
        a = rng.randint(2, n - 1)
        g = math.gcd(a, n)
        if g != 1:
            return (g, n // g)
        r = quantum_order_finding(a, n)
        if r == 0 or r % 2 == 1:
            continue
        x = pow(a, r // 2, n)
        if x == n - 1:
            continue
        p = math.gcd(x - 1, n)
        q = math.gcd(x + 1, n)
        if 1 < p < n:
            return (p, n // p)
        if 1 < q < n:
            return (q, n // q)
    return None


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

TEST_CASES = [15, 21, 35, 77, 143, 221]


# ---------------------------------------------------------------------------
# RSA threat matrix (Beauregard circuit: 2n+3 logical qubits)
# ---------------------------------------------------------------------------

RSA_THREAT_MATRIX = [
    {
        "rsa_key_bits": 1024,
        "logical_qubits": 2051,   # 2*1024 + 3
        "gates": "2.1×10¹⁰",
        "time_at_1mhz": "~6 hours",
        "cnsa2_status": "Deprecated now",
    },
    {
        "rsa_key_bits": 2048,
        "logical_qubits": 4099,
        "gates": "1.7×10¹¹",
        "time_at_1mhz": "~55 hours",
        "cnsa2_status": "Replace by 2030",
    },
    {
        "rsa_key_bits": 3072,
        "logical_qubits": 6147,
        "gates": "~10¹²",
        "time_at_1mhz": "~2 weeks",
        "cnsa2_status": "Never new deployments",
    },
    {
        "rsa_key_bits": 4096,
        "logical_qubits": 8195,
        "gates": "~10¹³",
        "time_at_1mhz": "~months",
        "cnsa2_status": "Future use? No.",
    },
]


# ---------------------------------------------------------------------------
# run_scenario
# ---------------------------------------------------------------------------

def run_scenario() -> dict:
    t0 = time.perf_counter()

    existing_module = _load_existing_shors()

    # Factor all test cases
    factoring_results = []
    for n in TEST_CASES:
        shors = shors_factor(n)
        trial = trial_division(n)
        rho_f = pollard_rho(n) if n > 4 else None
        factoring_results.append({
            "N": n,
            "shors_result": shors,
            "trial_division": trial,
            "pollard_rho_factor": rho_f,
            "shors_correct": shors is not None and shors[0] * shors[1] == n,
        })

    result = {
        "scenario": "QC-15",
        "name": "Shor's Algorithm on RSA",
        "category": "Attack",
        "existing_module_found": os.path.exists(_EXISTING_SHORS),
        "factoring_results": factoring_results,
        "rsa_threat_matrix": RSA_THREAT_MATRIX,
        "hndl_analysis": (
            "HNDL (Harvest Now Decrypt Later): Data encrypted with RSA-2048 today "
            "will be decryptable on a CRQC (Cryptographically Relevant Quantum Computer). "
            "Best estimate: CRQC capable of breaking RSA-2048 available by ~2030–2035. "
            "All sensitive data with >10-year confidentiality requirement is at risk NOW."
        ),
        "beauregard_circuit": "Requires 2n+3 logical qubits for n-bit RSA (Beauregard 2002)",
        "migration": "RSA-2048 → ML-KEM-768 (FIPS 203) + ML-DSA-65 (FIPS 204)",
        "elapsed_s": round(time.perf_counter() - t0, 4),
    }
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    res = run_scenario()
    print("=" * 60)
    print(f"QC-15: {res['name']}")
    print("=" * 60)
    print(f"Existing shors_algorithm.py found: {res['existing_module_found']}")
    if res["existing_module_found"]:
        print(f"  → Loaded from: {_EXISTING_SHORS}")
    print()
    print("Factoring test cases (Shor's + Classical comparison):")
    hdr = f"  {'N':>4}  {'Shor':>10}  {'Trial Div':>10}  {'Pollard-ρ':>10}  OK"
    print(hdr)
    print("  " + "-" * 48)
    for r in res["factoring_results"]:
        shors_str = str(r["shors_result"]) if r["shors_result"] else "None"
        trial_str = str(r["trial_division"]) if r["trial_division"] else "None"
        rho_str = str(r["pollard_rho_factor"]) if r["pollard_rho_factor"] else "None"
        ok = "✓" if r["shors_correct"] else "✗"
        print(f"  {r['N']:>4}  {shors_str:>10}  {trial_str:>10}  {rho_str:>10}  {ok}")
    print()
    print("RSA Threat Matrix (Beauregard circuit, 2n+3 qubits):")
    hdr2 = f"  {'RSA key':>10} {'Logical Q':>10} {'Gates':>14} {'Time@1MHz':>14}  CNSA 2.0"
    print(hdr2)
    print("  " + "-" * 66)
    for row in res["rsa_threat_matrix"]:
        print(f"  {row['rsa_key_bits']:>7}-bit {row['logical_qubits']:>10} "
              f"{row['gates']:>14} {row['time_at_1mhz']:>14}  {row['cnsa2_status']}")
    print()
    print(f"HNDL: {res['hndl_analysis']}")
    print(f"Migration: {res['migration']}")
    print(f"Elapsed: {res['elapsed_s']}s")
