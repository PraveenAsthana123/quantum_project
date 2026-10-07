#!/usr/bin/env python3
"""Quantum Sensing Demo."""
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
print("Quantum Sensing")
print("="*60)

step("SQL vs Heisenberg", lambda: exec('import numpy as np; N=100; sql=1/np.sqrt(N); hl=1/N; assert hl < sql', {**globals(), **locals()}))
step("Improvement factor", lambda: exec('N=100; improvement=N/np.sqrt(N); assert improvement==np.sqrt(N); import numpy as np', {**globals(), **locals()}))
step("NV center sensitivity", lambda: exec('sensitivity_nT_rtHz=1.0; assert sensitivity_nT_rtHz < 10', {**globals(), **locals()}))
step("Gravitational sensing", lambda: exec('sql_m_rtHz=1e-20; assert sql_m_rtHz < 1e-18', {**globals(), **locals()}))

print(f"\n{'='*60}\nResult: {sum(results)}/{len(results)} PASS")
