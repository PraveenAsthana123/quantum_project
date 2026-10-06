#!/usr/bin/env python3

from pathlib import Path
import json
import numpy as np

from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import (
    IGate, XGate, YGate, ZGate, HGate, SGate, TGate,
    SXGate, PhaseGate, UGate,
    RXGate, RYGate, RZGate,
    CXGate, CZGate, SwapGate, iSwapGate, ECRGate,
    CCXGate,
)
from qiskit.quantum_info import Operator, Statevector, state_fidelity

ROOT = Path("/mnt/deepa/quantum")
OUT = ROOT / "results" / "gate-circuit-tests"
DATA = ROOT / "datasets" / "generated" / "gate-tests"

OUT.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

results = []


def record(name, passed, detail):
    row = {
        "test": name,
        "passed": bool(passed),
        "detail": str(detail),
    }
    results.append(row)
    print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")


def unitary_test(name, gate):
    U = Operator(gate).data
    eye = np.eye(U.shape[0], dtype=complex)
    ok = np.allclose(U.conj().T @ U, eye, atol=1e-10)
    record(f"unitary:{name}", ok, f"dimension={U.shape[0]}")


gates = {
    "I": IGate(),
    "X": XGate(),
    "Y": YGate(),
    "Z": ZGate(),
    "H": HGate(),
    "S": SGate(),
    "T": TGate(),
    "SX": SXGate(),
    "P": PhaseGate(0.23),
    "U": UGate(0.2, 0.3, 0.4),
    "RX": RXGate(0.37),
    "RY": RYGate(-0.42),
    "RZ": RZGate(0.91),
    "CX": CXGate(),
    "CZ": CZGate(),
    "SWAP": SwapGate(),
    "iSWAP": iSwapGate(),
    "ECR": ECRGate(),
    "CCX": CCXGate(),
}

for name, gate in gates.items():
    unitary_test(name, gate)


# X truth table
qc = QuantumCircuit(1)
qc.x(0)
sv = Statevector.from_instruction(qc)
record("X|0> -> |1>", np.allclose(np.abs(sv.data), [0, 1]), sv.data)


# H superposition
qc = QuantumCircuit(1)
qc.h(0)
sv = Statevector.from_instruction(qc)
record("H superposition", np.allclose(sv.probabilities(), [0.5, 0.5]), sv.probabilities())


# H twice identity
qc = QuantumCircuit(1)
qc.h(0)
qc.h(0)
sv = Statevector.from_instruction(qc)
record("H.H identity", np.allclose(np.abs(sv.data), [1, 0]), sv.data)


# Bell
bell = QuantumCircuit(2)
bell.h(0)
bell.cx(0, 1)
sv = Statevector.from_instruction(bell)
p = sv.probabilities_dict()

ok = (
    abs(p.get("00", 0) - 0.5) < 1e-10
    and abs(p.get("11", 0) - 0.5) < 1e-10
)

record("Bell state", ok, p)


# GHZ
ghz = QuantumCircuit(3)
ghz.h(0)
ghz.cx(0, 1)
ghz.cx(1, 2)
sv = Statevector.from_instruction(ghz)
p = sv.probabilities_dict()

ok = (
    abs(p.get("000", 0) - 0.5) < 1e-10
    and abs(p.get("111", 0) - 0.5) < 1e-10
)

record("GHZ state", ok, p)


# QFT smoke test
qft = QuantumCircuit(3)
qft.h(2)
qft.cp(np.pi / 2, 1, 2)
qft.cp(np.pi / 4, 0, 2)
qft.h(1)
qft.cp(np.pi / 2, 0, 1)
qft.h(0)
record("QFT-like circuit unitary", np.allclose(
    Operator(qft).data.conj().T @ Operator(qft).data,
    np.eye(8),
    atol=1e-10,
), f"depth={qft.depth()}")


# Compiler optimization equivalence via state fidelity
original = QuantumCircuit(3)
original.h(0)
original.cx(0, 1)
original.cx(1, 2)
original.rz(0.31, 2)
original.cx(1, 2)
original.cx(0, 1)

compiled = transpile(
    original,
    basis_gates=["rz", "sx", "x", "cx"],
    optimization_level=3,
)

sv1 = Statevector.from_instruction(original)
sv2 = Statevector.from_instruction(compiled)

fid = state_fidelity(sv1, sv2)

record(
    "transpile state fidelity",
    fid > 1 - 1e-9,
    f"fidelity={fid:.12f}",
)

record(
    "transpile metrics",
    True,
    f"depth={original.depth()}->{compiled.depth()}, gates={original.size()}->{compiled.size()}",
)


summary = {
    "passed": sum(1 for r in results if r["passed"]),
    "failed": sum(1 for r in results if not r["passed"]),
    "results": results,
}

text = json.dumps(summary, indent=2, default=str)

(OUT / "gate-circuit-test.json").write_text(text)
(DATA / "gate-circuit-test.json").write_text(text)

print()
print(json.dumps({
    "passed": summary["passed"],
    "failed": summary["failed"],
}, indent=2))

if summary["failed"]:
    raise SystemExit(1)
