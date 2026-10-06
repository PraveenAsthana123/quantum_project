"""
QPU FinOps Lab — CLI Demo Script
==================================
Runs 8 demonstration steps that exercise every module in the lab and prints
formatted tables.  No Streamlit — pure Python CLI output.

Usage
-----
    cd qc-finops-lab
    python src/demo.py

Steps
-----
  1  Generate / load QPU job history (500 rows)
  2  Data quality stats
  3  Cost analysis by provider
  4  Algorithm cost analysis
  5  Resource estimation (Shor 2048-bit, Grover 1M items, VQE 10e)
  6  Scheduler demo (5 jobs submitted, 5 scheduled)
  7  Monthly budget forecast (3 months, 95 % CI)
  8  Summary PASS/FAIL board
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
import time
from collections import defaultdict
from statistics import mean, median, stdev
from typing import Any, Dict, List

# ── path setup ───────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)

# ── local imports ─────────────────────────────────────────────────────────────
from generate_data import generate, JOBS_CSV, MONTHLY_JSON
from resource_estimator import ResourceEstimator
from qpu_cost_model import QPUCostModeler, QPUJob
from qpu_scheduler import QPUScheduler, Priority

# ── helpers ───────────────────────────────────────────────────────────────────
PASS = "\u2713 PASS"
FAIL = "\u2717 FAIL"
SEP  = "=" * 72


def _fmt_usd(v: float) -> str:
    if math.isinf(v):
        return "infeasible"
    return f"${v:,.4f}"


def _banner(step: int, title: str) -> None:
    print(f"\n{SEP}")
    print(f"  STEP {step}: {title}")
    print(SEP)


def _table(headers: List[str], rows: List[List[Any]], col_width: int = 18) -> None:
    """Print a simple fixed-width table."""
    widths = [max(col_width, len(h) + 2) for h in headers]
    header_line = "  ".join(str(h).ljust(w) for h, w in zip(headers, widths))
    print(header_line)
    print("-" * len(header_line))
    for row in rows:
        print("  ".join(str(c).ljust(w) for c, w in zip(row, widths)))


# ── step implementations ──────────────────────────────────────────────────────

def step1_load_jobs() -> List[Dict[str, Any]]:
    _banner(1, "Generate / Load QPU Job History")
    t0 = time.perf_counter()

    if not os.path.exists(JOBS_CSV):
        print("  [INFO] data/qpu_jobs.csv not found — generating …")
        generate(500)
    else:
        print(f"  [INFO] Loading existing dataset from:\n         {JOBS_CSV}")

    jobs: List[Dict[str, Any]] = []
    with open(JOBS_CSV, newline="") as fh:
        for row in csv.DictReader(fh):
            jobs.append({
                "job_id":        row["job_id"],
                "algorithm":     row["algorithm"],
                "n_qubits":      int(row["n_qubits"]),
                "circuit_depth": int(row["circuit_depth"]),
                "n_shots":       int(row["n_shots"]),
                "provider":      row["provider"],
                "cost_usd":      float(row["cost_usd"]),
                "queue_time_s":  int(row["queue_time_s"]),
                "run_time_s":    int(row["run_time_s"]),
                "success":       int(row["success"]),
                "month":         row["month"],
                "priority":      row["priority"],
            })

    elapsed = time.perf_counter() - t0
    print(f"  Loaded {len(jobs):,} jobs in {elapsed*1000:.1f} ms")
    return jobs


def step2_data_quality(jobs: List[Dict[str, Any]]) -> None:
    _banner(2, "Data Quality Stats")
    t0 = time.perf_counter()

    n = len(jobs)
    costs = [j["cost_usd"] for j in jobs]
    providers = set(j["provider"] for j in jobs)
    months    = set(j["month"]    for j in jobs)
    algos     = set(j["algorithm"] for j in jobs)

    # Null / anomaly check
    null_counts = defaultdict(int)
    for j in jobs:
        for k, v in j.items():
            if v is None or v == "":
                null_counts[k] += 1

    rows_data = [
        ["rows",          n],
        ["columns",       12],
        ["null_fields",   sum(null_counts.values())],
        ["providers",     len(providers)],
        ["algorithms",    len(algos)],
        ["months_covered",len(months)],
        ["min_cost_usd",  _fmt_usd(min(costs))],
        ["max_cost_usd",  _fmt_usd(max(costs))],
        ["mean_cost_usd", _fmt_usd(mean(costs))],
        ["success_rate",  f"{sum(j['success'] for j in jobs)/n*100:.1f}%"],
    ]
    _table(["metric", "value"], rows_data, col_width=22)
    elapsed = time.perf_counter() - t0
    print(f"\n  Completed in {elapsed*1000:.1f} ms  {PASS}")


def step3_cost_by_provider(jobs: List[Dict[str, Any]]) -> None:
    _banner(3, "Cost Analysis by Provider")
    t0 = time.perf_counter()

    by_prov: Dict[str, List[float]] = defaultdict(list)
    for j in jobs:
        by_prov[j["provider"]].append(j["cost_usd"])

    rows_data = []
    for prov in sorted(by_prov):
        costs = sorted(by_prov[prov])
        n     = len(costs)
        total = sum(costs)
        avg   = total / n
        p50   = costs[n // 2]
        p99   = costs[int(n * 0.99)]
        rows_data.append([prov, n, _fmt_usd(total), _fmt_usd(avg),
                          _fmt_usd(p50), _fmt_usd(p99)])

    _table(["provider", "jobs", "total_cost", "avg_cost", "p50_cost", "p99_cost"],
           rows_data, col_width=14)
    elapsed = time.perf_counter() - t0
    print(f"\n  Completed in {elapsed*1000:.1f} ms  {PASS}")


def step4_cost_by_algorithm(jobs: List[Dict[str, Any]]) -> None:
    _banner(4, "Algorithm Cost Analysis")
    t0 = time.perf_counter()

    by_algo: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for j in jobs:
        by_algo[j["algorithm"]].append(j)

    rows_data = []
    for algo in sorted(by_algo):
        grp = by_algo[algo]
        n   = len(grp)
        avg_q = mean(j["n_qubits"]  for j in grp)
        avg_c = mean(j["cost_usd"]  for j in grp)
        avg_t = mean(j["run_time_s"] for j in grp)
        rows_data.append([algo, n, f"{avg_q:.1f}", _fmt_usd(avg_c), f"{avg_t:.1f}s"])

    _table(["algorithm", "jobs", "avg_qubits", "avg_cost", "avg_time_s"],
           rows_data, col_width=14)
    elapsed = time.perf_counter() - t0
    print(f"\n  Completed in {elapsed*1000:.1f} ms  {PASS}")


def step5_resource_estimation() -> None:
    _banner(5, "Resource Estimator — Shor / Grover / VQE")
    t0 = time.perf_counter()
    est = ResourceEstimator()

    # Shor 2048-bit RSA
    shor = est.estimate_shor_rsa(2048)
    print("\n  [Shor — RSA-2048]")
    rows_shor = [
        ["logical_qubits",  f"{shor['logical_qubits']:,}"],
        ["physical_qubits", f"{shor['physical_qubits']:,}" if shor['physical_qubits'] else "N/A"],
        ["code_distance_d", shor["code_distance_d"]],
        ["T_gates",         f"{shor['T_gates']:,}"],
        ["total_gates",     f"{shor['total_gates']:,}"],
        ["runtime_days",    shor["runtime_days"]],
        ["feasibility",     shor["feasibility"]],
    ]
    _table(["parameter", "value"], rows_shor, col_width=20)

    # Grover 1M items
    grover = est.estimate_grover_search(1_000_000)
    print("\n  [Grover — 1,000,000 items]")
    rows_grover = [
        ["logical_qubits",      f"{grover['qubits_logical']}"],
        ["oracle_calls",        f"{grover['oracle_calls']:,}"],
        ["speedup_vs_classical",f"{grover['speedup_over_classical']:,.0f}×"],
        ["total_gates",         f"{grover['total_gates']:,}"],
        ["runtime_ms",          grover["runtime_ms"]],
        ["feasibility",         grover["feasibility"]],
    ]
    _table(["parameter", "value"], rows_grover, col_width=26)

    # VQE 10 electrons, 20 basis functions
    vqe = est.estimate_vqe(n_electrons=10, basis_size=20)
    print("\n  [VQE — 10 electrons, 20 basis functions (UCCSD)]")
    rows_vqe = [
        ["qubits_logical",   f"{vqe['qubits_logical']}"],
        ["ansatz_layers",    f"{vqe['ansatz_layers']:,}"],
        ["total_gates",      f"{vqe['total_gates']:,}"],
        ["total_shots",      f"{vqe['total_shots']:,}"],
        ["feasibility",      vqe["feasibility"]],
    ]
    _table(["parameter", "value"], rows_vqe, col_width=20)

    elapsed = time.perf_counter() - t0
    print(f"\n  Completed in {elapsed*1000:.1f} ms  {PASS}")


def step6_scheduler_demo() -> None:
    _banner(6, "Scheduler Demo — 5 Jobs Submitted + Scheduled")
    t0 = time.perf_counter()

    sched = QPUScheduler()

    test_jobs = [
        (QPUJob(circuit_depth=20, n_qubits=10, n_shots=1024,  gate_count=80,  error_rate=0.001, algorithm_tag="VQE"),    Priority.HIGH),
        (QPUJob(circuit_depth=50, n_qubits=25, n_shots=4096,  gate_count=400, error_rate=0.001, algorithm_tag="QAOA"),   Priority.NORMAL),
        (QPUJob(circuit_depth=10, n_qubits=8,  n_shots=512,   gate_count=40,  error_rate=0.001, algorithm_tag="QKD"),    Priority.CRITICAL),
        (QPUJob(circuit_depth=30, n_qubits=15, n_shots=2048,  gate_count=200, error_rate=0.001, algorithm_tag="Grover"), Priority.LOW),
        (QPUJob(circuit_depth=80, n_qubits=40, n_shots=8192,  gate_count=800, error_rate=0.001, algorithm_tag="Shor"),   Priority.HIGH),
    ]

    job_ids = []
    for job, pri in test_jobs:
        jid = sched.submit(job, priority=pri)
        job_ids.append(jid)

    print(f"  Submitted {len(test_jobs)} jobs to scheduler\n")

    scheduled = []
    for _ in range(5):
        nxt = sched.schedule_next()
        if nxt:
            scheduled.append(nxt)

    rows_data = []
    for entry in scheduled:
        rows_data.append([
            str(entry.id)[:14],
            entry.job.algorithm_tag,
            entry.priority.name,
            entry.job.n_qubits,
            entry.job.n_shots,
        ])

    _table(["job_id", "algorithm", "priority", "n_qubits", "n_shots"],
           rows_data, col_width=16)

    stats = sched.get_throughput_stats()
    print(f"\n  Queue stats: submitted={stats.get('total_submitted',0)} | "
          f"running={stats.get('currently_running',0)} | "
          f"avg_wait_s={stats.get('avg_wait_s', 0):.1f}")

    elapsed = time.perf_counter() - t0
    print(f"\n  Completed in {elapsed*1000:.1f} ms  {PASS}")


def step7_budget_forecast(jobs: List[Dict[str, Any]]) -> None:
    _banner(7, "Monthly Budget Forecast — 3 Months (95% CI)")
    t0 = time.perf_counter()

    modeler = QPUCostModeler()

    # Use observed IBM/AWS/Azure costs to build a simple cost-per-day model
    by_month: Dict[str, List[float]] = defaultdict(list)
    for j in jobs:
        by_month[j["month"]].append(j["cost_usd"])

    monthly_totals = sorted([sum(v) for v in by_month.values()])
    if len(monthly_totals) < 2:
        print("  Not enough monthly data for forecast.")
        return

    mu    = mean(monthly_totals)
    sigma = stdev(monthly_totals) if len(monthly_totals) > 1 else mu * 0.15
    z95   = 1.96   # 95% CI z-score

    print(f"  Historical monthly spend:  mean=${mu:,.2f}  stddev=${sigma:,.2f}")
    print()
    rows_data = []
    for i in range(1, 4):
        label     = f"2026-{10+i:02d}" if 10+i <= 12 else f"2027-{10+i-12:02d}"
        forecast  = mu
        ci_lo     = max(0, forecast - z95 * sigma)
        ci_hi     = forecast + z95 * sigma
        budget    = 2000.0
        status    = "ON BUDGET" if ci_hi < budget else "RISK"
        rows_data.append([label, _fmt_usd(forecast),
                          f"[{_fmt_usd(ci_lo)}, {_fmt_usd(ci_hi)}]",
                          _fmt_usd(budget), status])

    _table(["month", "forecast", "95%_CI", "budget", "status"],
           rows_data, col_width=24)

    # Also show provider recommendation
    rep_job = QPUJob(circuit_depth=20, n_qubits=20, n_shots=4096,
                     gate_count=200, error_rate=0.001, algorithm_tag="VQE")
    plan = modeler.monthly_budget_plan(jobs_per_day=5, budget_usd=2000,
                                       representative_job=rep_job)
    print(f"\n  Cheapest provider for representative job: {plan['cheapest_provider']}")
    print(f"  Projected monthly spend (5 jobs/day):    {_fmt_usd(plan['projected_spend_usd'])}")
    print(f"  Budget surplus:                          {_fmt_usd(plan['budget_surplus_usd'])}")

    elapsed = time.perf_counter() - t0
    print(f"\n  Completed in {elapsed*1000:.1f} ms  {PASS}")


def step8_summary(results: Dict[str, bool]) -> None:
    _banner(8, "Demo Summary")
    all_pass = all(results.values())
    for step_name, passed in results.items():
        icon = PASS if passed else FAIL
        print(f"  {icon}  {step_name}")
    print()
    if all_pass:
        print("  ALL STEPS PASSED — QPU FinOps Lab demo complete.")
    else:
        print("  SOME STEPS FAILED — review output above.")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{'#'*72}")
    print("  QPU FinOps Lab — Production Demo")
    print(f"{'#'*72}")

    results: Dict[str, bool] = {}
    jobs: List[Dict[str, Any]] = []

    t_total = time.perf_counter()

    try:
        jobs = step1_load_jobs()
        results["Step 1 — Load job history"] = len(jobs) > 0
    except Exception as exc:
        print(f"  {FAIL}: {exc}")
        results["Step 1 — Load job history"] = False

    try:
        step2_data_quality(jobs)
        results["Step 2 — Data quality stats"] = True
    except Exception as exc:
        print(f"  {FAIL}: {exc}")
        results["Step 2 — Data quality stats"] = False

    try:
        step3_cost_by_provider(jobs)
        results["Step 3 — Cost by provider"] = True
    except Exception as exc:
        print(f"  {FAIL}: {exc}")
        results["Step 3 — Cost by provider"] = False

    try:
        step4_cost_by_algorithm(jobs)
        results["Step 4 — Algorithm cost analysis"] = True
    except Exception as exc:
        print(f"  {FAIL}: {exc}")
        results["Step 4 — Algorithm cost analysis"] = False

    try:
        step5_resource_estimation()
        results["Step 5 — Resource estimation"] = True
    except Exception as exc:
        print(f"  {FAIL}: {exc}")
        results["Step 5 — Resource estimation"] = False

    try:
        step6_scheduler_demo()
        results["Step 6 — Scheduler demo"] = True
    except Exception as exc:
        print(f"  {FAIL}: {exc}")
        results["Step 6 — Scheduler demo"] = False

    try:
        step7_budget_forecast(jobs)
        results["Step 7 — Budget forecast"] = True
    except Exception as exc:
        print(f"  {FAIL}: {exc}")
        results["Step 7 — Budget forecast"] = False

    step8_summary(results)

    elapsed_total = time.perf_counter() - t_total
    print(f"\n  Total wall time: {elapsed_total:.2f} s\n")


if __name__ == "__main__":
    main()
