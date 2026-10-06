"""
Portfolio optimization: Markowitz classical baseline vs QAOA quantum approach.
Uses yfinance for real stock data with synthetic fallback.
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent / "data"
RESULTS_FILE = DATA_DIR / "portfolio_results.json"

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
N_ASSETS = len(TICKERS)
N_QAOA_LAYERS = 1
SHOTS = 1024


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_returns() -> pd.DataFrame:
    try:
        import yfinance as yf
        print("Fetching stock data via yfinance...")
        data = yf.download(TICKERS, period="1y", progress=False)["Close"]
        returns = data.pct_change().dropna()
        print(f"  Loaded {len(returns)} days for {N_ASSETS} assets")
        return returns
    except Exception as e:
        print(f"yfinance failed ({e}) — using synthetic returns")
        rng = np.random.default_rng(42)
        dates = pd.date_range("2023-01-01", periods=252)
        mu = np.array([0.0003, 0.0004, 0.00025, 0.00035, 0.0005])
        sigma = np.array([0.015, 0.014, 0.016, 0.018, 0.020])
        data = rng.normal(mu, sigma, (252, N_ASSETS))
        return pd.DataFrame(data, index=dates, columns=TICKERS)


# ---------------------------------------------------------------------------
# Markowitz classical optimization
# ---------------------------------------------------------------------------

def markowitz_optimal(returns: pd.DataFrame, risk_free: float = 0.0) -> dict:
    mu = returns.mean().values * 252           # annualised
    cov = returns.cov().values * 252
    n = len(mu)

    # Monte Carlo sampling of the efficient frontier
    rng = np.random.default_rng(42)
    n_portfolios = 5000
    weights_all, port_rets, port_risks = [], [], []
    for _ in range(n_portfolios):
        w = rng.dirichlet(np.ones(n))
        r = float(w @ mu)
        v = float(np.sqrt(w @ cov @ w))
        weights_all.append(w.tolist())
        port_rets.append(r)
        port_risks.append(v)

    sharpes = [(r - risk_free) / (v + 1e-10) for r, v in zip(port_rets, port_risks)]
    best = int(np.argmax(sharpes))
    return {
        "method": "Markowitz-MonteCarlo",
        "optimal_weights": weights_all[best],
        "expected_return": round(port_rets[best], 4),
        "volatility": round(port_risks[best], 4),
        "sharpe": round(sharpes[best], 4),
        "frontier_returns": port_rets,
        "frontier_risks": port_risks,
        "tickers": TICKERS,
    }


# ---------------------------------------------------------------------------
# QAOA portfolio optimization (Qiskit)
# ---------------------------------------------------------------------------

def _qubo_portfolio(mu: np.ndarray, cov: np.ndarray, q: float, budget: int) -> np.ndarray:
    """Build QUBO matrix for budget-constrained portfolio (binary: include/exclude asset)."""
    n = len(mu)
    penalty = 2.0
    Q = np.zeros((n, n))
    # Risk term
    Q += q * cov
    # Return term (diagonal)
    for i in range(n):
        Q[i, i] -= (1 - q) * mu[i]
    # Budget constraint: (sum xi - budget)^2
    for i in range(n):
        Q[i, i] += penalty * (1 - 2 * budget)
        for j in range(n):
            if i != j:
                Q[i, j] += penalty
    return Q


def qaoa_portfolio(returns: pd.DataFrame) -> dict:
    try:
        from qiskit.circuit.library import QAOAAnsatz
        from qiskit_algorithms import QAOA, NumPyMinimumEigensolver
        from qiskit_algorithms.optimizers import COBYLA
        from qiskit_optimization import QuadraticProgram
        from qiskit_optimization.algorithms import MinimumEigenOptimizer
        from qiskit_optimization.translators import from_ising
        from qiskit.primitives import StatevectorSampler as Sampler
        from qiskit.quantum_info import SparsePauliOp
    except ImportError as e:
        print(f"Qiskit Finance QAOA unavailable ({e}) — returning classical only result")
        return {"method": "QAOA-unavailable", "error": str(e)}

    mu = returns.mean().values * 252
    cov = returns.cov().values * 252
    n = len(mu)
    budget = n // 2  # select half the assets
    q = 0.5          # risk aversion

    print(f"Building QUBO for {n}-asset portfolio (budget={budget})...")
    Q = _qubo_portfolio(mu, cov, q, budget)

    qp = QuadraticProgram("portfolio")
    for i, ticker in enumerate(TICKERS[:n]):
        qp.binary_var(ticker)

    linear = {TICKERS[i]: float(Q[i, i]) for i in range(n)}
    quadratic = {
        (TICKERS[i], TICKERS[j]): float(Q[i, j] + Q[j, i])
        for i in range(n) for j in range(i + 1, n)
    }
    qp.minimize(constant=0.0, linear=linear, quadratic=quadratic)

    print("Solving with QAOA...")
    t0 = time.perf_counter()
    try:
        sampler = Sampler()
        optimizer = COBYLA(maxiter=100)
        qaoa = QAOA(sampler=sampler, optimizer=optimizer, reps=N_QAOA_LAYERS)
        solver = MinimumEigenOptimizer(qaoa)
        result = solver.solve(qp)
        elapsed = time.perf_counter() - t0

        selected = [TICKERS[i] for i, x in enumerate(result.x) if x > 0.5]
        n_sel = max(len(selected), 1)
        w = np.array([1.0 / n_sel if t in selected else 0.0 for t in TICKERS])
        exp_ret = float(w @ mu)
        vol = float(np.sqrt(w @ cov @ w))
        sharpe = exp_ret / (vol + 1e-10)

        return {
            "method": "QAOA",
            "n_qubits": n,
            "n_layers": N_QAOA_LAYERS,
            "selected_assets": selected,
            "optimal_weights": w.tolist(),
            "expected_return": round(exp_ret, 4),
            "volatility": round(vol, 4),
            "sharpe": round(sharpe, 4),
            "objective_value": float(result.fval),
            "elapsed_s": round(elapsed, 2),
            "tickers": TICKERS,
        }
    except Exception as e:
        return {"method": "QAOA-error", "error": str(e), "elapsed_s": round(time.perf_counter() - t0, 2)}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    returns = load_returns()

    print("\n--- Classical Markowitz Optimization ---")
    t0 = time.perf_counter()
    classical = markowitz_optimal(returns)
    classical["elapsed_s"] = round(time.perf_counter() - t0, 2)
    print(f"  return={classical['expected_return']:.4f}  vol={classical['volatility']:.4f}  sharpe={classical['sharpe']:.4f}")

    print("\n--- QAOA Quantum Portfolio Optimization ---")
    quantum = qaoa_portfolio(returns)
    if "error" not in quantum:
        print(f"  return={quantum['expected_return']:.4f}  vol={quantum['volatility']:.4f}  sharpe={quantum['sharpe']:.4f}")
    else:
        print(f"  {quantum.get('error', 'failed')}")

    result = {"classical": classical, "quantum": quantum}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nResults saved → {RESULTS_FILE}")
    return result


if __name__ == "__main__":
    main()
