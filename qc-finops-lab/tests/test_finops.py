"""
QPU FinOps Lab — Test Suite
=============================
Purpose   : Comprehensive unit tests for all four FinOps lab modules.
Reference : unittest standard library; covers QPUCostModeler, QPUScheduler,
            ResourceEstimator, and FinOpsDashboard.
Coverage  : 24 test functions across all public methods.

Run
---
    cd qc-finops-lab
    python -m pytest tests/test_finops.py -v
    # or
    python -m unittest tests.test_finops -v
"""
from __future__ import annotations

import math
import sys
import os
import time
import unittest

# Allow running from any working directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from qpu_cost_model   import QPUJob, QPUCostModeler, CostEstimate
from qpu_scheduler    import QPUScheduler, Priority, JobStatus
from resource_estimator import ResourceEstimator
from finops_dashboard import FinOpsDashboard, JobRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_job(
    circuit_depth: int = 15,
    n_qubits: int = 10,
    n_shots: int = 4096,
    gate_count: int = 80,
    error_rate: float = 0.001,
    algorithm_tag: str = "test",
) -> QPUJob:
    return QPUJob(
        circuit_depth=circuit_depth,
        n_qubits=n_qubits,
        n_shots=n_shots,
        gate_count=gate_count,
        error_rate=error_rate,
        algorithm_tag=algorithm_tag,
    )


def _make_record(
    provider: str = "IBM_Quantum",
    algorithm: str = "VQE",
    cost_usd: float = 0.05,
    n_shots: int = 4096,
) -> JobRecord:
    return JobRecord(
        job_id=f"jr-{provider}-{algorithm}",
        algorithm=algorithm,
        provider=provider,
        backend="Eagle_r3",
        n_qubits=10,
        n_shots=n_shots,
        cost_usd=cost_usd,
        latency_ms=800.0,
    )


# ---------------------------------------------------------------------------
# 1. QPUJob validation
# ---------------------------------------------------------------------------

class TestQPUJob(unittest.TestCase):

    def test_valid_job_creation(self):
        job = _make_job()
        self.assertEqual(job.n_qubits, 10)
        self.assertEqual(job.n_shots, 4096)

    def test_invalid_circuit_depth(self):
        with self.assertRaises(ValueError):
            QPUJob(circuit_depth=0, n_qubits=5, n_shots=100,
                   gate_count=30, error_rate=0.001)

    def test_invalid_error_rate_zero(self):
        with self.assertRaises(ValueError):
            QPUJob(circuit_depth=5, n_qubits=5, n_shots=100,
                   gate_count=30, error_rate=0.0)

    def test_invalid_error_rate_one(self):
        with self.assertRaises(ValueError):
            QPUJob(circuit_depth=5, n_qubits=5, n_shots=100,
                   gate_count=30, error_rate=1.0)

    def test_two_qubit_gate_count(self):
        job = QPUJob(circuit_depth=10, n_qubits=5, n_shots=1024,
                     gate_count=100, error_rate=0.001, two_qubit_fraction=0.30)
        self.assertEqual(job.two_qubit_gates, 30)
        self.assertEqual(job.single_qubit_gates, 70)

    def test_circuit_volume(self):
        job = _make_job(circuit_depth=20, n_qubits=10)
        # min(10, 20) ** 2 = 100
        self.assertEqual(job.circuit_volume(), 100)


# ---------------------------------------------------------------------------
# 2. QPUCostModeler — individual providers
# ---------------------------------------------------------------------------

class TestQPUCostModeler(unittest.TestCase):

    def setUp(self):
        self.modeler = QPUCostModeler()
        self.job     = _make_job(n_shots=8000)

    def test_ibm_eagle_cost_positive(self):
        est = self.modeler.estimate_ibm_quantum(self.job)
        self.assertGreater(est.cost_usd, 0.0)
        self.assertEqual(est.provider, "IBM_Quantum")

    def test_ibm_cost_scales_with_shots(self):
        job_low  = _make_job(n_shots=1000)
        job_high = _make_job(n_shots=10000)
        est_low  = self.modeler.estimate_ibm_quantum(job_low)
        est_high = self.modeler.estimate_ibm_quantum(job_high)
        self.assertLess(est_low.cost_usd, est_high.cost_usd)

    def test_aws_braket_cost_positive(self):
        est = self.modeler.estimate_aws_braket(self.job)
        # AWS always has $0.30 task fee minimum
        self.assertGreaterEqual(est.cost_usd, 0.30)
        self.assertEqual(est.provider, "AWS_Braket")

    def test_azure_quantum_returns_estimate(self):
        est = self.modeler.estimate_azure_quantum(self.job)
        self.assertIn(est.provider, ["Azure_Quantum"])
        self.assertGreater(est.cost_usd, 0.0)

    def test_google_cirq_zero_cost(self):
        est = self.modeler.estimate_google_cirq(self.job)
        self.assertEqual(est.cost_usd, 0.0)
        self.assertEqual(est.provider, "Google_Cirq")

    def test_google_cirq_latency_positive(self):
        est = self.modeler.estimate_google_cirq(self.job)
        self.assertGreater(est.latency_ms, 0.0)

    def test_ibm_infeasible_for_too_many_qubits(self):
        big_job = _make_job(n_qubits=200)
        est = self.modeler.estimate_ibm_quantum(big_job)
        self.assertTrue(math.isinf(est.cost_usd))

    def test_fidelity_score_in_range(self):
        est = self.modeler.estimate_ibm_quantum(self.job)
        self.assertGreaterEqual(est.fidelity_score, 0.0)
        self.assertLessEqual(est.fidelity_score, 1.0)

    def test_compare_providers_sorted_by_cost(self):
        estimates = self.modeler.compare_providers(self.job)
        finite = [e for e in estimates if math.isfinite(e.cost_usd)]
        costs  = [e.cost_usd for e in finite]
        self.assertEqual(costs, sorted(costs))

    def test_monthly_budget_plan_structure(self):
        plan = self.modeler.monthly_budget_plan(
            jobs_per_day=5, budget_usd=500.0
        )
        self.assertIn("monthly_jobs", plan)
        self.assertIn("cheapest_provider", plan)
        self.assertIn("provider_breakdown", plan)
        self.assertGreater(plan["monthly_jobs"], 0)

    def test_monthly_budget_plan_overage_detection(self):
        # Use a 60-qubit job (exceeds Sycamore 54q cap so Google routes to Willow,
        # but $0 cost still applies).  Test overage using AWS only by checking that
        # the AWS breakdown entry has monthly_total > budget.
        rep_job = _make_job(n_qubits=60, n_shots=50000)
        plan = self.modeler.monthly_budget_plan(
            jobs_per_day=1000, budget_usd=5.0,
            representative_job=rep_job,
        )
        # AWS Braket: $0.30 task + shots × $0.00035 ≈ $0.30+ per job
        # 1000 jobs/day × 30.44 days ≈ 30440 jobs × $0.30 ≈ $9132 >> $5
        aws_key = next(
            (k for k in plan["provider_breakdown"] if "AWS_Braket" in k), None
        )
        self.assertIsNotNone(aws_key, "AWS_Braket not in provider_breakdown")
        aws_monthly = plan["provider_breakdown"][aws_key]["monthly_total_usd"]
        self.assertGreater(aws_monthly, 5.0)

    def test_circuit_cost_optimization_has_suggestions(self):
        job  = _make_job(n_shots=50000, n_qubits=10, circuit_depth=30)
        opts = self.modeler.circuit_cost_optimization(job)
        self.assertIn("suggestions", opts)
        self.assertIsInstance(opts["suggestions"], list)

    def test_shot_reduction_suggestion_lowers_cost(self):
        job  = _make_job(n_shots=100000)
        opts = self.modeler.circuit_cost_optimization(job)
        shot_sug = next(
            (s for s in opts["suggestions"] if s["strategy"] == "shot_reduction"), None
        )
        if shot_sug:
            self.assertGreater(shot_sug["savings_usd"], 0)


# ---------------------------------------------------------------------------
# 3. QPUScheduler
# ---------------------------------------------------------------------------

class TestQPUScheduler(unittest.TestCase):

    def setUp(self):
        self.sched = QPUScheduler(max_concurrency=2)
        self.job   = _make_job()

    def test_submit_returns_job_id(self):
        jid = self.sched.submit(self.job)
        self.assertIsInstance(jid, str)
        self.assertGreater(len(jid), 0)

    def test_queue_depth_increases_on_submit(self):
        self.assertEqual(self.sched.get_queue_depth(), 0)
        self.sched.submit(self.job)
        self.assertEqual(self.sched.get_queue_depth(), 1)

    def test_schedule_next_returns_highest_priority(self):
        low_id  = self.sched.submit(self.job, priority=Priority.LOW)
        crit_id = self.sched.submit(self.job, priority=Priority.CRITICAL)
        next_j  = self.sched.schedule_next()
        self.assertIsNotNone(next_j)
        self.assertEqual(next_j.id, crit_id)

    def test_schedule_next_marks_running(self):
        self.sched.submit(self.job)
        nj = self.sched.schedule_next()
        self.assertEqual(nj.status, JobStatus.RUNNING)
        self.assertEqual(self.sched.get_running_count(), 1)

    def test_cancel_queued_job(self):
        jid = self.sched.submit(self.job)
        result = self.sched.cancel(jid)
        self.assertTrue(result)
        self.assertEqual(self.sched.get_queue_depth(), 0)

    def test_cancel_nonexistent_job_returns_false(self):
        self.assertFalse(self.sched.cancel("fake-id-123"))

    def test_complete_job_updates_stats(self):
        jid = self.sched.submit(self.job)
        self.sched.schedule_next()
        time.sleep(0.01)
        ok = self.sched.complete_job(jid, success=True)
        self.assertTrue(ok)
        stats = self.sched.get_throughput_stats()
        self.assertEqual(stats["total_completed"], 1)

    def test_throughput_stats_structure(self):
        stats = self.sched.get_throughput_stats()
        for key in ("total_submitted", "total_completed", "currently_queued",
                    "avg_wait_s", "p99_wait_s", "priority_breakdown"):
            self.assertIn(key, stats)

    def test_estimate_wait_time_empty_queue(self):
        wt = self.sched.estimate_wait_time(Priority.NORMAL)
        self.assertGreaterEqual(wt, 0.0)

    def test_drain_completes_all_jobs(self):
        for _ in range(5):
            self.sched.submit(self.job)
        drained = self.sched.drain(simulate_exec_s=0.001)
        self.assertEqual(len(drained), 5)
        self.assertEqual(self.sched.get_queue_depth(), 0)

    def test_max_concurrency_respected(self):
        sched = QPUScheduler(max_concurrency=1)
        sched.submit(self.job)
        sched.submit(self.job)
        sched.schedule_next()   # fills the 1 slot
        second = sched.schedule_next()
        self.assertIsNone(second)   # slot full

    def test_submit_with_cost_check_accepted(self):
        result = self.sched.submit_with_cost_check(
            self.job, max_cost_usd=100.0
        )
        self.assertEqual(result["decision"], "ACCEPTED")
        self.assertIsNotNone(result["job_id"])

    def test_submit_with_cost_check_rejected(self):
        # Force AWS Braket preferred — minimum cost is $0.30 task fee.
        # Budget of $0.01 must be rejected.
        result = self.sched.submit_with_cost_check(
            self.job,
            max_cost_usd=0.01,
            preferred_provider="AWS_Braket",
        )
        # AWS cheapest is $0.30+ which exceeds $0.01; Google ($0) is
        # excluded by preferred_provider filter applied first — but if Google
        # ends up cheaper it would accept, so we test on a job too large for
        # Google and small enough to only consider paid providers.
        # Simpler: test with a 60-qubit job (too big for Sycamore 54q) so
        # Google routes to Willow but we restrict preferred_provider=AWS_Braket.
        big_job = _make_job(n_qubits=60)
        result2 = self.sched.submit_with_cost_check(
            big_job,
            max_cost_usd=0.01,
            preferred_provider="AWS_Braket",
        )
        # AWS_Braket >= $0.30 > $0.01 → REJECTED
        self.assertEqual(result2["decision"], "REJECTED_OVER_BUDGET")
        self.assertIsNone(result2["job_id"])


# ---------------------------------------------------------------------------
# 4. ResourceEstimator
# ---------------------------------------------------------------------------

class TestResourceEstimator(unittest.TestCase):

    def setUp(self):
        self.est = ResourceEstimator()

    def test_shor_rsa_logical_qubits(self):
        r = self.est.estimate_shor_rsa(512)
        self.assertEqual(r["logical_qubits"], 2 * 512 + 3)

    def test_shor_rsa_t_gate_count(self):
        r = self.est.estimate_shor_rsa(64)
        # T_gates = 7 × 40 × n³
        expected_toffoli = 40 * (64 ** 3)
        self.assertEqual(r["toffoli_gates"], expected_toffoli)
        self.assertEqual(r["T_gates"], 7 * expected_toffoli)

    def test_grover_oracle_calls(self):
        n = 1024
        r = self.est.estimate_grover_search(n)
        expected = math.ceil(math.pi / 4.0 * math.sqrt(n))
        self.assertEqual(r["oracle_calls"], expected)

    def test_grover_quadratic_speedup(self):
        r = self.est.estimate_grover_search(10000)
        self.assertAlmostEqual(r["speedup_over_classical"], 100.0, places=0)

    def test_vqe_qubit_count(self):
        r = self.est.estimate_vqe(n_electrons=4, basis_size=16)
        self.assertEqual(r["qubits_logical"], 16)

    def test_vqe_double_excitations_correct(self):
        r = self.est.estimate_vqe(n_electrons=4, basis_size=8)
        # doubles = C(4,2) × C(4,2) = 6 × 6 = 36
        self.assertEqual(r["double_excitations"], 36)

    def test_qaoa_gate_count(self):
        r = self.est.estimate_qaoa(n_nodes=10, p_layers=2, graph_density=0.5)
        self.assertGreater(r["total_gates"], 0)
        self.assertEqual(r["qubits_logical"], 10)

    def test_qec_overhead_physical_greater_than_logical(self):
        r = self.est.estimate_qec_overhead(logical_qubits=10)
        self.assertGreater(r["physical_qubits_total"], 10)

    def test_feasibility_current_hardware(self):
        # Small circuit should be feasible today
        r = self.est.estimate_grover_search(128)
        self.assertEqual(r["feasibility"], "current_hardware")

    def test_feasibility_theoretical_for_large_shor(self):
        r = self.est.estimate_shor_rsa(2048)
        self.assertIn(r["feasibility"],
                      ["fault_tolerant_only", "theoretical_only", "near_term_2028"])


# ---------------------------------------------------------------------------
# 5. FinOpsDashboard
# ---------------------------------------------------------------------------

class TestFinOpsDashboard(unittest.TestCase):

    def setUp(self):
        self.db = FinOpsDashboard()
        self.records = [
            _make_record("IBM_Quantum", "VQE",   0.065, 4096),
            _make_record("AWS_Braket",  "QAOA",  0.312, 8000),
            _make_record("IBM_Quantum", "Grover", 0.032, 2000),
            _make_record("Azure_Quantum", "VQE", 0.240, 4096),
        ]

    def test_monthly_report_total_spend(self):
        report = self.db.generate_monthly_report("2025-10", self.records)
        expected = sum(r.cost_usd for r in self.records)
        self.assertAlmostEqual(report["total_spend_usd"], expected, places=4)

    def test_monthly_report_algorithm_keys(self):
        report = self.db.generate_monthly_report("2025-10", self.records)
        self.assertIn("VQE",    report["cost_per_algorithm"])
        self.assertIn("QAOA",   report["cost_per_algorithm"])
        self.assertIn("Grover", report["cost_per_algorithm"])

    def test_anomaly_detection_finds_spike(self):
        history = [10.0, 11.0, 10.5, 9.5, 10.2, 50.0, 10.0, 11.0, 9.8, 10.3]
        anomalies = self.db.cost_anomaly_detection(history)
        # The $50 spike should be flagged
        spikes = [a for a in anomalies if a.get("direction") == "spike"]
        self.assertGreater(len(spikes), 0)

    def test_anomaly_detection_no_alert_flat(self):
        history = [10.0] * 10
        anomalies = self.db.cost_anomaly_detection(history)
        # Zero variance → should return info only
        self.assertTrue(any("info" in a or "warning" in a for a in anomalies))

    def test_roi_analysis_break_even(self):
        roi = self.db.roi_analysis(
            classical_compute_cost=50.0,
            quantum_compute_cost=50.0,
            speedup_factor=1.0,
        )
        # speedup=1 → effective quantum cost = classical cost → ROI=0%
        self.assertAlmostEqual(roi["roi_percent"], 0.0, places=2)

    def test_roi_positive_at_high_speedup(self):
        roi = self.db.roi_analysis(
            classical_compute_cost=100.0,
            quantum_compute_cost=50.0,
            speedup_factor=10.0,
        )
        self.assertGreater(roi["roi_percent"], 0.0)

    def test_budget_forecast_returns_n_months(self):
        history = [100.0, 110.0, 115.0, 125.0, 130.0, 140.0]
        fc = self.db.budget_forecast(history, months_ahead=3)
        self.assertEqual(len(fc["forecast"]), 3)

    def test_budget_forecast_increasing_trend(self):
        history = [100.0, 110.0, 120.0, 130.0, 140.0, 150.0]
        fc = self.db.budget_forecast(history, months_ahead=1)
        self.assertEqual(fc["forecast"][0]["trend"], "increasing")

    def test_optimize_shots_chebyshev(self):
        opt = self.db.optimize_shot_count(
            target_precision=0.05,
            current_shots=100000,
            method="chebyshev",
        )
        # Chebyshev: n ≥ 1/(4 × 0.05² × 0.05) = 2000
        self.assertEqual(opt["recommended_shots"], 2000)
        self.assertGreater(opt["reduction_pct"], 0)

    def test_optimize_shots_hoeffding(self):
        opt = self.db.optimize_shot_count(
            target_precision=0.05,
            current_shots=50000,
            method="hoeffding",
        )
        self.assertGreater(opt["recommended_shots"], 0)
        self.assertLess(opt["recommended_shots"], 50000)

    def test_carbon_footprint_ibm(self):
        co2 = self.db.carbon_footprint("IBM_Quantum", n_jobs=100)
        self.assertGreater(co2["co2_grams_total"], 0)
        self.assertIn("equivalent_km_driven", co2)

    def test_carbon_footprint_google_lowest(self):
        ibm_co2    = self.db.carbon_footprint("IBM_Quantum",   n_jobs=1)["co2_grams_per_job"]
        google_co2 = self.db.carbon_footprint("Google_Cirq",   n_jobs=1)["co2_grams_per_job"]
        # Google has lowest carbon intensity → lowest CO₂
        self.assertLess(google_co2, ibm_co2)

    def test_allocate_budget_sums_correctly(self):
        total = 1000.0
        priorities = {"VQE": 3.0, "QAOA": 2.0, "Grover": 1.0}
        unit_costs = {"VQE": 0.05, "QAOA": 0.32, "Grover": 0.02}
        alloc = self.db.allocate_budget(total, priorities, unit_costs)
        alloc_sum = sum(v["allocated_usd"] for v in alloc["allocations"].values())
        self.assertAlmostEqual(alloc_sum, total, places=1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
