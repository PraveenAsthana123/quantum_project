# Quantum Lab Session Notes

## Goal
Build complete quantum computing portfolio for Praveen Asthana's job applications.

## What's Built
- 30 quantum project folders at /mnt/deepa/quantum/
- qlab CLI: `/mnt/deepa/quantum/qlab` (in PATH via ~/.bashrc)
- Global portal: http://localhost:8765 (Streamlit)
- 3 fully implemented projects:
  - pqc-control-tower: PQC benchmark + crypto inventory + migration planner + UI
  - qc-banking-lab: Classical (XGBoost 99.95% AUC) + Quantum VQC + Portfolio QAOA + UI
  - qc-logistics-lab: OR-Tools VRP + QAOA TSP + UI
- 27 scaffolded projects (src + ui + notebooks + tests stubs)
- Kaggle datasets downloaded: creditcard fraud, NIFTY50 stocks, VRPTW benchmarks, routing

## URLs
- Global portal: http://localhost:8765 (or http://0.0.0.0:8765)
- Banking lab UI: http://localhost:8501
- Launch more: qlab run <project-id>

## Commands
```bash
qlab list            # see all 30 projects
qlab status          # ready/partial/scaffold counts
qlab info <id>       # project details
qlab run <id>        # launch UI (streamlit, port auto-assigned)
qlab portal          # global portal on 8765
qlab data <id>       # kaggle download for project
qlab setup <id>      # pip install requirements
```

## Next Steps
- Implement src code for q01-algorithms through q27-clocks
- One project at a time: say "build q01" to start next project

## 2026-10-01 — Independent quantum review
- Review saved in docs/audits/2026-10-01-review.md. Crypto suite: 108 passed. Highest priorities: truthful run outcomes, leakage-free comparable benchmarks, access control, live/source security-route drift and deployment reproducibility. No application fixes or deployment performed.

## 2026-10-01 — Demo and production plan
- Created docs/plans/quantum-demo-production-plan.md and quantum-readiness-tasks.csv: 25 tasks, G0–G4 evidence gates, five guided demos, authenticated research pilot and operational acceptance. All tasks NOT_STARTED. First slice: source inventory, deployment drift, truthful execution and leakage-free preprocessing. Planning only; no services changed.
