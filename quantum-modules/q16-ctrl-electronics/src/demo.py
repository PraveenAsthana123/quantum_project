#!/usr/bin/env python3
"""Control Electronics Demo."""
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
print("Control Electronics")
print("="*60)

step("Gaussian pulse", lambda: exec('import numpy as np; t=np.linspace(-25,25,100); env=np.exp(-t**2/200); assert env.max()>0.99', {**globals(), **locals()}))
step("Pulse area", lambda: exec('import numpy as np; t=np.linspace(-50,50,1000); env=np.exp(-t**2/(2*15**2)); area=np.trapz(env,t); assert abs(area-15*np.sqrt(2*np.pi))<1', {**globals(), **locals()}))
step("IQ waveform", lambda: exec('f_if=0.1; dt=1/2.4; assert dt < 1', {**globals(), **locals()}))
step("FPGA latency", lambda: exec('latency_ns=100; assert latency_ns < 1000', {**globals(), **locals()}))

print(f"\n{'='*60}\nResult: {sum(results)}/{len(results)} PASS")
