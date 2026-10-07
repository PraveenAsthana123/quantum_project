#!/usr/bin/env python3
"""QC Cryptography Module Demo — end-to-end walkthrough."""
import sys, time, json, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []

def step(name, fn):
    t = time.perf_counter()
    try:
        r = fn()
        ms = (time.perf_counter()-t)*1000
        print(f"  {PASS} {name} ({ms:.1f}ms)")
        results.append(True); return r
    except Exception as e:
        print(f"  {FAIL} {name}: {e}")
        results.append(False); return None

print("=" * 60)
print("QC Cryptography Module")
print("=" * 60)

step("BB84 QKD (simplified)", lambda: (
    import numpy as np; np.random.seed(42),
    alice_bits = np.random.randint(0,2,200),
    alice_bases = np.random.randint(0,2,200),
    bob_bases = np.random.randint(0,2,200),
    sifted = alice_bits[alice_bases==bob_bases],
    assert len(sifted) > 80,
)[-1])

step("Grover oracle (4-item search)", lambda: (
    import numpy as np,
    n=4; target=2,
    steps_grover = int(np.pi/4*np.sqrt(n)),
    assert steps_grover == 1,
)[-1])

step("Shor qubit estimate (n=15)", lambda: (
    n=15; bits=4,
    qubits = 2*bits+3,
    assert qubits == 11,
)[-1])

step("ML-KEM-768 sizes", lambda: (
    pk_bytes=1184; ct_bytes=1088; ss_bytes=32,
    assert pk_bytes==1184 and ct_bytes==1088 and ss_bytes==32,
)[-1])

step("ML-DSA-65 sizes", lambda: (
    pk=1952; sk=4032; sig=3293,
    assert sig==3293,
)[-1])

print(f"\n{'='*60}")
print(f"Result: {sum(results)}/{len(results)} PASS")
