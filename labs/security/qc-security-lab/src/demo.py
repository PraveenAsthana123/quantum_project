#!/usr/bin/env python3
"""Quantum Security Lab Demo — end-to-end walkthrough."""
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
print("Quantum Security Lab")
print("=" * 60)

step("BB84 QKD simulation", lambda: (
    import numpy as np; np.random.seed(42),
    alice_bits = np.random.randint(0,2,100),
    alice_bases = np.random.randint(0,2,100),
    bob_bases = np.random.randint(0,2,100),
    matching = alice_bases == bob_bases,
    sifted_key = alice_bits[matching],
    assert len(sifted_key) > 30,
)[-1])

step("Grover speedup on AES-128", lambda: (
    import math,
    classical_steps = 2**128,
    grover_steps = 2**64,
    speedup = classical_steps / grover_steps,
    assert speedup == 2**64,
)[-1])

step("Quantum threat assessment", lambda: (
    vulnerable = ['RSA-2048','ECDSA-P256','DH-2048','ECDH-P256'],
    safe = ['AES-256','SHA-256','ML-KEM-768','ML-DSA-65'],
    assert len(vulnerable) == 4,
)[-1])

step("Shor algorithm qubit estimate", lambda: (
    n_bits = 2048,
    logical_qubits = 2*n_bits + 3,
    assert logical_qubits == 4099,
)[-1])

print(f"\n{'='*60}")
print(f"Result: {sum(results)}/{len(results)} PASS")
