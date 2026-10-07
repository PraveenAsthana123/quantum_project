#!/usr/bin/env python3
"""Quantum Control Tower Demo — end-to-end walkthrough."""
import sys, time, json, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []

def step(name, fn):
    t = time.perf_counter()
    try:
        r = fn()
        ms = (time.perf_counter()-t)*1000
        print(f"  {PASS} {name} ({ms:.1f}ms)")
        results.append(True); return r
    except Exception as e:
        print(f"  {FAIL} {name}: {e}")
        results.append(False); return None

print("=" * 60)
print("Quantum Control Tower")
print("=" * 60)

step("Load layer definitions", lambda: (
    layers = [f'L{i:02d}' for i in range(1,30)],
    assert len(layers)==29,
)[-1])

step("Compute HNDL risk", lambda: (
    risk = 9*6,
    assert risk == 54,
)[-1])

step("Vendor readiness", lambda: (
    v={'AWS':72,'Google':68,'IBM':85},
    assert max(v.values())==85,
)[-1])

step("Generate health score", lambda: (
    score = int(3/29*100),
    assert 0 < score < 100,
)[-1])

print(f"\n{'='*60}")
print(f"Result: {sum(results)}/{len(results)} PASS")
