"""
QPU FinOps: Dashboard & Reporting Engine
==========================================
Purpose   : Aggregate QPU spend data into reports, detect cost anomalies,
            compute ROI vs classical compute, forecast spend, optimise shot
            counts, and estimate carbon footprint.
Reference : Z-score anomaly detection (Shewhart 1931); Chebyshev shot bound
            (Audenaert 2014); linear regression for spend forecasting;
            carbon intensity data from IEA 2023 / provider sustainability reports.
Complexity: O(n) for report/anomaly; O(n log n) for regression (numpy lstsq).

Key outputs
-----------
  monthly_report       : total spend, per-algorithm breakdown, utilisation
  cost_anomaly_detection: z-score alerts (|z| > 2.5)
  roi_analysis         : break-even qubits, ROI %, recommendation
  budget_forecast      : n-month-ahead linear extrapolation with CI
  optimize_shot_count  : minimum shots for target precision (Chebyshev)
  carbon_footprint     : CO₂ grams per provider + job count

Usage
-----
    from finops_dashboard import FinOpsDashboard
    db = FinOpsDashboard()
    report = db.generate_monthly_report("2025-10", jobs_run)
    anomalies = db.cost_anomaly_detection(historical_spend)
    roi = db.roi_analysis(classical_cost=50.0, quantum_cost=200.0, speedup=100.0)
"""
from __future__ import annotations

import math
import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Carbon intensity constants (kg CO₂ per kWh)
# ---------------------------------------------------------------------------
# Source: IEA 2023 grid carbon intensity + provider sustainability reports

CARBON_INTENSITY_KG_KWH: Dict[str, float] = {
    "IBM_Quantum":    0.020,   # IBM uses renewable energy for quantum data centres
    "AWS_Braket":     0.045,   # AWS US-East average (mixed grid)
    "Azure_Quantum":  0.040,   # Microsoft Azure (partial renewable)
    "Google_Cirq":    0.010,   # Google: 100% renewable + carbon offsets
}

# Power consumption estimates per QPU job (kWh)
# Includes dilution refrigerator (~1-5 kW continuous) + electronics overhead
# Amortised per job: fridge power × job_exec_time / 3600
FRIDGE_POWER_KW: Dict[str, float] = {
    "IBM_Quantum":    3.5,     # dilution fridge + control electronics
    "AWS_Braket":     2.8,     # Rigetti / IonQ systems (varies)
    "Azure_Quantum":  4.0,     # Quantinuum + IonQ systems
    "Google_Cirq":    5.0,     # Sycamore + Willow systems (larger cryostats)
}

# Typical job execution time in hours (for carbon calc)
EXEC_TIME_H: Dict[str, float] = {
    "IBM_Quantum":    0.00010,   # ~0.36 s average job exec
    "AWS_Braket":     0.00015,   # ~0.54 s
    "Azure_Quantum":  0.00050,   # ~1.8 s (trapped-ion slower)
    "Google_Cirq":    0.00008,   # ~0.29 s
}

# Classical compute comparison: AWS EC2 c6i.large = $0.085/hr, 200 GFLOPS
EC2_COST_PER_HOUR      = 0.085   # USD
EC2_GFLOPS             = 200.0   # GFLOPS for c6i.large
CLASSICAL_KWH_PER_HOUR = 0.120   # kWh for a typical server


# ---------------------------------------------------------------------------
# Data class for a single job record
# ---------------------------------------------------------------------------

@dataclass
class JobRecord:
    """A completed QPU job with cost and metadata for reporting."""
    job_id:       str
    algorithm:    str
    provider:     str
    backend:      str
    n_qubits:     int
    n_shots:      int
    cost_usd:     float
    latency_ms:   float
    timestamp:    float = field(default_factory=time.time)
    success:      bool  = True
    tags:         List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Main dashboard class
# ---------------------------------------------------------------------------

class FinOpsDashboard:
    """
    QPU FinOps reporting, anomaly detection, ROI analysis, forecasting,
    shot optimisation, and carbon footprint tracking.
    """

    def __init__(self) -> None:
        self._records:   List[JobRecord]   = []
        self._spend_log: List[Dict[str, Any]] = []

    def add_record(self, record: JobRecord) -> None:
        """Ingest a completed job record for future reporting."""
        self._records.append(record)

    def add_records(self, records: List[JobRecord]) -> None:
        for r in records:
            self.add_record(r)

    # ------------------------------------------------------------------
    # 1. Monthly report
    # ------------------------------------------------------------------

    def generate_monthly_report(
        self,
        month: str,
        jobs_run: Optional[List[JobRecord]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive monthly FinOps report.

        Parameters
        ----------
        month    : "YYYY-MM" label for the report
        jobs_run : list of JobRecord; if None, uses self._records

        Returns
        -------
        dict with keys:
          month, total_jobs, total_spend_usd, success_rate_pct,
          cost_per_algorithm (dict), provider_utilisation (dict),
          avg_cost_per_job, avg_latency_ms,
          most_expensive_algorithm, cheapest_provider,
          savings_achieved_usd, top_cost_drivers
        """
        jobs = jobs_run if jobs_run is not None else self._records
        if not jobs:
            return {"month": month, "total_jobs": 0, "total_spend_usd": 0.0,
                    "warning": "No job records provided"}

        total_jobs    = len(jobs)
        total_spend   = sum(j.cost_usd for j in jobs)
        success_count = sum(1 for j in jobs if j.success)
        success_rate  = 100.0 * success_count / total_jobs

        # Cost per algorithm
        alg_spend: Dict[str, float]  = {}
        alg_count: Dict[str, int]    = {}
        for j in jobs:
            alg_spend[j.algorithm] = alg_spend.get(j.algorithm, 0.0) + j.cost_usd
            alg_count[j.algorithm] = alg_count.get(j.algorithm, 0) + 1

        cost_per_algorithm = {
            alg: {
                "total_spend_usd": round(spend, 4),
                "job_count":       alg_count[alg],
                "avg_cost_usd":    round(spend / alg_count[alg], 6),
                "share_pct":       round(100.0 * spend / total_spend, 1) if total_spend else 0,
            }
            for alg, spend in sorted(alg_spend.items(), key=lambda x: -x[1])
        }

        # Provider utilisation
        prov_spend: Dict[str, float] = {}
        prov_count: Dict[str, int]   = {}
        for j in jobs:
            prov_spend[j.provider] = prov_spend.get(j.provider, 0.0) + j.cost_usd
            prov_count[j.provider] = prov_count.get(j.provider, 0) + 1

        provider_utilisation = {
            prov: {
                "total_spend_usd": round(spend, 4),
                "job_count":       prov_count[prov],
                "share_pct":       round(100.0 * spend / total_spend, 1) if total_spend else 0,
            }
            for prov, spend in sorted(prov_spend.items(), key=lambda x: -x[1])
        }

        avg_cost     = total_spend / total_jobs
        avg_latency  = statistics.mean(j.latency_ms for j in jobs)

        most_expensive_alg = max(alg_spend, key=alg_spend.get) if alg_spend else "N/A"
        cheapest_prov      = min(prov_spend, key=prov_spend.get) if prov_spend else "N/A"

        # Savings achieved: compare to most expensive provider for each job
        # Heuristic: if any job was on the cheapest backend, estimate savings
        savings_achieved = self._estimate_savings(jobs)

        # Top cost drivers
        top_drivers = sorted(
            cost_per_algorithm.items(),
            key=lambda x: x[1]["total_spend_usd"],
            reverse=True,
        )[:5]

        return {
            "month":                    month,
            "total_jobs":               total_jobs,
            "total_spend_usd":          round(total_spend, 4),
            "success_rate_pct":         round(success_rate, 1),
            "avg_cost_per_job_usd":     round(avg_cost, 6),
            "avg_latency_ms":           round(avg_latency, 1),
            "most_expensive_algorithm": most_expensive_alg,
            "cheapest_provider":        cheapest_prov,
            "savings_achieved_usd":     round(savings_achieved, 4),
            "cost_per_algorithm":       cost_per_algorithm,
            "provider_utilisation":     provider_utilisation,
            "top_cost_drivers":         [k for k, _ in top_drivers],
        }

    # ------------------------------------------------------------------
    # 2. Anomaly detection
    # ------------------------------------------------------------------

    def cost_anomaly_detection(
        self,
        spend_history: List[float],
        z_threshold: float = 2.5,
    ) -> List[Dict[str, Any]]:
        """
        Detect cost anomalies in a time-series of daily/weekly spend.

        Method: Shewhart control chart (z-score).
          z = (x - μ) / σ
          Alert when |z| > z_threshold (default 2.5 ≈ 98.8th percentile).

        Parameters
        ----------
        spend_history : list of spend values (USD), one per period
        z_threshold   : alert threshold (default 2.5)

        Returns list of dicts: index, spend_usd, z_score, direction, severity
        """
        if len(spend_history) < 3:
            return [{"warning": "Need ≥ 3 data points for anomaly detection"}]

        arr  = np.array(spend_history, dtype=float)
        mu   = float(np.mean(arr))
        sigma = float(np.std(arr, ddof=1))

        if sigma < 1e-10:
            return [{"info": "Zero variance in spend history; no anomalies detectable"}]

        anomalies: List[Dict[str, Any]] = []
        for i, x in enumerate(arr):
            z = (x - mu) / sigma
            if abs(z) > z_threshold:
                direction = "spike" if z > 0 else "drop"
                severity  = (
                    "CRITICAL" if abs(z) > 4.0 else
                    "HIGH"     if abs(z) > 3.0 else
                    "MEDIUM"
                )
                anomalies.append({
                    "period_index":  i,
                    "spend_usd":     round(x, 4),
                    "mean_usd":      round(mu, 4),
                    "std_usd":       round(sigma, 4),
                    "z_score":       round(z, 3),
                    "direction":     direction,
                    "severity":      severity,
                    "deviation_pct": round(100.0 * abs(x - mu) / mu, 1) if mu else 0,
                    "recommendation": (
                        f"Investigate period {i}: spend ${x:.2f} is "
                        f"{abs(z):.1f}σ {'above' if z > 0 else 'below'} mean ${mu:.2f}"
                    ),
                })

        return anomalies if anomalies else [{"info": "No anomalies detected"}]

    # ------------------------------------------------------------------
    # 3. ROI analysis
    # ------------------------------------------------------------------

    def roi_analysis(
        self,
        classical_compute_cost: float,
        quantum_compute_cost: float,
        speedup_factor: float,
        classical_kw: float = 0.3,
        quantum_kw:   float = 5.0,
    ) -> Dict[str, Any]:
        """
        Compute quantum vs classical ROI.

        Model
        -----
        quantum_effective_cost = quantum_compute_cost / speedup_factor
          (cost per unit of equivalent classical work)
        roi_percent = (classical_compute_cost - quantum_effective_cost) /
                       quantum_compute_cost × 100

        break_even_speedup: speedup at which quantum_cost == classical_cost
          → break_even_speedup = quantum_cost / classical_cost

        break_even_qubits (heuristic): beyond ~50 logical qubits, quantum
          advantage begins to emerge for specific problem classes.

        Carbon comparison: classical uses ~0.3 kW; quantum uses ~5 kW
          (dilution fridge); but quantum runs much shorter wall-clock.
        """
        if speedup_factor <= 0:
            raise ValueError("speedup_factor must be positive")
        if classical_compute_cost <= 0 or quantum_compute_cost <= 0:
            raise ValueError("costs must be positive")

        quantum_eff_cost     = quantum_compute_cost / speedup_factor
        raw_savings          = classical_compute_cost - quantum_eff_cost
        roi_pct              = 100.0 * raw_savings / quantum_compute_cost

        break_even_speedup   = quantum_compute_cost / classical_compute_cost
        break_even_qubits    = 50  # heuristic threshold for quantum advantage

        # Carbon: assume classical_hours = 1 unit of wall time
        classical_co2 = classical_kw  * CARBON_INTENSITY_KG_KWH.get("AWS_Braket", 0.045)
        quantum_co2   = quantum_kw    * CARBON_INTENSITY_KG_KWH.get("IBM_Quantum", 0.020)
        co2_pct_diff  = 100.0 * (classical_co2 - quantum_co2) / classical_co2

        # Recommendation
        if roi_pct > 50:
            rec = "STRONG_BUY: Quantum provides significant cost advantage at this speedup."
        elif roi_pct > 0:
            rec = "MARGINAL_BUY: Quantum is cost-effective but advantage is thin."
        elif roi_pct > -50:
            rec = "WAIT: Quantum currently costs more. Monitor hardware improvements."
        else:
            rec = "NOT_YET: Classical compute is substantially cheaper at current QPU pricing."

        return {
            "classical_compute_cost_usd":   round(classical_compute_cost, 4),
            "quantum_compute_cost_usd":     round(quantum_compute_cost, 4),
            "speedup_factor":               speedup_factor,
            "quantum_effective_cost_usd":   round(quantum_eff_cost, 4),
            "savings_usd":                  round(raw_savings, 4),
            "roi_percent":                  round(roi_pct, 2),
            "break_even_speedup":           round(break_even_speedup, 4),
            "break_even_qubits_heuristic":  break_even_qubits,
            "classical_co2_kg_per_job":     round(classical_co2, 6),
            "quantum_co2_kg_per_job":       round(quantum_co2, 6),
            "carbon_reduction_pct":         round(co2_pct_diff, 1),
            "recommendation":               rec,
        }

    # ------------------------------------------------------------------
    # 4. Budget forecast
    # ------------------------------------------------------------------

    def budget_forecast(
        self,
        historical_spend: List[float],
        months_ahead: int = 3,
        confidence_level: float = 0.95,
    ) -> Dict[str, Any]:
        """
        Forecast future spend using ordinary least-squares linear regression.

        Model: y = a·t + b,  t = {0, 1, ..., n-1}
        Confidence interval: ŷ ± t_{α/2, n-2} × se_forecast

        Parameters
        ----------
        historical_spend : list of monthly spend (USD), ordered oldest→newest
        months_ahead     : number of future months to forecast
        confidence_level : CI level (default 0.95)

        Returns dict: coefficients, r_squared, forecast list (month, usd, lower, upper)
        """
        n = len(historical_spend)
        if n < 2:
            raise ValueError("Need at least 2 months of historical data")

        t    = np.arange(n, dtype=float)
        y    = np.array(historical_spend, dtype=float)

        # OLS via numpy (A @ [a, b] = y)
        A    = np.column_stack([t, np.ones(n)])
        coeffs, residuals, rank, sv = np.linalg.lstsq(A, y, rcond=None)
        a, b = float(coeffs[0]), float(coeffs[1])

        y_hat   = a * t + b
        ss_res  = float(np.sum((y - y_hat) ** 2))
        ss_tot  = float(np.sum((y - np.mean(y)) ** 2))
        r2      = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0

        # Standard error of estimate
        if n > 2:
            se_est = math.sqrt(ss_res / (n - 2))
        else:
            se_est = 0.0

        # t-critical value (two-tailed) — approximation for common levels
        t_crits = {0.90: 1.645, 0.95: 1.960, 0.99: 2.576}
        t_crit  = t_crits.get(confidence_level, 1.960)

        forecast: List[Dict[str, Any]] = []
        for k in range(1, months_ahead + 1):
            t_future  = float(n - 1 + k)
            y_pred    = a * t_future + b
            # Standard error for prediction: se × sqrt(1 + 1/n + (t-t_bar)²/Stt)
            t_bar     = np.mean(t)
            stt       = float(np.sum((t - t_bar) ** 2))
            se_pred   = se_est * math.sqrt(1 + 1.0/n + (t_future - t_bar)**2 / (stt or 1))
            margin    = t_crit * se_pred
            forecast.append({
                "month_ahead":  k,
                "forecast_usd": round(max(0.0, y_pred), 2),
                "lower_ci_usd": round(max(0.0, y_pred - margin), 2),
                "upper_ci_usd": round(max(0.0, y_pred + margin), 2),
                "trend":        "increasing" if a > 0.01 else ("decreasing" if a < -0.01 else "stable"),
            })

        total_forecast = sum(f["forecast_usd"] for f in forecast)
        mom_growth     = 100.0 * a / (abs(b) or 1.0)   # MoM % change in spend

        return {
            "n_historical_months":   n,
            "historical_spend_usd":  [round(x, 2) for x in historical_spend],
            "slope_usd_per_month":   round(a, 4),
            "intercept_usd":         round(b, 4),
            "r_squared":             round(r2, 4),
            "se_estimate":           round(se_est, 4),
            "confidence_level":      confidence_level,
            "mom_growth_pct":        round(mom_growth, 2),
            "months_ahead":          months_ahead,
            "total_forecast_usd":    round(total_forecast, 2),
            "forecast":              forecast,
            "warning": (
                "Low R² — spend is not well-explained by linear trend; "
                "CI may be unreliable." if r2 < 0.6 else None
            ),
        }

    # ------------------------------------------------------------------
    # 5. Shot count optimisation
    # ------------------------------------------------------------------

    def optimize_shot_count(
        self,
        target_precision: float,
        current_shots: int,
        confidence: float = 0.95,
        method: str = "chebyshev",
    ) -> Dict[str, Any]:
        """
        Recommend minimum shot count for a given measurement precision.

        Methods
        -------
        chebyshev : distribution-free bound
                    P(|X̄ - μ| ≥ ε) ≤ 1/(4nε²) for Bernoulli r.v.
                    → n ≥ 1/(4ε²(1-confidence))

        hoeffding  : P(|X̄ - μ| ≥ ε) ≤ 2 exp(-2nε²)
                    → n ≥ log(2/(1-confidence)) / (2ε²)

        Parameters
        ----------
        target_precision : ε (absolute error tolerance, e.g. 0.01 = 1%)
        current_shots    : current shot count for comparison
        confidence       : desired confidence level (default 0.95)
        method           : "chebyshev" | "hoeffding"

        Returns dict: recommended_shots, reduction_pct, cost_impact explanation
        """
        if not (0 < target_precision < 1):
            raise ValueError("target_precision must be in (0, 1)")
        if current_shots < 1:
            raise ValueError("current_shots must be >= 1")
        if not (0 < confidence < 1):
            raise ValueError("confidence must be in (0, 1)")

        eps    = target_precision
        alpha  = 1.0 - confidence

        if method == "chebyshev":
            # Chebyshev for Bernoulli: n ≥ 1 / (4 ε² α)
            n_recommended = math.ceil(1.0 / (4.0 * (eps ** 2) * alpha))
            bound_type    = "Chebyshev (distribution-free)"
            formula       = f"n ≥ 1 / (4ε²α) = 1/(4×{eps}²×{alpha}) = {n_recommended}"
        elif method == "hoeffding":
            # Hoeffding: n ≥ log(2/α) / (2ε²)
            n_recommended = math.ceil(math.log(2.0 / alpha) / (2.0 * eps ** 2))
            bound_type    = "Hoeffding (tighter for bounded r.v.)"
            formula       = f"n ≥ ln(2/α)/(2ε²) = ln({2/alpha:.2f})/(2×{eps}²) = {n_recommended}"
        else:
            raise ValueError(f"Unknown method: {method}. Use 'chebyshev' or 'hoeffding'.")

        reduction_shots = current_shots - n_recommended
        reduction_pct   = 100.0 * reduction_shots / current_shots if current_shots > 0 else 0.0

        # Cost impact (IBM Eagle as reference: $1.60/1000 shots)
        ibm_shot_price = 1.60 / 1_000
        cost_current   = current_shots * ibm_shot_price
        cost_recommended = n_recommended * ibm_shot_price
        cost_saving    = cost_current - cost_recommended

        return {
            "target_precision_eps":    eps,
            "confidence_level":        confidence,
            "method":                  method,
            "bound_type":              bound_type,
            "formula":                 formula,
            "current_shots":           current_shots,
            "recommended_shots":       n_recommended,
            "reduction_shots":         max(0, reduction_shots),
            "reduction_pct":           round(max(0.0, reduction_pct), 1),
            "cost_current_ibm_usd":    round(cost_current, 4),
            "cost_recommended_ibm_usd": round(cost_recommended, 4),
            "cost_saving_ibm_usd":     round(max(0.0, cost_saving), 4),
            "note": (
                "Recommended shots exceeds current; consider increasing shot count "
                f"by {-reduction_shots} for the desired precision."
            ) if n_recommended > current_shots else (
                f"Reducing to {n_recommended} shots saves "
                f"${max(0.0, cost_saving):.4f} at IBM Eagle pricing."
            ),
        }

    # ------------------------------------------------------------------
    # 6. Carbon footprint
    # ------------------------------------------------------------------

    def carbon_footprint(
        self,
        provider: str,
        n_jobs: int,
        n_shots_per_job: int = 8_192,
    ) -> Dict[str, Any]:
        """
        Estimate CO₂ emissions for QPU job execution.

        Model
        -----
        energy_kwh = FRIDGE_POWER_KW[provider] × EXEC_TIME_H[provider]
        co2_grams  = energy_kwh × CARBON_INTENSITY_KG_KWH[provider] × 1000 × n_jobs

        Note: overhead computation excluded (cryostat idle power ~1 kW continuous).
        Idle power is attributed to the data centre, not per-job.

        Returns
        -------
        dict: co2_grams_per_job, co2_grams_total, co2_kg_total,
              kwh_per_job, kwh_total, equivalent_km_driven,
              carbon_intensity_kg_kwh, comparison_to_classical
        """
        if provider not in CARBON_INTENSITY_KG_KWH:
            raise ValueError(
                f"Unknown provider '{provider}'. "
                f"Valid: {list(CARBON_INTENSITY_KG_KWH.keys())}"
            )
        if n_jobs < 1:
            raise ValueError("n_jobs must be >= 1")

        power_kw     = FRIDGE_POWER_KW[provider]
        exec_h       = EXEC_TIME_H[provider]
        intensity    = CARBON_INTENSITY_KG_KWH[provider]

        kwh_per_job  = power_kw * exec_h
        co2_kg_job   = kwh_per_job * intensity
        co2_g_job    = co2_kg_job * 1_000.0

        co2_g_total  = co2_g_job * n_jobs
        co2_kg_total = co2_g_total / 1_000.0
        kwh_total    = kwh_per_job * n_jobs

        # Equivalent driving: ~0.21 kg CO₂/km for average passenger car
        km_driven_equiv = co2_kg_total / 0.21

        # Classical comparison: AWS EC2 c6i.large for same wall time
        classical_kwh  = CLASSICAL_KWH_PER_HOUR * exec_h * n_jobs
        classical_co2g = classical_kwh * CARBON_INTENSITY_KG_KWH["AWS_Braket"] * 1_000.0
        carbon_saved_g = classical_co2g - co2_g_total

        return {
            "provider":                  provider,
            "n_jobs":                    n_jobs,
            "n_shots_per_job":           n_shots_per_job,
            "fridge_power_kw":           power_kw,
            "exec_time_h_per_job":       exec_h,
            "carbon_intensity_kg_kwh":   intensity,
            "kwh_per_job":               round(kwh_per_job, 8),
            "kwh_total":                 round(kwh_total, 6),
            "co2_grams_per_job":         round(co2_g_job, 6),
            "co2_grams_total":           round(co2_g_total, 4),
            "co2_kg_total":              round(co2_kg_total, 6),
            "equivalent_km_driven":      round(km_driven_equiv, 4),
            "classical_co2_grams_total": round(classical_co2g, 4),
            "carbon_saved_vs_classical_g": round(carbon_saved_g, 4),
            "carbon_saved_pct":          round(
                100.0 * carbon_saved_g / max(classical_co2g, 1e-10), 1
            ),
            "reference": (
                "IEA 2023 grid carbon intensity; "
                "Krantz et al. 2019 QPU power estimates"
            ),
        }

    # ------------------------------------------------------------------
    # 7. Budget allocation optimiser
    # ------------------------------------------------------------------

    def allocate_budget(
        self,
        total_budget_usd: float,
        algorithm_priorities: Dict[str, float],
        unit_costs: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Allocate a fixed QPU budget across multiple algorithms using a
        priority-weighted approach (greedy proportional allocation).

        Parameters
        ----------
        total_budget_usd      : total monthly QPU budget
        algorithm_priorities  : {algorithm_name: priority_weight}
                                 (higher = more important)
        unit_costs            : {algorithm_name: cost_per_job_usd}

        Returns
        -------
        dict: per-algorithm allocation (budget_usd, max_jobs, utilisation_pct)
        """
        if total_budget_usd <= 0:
            raise ValueError("total_budget_usd must be positive")
        if not algorithm_priorities:
            raise ValueError("algorithm_priorities must not be empty")

        total_weight = sum(algorithm_priorities.values())
        allocations: Dict[str, Dict[str, Any]] = {}

        remaining = total_budget_usd
        for alg, weight in sorted(algorithm_priorities.items(),
                                   key=lambda x: -x[1]):
            share      = weight / total_weight
            alloc_usd  = total_budget_usd * share
            unit_cost  = unit_costs.get(alg, 1.0)
            max_jobs   = int(alloc_usd / unit_cost) if unit_cost > 0 else 0
            allocations[alg] = {
                "priority_weight":  weight,
                "share_pct":        round(share * 100, 1),
                "allocated_usd":    round(alloc_usd, 2),
                "unit_cost_usd":    round(unit_cost, 6),
                "max_jobs":         max_jobs,
                "utilisation_pct":  round(min(100.0, (max_jobs * unit_cost / alloc_usd) * 100), 1)
                                    if alloc_usd > 0 else 0,
            }

        return {
            "total_budget_usd": total_budget_usd,
            "n_algorithms":     len(allocations),
            "allocations":      allocations,
            "fully_allocated":  True,   # proportional allocation always uses 100 %
        }

    # ------------------------------------------------------------------
    # 8. Summary dashboard print
    # ------------------------------------------------------------------

    def print_dashboard(self, jobs: Optional[List[JobRecord]] = None) -> None:
        """Print a text-mode FinOps dashboard summary to stdout."""
        records = jobs if jobs is not None else self._records
        if not records:
            print("[FinOps Dashboard] No records loaded.")
            return

        total_spend = sum(r.cost_usd for r in records)
        n = len(records)
        providers   = sorted({r.provider for r in records})
        algorithms  = sorted({r.algorithm for r in records})

        print("=" * 60)
        print("    QPU FinOps Dashboard")
        print("=" * 60)
        print(f"  Total jobs       : {n}")
        print(f"  Total spend      : ${total_spend:.4f}")
        print(f"  Avg cost/job     : ${total_spend/n:.6f}")
        print(f"  Providers used   : {', '.join(providers)}")
        print(f"  Algorithms       : {', '.join(algorithms)}")
        print("-" * 60)

        # Per-provider spend
        print("  Provider breakdown:")
        for p in providers:
            p_jobs  = [r for r in records if r.provider == p]
            p_spend = sum(r.cost_usd for r in p_jobs)
            print(f"    {p:<25} ${p_spend:>10.4f}  ({len(p_jobs)} jobs)")

        print("-" * 60)
        # Per-algorithm spend
        print("  Algorithm breakdown:")
        for a in algorithms:
            a_jobs  = [r for r in records if r.algorithm == a]
            a_spend = sum(r.cost_usd for r in a_jobs)
            print(f"    {a:<25} ${a_spend:>10.4f}  ({len(a_jobs)} jobs)")
        print("=" * 60)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _estimate_savings(self, jobs: List[JobRecord]) -> float:
        """
        Heuristic: estimate savings vs using the most expensive provider
        for every job.  Uses IBM Eagle as the reference "expensive" provider.
        """
        IBM_EAGLE_SHOT = 1.60 / 1_000
        savings = 0.0
        for j in jobs:
            ibm_cost = j.n_shots * IBM_EAGLE_SHOT
            if j.cost_usd < ibm_cost:
                savings += ibm_cost - j.cost_usd
        return savings
