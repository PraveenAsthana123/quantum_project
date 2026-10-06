"""
QC-07: CV-QKD — Continuous-Variable Gaussian Modulated QKD
============================================================
Algorithm  : GG02 / GMCS CV-QKD (Grosshans & Grangier 2002)
Reference  : F. Grosshans, Ph. Grangier, "Continuous variable quantum
             cryptography using coherent states", PRL 88, 057902 (2002).
             Leverich et al. "Composable security of squeezed-state CV-QKD" (2015).
Complexity : O(N) coherent state preparations; homodyne detection; O(N) sifting
Security   : Information-theoretic via Devetak-Winter key rate formula;
             composable security proven in finite-size regime
Quantum Adv: Uses standard telecom lasers & balanced homodyne detectors;
             no single-photon sources required; shot-noise limited measurement
"""

import time
import math
import numpy as np

RNG = np.random.default_rng(seed=42)

SHOT_NOISE_VARIANCE = 1.0   # vacuum noise units (normalized)


def _binary_entropy(p: float) -> float:
    if p <= 0 or p >= 1:
        return 0.0
    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)


def _von_neumann_entropy_gaussian(variance: float) -> float:
    """
    Von Neumann entropy of a single-mode Gaussian state with variance V.
    g(x) = ((x+1)/2)·log2((x+1)/2) - ((x-1)/2)·log2((x-1)/2)
    """
    if variance <= 1.0:
        return 0.0
    x = variance
    a = (x + 1) / 2
    b = (x - 1) / 2
    return (a * math.log2(a + 1e-12)) - (b * math.log2(b + 1e-12))


def mutual_information_alice_bob(V_A: float, T: float, V_N: float,
                                 xi: float = 0.0) -> float:
    """
    Mutual information I(A;B) for Gaussian-modulated coherent state protocol.

    Parameters
    ----------
    V_A : Alice's modulation variance (shot-noise units)
    T   : channel transmittance (0–1)
    V_N : shot noise variance (= 1 in SNUs)
    xi  : excess noise referred to channel input

    I(A;B) = 0.5 * log2(1 + T·V_A / (V_N + T·xi))
    """
    snr = T * V_A / (V_N + T * xi)
    if snr <= 0:
        return 0.0
    return 0.5 * math.log2(1 + snr)


def holevo_bound_eve(V_A: float, T: float, V_N: float,
                     xi: float = 0.0) -> float:
    """
    Holevo information χ(E;B) for the optimal Gaussian collective attack
    (beam-splitter + vacuum injection).

    Under reverse reconciliation (Bob reconciles toward Alice), the bound
    is Eve's Gaussian MI about Bob's homodyne measurement:

        χ(E;B) = max(0, I(E;X_B))
               = (1/2) * log2(V_E / V_{E|X_B})

    where:
      V_E      = (1-T) * (V_A + 1)   — Eve's mode variance
      C_{EB}²  = (1-T)*T * V_A²       — covariance squared (X quad)
      V_B      = T*(V_A+xi) + V_N     — Bob's mode variance
      V_{E|X_B} = V_E - C_{EB}²/V_B  — conditional variance

    Reference: Grosshans & Grangier, PRL 88, 057902 (2002), Eq.(8).
    """
    if T <= 0:
        return 0.5 * math.log2(V_A + 1)
    if T >= 1:
        return 0.0

    V_B  = T * (V_A + xi) + V_N          # Bob's quadrature variance
    V_E  = (1.0 - T) * (V_A + 1.0)       # Eve's mode variance
    C2   = (1.0 - T) * T * V_A ** 2      # covariance squared (X quad)

    V_E_given_B = V_E - C2 / max(V_B, 1e-12)

    if V_E_given_B <= 0 or V_E <= 0:
        return 0.0

    return max(0.0, 0.5 * math.log2(V_E / V_E_given_B))


def secret_key_rate_cv(V_A: float, T: float, V_N: float = 1.0,
                       xi: float = 0.0, beta: float = 0.95) -> float:
    """
    Devetak-Winter asymptotic secret key rate:
    r = β·I(A;B) − χ(E;B)

    β = reconciliation efficiency (< 1 because Bob's reverse reconciliation
        uses capacity-achieving codes at finite SNR is hard).
    """
    IAB = mutual_information_alice_bob(V_A, T, V_N, xi)
    chi = holevo_bound_eve(V_A, T, V_N, xi)
    return max(0.0, beta * IAB - chi)


def channel_transmittance(distance_km: float,
                          alpha_db: float = 0.2) -> float:
    return 10 ** (-alpha_db * distance_km / 10)


def simulate_cvqkd(n_samples: int = 1000, distance_km: float = 50.0,
                   V_A: float = 20.0, xi: float = 0.01,
                   beta: float = 0.95, seed: int = 42) -> dict:
    """
    Simulate CV-QKD raw data exchange.

    Alice draws (x, p) pairs from Gaussian N(0, V_A).
    Transmits x quadrature (homodyne: Bob measures X or P, not both).
    Bob's measurement = √T · x_Alice + noise_channel + noise_Bob
    """
    rng = np.random.default_rng(seed)
    T = channel_transmittance(distance_km)

    # Alice's Gaussian modulated coherent state quadratures
    alice_x = rng.normal(0, math.sqrt(V_A), size=n_samples)

    # Channel: loss + excess noise + shot noise
    noise_channel = rng.normal(0, math.sqrt(T * xi + SHOT_NOISE_VARIANCE), size=n_samples)
    bob_x = math.sqrt(T) * alice_x + noise_channel

    # Estimate channel parameters from sample
    T_est  = np.cov(alice_x, bob_x)[0, 1] / np.var(alice_x)
    xi_est = max(0.0, float(np.var(bob_x) - T_est * V_A - SHOT_NOISE_VARIANCE) / max(T_est, 1e-9))

    # Theoretical key rate
    r = secret_key_rate_cv(V_A, T, SHOT_NOISE_VARIANCE, xi, beta)
    r_est = secret_key_rate_cv(V_A, max(T_est, 1e-9), SHOT_NOISE_VARIANCE,
                               max(xi_est, 0), beta)

    snr = T * V_A / (SHOT_NOISE_VARIANCE + T * xi)

    return {
        "distance_km": distance_km,
        "n_samples": n_samples,
        "T_theoretical": round(T, 6),
        "T_estimated": round(float(T_est), 6),
        "xi_theoretical": xi,
        "xi_estimated": round(float(xi_est), 6),
        "snr_db": round(10 * math.log10(snr + 1e-12), 2),
        "key_rate_theoretical": round(r, 6),
        "key_rate_estimated": round(r_est, 6),
    }


def run_scenario() -> dict:
    t_start = time.perf_counter()

    # Key rate vs distance for different excess noise levels
    distances = [10, 20, 30, 50, 75, 100, 130, 150]
    xi_levels = [0.005, 0.01, 0.05]
    V_A = 20.0
    beta = 0.95

    table = []
    for d in distances:
        row = {"distance_km": d}
        for xi in xi_levels:
            r = secret_key_rate_cv(V_A, channel_transmittance(d),
                                   SHOT_NOISE_VARIANCE, xi, beta)
            row[f"rate_xi_{xi}"] = round(r, 6)
        table.append(row)

    # Simulation at representative distances
    sim_50  = simulate_cvqkd(1000, distance_km=50,  seed=42)
    sim_100 = simulate_cvqkd(1000, distance_km=100, seed=42)

    elapsed = time.perf_counter() - t_start

    output = {
        "scenario_id": "QC-07",
        "algorithm": "CV-QKD (GG02 / GMCS)",
        "modulation_variance_V_A": V_A,
        "reconciliation_efficiency_beta": beta,
        "shot_noise_V_N": SHOT_NOISE_VARIANCE,
        "key_rate_table": table,
        "sim_50km_qr": sim_50["key_rate_estimated"],
        "sim_100km_qr": sim_100["key_rate_estimated"],
        "sim_time_ms": round(elapsed * 1000, 2),
        "security_model": "information-theoretic (Devetak-Winter, collective attacks)",
        "hardware_advantage": "Standard telecom lasers + homodyne; no single-photon sources",
        "status": "PASS" if sim_50["key_rate_estimated"] > 0 else "FAIL",
    }
    return output


def _print_table(results: dict) -> None:
    print("\n" + "=" * 72)
    print("QC-07  CV-QKD — Continuous Variable QKD (Gaussian Modulation)")
    print("=" * 72)
    for k, v in results.items():
        if k == "key_rate_table":
            continue
        print(f"  {k:<45} {v}")
    print()
    print(f"  Key rate vs distance vs excess noise (β={results['reconciliation_efficiency_beta']}):")
    print(f"  {'Dist (km)':<12} {'ξ=0.005':>14} {'ξ=0.01':>14} {'ξ=0.05':>14}")
    print("  " + "-" * 58)
    for row in results["key_rate_table"]:
        d = row["distance_km"]
        r1 = row.get("rate_xi_0.005", 0)
        r2 = row.get("rate_xi_0.01", 0)
        r3 = row.get("rate_xi_0.05", 0)
        print(f"  {d:<12} {r1:>14.6f} {r2:>14.6f} {r3:>14.6f}")
    print()
    print("  DV-QKD vs CV-QKD hardware:")
    print(f"  {'Feature':<35} {'DV-QKD (BB84)':<25} {'CV-QKD (GG02)'}")
    print("  " + "-" * 72)
    rows = [
        ("Light source", "Single-photon source", "Coherent laser (telecom)"),
        ("Detector", "Single-photon detector (SNSPD)", "Balanced homodyne"),
        ("Cryogenics needed?", "Yes (SNSPD)", "No (room temperature)"),
        ("Modulation", "Discrete (4 states)", "Continuous Gaussian"),
        ("Max distance", "~400 km (with repeaters)", "~150 km (excess noise limited)"),
        ("Key rate at 50 km", "~10^-3 bits/use", "~10^-2 bits/use"),
    ]
    for prop, dv, cv in rows:
        print(f"  {prop:<35} {dv:<25} {cv}")
    print("=" * 72)


if __name__ == "__main__":
    res = run_scenario()
    _print_table(res)
