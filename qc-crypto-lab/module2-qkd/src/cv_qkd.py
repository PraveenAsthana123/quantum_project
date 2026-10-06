"""
CUSTOMER DEMO PITCH — Continuous-Variable QKD (CV-QKD)
=======================================================
All QKD protocols so far use DISCRETE variables (individual photon polarisation
or timing).  CV-QKD (Grosshans & Grangier 2002) encodes key bits in the
CONTINUOUS quadratures (X, P) of coherent laser states — the same physics
as standard telecom lasers.

Why CV-QKD matters:
  - Compatible with standard telecom fiber and components (no single-photon detectors).
  - Lower hardware cost for metropolitan distances (<50 km).
  - Gaussian Modulated Coherent State (GMCS) protocol has the highest proven
    secure key rate at short-to-medium distances.

This demo uses numpy to simulate the GMCS CV-QKD channel:
  Alice samples (X_A, P_A) from N(0, V_A·N_0).
  Bob receives (X_B, P_B) = (√T · X_A + noise_X, √T · P_A + noise_P).
  Secure key rate: r = (1/2) log(1 + SNR_Bob) - χ(A;E)

Audience: Network engineers, quantum hardware teams, interview panels.
Runtime: < 5 seconds (numpy only, no Qiskit needed).
"""

import math
import numpy as np


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_sep(title: str = "") -> None:
    w = 64
    if title:
        p = (w - len(title) - 2) // 2
        print("=" * p + f" {title} " + "=" * (w - p - len(title) - 2))
    else:
        print("=" * w)


# ---------------------------------------------------------------------------
# CV-QKD channel simulation
# ---------------------------------------------------------------------------

def simulate_gmcs_qkd(
    V_A: float,           # Alice's modulation variance (in shot-noise units N_0)
    T: float,             # Channel transmittance (0 to 1)
    xi: float,            # Excess noise (in shot-noise units)
    n_symbols: int = 5000,
    rng: np.random.Generator = None,
) -> dict:
    """
    Simulate GMCS CV-QKD:
      Alice: (X_A, P_A) ~ N(0, V_A)
      Bob homodyne: X_B = sqrt(T)*X_A + noise    (homodyne, single quadrature)
      Noise variance: N = 1 + T*xi + (1-T) [shot noise + excess + vacuum]

    Returns mutual information, Holevo bound, secure key rate.
    """
    if rng is None:
        rng = np.random.default_rng(42)

    # Alice's quadratures
    X_A = rng.normal(0, math.sqrt(V_A), n_symbols)

    # Channel noise variance at Bob (shot-noise units)
    # N_0 = 1 (shot noise), vacuum noise contributes 1-T
    N_noise = 1 + T * xi      # total noise = shot noise + excess noise * T

    # Bob's measurement
    noise    = rng.normal(0, math.sqrt(N_noise), n_symbols)
    X_B = math.sqrt(T) * X_A + noise

    # Signal-to-noise ratio at Bob
    SNR_B = T * V_A / N_noise

    # Mutual information I(A;B) in bits per symbol (Gaussian channel formula)
    I_AB = 0.5 * math.log2(1 + SNR_B)

    # Holevo bound χ(A;E) — Eve's maximum information (collective attack, reverse rec.)
    # V_B = T*V_A + N_noise
    V_B = T * V_A + N_noise
    # Symplectic eigenvalues of the two-mode covariance matrix (collective attack)
    # Simplified Devetak-Winter bound
    V_mode = V_A + 1   # total Alice mode variance
    chi_BE = h_von((math.sqrt((V_mode * N_noise / T + 1))) ) - \
             h_von(math.sqrt(N_noise / T + (T * V_A + N_noise - 1) / (V_B)))

    chi_BE = max(0.0, chi_BE)
    r_secure = max(0.0, I_AB - chi_BE)

    return {
        "V_A":      V_A,
        "T":        T,
        "xi":       xi,
        "SNR_B":    SNR_B,
        "I_AB":     I_AB,
        "chi_BE":   chi_BE,
        "r_secure": r_secure,
        "n_symbols": n_symbols,
        "correlation": float(np.corrcoef(X_A, X_B)[0, 1]),
    }


def h_von(x: float) -> float:
    """Von Neumann entropy for a bosonic mode with symplectic eigenvalue x."""
    if x <= 1:
        return 0.0
    g = (x + 1) / 2 * math.log2((x + 1) / 2) - (x - 1) / 2 * math.log2((x - 1) / 2)
    return g


def transmittance(distance_km: float, alpha_db_per_km: float = 0.2) -> float:
    """Fiber transmittance T = 10^(-alpha * L / 10)."""
    return 10 ** (-alpha_db_per_km * distance_km / 10)


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    rng = np.random.default_rng(42)

    V_A     = 20.0    # modulation variance in shot-noise units
    xi      = 0.01    # excess noise (1% — typical lab value)

    print_sep("CV-QKD — GAUSSIAN MODULATED COHERENT STATE DEMO")
    print("Purpose: Continuous-variable QKD compatible with telecom hardware\n")

    # Single operating point
    T0 = transmittance(20)   # 20 km fiber
    r0 = simulate_gmcs_qkd(V_A, T0, xi, n_symbols=5000, rng=rng)

    print_sep("Channel Parameters")
    print(f"  Modulation variance V_A:          {V_A} shot-noise units")
    print(f"  Channel distance:                 20 km fiber")
    print(f"  Fiber loss coefficient α:         0.2 dB/km")
    print(f"  Transmittance T:                  {T0:.4f}  ({-10*math.log10(T0):.1f} dB)")
    print(f"  Excess noise ξ:                   {xi} (shot-noise units)")
    print()

    print_sep("Information-Theoretic Results")
    print(f"  Alice-Bob correlation coefficient: {r0['correlation']:.4f}")
    print(f"  SNR at Bob's detector:             {r0['SNR_B']:.4f}")
    print(f"  Mutual information I(A;B):         {r0['I_AB']:.4f} bits/symbol")
    print(f"  Holevo bound χ(A;E):               {r0['chi_BE']:.4f} bits/symbol")
    print(f"  Secure key rate r = I(A;B)-χ(A;E): {r0['r_secure']:.4f} bits/symbol")
    print()

    # Distance table
    print_sep("Key Rate vs Distance Table")
    print(f"  {'Distance':>10}  {'T':>8}  {'Loss (dB)':>10}  {'SNR_B':>8}  "
          f"{'I(A;B)':>8}  {'r_secure':>10}  Feasible?")
    print(f"  {'-'*10}  {'-'*8}  {'-'*10}  {'-'*8}  "
          f"{'-'*8}  {'-'*10}  {'-'*10}")
    for d_km in [1, 5, 10, 20, 30, 50, 75, 100, 120]:
        T   = transmittance(d_km)
        r   = simulate_gmcs_qkd(V_A, T, xi, n_symbols=2000, rng=rng)
        loss_db = -10 * math.log10(T) if T > 0 else 999
        feasible = "Yes" if r['r_secure'] > 0.001 else "No"
        print(f"  {d_km:>8} km  {T:>8.4f}  {loss_db:>8.1f} dB  "
              f"{r['SNR_B']:>8.4f}  {r['I_AB']:>8.4f}  {r['r_secure']:>10.6f}  {feasible}")

    print()
    print_sep("Secure Key Rate Formula")
    print("""
  r_secure = β · I(A;B) - χ(A;E)

  where:
    β = reconciliation efficiency (~0.95 for good EC codes)
    I(A;B) = (1/2) log₂(1 + T·V_A / (1 + T·ξ))   [Gaussian MI]
    χ(A;E) = Holevo bound (collective attacks, reverse reconciliation)

  Protocol flow:
    1. Alice samples (X_A, P_A) ~ N(0, V_A · N₀) — coherent state amplitude
    2. Alice sends coherent states |α⟩ where α = (X_A + iP_A) / 2
    3. Bob randomly measures X or P with homodyne detector
    4. Classical channel: Bob announces which quadrature he measured
    5. Alice keeps matching data → raw key
    6. Error correction + Privacy Amplification → secure key
""")

    print_sep("CV-QKD vs DV-QKD (BB84) Comparison")
    rows = [
        ("Light source",        "Laser + modulator",      "Single-photon source"),
        ("Detector",            "Homodyne/heterodyne",    "SNSPD / APD"),
        ("Telecom compatible",  "Yes (C-band 1550 nm)",   "Partial (IDQ solutions)"),
        ("Metropolitan range",  "50–100 km",              "50–300 km (decoy)"),
        ("Long-haul range",     "Needs quantum repeater", "Satellite-assisted 1200 km"),
        ("Key rate at 20 km",   "~1 Mbps",                "~100 kbps"),
        ("Hardware cost",       "Lower",                  "Higher (cryogenic detectors)"),
        ("Proven PQC secure",   "Yes (ITS, coll. attack)", "Yes (ITS)"),
    ]
    print(f"  {'Feature':<28}  {'CV-QKD':>24}  {'DV-QKD (BB84)':>24}")
    print(f"  {'-'*28}  {'-'*24}  {'-'*24}")
    for f, cv, dv in rows:
        print(f"  {f:<28}  {cv:>24}  {dv:>24}")

    print()
    print_sep("Key Takeaway")
    print("""
  CV-QKD is the path to QKD on standard telecom infrastructure.
  No exotic single-photon sources or cryogenic detectors required.
  Practical for enterprise metro-area networks at costs approaching
  classical fiber encryption hardware.
  Limitation: ~100 km range without quantum repeaters (satellite closes gap).
""")
    print_sep()


if __name__ == "__main__":
    main()
