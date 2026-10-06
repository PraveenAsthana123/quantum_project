# QC Logistics Lab — Quantum Optimization for Vehicle Routing & Supply Chain

**Status: Research / Portfolio**  
**Author:** PraveenAsthana123  
**Date:** 2026-09-22  
**Stack:** PennyLane 0.45.1 · scikit-learn 1.9.1 · SciPy 1.18.1 · NumPy 2.5.3  

---

## Problem Statement

Vehicle Routing Problem (VRP) is NP-hard. The number of feasible routes for N cities grows
as (N-1)!/2 — for 20 cities that is ~1.2 × 10^17 combinations. Classical exact solvers
(branch-and-bound, dynamic programming) become intractable beyond ~50 cities.

**Why quantum?** Quantum algorithms like QAOA can explore exponentially large solution spaces
via superposition and interference. QUBO (Quadratic Unconstrained Binary Optimization)
maps VRP to a Hamiltonian whose ground state encodes the optimal route. A fault-tolerant
quantum computer running QAOA could in principle find near-optimal routes faster than any
classical algorithm for large N.

**Why now?** Benchmarking on NISQ simulators today establishes the methodology, validates
the QUBO formulation, and measures the approximation ratio — so the code is ready when
hardware matures.

---

## Datasets

| Dataset | Source | Size | Use |
|---|---|---|---|
| `data/routing/distance.csv` | Custom logistics network | 62 cities, 3 782 edges | VRP distance matrix |
| `data/routing/order_small.csv` | Same network | 10 orders | Small VRP instance |
| `data/routing/order_large.csv` | Same network | 4 635 orders | Large VRP instance |
| `datasets/logistics/DataCoSupplyChainDataset.csv` | DataCo / Kaggle | 180 519 rows × 53 cols | Late-delivery classification |
| `data/vrp/data/Solomon/` | Solomon VRPTW benchmarks | 56 instances | Standard benchmarks |

---

## Methods Compared

### VRP Benchmark (`src/vrp_benchmark.py`)

| Method | Problem | Cities | Vehicles | Cap |
|---|---|---|---|---|
| NN Greedy (OR-Tools fallback) | CVRP | 6 | 2 | 50 |
| Simulated Annealing | CVRP | 6 | 2 | 50 |
| QAOA p=1 | TSP (sub-problem) | 3 | — | — |
| QAOA p=2 | TSP (sub-problem) | 3 | — | — |

### Supply Chain (`src/supply_chain_quantum.py`)

| Method | Task | Features |
|---|---|---|
| Logistic Regression | Late-delivery risk | All 13 features |
| Random Forest (100 trees) | Late-delivery risk | All 13 features |
| VQC (4 qubits × 2 layers) | Late-delivery risk | PCA top-4 |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     QC Logistics Lab                             │
├─────────────────┬───────────────────┬───────────────────────────┤
│  Classical Path │  Quantum Path     │  Supply Chain Path        │
├─────────────────┼───────────────────┼───────────────────────────┤
│                 │                   │                           │
│  distance.csv   │  distance.csv     │  DataCoSupplyChain.csv    │
│       │         │       │           │       │                   │
│       ▼         │       ▼           │       ▼                   │
│  Build N×N      │  Extract N=3      │  Feature Engineering      │
│  dist matrix    │  city sub-matrix  │  (13 numeric/cat feats)   │
│       │         │       │           │       │                   │
│       ▼         │       ▼           │       ▼                   │
│  NN Greedy      │  Build QUBO       │  StandardScaler           │
│  (CVRP)         │  (N²×N² matrix)   │  + PCA(4 components)      │
│       │         │       │           │       │                   │
│       ▼         │       ▼           │       ▼                   │
│  Simulated      │  QUBO → Ising     │  LR / RF (full feats)     │
│  Annealing 2opt │  (h, J mapping)   │  VQC  (PCA-4 feats)       │
│       │         │       │           │       │                   │
│       ▼         │       ▼           │       ▼                   │
│  VRP Routes     │  Build QAOA       │  Predict                  │
│  + distances    │  circuit (9q)     │  Late_delivery_risk       │
│                 │       │           │                           │
│                 │       ▼           │                           │
│                 │  COBYLA optimize  │                           │
│                 │  γ, β params      │                           │
│                 │       │           │                           │
│                 │       ▼           │                           │
│                 │  Statevector      │                           │
│                 │  decode best      │                           │
│                 │  feasible route   │                           │
└─────────────────┴───────────────────┴───────────────────────────┘
                          │
                          ▼
              results/vrp_benchmark_results.json
              results/supply_chain_results.json
```

---

## Results — Real Numbers (Run: 2026-09-22)

### VRP Benchmark (6-city CVRP, distances in km)

| Method | Total Distance | Gap to Reference | Runtime |
|---|---|---|---|
| NN Greedy (reference) | 696 km | 0% | 0.02 ms |
| Simulated Annealing | 464 km | −33.3% (better) | 7.81 ms |
| QAOA p=1 (3-city TSP) | 100.83 km | — (different scope) | 505 ms |
| QAOA p=2 (3-city TSP) | 100.83 km | — (different scope) | 1 601 ms |

**QAOA approximation ratio (optimal / QAOA cost): 1.000**  
Both p=1 and p=2 found the exact optimal 3-city TSP tour via statevector decoding.

> Note: SA beats NN Greedy on 6-city CVRP because 2-opt moves find a better tour
> ordering before splitting to vehicles. NN Greedy is a fast constructive heuristic,
> not an optimal solver (OR-Tools was not available in this environment).

### Supply Chain Late-Delivery Classification (180 K rows, 5 000 sampled)

| Method | Accuracy | Precision | F1 | ROC-AUC | Runtime |
|---|---|---|---|---|---|
| Logistic Regression | 0.970 | 0.949 | 0.974 | — | 295 ms |
| Random Forest (100 trees) | 0.997 | 0.995 | 0.997 | 1.000 | 386 ms |
| VQC (4 qubits, 200 samples) | 0.630 | 0.679 | 0.661 | — | 43 267 ms |

PCA(4 components) explained variance: **63.2%**

---

## QAOA Technical Details

```
QUBO formulation (TSP, N cities):
  Variables:  x_{i,p} ∈ {0,1}  →  city i at position p
  n_qubits = N²  (N=3 → 9 qubits)

  Objective:  ∑_{i,j,p} d[i,j] · x_{i,p} · x_{j,p+1 mod N}

  Constraints (penalty λ):
    (a) ∑_p x_{i,p} = 1  ∀i    (each city visited once)
    (b) ∑_i x_{i,p} = 1  ∀p    (each position filled once)

QUBO → Ising:  x = (1 - z)/2
  → h_i Z_i terms  +  J_{ij} Z_i Z_j terms

QAOA circuit:
  |ψ₀⟩ = H^⊗n |0⟩        (uniform superposition)
  for layer in [1..p]:
    U_C(γ) = exp(-iγ H_cost)   (cost unitary via ApproxTimeEvolution)
    U_B(β) = exp(-iβ H_mix)    (X-mixer unitary)

Optimiser: COBYLA (gradient-free)
Decoder:   full statevector → argmax probability over feasible bitstrings
```

---

## When Quantum Wins (Honest NISQ-era Analysis)

| Scale | Quantum Status |
|---|---|
| N = 3-4 cities (9-16 qubits) | QAOA works as a proof-of-concept on simulators. Finds optimal for simple instances. |
| N = 6-8 cities (36-64 qubits) | Borderline IBM Eagle/Heron. Noise makes results unreliable without error mitigation. |
| N = 10-20 cities (100-400 qubits) | Beyond current fault-tolerant capability. Classical heuristics (SA, LKH) still win easily. |
| N > 1 000 cities | Classical branch-and-bound becomes exponential. Theoretical QAOA advantage possible with fault-tolerant QC. |

**Honest assessment:** NISQ-era QAOA (p ≤ 10, noisy hardware) does **not** currently surpass
classical heuristics on VRP at any practical scale. The value of this work is:
1. Proving the QUBO formulation and circuit are correct (ratio = 1.00 on N=3)
2. Establishing runtime/qubit baseline for scaling analysis
3. Building the pipeline ready for fault-tolerant hardware

For supply chain classification: VQC with 200 training samples achieves 63% accuracy vs
RF's 99.7% — the gap is almost entirely explained by the training-size constraint (VQC
forward pass costs ~215 ms/sample on CPU). With quantum hardware and kernel-based QML,
the gap narrows for datasets with quantum-structured correlations.

---

## Tech Stack

```
Quantum:
  PennyLane 0.45.1       — circuit simulation, QAOA, VQC
  default.qubit          — statevector simulator (noise-free)
  ApproxTimeEvolution    — Hamiltonian cost/mixer unitaries
  COBYLA (SciPy)         — gradient-free variational optimiser

Classical:
  scikit-learn 1.9.1     — LR, RF, PCA, StandardScaler
  NumPy 2.5.3            — matrix operations, QUBO construction
  SciPy 1.18.1           — COBYLA, sparse operations
  Pandas 3.0.6           — data loading and preprocessing

Data:
  Custom 62-city routing dataset (edge-list CSV)
  DataCo Supply Chain Dataset (Kaggle, 180 K rows)
  Solomon VRPTW benchmark instances (56 files)
```

---

## How to Run

```bash
# Activate environment
source /mnt/deepa/quantum/venvs/qml/bin/activate

# VRP benchmark (classical vs QAOA)
python qc-logistics-lab/src/vrp_benchmark.py

# Supply chain quantum classification
python qc-logistics-lab/src/supply_chain_quantum.py

# Results are saved to:
#   qc-logistics-lab/results/vrp_benchmark_results.json
#   qc-logistics-lab/results/supply_chain_results.json
```

**Expected runtimes:**
- VRP benchmark: ~3 seconds (QAOA p=1 ≈ 0.5s, p=2 ≈ 1.6s with 9 qubits)
- Supply chain: ~50 seconds (VQC on 200 samples × 50 COBYLA iterations)

---

## File Structure

```
qc-logistics-lab/
├── src/
│   ├── vrp_benchmark.py          # Main VRP benchmark (this file)
│   └── supply_chain_quantum.py   # Supply chain VQC benchmark
├── results/
│   ├── vrp_benchmark_results.json
│   └── supply_chain_results.json
├── data/                          # Symlinked to /mnt/deepa/quantum/data/
├── notebooks/
├── tests/
├── ui/
├── requirements.txt
└── README_PORTFOLIO.md            # This file
```

---

## References

1. Farhi, E., Goldstone, J., & Gutmann, S. (2014). A Quantum Approximate Optimization Algorithm. *arXiv:1411.4028*
2. Lucas, A. (2014). Ising formulations of many NP problems. *Frontiers in Physics, 2*, 5.
3. Harwood, S. et al. (2021). Formulating and Solving Routing Problems on Quantum Computers. *IEEE TQCE, 2*, 1–17.
4. Benedetti, M. et al. (2019). Parameterized quantum circuits as machine learning models. *Quantum Science and Technology, 4*(4), 043001.

---

*Generated by QC Logistics Lab pipeline · PennyLane 0.45.1 · 2026-09-22*
