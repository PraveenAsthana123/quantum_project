"""
job_manager.py — Quantum job lifecycle management for Q07
Simulates QUEUED → RUNNING → COMPLETED/FAILED lifecycle
with exponential backoff retry logic.
"""

import json
import os
import time
import random
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"


@dataclass
class QuantumJob:
    job_id: str
    circuit_name: str
    n_qubits: int
    n_shots: int
    backend: str
    status: JobStatus = JobStatus.QUEUED
    submission_time: float = field(default_factory=time.time)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    queue_time_s: float = 0.0
    execution_time_s: float = 0.0
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    result_counts: Optional[Dict] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


class ExponentialBackoff:
    """Compute exponential backoff delay with jitter."""
    def __init__(self, base_delay: float = 1.0, max_delay: float = 30.0, factor: float = 2.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.factor = factor

    def delay(self, attempt: int) -> float:
        """Return delay in seconds for given retry attempt (0-indexed)."""
        d = min(self.base_delay * (self.factor ** attempt), self.max_delay)
        jitter = random.uniform(0, d * 0.1)
        return d + jitter


class QuantumJobManager:
    """Manages quantum job lifecycle with retry and tracking."""

    def __init__(self, failure_rate: float = 0.25, rng_seed: int = 42):
        self.jobs: List[QuantumJob] = []
        self.failure_rate = failure_rate
        self.backoff = ExponentialBackoff(base_delay=0.05, max_delay=0.5, factor=2.0)
        random.seed(rng_seed)

    def submit(self, circuit_name: str, n_qubits: int, n_shots: int, backend: str) -> QuantumJob:
        """Submit a new quantum job."""
        job = QuantumJob(
            job_id=str(uuid.uuid4())[:8],
            circuit_name=circuit_name,
            n_qubits=n_qubits,
            n_shots=n_shots,
            backend=backend,
        )
        self.jobs.append(job)
        return job

    def _simulate_queue_wait(self, job: QuantumJob) -> float:
        """Simulate queue wait time (0.1 - 2.0 seconds scaled)."""
        queue_s = random.uniform(0.05, 0.2)
        time.sleep(queue_s)
        return queue_s

    def _simulate_execution(self, job: QuantumJob) -> Optional[Dict]:
        """
        Simulate job execution. Returns result counts or raises on failure.
        Fails with probability = self.failure_rate.
        """
        exec_s = random.uniform(0.05, 0.15)
        time.sleep(exec_s)

        if random.random() < self.failure_rate:
            raise RuntimeError(f"Hardware error on backend {job.backend}: calibration drift detected")

        # Generate plausible GHZ-like output counts
        n = job.n_qubits
        all_zeros = "0" * n
        all_ones = "1" * n
        shots = job.n_shots
        noise = random.uniform(0.02, 0.05)
        counts = {all_zeros: int(shots * (0.5 - noise)), all_ones: int(shots * (0.5 - noise))}
        # Spread remaining shots as noise
        remaining = shots - sum(counts.values())
        for _ in range(remaining):
            rand_state = format(random.randint(0, 2**n - 1), f"0{n}b")
            counts[rand_state] = counts.get(rand_state, 0) + 1

        return {k: v for k, v in counts.items() if v > 0}

    def run_job(self, job: QuantumJob) -> QuantumJob:
        """Run a single job with retry logic."""
        t_submit = job.submission_time

        # Queue phase
        job.status = JobStatus.QUEUED
        queue_s = self._simulate_queue_wait(job)
        job.queue_time_s = queue_s
        job.start_time = time.time()

        attempt = 0
        while attempt <= job.max_retries:
            job.status = JobStatus.RUNNING if attempt == 0 else JobStatus.RETRYING
            t_run_start = time.time()

            try:
                counts = self._simulate_execution(job)
                job.end_time = time.time()
                job.execution_time_s = job.end_time - t_run_start
                job.status = JobStatus.COMPLETED
                job.result_counts = counts
                if attempt > 0:
                    print(f"  Job {job.job_id} succeeded on retry {attempt}")
                return job

            except RuntimeError as e:
                job.error_message = str(e)
                attempt += 1
                job.retry_count = attempt - 1

                if attempt > job.max_retries:
                    job.status = JobStatus.FAILED
                    job.end_time = time.time()
                    print(f"  Job {job.job_id} FAILED after {job.max_retries} retries: {e}")
                    return job

                delay = self.backoff.delay(attempt - 1)
                print(f"  Job {job.job_id} failed (attempt {attempt}/{job.max_retries}), "
                      f"retrying in {delay:.2f}s...")
                time.sleep(delay)

        job.status = JobStatus.FAILED
        return job

    def run_batch(self, jobs: List[QuantumJob]) -> List[QuantumJob]:
        """Run a batch of jobs sequentially."""
        results = []
        for job in jobs:
            result = self.run_job(job)
            results.append(result)
        return results

    def summary(self) -> Dict:
        """Compute summary statistics over all tracked jobs."""
        total = len(self.jobs)
        completed = [j for j in self.jobs if j.status == JobStatus.COMPLETED]
        failed = [j for j in self.jobs if j.status == JobStatus.FAILED]
        retried = [j for j in self.jobs if j.retry_count > 0]

        avg_queue = (
            sum(j.queue_time_s for j in completed) / len(completed)
            if completed else 0.0
        )
        avg_exec = (
            sum(j.execution_time_s for j in completed) / len(completed)
            if completed else 0.0
        )

        return {
            "total_jobs": total,
            "successful": len(completed),
            "failed": len(failed),
            "retried": len(retried),
            "success_rate_pct": round(len(completed) / total * 100, 1) if total else 0.0,
            "avg_queue_time_s": round(avg_queue, 4),
            "avg_execution_time_s": round(avg_exec, 4),
            "job_details": [j.to_dict() for j in self.jobs],
        }


def main():
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "job_manager_results.json")

    print("=== Q07 Quantum Job Manager ===")

    manager = QuantumJobManager(failure_rate=0.25, rng_seed=42)

    # Submit 10 jobs across different backends
    job_specs = [
        ("ghz_5q", 5, 8192, "ibm_falcon_r5"),
        ("vqe_4q", 4, 4096, "ibm_falcon_r5"),
        ("qft_6q", 6, 8192, "ibm_eagle_r3"),
        ("grover_4q", 4, 2048, "ionq_harmony"),
        ("bernstein_3q", 3, 1024, "aws_sv1"),
        ("ghz_7q", 7, 8192, "ibm_eagle_r3"),
        ("qpe_5q", 5, 4096, "rigetti_aspen"),
        ("vqe_6q", 6, 8192, "ionq_harmony"),
        ("qft_4q", 4, 4096, "aws_sv1"),
        ("grover_5q", 5, 8192, "ibm_falcon_r5"),
    ]

    print(f"Submitting {len(job_specs)} jobs...")
    jobs = [manager.submit(*spec) for spec in job_specs]

    print("Running jobs with retry logic...")
    manager.run_batch(jobs)

    results = manager.summary()

    print(f"\nResults:")
    print(f"  Total:      {results['total_jobs']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed:     {results['failed']}")
    print(f"  Retried:    {results['retried']}")
    print(f"  Success rate: {results['success_rate_pct']}%")
    print(f"  Avg queue time:  {results['avg_queue_time_s']:.4f}s")
    print(f"  Avg exec time:   {results['avg_execution_time_s']:.4f}s")

    # Trim result_counts for cleaner JSON
    for job in results["job_details"]:
        if job.get("result_counts") and len(job["result_counts"]) > 5:
            top5 = sorted(job["result_counts"].items(), key=lambda x: -x[1])[:5]
            job["result_counts"] = dict(top5)
            job["result_counts"]["__truncated__"] = True

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
    return results


if __name__ == "__main__":
    main()
