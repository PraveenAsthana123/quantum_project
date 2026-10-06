"""
Logistics Lab Synthetic Data Generator
=======================================
Generates two complementary datasets for the VRP / supply-chain modules:

1. VRP instance (50 nodes: 1 depot + 49 customers)
   ─────────────────────────────────────────────────
   Nodes CSV  : qc-logistics-lab/data/vrp_nodes.csv
   Config JSON: qc-logistics-lab/data/vrp_config.json

   Node columns:
       id              – integer node index (0 = depot)
       x, y            – Cartesian coordinates (0–100)
       demand          – load demand (5–50 units; depot = 0)
       time_window_open   – earliest service start (minutes, 0–480)
       time_window_close  – latest service finish (minutes, 60–600)
       service_time       – on-site service duration (minutes, 10–30)
       is_depot        – boolean flag

   Vehicle config keys:
       n_vehicles, capacity, speed_kmh, max_route_time_min

2. Supply chain shipment log (500 rows)
   ─────────────────────────────────────
   File: qc-logistics-lab/data/supply_chain.csv

   Columns:
       date           – ISO date (2024-01-01 .. 2024-06-29)
       origin         – city name (from a 10-city pool)
       destination    – city name (different from origin)
       distance_km    – Euclidean proxy (50–4500 km)
       weight_kg      – shipment weight (10–5000 kg)
       cost_usd       – freight cost (function of distance × weight + noise)
       delivery_days  – integer 1–14
       on_time        – bool (missed if delivery_days > SLA)

Usage:
    python src/generate_data.py

Version: 1.0.0
Date: 2026-10-06
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data"
VRP_NODES_FILE = DATA_DIR / "vrp_nodes.csv"
VRP_CONFIG_FILE = DATA_DIR / "vrp_config.json"
SUPPLY_CHAIN_FILE = DATA_DIR / "supply_chain.csv"

# ---------------------------------------------------------------------------
# VRP parameters
# ---------------------------------------------------------------------------

N_NODES = 50          # 1 depot + 49 customers
N_VEHICLES = 8        # enough for avg demand 27.8 × 49 = 1362 total / 200 cap = 6.8 → 8
VEHICLE_CAPACITY = 200
VEHICLE_SPEED_KMH = 50.0
MAX_ROUTE_TIME_MIN = 480   # 8-hour shift
SEED = 42

# ---------------------------------------------------------------------------
# Supply chain city pool (with approximate coordinates for distance proxy)
# ---------------------------------------------------------------------------

CITIES: dict[str, tuple[float, float]] = {
    "New York":     (74.0,   40.7),
    "Los Angeles":  (118.2,  34.1),
    "Chicago":      (87.6,   41.9),
    "Houston":      (95.4,   29.7),
    "Phoenix":      (112.1,  33.4),
    "Philadelphia": (75.2,   40.0),
    "San Antonio":  (98.5,   29.4),
    "San Diego":    (117.2,  32.7),
    "Dallas":       (96.8,   32.8),
    "San Jose":     (121.9,  37.3),
}


# ---------------------------------------------------------------------------
# VRP generator
# ---------------------------------------------------------------------------

def _generate_vrp(rng: np.random.Generator) -> tuple[pd.DataFrame, dict]:
    """Generate VRP nodes and vehicle configuration."""

    ids = list(range(N_NODES))
    x_coords = rng.uniform(0.0, 100.0, N_NODES)
    y_coords = rng.uniform(0.0, 100.0, N_NODES)

    # Place depot at centroid-ish position for realistic routing
    x_coords[0] = 50.0
    y_coords[0] = 50.0

    demands = np.zeros(N_NODES)
    demands[1:] = rng.integers(5, 51, N_NODES - 1)   # depot demand = 0

    # Time windows: depot open all day; customers have 2-hour windows
    tw_open = np.zeros(N_NODES)
    tw_close = np.full(N_NODES, MAX_ROUTE_TIME_MIN)

    tw_open[1:] = rng.integers(0, 481, N_NODES - 1)
    window_widths = rng.integers(60, 181, N_NODES - 1)   # 1–3 hour windows
    tw_close[1:] = np.minimum(tw_open[1:] + window_widths, 600)

    service_times = np.zeros(N_NODES)
    service_times[1:] = rng.integers(10, 31, N_NODES - 1)

    is_depot = np.zeros(N_NODES, dtype=bool)
    is_depot[0] = True

    nodes_df = pd.DataFrame({
        "id": ids,
        "x": np.round(x_coords, 4),
        "y": np.round(y_coords, 4),
        "demand": demands.astype(int),
        "time_window_open": tw_open.astype(int),
        "time_window_close": tw_close.astype(int),
        "service_time": service_times.astype(int),
        "is_depot": is_depot,
    })

    config = {
        "n_nodes": N_NODES,
        "n_customers": N_NODES - 1,
        "depot_id": 0,
        "n_vehicles": N_VEHICLES,
        "vehicle_capacity": VEHICLE_CAPACITY,
        "speed_kmh": VEHICLE_SPEED_KMH,
        "max_route_time_min": MAX_ROUTE_TIME_MIN,
        "total_demand": int(demands.sum()),
        "avg_customer_demand": float(demands[1:].mean()),
        "seed": SEED,
    }
    return nodes_df, config


# ---------------------------------------------------------------------------
# Supply chain generator
# ---------------------------------------------------------------------------

def _generate_supply_chain(rng: np.random.Generator, n: int = 500) -> pd.DataFrame:
    """Generate synthetic supply chain shipment log."""

    city_names = list(CITIES.keys())
    city_coords = np.array(list(CITIES.values()))

    # Random date range: 2024-01-01 to 2024-06-29 (181 days)
    base_date = np.datetime64("2024-01-01")
    day_offsets = rng.integers(0, 181, n)
    dates = [str(base_date + np.timedelta64(int(d), "D")) for d in day_offsets]

    # Origin and destination (ensure different cities)
    origin_idx = rng.integers(0, len(city_names), n)
    dest_idx = rng.integers(0, len(city_names), n)
    # Resample where origin == destination
    same_mask = origin_idx == dest_idx
    while same_mask.any():
        dest_idx[same_mask] = rng.integers(0, len(city_names), same_mask.sum())
        same_mask = origin_idx == dest_idx

    origins = [city_names[i] for i in origin_idx]
    destinations = [city_names[i] for i in dest_idx]

    # Euclidean distance proxy (degree-scaled to rough km)
    o_coords = city_coords[origin_idx]
    d_coords = city_coords[dest_idx]
    raw_dist = np.sqrt(np.sum((o_coords - d_coords) ** 2, axis=1))
    # Scale: 1 degree ≈ 111 km
    distance_km = np.round(np.clip(raw_dist * 111.0, 50.0, 4500.0), 1)

    weight_kg = np.round(rng.uniform(10.0, 5000.0, n), 1)

    # Cost model: 0.002 USD/(kg·km) + random carrier variation + fixed fees
    base_cost = 0.002 * weight_kg * distance_km
    noise_factor = rng.uniform(0.80, 1.25, n)
    fixed_fee = rng.uniform(20.0, 150.0, n)
    cost_usd = np.round(base_cost * noise_factor + fixed_fee, 2)

    # Delivery days: function of distance (longer distance → more days)
    # SLA: ≤ 7 days for domestic (< 2000 km), ≤ 10 days for cross-country
    expected_days = np.round(1 + distance_km / 800.0).astype(int)
    delivery_variation = rng.integers(-1, 3, n)
    delivery_days = np.clip(expected_days + delivery_variation, 1, 14)

    sla_days = np.where(distance_km < 2000, 7, 10)
    on_time = delivery_days <= sla_days

    df = pd.DataFrame({
        "date": dates,
        "origin": origins,
        "destination": destinations,
        "distance_km": distance_km,
        "weight_kg": weight_kg,
        "cost_usd": cost_usd,
        "delivery_days": delivery_days,
        "on_time": on_time,
    })

    # Sort by date for time-series readability
    df = df.sort_values("date").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate(
    vrp_nodes_path: Path = VRP_NODES_FILE,
    vrp_config_path: Path = VRP_CONFIG_FILE,
    supply_chain_path: Path = SUPPLY_CHAIN_FILE,
    seed: int = SEED,
) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """Generate both VRP and supply chain datasets."""
    t_start = time.perf_counter()
    rng = np.random.default_rng(seed)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # --- VRP -----------------------------------------------------------------
    print(f"Generating VRP instance ({N_NODES} nodes, {N_VEHICLES} vehicles)...")
    nodes_df, config = _generate_vrp(rng)
    nodes_df.to_csv(vrp_nodes_path, index=False)
    with open(vrp_config_path, "w") as fh:
        json.dump(config, fh, indent=2)

    total_demand = config["total_demand"]
    min_vehicles_needed = int(np.ceil(total_demand / VEHICLE_CAPACITY))
    print(f"  Customers       : {N_NODES - 1}")
    print(f"  Total demand    : {total_demand} units")
    print(f"  Vehicle capacity: {VEHICLE_CAPACITY} units × {N_VEHICLES} vehicles")
    print(f"  Min vehicles    : {min_vehicles_needed} (feasibility check)")
    print(f"  Nodes saved     → {vrp_nodes_path}")
    print(f"  Config saved    → {vrp_config_path}")

    # --- Supply chain --------------------------------------------------------
    print("\nGenerating supply chain log (500 shipments)...")
    sc_df = _generate_supply_chain(rng, n=500)
    sc_df.to_csv(supply_chain_path, index=False)

    on_time_rate = sc_df["on_time"].mean()
    print(f"  Shipments       : {len(sc_df):,}")
    print(f"  On-time rate    : {on_time_rate:.1%}")
    print(f"  Avg distance    : {sc_df['distance_km'].mean():.0f} km")
    print(f"  Avg cost        : ${sc_df['cost_usd'].mean():.2f}")
    print(f"  Saved           → {supply_chain_path}")

    elapsed_ms = (time.perf_counter() - t_start) * 1000
    print(f"\n  Total elapsed   : {elapsed_ms:.1f} ms")

    return nodes_df, config, sc_df


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    generate()
