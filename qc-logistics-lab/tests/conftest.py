"""Conftest for qc-logistics-lab — forces correct src/ path before each test."""
import sys
from pathlib import Path

_SRC = str(Path(__file__).parent.parent / "src")

if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def pytest_runtest_setup(item):
    sys.modules.pop("classical_baseline", None)
    if _SRC in sys.path:
        sys.path.remove(_SRC)
    sys.path.insert(0, _SRC)
