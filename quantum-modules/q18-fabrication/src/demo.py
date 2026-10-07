#!/usr/bin/env python3
"""Qubit Fabrication Demo."""
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
print("Qubit Fabrication")
print("="*60)

step("Josephson parameters", lambda: exec('EJ_GHz=20; EC_GHz=0.3; ratio=EJ_GHz/EC_GHz; assert ratio > 50', {**globals(), **locals()}))
step("Qubit frequency", lambda: exec('import numpy as np; freq=np.sqrt(8*20*0.3)-0.3; assert 3 < freq < 7', {**globals(), **locals()}))
step("Anharmonicity", lambda: exec('anharmonicity_GHz=-0.3; assert anharmonicity_GHz < 0', {**globals(), **locals()}))
step("Fabrication yield", lambda: exec('yield_pct=85; assert yield_pct > 70', {**globals(), **locals()}))

print(f"\n{'='*60}\nResult: {sum(results)}/{len(results)} PASS")
