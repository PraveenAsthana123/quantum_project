"""
Classical finance baseline for the Quantum Finance Lab.

Computes:
  1. Markowitz mean-variance portfolio optimization (Monte Carlo efficient frontier)
  2. Simple Moving Average (SMA) crossover trading signals & backtest
  3. Bitcoin volatility profile (using 1-min OHLCV data resampled to daily)

Results saved to data/classical_results.json with keys:
  markowitz, sma_backtest, bitcoin_stats
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR    = Path(__file__).parent.parent / "data"
DATASET_DIR = Path(__file__).parent.parent.parent / "datasets" / "finance"
RESULTS_FILE = DATA_DIR / "classical_results.json"

# Stocks to use in Markowitz portfolio
PORTFOLIO_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "GS", "JPM", "KO", "JNJ"]
RISK_FREE_RATE    = 0.04      # annualised
N_SIM_PORTFOLIOS  = 10_000    # Monte Carlo frontier samples
SMA_SHORT         = 20        # days
SMA_LONG          = 60        # days
BACKTEST_START    = "2012-01-01"
BACKTEST_END      = "2017-12-31"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_stock_prices(tickers: list[str]) -> pd.DataFrame:
    """Load Close prices from per-ticker CSVs in DATASET_DIR."""
    frames = []
    for ticker in tickers:
        csv = DATASET_DIR / f"{ticker}_2006-01-01_to_2018-01-01.csv"
        if csv.exists():
            df = pd.read_csv(csv, parse_dates=["Date"], index_col="Date")
            frames.append(df["Close"].rename(ticker))
        else:
            print(f"  Warning: {csv.name} not found — skipping {ticker}")

    if not frames:
        raise FileNotFoundError(
            f"No ticker CSVs found in {DATASET_DIR}. "
            "Expected files like AAPL_2006-01-01_to_2018-01-01.csv"
        )

    prices = pd.concat(frames, axis=1).sort_index().dropna(how="all")
    # Forward-fill small gaps (weekends already absent, but handle missing dates)
    prices = prices.ffill().dropna()
    available_tickers = prices.columns.tolist()
    print(f"  Loaded {len(prices)} trading days for {available_tickers}")
    return prices


def load_all_stocks() -> pd.DataFrame:
    """Load the consolidated all_stocks CSV as a cross-sectional Close pivot."""
    csv = DATASET_DIR / "all_stocks_2006-01-01_to_2018-01-01.csv"
    if csv.exists():
        df = pd.read_csv(csv, parse_dates=["Date"])
        pivot = df.pivot_table(index="Date", columns="Name", values="Close")
        pivot = pivot.sort_index().ffill().dropna(how="all")
        return pivot
    return pd.DataFrame()


def load_bitcoin_daily() -> pd.Series:
    """Load BTC/USD 1-min data and resample to daily OHLCV → return daily Close."""
    csv = DATASET_DIR / "btcusd_1-min_data.csv"
    if not csv.exists():
        print("  btcusd_1-min_data.csv not found — skipping Bitcoin stats")
        return pd.Series(dtype=float)

    print("  Resampling BTC 1-min → daily (this may take a moment)…")
    # Read in chunks to handle the large file
    # Timestamp column is Unix epoch seconds — convert explicitly
    chunks = []
    for chunk in pd.read_csv(
        csv,
        chunksize=200_000,
    ):
        chunk["Timestamp"] = pd.to_datetime(chunk["Timestamp"], unit="s", utc=True)
        chunk = chunk.set_index("Timestamp")
        daily = chunk["Close"].resample("D").last().dropna()
        chunks.append(daily)

    btc = pd.concat(chunks).groupby(level=0).last().sort_index()
    btc = btc[btc > 0]
    print(f"  BTC daily: {len(btc)} days  ({btc.index[0].date()} – {btc.index[-1].date()})")
    return btc


# ---------------------------------------------------------------------------
# 1. Markowitz portfolio optimisation
# ---------------------------------------------------------------------------

def markowitz_optimize(prices: pd.DataFrame) -> dict:
    """Compute efficient frontier via Monte Carlo + find max-Sharpe portfolio."""
    returns = prices.pct_change().dropna()
    mu  = returns.mean().values * 252          # annualised expected return
    cov = returns.cov().values * 252           # annualised covariance
    tickers = list(prices.columns)
    n = len(tickers)

    # ---- Monte Carlo sampling ----
    rng = np.random.default_rng(42)
    weights_all, port_rets, port_vols = [], [], []
    for _ in range(N_SIM_PORTFOLIOS):
        w = rng.dirichlet(np.ones(n))
        ret = float(w @ mu)
        vol = float(np.sqrt(w @ cov @ w))
        weights_all.append(w.tolist())
        port_rets.append(ret)
        port_vols.append(vol)

    sharpes   = [(r - RISK_FREE_RATE) / (v + 1e-10) for r, v in zip(port_rets, port_vols)]
    best_idx  = int(np.argmax(sharpes))

    # ---- Scipy analytical max-Sharpe ----
    def neg_sharpe(w):
        r = w @ mu
        v = np.sqrt(w @ cov @ w)
        return -(r - RISK_FREE_RATE) / (v + 1e-10)

    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
    bounds = [(0.0, 1.0)] * n
    x0 = np.ones(n) / n
    res = minimize(neg_sharpe, x0, bounds=bounds, constraints=constraints, method="SLSQP")
    opt_w  = res.x if res.success else np.array(weights_all[best_idx])
    opt_r  = float(opt_w @ mu)
    opt_v  = float(np.sqrt(opt_w @ cov @ opt_w))
    opt_sr = float((opt_r - RISK_FREE_RATE) / (opt_v + 1e-10))

    # ---- Minimum variance portfolio ----
    def port_vol(w):
        return np.sqrt(w @ cov @ w)

    res_mv = minimize(port_vol, x0, bounds=bounds, constraints=constraints, method="SLSQP")
    mv_w   = res_mv.x if res_mv.success else x0
    mv_r   = float(mv_w @ mu)
    mv_v   = float(np.sqrt(mv_w @ cov @ mv_w))
    mv_sr  = float((mv_r - RISK_FREE_RATE) / (mv_v + 1e-10))

    print(f"  Max-Sharpe  → return={opt_r:.4f}  vol={opt_v:.4f}  sharpe={opt_sr:.4f}")
    print(f"  Min-Variance→ return={mv_r:.4f}  vol={mv_v:.4f}  sharpe={mv_sr:.4f}")

    return {
        "method": "Markowitz",
        "tickers": tickers,
        "risk_free_rate": RISK_FREE_RATE,
        "max_sharpe": {
            "weights": {t: round(float(w), 6) for t, w in zip(tickers, opt_w)},
            "expected_annual_return": round(opt_r, 6),
            "annual_volatility": round(opt_v, 6),
            "sharpe_ratio": round(opt_sr, 6),
        },
        "min_variance": {
            "weights": {t: round(float(w), 6) for t, w in zip(tickers, mv_w)},
            "expected_annual_return": round(mv_r, 6),
            "annual_volatility": round(mv_v, 6),
            "sharpe_ratio": round(mv_sr, 6),
        },
        "equal_weight": {
            "weights": {t: round(1 / n, 6) for t in tickers},
            "expected_annual_return": round(float(np.ones(n) / n @ mu), 6),
            "annual_volatility": round(float(np.sqrt(np.ones(n) / n @ cov @ np.ones(n) / n)), 6),
            "sharpe_ratio": round(
                float((np.ones(n) / n @ mu - RISK_FREE_RATE) / np.sqrt(np.ones(n) / n @ cov @ np.ones(n) / n + 1e-10)), 6
            ),
        },
        "monte_carlo_n": N_SIM_PORTFOLIOS,
        "efficient_frontier_sample": {
            "returns": [round(r, 6) for r in port_rets[:500]],
            "volatilities": [round(v, 6) for v in port_vols[:500]],
            "sharpes": [round(s, 6) for s in sharpes[:500]],
        },
        # Alias keys for API compatibility
        "sharpe_ratio": round(opt_sr, 6),
        "returns": round(opt_r, 6),
        "volatility": round(opt_v, 6),
    }


# ---------------------------------------------------------------------------
# 2. SMA crossover trading strategy
# ---------------------------------------------------------------------------

def sma_backtest(prices: pd.DataFrame, ticker: str = "AAPL") -> dict:
    """
    Dual SMA crossover strategy on a single ticker.
      - Long  when SMA_SHORT > SMA_LONG
      - Cash  when SMA_SHORT <= SMA_LONG  (no shorting)
    """
    if ticker not in prices.columns:
        ticker = prices.columns[0]
        print(f"  {ticker} not available; using {ticker}")

    price = prices[ticker].loc[BACKTEST_START:BACKTEST_END]
    if len(price) < SMA_LONG + 10:
        print(f"  Insufficient data for SMA backtest ({len(price)} rows)")
        return {"ticker": ticker, "error": "insufficient data"}

    # Signals
    sma_s = price.rolling(SMA_SHORT).mean()
    sma_l = price.rolling(SMA_LONG).mean()
    signal = (sma_s > sma_l).astype(int).shift(1).fillna(0)  # next-day execution

    # Daily returns
    daily_ret = price.pct_change().fillna(0)
    strategy_ret = signal * daily_ret
    buy_hold_ret  = daily_ret

    # Cumulative
    strat_cum   = (1 + strategy_ret).cumprod()
    bh_cum      = (1 + buy_hold_ret).cumprod()

    n_trading_days = len(price)
    n_years = n_trading_days / 252

    def annualised(daily_series: pd.Series) -> dict:
        ann_ret = float((1 + daily_series).prod() ** (1 / n_years) - 1)
        ann_vol = float(daily_series.std() * np.sqrt(252))
        sr      = float((ann_ret - RISK_FREE_RATE) / (ann_vol + 1e-10))
        max_dd  = float(((1 + daily_series).cumprod() / (1 + daily_series).cumprod().cummax() - 1).min())
        return {
            "annual_return": round(ann_ret, 6),
            "annual_volatility": round(ann_vol, 6),
            "sharpe_ratio": round(sr, 6),
            "max_drawdown": round(max_dd, 6),
            "total_return": round(float(strat_cum.iloc[-1] - 1 if daily_series is strategy_ret else bh_cum.iloc[-1] - 1), 6),
        }

    # Count trades (signal transitions 0→1 or 1→0)
    n_trades = int((signal.diff().abs() > 0).sum())

    strat_metrics = annualised(strategy_ret)
    bh_metrics    = annualised(buy_hold_ret)

    print(f"  SMA({SMA_SHORT}/{SMA_LONG}) on {ticker}: "
          f"sharpe={strat_metrics['sharpe_ratio']:.4f}  "
          f"ann_ret={strat_metrics['annual_return']:.4f}  "
          f"trades={n_trades}")

    return {
        "ticker": ticker,
        "period": f"{BACKTEST_START} – {BACKTEST_END}",
        "sma_short": SMA_SHORT,
        "sma_long": SMA_LONG,
        "n_trading_days": n_trading_days,
        "n_trades": n_trades,
        "strategy": strat_metrics,
        "buy_and_hold": bh_metrics,
        "alpha": round(strat_metrics["annual_return"] - bh_metrics["annual_return"], 6),
        # Equity curve (subsample every 5th point for JSON size)
        "equity_curve_strategy": [round(float(v), 6) for v in strat_cum.iloc[::5].values],
        "equity_curve_bh":       [round(float(v), 6) for v in bh_cum.iloc[::5].values],
        "equity_curve_dates":    [str(d.date()) for d in strat_cum.iloc[::5].index],
    }


# ---------------------------------------------------------------------------
# 3. Bitcoin volatility & rolling statistics
# ---------------------------------------------------------------------------

def bitcoin_stats(btc_daily: pd.Series) -> dict:
    """Compute rolling volatility, drawdown, and annual return statistics for BTC."""
    if btc_daily.empty:
        return {"error": "BTC data unavailable"}

    ret = btc_daily.pct_change().dropna()

    # Annual windows
    yearly: dict = {}
    for yr in range(int(btc_daily.index.year.min()), int(btc_daily.index.year.max()) + 1):
        yr_ret = ret[ret.index.year == yr]
        if len(yr_ret) < 30:
            continue
        cum = float((1 + yr_ret).prod() - 1)
        vol = float(yr_ret.std() * np.sqrt(365))
        yearly[str(yr)] = {
            "annual_return": round(cum, 6),
            "annual_volatility": round(vol, 6),
            "sharpe": round((cum - RISK_FREE_RATE) / (vol + 1e-10), 6),
        }

    # Overall stats
    total_return = float((1 + ret).prod() - 1)
    overall_vol  = float(ret.std() * np.sqrt(365))
    max_price    = float(btc_daily.max())
    min_price    = float(btc_daily.min())

    # Rolling 30-day volatility (annualised)
    roll_vol = ret.rolling(30).std() * np.sqrt(365)
    roll_vol = roll_vol.dropna()

    # Max drawdown
    cum_prices = (1 + ret).cumprod()
    running_max = cum_prices.cummax()
    drawdown = (cum_prices / running_max - 1)
    max_drawdown = float(drawdown.min())

    print(f"  BTC total return={total_return:.2f}  vol(ann)={overall_vol:.4f}  max_dd={max_drawdown:.4f}")

    return {
        "ticker": "BTC/USD",
        "source": "btcusd_1-min_data.csv",
        "date_range": {
            "start": str(btc_daily.index.min().date()),
            "end":   str(btc_daily.index.max().date()),
        },
        "n_days": len(btc_daily),
        "price_range": {"min": round(min_price, 2), "max": round(max_price, 2)},
        "total_return": round(total_return, 6),
        "annual_volatility": round(overall_vol, 6),
        "max_drawdown": round(max_drawdown, 6),
        "yearly_stats": yearly,
        "rolling_30d_vol_sample": [
            round(float(v), 6)
            for v in roll_vol.iloc[::30].values[:50]   # ~50 monthly data points
        ],
        # Alias for API
        "sharpe_ratio": round((total_return - RISK_FREE_RATE) / (overall_vol + 1e-10), 6),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # ---- Load data ----
    print("\n[1/3] Loading stock price data…")
    t0 = time.perf_counter()
    try:
        prices = load_stock_prices(PORTFOLIO_TICKERS)
    except FileNotFoundError:
        # Fallback: use all_stocks consolidated file
        print("  Falling back to all_stocks consolidated CSV…")
        all_prices = load_all_stocks()
        if all_prices.empty:
            raise
        available = [t for t in PORTFOLIO_TICKERS if t in all_prices.columns]
        prices = all_prices[available].dropna()
        print(f"  Using {list(prices.columns)} from consolidated CSV")

    load_time = time.perf_counter() - t0

    # ---- Markowitz ----
    print("\n[2/3] Markowitz portfolio optimisation…")
    t0 = time.perf_counter()
    markowitz = markowitz_optimize(prices)
    markowitz["elapsed_s"] = round(time.perf_counter() - t0, 3)

    # ---- SMA Backtest ----
    print("\n[3/4] SMA crossover backtest…")
    t0 = time.perf_counter()
    sma = sma_backtest(prices, ticker="AAPL")
    sma["elapsed_s"] = round(time.perf_counter() - t0, 3)

    # ---- Bitcoin stats ----
    print("\n[4/4] Bitcoin daily stats…")
    t0 = time.perf_counter()
    btc_daily = load_bitcoin_daily()
    btc = bitcoin_stats(btc_daily)
    btc["elapsed_s"] = round(time.perf_counter() - t0, 3)

    # ---- Save ----
    results = {
        "generated_at": pd.Timestamp.now().isoformat(),
        "data_load_time_s": round(load_time, 3),
        "markowitz": markowitz,
        "sma_backtest": sma,
        "bitcoin_stats": btc,
        # Top-level aliases used by the portal API
        "sharpe_ratio": markowitz["sharpe_ratio"],
        "returns":      markowitz["returns"],
        "volatility":   markowitz["volatility"],
    }

    with open(RESULTS_FILE, "w") as fh:
        json.dump(results, fh, indent=2, default=str)
    print(f"\nResults saved → {RESULTS_FILE}")
    return results


if __name__ == "__main__":
    main()
