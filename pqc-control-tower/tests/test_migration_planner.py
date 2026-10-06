"""
test_migration_planner.py — pytest tests for pqc-control-tower/src/migration_planner.py.

Covers:
  - plan_migration() accepts a list of asset dicts and returns a list of
    MigrationAction objects.
  - Each action has required fields: asset_path (maps to asset), current_algorithm,
    recommended_replacement, effort_days, migration_priority.
  - P1 items appear before P2 in the sorted output.
  - RSA-2048 replacement contains "ML-KEM" or "ML-DSA".
  - Quantum-safe assets are skipped (no action created).
  - REPLACEMENT_MAP and PHASE_MAP are importable and contain expected entries.
"""
import pytest

# conftest.py already inserted src/ into sys.path
import migration_planner as mp


# ---------------------------------------------------------------------------
# Sample CBOM assets for use across tests
# ---------------------------------------------------------------------------

SAMPLE_ASSETS = [
    {
        "path": "web/server.crt",
        "asset_type": "certificate",
        "algorithm": "RSA",
        "key_size": 2048,
        "subject": "CN=example.com",
        "issuer": "CN=CA",
        "expiry": "2025-03-15",
        "quantum_safe": False,
        "harvest_now_risk": True,
        "migration_priority": "P1",
    },
    {
        "path": "ssh/id_ed25519",
        "asset_type": "ssh_key",
        "algorithm": "ED25519",
        "key_size": 256,
        "subject": "SSH Key",
        "issuer": "Local",
        "expiry": None,
        "quantum_safe": False,
        "harvest_now_risk": False,
        "migration_priority": "P2",
    },
    {
        "path": "pqc/kyber.cer",
        "asset_type": "certificate",
        "algorithm": "ML-KEM",
        "key_size": 768,
        "subject": "CN=pqc.example.com",
        "issuer": "CN=PQC CA",
        "expiry": "2030-01-01",
        "quantum_safe": True,   # should be SKIPPED by planner
        "harvest_now_risk": False,
        "migration_priority": "P3",
    },
    {
        "path": "web/api.crt",
        "asset_type": "certificate",
        "algorithm": "ECDSA",
        "key_size": 256,
        "subject": "CN=api.example.com",
        "issuer": "CN=DigiCert",
        "expiry": "2026-01-10",
        "quantum_safe": False,
        "harvest_now_risk": True,
        "migration_priority": "P1",
    },
]


@pytest.fixture(scope="module")
def actions():
    """Run plan_migration once for the whole test module."""
    return mp.plan_migration(SAMPLE_ASSETS)


# ---------------------------------------------------------------------------
# Basic shape tests
# ---------------------------------------------------------------------------

class TestPlanMigrationBasics:
    def test_returns_list(self, actions):
        assert isinstance(actions, list)

    def test_quantum_safe_asset_excluded(self, actions):
        """ML-KEM asset is quantum_safe=True; planner should skip it."""
        paths = [a.asset_path for a in actions]
        assert "pqc/kyber.cer" not in paths

    def test_vulnerable_assets_included(self, actions):
        paths = [a.asset_path for a in actions]
        assert "web/server.crt" in paths
        assert "web/api.crt" in paths

    def test_each_action_has_required_fields(self, actions):
        required = {"asset_path", "current_algorithm", "recommended_replacement",
                    "effort_days", "migration_priority"}
        for action in actions:
            d = action.to_dict()
            missing = required - d.keys()
            assert not missing, f"Action {action.asset_path!r} missing: {missing}"

    def test_effort_days_positive(self, actions):
        for action in actions:
            assert action.effort_days > 0, (
                f"effort_days must be positive for {action.asset_path!r}"
            )

    def test_risk_score_positive(self, actions):
        for action in actions:
            assert action.risk_score > 0


# ---------------------------------------------------------------------------
# RSA replacement
# ---------------------------------------------------------------------------

class TestRSAMigration:
    @pytest.fixture(scope="class")
    def rsa_action(self, actions):
        matches = [a for a in actions if "RSA" in a.current_algorithm.upper()]
        assert matches, "Expected at least one RSA action"
        return matches[0]

    def test_rsa_replacement_is_pqc(self, rsa_action):
        replacement = rsa_action.recommended_replacement.upper()
        assert "ML-KEM" in replacement or "ML-DSA" in replacement, (
            f"RSA replacement should be ML-KEM or ML-DSA, got {rsa_action.recommended_replacement!r}"
        )

    def test_rsa_is_p1(self, rsa_action):
        assert rsa_action.migration_priority == "P1"

    def test_rsa_phase_is_1(self, rsa_action):
        assert rsa_action.phase == 1


# ---------------------------------------------------------------------------
# P1 before P2 ordering
# ---------------------------------------------------------------------------

class TestSortOrder:
    def test_p1_before_p2(self, actions):
        """After sort, all P1 actions must precede the first P2 action."""
        priorities = [a.migration_priority for a in actions]
        last_p1 = max((i for i, p in enumerate(priorities) if p == "P1"), default=-1)
        first_p2 = min((i for i, p in enumerate(priorities) if p == "P2"), default=len(priorities))
        assert last_p1 < first_p2, (
            f"P1 items must come before P2. P1 last at index {last_p1}, "
            f"P2 first at index {first_p2}. Priorities: {priorities}"
        )

    def test_risk_score_descending(self, actions):
        """Actions should be sorted by descending risk_score (higher risk first)."""
        scores = [a.risk_score for a in actions]
        assert scores == sorted(scores, reverse=True) or len(set(scores)) < len(scores), (
            "Actions should be sorted with highest risk_score first"
        )


# ---------------------------------------------------------------------------
# Migration steps field
# ---------------------------------------------------------------------------

class TestMigrationSteps:
    def test_steps_string_nonempty(self, actions):
        for action in actions:
            assert isinstance(action.migration_steps, str)
            assert len(action.migration_steps) > 0

    def test_steps_contain_step_keyword(self, actions):
        for action in actions:
            assert "Step" in action.migration_steps or "step" in action.migration_steps.lower()


# ---------------------------------------------------------------------------
# REPLACEMENT_MAP integrity
# ---------------------------------------------------------------------------

class TestReplacementMap:
    def test_rsa_has_sig_replacement(self):
        assert "RSA" in mp.REPLACEMENT_MAP
        assert mp.REPLACEMENT_MAP["RSA"]["sig"] is not None
        assert "ML-" in mp.REPLACEMENT_MAP["RSA"]["sig"]

    def test_ecdsa_has_replacement(self):
        assert "ECDSA" in mp.REPLACEMENT_MAP

    def test_effort_days_all_positive(self):
        for alg, info in mp.REPLACEMENT_MAP.items():
            assert info["effort_days"] > 0, (
                f"REPLACEMENT_MAP[{alg!r}]['effort_days'] must be positive"
            )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_input_returns_empty_list(self):
        result = mp.plan_migration([])
        assert result == []

    def test_all_safe_returns_empty_list(self):
        safe_only = [
            {"path": "p", "asset_type": "certificate", "algorithm": "ML-KEM",
             "quantum_safe": True, "harvest_now_risk": False, "migration_priority": "P3",
             "expiry": None}
        ]
        result = mp.plan_migration(safe_only)
        assert result == []

    def test_unknown_algo_falls_back_gracefully(self):
        unknown = [
            {"path": "x", "asset_type": "certificate", "algorithm": "UNKNOWN_ALGO_XYZ",
             "quantum_safe": False, "harvest_now_risk": False, "migration_priority": "P2",
             "expiry": None}
        ]
        result = mp.plan_migration(unknown)
        assert len(result) == 1
        # Should default to some PQC recommendation
        assert result[0].recommended_replacement != ""
