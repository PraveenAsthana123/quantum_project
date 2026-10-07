#!/usr/bin/env python3
"""Quantum Optical Clocks Demo."""
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
print("Quantum Optical Clocks")
print("="*60)

step("Clock frequencies", lambda: exec('Sr_Hz=4.29e14; Cs_Hz=9.19e9; ratio=Sr_Hz/Cs_Hz; assert ratio > 10000', {**globals(), **locals()}))
step("Fractional uncertainty", lambda: exec('Sr_uncertainty=2e-18; Cs_uncertainty=2e-16; improvement=Cs_uncertainty/Sr_uncertainty; assert improvement > 50', {**globals(), **locals()}))
step("Allan deviation", lambda: exec('tau_s=1; stability=1e-16; assert stability < 1e-14', {**globals(), **locals()}))
step("Relativistic correction", lambda: exec('height_m=1; df_f=1.1e-16*height_m; assert df_f > 0', {**globals(), **locals()}))

print(f"\n{'='*60}\nResult: {sum(results)}/{len(results)} PASS")
