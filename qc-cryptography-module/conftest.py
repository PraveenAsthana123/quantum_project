"""Root conftest for qc-cryptography-module — adds src/ to sys.path."""
import sys
from pathlib import Path

_SRC = str(Path(__file__).parent / "src")
if _SRC in sys.path:
    sys.path.remove(_SRC)
sys.path.insert(0, _SRC)
