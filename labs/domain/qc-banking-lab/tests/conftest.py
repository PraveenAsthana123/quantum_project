"""Conftest for qc-banking-lab — forces correct src/ path before each test."""
import sys
import importlib
from pathlib import Path

_SRC = str(Path(__file__).parent.parent / "src")

# Ensure path is registered at collection time
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def pytest_runtest_setup(item):
    """Before each test, evict shared module names and ensure banking src is first."""
    _shared = ("classical_baseline", "quantum_fraud", "quantum_portfolio",
               "fraud_benchmark", "portfolio_optimization")
    for mod in _shared:
        sys.modules.pop(mod, None)
    # Re-insert our src at front
    if _SRC in sys.path:
        sys.path.remove(_SRC)
    sys.path.insert(0, _SRC)
