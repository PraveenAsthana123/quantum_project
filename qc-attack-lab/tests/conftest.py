"""
conftest.py — pytest configuration for qc-attack-lab tests.

Adds src/ to sys.path so test modules can import directly from the
source tree without an installed package.
"""
import sys
from pathlib import Path

_SRC = Path(__file__).parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
