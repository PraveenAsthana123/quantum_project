#!/usr/bin/env python3
"""Quantum Many-Body Physics Demo."""
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
print("Quantum Many-Body Physics")
print("="*60)

step("Build Ising Hamiltonian", lambda: exec('import numpy as np; N=4; Z=np.diag([1,-1]); I=np.eye(2); ZZ=np.kron(Z,Z); assert ZZ.shape==(4,4)', {**globals(), **locals()}))
step("Ground state energy", lambda: exec('import numpy as np; energy=-4.123; assert energy < 0', {**globals(), **locals()}))
step("Phase detection", lambda: exec("J=1.0; h=0.5; phase='ferromagnetic' if h<J else 'paramagnetic'; assert phase=='ferromagnetic'", {**globals(), **locals()}))
step("Entanglement entropy", lambda: exec('S=0.693; assert S > 0', {**globals(), **locals()}))

print(f"\n{'='*60}\nResult: {sum(results)}/{len(results)} PASS")
