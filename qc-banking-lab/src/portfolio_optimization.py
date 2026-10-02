"""
portfolio_optimization.py — QAOA Portfolio Optimization vs. Markowitz Classical Baseline.

Stocks  : RELIANCE, TCS, INFY, HDFCBANK, WIPRO  (NSE Nifty-50 historical data)
Data    : /mnt/deepa/quantum/data/stocks/*.csv
Classical: Markowitz mean-variance (scipy minimize)
Quantum  : QUBO → QAOA circuit via PennyLane
Results : results/portfolio_results.json

Run with:
    /mnt/deepa/quantum/venvs/qml/bin/python3 portfolio_optimization.py
"""

import json, time, os, warnings
import numpy as np
import pandas as pd
from scipy.optimize import minimize
import pennylane as qml
from pennylane import numpy as pnp

warnings.filterwarnings("ignore")

STOCKS_DIR   = "/mnt/deepa/quantum/data/stocks"
RESULTS_DIR  = "/mnt/deepa/quantum/qc-banking-lab/results"
RESULTS_FILE = os.path.join(RESULTS_DIR, "portfolio_results.json")
os.makedirs(RESULTS_DIR, exist_ok=True)

TICKERS = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "WIPRO"]
N       = len(TICKERS)           # 5 assets
N_BITS  = N                       # 1 binary variable per stock
RISK_PENALTY  = 0.5               # λ  in QUBO: obj = -μᵀw + λ wᵀΣw
BUDGET_LAMBDA = 5.0               # penalty for |Σwᵢ - K| ≠ 0
BUDGET_K      = 2                 # select exactly K stocks

def sep(c="─", n=72): print(c * n)
def header(t): sep("═"); print(f"  {t}"); sep("═")
def section(t): print(); sep(); print(f"  {t}"); sep()


# ══════════════════════════════════════════════════════════════════════════════
# 1. LOAD & PREPARE DATA
# ══════════════════════════════════════════════════════════════════════════════
header("QC BANKING LAB — PORTFOLIO OPTIMIZATION")
section("1 · Load Historical Price Data")

frames = {}
for tk in TICKERS:
    fp = os.path.join(STOCKS_DIR, f"{tk}.csv")
    df = pd.read_csv(fp, parse_dates=["Date"])
    df = df.sort_values("Date").set_index("Date")
    # Use 'Close' price; fallback to 'Last' if not present
    price_col = "Close" if "Close" in df.columns else "Last"
    frames[tk] = df[price_col].dropna()
    print(f"  {tk:12s}: {len(frames[tk]):,} trading days  "
          f"({frames[tk].index[0].date()} → {frames[tk].index[-1].date()})")

# Align all to common date range (last 5 years of trading data)
prices = pd.DataFrame(frames).dropna()
prices = prices.tail(min(1260, len(prices)))   # ~5 years
print(f"\n  Common window: {prices.index[0].date()} → {prices.index[-1].date()}  "
      f"({len(prices)} days)")

# Daily log returns
returns = np.log(prices / prices.shift(1)).dropna()

# Annualised stats
ann_ret  = returns.mean() * 252                   # expected annual return
ann_cov  = returns.cov()  * 252                   # annual covariance matrix
ann_std  = returns.std()  * np.sqrt(252)          # annual volatility

print("\n  Annualised expected returns:")
for tk in TICKERS:
    print(f"    {tk:12s}: μ={ann_ret[tk]*100:+.2f}%  σ={ann_std[tk]*100:.2f}%")

mu  = ann_ret.values.astype(float)
cov = ann_cov.values.astype(float)


# ══════════════════════════════════════════════════════════════════════════════
# 2. CLASSICAL BASELINE — Markowitz Mean-Variance
# ══════════════════════════════════════════════════════════════════════════════
section("2 · Classical Markowitz Mean-Variance Optimization")

RISK_FREE = 0.065   # India 10-yr bond ~ 6.5%

def portfolio_metrics(w, mu, cov, risk_free=RISK_FREE):
    ret   = float(w @ mu)
    risk  = float(np.sqrt(w @ cov @ w))
    sharpe = (ret - risk_free) / risk if risk > 1e-9 else 0.0
    return ret, risk, sharpe

def neg_sharpe(w, mu, cov, rf):
    r, s, sh = portfolio_metrics(w, mu, cov, rf)
    return -sh

# Equal-weight initial guess
w0 = np.ones(N) / N
constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
bounds      = [(0.0, 1.0)] * N

t0 = time.perf_counter()
res_markowitz = minimize(
    neg_sharpe, w0,
    args=(mu, cov, RISK_FREE),
    method="SLSQP",
    bounds=bounds,
    constraints=constraints,
    options={"ftol": 1e-9, "maxiter": 1000},
)
t_mark = (time.perf_counter() - t0) * 1000
w_mark = res_markowitz.x
w_mark = np.clip(w_mark, 0, 1); w_mark /= w_mark.sum()

ret_m, risk_m, sharpe_m = portfolio_metrics(w_mark, mu, cov)
print(f"\n  Markowitz optimal weights:")
for i, tk in enumerate(TICKERS):
    print(f"    {tk:12s}: {w_mark[i]*100:.2f}%")
print(f"\n  Annual Return : {ret_m*100:.2f}%")
print(f"  Annual Risk   : {risk_m*100:.2f}%")
print(f"  Sharpe Ratio  : {sharpe_m:.4f}")
print(f"  Runtime       : {t_mark:.1f} ms")


# ══════════════════════════════════════════════════════════════════════════════
# 3. QUBO FORMULATION
# ══════════════════════════════════════════════════════════════════════════════
section("3 · QUBO Formulation for Quantum Optimization")

# QUBO: minimize  -λ_r μᵀx + λ_r xᵀΣx + λ_b (Σxᵢ - K)²
# Variables: x ∈ {0,1}^N  (1 = include stock)
#
# Expand budget penalty: (Σxᵢ - K)² = Σxᵢ + 2Σ_{i<j}xᵢxⱼ - 2KΣxᵢ + K²
# Diagonal of Q:  Q_ii = -λ_r μᵢ + λ_r Σ_ii + λ_b(1 - 2K)
# Off-diagonal:   Q_ij = λ_r Σ_ij + λ_b   (i≠j)

Q = np.zeros((N, N))
for i in range(N):
    Q[i, i] = -RISK_PENALTY * mu[i] + RISK_PENALTY * cov[i, i] \
               + BUDGET_LAMBDA * (1 - 2 * BUDGET_K)
for i in range(N):
    for j in range(i + 1, N):
        Q[i, j] = RISK_PENALTY * cov[i, j] + BUDGET_LAMBDA
        Q[j, i] = Q[i, j]

print(f"  QUBO matrix Q ({N}×{N}) formed.")
print(f"  Budget constraint: select exactly {BUDGET_K} of {N} stocks.")
print(f"  λ_risk={RISK_PENALTY}  λ_budget={BUDGET_LAMBDA}")

# Convert QUBO to Ising h, J:  x = (1+z)/2 , z ∈ {-1,+1}
# E_ising = Σ h_i z_i + Σ_{i<j} J_ij z_i z_j  + const
h = np.zeros(N)
J = np.zeros((N, N))
const_ising = 0.0

for i in range(N):
    for j in range(N):
        if i == j:
            h[i] += Q[i, i] / 2.0
            const_ising += Q[i, i] / 4.0
        else:
            J[i, j] += Q[i, j] / 4.0
            h[i]     += Q[i, j] / 4.0

print(f"  Ising h: {np.round(h, 3)}")


# ══════════════════════════════════════════════════════════════════════════════
# 4. QUANTUM QAOA  (PennyLane · p=2 layers · 5 qubits)
# ══════════════════════════════════════════════════════════════════════════════
section("4 · Quantum QAOA  (p=2 layers, 5 qubits)")

N_LAYERS = 2          # QAOA depth p
dev_qaoa = qml.device("default.qubit", wires=N)

def cost_unitary(gamma):
    """Problem unitary: e^{-i γ H_C}."""
    # Single-qubit ZZ terms  → RZZ gates
    for i in range(N):
        for j in range(i + 1, N):
            if abs(J[i, j]) > 1e-9:
                qml.IsingZZ(2 * gamma * J[i, j], wires=[i, j])
    # Single-qubit Z terms → RZ gates
    for i in range(N):
        qml.RZ(2 * gamma * h[i], wires=i)

def mixer_unitary(beta):
    """Mixer unitary: e^{-i β H_B} = product of RX(2β)."""
    for i in range(N):
        qml.RX(2 * beta, wires=i)

@qml.qnode(dev_qaoa)
def qaoa_circuit(params):
    """QAOA circuit: |+⟩^N → p layers of (cost + mixer) → measure."""
    gammas = params[:N_LAYERS]
    betas  = params[N_LAYERS:]
    # Initial superposition
    for i in range(N):
        qml.Hadamard(wires=i)
    # QAOA layers
    for layer in range(N_LAYERS):
        cost_unitary(gammas[layer])
        mixer_unitary(betas[layer])
    # Measure cost Hamiltonian expectation
    # H_C = Σ h_i Z_i + Σ J_ij Z_i Z_j
    obs = []
    for i in range(N):
        if abs(h[i]) > 1e-9:
            obs.append(h[i] * qml.PauliZ(i))
    for i in range(N):
        for j in range(i + 1, N):
            if abs(J[i, j]) > 1e-9:
                obs.append(J[i, j] * qml.PauliZ(i) @ qml.PauliZ(j))
    if not obs:
        return qml.expval(qml.PauliZ(0))
    H = sum(obs)
    return qml.expval(H)

# Training QAOA parameters
rng = np.random.default_rng(42)
params_init = rng.uniform(0, np.pi, 2 * N_LAYERS)

print(f"  QAOA circuit: p={N_LAYERS} layers, {N} qubits")
print(f"  Optimizing with COBYLA (100 iterations) …")

call_cnt = [0]
losses_qaoa = []

def qaoa_cost(params):
    call_cnt[0] += 1
    val = float(qaoa_circuit(params))
    losses_qaoa.append(val)
    if call_cnt[0] % 25 == 0:
        print(f"    iter {call_cnt[0]:3d}  cost={val:.4f}")
    return val

t0 = time.perf_counter()
res_qaoa = minimize(qaoa_cost, params_init, method="COBYLA",
                    options={"maxiter": 100, "rhobeg": 0.5})
t_qaoa = (time.perf_counter() - t0) * 1000
params_opt = res_qaoa.x
print(f"  QAOA done in {t_qaoa/1000:.1f}s  (success={res_qaoa.success})")

# Sample the optimized circuit to get the best bit-string
@qml.qnode(dev_qaoa)
def qaoa_sample(params, shots=1024):
    gammas = params[:N_LAYERS]
    betas  = params[N_LAYERS:]
    for i in range(N):
        qml.Hadamard(wires=i)
    for layer in range(N_LAYERS):
        cost_unitary(gammas[layer])
        mixer_unitary(betas[layer])
    return qml.probs(wires=range(N))

probs = qaoa_sample(params_opt)
best_state_idx = int(np.argmax(probs))
best_bits = np.array(list(map(int, format(best_state_idx, f"0{N}b"))))

# Also scan all 2^N states for best valid QUBO solution
def qubo_energy(x):
    return float(x @ Q @ x)

best_energy = np.inf
best_x = None
for state in range(2 ** N):
    x = np.array(list(map(int, format(state, f"0{N}b"))))
    e = qubo_energy(x)
    if e < best_energy:
        best_energy = e
        best_x = x.copy()

# Use the QAOA-proposed solution first, fallback to best classical scan
x_qaoa = best_bits
e_qaoa  = qubo_energy(x_qaoa)
print(f"\n  QAOA proposed  : {x_qaoa}  QUBO energy={e_qaoa:.4f}")
print(f"  Optimal (scan) : {best_x}  QUBO energy={best_energy:.4f}")

# Build quantum portfolio (equal weight among selected stocks)
selected_qaoa = [TICKERS[i] for i in range(N) if x_qaoa[i] == 1]
if not selected_qaoa:            # fallback: pick top-2 by μ
    top2 = np.argsort(-mu)[:2]
    x_qaoa = np.zeros(N, dtype=int); x_qaoa[top2] = 1
    selected_qaoa = [TICKERS[i] for i in top2]

k_sel = len(selected_qaoa)
w_qaoa = np.zeros(N)
for i in range(N):
    if x_qaoa[i] == 1:
        w_qaoa[i] = 1.0 / k_sel

ret_q, risk_q, sharpe_q = portfolio_metrics(w_qaoa, mu, cov)

print(f"\n  QAOA selected stocks : {selected_qaoa}")
print(f"  QAOA weights         : {dict(zip(TICKERS, np.round(w_qaoa, 3)))}")
print(f"  Annual Return : {ret_q*100:.2f}%")
print(f"  Annual Risk   : {risk_q*100:.2f}%")
print(f"  Sharpe Ratio  : {sharpe_q:.4f}")
print(f"  Runtime       : {t_qaoa:.1f} ms")


# ══════════════════════════════════════════════════════════════════════════════
# 5. COMPARISON TABLE
# ══════════════════════════════════════════════════════════════════════════════
section("5 · Classical vs Quantum Portfolio Comparison")

col_w = [22, 14, 12, 12, 16]
headers_ = ["Model", "Ann. Return", "Ann. Risk", "Sharpe", "Runtime (ms)"]

def row_str(vals):
    return " │ ".join(str(v).ljust(w) for v, w in zip(vals, col_w))

print()
print("  " + row_str(headers_))
print("  " + "─┼─".join("─" * w for w in col_w))
print("  " + row_str(["Markowitz (SLSQP)",
                       f"{ret_m*100:.2f}%", f"{risk_m*100:.2f}%",
                       f"{sharpe_m:.4f}", f"{t_mark:.1f}"]))
print("  " + row_str(["QAOA (p=2, N=5)",
                       f"{ret_q*100:.2f}%", f"{risk_q*100:.2f}%",
                       f"{sharpe_q:.4f}", f"{t_qaoa:.1f}"]))
print()

# ── Save JSON ─────────────────────────────────────────────────────────────────
output = {
    "dataset"      : "NSE Nifty-50 historical prices",
    "tickers"      : TICKERS,
    "data_window"  : f"{prices.index[0].date()} to {prices.index[-1].date()}",
    "n_trading_days": len(prices),
    "risk_free_rate": RISK_FREE,
    "budget_K"     : BUDGET_K,
    "classical_markowitz": {
        "method"       : "Scipy SLSQP — Sharpe maximization",
        "weights"      : {tk: round(float(w), 4) for tk, w in zip(TICKERS, w_mark)},
        "annual_return": round(ret_m, 4),
        "annual_risk"  : round(risk_m, 4),
        "sharpe_ratio" : round(sharpe_m, 4),
        "runtime_ms"   : round(t_mark, 2),
    },
    "quantum_qaoa": {
        "method"       : "QAOA p=2 via PennyLane — QUBO binary selection",
        "n_qubits"     : N,
        "n_layers"     : N_LAYERS,
        "qubo_lambda_risk"  : RISK_PENALTY,
        "qubo_lambda_budget": BUDGET_LAMBDA,
        "selected_stocks"   : selected_qaoa,
        "weights"      : {tk: round(float(w), 4) for tk, w in zip(TICKERS, w_qaoa)},
        "annual_return": round(ret_q, 4),
        "annual_risk"  : round(risk_q, 4),
        "sharpe_ratio" : round(sharpe_q, 4),
        "runtime_ms"   : round(t_qaoa, 2),
    },
    "analysis": {
        "winner_by_sharpe": (
            "Markowitz" if sharpe_m >= sharpe_q else "QAOA"
        ),
        "quantum_notes": (
            "QAOA solves a binary (combinatorial) portfolio-selection QUBO: "
            "which K stocks to hold. Markowitz solves a continuous QP: how much "
            "of each stock to hold. Both formulations are valid; they answer "
            "different sub-problems. QAOA advantage grows with N (combinatorial "
            "explosion) but requires deep fault-tolerant circuits for N>20."
        ),
    },
}

with open(RESULTS_FILE, "w") as f:
    json.dump(output, f, indent=2)

print(f"  Results saved → {RESULTS_FILE}")
sep("═")
print("  PORTFOLIO OPTIMIZATION COMPLETE")
sep("═")
