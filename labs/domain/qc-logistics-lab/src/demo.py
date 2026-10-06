"""
Logistics Lab End-to-End Demo
================================
Demonstrates the full quantum vs classical VRP / supply-chain pipeline:

    Step 1 – Load VRP nodes + vehicle config (generate if absent)
    Step 2 – Problem statistics: nodes, total demand, avg inter-node distance
    Step 3 – Classical greedy routing (nearest-neighbour), total distance + routes
    Step 4 – QAOA quantum optimisation (subset of 10 nodes), quantum distance
    Step 5 – Comparison: classical vs quantum improvement %
    Step 6 – PASS / FAIL gate (all demand nodes covered)

Run:
    python src/demo.py

The script is self-contained: if vrp_nodes.csv is absent it calls
generate_data.generate() to produce it first.

Version: 1.0.0
Date: 2026-10-06
"""
from __future__ import annotations

import importlib.util
import json
import math
import time
import warnings
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SRC_DIR = Path(__file__).parent
LAB_DIR = SRC_DIR.parent
DATA_DIR = LAB_DIR / "data"
VRP_NODES_CSV = DATA_DIR / "vrp_nodes.csv"
VRP_CONFIG_JSON = DATA_DIR / "vrp_config.json"
SUPPLY_CHAIN_CSV = DATA_DIR / "supply_chain.csv"

DIVIDER = "=" * 72


def _header(step: int, title: str) -> None:
    print(f"\n{DIVIDER}")
    print(f"  Step {step}: {title}")
    print(DIVIDER)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _euclidean(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x1 - x2, y1 - y2)


def _distance_matrix(nodes_df: pd.DataFrame) -> np.ndarray:
    """Full n×n Euclidean distance matrix from node coordinates."""
    x = nodes_df["x"].values
    y = nodes_df["y"].values
    n = len(x)
    dm = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            dm[i, j] = math.hypot(x[i] - x[j], y[i] - y[j])
    return dm


# ---------------------------------------------------------------------------
# Step 1: Data loading
# ---------------------------------------------------------------------------

def step1_load() -> tuple[pd.DataFrame, dict, pd.DataFrame | None]:
    _header(1, "Data Loading / Generation")

    if not VRP_NODES_CSV.exists():
        print("  vrp_nodes.csv not found — generating data...")
        spec = importlib.util.spec_from_file_location("generate_data", SRC_DIR / "generate_data.py")
        gen_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen_mod)
        gen_mod.generate()

    t0 = time.perf_counter()
    nodes_df = pd.read_csv(VRP_NODES_CSV)
    with open(VRP_CONFIG_JSON) as fh:
        config = json.load(fh)
    load_ms = (time.perf_counter() - t0) * 1000
    print(f"  Loaded nodes   : {VRP_NODES_CSV.name}  ({load_ms:.1f} ms)")
    print(f"  Nodes          : {len(nodes_df)} ({config['n_customers']} customers + 1 depot)")
    print(f"  Vehicles       : {config['n_vehicles']}  capacity={config['vehicle_capacity']} units")

    sc_df = None
    if SUPPLY_CHAIN_CSV.exists():
        sc_df = pd.read_csv(SUPPLY_CHAIN_CSV)
        print(f"  Supply chain   : {len(sc_df):,} shipments loaded")

    return nodes_df, config, sc_df


# ---------------------------------------------------------------------------
# Step 2: Problem statistics
# ---------------------------------------------------------------------------

def step2_stats(nodes_df: pd.DataFrame, config: dict) -> np.ndarray:
    _header(2, "Problem Statistics")

    dm = _distance_matrix(nodes_df)

    # Average inter-node distance (excluding diagonal, depot-to-depot)
    n = len(nodes_df)
    off_diag = dm[np.triu_indices(n, k=1)]
    avg_dist = float(off_diag.mean())
    max_dist = float(off_diag.max())

    customers = nodes_df[~nodes_df["is_depot"]]
    total_demand = int(customers["demand"].sum())
    avg_demand = float(customers["demand"].mean())
    min_vehicles = math.ceil(total_demand / config["vehicle_capacity"])

    print(f"  Total nodes          : {n}")
    print(f"  Customer nodes       : {len(customers)}")
    print(f"  Total demand         : {total_demand} units")
    print(f"  Average demand/node  : {avg_demand:.1f} units")
    print(f"  Vehicle capacity     : {config['vehicle_capacity']} units × {config['n_vehicles']}")
    print(f"  Min vehicles needed  : {min_vehicles}")
    print(f"  Avg inter-node dist  : {avg_dist:.2f} units")
    print(f"  Max inter-node dist  : {max_dist:.2f} units")

    return dm


# ---------------------------------------------------------------------------
# Step 3: Classical greedy routing
# ---------------------------------------------------------------------------

def _nearest_neighbor_route(
    dm: np.ndarray,
    demands: np.ndarray,
    capacity: int,
    n_vehicles: int,
    depot: int = 0,
) -> dict[str, Any]:
    """
    Nearest-neighbour greedy VRP heuristic.
    Assigns customers to vehicles greedily; restarts from depot when capacity
    would be exceeded.  Returns routes, per-route distances, and total distance.
    """
    n = len(demands)
    unvisited = set(range(n)) - {depot}
    routes: list[list[int]] = []
    distances: list[float] = []
    total_dist = 0.0

    while unvisited and len(routes) < n_vehicles:
        route = [depot]
        route_load = 0
        route_dist = 0.0
        current = depot

        while unvisited:
            # Find nearest feasible neighbour
            best_node = -1
            best_dist = float("inf")
            for node in unvisited:
                if route_load + demands[node] <= capacity:
                    d = dm[current, node]
                    if d < best_dist:
                        best_dist = d
                        best_node = node
            if best_node == -1:
                break   # no feasible neighbour — close route
            route.append(best_node)
            route_dist += best_dist
            route_load += demands[best_node]
            unvisited.remove(best_node)
            current = best_node

        # Return to depot
        route_dist += dm[current, depot]
        route.append(depot)
        routes.append(route)
        distances.append(route_dist)
        total_dist += route_dist

    return {
        "routes": routes,
        "route_distances": [round(d, 2) for d in distances],
        "total_distance": round(total_dist, 2),
        "n_routes": len(routes),
        "unserved": list(unvisited),
    }


def step3_classical(
    nodes_df: pd.DataFrame,
    config: dict,
    dm: np.ndarray,
) -> dict[str, Any]:
    _header(3, "Classical Greedy Routing — Nearest-Neighbour")

    demands = nodes_df["demand"].values.astype(int)
    capacity = config["vehicle_capacity"]
    n_vehicles = config["n_vehicles"]

    t0 = time.perf_counter()
    solution = _nearest_neighbor_route(dm, demands, capacity, n_vehicles)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    solution["elapsed_ms"] = round(elapsed_ms, 2)

    print(f"  Total distance  : {solution['total_distance']:.2f} units")
    print(f"  Routes          : {solution['n_routes']}")
    print(f"  Unserved nodes  : {len(solution['unserved'])}")
    print(f"  Time            : {elapsed_ms:.2f} ms")
    print()

    for i, (route, dist) in enumerate(zip(solution["routes"], solution["route_distances"])):
        load = sum(demands[n] for n in route if n != 0)
        nodes_str = " → ".join(str(n) for n in route)
        print(f"  Route {i+1}: [{nodes_str}]  dist={dist:.2f}  load={load}/{capacity}")

    return solution


# ---------------------------------------------------------------------------
# Step 4: QAOA quantum optimisation (10-node subset)
# ---------------------------------------------------------------------------

def step4_quantum(
    nodes_df: pd.DataFrame,
    dm: np.ndarray,
) -> dict[str, Any]:
    _header(4, "Quantum QAOA Optimisation (10-node subset TSP proxy)")

    # Sub-sample 10 nodes (depot + 9 customers) for tractable circuit
    SUBSET_SIZE = 10
    depot_row = nodes_df[nodes_df["is_depot"]].index[0]
    customer_idx = nodes_df[~nodes_df["is_depot"]].index[:SUBSET_SIZE - 1].tolist()
    subset_idx = [depot_row] + customer_idx

    dm_sub = dm[np.ix_(subset_idx, subset_idx)]
    n_cities = len(subset_idx)

    print(f"  Subset size     : {n_cities} nodes (depot + {n_cities-1} customers)")

    try:
        spec = importlib.util.spec_from_file_location("vrp_quantum", SRC_DIR / "vrp_quantum.py")
        qv = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(qv)

        t0 = time.perf_counter()
        Q = qv.tsp_qubo(n_cities, dm_sub, penalty=50.0)
        qa_result = qv.qaoa_tsp(n_cities, Q, n_layers=1)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        if "error" in qa_result or "reason" in qa_result:
            print(f"  QAOA status     : {qa_result.get('error', qa_result.get('reason', 'skipped'))}")
            print(f"  Time            : {elapsed_ms:.2f} ms")
            return {"method": "QAOA", "elapsed_ms": round(elapsed_ms, 2), "status": "skipped", "total_distance": None}

        best_energy = qa_result.get("best_energy", None)
        print(f"  QAOA best energy: {best_energy:.2f}")
        print(f"  Qubits          : {qa_result.get('n_qubits', '?')}")
        print(f"  Layers          : {qa_result.get('n_layers', '?')}")
        print(f"  Time            : {elapsed_ms:.2f} ms")

        # Use best energy as proxy for tour cost; convert from QUBO energy to distance estimate
        # (positive energy contribution from distance terms)
        loss_hist = qa_result.get("loss_history", [])
        if loss_hist:
            print(f"  Loss: initial={loss_hist[0]:.2f}  final={loss_hist[-1]:.2f}")

        # Estimate a route distance from the sampled state
        # The QAOA energy includes penalty + distance; rough extraction:
        dm_sub_total = dm_sub.sum()
        estimated_dist = max(0.0, best_energy) if best_energy else dm_sub_total

        return {
            "method": "QAOA",
            "n_cities_subset": n_cities,
            "n_qubits": qa_result.get("n_qubits"),
            "best_energy": best_energy,
            "estimated_distance": round(estimated_dist, 2),
            "elapsed_ms": round(elapsed_ms, 2),
            "status": "completed",
        }

    except Exception as exc:
        print(f"  Quantum step failed: {exc}")
        return {"method": "QAOA", "elapsed_ms": 0.0, "status": f"error: {exc}", "total_distance": None}


# ---------------------------------------------------------------------------
# Step 5: Comparison
# ---------------------------------------------------------------------------

def step5_comparison(
    classical: dict[str, Any],
    quantum: dict[str, Any],
    nodes_df: pd.DataFrame,
    config: dict,
    sc_df: pd.DataFrame | None,
) -> None:
    _header(5, "Classical vs Quantum Comparison")

    c_dist = classical["total_distance"]
    q_dist = quantum.get("estimated_distance")

    print(f"  {'Metric':<30} {'Classical':>12} {'Quantum':>12}")
    print("  " + "-" * 56)
    print(f"  {'Total distance (units)':<30} {c_dist:>12.2f} {'(subset only)':>12}")
    print(f"  {'Time (ms)':<30} {classical['elapsed_ms']:>12.2f} {quantum['elapsed_ms']:>12.2f}")
    print(f"  {'Algorithm':<30} {'Nearest-Nbr':>12} {'QAOA':>12}")

    if q_dist is not None and c_dist > 0:
        n_subset = quantum.get("n_cities_subset", 10)
        # Compare classical on same subset
        demands = nodes_df["demand"].values.astype(int)
        subset_idx = nodes_df[nodes_df["is_depot"]].index.tolist()[:1]
        cust_idx = nodes_df[~nodes_df["is_depot"]].index[: n_subset - 1].tolist()
        sub_all_idx = subset_idx + cust_idx

        from numpy import ix_
        dm_all = _distance_matrix(nodes_df)
        dm_sub2 = dm_all[ix_(sub_all_idx, sub_all_idx)]
        demands_sub = demands[sub_all_idx]
        classical_sub = _nearest_neighbor_route(
            dm_sub2, demands_sub, config["vehicle_capacity"], config["n_vehicles"]
        )
        c_sub_dist = classical_sub["total_distance"]
        improvement = (c_sub_dist - q_dist) / max(c_sub_dist, 1e-6) * 100
        print(f"\n  Classical on same {n_subset}-node subset : {c_sub_dist:.2f} units")
        print(f"  QAOA estimated distance            : {q_dist:.2f} units")
        print(f"  Improvement                        : {improvement:+.1f}%")

    if sc_df is not None:
        print(f"\n  Supply chain summary ({len(sc_df):,} shipments):")
        print(f"    On-time rate : {sc_df['on_time'].mean():.1%}")
        print(f"    Avg cost     : ${sc_df['cost_usd'].mean():.2f}")
        print(f"    Top route    : {sc_df.groupby(['origin','destination']).size().idxmax()}")


# ---------------------------------------------------------------------------
# Step 6: PASS / FAIL gate
# ---------------------------------------------------------------------------

def step6_gate(classical: dict[str, Any]) -> None:
    _header(6, "PASS / FAIL Gate — All Demand Nodes Covered")

    unserved = classical.get("unserved", [])
    n_routes = classical.get("n_routes", 0)
    total_dist = classical.get("total_distance", 0.0)

    if len(unserved) == 0:
        status = "PASS"
        indicator = "✓"
    else:
        status = "FAIL"
        indicator = "✗"

    print(f"  {indicator} Unserved nodes    : {len(unserved)}")
    print(f"  {indicator} Routes completed  : {n_routes}")
    print(f"    Total distance  : {total_dist:.2f} units")
    print()

    if status == "PASS":
        print("  OVERALL: PASS — all customer demand nodes are served")
    else:
        print(f"  OVERALL: FAIL — {len(unserved)} nodes unserved: {unserved}")
        print("  Tip: increase vehicle count or capacity in vrp_config.json")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    wall_start = time.perf_counter()
    print(f"\n{'#' * 72}")
    print("  QC Logistics Lab — End-to-End VRP Optimisation Demo")
    print(f"{'#' * 72}")

    nodes_df, config, sc_df = step1_load()
    dm = step2_stats(nodes_df, config)
    classical_sol = step3_classical(nodes_df, config, dm)
    quantum_sol = step4_quantum(nodes_df, dm)
    step5_comparison(classical_sol, quantum_sol, nodes_df, config, sc_df)
    step6_gate(classical_sol)

    wall_ms = (time.perf_counter() - wall_start) * 1000
    print(f"\n{DIVIDER}")
    print(f"  Total wall time: {wall_ms / 1000:.1f} s")
    print(f"{DIVIDER}\n")


if __name__ == "__main__":
    main()
