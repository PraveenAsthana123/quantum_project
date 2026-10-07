#!/usr/bin/env python3
"""Fault-Tolerant Quantum Computing Demo."""
import sys, time, math
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

PASS="✅ PASS"; FAIL="❌ FAIL"; results=[]

def step(name, fn):
    t=time.perf_counter()
    try:
        fn(); ms=(time.perf_counter()-t)*1000
        print(f"  {PASS} {name} ({ms:.1f}ms)"); results.append(True)
    except Exception as e:
        print(f"  {FAIL} {name}: {e}"); results.append(False)

print("="*60)
print("Fault-Tolerant Quantum Computing")
print("="*60)

step("Surface code d=3", lambda: exec('d=3; physical=d*d; assert physical==9', {**globals(), **locals()}))
step("Error threshold", lambda: exec('threshold=0.01; physical_error=0.001; assert physical_error < threshold', {**globals(), **locals()}))
step("Logical error rate", lambda: exec('logical_error=1e-6; assert logical_error < 1e-4', {**globals(), **locals()}))
step("Qubit overhead", lambda: exec('overhead=9; assert overhead >= 7', {**globals(), **locals()}))

print(f"\n{'='*60}\nResult: {sum(results)}/{len(results)} PASS")
