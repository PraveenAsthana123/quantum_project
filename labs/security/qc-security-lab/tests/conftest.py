"""
conftest.py — pytest configuration for qc-security-lab tests.

Adds src/ to sys.path so test modules can import directly from the
source tree without an installed package. Also evicts any classical_baseline
already cached by another lab to prevent import collision.
"""
import sys
from pathlib import Path

# /mnt/deepa/quantum/qc-security-lab/src
_SRC = str(Path(__file__).parent.parent / "src")
if _SRC in sys.path:
    sys.path.remove(_SRC)
sys.path.insert(0, _SRC)

for _mod in list(sys.modules):
    if _mod in ("classical_baseline",):
        del sys.modules[_mod]


def pytest_runtest_setup(item):
    sys.modules.pop("classical_baseline", None)
    if _SRC in sys.path:
        sys.path.remove(_SRC)
    sys.path.insert(0, _SRC)
