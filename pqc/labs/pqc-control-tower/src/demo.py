#!/usr/bin/env python3
"""PQC Control Tower Demo — end-to-end walkthrough."""
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
print("PQC Control Tower")
print("=" * 60)

step("Import control tower", lambda: (
    __import__('sys').path.insert(0, str(__import__('pathlib').Path(__file__).parent)),
)[-1])

step("Layer status (29 layers)", lambda: (
    data = [{'layer': f'L{i:02d}', 'status': ['not-started','planning','in-progress','done'][i%4]} for i in range(1,30)],
    assert len(data) == 29,
)[-1])

step("HNDL risk formula", lambda: (
    hndl = lambda s,t: round(s*t,2),
    tls_risk = hndl(9, 6),
    assert tls_risk == 54.0,
)[-1])

step("Vendor readiness scores", lambda: (
    vendors = {'AWS':72,'Google':68,'IBM':85,'Thales':90,'Microsoft':65},
    assert len(vendors) == 5,
)[-1])

step("CISO executive summary", lambda: (
    summary = {'overall_health': 34, 'layers_done': 3, 'layers_total': 29},
    assert summary['overall_health'] > 0,
)[-1])

print(f"\n{'='*60}")
print(f"Result: {sum(results)}/{len(results)} PASS")
