"""
Tests for QC Finance Lab — validates result JSONs and core pricing function.
Does NOT re-run the full scripts (they are time-consuming).
"""
import json
import sys
import pathlib

import pytest

# ── Path setup ─────────────────────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT / "src"))


# ── Result JSON tests ──────────────────────────────────────────────────────────

def test_options_results_black_scholes_price():
    """options_results.json must have black_scholes.price > 0."""
    with open(DATA / "options_results.json") as f:
        d = json.load(f)
    assert "black_scholes" in d, "Missing 'black_scholes' key"
    price = d["black_scholes"]["price"]
    assert price > 0, f"black_scholes.price should be > 0, got {price}"


def test_risk_results_var_historical():
    """risk_results.json must have historical_var.var_95 > 0."""
    with open(DATA / "risk_results.json") as f:
        d = json.load(f)
    assert "historical_var" in d, "Missing 'historical_var' key"
    var95 = d["historical_var"]["var_95"]
    assert var95 > 0, f"historical_var.var_95 should be > 0, got {var95}"


# ── Function-level test ────────────────────────────────────────────────────────

def test_black_scholes_call_known_value():
    """black_scholes_call(S=100, K=105, T=0.5, r=0.05, sigma=0.20) ≈ 4.58 ± 0.5."""
    from quantum_options import black_scholes_call  # noqa: PLC0415

    result = black_scholes_call(S=100.0, K=105.0, T=0.5, r=0.05, sigma=0.20)
    price = result["price"]
    assert abs(price - 4.58) <= 0.5, (
        f"Expected price ≈ 4.58 (±0.5), got {price}"
    )
    assert price > 0, "Price must be positive"
