# Q01 Algorithms — User Stories

## Overview
Foundational quantum algorithms (Shor, Grover, VQE, QAOA) demonstrating exponential or quadratic speedup over classical counterparts, with classical simulation and benchmark comparison.

## User Stories

### US-01: Researcher — Factor a Semiprime with Shor's Algorithm
**As a** quantum computing researcher, **I want** to run Shor's algorithm on N=15 **so that** I can observe the period-finding step and verify it returns factors [3, 5].
**Acceptance Criteria:**
- [ ] Algorithm identifies coprime base a and finds period r correctly
- [ ] Returns factors (3, 5) from period-based GCD computation
- [ ] Reports qubit count required for quantum period-finding register
- [ ] Compares classical trial-division timing vs quantum simulation timing

### US-02: Developer — Run Grover Search on Small Database
**As a** developer, **I want** to search a 4-item database with Grover's algorithm **so that** I can confirm the √N speedup over classical linear search.
**Acceptance Criteria:**
- [ ] Oracle marks exactly 1 target item
- [ ] Algorithm finds the target in ~1 iteration (optimal for N=4)
- [ ] Classical search requires up to 4 queries; Grover requires 1
- [ ] Success probability printed after each iteration

### US-03: Chemist — Minimize H2 Ground-State Energy with VQE
**As a** computational chemist, **I want** to run VQE on the H2 molecule Hamiltonian **so that** I can obtain the ground-state energy and compare with FCI reference.
**Acceptance Criteria:**
- [ ] Hamiltonian encoded via Bravyi–Kitaev transform (2-qubit)
- [ ] Variational optimizer converges within 200 iterations
- [ ] Energy within 1e-3 Ha of FCI reference (−1.137 Ha)
- [ ] Outputs final ansatz parameters and convergence curve

### US-04: Optimizer — Solve Max-Cut with QAOA
**As a** combinatorial optimizer, **I want** to apply QAOA to a 6-node graph **so that** I can benchmark approximation ratio against the classical best cut.
**Acceptance Criteria:**
- [ ] QAOA circuit built with p=2 layers
- [ ] Optimizer finds γ, β parameters maximizing cut value
- [ ] Approximation ratio ≥ 0.88 vs. classical brute-force
- [ ] Outputs bitstring solution and cut weight

### US-05: Educator — Visualize Quantum Phase Estimation
**As a** quantum educator, **I want** to view the phase estimation step of Shor's algorithm **so that** I can explain it to students without full Qiskit simulation.
**Acceptance Criteria:**
- [ ] Circuit structure described textually (register sizes, QFT, controlled-U)
- [ ] Qubit count formula n ≈ 2 log₂(N) displayed
- [ ] Example eigenphase printed for N=15

### US-06: Engineer — Benchmark Algorithm Scaling
**As a** systems engineer, **I want** to compare classical vs quantum steps for increasing problem sizes **so that** I can build a scaling chart.
**Acceptance Criteria:**
- [ ] Benchmark CSV generated with columns: algorithm, problem_size, classical_steps, quantum_steps, speedup_factor
- [ ] Covers at least 5 problem sizes per algorithm
- [ ] CSV saved to data/algorithm_benchmarks.csv

### US-07: DevOps — Run Full Demo Without External QPU
**As a** DevOps engineer, **I want** to run demo.py with numpy only (no Qiskit/PennyLane required) **so that** the CI pipeline validates logic without quantum dependencies.
**Acceptance Criteria:**
- [ ] demo.py exits 0 with numpy-only fallback path
- [ ] All steps print PASS
- [ ] Results JSON written to results/q01_results.json

### US-08: Analyst — Export Algorithm Results to JSON
**As a** data analyst, **I want** a structured JSON results file **so that** I can load metrics into the quantum portal dashboard.
**Acceptance Criteria:**
- [ ] results/q01_results.json contains shor_n15_factors, grover_speedup, vqe_energy, qaoa_approximation_ratio
- [ ] File is valid JSON with a "generated" timestamp
- [ ] All numeric values match expected quantum-theory predictions

## Input / Process / Output

| Stage | Description |
|-------|-------------|
| **Input** | Integer N for Shor (N=15); database size for Grover (N=4); H2 geometry for VQE; graph adjacency matrix for QAOA |
| **Process** | Classical simulation of quantum period-finding; amplitude amplification; variational energy minimization via SPSA/COBYLA; parameterized quantum circuit optimization |
| **Output** | Prime factors of N; marked item index; ground-state energy in Hartree; Max-Cut bitstring and approximation ratio; benchmark CSV |

## Demo Workflow
1. Run Shor on N=15: pick a=2, find period r=4, compute GCD(a^(r/2)±1, N) → factors [3, 5]
2. Run Grover on 4-item database: apply oracle + diffusion 1 time, measure marked item
3. Run VQE: optimize 2-qubit H2 Hamiltonian with RY ansatz, report energy = −1.137 Ha
4. Run QAOA: optimize Max-Cut on 6-node graph with p=2, report approximation ratio ≥ 0.88
5. Write results to results/q01_results.json
