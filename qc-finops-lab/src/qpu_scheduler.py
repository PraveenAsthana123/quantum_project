"""
QPU FinOps: Job Queue & Scheduler
===================================
Purpose   : Priority-queue-based scheduling for QPU jobs with deadline
            awareness, fair-share aging, and throughput telemetry.
Reference : IBM Quantum fair-share scheduler paper; LSF/SLURM priority aging
            algorithms; real-time heapq-based scheduling in Python.
Complexity: O(log n) submit/pop via heapq; O(n) aging sweep per tick;
            O(1) cancel via lazy deletion.

Scheduling policy
-----------------
  1. Primary key : Priority enum ordinal (CRITICAL=0 wins over LOW=3)
  2. Secondary   : Earliest deadline first (EDF) within same priority tier
  3. Tertiary    : FIFO arrival time to break EDF ties
  4. Anti-starvation: Jobs waiting > aging_threshold_s gain one priority
     level (aging) up to CRITICAL; prevents LOW-priority starvation.

Usage
-----
    from qpu_scheduler import QPUScheduler, Priority
    from qpu_cost_model import QPUJob

    sched = QPUScheduler()
    job   = QPUJob(circuit_depth=10, n_qubits=8, n_shots=1024,
                   gate_count=60, error_rate=0.001)
    jid = sched.submit(job, priority=Priority.HIGH)
    next_job = sched.schedule_next()
    stats = sched.get_throughput_stats()
"""
from __future__ import annotations

import heapq
import math
import time
import uuid
import json
import statistics
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple

from qpu_cost_model import QPUJob, QPUCostModeler


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Priority(IntEnum):
    """Job priority levels.  Lower ordinal = higher scheduling urgency."""
    CRITICAL = 0
    HIGH     = 1
    NORMAL   = 2
    LOW      = 3


class JobStatus(IntEnum):
    """Lifecycle states for a scheduled QPU job."""
    QUEUED    = 0
    RUNNING   = 1
    COMPLETED = 2
    FAILED    = 3
    CANCELLED = 4


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ScheduledJob:
    """A QPUJob wrapped with scheduling metadata."""
    id:           str
    job:          QPUJob
    priority:     Priority
    submitted_at: float          # Unix epoch seconds
    deadline:     Optional[float]  # Unix epoch seconds; None = best-effort
    tags:         List[str] = field(default_factory=list)
    status:       JobStatus = JobStatus.QUEUED
    started_at:   Optional[float] = None
    completed_at: Optional[float] = None
    retries:      int = 0
    aged_priority: Optional[Priority] = None  # effective after aging

    @property
    def effective_priority(self) -> int:
        """Priority after aging adjustments."""
        if self.aged_priority is not None:
            return int(self.aged_priority)
        return int(self.priority)

    @property
    def wait_time_s(self) -> float:
        """Seconds since submission (if still queued/running)."""
        return time.time() - self.submitted_at

    @property
    def turnaround_s(self) -> Optional[float]:
        """Queue wait + execution time (only for completed/failed jobs)."""
        if self.completed_at is not None:
            return self.completed_at - self.submitted_at
        return None

    def is_overdue(self) -> bool:
        """True if a deadline exists and has already passed."""
        if self.deadline is None:
            return False
        return time.time() > self.deadline


@dataclass(order=True)
class _HeapEntry:
    """
    Heap item that makes ScheduledJob comparable without modifying the
    dataclass itself.  Uses (effective_priority, deadline_key, submitted_at,
    job_id) as the composite sort key.
    """
    effective_priority: int
    deadline_key:       float   # inf if no deadline
    submitted_at:       float
    job_id:             str
    valid:              bool = field(compare=False, default=True)
    sched_job_ref:      Any  = field(compare=False, default=None)  # ScheduledJob

    def __post_init__(self) -> None:
        # Ensure deadline_key is float for comparison
        if self.deadline_key is None:
            object.__setattr__(self, "deadline_key", float("inf"))


# ---------------------------------------------------------------------------
# Main scheduler
# ---------------------------------------------------------------------------

class QPUScheduler:
    """
    Priority-queue QPU job scheduler with:
      - heapq-based O(log n) submit / pop
      - Lazy deletion (cancel marks invalid; popped on next schedule_next call)
      - EDF tie-breaking within priority tier
      - Anti-starvation aging: jobs gain priority every aging_threshold_s seconds
      - Throughput telemetry: jobs/hour, avg/p50/p99 wait times
    """

    DEFAULT_AGING_THRESHOLD_S = 300.0   # 5 minutes without scheduling → +1 priority
    DEFAULT_MAX_CONCURRENCY   = 4       # simultaneous running slots

    def __init__(
        self,
        aging_threshold_s: float = DEFAULT_AGING_THRESHOLD_S,
        max_concurrency:   int   = DEFAULT_MAX_CONCURRENCY,
        cost_modeler:      Optional[QPUCostModeler] = None,
    ) -> None:
        self._heap:       List[_HeapEntry]          = []
        self._jobs:       Dict[str, ScheduledJob]   = {}   # id → ScheduledJob
        self._running:    Dict[str, ScheduledJob]   = {}   # id → ScheduledJob
        self._completed:  List[ScheduledJob]        = []
        self._cancelled:  Dict[str, ScheduledJob]   = {}
        self._invalid_ids: set                       = set()  # lazy-deleted

        self.aging_threshold_s = aging_threshold_s
        self.max_concurrency   = max_concurrency
        self._modeler          = cost_modeler or QPUCostModeler()

        self._submit_count     = 0
        self._total_wait_s:    List[float] = []   # wait times of completed jobs
        self._total_exec_s:    List[float] = []   # execution times

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(
        self,
        job:      QPUJob,
        priority: Priority = Priority.NORMAL,
        deadline: Optional[float] = None,
        tags:     Optional[List[str]] = None,
    ) -> str:
        """
        Submit a job to the queue.

        Parameters
        ----------
        job      : QPUJob to execute
        priority : scheduling priority (default NORMAL)
        deadline : Unix timestamp by which the job should start; None = best-effort
        tags     : arbitrary metadata labels

        Returns
        -------
        job_id : str (UUID4)
        """
        job_id = str(uuid.uuid4())
        now    = time.time()

        sched_job = ScheduledJob(
            id=job_id, job=job, priority=priority,
            submitted_at=now, deadline=deadline,
            tags=tags or [], status=JobStatus.QUEUED,
        )
        self._jobs[job_id] = sched_job
        self._push_heap(sched_job)
        self._submit_count += 1
        return job_id

    def schedule_next(self) -> Optional[ScheduledJob]:
        """
        Pop the highest-priority job from the queue and mark it RUNNING.

        Applies aging before selecting, then does lazy-deletion of cancelled
        or already-running jobs while scanning the heap.

        Returns
        -------
        ScheduledJob if one is available and a concurrency slot is free, else None.
        """
        if len(self._running) >= self.max_concurrency:
            return None

        self._apply_aging()

        while self._heap:
            entry = heapq.heappop(self._heap)

            # Lazy deletion
            if entry.job_id in self._invalid_ids or not entry.valid:
                continue
            if entry.job_id not in self._jobs:
                continue

            sched_job = self._jobs[entry.job_id]

            # Skip jobs that have already moved out of QUEUED state
            if sched_job.status != JobStatus.QUEUED:
                continue

            # Mark running
            sched_job.status     = JobStatus.RUNNING
            sched_job.started_at = time.time()
            self._running[entry.job_id] = sched_job
            return sched_job

        return None

    def complete_job(self, job_id: str, success: bool = True) -> bool:
        """
        Mark a running job as COMPLETED or FAILED.

        Returns True if the transition succeeded.
        """
        if job_id not in self._running:
            return False

        sched_job = self._running.pop(job_id)
        now = time.time()
        sched_job.completed_at = now
        sched_job.status = JobStatus.COMPLETED if success else JobStatus.FAILED

        # Record telemetry
        wait_s = (sched_job.started_at - sched_job.submitted_at
                  if sched_job.started_at else 0.0)
        exec_s = now - (sched_job.started_at or now)
        self._total_wait_s.append(wait_s)
        self._total_exec_s.append(exec_s)

        self._completed.append(sched_job)
        del self._jobs[job_id]
        return True

    def cancel(self, job_id: str) -> bool:
        """
        Cancel a QUEUED job.  Running jobs cannot be cancelled here
        (use abort_running for that).

        Returns True if the job was found and cancelled.
        """
        if job_id not in self._jobs:
            return False
        sched_job = self._jobs[job_id]
        if sched_job.status != JobStatus.QUEUED:
            return False

        sched_job.status = JobStatus.CANCELLED
        self._invalid_ids.add(job_id)
        self._cancelled[job_id] = sched_job
        del self._jobs[job_id]
        return True

    def abort_running(self, job_id: str) -> bool:
        """Force-abort a RUNNING job and mark it FAILED."""
        if job_id not in self._running:
            return False
        return self.complete_job(job_id, success=False)

    def requeue(self, job_id: str, new_priority: Optional[Priority] = None) -> bool:
        """
        Re-queue a FAILED job (e.g. after a QPU error).
        Increments the retry counter.
        """
        # Look in completed for the failed job
        failed = next((j for j in self._completed
                       if j.id == job_id and j.status == JobStatus.FAILED), None)
        if failed is None:
            return False

        self._completed = [j for j in self._completed if j.id != job_id]
        failed.status       = JobStatus.QUEUED
        failed.started_at   = None
        failed.completed_at = None
        failed.retries     += 1
        failed.submitted_at = time.time()
        if new_priority is not None:
            failed.priority      = new_priority
            failed.aged_priority = None

        self._jobs[job_id] = failed
        if job_id in self._invalid_ids:
            self._invalid_ids.discard(job_id)
        self._push_heap(failed)
        return True

    # ------------------------------------------------------------------
    # Queue inspection
    # ------------------------------------------------------------------

    def get_queue_depth(self) -> int:
        """Number of jobs currently in QUEUED state."""
        return sum(1 for j in self._jobs.values() if j.status == JobStatus.QUEUED)

    def get_running_count(self) -> int:
        """Number of currently RUNNING jobs."""
        return len(self._running)

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """Look up any job (queued, running, completed, cancelled)."""
        if job_id in self._jobs:
            return self._jobs[job_id]
        if job_id in self._running:
            return self._running[job_id]
        for j in self._completed:
            if j.id == job_id:
                return j
        return self._cancelled.get(job_id)

    def list_queued(self, priority_filter: Optional[Priority] = None) -> List[ScheduledJob]:
        """Return queued jobs, optionally filtered by priority."""
        jobs = [j for j in self._jobs.values() if j.status == JobStatus.QUEUED]
        if priority_filter is not None:
            jobs = [j for j in jobs if j.priority == priority_filter]
        jobs.sort(key=lambda j: (j.effective_priority,
                                  j.deadline or float("inf"),
                                  j.submitted_at))
        return jobs

    def list_overdue(self) -> List[ScheduledJob]:
        """Return all queued jobs whose deadline has passed."""
        return [j for j in self._jobs.values()
                if j.status == JobStatus.QUEUED and j.is_overdue()]

    # ------------------------------------------------------------------
    # Wait-time estimation
    # ------------------------------------------------------------------

    def estimate_wait_time(self, priority: Priority) -> float:
        """
        Estimate how many seconds a newly-submitted job at `priority` would
        wait before being scheduled.

        Method
        ------
        Count jobs ahead in queue (same or higher priority + overdue jobs
        at any priority), multiply by average execution time of completed
        jobs (fallback = 30 s).
        """
        avg_exec = (statistics.mean(self._total_exec_s)
                    if self._total_exec_s else 30.0)
        jobs_ahead = sum(
            1 for j in self._jobs.values()
            if j.status == JobStatus.QUEUED and (
                j.effective_priority <= int(priority) or j.is_overdue()
            )
        )
        # Divide by concurrency slots
        effective_ahead = max(0, jobs_ahead - self.max_concurrency)
        return effective_ahead * avg_exec / max(1, self.max_concurrency)

    # ------------------------------------------------------------------
    # Throughput statistics
    # ------------------------------------------------------------------

    def get_throughput_stats(self) -> Dict[str, Any]:
        """
        Return throughput telemetry for the scheduler lifetime.

        Keys
        ----
        total_submitted, total_completed, total_failed, total_cancelled,
        currently_queued, currently_running,
        jobs_per_hour (based on completed jobs and elapsed time),
        avg_wait_s, p50_wait_s, p99_wait_s,
        avg_exec_s, p99_exec_s,
        priority_breakdown (count per priority level for queued jobs)
        """
        completed_count = sum(1 for j in self._completed
                              if j.status == JobStatus.COMPLETED)
        failed_count    = sum(1 for j in self._completed
                              if j.status == JobStatus.FAILED)

        def percentile(data: List[float], pct: float) -> float:
            if not data:
                return 0.0
            s = sorted(data)
            idx = min(len(s) - 1, math.ceil(pct / 100.0 * len(s)) - 1)
            return s[max(0, idx)]

        wait_data = self._total_wait_s
        exec_data = self._total_exec_s

        # jobs/hour: use first-completed to now as observation window
        jobs_per_hour = 0.0
        if self._completed:
            oldest_submit = min(j.submitted_at for j in self._completed)
            window_h = (time.time() - oldest_submit) / 3600.0
            if window_h > 0:
                jobs_per_hour = len(self._completed) / window_h

        priority_breakdown: Dict[str, int] = {p.name: 0 for p in Priority}
        for j in self._jobs.values():
            if j.status == JobStatus.QUEUED:
                priority_breakdown[j.priority.name] += 1

        return {
            "total_submitted":    self._submit_count,
            "total_completed":    completed_count,
            "total_failed":       failed_count,
            "total_cancelled":    len(self._cancelled),
            "total_requeued":     sum(j.retries for j in self._completed),
            "currently_queued":   self.get_queue_depth(),
            "currently_running":  self.get_running_count(),
            "jobs_per_hour":      round(jobs_per_hour, 2),
            "avg_wait_s":         round(statistics.mean(wait_data), 3) if wait_data else 0.0,
            "p50_wait_s":         round(percentile(wait_data, 50), 3),
            "p99_wait_s":         round(percentile(wait_data, 99), 3),
            "avg_exec_s":         round(statistics.mean(exec_data), 3) if exec_data else 0.0,
            "p99_exec_s":         round(percentile(exec_data, 99), 3),
            "max_concurrency":    self.max_concurrency,
            "priority_breakdown": priority_breakdown,
        }

    # ------------------------------------------------------------------
    # Budget-aware scheduling extension
    # ------------------------------------------------------------------

    def submit_with_cost_check(
        self,
        job:             QPUJob,
        priority:        Priority = Priority.NORMAL,
        deadline:        Optional[float] = None,
        max_cost_usd:    Optional[float] = None,
        preferred_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Estimate cost before submitting; reject if over budget.

        Parameters
        ----------
        max_cost_usd        : reject if cheapest estimate exceeds this
        preferred_provider  : if set, prefer this provider (IBM_Quantum /
                              AWS_Braket / Azure_Quantum / Google_Cirq)

        Returns dict: job_id (or None if rejected), estimates, decision
        """
        estimates = self._modeler.compare_providers(job)
        feasible  = [e for e in estimates if math.isfinite(e.cost_usd)]

        if preferred_provider:
            preferred = [e for e in feasible if e.provider == preferred_provider]
            feasible  = preferred + [e for e in feasible if e.provider != preferred_provider]

        cheapest = feasible[0] if feasible else None

        if cheapest is None:
            return {
                "job_id":   None,
                "decision": "REJECTED_NO_FEASIBLE_PROVIDER",
                "estimates": [],
            }

        if max_cost_usd is not None and cheapest.cost_usd > max_cost_usd:
            return {
                "job_id":          None,
                "decision":        "REJECTED_OVER_BUDGET",
                "cheapest_cost":   cheapest.cost_usd,
                "budget_usd":      max_cost_usd,
                "recommended":     cheapest.provider,
                "estimates":       [{"provider": e.provider, "cost_usd": e.cost_usd,
                                     "backend": e.backend} for e in feasible],
            }

        job_id = self.submit(job, priority=priority, deadline=deadline)
        return {
            "job_id":       job_id,
            "decision":     "ACCEPTED",
            "selected_provider": cheapest.provider,
            "estimated_cost_usd": cheapest.cost_usd,
            "estimated_latency_ms": cheapest.latency_ms,
            "estimates":    [{"provider": e.provider, "cost_usd": e.cost_usd,
                              "backend": e.backend} for e in feasible],
        }

    def drain(self, simulate_exec_s: float = 0.01) -> List[ScheduledJob]:
        """
        Convenience method for testing: drain entire queue by completing jobs
        instantly (simulating fast execution).

        Returns list of completed ScheduledJobs.
        """
        completed = []
        while self.get_queue_depth() > 0 or self.get_running_count() > 0:
            # Fill running slots
            while self.get_running_count() < self.max_concurrency and self.get_queue_depth() > 0:
                sj = self.schedule_next()
                if sj is None:
                    break

            # Complete all running
            for jid in list(self._running.keys()):
                time.sleep(simulate_exec_s)
                self.complete_job(jid, success=True)
                completed.append(self._completed[-1])

        return completed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _push_heap(self, sched_job: ScheduledJob) -> None:
        deadline_key = sched_job.deadline if sched_job.deadline is not None else float("inf")
        entry = _HeapEntry(
            effective_priority = sched_job.effective_priority,
            deadline_key       = deadline_key,
            submitted_at       = sched_job.submitted_at,
            job_id             = sched_job.id,
            valid              = True,
            sched_job_ref      = sched_job,
        )
        heapq.heappush(self._heap, entry)

    def _apply_aging(self) -> None:
        """
        Scan all QUEUED jobs.  If a job has been waiting longer than
        aging_threshold_s, boost its effective priority by one level
        (minimum CRITICAL).  Re-insert into heap with updated key.
        """
        now = time.time()
        rescheduled: List[ScheduledJob] = []

        for job_id, sched_job in self._jobs.items():
            if sched_job.status != JobStatus.QUEUED:
                continue
            wait = now - sched_job.submitted_at
            current_p = sched_job.effective_priority
            n_boosts  = int(wait // self.aging_threshold_s)
            if n_boosts == 0:
                continue
            new_p = max(int(Priority.CRITICAL), current_p - n_boosts)
            if new_p < current_p:
                sched_job.aged_priority = Priority(new_p)
                rescheduled.append(sched_job)

        if rescheduled:
            # Invalidate old entries and re-push with new keys
            for sched_job in rescheduled:
                self._invalid_ids.add(sched_job.id)
                self._push_heap(sched_job)
                self._invalid_ids.discard(sched_job.id)  # new entry is valid

    def snapshot(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of queue state."""
        def _job_dict(j: ScheduledJob) -> Dict[str, Any]:
            return {
                "id":           j.id,
                "priority":     j.priority.name,
                "effective_p":  Priority(j.effective_priority).name,
                "status":       j.status.name,
                "submitted_at": j.submitted_at,
                "deadline":     j.deadline,
                "wait_s":       round(j.wait_time_s, 1),
                "tags":         j.tags,
                "retries":      j.retries,
                "n_qubits":     j.job.n_qubits,
                "n_shots":      j.job.n_shots,
                "algorithm":    j.job.algorithm_tag,
            }

        return {
            "queued":    [_job_dict(j) for j in self.list_queued()],
            "running":   [_job_dict(j) for j in self._running.values()],
            "completed": [_job_dict(j) for j in self._completed[-20:]],  # last 20
            "stats":     self.get_throughput_stats(),
        }
