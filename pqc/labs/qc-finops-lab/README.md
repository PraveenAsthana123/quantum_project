# QPU FinOps & Scheduling Lab

Cost modelling, job scheduling, resource estimation, and FinOps reporting for
quantum computing workloads across IBM Quantum, AWS Braket, Azure Quantum, and
Google Cirq.

## What it does

| Module | Key function |
|---|---|
| `qpu_cost_model.py` | Prices any QPU job across 4 cloud providers using real 2024 tariffs |
| `qpu_scheduler.py` | Priority + EDF queue with aging, concurrency limits, and cost gating |
| `resource_estimator.py` | Closed-form qubit / gate / runtime estimates for Shor, Grover, VQE, QAOA, QEC |
| `finops_dashboard.py` | Monthly reports, z-score anomaly alerts, ROI, spend forecasting, shot optimisation, carbon footprint |

## How to run

```bash
cd qc-finops-lab
pip install -r requirements.txt

# Run all tests
python -m pytest tests/test_finops.py -v

# Quick smoke-test
python -c "
import sys; sys.path.insert(0, 'src')
from qpu_cost_model import QPUJob, QPUCostModeler
job = QPUJob(circuit_depth=20, n_qubits=10, n_shots=8192, gate_count=120, error_rate=0.001)
for e in QPUCostModeler().compare_providers(job):
    print(e.summary())
"
```

## Key outputs

- **Cost comparison** (4 providers, sorted by USD): `QPUCostModeler.compare_providers(job)`
- **Monthly budget plan**: `QPUCostModeler.monthly_budget_plan(jobs_per_day=10, budget_usd=500)`
- **Resource estimate** (Shor RSA-2048): `ResourceEstimator().estimate_shor_rsa(2048)`
- **Feasibility label**: `"current_hardware" | "near_term_2028" | "fault_tolerant_only" | "theoretical_only"`
- **Anomaly detection**: `FinOpsDashboard().cost_anomaly_detection(spend_history)`
- **Shot optimisation** (Chebyshev ε=5%): `FinOpsDashboard().optimize_shot_count(0.05, 100000)`
