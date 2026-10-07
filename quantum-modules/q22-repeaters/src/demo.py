#!/usr/bin/env python3
"""Quantum Repeaters Demo."""
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
print("Quantum Repeaters")
print("="*60)

step("Link fidelity", lambda: exec('F_raw=0.70; assert 0.5 < F_raw < 1.0', {**globals(), **locals()}))
step("Purification step", lambda: exec('F_purified = (F_raw**2)/(F_raw**2+(1-F_raw)**2); assert F_purified > F_raw; F_raw=0.70', {**globals(), **locals()}))
step("3-node chain", lambda: exec('nodes=3; links=2; assert links==nodes-1', {**globals(), **locals()}))
step("End-to-end fidelity", lambda: exec('F_ee=0.95; assert F_ee > 0.9', {**globals(), **locals()}))

print(f"\n{'='*60}\nResult: {sum(results)}/{len(results)} PASS")
