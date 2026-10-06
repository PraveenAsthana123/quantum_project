"""Conftest for qc-finance-lab — forces correct src/ path before each test."""
import sys
from pathlib import Path

_SRC = str(Path(__file__).parent.parent / "src")

if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def pytest_runtest_setup(item):
    """Before each test, evict classical_baseline and ensure finance src is first."""
    sys.modules.pop("classical_baseline", None)
    if _SRC in sys.path:
        sys.path.remove(_SRC)
    sys.path.insert(0, _SRC)
