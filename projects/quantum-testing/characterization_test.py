#!/usr/bin/env python3

from pathlib import Path
import json

ROOT = Path("/mnt/deepa/quantum")
OUT = ROOT / "results" / "characterization-tests"
OUT.mkdir(parents=True, exist_ok=True)

result = {}

try:
    import pygsti

    result["pygsti"] = {
        "status": "PASS",
        "version": getattr(pygsti, "__version__", "installed"),
        "capabilities": [
            "gate-set-tomography",
            "randomized-benchmarking",
            "robust-phase-estimation",
            "drift-analysis",
        ],
    }

except Exception as exc:
    result["pygsti"] = {
        "status": "FAIL",
        "error": repr(exc),
    }

try:
    import qiskit_experiments

    result["qiskit_experiments"] = {
        "status": "PASS",
        "version": getattr(qiskit_experiments, "__version__", "installed"),
    }

except Exception as exc:
    result["qiskit_experiments"] = {
        "status": "FAIL",
        "error": repr(exc),
    }

(OUT / "characterization.json").write_text(
    json.dumps(result, indent=2)
)

print(json.dumps(result, indent=2))
