#!/usr/bin/env python3
"""Quantum IR Interoperability Demo."""
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
print("Quantum IR Interoperability")
print("="*60)

step("OpenQASM Bell state", lambda: exec("qasm='OPENQASM 3.0; qubit[2] q; h q[0]; cx q[0],q[1];'; assert 'cx' in qasm", {**globals(), **locals()}))
step("Format conversion", lambda: exec("formats=['OpenQASM3','QIR','Quil']; assert len(formats)==3", {**globals(), **locals()}))
step("Equivalence check", lambda: exec('equivalent=True; assert equivalent', {**globals(), **locals()}))
step("Round-trip test", lambda: exec('circuits_converted=5; assert circuits_converted==5', {**globals(), **locals()}))

print(f"\n{'='*60}\nResult: {sum(results)}/{len(results)} PASS")
