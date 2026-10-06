"""
CUSTOMER DEMO PITCH — Fiber QKD Channel Model
==============================================
This demo models photon loss in optical fiber and computes the secret key rate
as a function of distance for three QKD protocols: BB84 (with decoy states),
E91 (entanglement-based), and CV-QKD (Gaussian coherent states).

Physics:
  Transmittance: T = 10^(-α·L/10), α = 0.2 dB/km for standard SMF-28 fiber.
  At 100 km: T ≈ 10^-2 → 99% of photons lost → key rate collapses.
  Satellite link at 1200 km: free-space loss is lower (beam divergence, not fiber).

Key rate models:
  BB84 decoy: R ≈ μ · T · [1 - h(e) - f(e)·h(e)] (GLLP bound, Scarani et al.)
  E91:        R ≈ T · [1 - h(QBER)] (Bell-state source)
  CV-QKD:     R ≈ (1/2)·log₂(1 + SNR) - χ_Eve (simplified Devetak-Winter)

Audience: Network architects, QKD system integrators, interview panels.
Runtime: < 5 seconds (numpy only).
"""

import math
import numpy as np


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_sep(title: str = "") -> None:
    w = 66
    if title:
        p = (w - len(title) - 2) // 2
        print("=" * p + f" {title} " + "=" * (w - p - len(title) - 2))
    else:
        print("=" * w)


def h2(p: float) -> float:
    """Binary entropy function."""
    if p <= 0 or p >= 1:
        return 0.0
    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)


def fiber_transmittance(distance_km: float, alpha: float = 0.2) -> float:
    return 10 ** (-alpha * distance_km / 10)


# ---------------------------------------------------------------------------
# BB84 decoy-state key rate (GLLP bound, Gobby-Yuan-Shields parameters)
# ---------------------------------------------------------------------------

def bb84_decoy_key_rate(distance_km: float) -> float:
    """
    Secret key rate (bits per pulse) for BB84 with weak-coherent decoy states.
    Parameters from Gobby-Yuan-Shields experiment (2004):
      μ = 0.1 mean photon number, detector efficiency η_d = 0.1, dark count p_dark = 10^-5.
    """
    mu       = 0.1      # mean photons per pulse
    eta_d    = 0.1      # detector quantum efficiency
    p_dark   = 1e-5     # dark count probability per time slot
    f_ec     = 1.16     # reconciliation efficiency

    T      = fiber_transmittance(distance_km)
    eta    = eta_d * T
    # Detection probability (single photon component)
    Q1     = 1 - (1 - p_dark) * math.exp(-mu * eta)      # gain for multi-photon
    Q_s    = mu * eta * math.exp(-mu * eta) / Q1           # single-photon fraction approx

    # QBER
    e0     = 0.5                                          # error rate from dark counts
    e_d    = 0.033                                        # optical misalignment
    E_mu   = (e0 * p_dark + e_d * eta * math.exp(-mu)) / max(Q1, 1e-15)
    E_mu   = min(E_mu, 0.5)

    # Shor-Preskill / GLLP lower bound
    rate = max(0.0, Q_s * (1 - h2(E_mu)) - f_ec * Q1 * h2(E_mu))
    return rate


# ---------------------------------------------------------------------------
# E91 key rate (simplified)
# ---------------------------------------------------------------------------

def e91_key_rate(distance_km: float) -> float:
    """
    E91 with entangled pair source.
    Assume pump efficiency = 0.01 pairs/pulse, η_d = 0.1.
    """
    eta_source = 0.01
    eta_d      = 0.1
    f_ec       = 1.16
    qber_opt   = 0.05   # typical optical QBER for well-aligned system

    T    = fiber_transmittance(distance_km)
    eta  = eta_d * T
    # Probability of coincidence
    Q    = eta_source * eta ** 2     # both photons must arrive
    if Q <= 0:
        return 0.0
    qber = qber_opt + 0.01 * distance_km / 10   # QBER grows slightly with distance
    qber = min(qber, 0.5)
    rate = max(0.0, Q * (1 - f_ec * h2(qber)))
    return rate


# ---------------------------------------------------------------------------
# CV-QKD key rate
# ---------------------------------------------------------------------------

def cv_qkd_key_rate(distance_km: float) -> float:
    """
    GMCS CV-QKD key rate (simplified Devetak-Winter, reverse reconciliation).
    V_A = 20 shot-noise units, ξ = 0.01, β = 0.95.
    """
    V_A    = 20.0
    xi     = 0.01
    beta   = 0.95
    T      = fiber_transmittance(distance_km)
    if T <= 0:
        return 0.0
    N_noise = 1.0 + T * xi
    SNR_B   = T * V_A / N_noise
    I_AB    = 0.5 * math.log2(1 + SNR_B)

    # Simplified Holevo bound (heuristic for illustration)
    chi_AE  = max(0.0, I_AB * (1 - T))
    rate    = max(0.0, beta * I_AB - chi_AE)
    return rate


# ---------------------------------------------------------------------------
# Satellite free-space model
# ---------------------------------------------------------------------------

def satellite_transmittance(ground_distance_km: float) -> float:
    """
    Free-space satellite QKD (Micius-style).
    Simplified link budget: telescope diameter D=30cm, divergence θ=5µrad, η_d=0.1.
    T = (D / (θ · L))^2 · η_d^2 · η_atm
    """
    D        = 0.30     # telescope diameter (m)
    theta    = 5e-6     # beam divergence (rad)
    eta_d    = 0.15     # combined detector + optical efficiency
    eta_atm  = 0.5      # atmospheric transmission

    L   = ground_distance_km * 1e3   # meters
    T   = (D / (theta * L)) ** 2 * eta_d ** 2 * eta_atm
    return min(T, 1.0)


def satellite_key_rate(ground_distance_km: float) -> float:
    """BB84 key rate over satellite free-space link."""
    mu    = 0.5
    T     = satellite_transmittance(ground_distance_km)
    f_ec  = 1.16
    qber  = 0.04   # typical Micius QBER
    Q     = mu * T
    if Q <= 0:
        return 0.0
    return max(0.0, Q * (1 - f_ec * h2(qber)))


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    print_sep("FIBER QKD CHANNEL MODEL")
    print("Purpose: Show how distance limits key rates across QKD protocols\n")

    # Fiber distance sweep
    distances = [1, 5, 10, 20, 30, 50, 75, 100, 120, 150]

    print_sep("Secret Key Rate vs Distance (bits/pulse)")
    print(f"  {'Dist(km)':>9}  {'T':>8}  {'Loss(dB)':>9}  "
          f"{'BB84-decoy':>12}  {'E91':>12}  {'CV-QKD':>12}")
    print(f"  {'-'*9}  {'-'*8}  {'-'*9}  {'-'*12}  {'-'*12}  {'-'*12}")

    for d in distances:
        T      = fiber_transmittance(d)
        loss   = -10 * math.log10(T) if T > 0 else 999.0
        r_bb84 = bb84_decoy_key_rate(d)
        r_e91  = e91_key_rate(d)
        r_cv   = cv_qkd_key_rate(d)

        def fmt(r):
            if r <= 0:
                return "  N/A (0 key)"
            return f"{r:.6f}"

        print(f"  {d:>7} km  {T:>8.5f}  {loss:>7.1f} dB  "
              f"{fmt(r_bb84):>12}  {fmt(r_e91):>12}  {fmt(r_cv):>12}")

    print()

    # Satellite range comparison
    print_sep("Satellite QKD — Free-Space Link Budget")
    print(f"  {'Dist(km)':>9}  {'T_sat':>10}  {'BB84 rate':>12}  Notes")
    print(f"  {'-'*9}  {'-'*10}  {'-'*12}  {'-'*40}")
    sat_distances = [300, 500, 600, 800, 1000, 1200, 2000]
    for d in sat_distances:
        T   = satellite_transmittance(d)
        r   = satellite_key_rate(d)
        note = ""
        if d == 1200:
            note = "← Micius actual distance"
        elif d == 500:
            note = "← Micius orbital altitude"
        print(f"  {d:>7} km  {T:>10.2e}  {r:>12.6f}  {note}")

    print()
    print_sep("Range Limits Summary")
    rows = [
        ("Fiber BB84 (no decoy)",   "~30 km",   "Single-photon loss dominates"),
        ("Fiber BB84 (decoy state)","~100 km",  "Decoy extends single-photon fraction"),
        ("Fiber E91",               "~50 km",   "Coincidence detection halves range"),
        ("Fiber CV-QKD",            "~100 km",  "Higher noise threshold"),
        ("Satellite BB84 (Micius)", "~1200 km", "Free-space loss < fiber beyond 50 km"),
        ("Quantum repeater (future)","Global",  "Bell-state measurement + entanglement swapping"),
    ]
    print(f"  {'Protocol':<30}  {'Max Range':>10}  Notes")
    print(f"  {'-'*30}  {'-'*10}  {'-'*45}")
    for proto, rng_, note in rows:
        print(f"  {proto:<30}  {rng_:>10}  {note}")

    print()
    print_sep("Photon Survival Rate at Key Distances")
    for d in [10, 50, 100, 500]:
        T_fib  = fiber_transmittance(d)
        T_sat  = satellite_transmittance(d)
        print(f"  {d:>5} km  fiber: {T_fib*100:>8.4f}% survive  "
              f"  satellite: {T_sat*100:>8.4f}% survive")

    print()
    print_sep("Key Takeaway")
    print("""
  Fiber QKD is limited to ~100 km because photon loss grows exponentially.
  Satellite QKD (Micius, 2017) demonstrated 1200 km ground-to-ground QKD
  through free-space links — beam divergence loss is polynomial in distance,
  far better than fiber beyond ~50 km.

  Quantum repeaters (when available) will extend fiber QKD to global range
  without satellites — but require quantum memory and entanglement swapping
  (engineering challenges projected 5–15 years away from commercial readiness).

  Today's practical network: satellite-assisted QKD + trusted relay nodes
  + AES-256 classical encryption for segments without QKD coverage.
""")
    print_sep()


if __name__ == "__main__":
    main()
