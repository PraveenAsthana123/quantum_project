"""
Q01 — Shor's factorization (classical simulation of quantum period-finding).

Demonstrates the algorithm for N=15 and N=21.
Uses classical modular arithmetic to simulate the period-finding step,
shows required qubit count, and compares vs. classical trial-division timing.

Saves results to data/shor_results.json.
"""

import json
import math
import random
import time
from pathlib import Path

RESULTS_PATH = Path(__file__).parent.parent / "data" / "shor_results.json"


# ── Number-theory helpers ─────────────────────────────────────────────────

def gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def find_period_classical(a: int, N: int) -> int:
    """Find the smallest r such that a^r ≡ 1 (mod N)."""
    r = 1
    value = a % N
    while value != 1:
        value = (value * a) % N
        r += 1
        if r > N:  # safety
            return -1
    return r


def choose_coprime(N: int, seed: int = 7) -> int:
    """Choose a random base a with 1 < a < N and gcd(a, N) == 1."""
    candidates = [a for a in range(2, N) if gcd(a, N) == 1]
    random.seed(seed)
    return random.choice(candidates)


def trial_division(N: int) -> list[int]:
    """Classical trial division factorization. Returns list of prime factors."""
    factors = []
    d = 2
    while d * d <= N:
        while N % d == 0:
            factors.append(d)
            N //= d
        d += 1
    if N > 1:
        factors.append(N)
    return factors


def shor_factor(N: int, seed: int = 7) -> dict:
    """
    Run Shor's algorithm (quantum period-finding simulated classically).
    Returns a dict with factors, period, qubit count, and timing.
    """
    print(f"\n--- Factoring N = {N} ---")

    # Step 0: trivial checks
    if N % 2 == 0:
        return {"N": N, "factors": [2, N // 2], "period": None, "note": "trivially even"}

    # Step 1: Classical timing for trial division
    t0 = time.perf_counter()
    classical_factors = trial_division(N)
    classical_time_ms = (time.perf_counter() - t0) * 1000
    print(f"  Classical trial division: {classical_factors} in {classical_time_ms:.4f} ms")

    # Step 2: Choose base a
    a = choose_coprime(N, seed=seed)
    g = gcd(a, N)
    if g > 1:
        # Lucky: a shares a factor with N
        p, q = g, N // g
        print(f"  Lucky GCD: a={a} shares factor with N → factors {p}, {q}")
        return {
            "N": N, "a": a, "factors": sorted([p, q]),
            "period": None, "method": "lucky_gcd",
            "n_qubits": 2 * math.ceil(math.log2(N)) + 3,
            "classical_time_ms": round(classical_time_ms, 4),
            "quantum_speedup": "O(log N)^3 vs O(exp(N^1/3))",
        }

    print(f"  Base a = {a}, gcd({a},{N}) = 1  ✓")

    # Step 3: Quantum period-finding (simulated classically)
    t_q0 = time.perf_counter()
    r = find_period_classical(a, N)
    quantum_sim_time_ms = (time.perf_counter() - t_q0) * 1000
    print(f"  Period r = {r}  (a^r mod N: {a}^{r} mod {N} = {pow(a, r, N)})")

    if r == -1 or r % 2 != 0:
        print(f"  Period r={r} is odd or not found — retry with different a")
        # Try another base
        for alt_seed in range(100, 200):
            a = choose_coprime(N, seed=alt_seed)
            if gcd(a, N) == 1:
                r = find_period_classical(a, N)
                if r != -1 and r % 2 == 0:
                    break
        print(f"  Retry: a={a}, r={r}")

    # Step 4: Extract factors
    factors = []
    if r is not None and r != -1 and r % 2 == 0:
        x = pow(a, r // 2, N)
        f1 = gcd(x - 1, N)
        f2 = gcd(x + 1, N)
        for f in [f1, f2]:
            if 1 < f < N:
                factors.append(f)
        if len(factors) == 2 and factors[0] * factors[1] == N:
            print(f"  Factors: {factors[0]} × {factors[1]} = {N}  ✓")
        elif factors:
            # One non-trivial factor found — complete by division
            for f in factors:
                companion = N // f
                if f * companion == N and f > 1 and companion > 1:
                    factors = sorted([f, companion])
                    break
    if not factors:
        factors = classical_factors  # fallback

    # Step 5: Qubit count estimate
    # QPE register: 2n+3 qubits where n = ceil(log2(N))
    n = math.ceil(math.log2(N))
    n_qubits = 2 * n + 3

    print(f"  Qubit count (estimate): {n_qubits}")
    print(f"  Quantum speedup: O((log N)^3) vs O(exp((log N)^(1/3)))")

    return {
        "N": N,
        "a": a,
        "factors": sorted(set(factors)),
        "period": int(r) if r and r != -1 else None,
        "n_qubits": n_qubits,
        "classical_time_ms": round(classical_time_ms, 6),
        "quantum_sim_time_ms": round(quantum_sim_time_ms, 6),
        "quantum_speedup": "O((log N)^3) vs O(exp((log N)^(1/3))) (Shor vs GNFS)",
    }


def main():
    print("=" * 60)
    print("Q01 — Shor's Factorization Algorithm (Simulation)")
    print("=" * 60)

    results = []
    for N in [15, 21]:
        res = shor_factor(N)
        results.append(res)

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved → {RESULTS_PATH}")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
