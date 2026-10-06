"""
conftest.py — pytest configuration for pqc-control-tower tests.

Adds src/ to sys.path so test modules can import directly from the
source tree without an installed package.
"""
import sys
from pathlib import Path

# /mnt/deepa/quantum/pqc-control-tower/src
_SRC = Path(__file__).parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
