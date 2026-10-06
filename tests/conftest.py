"""
conftest.py — pytest configuration for the quantum security portfolio tests.
Adds all lab src/ directories and api/ to sys.path so test modules can
import from them without package installation.
"""
import sys
import os

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# API
sys.path.insert(0, os.path.join(_ROOT, "api"))

# Lab src directories
_LAB_DIRS = [
    "qc-banking-lab/src",
    "qc-finance-lab/src",
    "qc-healthcare-lab/src",
    "qc-cryptography-module/src",
    "qc-pqc-migration-lab/src",
    "qc-attack-lab/src",
    "qc-classical-security-lab/src",
    "qc-crypto-lab/src",
    "control-tower/src",
    "pqc-control-tower/src",
]

for _lab in _LAB_DIRS:
    _path = os.path.join(_ROOT, _lab)
    if os.path.isdir(_path) and _path not in sys.path:
        sys.path.insert(0, _path)
