"""Tests for qc-crypto-lab data and utilities."""
import pytest
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def test_crypto_benchmark_csv_exists():
    assert (DATA_DIR / "crypto_benchmark.csv").exists()


def test_vulnerability_scan_csv_exists():
    assert (DATA_DIR / "vulnerability_scan.csv").exists()


def test_quantum_safe_algorithms():
    pqc = ["ML-KEM-768", "ML-DSA-65", "SLH-DSA-128f", "FALCON-512"]
    classical = ["RSA-2048", "ECDSA-P256"]
    assert all(a not in classical for a in pqc)


def test_benchmark_data_structure():
    import csv
    f = DATA_DIR / "crypto_benchmark.csv"
    if not f.exists():
        pytest.skip("Generate data first")
    rows = list(csv.DictReader(open(f)))
    assert len(rows) >= 10
    assert "algorithm" in rows[0]
    assert "quantum_safe" in rows[0]


def test_benchmark_has_pqc_algorithms():
    import csv
    f = DATA_DIR / "crypto_benchmark.csv"
    if not f.exists():
        pytest.skip("Generate data first")
    rows = list(csv.DictReader(open(f)))
    algorithms = {r["algorithm"] for r in rows}
    pqc_expected = {"ML-KEM-768", "ML-DSA-65", "SLH-DSA-128f"}
    for alg in pqc_expected:
        assert alg in algorithms or f"{alg}-HW" in algorithms, f"Missing {alg}"


def test_vulnerability_scan_has_required_columns():
    import csv
    f = DATA_DIR / "vulnerability_scan.csv"
    if not f.exists():
        pytest.skip("Generate data first")
    rows = list(csv.DictReader(open(f)))
    assert len(rows) >= 10
    required_cols = {"system_id", "algorithm_found", "quantum_safe", "recommended_replacement"}
    assert required_cols.issubset(set(rows[0].keys()))


def test_vulnerability_scan_priority_values():
    import csv
    f = DATA_DIR / "vulnerability_scan.csv"
    if not f.exists():
        pytest.skip("Generate data first")
    rows = list(csv.DictReader(open(f)))
    valid_priorities = {"low", "medium", "critical", "high"}
    for row in rows:
        assert row["priority"] in valid_priorities, f"Invalid priority: {row['priority']}"


def test_nist_levels_positive():
    """NIST security levels should be non-negative integers."""
    import csv
    f = DATA_DIR / "crypto_benchmark.csv"
    if not f.exists():
        pytest.skip("Generate data first")
    rows = list(csv.DictReader(open(f)))
    for row in rows:
        lvl = int(row["nist_level"])
        assert lvl >= 0, f"Negative NIST level: {row}"
