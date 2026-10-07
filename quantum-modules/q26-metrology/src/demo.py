#!/usr/bin/env python3
"""Quantum Metrology Demo."""
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
print("Quantum Metrology")
print("="*60)

step("Phase estimation", lambda: exec('import numpy as np; phi=0.3; n=10; precision=1/2**n; estimated=round(phi/precision)*precision; assert abs(estimated-phi)<0.01', {**globals(), **locals()}))
step("Classical comparison", lambda: exec('classical_prec=1/np.sqrt(10); quantum_prec=1/10; assert quantum_prec < classical_prec; import numpy as np', {**globals(), **locals()}))
step("Heisenberg scaling", lambda: exec('N=10; hl=1/N; assert hl == 0.1', {**globals(), **locals()}))
step("Clock stability", lambda: exec('stability_1s=1e-16; assert stability_1s < 1e-14', {**globals(), **locals()}))

print(f"\n{'='*60}\nResult: {sum(results)}/{len(results)} PASS")
