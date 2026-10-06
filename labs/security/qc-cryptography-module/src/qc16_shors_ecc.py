"""
QC-16: Shor's Algorithm on ECC
Quantum algorithm for the Elliptic Curve Discrete Logarithm Problem (ECDLP).

stdlib + numpy only. Run directly to see results.
Exports run_scenario() -> dict.
"""

import math
import time
import numpy as np


# ---------------------------------------------------------------------------
# ECC qubit requirements (Roetteler et al. 2017 + Regev 2024 improvements)
# ---------------------------------------------------------------------------

ECC_THREAT_MATRIX = [
    {
        "curve": "P-192",
        "bits": 192,
        "qubits_roetteler": 1384,
        "gates": "~10¹⁰",
        "time_at_1mhz": "~3 hours",
        "use": "Legacy TLS, ECDSA",
    },
    {
        "curve": "P-256",
        "bits": 256,
        "qubits_roetteler": 2330,
        "gates": "~3×10¹⁰",
        "time_at_1mhz": "~8 hours",
        "use": "TLS 1.3, HTTPS, ECDSA-256",
    },
    {
        "curve": "P-384",
        "bits": 384,
        "qubits_roetteler": 3484,
        "gates": "~10¹¹",
        "time_at_1mhz": "~28 hours",
        "use": "Top-secret NSA Suite B",
    },
    {
        "curve": "P-521",
        "bits": 521,
        "qubits_roetteler": 4719,
        "gates": "~4×10¹¹",
        "time_at_1mhz": "~4 days",
        "use": "High-assurance certificates",
    },
    {
        "curve": "Curve25519",
        "bits": 256,
        "qubits_roetteler": 2330,
        "gates": "~3×10¹⁰",
        "time_at_1mhz": "~8 hours",
        "use": "TLS 1.3 key exchange (X25519)",
    },
]

# Regev 2024: more efficient multi-controlled addition reduces qubits
REGEV_IMPROVEMENT = {
    "description": "Regev (2024) reduces gate complexity for ECDLP by using "
                   "lattice-based multi-controlled Toffoli decomposition, "
                   "cutting circuit depth roughly 2-3x over original Shor's for ECC.",
    "paper": "Regev, O. (2024). An Efficient Quantum Factoring Algorithm. arXiv:2308.06572",
}

RSA_VS_ECC = {
    "RSA-2048": {"qubits": 4099,  "gates": "1.7×10¹¹", "comparison_note": "Same quantum vulnerability class"},
    "ECC-256":  {"qubits": 2330,  "gates": "3×10¹⁰",   "comparison_note": "Fewer qubits than RSA-2048"},
    "note": (
        "ECC uses fewer qubits than RSA for equivalent classical security, "
        "but both are equally broken by a CRQC. ECC-256 ≈ RSA-3072 classically, "
        "yet requires fewer quantum resources to break."
    ),
}


# ---------------------------------------------------------------------------
# Simplified ECDLP simulator (small curve for demo)
# ---------------------------------------------------------------------------

def ec_add(P: tuple, Q: tuple, a: int, p: int) -> tuple:
    """Add two points on y^2 = x^3 + ax + b over GF(p)."""
    if P is None:
        return Q
    if Q is None:
        return P
    x1, y1 = P
    x2, y2 = Q
    if x1 == x2:
        if y1 != y2:
            return None  # point at infinity
        # Point doubling
        if y1 == 0:
            return None
        m = (3 * x1 * x1 + a) * pow(2 * y1, -1, p) % p
    else:
        m = (y2 - y1) * pow(x2 - x1, -1, p) % p
    x3 = (m * m - x1 - x2) % p
    y3 = (m * (x1 - x3) - y1) % p
    return (x3, y3)


def ec_mul(k: int, P: tuple, a: int, p: int) -> tuple:
    """Scalar multiplication k*P."""
    result = None
    base = P
    while k > 0:
        if k & 1:
            result = ec_add(result, base, a, p)
        base = ec_add(base, base, a, p)
        k >>= 1
    return result


def ecdlp_brute(Q: tuple, P: tuple, a: int, p: int, max_k: int = 500) -> int | None:
    """
    Brute-force ECDLP: find k s.t. Q = k*P.
    Classical O(√n) Pollard's rho; we do brute force for small demo.
    """
    cur = P
    for k in range(1, max_k + 1):
        if cur == Q:
            return k
        cur = ec_add(cur, P, a, p)
        if cur is None:
            break
    return None


def simulated_quantum_ecdlp(Q: tuple, P: tuple, a: int, p: int, n: int) -> dict:
    """
    Simulate quantum ECDLP solving via Shor's algorithm (classical sim).
    In a real CRQC: uses quantum Fourier transform on the group Z_n × Z_n.
    Returns the discrete log k.
    """
    # Classical simulation: just use brute force for small n
    k = ecdlp_brute(Q, P, a, p, max_k=n)
    # Qubit estimate: ~9n qubits for n-bit curve (Roetteler et al.)
    qubit_estimate = 9 * int(math.log2(n + 1)) if n > 1 else 10
    return {
        "k_found": k,
        "method": "Classical brute-force (simulating quantum ECDLP output)",
        "real_quantum_qubits": f"~9×{int(math.log2(n+1))}bits ≈ {qubit_estimate} for this curve",
    }


# ---------------------------------------------------------------------------
# run_scenario
# ---------------------------------------------------------------------------

def run_scenario() -> dict:
    t0 = time.perf_counter()

    # Demo: tiny curve y^2 = x^3 + 2x + 3 over GF(97)
    p_demo, a_demo, b_demo = 97, 2, 3
    P_demo = (3, 6)   # base point (verify on curve: 6^2 = 36, 3^3+6+3=36 mod 97 ✓ — adjusted)
    # Find a valid base point
    valid_P = None
    for x in range(2, p_demo):
        rhs = (pow(x, 3, p_demo) + a_demo * x + b_demo) % p_demo
        # Find square root of rhs mod p
        for y in range(1, p_demo):
            if (y * y) % p_demo == rhs:
                valid_P = (x, y)
                break
        if valid_P:
            break

    demo_result = None
    if valid_P:
        k_secret = 17
        Q_point = ec_mul(k_secret, valid_P, a_demo, p_demo)
        qdlp = simulated_quantum_ecdlp(Q_point, valid_P, a_demo, p_demo, p_demo)
        k_recovered = qdlp["k_found"]
        demo_result = {
            "curve": f"y²=x³+{a_demo}x+{b_demo} over GF({p_demo})",
            "base_point_P": valid_P,
            "k_secret": k_secret,
            "Q_point": Q_point,
            "k_recovered": k_recovered,
            "correct": k_recovered == k_secret,
        }

    result = {
        "scenario": "QC-16",
        "name": "Shor's Algorithm on ECC (ECDLP)",
        "category": "Attack",
        "demo_ecdlp": demo_result,
        "ecc_threat_matrix": ECC_THREAT_MATRIX,
        "rsa_vs_ecc_comparison": RSA_VS_ECC,
        "regev_2024": REGEV_IMPROVEMENT,
        "recommendation": (
            "Both RSA and ECC are broken by Shor's algorithm on a CRQC. "
            "Migrate to: ML-KEM-768/1024 (key encapsulation), "
            "ML-DSA-44/65/87 (signatures), SLH-DSA (hash-based signatures). "
            "ECC-256 needs ~2330 logical qubits; RSA-2048 needs ~4099 — "
            "ECC is actually *easier* to break with fewer quantum resources."
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
    print(f"QC-16: {res['name']}")
    print("=" * 60)
    if res["demo_ecdlp"]:
        d = res["demo_ecdlp"]
        print(f"Demo ECDLP on {d['curve']}")
        print(f"  Base point P = {d['base_point_P']}")
        print(f"  Secret k = {d['k_secret']}")
        print(f"  Q = k*P = {d['Q_point']}")
        print(f"  Quantum ECDLP recovered k = {d['k_recovered']}  ✓" if d["correct"]
              else f"  Recovered k = {d['k_recovered']}  ✗")
    print()
    print("ECC Threat Matrix (Roetteler et al. 2017):")
    hdr = f"  {'Curve':<14} {'Bits':>6} {'Qubits':>8} {'Gates':>12} {'Time@1MHz':>12}  Use"
    print(hdr)
    print("  " + "-" * 72)
    for row in res["ecc_threat_matrix"]:
        print(f"  {row['curve']:<14} {row['bits']:>6} {row['qubits_roetteler']:>8} "
              f"{row['gates']:>12} {row['time_at_1mhz']:>12}  {row['use']}")
    print()
    print("RSA vs ECC quantum resource comparison:")
    for k, v in res["rsa_vs_ecc_comparison"].items():
        if k == "note":
            print(f"  Note: {v}")
        else:
            print(f"  {k}: qubits={v['qubits']}, gates={v['gates']}")
    print()
    print(f"Regev 2024: {res['regev_2024']['description']}")
    print()
    print(f"Recommendation: {res['recommendation']}")
    print(f"Elapsed: {res['elapsed_s']}s")
