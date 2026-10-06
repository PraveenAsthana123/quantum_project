"""
Tests for QC Logistics Lab — validates result JSONs and core VRP solver.
Does NOT re-run the full benchmark scripts.
"""
import json
import sys
import pathlib

import pytest

# ── Path setup ─────────────────────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT / "src"))


# ── Result JSON tests ──────────────────────────────────────────────────────────

def test_vrp_classical_results_total_distance():
    """vrp_classical_results.json must have total_distance > 0."""
    with open(DATA / "vrp_classical_results.json") as f:
        d = json.load(f)
    assert "total_distance" in d, "Missing 'total_distance' key"
    assert d["total_distance"] > 0, (
        f"total_distance should be > 0, got {d['total_distance']}"
    )


def test_vrp_classical_results_num_routes():
    """vrp_classical_results.json must have at least 1 route (num_routes > 0)."""
    with open(DATA / "vrp_classical_results.json") as f:
        d = json.load(f)
    assert "routes" in d, "Missing 'routes' key"
    num_routes = len(d["routes"])
    assert num_routes > 0, f"Expected > 0 routes, got {num_routes}"


def test_vrp_benchmark_results_has_multiple_methods():
    """vrp_benchmark_results.json must have results for at least 2 methods."""
    with open(RESULTS / "vrp_benchmark_results.json") as f:
        d = json.load(f)
    assert "methods" in d, "Missing 'methods' key in benchmark results"
    methods = d["methods"]
    assert len(methods) >= 2, (
        f"Expected >= 2 methods in benchmark, got {len(methods)}: {list(methods)}"
    )


# ── Function-level test ────────────────────────────────────────────────────────

def test_nearest_neighbor_vrp_tiny_instance():
    """nearest_neighbor_vrp returns valid route for a tiny 3-city problem."""
    from vrp_classical import nearest_neighbor_vrp  # noqa: PLC0415

    # 3 cities: depot=0, city1=1, city2=2 in a triangle
    instance = {
        "coords": [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)],
        "demands": [0, 1, 1],
        "capacity": 10,
        "n_vehicles": 1,
        "depot": 0,
    }
    result = nearest_neighbor_vrp(instance)

    assert "routes" in result, "Result must have 'routes'"
    assert "total_distance" in result, "Result must have 'total_distance'"
    assert result["total_distance"] > 0, "total_distance must be > 0"

    # All routes must start and end at depot
    for route in result["routes"]:
        assert route[0] == 0, f"Route must start at depot (0), got {route[0]}"
        assert route[-1] == 0, f"Route must end at depot (0), got {route[-1]}"

    # All non-depot cities visited (no unserved)
    assert result.get("unserved", []) == [], (
        f"All cities should be served, unserved: {result.get('unserved')}"
    )
