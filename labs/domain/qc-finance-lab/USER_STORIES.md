# QC Finance Lab — User Stories

Version: 1.0.0 | Date: 2026-10-06 | Lab: qc-finance-lab

---

## US-001: European Option Price Validation

**As a** quant analyst
**I want** to compare Black-Scholes analytical prices with Quantum Amplitude Estimation (QAE) outputs for European calls
**so that** I can quantify the pricing error introduced by circuit discretisation and identify when QAE is accurate enough for production use.

**Acceptance criteria:**
- Black-Scholes and QAE are run on identical parameters (S=100, K=105, T=0.5, r=0.05, sigma=0.20).
- Absolute pricing error between QAE and Black-Scholes is printed in dollars.
- Both results and the 95 % confidence interval are saved to `data/options_results.json`.
- Script completes in under 120 s on the local simulator.

**Demo:**
1. Run `python src/quantum_options.py`.
2. Check `data/options_results.json` for `comparison.qae_vs_bs_error`.

---

## US-002: Synthetic Options Data Generation

**As a** data scientist
**I want** to generate 2,000 rows of synthetic options pricing data covering a wide range of moneyness and tenors
**so that** I can train and evaluate ML pricing models without exposure to proprietary market data.

**Acceptance criteria:**
- Output CSV has columns: S, K, T, r, sigma, option_type, option_price, theo_price, moneyness, log_moneyness.
- Calls and puts are approximately equally split (±5 %).
- Prices are computed using the exact Black-Scholes formula with a configurable noise fraction (default 5 %).
- File is reproducible: re-running with seed=42 produces byte-identical output.

**Demo:**
1. Run `python src/generate_data.py`.
2. Check `data/options_synthetic.csv` — verify `df["option_type"].value_counts()` is approximately balanced.

---

## US-003: ML Pricing Benchmark

**As a** quant analyst
**I want** to benchmark LinearRegression and RandomForestRegressor against Black-Scholes on the synthetic options dataset
**so that** I can assess whether ML models learn the non-linear pricing surface without overfitting.

**Acceptance criteria:**
- Both models are trained on an 80/20 random split.
- MAE and RMSE are reported on the held-out test set alongside inference time in ms.
- RandomForest RMSE is lower than LinearRegression RMSE (ML captures non-linearity).
- All metrics are printed in a formatted comparison table.

**Demo:**
1. Run `python src/demo.py`.
2. Step 4 and Step 5 print the comparison table — confirm RF RMSE < LR RMSE.

---

## US-004: Risk Manager Greeks Dashboard

**As a** risk manager
**I want** to compute and display the full set of Black-Scholes Greeks (delta, gamma, vega, theta, rho) for a portfolio of options
**so that** I can monitor net Greeks exposure and hedge accordingly.

**Acceptance criteria:**
- `quantum_options.py` exports `black_scholes_call(S, K, T, r, sigma)` returning a dict with price + all Greeks.
- Greeks are correct to four decimal places (verified against QuantLib reference values for S=100 K=105 T=0.5).
- Delta is in [0, 1] for calls; vega is non-negative; theta is negative.
- Results are stored in `data/options_results.json` under the `black_scholes` key.

**Demo:**
1. Run `python -c "from src.quantum_options import black_scholes_call; import pprint; pprint.pprint(black_scholes_call(100,105,0.5,0.05,0.20))"`.

---

## US-005: Options Trader RMSE Gate

**As a** options trader
**I want** the demo pipeline to fail loudly if any pricing model's RMSE exceeds $5.00
**so that** I have an automated guard against degraded model quality before deployment to the pricing engine.

**Acceptance criteria:**
- `demo.py` Step 6 prints PASS / FAIL per model based on RMSE < 5.0.
- Overall exit status reflects the gate: if any model fails, the script exits with code 1 (future enhancement).
- The RMSE threshold is documented in the demo docstring for auditability.
- Black-Scholes RMSE reflects only market noise (expected < 1.0) and always passes.

**Demo:**
1. Run `python src/demo.py` — observe all three PASS lines in Step 6.

---

## US-006: Volatility Surface Visualisation

**As a** portfolio manager
**I want** to view the implied volatility smile curve across strikes for a given expiry
**so that** I can assess skew, kurtosis, and risk-reversal structure before entering a new position.

**Acceptance criteria:**
- `quantum_options.py` exports `implied_vol_surface(S, T, r)` returning a list of dicts with strike, moneyness, implied_vol, delta.
- The surface is saved to `data/options_results.json` under `implied_vol_surface`.
- At least 13 strike points spanning 0.7×S to 1.3×S are returned.
- A synthetic Heston-like skew (negative for calls, convex curve) is used when real market data is absent.

**Demo:**
1. Run `python src/quantum_options.py`.
2. Open `data/options_results.json` — plot `surface[*].strike` vs `surface[*].implied_vol` in a notebook.

---

## US-007: Put-Call Parity Verification

**As a** quant analyst
**I want** an automated put-call parity check after every pricing run
**so that** I can catch model implementation bugs before they propagate into the trading system.

**Acceptance criteria:**
- `quantum_options.py` exports `put_call_parity_check(S, K, T, r, sigma)` returning a dict with call price, put price, theoretical parity value, and a boolean `parity_satisfied`.
- `parity_satisfied` is True when `|C - P - (S - K·e^{-rT})| < 1e-8`.
- Result is included in `data/options_results.json`.
- Demo prints the parity check result inline.

**Demo:**
1. Run `python src/quantum_options.py` — observe "Put-call parity satisfied: True" in output.

---

## US-008: Monte Carlo Confidence Interval Reporting

**As a** risk manager
**I want** Monte Carlo option pricing to report a 95 % confidence interval alongside the point estimate
**so that** I can communicate model uncertainty to trading desks and regulators.

**Acceptance criteria:**
- `monte_carlo_call()` returns `price`, `std_error`, and `ci_95` tuple.
- With N=100,000 paths the CI width is less than $0.10.
- The CI is reported on the console during `demo.py` Step 3 or `quantum_options.py` main run.
- Results are saved to `data/options_results.json` under `monte_carlo`.

**Demo:**
1. Run `python src/quantum_options.py` — observe MC price and CI in Step 2/4 output.
2. Check `data/options_results.json` key `monte_carlo.ci_95`.
