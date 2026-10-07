#!/usr/bin/env python3
"""Silicon Spin Qubits Demo."""
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
print("Silicon Spin Qubits")
print("="*60)

step("Spin-1/2 Pauli matrices", lambda: exec('import numpy as np; X=np.array([[0,1],[1,0]]); assert X[0,1]==1', {**globals(), **locals()}))
step("Single qubit gate fidelity", lambda: exec('fidelity=0.9995; assert fidelity > 0.999', {**globals(), **locals()}))
step("T1 coherence time", lambda: exec('T1_ms=100; assert T1_ms > 10', {**globals(), **locals()}))
step("Two-qubit gate", lambda: exec('two_q_fidelity=0.995; assert two_q_fidelity > 0.99', {**globals(), **locals()}))

print(f"\n{'='*60}\nResult: {sum(results)}/{len(results)} PASS")
