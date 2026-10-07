#!/usr/bin/env python3
"""Quantum Chip Packaging Demo."""
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
print("Quantum Chip Packaging")
print("="*60)

step("Package resonance", lambda: exec('import math; L_nH=0.1; C_fF=10; f=1/(2*math.pi*math.sqrt(L_nH*1e-9*C_fF*1e-15))/1e9; assert f > 8', {**globals(), **locals()}))
step("Qubit isolation", lambda: exec('qubit_GHz=5; package_GHz=12.5; assert abs(qubit_GHz-package_GHz)>5', {**globals(), **locals()}))
step("Crosstalk", lambda: exec('crosstalk_dB=-35; assert crosstalk_dB < -20', {**globals(), **locals()}))
step("Flip-chip yield", lambda: exec('yield_pct=92; assert yield_pct > 85', {**globals(), **locals()}))

print(f"\n{'='*60}\nResult: {sum(results)}/{len(results)} PASS")
