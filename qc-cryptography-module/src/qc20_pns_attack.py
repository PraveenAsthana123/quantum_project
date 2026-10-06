"""
QC-20: Photon Number Splitting (PNS) Attack
WCP (Weak Coherent Pulse) QKD vulnerability and defenses.

stdlib + numpy only. Run directly to see results.
Exports run_scenario() -> dict.
"""

import math
import time
import numpy as np


# ---------------------------------------------------------------------------
# Poisson photon number distribution (WCP source)
# ---------------------------------------------------------------------------

def poisson_prob(n: int, mu: float) -> float:
    """P(n photons) = e^{-μ} μ^n / n! for WCP source."""
    return math.exp(-mu) * (mu ** n) / math.factorial(n)


def photon_distribution(mu: float, max_n: int = 10) -> dict:
    """Distribution of photon numbers for mean photon number mu."""
    dist = {}
    for n in range(max_n + 1):
        dist[n] = round(poisson_prob(n, mu), 8)
    return dist


def multi_photon_rate(mu: float) -> float:
    """
    Fraction of pulses with ≥ 2 photons (vulnerable to PNS).
    P(n≥2) = 1 - P(0) - P(1) = 1 - e^{-μ}(1 + μ)
    """
    return 1.0 - math.exp(-mu) * (1.0 + mu)


def vacuum_rate(mu: float) -> float:
    """P(0 photons) = e^{-μ}."""
    return math.exp(-mu)


def single_photon_rate(mu: float) -> float:
    """P(1 photon) = μ·e^{-μ}."""
    return mu * math.exp(-mu)


# ---------------------------------------------------------------------------
# PNS attack simulation
# ---------------------------------------------------------------------------

def pns_attack_simulation(mu: float = 0.1, n_pulses: int = 100000,
                          channel_loss_db: float = 3.0, seed: int = 42) -> dict:
    """
    Simulate PNS attack strategy:
    - Eve blocks vacuum pulses
    - Eve splits multi-photon pulses: keeps one photon, forwards one
    - Single-photon pulses: Eve blocks (or guesses), Bob sees higher loss

    QBER stays 0% from Eve's interception (she doesn't disturb photons she splits).
    """
    rng = np.random.default_rng(seed)
    eta = 10 ** (-channel_loss_db / 10)   # channel transmittance

    # Generate pulse types
    n_vac     = int(vacuum_rate(mu) * n_pulses)
    n_single  = int(single_photon_rate(mu) * n_pulses)
    n_multi   = int(multi_photon_rate(mu) * n_pulses)

    # Eve's strategy
    # Multi-photon: Eve keeps one photon perfectly, forwards one (QBER = 0 from Eve)
    eve_gained_bits = n_multi  # Eve gets full info on these
    # Single-photon: Eve cannot split → she blocks them (or some pass with loss)
    # To avoid detection, Eve must maintain same apparent loss level
    eve_forwarded_single = int(n_single * eta)

    # Bob's reception (without PNS attack, for comparison)
    bob_expected_honest = int((n_single + n_multi) * eta)
    # Bob's reception with PNS attack
    bob_received_pns = n_multi + eve_forwarded_single  # Multi passed + some single

    # Eve's information fraction
    total_bob_received = max(1, bob_received_pns)
    eve_info_fraction = min(1.0, eve_gained_bits / total_bob_received)

    # QBER with PNS (Eve introduces no errors for split pulses)
    qber_pns = 0.0   # Eve doesn't disturb the photons she splits

    return {
        "mu": mu,
        "channel_loss_db": channel_loss_db,
        "n_pulses": n_pulses,
        "n_vacuum": n_vac,
        "n_single_photon": n_single,
        "n_multi_photon": n_multi,
        "multi_photon_fraction": round(multi_photon_rate(mu), 6),
        "eve_gained_bits": eve_gained_bits,
        "bob_received_pns": bob_received_pns,
        "bob_expected_honest": bob_expected_honest,
        "eve_info_fraction": round(eve_info_fraction, 4),
        "qber_pns": qber_pns,
        "pns_advantage": "Eve gains full information on multi-photon pulses with 0 QBER",
    }


# ---------------------------------------------------------------------------
# mu vs mutual information table
# ---------------------------------------------------------------------------

def mu_vs_eve_info(mu_values=None) -> list[dict]:
    """Compute I(A;E) for different mean photon numbers."""
    if mu_values is None:
        mu_values = [0.01, 0.05, 0.1, 0.2, 0.5, 1.0]
    rows = []
    for mu in mu_values:
        mp = multi_photon_rate(mu)
        single = single_photon_rate(mu)
        total = single + mp
        eve_fraction = mp / total if total > 0 else 0.0
        rows.append({
            "mu": mu,
            "single_photon_fraction": round(single, 5),
            "multi_photon_fraction": round(mp, 6),
            "eve_info_fraction": round(eve_fraction, 4),
        })
    return rows


# ---------------------------------------------------------------------------
# Decoy state defense
# ---------------------------------------------------------------------------

DECOY_STATE_DEFENSE = {
    "principle": (
        "Send pulses at multiple mean photon numbers: signal (μ_s), decoy (μ_d), vacuum. "
        "Alice and Bob compare statistics across intensity levels to estimate single-photon "
        "gain and error rate. Eve cannot attack signal pulses without affecting decoy statistics."
    ),
    "protocols": {
        "1-decoy": {
            "mu_signal": 0.5, "mu_decoy": 0.1,
            "advantage": "Simple; detects most PNS attacks",
            "limitation": "Weaker bounds on single-photon fraction",
        },
        "2-decoy": {
            "mu_signal": 0.5, "mu_decoy1": 0.1, "mu_decoy2": 0.0,
            "advantage": "Tight bounds; optimal secret key rate",
            "limitation": "Requires vacuum pulses",
        },
    },
    "pns_defeat": (
        "Decoy states make multi-photon fraction measurable. "
        "Eve cannot block multi-photon selectively without changing transmittance statistics. "
        "Deployed in: ID Quantique, Toshiba QKD systems."
    ),
}


# ---------------------------------------------------------------------------
# BB84 vs SARG04 vs Decoy-BB84
# ---------------------------------------------------------------------------

PROTOCOL_COMPARISON = [
    {
        "protocol": "BB84",
        "pns_vulnerability": "High (μ≈0.5 → ~9% multi-photon pulses)",
        "key_rate": "~μη/2",
        "sarg04_advantage": "Baseline — no PNS defense",
    },
    {
        "protocol": "SARG04",
        "pns_vulnerability": "Reduced (~50% of BB84 vulnerability)",
        "key_rate": "~μη/4",
        "sarg04_advantage": (
            "Uses 4-state encoding with non-orthogonal state reveal; "
            "Eve needs 2 photons to determine basis unambiguously → "
            "halves PNS information advantage"
        ),
    },
    {
        "protocol": "Decoy-BB84",
        "pns_vulnerability": "Near-zero (decoy states detect PNS)",
        "key_rate": "~Q₁(1-H₂(e₁))",
        "sarg04_advantage": "Gold standard defense against PNS attacks",
    },
]


# ---------------------------------------------------------------------------
# run_scenario
# ---------------------------------------------------------------------------

def run_scenario() -> dict:
    t0 = time.perf_counter()

    # Run PNS simulation for mu=0.1 (typical QKD setting)
    sim_01 = pns_attack_simulation(mu=0.1, n_pulses=100000, channel_loss_db=3.0)
    sim_05 = pns_attack_simulation(mu=0.5, n_pulses=100000, channel_loss_db=3.0)

    mu_analysis = mu_vs_eve_info()

    result = {
        "scenario": "QC-20",
        "name": "Photon Number Splitting (PNS) Attack",
        "category": "Attack",
        "photon_dist_mu01": photon_distribution(mu=0.1, max_n=5),
        "photon_dist_mu05": photon_distribution(mu=0.5, max_n=5),
        "pns_simulation_mu01": sim_01,
        "pns_simulation_mu05": sim_05,
        "mu_vs_eve_info": mu_analysis,
        "decoy_state_defense": DECOY_STATE_DEFENSE,
        "protocol_comparison": PROTOCOL_COMPARISON,
        "key_insight": (
            "WCP sources emit multi-photon pulses with probability ~μ²/2. "
            "Eve can intercept multi-photon pulses silently (0 QBER). "
            "At μ=0.1: ~0.9% multi-photon rate → Eve gains info on ~1-2% of key bits. "
            "Defense: decoy states expose PNS by checking statistics across μ levels. "
            "SARG04 halves PNS advantage by requiring Eve to measure 2 photons for 1 bit of info."
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
    print(f"QC-20: {res['name']}")
    print("=" * 60)
    print()
    print("Photon distribution P(n) for μ=0.1:")
    for n, p in res["photon_dist_mu01"].items():
        bar = "#" * int(p * 200)
        print(f"  n={n}: {p:.6f}  {bar}")
    print()
    s = res["pns_simulation_mu01"]
    print(f"PNS Attack Simulation (μ={s['mu']}, {s['n_pulses']:,} pulses):")
    print(f"  Vacuum pulses:          {s['n_vacuum']:>8,}")
    print(f"  Single-photon pulses:   {s['n_single_photon']:>8,}")
    print(f"  Multi-photon pulses:    {s['n_multi_photon']:>8,}  ← Eve exploits these")
    print(f"  Multi-photon fraction:  {s['multi_photon_fraction']:.4%}")
    print(f"  Eve's info fraction:    {s['eve_info_fraction']:.4f}")
    print(f"  QBER from PNS attack:   {s['qber_pns']:.4f}  ← Eve is UNDETECTABLE via QBER!")
    print()
    print("μ vs Eve's information (PNS):")
    hdr = f"  {'μ':>6} {'Single':>10} {'Multi':>12} {'Eve info%':>10}"
    print(hdr)
    print("  " + "-" * 44)
    for row in res["mu_vs_eve_info"]:
        print(f"  {row['mu']:>6.2f} {row['single_photon_fraction']:>10.5f} "
              f"{row['multi_photon_fraction']:>12.6f} {row['eve_info_fraction']:>10.4f}")
    print()
    print("Protocol Comparison (PNS resistance):")
    for p in res["protocol_comparison"]:
        print(f"  {p['protocol']:<16}: PNS vulnerability: {p['pns_vulnerability']}")
    print()
    print(f"Key insight: {res['key_insight']}")
    print(f"Elapsed: {res['elapsed_s']}s")
