"""
Root conftest.py — prevents pytest from treating directories with hyphens
as importable packages, which breaks qc-cryptography-module/tests imports.
"""
import sys
collect_ignore_glob = []
