"""
QPU FinOps: Quantum Resource Estimator
========================================
Purpose   : Estimate logical/physical qubit counts, gate totals, T-gate counts,
            runtime, and error-correction overhead for key quantum algorithms.
Reference : Fowler et al. 2012 (surface code); Babbush et al. 2018 (Shor);
            Bravyi & Haah 2012 (magic state distillation); Reiher et al. 2017
            (VQE for chemistry); Farhi et al. 2014 (QAOA).
Complexity: All estimates are O(1) closed-form calculations; no simulation.

Algorithms covered
------------------
  Shor's RSA factoring          : 2n+3 logical qubits, polylog gate depth
  Grover's unstructured search  : n = ceil(log2(N)) qubits, O(√N) oracle calls
  VQE (variational quantum eigensolver): qubit count = basis size
  QAOA (quantum approximate optimisation): 2×n_nodes qubits, p-layer depth
  QEC overhead (surface code)   : code distance d, syndrome measurement count

Feasibility labels
------------------
  current_hardware   : ≤127 qubits, ≤1000 circuit depth, ≤1e6 gates
  near_term_2028     : ≤1000 qubits, ≤1e4 depth, ≤1e8 gates
  fault_tolerant_only: ≤1e6 physical qubits, ≤1e10 gates
  theoretical_only   : beyond fault_tolerant_only threshold

Usage
-----
    from resource_estimator import ResourceEstimator
    est = ResourceEstimator()
    r = est.estimate_shor_rsa(2048)
    print(r)
    print(est.feasibility_check(r))
"""
from __future__ import annotations

import math
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Physical constants and surface-code parameters
# ---------------------------------------------------------------------------

# Surface code threshold: below this physical error rate, QEC helps
SURFACE_CODE_THRESHOLD     = 0.01     # 1 %
DEFAULT_PHYS_ERROR_RATE    = 0.001    # typical superconductor 2-q gate error
DEFAULT_TARGET_LOGICAL_ERR = 1e-12   # desired logical error rate per gate

# Code distance heuristic from Fowler et al. (Eq. 15):
# d ≈ 2 × ceil( log(n_gates / target_err) / log(1 / p_phys) )
# Physical-to-logical qubit ratio = d²
# (surface code needs d² physical qubits per logical qubit)

# Shor factoring resource estimates (Beauregard 2003; improved Zalka 2006):
# logical qubits = 2n + 3 (n = bit length of RSA modulus)
# Toffoli count  ≈ 40 n³  (dominant cost in optimised circuit)
# T gates per Toffoli ≈ 7
# circuit depth  ≈ 40 n³ (serial, fully optimised)

# Grover oracle model: query complexity = ceil(π/4 × √N)
# Qubit count = ceil(log2(N)) + ancillae ≈ ceil(log2(N)) + 1

# VQE (UCCSD ansatz):
# qubits = basis_set_size (spin orbitals)
# ansatz layers ≈ n_electrons (singles + doubles)
# shots_per_energy_call ≈ 10^4 for 1 mHa precision
# total_shots = shots_per_call × optimiser_iterations

# QAOA (Farhi et al., MaxCut):
# qubits = n_nodes
# two-qubit gates per layer = n_edges ≈ n_nodes * (n_nodes-1) / 2 (complete graph)
# total gates = p_layers × (n_nodes + 2 × n_edges)

# Error correction overhead (Fowler et al. 2012):
# physical qubits = logical_qubits × d²
# syndrome measurements per round = (d² - 1) per logical qubit
# rounds per gate = d (one QEC cycle per surface-code gate)

# Feasibility thresholds (as of 2024-2025)
CURRENT_HW_MAX_QUBITS     = 127        # IBM Eagle
CURRENT_HW_MAX_DEPTH      = 1_000
CURRENT_HW_MAX_GATES      = 1_000_000
NEAR_TERM_MAX_QUBITS      = 1_000      # projected ~2028
NEAR_TERM_MAX_DEPTH       = 10_000
NEAR_TERM_MAX_GATES       = 100_000_000
FAULT_TOL_MAX_PHYS_QUBITS = 1_000_000
FAULT_TOL_MAX_GATES       = 10_000_000_000


# ---------------------------------------------------------------------------
# Helper: surface code distance
# ---------------------------------------------------------------------------

def _code_distance(
    n_gates: int,
    target_logical_err: float = DEFAULT_TARGET_LOGICAL_ERR,
    p_phys: float = DEFAULT_PHYS_ERROR_RATE,
) -> int:
    """
    Compute minimum surface code distance d such that the total logical
    error probability over n_gates is ≤ target_logical_err.

    Fowler et al. 2012, Eq. 15 (simplified):
        p_logical ≈ (p_phys / p_th)^((d+1)/2)
    Solving for d:
        d = 2 × ceil( log(target_err / n_gates) /
                      log(p_phys / SURFACE_CODE_THRESHOLD) ) - 1
    Minimum d = 3 (smallest useful surface code distance).
    """
    if p_phys >= SURFACE_CODE_THRESHOLD:
        return -1   # below threshold; QEC cannot help
    ratio = math.log(p_phys / SURFACE_CODE_THRESHOLD)
    # p_logical per gate ≤ target_logical_err / n_gates
    per_gate_target = target_logical_err / max(1, n_gates)
    log_target = math.log(per_gate_target)
    # (d+1)/2 ≥ log_target / ratio  (ratio < 0 → flip)
    exp_needed = log_target / ratio
    d = max(3, int(math.ceil(2 * exp_needed - 1)))
    return d


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class ResourceEstimator:
    """
    Closed-form quantum resource estimation for common algorithms.
    All methods return a dict with all resource quantities + a
    feasibility label.
    """

    def __init__(
        self,
        p_phys: float = DEFAULT_PHYS_ERROR_RATE,
        target_logical_err: float = DEFAULT_TARGET_LOGICAL_ERR,
    ) -> None:
        self.p_phys            = p_phys
        self.target_logical_err = target_logical_err

    # ------------------------------------------------------------------
    # Shor's algorithm for RSA-n
    # ------------------------------------------------------------------

    def estimate_shor_rsa(self, n_bits: int) -> Dict[str, Any]:
        """
        Estimate resources for factoring an n-bit RSA number using Shor's algorithm.

        Model: Beauregard (2003) + optimisations from Häner, Roetteler, Svore (2017).
          logical_qubits = 2n + 3
          toffoli_gates  = 40 n³   (dominant term)
          T_gates        = 7 × toffoli_gates  (Toffoli → T decomposition)
          CNOT_gates     ≈ 8 n³
          total_gates    = T_gates + CNOT_gates + single_qubit_gates
          circuit_depth  ≈ 40 n³   (fully serialized)

        Physical qubit overhead (surface code):
          code_distance d: use Fowler formula
          physical_qubits = logical_qubits × d²

        Runtime:
          clock_cycle_ns = 1000 ns (superconducting qubits)
          total_cycles = circuit_depth × d  (d syndrome rounds per layer)
          runtime_s = total_cycles × clock_cycle_ns × 1e-9
        """
        if n_bits < 8:
            raise ValueError("n_bits must be >= 8 for RSA factoring")

        logical_qubits = 2 * n_bits + 3
        toffoli_gates  = 40 * (n_bits ** 3)
        t_gates        = 7 * toffoli_gates
        cnot_gates     = 8 * (n_bits ** 3)
        single_q_gates = 3 * (n_bits ** 3)
        total_gates    = t_gates + cnot_gates + single_q_gates
        circuit_depth  = 40 * (n_bits ** 3)    # sequential model

        d = _code_distance(total_gates, self.target_logical_err, self.p_phys)
        physical_qubits = logical_qubits * (d ** 2) if d > 0 else None

        clock_cycle_ns = 1_000.0  # 1 μs per cycle (superconducting)
        if d > 0:
            total_cycles = circuit_depth * d
            runtime_s    = total_cycles * clock_cycle_ns * 1e-9
            runtime_days = runtime_s / 86_400.0
        else:
            runtime_days = float("inf")

        result = {
            "algorithm":          "Shor_RSA",
            "input_n_bits":       n_bits,
            "logical_qubits":     logical_qubits,
            "physical_qubits":    physical_qubits,
            "code_distance_d":    d if d > 0 else "N/A (below threshold)",
            "toffoli_gates":      toffoli_gates,
            "T_gates":            t_gates,
            "CNOT_gates":         cnot_gates,
            "total_gates":        total_gates,
            "circuit_depth":      circuit_depth,
            "runtime_days":       round(runtime_days, 2) if not math.isinf(runtime_days) else "inf",
            "p_phys":             self.p_phys,
            "target_logical_err": self.target_logical_err,
            "reference":          "Beauregard 2003; Fowler et al. 2012",
        }
        result["feasibility"] = self.feasibility_check(result)
        return result

    # ------------------------------------------------------------------
    # Grover's search
    # ------------------------------------------------------------------

    def estimate_grover_search(self, n_items: int) -> Dict[str, Any]:
        """
        Estimate resources for Grover's unstructured database search.

        Model:
          qubits        = ceil(log2(n_items)) + 1 (ancilla)
          oracle_calls  = ceil(π/4 × √n_items)
          gates_per_oracle ≈ 3 × qubits  (simplified diffusion + oracle)
          total_gates   = oracle_calls × gates_per_oracle
          circuit_depth = oracle_calls × (2 × qubits)
        """
        if n_items < 2:
            raise ValueError("n_items must be >= 2")

        n_qubits       = math.ceil(math.log2(n_items)) + 1
        oracle_calls   = math.ceil(math.pi / 4.0 * math.sqrt(n_items))
        gates_per_oracle = 3 * n_qubits
        total_gates    = oracle_calls * gates_per_oracle
        circuit_depth  = oracle_calls * (2 * n_qubits)
        speedup_over_classical = math.sqrt(n_items)   # quadratic speedup

        d = _code_distance(total_gates, self.target_logical_err, self.p_phys)
        physical_qubits = n_qubits * (d ** 2) if d > 0 else None

        clock_ns = 1_000.0
        if d > 0:
            runtime_s    = circuit_depth * d * clock_ns * 1e-9
            runtime_ms   = runtime_s * 1_000.0
        else:
            runtime_ms = float("inf")

        result = {
            "algorithm":                "Grover_Search",
            "n_items":                  n_items,
            "qubits_logical":           n_qubits,
            "physical_qubits":          physical_qubits,
            "code_distance_d":          d if d > 0 else "N/A",
            "oracle_calls":             oracle_calls,
            "total_gates":              total_gates,
            "circuit_depth":            circuit_depth,
            "classical_queries":        n_items,
            "speedup_over_classical":   round(speedup_over_classical, 2),
            "runtime_ms":               round(runtime_ms, 3) if not math.isinf(runtime_ms) else "inf",
            "reference":                "Grover 1996; Boyer et al. 1998",
        }
        result["feasibility"] = self.feasibility_check(result)
        return result

    # ------------------------------------------------------------------
    # VQE
    # ------------------------------------------------------------------

    def estimate_vqe(
        self,
        n_electrons: int,
        basis_size: int,
        optimizer_iters: int = 200,
        shots_per_call: int = 10_000,
    ) -> Dict[str, Any]:
        """
        Estimate resources for VQE with UCCSD ansatz.

        Model (Reiher et al. 2017; Babbush et al. 2018):
          qubits        = basis_size (spin orbitals)
          single excitations: n_electrons × (basis_size - n_electrons)
          double excitations: C(n_electrons,2) × C(basis_size-n_electrons,2)
          ansatz_layers = singles + doubles  (each layer = O(n_qubits) gates)
          gates_per_layer ≈ 4 × qubits  (CNOT ladder per excitation)
          total_2q_gates = ansatz_layers × qubits
          shots_needed  = shots_per_call × optimizer_iters × n_paulis
          n_paulis      ≈ O(n^4) Pauli terms; heuristic n_paulis = basis_size^2
        """
        if n_electrons > basis_size:
            raise ValueError("n_electrons cannot exceed basis_size")
        if basis_size < 2:
            raise ValueError("basis_size must be >= 2")

        n_qubits = basis_size
        virt = basis_size - n_electrons
        singles = n_electrons * virt
        doubles = math.comb(n_electrons, 2) * math.comb(virt, 2)
        ansatz_layers = singles + doubles

        gates_per_layer = max(4, 4 * n_qubits)
        total_2q_gates  = ansatz_layers * n_qubits  # CNOT count
        total_gates     = ansatz_layers * gates_per_layer
        circuit_depth   = ansatz_layers * n_qubits

        n_paulis_heuristic = basis_size ** 2   # rough O(n^4) / overhead
        shots_needed = shots_per_call * optimizer_iters * n_paulis_heuristic

        # Classical CPU for classical gradient computation (SciPy L-BFGS-B)
        params_count         = ansatz_layers
        classical_flops_iter = params_count ** 2
        cpu_iters_wall_s     = optimizer_iters * classical_flops_iter * 1e-9  # rough @ 1 GFlop

        d = _code_distance(total_gates, self.target_logical_err, self.p_phys)
        physical_qubits = n_qubits * (d ** 2) if d > 0 else None

        result = {
            "algorithm":              "VQE_UCCSD",
            "n_electrons":            n_electrons,
            "basis_size":             basis_size,
            "qubits_logical":         n_qubits,
            "physical_qubits":        physical_qubits,
            "code_distance_d":        d if d > 0 else "N/A",
            "single_excitations":     singles,
            "double_excitations":     doubles,
            "ansatz_layers":          ansatz_layers,
            "total_gates":            total_gates,
            "total_2q_gates":         total_2q_gates,
            "circuit_depth":          circuit_depth,
            "optimizer_iterations":   optimizer_iters,
            "shots_per_energy_call":  shots_per_call,
            "n_pauli_terms":          n_paulis_heuristic,
            "total_shots":            shots_needed,
            "classical_cpu_time_s":   round(cpu_iters_wall_s, 3),
            "reference":              "Reiher et al. 2017; Babbush et al. 2018",
        }
        result["feasibility"] = self.feasibility_check(result)
        return result

    # ------------------------------------------------------------------
    # QAOA
    # ------------------------------------------------------------------

    def estimate_qaoa(
        self,
        n_nodes: int,
        p_layers: int,
        graph_density: float = 0.5,
        shots_per_iter: int = 8_192,
        optimizer_iters: int = 100,
    ) -> Dict[str, Any]:
        """
        Estimate resources for QAOA on MaxCut.

        Model (Farhi et al. 2014; Zhou et al. 2020):
          qubits    = n_nodes
          n_edges   ≈ floor(density × n_nodes × (n_nodes-1) / 2)
          gates per layer = n_nodes (Rx phase) + 2 × n_edges (CNOT+Rz)
          total_gates = p_layers × gates_per_layer
          circuit_depth = p_layers × (1 + 2 × ceil(log2(n_nodes)))
                          (parallelized CNOT layers)
          shots_needed  = shots_per_iter × optimizer_iters
        """
        if n_nodes < 2:
            raise ValueError("n_nodes must be >= 2")
        if p_layers < 1:
            raise ValueError("p_layers must be >= 1")

        n_edges = int(math.floor(graph_density * n_nodes * (n_nodes - 1) / 2))
        n_edges = max(1, n_edges)

        gates_per_layer  = n_nodes + 2 * n_edges   # Rx + (CNOT, Rz) per edge
        total_gates      = p_layers * gates_per_layer
        two_qubit_gates  = p_layers * n_edges       # one CNOT per edge per layer

        # Circuit depth with parallelized CNOT layers
        cnot_depth_per_layer = max(1, math.ceil(math.log2(n_nodes + 1)))
        circuit_depth = p_layers * (1 + 2 * cnot_depth_per_layer)

        shots_needed = shots_per_iter * optimizer_iters

        d = _code_distance(total_gates, self.target_logical_err, self.p_phys)
        physical_qubits = n_nodes * (d ** 2) if d > 0 else None

        # Approximation ratio bound (Farhi p=1): ≥ 0.6924 for 3-regular graphs
        approx_ratio_lower = 0.6924 + 0.05 * min(p_layers, 6)  # heuristic improvement

        result = {
            "algorithm":            "QAOA_MaxCut",
            "n_nodes":              n_nodes,
            "p_layers":             p_layers,
            "graph_density":        graph_density,
            "n_edges":              n_edges,
            "qubits_logical":       n_nodes,
            "physical_qubits":      physical_qubits,
            "code_distance_d":      d if d > 0 else "N/A",
            "gates_per_layer":      gates_per_layer,
            "total_gates":          total_gates,
            "two_qubit_gates":      two_qubit_gates,
            "circuit_depth":        circuit_depth,
            "shots_per_iteration":  shots_per_iter,
            "optimizer_iterations": optimizer_iters,
            "total_shots":          shots_needed,
            "approx_ratio_lower_bound": round(min(1.0, approx_ratio_lower), 4),
            "reference":            "Farhi et al. 2014; Zhou et al. 2020",
        }
        result["feasibility"] = self.feasibility_check(result)
        return result

    # ------------------------------------------------------------------
    # QEC overhead
    # ------------------------------------------------------------------

    def estimate_qec_overhead(
        self,
        logical_qubits: int,
        target_error_rate: float = DEFAULT_TARGET_LOGICAL_ERR,
        n_gates_total: int = 1_000_000,
    ) -> Dict[str, Any]:
        """
        Estimate surface-code QEC overhead for a given number of logical qubits.

        Model (Fowler et al. 2012):
          code_distance d ← see _code_distance()
          physical_qubits = logical_qubits × d²
          ancilla_qubits  = logical_qubits × (d² - 1)  (syndrome qubits)
          syndrome_measurements_per_round = logical_qubits × (d² - 1)
          rounds_per_logical_gate = d
          total_syndrome_measurements = n_gates_total × d × logical_qubits × (d²-1)

        Magic state distillation (T-gate factory):
          factory_qubits = 15 × d²   (15-to-1 distillation protocol)
        """
        if logical_qubits < 1:
            raise ValueError("logical_qubits must be >= 1")
        if not (0 < target_error_rate < 1):
            raise ValueError("target_error_rate must be in (0, 1)")

        d = _code_distance(n_gates_total, target_error_rate, self.p_phys)
        if d < 0:
            return {
                "error": (
                    f"Physical error rate {self.p_phys} >= threshold "
                    f"{SURFACE_CODE_THRESHOLD}; QEC cannot help."
                )
            }

        data_qubits_per_logical     = d ** 2
        ancilla_qubits_per_logical  = d ** 2 - 1
        physical_qubits_total       = logical_qubits * (data_qubits_per_logical
                                                         + ancilla_qubits_per_logical)

        syndrome_meas_per_round     = logical_qubits * ancilla_qubits_per_logical
        rounds_per_logical_gate     = d
        total_syndrome_meas         = n_gates_total * rounds_per_logical_gate * syndrome_meas_per_round

        # T-gate magic state factory (15-to-1 protocol, Bravyi & Haah)
        t_factory_qubits            = 15 * (d ** 2)

        overhead_ratio              = physical_qubits_total / max(1, logical_qubits)

        result = {
            "algorithm":                      "QEC_SurfaceCode",
            "logical_qubits":                 logical_qubits,
            "code_distance_d":                d,
            "data_qubits_per_logical":        data_qubits_per_logical,
            "ancilla_qubits_per_logical":     ancilla_qubits_per_logical,
            "physical_qubits_total":          physical_qubits_total,
            "t_factory_qubits":               t_factory_qubits,
            "total_physical_incl_factory":    physical_qubits_total + t_factory_qubits,
            "overhead_ratio":                 round(overhead_ratio, 1),
            "syndrome_meas_per_round":        syndrome_meas_per_round,
            "rounds_per_logical_gate":        rounds_per_logical_gate,
            "total_syndrome_measurements":    total_syndrome_meas,
            "n_gates_assumed":                n_gates_total,
            "target_error_rate":              target_error_rate,
            "p_phys":                         self.p_phys,
            "reference":                      "Fowler et al. 2012; Bravyi & Haah 2012",
        }
        result["feasibility"] = self.feasibility_check(result)
        return result

    # ------------------------------------------------------------------
    # Feasibility classifier
    # ------------------------------------------------------------------

    def feasibility_check(self, estimate: Dict[str, Any]) -> str:
        """
        Classify a resource estimate into one of four hardware maturity tiers.

        Inputs (keys consumed from estimate dict)
        -----------------------------------------
        qubits_logical  OR  logical_qubits  OR  n_qubits_logical
        total_gates
        circuit_depth   (optional; only used for current_hardware gate)

        Returns
        -------
        "current_hardware"   : achievable on today's NISQ devices
        "near_term_2028"     : feasible with projected ~2028 hardware
        "fault_tolerant_only": requires large-scale FT QPU (post-2030)
        "theoretical_only"   : beyond any credibly projected hardware
        """
        qubits = (
            estimate.get("qubits_logical")
            or estimate.get("logical_qubits")
            or estimate.get("n_qubits_logical")
            or 0
        )
        total_gates   = estimate.get("total_gates", 0)
        circuit_depth = estimate.get("circuit_depth", 0)
        phys_qubits   = estimate.get("physical_qubits") or estimate.get("physical_qubits_total") or 0

        # Use physical qubit count if logical qubits are already large
        qubit_count = max(qubits, phys_qubits // 100 if phys_qubits else 0)

        if (qubit_count   <= CURRENT_HW_MAX_QUBITS
                and total_gates   <= CURRENT_HW_MAX_GATES
                and circuit_depth <= CURRENT_HW_MAX_DEPTH):
            return "current_hardware"

        if (qubit_count <= NEAR_TERM_MAX_QUBITS
                and total_gates <= NEAR_TERM_MAX_GATES
                and circuit_depth <= NEAR_TERM_MAX_DEPTH):
            return "near_term_2028"

        if (phys_qubits <= FAULT_TOL_MAX_PHYS_QUBITS
                and total_gates <= FAULT_TOL_MAX_GATES):
            return "fault_tolerant_only"

        return "theoretical_only"

    # ------------------------------------------------------------------
    # Batch / comparison helpers
    # ------------------------------------------------------------------

    def compare_algorithms(self, n_qubits: int = 20) -> Dict[str, Any]:
        """
        Run all estimators at a comparable problem size and return a
        side-by-side comparison table.
        """
        results: Dict[str, Any] = {}

        # Shor: n_bits = n_qubits // 2 to keep it representative
        n_bits = max(8, n_qubits // 2)
        try:
            results["shor_rsa"] = self.estimate_shor_rsa(n_bits)
        except Exception as e:
            results["shor_rsa"] = {"error": str(e)}

        # Grover: n_items = 2^n_qubits
        n_items = 2 ** n_qubits
        try:
            results["grover_search"] = self.estimate_grover_search(n_items)
        except Exception as e:
            results["grover_search"] = {"error": str(e)}

        # VQE: n_electrons = n_qubits // 4, basis_size = n_qubits
        n_elec = max(2, n_qubits // 4)
        try:
            results["vqe_uccsd"] = self.estimate_vqe(n_elec, n_qubits)
        except Exception as e:
            results["vqe_uccsd"] = {"error": str(e)}

        # QAOA: n_nodes = n_qubits, p=3
        try:
            results["qaoa_maxcut"] = self.estimate_qaoa(n_qubits, p_layers=3)
        except Exception as e:
            results["qaoa_maxcut"] = {"error": str(e)}

        # QEC overhead: n_qubits logical
        try:
            results["qec_overhead"] = self.estimate_qec_overhead(n_qubits)
        except Exception as e:
            results["qec_overhead"] = {"error": str(e)}

        # Summary table
        summary = []
        for alg, r in results.items():
            if "error" in r:
                continue
            summary.append({
                "algorithm":    alg,
                "qubits":       r.get("qubits_logical") or r.get("logical_qubits", "N/A"),
                "total_gates":  r.get("total_gates", "N/A"),
                "feasibility":  r.get("feasibility", "unknown"),
            })
        results["_summary"] = summary
        return results

    def cost_per_algorithm(
        self,
        n_qubits: int = 20,
        n_shots: int = 8_192,
    ) -> Dict[str, Any]:
        """
        Pair resource estimates with QPU cost estimates for a quick
        cost-vs-feasibility matrix.

        Returns a list of dicts: algorithm, qubits, gates, feasibility,
        estimated_shots, ibm_cost_usd, aws_cost_usd
        """
        from qpu_cost_model import QPUCostModeler, QPUJob

        modeler    = QPUCostModeler()
        comparison = self.compare_algorithms(n_qubits)
        rows: List[Dict[str, Any]] = []

        for alg, r in comparison.items():
            if alg.startswith("_") or "error" in r:
                continue
            qubits     = r.get("qubits_logical") or r.get("logical_qubits") or n_qubits
            gates      = int(r.get("total_gates", 1000))
            depth      = int(r.get("circuit_depth", 50))
            shots_est  = int(r.get("total_shots", n_shots))

            if qubits > 133 or depth > 5_000:
                ibm_usd  = float("inf")
                aws_usd  = float("inf")
            else:
                job = QPUJob(
                    circuit_depth=min(depth, 1000),
                    n_qubits=min(qubits, 133),
                    n_shots=min(shots_est, 100_000),
                    gate_count=min(gates, 10_000_000),
                    error_rate=self.p_phys,
                    algorithm_tag=alg,
                )
                ibm_est = modeler.estimate_ibm_quantum(job)
                aws_est = modeler.estimate_aws_braket(job)
                ibm_usd = ibm_est.cost_usd
                aws_usd = aws_est.cost_usd

            rows.append({
                "algorithm":       alg,
                "logical_qubits":  qubits,
                "total_gates":     gates,
                "circuit_depth":   depth,
                "shots":           shots_est,
                "feasibility":     r.get("feasibility", "unknown"),
                "ibm_cost_usd":    round(ibm_usd, 4) if not math.isinf(ibm_usd) else "infeasible",
                "aws_cost_usd":    round(aws_usd, 4) if not math.isinf(aws_usd) else "infeasible",
            })

        return {"n_qubits_param": n_qubits, "rows": rows}
