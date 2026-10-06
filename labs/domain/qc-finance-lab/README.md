# Quantum Finance Lab

Quantum computing applications for quantitative finance — portfolio optimisation,
options pricing, and risk management.

Part of the **30-project Quantum Computing Portfolio** at `/mnt/deepa/quantum/`.

---

## Structure

```
qc-finance-lab/
├── src/
│   ├── classical_baseline.py   # Markowitz, SMA strategy, Bitcoin stats
│   ├── quantum_options.py      # QAE options pricing vs Black-Scholes/MC
│   └── quantum_risk.py         # Quantum VaR via QAE vs classical methods
├── data/                       # Output JSON results (auto-created)
├── notebooks/                  # Jupyter notebooks (exploratory)
├── tests/                      # Unit tests
├── requirements.txt
└── README.md
```

---

## Datasets

Sourced from `/mnt/deepa/quantum/datasets/finance/`:

| File | Description |
|------|-------------|
| `all_stocks_2006-01-01_to_2018-01-01.csv` | 30 Dow components, daily OHLCV |
| `AAPL_*.csv`, `MSFT_*.csv`, … | Per-ticker daily prices (2006–2018) |
| `btcusd_1-min_data.csv` | Bitcoin/USD 1-minute OHLCV |

---

## Modules

### `classical_baseline.py`

- **Markowitz portfolio optimisation** — Monte Carlo efficient frontier (10,000 portfolios)
  + scipy SLSQP max-Sharpe and min-variance exact solutions across 8 Dow stocks.
- **SMA crossover backtest** — dual moving-average strategy (20/60-day) on AAPL
  with full equity curve, alpha, Sharpe, max-drawdown.
- **Bitcoin daily statistics** — resampled from 1-min data; annualised volatility,
  yearly Sharpe, max drawdown.

Output: `data/classical_results.json`

```bash
python src/classical_baseline.py
```

### `quantum_options.py`

European call option pricing comparison:

| Method | Complexity |
|--------|-----------|
| Black-Scholes (analytical) | O(1) |
| Monte Carlo (100k paths) | O(1/√N) |
| Quantum Amplitude Estimation | O(1/N) — quadratic speedup |

Implements:
- Full Black-Scholes Greeks (delta, gamma, vega, theta, rho)
- Confidence-interval Monte Carlo
- **IQAE (Iterative QAE)** via `qiskit-finance` — log-normal distribution
  encoding + linear amplitude function for call payoff
- PennyLane fallback (amplitude-embedded discrete distribution)
- Implied volatility surface / vol smile (synthetic Heston-like skew)
- Put-call parity verification

Output: `data/options_results.json`

```bash
python src/quantum_options.py
```

### `quantum_risk.py`

Value at Risk (VaR) and Conditional VaR computed four ways for a
5-stock, $1M portfolio (AAPL, MSFT, GOOGL, AMZN, GS):

| Method | Notes |
|--------|-------|
| Historical Simulation | Non-parametric, captures fat tails |
| Parametric Normal | Closed-form, t-distribution variant |
| Monte Carlo Cholesky | Multivariate normal with correlation |
| **Quantum QAE** | Amplitude-estimates tail probability, O(1/N) |

Also computes:
- Rolling annual VaR (2009–2017)
- Stress tests: 1987 crash, 2008 GFC, 2020 COVID, 2σ/3σ events
- Actual worst days from dataset (2008, 2011)

Output: `data/risk_results.json`

```bash
python src/quantum_risk.py
```

---

## Quantum Advantage Note

Classical Monte Carlo achieves ε-precision in VaR/option price with O(1/ε²) samples.
Quantum Amplitude Estimation achieves the same ε with O(1/ε) oracle queries —
a **quadratic speedup**. For financial institutions running millions of risk
calculations daily, this translates to significant compute cost reduction once
fault-tolerant quantum hardware matures.

---

## Installation

```bash
# From the lab root
pip install -r requirements.txt

# Minimal (no quantum, classical only)
pip install numpy pandas scipy scikit-learn matplotlib
```

Qiskit packages require Python 3.8–3.11. PennyLane is the fallback when
`qiskit-finance` or `qiskit-algorithms` are not installed.

---

## Running All Modules

```bash
cd /mnt/deepa/quantum/qc-finance-lab

python src/classical_baseline.py
python src/quantum_options.py
python src/quantum_risk.py
```

Results land in `data/` as JSON, ready for the portal API at `/api/main.py`.
