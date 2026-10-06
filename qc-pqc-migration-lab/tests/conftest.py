"""Conftest for qc-pqc-migration-lab — adds src/ to sys.path."""
import sys
from pathlib import Path

_SRC = str(Path(__file__).parent.parent / "src")
if _SRC in sys.path:
    sys.path.remove(_SRC)
sys.path.insert(0, _SRC)
