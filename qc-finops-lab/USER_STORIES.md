# QPU FinOps Lab — User Stories

Version: 1.0 | Date: 2026-10-06 | Lab: qc-finops-lab

---

## US-01 — QPU Platform Engineer: Job Cost Visibility

**As a** QPU platform engineer managing multi-cloud quantum workloads,
**I want to** see the per-job cost broken down by provider, algorithm, and month,
**So that** I can identify cost anomalies and route future jobs to cheaper backends.

**Acceptance Criteria:**
- Provider cost comparison table (IBM / AWS / Azure / Google) with p50 and p99 percentiles
- Per-algorithm average cost and average execution time
- Cost exported to CSV for downstream BI tooling
- Demo runs end-to-end in under 30 seconds on a laptop

---

## US-02 — FinOps Analyst: Monthly Budget Forecasting

**As a** FinOps analyst responsible for the quantum compute budget,
**I want to** see a 3-month rolling forecast with a 95% confidence interval,
**So that** I can flag budget overruns before they happen and request additional headroom.

**Acceptance Criteria:**
- Forecast uses real historical monthly totals from qpu_jobs.csv
- 95% CI bounds are displayed per month
- ON BUDGET / RISK status shown against a configurable budget ceiling ($2,000 default)
- Cheapest provider recommendation included in forecast output

---

## US-03 — Research Scientist: Algorithm Resource Planning

**As a** research scientist preparing a Shor / VQE / Grover experiment,
**I want to** know the logical qubit count, T-gate count, and feasibility tier before submitting,
**So that** I can decide whether to run on current NISQ hardware or target a 2028 fault-tolerant device.

**Acceptance Criteria:**
- ResourceEstimator returns logical qubits, physical qubits, code distance, and runtime
- Feasibility label: current_hardware / near_term_2028 / fault_tolerant_only / theoretical_only
- VQE estimate includes ansatz layers and total shots needed
- All estimates are reproducible closed-form calculations (no simulation required)

---

## US-04 — CTO: Cloud Provider Cost Comparison

**As a** CTO approving multi-cloud quantum spending,
**I want to** see a side-by-side cost table for the same job across IBM, AWS, Azure, and Google,
**So that** I can justify vendor selection decisions to the board.

**Acceptance Criteria:**
- QPUCostModeler.compare_providers() runs all four providers for a given job
- Output includes cost_usd, latency_ms, and fidelity_score per provider
- Google ($0 research partner) is clearly labeled with its queue-latency trade-off
- Infeasible providers (qubit count exceeded) labeled "infeasible" rather than erroring

---

## US-05 — QPU Platform Engineer: Priority Scheduling

**As a** QPU platform engineer operating a shared quantum cluster,
**I want to** submit jobs with CRITICAL / HIGH / NORMAL / LOW priority and have the scheduler respect deadlines,
**So that** urgent production jobs are never starved by large research workloads.

**Acceptance Criteria:**
- QPUScheduler implements EDF + FIFO tie-breaking within each priority tier
- Anti-starvation aging promotes LOW jobs after a configurable threshold
- schedule_next() returns the correct job in O(log n) time
- Throughput stats (dispatched, queue depth, avg wait) available after scheduling

---

## US-06 — FinOps Analyst: Cost Optimization Recommendations

**As a** FinOps analyst reviewing a batch of QPU job submissions,
**I want to** receive concrete cost-reduction suggestions (shot reduction, provider arbitrage, simulator offload),
**So that** I can present a cost-reduction plan with quantified savings to engineering leads.

**Acceptance Criteria:**
- circuit_cost_optimization() returns suggestions sorted by savings_usd descending
- Each suggestion includes: strategy name, description, new parameters, savings_usd, savings_pct
- Shot reduction uses Chebyshev bound (ε = 5%)
- Simulator offload flagged for circuits ≤ 24 qubits and depth ≤ 30

---

## US-07 — Research Scientist: QEC Overhead Awareness

**As a** research scientist designing a fault-tolerant algorithm,
**I want to** know the surface-code physical qubit overhead and T-factory cost for my logical circuit,
**So that** I can set realistic hardware requirements in my grant proposals.

**Acceptance Criteria:**
- estimate_qec_overhead() returns code distance d, physical qubits, ancilla count, and T-factory qubits
- Overhead ratio (physical / logical) displayed
- Magic state distillation factory size (15-to-1 protocol) included
- Reference to Fowler et al. 2012 and Bravyi & Haah 2012 cited in output

---

## US-08 — CTO: Monthly Executive Dashboard

**As a** CTO reviewing quantum program ROI each month,
**I want to** see a one-page summary of total spend, job success rate, top algorithms by cost, and next-quarter forecast,
**So that** I can decide whether to expand or constrain the quantum compute budget for the next fiscal quarter.

**Acceptance Criteria:**
- Monthly totals aggregated from qpu_monthly_summary.json
- Success rate computed per month and overall
- Top 3 algorithms by total cost highlighted
- 3-month budget forecast with CI printed at end of demo
- All output is terminal-printable (no GUI required)
