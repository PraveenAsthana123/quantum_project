"""
Classical Vehicle Routing Problem solver.
Uses nearest-neighbor greedy heuristic with OR-Tools fallback.
Generates random VRP instances if no external data is provided.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA_DIR = Path(__file__).parent.parent / "data"
RESULTS_FILE = DATA_DIR / "vrp_classical_results.json"


# ---------------------------------------------------------------------------
# Instance generation
# ---------------------------------------------------------------------------

def generate_vrp(n_cities: int = 12, n_vehicles: int = 3, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    coords = rng.uniform(0, 100, (n_cities, 2))
    demands = np.concatenate([[0], rng.integers(5, 20, n_cities - 1)])  # depot demand = 0
    capacity = int(demands[1:].sum() / n_vehicles * 1.3)
    return {"coords": coords.tolist(), "demands": demands.tolist(), "capacity": capacity,
            "n_vehicles": n_vehicles, "depot": 0}


def _dist(a: list[float], b: list[float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _distance_matrix(coords: list[list[float]]) -> list[list[float]]:
    n = len(coords)
    return [[_dist(coords[i], coords[j]) for j in range(n)] for i in range(n)]


# ---------------------------------------------------------------------------
# Nearest-neighbour greedy solver
# ---------------------------------------------------------------------------

def nearest_neighbor_vrp(instance: dict) -> dict:
    coords = instance["coords"]
    demands = instance["demands"]
    capacity = instance["capacity"]
    n_vehicles = instance["n_vehicles"]
    depot = instance["depot"]
    n = len(coords)
    dm = _distance_matrix(coords)

    unvisited = set(range(n)) - {depot}
    routes: list[list[int]] = []
    total_dist = 0.0

    for _ in range(n_vehicles):
        if not unvisited:
            break
        route = [depot]
        load = 0
        current = depot
        route_dist = 0.0
        while unvisited:
            # nearest feasible node
            cands = [(dm[current][j], j) for j in unvisited if load + demands[j] <= capacity]
            if not cands:
                break
            cands.sort()
            _, nxt = cands[0]
            route_dist += dm[current][nxt]
            route.append(nxt)
            load += demands[nxt]
            unvisited.remove(nxt)
            current = nxt
        route_dist += dm[current][depot]
        route.append(depot)
        routes.append(route)
        total_dist += route_dist

    return {"routes": routes, "total_distance": round(total_dist, 2), "unserved": list(unvisited)}


# ---------------------------------------------------------------------------
# OR-Tools solver (optional)
# ---------------------------------------------------------------------------

def ortools_vrp(instance: dict) -> dict:
    try:
        from ortools.constraint_solver import routing_enums_pb2, pywrapcp
    except ImportError:
        print("OR-Tools not installed (pip install ortools) — using greedy fallback")
        return nearest_neighbor_vrp(instance)

    coords = instance["coords"]
    demands = instance["demands"]
    capacity = instance["capacity"]
    n_vehicles = instance["n_vehicles"]
    depot = instance["depot"]
    n = len(coords)
    dm_int = [[int(_dist(coords[i], coords[j]) * 10) for j in range(n)] for i in range(n)]

    manager = pywrapcp.RoutingIndexManager(n, n_vehicles, depot)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        return dm_int[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit_cb = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_cb)

    def demand_callback(from_index):
        return int(demands[manager.IndexToNode(from_index)])

    demand_cb = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(demand_cb, 0, [capacity] * n_vehicles, True, "Capacity")

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.time_limit.FromSeconds(10)

    solution = routing.SolveWithParameters(params)
    if not solution:
        return nearest_neighbor_vrp(instance)

    routes = []
    total_dist = 0.0
    for v in range(n_vehicles):
        index = routing.Start(v)
        route = []
        while not routing.IsEnd(index):
            route.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))
        route.append(depot)
        routes.append(route)
        total_dist += solution.ObjectiveValue() / n_vehicles / 10  # rough per-vehicle

    return {"routes": routes, "total_distance": round(solution.ObjectiveValue() / 10, 2), "unserved": []}


# ---------------------------------------------------------------------------
# Visualisation
# ---------------------------------------------------------------------------

def plot_routes(instance: dict, solution: dict, path: Path):
    coords = np.array(instance["coords"])
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = plt.cm.tab10.colors  # type: ignore
    for idx, route in enumerate(solution["routes"]):
        c = colors[idx % len(colors)]
        xs = [coords[n][0] for n in route]
        ys = [coords[n][1] for n in route]
        ax.plot(xs, ys, "-o", color=c, label=f"Vehicle {idx+1}", linewidth=1.5, markersize=5)
    ax.plot(*coords[instance["depot"]], "k*", markersize=15, label="Depot")
    for i, (x, y) in enumerate(coords):
        ax.annotate(str(i), (x, y), textcoords="offset points", xytext=(4, 4), fontsize=7)
    ax.set_title(f"VRP Solution — {len(solution['routes'])} routes, dist={solution['total_distance']:.1f}")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=100)
    plt.close()
    print(f"Route plot saved → {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(n_cities: int = 15, n_vehicles: int = 3, use_ortools: bool = True) -> dict:
    instance = generate_vrp(n_cities=n_cities, n_vehicles=n_vehicles)

    solver_name = "OR-Tools" if use_ortools else "Nearest-Neighbour"
    print(f"\nSolving VRP ({n_cities} cities, {n_vehicles} vehicles) with {solver_name}...")

    t0 = time.perf_counter()
    solution = ortools_vrp(instance) if use_ortools else nearest_neighbor_vrp(instance)
    elapsed = time.perf_counter() - t0

    print(f"  Total distance: {solution['total_distance']:.2f}")
    print(f"  Elapsed: {elapsed:.3f}s")
    for i, r in enumerate(solution["routes"]):
        print(f"  Vehicle {i+1}: {' → '.join(map(str, r))}")

    result: dict[str, Any] = {
        "solver": solver_name, "n_cities": n_cities, "n_vehicles": n_vehicles,
        "total_distance": solution["total_distance"], "elapsed_s": round(elapsed, 4),
        "routes": solution["routes"],
        "instance": {"coords": instance["coords"], "demands": instance["demands"],
                     "capacity": instance["capacity"]},
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Results saved → {RESULTS_FILE}")

    plot_routes(instance, solution, DATA_DIR / "vrp_classical_routes.png")
    return result


if __name__ == "__main__":
    main()
