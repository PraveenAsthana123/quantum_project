#!/usr/bin/env python3

from pathlib import Path
import json

from qiskit import QuantumCircuit, transpile

ROOT = Path("/mnt/deepa/quantum")
OUT = ROOT / "results" / "mqt-tests"
OUT.mkdir(parents=True, exist_ok=True)

result = {}

try:
    import mqt.ddsim
    result["mqt_ddsim"] = {
        "status": "PASS",
        "version": getattr(mqt.ddsim, "__version__", "installed"),
    }
except Exception as exc:
    result["mqt_ddsim"] = {
        "status": "FAIL",
        "error": repr(exc),
    }

try:
    import mqt.yaqs
    result["mqt_yaqs"] = {
        "status": "PASS",
        "version": getattr(mqt.yaqs, "__version__", "installed"),
    }
except Exception as exc:
    result["mqt_yaqs"] = {
        "status": "FAIL",
        "error": repr(exc),
    }

try:
    from mqt.bench import BenchmarkLevel, get_benchmark

    circuit = get_benchmark(
        benchmark="ghz",
        level=BenchmarkLevel.ALG,
        circuit_size=5,
    )

    result["mqt_bench"] = {
        "status": "PASS",
        "qubits": circuit.num_qubits,
        "depth": circuit.depth(),
        "gates": circuit.size(),
    }

except Exception as exc:
    result["mqt_bench"] = {
        "status": "FAIL",
        "error": repr(exc),
    }

try:
    from mqt import qcec

    original = QuantumCircuit(3)
    original.h(0)
    original.cx(0, 1)
    original.cx(1, 2)

    compiled = transpile(
        original,
        basis_gates=["rz", "sx", "x", "cx"],
        optimization_level=3,
    )

    verification = qcec.verify(original, compiled)

    result["qcec"] = {
        "status": "PASS",
        "equivalence": str(verification.equivalence),
    }

except Exception as exc:
    result["qcec"] = {
        "status": "FAIL",
        "error": repr(exc),
    }

(OUT / "mqt-test.json").write_text(
    json.dumps(result, indent=2)
)

print(json.dumps(result, indent=2))
