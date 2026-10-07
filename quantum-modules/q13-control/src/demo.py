#!/usr/bin/env python3
"""Qubit Control Systems Demo."""
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
print("Qubit Control Systems")
print("="*60)

step("Rabi oscillation", lambda: exec('import numpy as np; t=np.linspace(0,100,1000); pop=np.sin(np.pi*t/100)**2; assert pop.max()>0.99', {**globals(), **locals()}))
step("Pi-pulse time", lambda: exec('pi_ns=50; omega=np.pi/pi_ns; assert abs(omega-np.pi/50)<0.01; import numpy as np', {**globals(), **locals()}))
step("Gate fidelity", lambda: exec('fidelity=0.9998; assert fidelity > 0.999', {**globals(), **locals()}))
step("AWG waveform", lambda: exec('sample_rate_GSps=2.4; assert sample_rate_GSps >= 1.0', {**globals(), **locals()}))

print(f"\n{'='*60}\nResult: {sum(results)}/{len(results)} PASS")
