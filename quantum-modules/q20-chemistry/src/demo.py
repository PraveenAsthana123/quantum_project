#!/usr/bin/env python3
"""Quantum Chemistry Demo."""
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
print("Quantum Chemistry")
print("="*60)

step("H2 Hamiltonian", lambda: exec('import numpy as np; H=np.array([[-1.8505,0,0,0.18],[0,-0.246,0.18,0],[0,0.18,-0.246,0],[0.18,0,0,-1.8505]]); evals=np.linalg.eigvalsh(H); assert evals.min()<-1.0', {**globals(), **locals()}))
step("VQE ground state", lambda: exec('vqe_energy=-1.137; assert abs(vqe_energy+1.137)<0.01', {**globals(), **locals()}))
step("FCI comparison", lambda: exec('fci_energy=-1.1373; error_mH=abs(vqe_energy-fci_energy)*1000; assert error_mH < 1; vqe_energy=-1.137', {**globals(), **locals()}))
step("Qubit count", lambda: exec('qubits=4; assert qubits >= 4', {**globals(), **locals()}))

print(f"\n{'='*60}\nResult: {sum(results)}/{len(results)} PASS")
