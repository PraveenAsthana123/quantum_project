"""
Healthcare Lab Test Suite
Tests for classical_baseline, quantum_disease, and ecg results.
"""
from __future__ import annotations

import sys
import json
from pathlib import Path

_SRC = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(_SRC))

_RESULTS_DIR = Path(__file__).parent.parent / "results"


# ---------------------------------------------------------------------------
# Classical Baseline Tests
# ---------------------------------------------------------------------------

def _make_mock_xy(n: int = 300, n_features: int = 8, seed: int = 42):
    """Return (X, y, feature_names) with linearly separable labels."""
    import numpy as np
    rng = np.random.default_rng(seed)
    X = rng.random((n, n_features))
    y = (X[:, 0] + X[:, 1] > 1.0).astype(int)
    feature_names = [f"f{i}" for i in range(n_features)]
    return X, y, feature_names


def test_classical_baseline_returns_results_for_diabetes():
    """classical_baseline.main() returns list of results with accuracy keys."""
    import classical_baseline as cb

    # Patch individual loaders so each dataset loads mock data without touching disk
    _orig_load_diabetes = cb.load_diabetes
    _orig_load_heart = cb.load_heart
    _orig_load_hf = cb.load_heart_failure

    cb.load_diabetes = lambda: _make_mock_xy(300, 8, 42)
    cb.load_heart = lambda: _make_mock_xy(300, 8, 43)
    cb.load_heart_failure = lambda: _make_mock_xy(300, 8, 44)
    try:
        results = cb.main()
    finally:
        cb.load_diabetes = _orig_load_diabetes
        cb.load_heart = _orig_load_heart
        cb.load_heart_failure = _orig_load_hf

    assert isinstance(results, list), "main() must return a list"
    assert len(results) >= 1, "must return at least one result"
    for r in results:
        assert "accuracy" in r, f"result missing 'accuracy': {r}"
        assert "model" in r, f"result missing 'model': {r}"
        assert r["accuracy"] >= 0.0


def test_classical_baseline_result_has_required_keys():
    """Each result has accuracy, f1, roc_auc, model keys."""
    import classical_baseline as cb

    _orig_load_diabetes = cb.load_diabetes
    _orig_load_heart = cb.load_heart
    _orig_load_hf = cb.load_heart_failure

    cb.load_diabetes = lambda: _make_mock_xy(200, 8, 1)
    cb.load_heart = lambda: _make_mock_xy(200, 8, 2)
    cb.load_heart_failure = lambda: _make_mock_xy(200, 8, 3)
    try:
        results = cb.main()
    finally:
        cb.load_diabetes = _orig_load_diabetes
        cb.load_heart = _orig_load_heart
        cb.load_heart_failure = _orig_load_hf

    required_keys = {"accuracy", "f1", "roc_auc", "model"}
    for r in results:
        missing = required_keys - set(r.keys())
        assert not missing, f"result missing keys {missing}: {r}"


# ---------------------------------------------------------------------------
# Quantum Disease Tests
# ---------------------------------------------------------------------------

def test_quantum_disease_run_scenario_returns_accuracy():
    """quantum_disease.run_experiment() returns dict with 'accuracy' key."""
    import quantum_disease as qd
    import numpy as np

    _orig_load = qd._load_and_encode
    _orig_epochs = qd.EPOCHS
    _orig_train = qd.TRAIN_SAMPLES
    _orig_test = qd.TEST_SAMPLES

    def _mock_load_and_encode(filename, target_col, cat_cols=None):
        rng = np.random.default_rng(99)
        # Provide enough samples for TRAIN+TEST below
        X = rng.random((200, 4))
        y = (X[:, 0] > 0.5).astype(int)
        return X, y

    qd._load_and_encode = _mock_load_and_encode
    qd.EPOCHS = 5
    qd.TRAIN_SAMPLES = 80
    qd.TEST_SAMPLES = 40
    try:
        result = qd.run_experiment(
            dataset_name="diabetes",
            filename="diabetes.csv",
            target_col="Outcome",
        )
    finally:
        qd._load_and_encode = _orig_load
        qd.EPOCHS = _orig_epochs
        qd.TRAIN_SAMPLES = _orig_train
        qd.TEST_SAMPLES = _orig_test

    assert isinstance(result, dict), "run_experiment() must return a dict"
    assert "error" not in result, f"run_experiment returned error: {result.get('error')}"
    assert "accuracy" in result, f"result missing 'accuracy' key: {list(result.keys())}"
    assert 0.0 <= result["accuracy"] <= 1.0


# ---------------------------------------------------------------------------
# ECG Results Tests
# ---------------------------------------------------------------------------

def test_ecg_results_json_exists():
    """healthcare_summary.json (or ecg-specific results) exists on disk."""
    # The lab uses healthcare_summary.json as the top-level results file
    summary_path = _RESULTS_DIR / "healthcare_summary.json"
    assert summary_path.exists(), (
        f"healthcare_summary.json not found at {summary_path}. "
        "Run qc-healthcare-lab pipeline to generate it."
    )


def test_ecg_results_accuracy_above_threshold():
    """healthcare_summary.json contains a classical model with accuracy > 0.60."""
    summary_path = _RESULTS_DIR / "healthcare_summary.json"
    if not summary_path.exists():
        import pytest
        pytest.skip("healthcare_summary.json not present — run the lab pipeline first")

    with open(summary_path) as f:
        data = json.load(f)

    # The summary has classical_baselines.all_results list
    all_results = data.get("classical_baselines", {}).get("all_results", [])
    if not all_results:
        # Fallback: look for any accuracy key at top level
        all_results = data if isinstance(data, list) else []

    assert len(all_results) >= 1, "No classical baseline results found in healthcare_summary.json"

    best_acc = max(r.get("accuracy", 0.0) for r in all_results)
    assert best_acc > 0.60, (
        f"Best classical accuracy {best_acc:.4f} is not > 0.60"
    )
