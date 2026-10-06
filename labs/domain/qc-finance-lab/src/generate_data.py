"""
Finance Lab Synthetic Data Generator
=====================================
Generates a realistic options pricing dataset (2,000 rows) covering both
European call and put options priced using the Black-Scholes closed-form
formula, augmented with small market-microstructure noise.

Columns:
    S          – spot price (USD, 50–200)
    K          – strike price (USD, 40–210)
    T          – time to expiry (years, 0.1–2.0)
    r          – risk-free rate (0.01–0.08)
    sigma      – implied volatility (0.10–0.60)
    option_type – "call" or "put"
    option_price – Black-Scholes price + Gaussian noise (σ=0.05×price)
    moneyness   – S / K
    log_moneyness – log(S / K)

The Black-Scholes formulas implemented here:
    d1 = (log(S/K) + (r + 0.5*sigma^2)*T) / (sigma*sqrt(T))
    d2 = d1 - sigma*sqrt(T)
    Call = S*N(d1) - K*exp(-r*T)*N(d2)
    Put  = K*exp(-r*T)*N(-d2) - S*N(-d1)

Output:
    qc-finance-lab/data/options_synthetic.csv

Usage:
    python src/generate_data.py

Version: 1.0.0
Date: 2026-10-06
"""
from __future__ import annotations

import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = DATA_DIR / "options_synthetic.csv"

# ---------------------------------------------------------------------------
# Generation parameters
# ---------------------------------------------------------------------------

N_ROWS = 2_000
SEED = 42
NOISE_FRACTION = 0.05    # Gaussian noise as a fraction of theoretical price


# ---------------------------------------------------------------------------
# Black-Scholes pricer
# ---------------------------------------------------------------------------

def black_scholes_price(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str
) -> float:
    """
    Return Black-Scholes price for a European option.

    Parameters
    ----------
    S           Spot price.
    K           Strike price.
    T           Time to expiry in years (must be > 0).
    r           Continuously compounded risk-free rate.
    sigma       Annualised volatility (> 0).
    option_type "call" or "put".

    Returns
    -------
    float  Option price.  Returns intrinsic value if T <= 0 or sigma <= 0.
    """
    if T <= 0 or sigma <= 0:
        if option_type == "call":
            return max(S - K, 0.0)
        return max(K - S, 0.0)

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    disc = math.exp(-r * T)

    if option_type == "call":
        price = S * norm.cdf(d1) - K * disc * norm.cdf(d2)
    else:
        price = K * disc * norm.cdf(-d2) - S * norm.cdf(-d1)

    return max(price, 0.0)


# ---------------------------------------------------------------------------
# Vectorised batch pricer (avoids Python-loop overhead for large N)
# ---------------------------------------------------------------------------

def _bs_batch(
    S: np.ndarray,
    K: np.ndarray,
    T: np.ndarray,
    r: np.ndarray,
    sigma: np.ndarray,
    is_call: np.ndarray,
) -> np.ndarray:
    """Vectorised Black-Scholes over NumPy arrays."""
    with np.errstate(divide="ignore", invalid="ignore"):
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    disc = np.exp(-r * T)

    call_px = S * norm.cdf(d1) - K * disc * norm.cdf(d2)
    put_px = K * disc * norm.cdf(-d2) - S * norm.cdf(-d1)

    prices = np.where(is_call, call_px, put_px)
    return np.maximum(prices, 0.0)


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate(output_path: Path = OUTPUT_FILE, seed: int = SEED) -> pd.DataFrame:
    """Generate synthetic options pricing dataset and save to CSV."""
    t_start = time.perf_counter()
    rng = np.random.default_rng(seed)

    print(f"Generating {N_ROWS:,} options pricing rows...")

    # --- Sample parameters uniformly over realistic market ranges -------------
    S = rng.uniform(50.0, 200.0, N_ROWS)
    K = rng.uniform(40.0, 210.0, N_ROWS)
    T = rng.uniform(0.1, 2.0, N_ROWS)
    r = rng.uniform(0.01, 0.08, N_ROWS)
    sigma = rng.uniform(0.10, 0.60, N_ROWS)

    # --- Option type (roughly equal split) ------------------------------------
    option_types_bool = rng.random(N_ROWS) > 0.5   # True = call
    option_type_str = np.where(option_types_bool, "call", "put")

    # --- Black-Scholes theoretical prices -------------------------------------
    theo_prices = _bs_batch(S, K, T, r, sigma, option_types_bool)

    # --- Add market microstructure noise (bid-ask spread proxy) ---------------
    noise = rng.normal(0.0, NOISE_FRACTION * (theo_prices + 0.01), N_ROWS)
    option_price = np.round(np.maximum(theo_prices + noise, 0.01), 4)

    # --- Derived features useful for ML models --------------------------------
    moneyness = np.round(S / K, 6)
    log_moneyness = np.round(np.log(S / K), 6)

    # --- Assemble DataFrame ---------------------------------------------------
    df = pd.DataFrame({
        "S": np.round(S, 4),
        "K": np.round(K, 4),
        "T": np.round(T, 6),
        "r": np.round(r, 6),
        "sigma": np.round(sigma, 6),
        "option_type": option_type_str,
        "option_price": option_price,
        "theo_price": np.round(theo_prices, 6),   # kept for benchmark verification
        "moneyness": moneyness,
        "log_moneyness": log_moneyness,
    })

    # --- Save -----------------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    elapsed_ms = (time.perf_counter() - t_start) * 1000
    file_size_kb = output_path.stat().st_size / 1024

    n_calls = int(option_types_bool.sum())
    n_puts = N_ROWS - n_calls
    print(f"  Rows generated : {len(df):,}")
    print(f"  Calls / Puts   : {n_calls} / {n_puts}")
    print(f"  Price range    : {option_price.min():.2f} – {option_price.max():.2f}")
    print(f"  File size      : {file_size_kb:.1f} KB")
    print(f"  Elapsed        : {elapsed_ms:.1f} ms")
    print(f"  Saved          → {output_path}")
    return df


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    generate()
