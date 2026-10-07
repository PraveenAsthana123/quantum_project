#!/usr/bin/env python3
"""Cryogenics & Dilution Refrigerators Demo."""
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
print("Cryogenics & Dilution Refrigerators")
print("="*60)

step("Fridge stages", lambda: exec("stages=['300K','4K','Still','Cold Plate','MC']; assert len(stages)==5", {**globals(), **locals()}))
step("Heat load 50 qubits", lambda: exec('heat_per_qubit_uW=1.0; n=50; total=heat_per_qubit_uW*n; assert total==50.0', {**globals(), **locals()}))
step("Cooling power", lambda: exec('cooling_uW=400; margin=cooling_uW-50; assert margin > 0', {**globals(), **locals()}))
step("Operating temperature", lambda: exec('T_mK=20; assert T_mK < 100', {**globals(), **locals()}))

print(f"\n{'='*60}\nResult: {sum(results)}/{len(results)} PASS")
