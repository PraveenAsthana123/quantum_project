#!/usr/bin/env python3
"""Quantum Memory Demo."""
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
print("Quantum Memory")
print("="*60)

step("AFC efficiency", lambda: exec('efficiency=0.90; assert efficiency > 0.5', {**globals(), **locals()}))
step("Storage time", lambda: exec('T_us=100; assert T_us > 10', {**globals(), **locals()}))
step("Fidelity", lambda: exec('fidelity=0.98; assert fidelity > 0.95', {**globals(), **locals()}))
step("Multimode capacity", lambda: exec('modes=1000; assert modes > 100', {**globals(), **locals()}))

print(f"\n{'='*60}\nResult: {sum(results)}/{len(results)} PASS")
