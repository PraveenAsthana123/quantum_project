# QC Logistics Lab — User Stories

Version: 1.0.0 | Date: 2026-10-06 | Lab: qc-logistics-lab

---

## US-001: Fleet Route Optimisation

**As a** logistics manager
**I want** to run QAOA quantum optimisation on a 10-node VRP subset and compare the result against the classical nearest-neighbour solution
**so that** I can determine whether quantum routing reduces total fleet distance on representative problem sizes.

**Acceptance criteria:**
- QAOA completes on a 10-node TSP proxy (100 QUBO variables) within 5 minutes on the local PennyLane simulator.
- Classical and quantum total distance (or QUBO energy proxy) are reported in a comparison table.
- The improvement percentage (positive = quantum is better) is printed explicitly.
- Results are saved to `data/vrp_quantum_results.json`.

**Demo:**
1. Run `python src/demo.py` — observe Step 4 QAOA run and Step 5 comparison.

---

## US-002: Full Fleet Coverage Validation

**As a** fleet operator
**I want** the classical greedy router to verify that all customer demand nodes are served within vehicle capacity constraints
**so that** I can catch infeasible routing plans before drivers are dispatched.

**Acceptance criteria:**
- `demo.py` Step 6 prints the number of unserved nodes (target: 0).
- If any nodes are unserved, the gate prints FAIL and lists the unserved node IDs.
- Served nodes, total distance, and number of routes are printed for each vehicle.
- The gate exits with code 1 on FAIL (future enhancement).

**Demo:**
1. Run `python src/demo.py` — observe "OVERALL: PASS — all customer demand nodes are served" in Step 6.

---

## US-003: VRP Dataset Generation

**As a** supply chain analyst
**I want** to generate a reproducible 50-node VRP instance and a 500-row supply chain shipment log
**so that** I can benchmark routing algorithms and supply chain KPIs without access to confidential fleet data.

**Acceptance criteria:**
- `vrp_nodes.csv` has columns: id, x, y, demand, time_window_open, time_window_close, service_time, is_depot.
- Depot node (id=0) has demand=0 and is flagged `is_depot=True`.
- `vrp_config.json` records n_vehicles, vehicle_capacity, speed_kmh, max_route_time_min, total_demand.
- `supply_chain.csv` has 500 rows with on-time rate printed to console.
- Re-running with seed=42 produces byte-identical files.

**Demo:**
1. Run `python src/generate_data.py`.
2. Confirm `data/vrp_nodes.csv` has 50 rows; `data/vrp_config.json` contains `n_vehicles: 5`.

---

## US-004: Supply Chain KPI Dashboard

**As a** supply chain analyst
**I want** to view on-time delivery rate, average cost, and average distance for a shipment log
**so that** I can track supply chain performance trends and identify underperforming lanes.

**Acceptance criteria:**
- `demo.py` Step 5 prints on-time rate, average cost, and the most-frequent origin-destination pair.
- The supply chain CSV is loaded automatically if present; the step is skipped gracefully if the file is missing.
- All KPIs are rounded to 2 decimal places.
- A per-lane breakdown (group by origin-destination) is available as a future enhancement (documented as backlog).

**Demo:**
1. Run `python src/demo.py` — Step 5 prints supply chain summary.

---

## US-005: Problem Statistics Summary

**As a** logistics manager
**I want** a problem statistics report (total demand, vehicle utilisation, avg inter-node distance) before routing begins
**so that** I can quickly assess whether the fleet is adequately sized for the current demand.

**Acceptance criteria:**
- `demo.py` Step 2 prints: total nodes, customer count, total demand, average demand per node, vehicle capacity × count, minimum vehicles needed, average and maximum inter-node distance.
- Minimum vehicles needed is computed as `ceil(total_demand / vehicle_capacity)`.
- If minimum vehicles needed > configured vehicle count, a warning is printed.
- All values are printed in a single block for easy copying into a planning report.

**Demo:**
1. Run `python src/demo.py` — Step 2 output appears before any routing begins.

---

## US-006: QUBO Formulation Review

**As a** supply chain analyst
**I want** to inspect the QUBO matrix dimensions and penalty parameters used for the quantum TSP formulation
**so that** I can tune the penalty-to-objective balance and assess circuit qubit requirements.

**Acceptance criteria:**
- `vrp_quantum.py` exports `tsp_qubo(n, dist_matrix, penalty)` returning the Q matrix.
- `demo.py` Step 4 prints n_cities, n_qubits (= n_cities²), and circuit depth (= 2×n_layers + 1).
- The penalty parameter is documented in `tsp_qubo` docstring with guidance on typical values.
- Increasing `n_cities` beyond 4 prints a "QAOA-skipped: n_qubits > 16" message rather than hanging.

**Demo:**
1. Run `python src/demo.py` — Step 4 prints QUBO / circuit metadata.
2. Open `src/vrp_quantum.py` — review `qaoa_tsp` guard at n_qubits > 16.

---

## US-007: Simulated Annealing Baseline

**As a** logistics manager
**I want** simulated annealing to serve as an intermediate baseline between greedy and QAOA
**so that** I can evaluate whether QAOA improves on SA before committing to quantum hardware costs.

**Acceptance criteria:**
- `vrp_quantum.py` exports `simulated_annealing(Q, num_reads)` supporting both D-Wave dimod and a pure-numpy fallback.
- SA result includes energy, elapsed time, and the backend used (dimod-SA or numpy-SA).
- SA is run in `vrp_quantum.py main()` and its result is saved to `data/vrp_quantum_results.json`.
- The numpy fallback runs in under 10 s for the 4-city problem.

**Demo:**
1. Run `python src/vrp_quantum.py` — observe SA result with backend label.
2. Check `data/vrp_quantum_results.json` key `simulated_annealing.backend`.

---

## US-008: Time-Window Constraint Awareness

**As a** fleet operator
**I want** routes to respect customer time windows (earliest open, latest close) so that deliveries arrive within agreed service windows
**so that** I can meet contractual SLA commitments and reduce customer complaints.

**Acceptance criteria:**
- `vrp_nodes.csv` includes `time_window_open` and `time_window_close` per node.
- Classical greedy router (current implementation) prints a note acknowledging time-window constraints are not yet enforced.
- A time-window-aware OR-Tools extension is documented as a backlog item in the demo output.
- `vrp_config.json` records `max_route_time_min` as the per-vehicle shift limit.

**Demo:**
1. Run `python src/demo.py` — Step 3 classical routing output notes time-window constraint status.
2. Open `data/vrp_nodes.csv` — confirm `time_window_open` and `time_window_close` columns are present.
