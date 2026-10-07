#!/usr/bin/env python3
"""Control Tower — Synthetic data generator."""
import csv, json, random
from pathlib import Path
import numpy as np

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- tower_summary.json ---
with open(DATA_DIR/'tower_summary.json','w') as f:
  json.dump({'layers':29,'done':3,'health':34,'generated':'2026-10-06'},f,indent=2)
print(f"  Saved → {DATA_DIR / "tower_summary.json"}")

print("\nData generation complete.")
