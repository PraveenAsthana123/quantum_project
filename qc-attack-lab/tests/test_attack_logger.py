"""
test_attack_logger.py — pytest tests for qc-attack-lab/src/attack_logger.py.

Covers:
  - DB creation on first instantiation.
  - log_attack() inserts a record with all required fields.
  - get_layer_logs() returns logs for the correct layer only.
  - get_attack_stats() returns a dict with expected top-level keys
    including 'by_severity'.
  - simulate_attack_session() generates at least some entries in the DB.
  - Multiple calls to log_attack() with identical log_id are idempotent
    (INSERT OR REPLACE — no duplicate primary key error).
  - get_recent_logs() honours the limit parameter.
  - search_logs() filters by severity correctly.

All tests use pytest's tmp_path fixture so they never touch the real
results/attack_logs.db.
"""
import json
import pathlib
import pytest

# conftest.py already inserted src/ into sys.path
from attack_logger import AttackLogger, AttackLog


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def logger(tmp_path) -> AttackLogger:
    """Fresh AttackLogger backed by a temp DB for each test."""
    db = tmp_path / "test_attacks.db"
    return AttackLogger(db_path=db)


@pytest.fixture
def sample_entry() -> dict:
    """Minimal valid kwargs for log_attack()."""
    return dict(
        layer_id="L04",
        layer_name="TLS / HTTPS",
        attack_name="POODLE Attack",
        cve="CVE-2014-3566",
        tool_used="poodle-poc",
        mitre_technique="T1557.004",
        source_system="S1",
        target_system="S3 Classical",
        severity="HIGH",
        status="DETECTED",
        classical_result="SSLv3 downgrade succeeded on classical stack",
        pqc_result="PQC N/A for this attack class",
        evidence={"pcap": "poodle.pcap", "hash": "abc123", "log_extract": "SSLv3 detected"},
        detection_method="IDS signature match",
        response_action="Blocked source IP; alert SOC",
        ttd_seconds=120.0,
        ttr_seconds=600.0,
        analyst="SOC-L1",
        notes="Test entry",
    )


# ---------------------------------------------------------------------------
# DB creation
# ---------------------------------------------------------------------------

class TestDBCreation:
    def test_db_file_created(self, tmp_path):
        db = tmp_path / "new.db"
        AttackLogger(db_path=db)
        assert db.exists(), "DB file should be created by AttackLogger.__init__"

    def test_parent_dir_created(self, tmp_path):
        db = tmp_path / "subdir" / "deep" / "attacks.db"
        AttackLogger(db_path=db)
        assert db.exists()

    def test_db_has_attack_logs_table(self, tmp_path):
        import sqlite3
        db = tmp_path / "check.db"
        AttackLogger(db_path=db)
        conn = sqlite3.connect(db)
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "attack_logs" in tables


# ---------------------------------------------------------------------------
# log_attack()
# ---------------------------------------------------------------------------

class TestLogAttack:
    def test_returns_attack_log_instance(self, logger, sample_entry):
        result = logger.log_attack(**sample_entry)
        assert isinstance(result, AttackLog)

    def test_record_inserted(self, logger, sample_entry):
        import sqlite3
        logger.log_attack(**sample_entry)
        conn = sqlite3.connect(logger.db_path)
        count = conn.execute("SELECT COUNT(*) FROM attack_logs").fetchone()[0]
        conn.close()
        assert count == 1

    def test_required_fields_populated(self, logger, sample_entry):
        entry = logger.log_attack(**sample_entry)
        assert entry.layer_id == "L04"
        assert entry.layer_name == "TLS / HTTPS"
        assert entry.attack_name == "POODLE Attack"
        assert entry.cve == "CVE-2014-3566"
        assert entry.severity == "HIGH"
        assert entry.status == "DETECTED"
        assert entry.ttd_seconds == pytest.approx(120.0)
        assert entry.ttr_seconds == pytest.approx(600.0)
        assert entry.analyst == "SOC-L1"

    def test_evidence_stored_as_dict(self, logger, sample_entry):
        entry = logger.log_attack(**sample_entry)
        assert isinstance(entry.evidence, dict)
        assert "pcap" in entry.evidence

    def test_log_id_is_16_hex_chars(self, logger, sample_entry):
        entry = logger.log_attack(**sample_entry)
        assert len(entry.log_id) == 16
        assert all(c in "0123456789abcdef" for c in entry.log_id)

    def test_duplicate_log_id_no_error(self, logger, sample_entry):
        """INSERT OR REPLACE means re-inserting same log_id is safe."""
        entry1 = logger.log_attack(**sample_entry)
        # Force same log_id
        sample_entry["log_id"] = entry1.log_id
        entry2 = logger.log_attack(**sample_entry)
        assert entry2.log_id == entry1.log_id

    def test_default_severity_is_medium(self, logger):
        entry = logger.log_attack(
            layer_id="L01", attack_name="Minimal Entry"
        )
        assert entry.severity == "MEDIUM"

    def test_default_status_is_attempted(self, logger):
        entry = logger.log_attack(
            layer_id="L01", attack_name="Minimal Entry 2"
        )
        assert entry.status == "ATTEMPTED"

    def test_default_analyst_is_automated(self, logger):
        entry = logger.log_attack(
            layer_id="L01", attack_name="Minimal Entry 3"
        )
        assert entry.analyst == "AUTOMATED"

    def test_multiple_entries_different_layers(self, logger):
        import sqlite3
        for i, layer in enumerate(["L01", "L02", "L03", "L04"]):
            logger.log_attack(layer_id=layer, attack_name=f"Attack {i}")
        conn = sqlite3.connect(logger.db_path)
        count = conn.execute("SELECT COUNT(*) FROM attack_logs").fetchone()[0]
        layers = {row[0] for row in conn.execute(
            "SELECT layer_id FROM attack_logs"
        ).fetchall()}
        conn.close()
        assert count == 4
        assert layers == {"L01", "L02", "L03", "L04"}


# ---------------------------------------------------------------------------
# get_layer_logs()
# ---------------------------------------------------------------------------

class TestGetLayerLogs:
    def test_returns_correct_layer_only(self, logger):
        logger.log_attack(layer_id="L04", attack_name="TLS Attack A")
        logger.log_attack(layer_id="L04", attack_name="TLS Attack B")
        logger.log_attack(layer_id="L10", attack_name="SSH Attack")

        l04_logs = logger.get_layer_logs("L04")
        assert len(l04_logs) == 2
        assert all(log.layer_id == "L04" for log in l04_logs)

    def test_returns_list_of_attack_log(self, logger, sample_entry):
        logger.log_attack(**sample_entry)
        logs = logger.get_layer_logs("L04")
        assert isinstance(logs, list)
        assert all(isinstance(log, AttackLog) for log in logs)

    def test_returns_empty_list_for_unknown_layer(self, logger):
        result = logger.get_layer_logs("L99")
        assert result == []

    def test_logs_ordered_by_timestamp_desc(self, logger):
        """Entries should come back most-recent first."""
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        # Insert older entry first
        logger.log_attack(
            layer_id="L04", attack_name="Old Attack",
            timestamp=(now - timedelta(hours=2)).isoformat(),
        )
        logger.log_attack(
            layer_id="L04", attack_name="New Attack",
            timestamp=now.isoformat(),
        )
        logs = logger.get_layer_logs("L04")
        assert logs[0].attack_name == "New Attack"
        assert logs[1].attack_name == "Old Attack"


# ---------------------------------------------------------------------------
# get_attack_stats()
# ---------------------------------------------------------------------------

class TestGetAttackStats:
    def test_returns_dict(self, logger, sample_entry):
        logger.log_attack(**sample_entry)
        stats = logger.get_attack_stats()
        assert isinstance(stats, dict)

    def test_has_by_severity_key(self, logger, sample_entry):
        logger.log_attack(**sample_entry)
        stats = logger.get_attack_stats()
        assert "by_severity" in stats

    def test_has_required_top_level_keys(self, logger, sample_entry):
        logger.log_attack(**sample_entry)
        stats = logger.get_attack_stats()
        for key in ("total_attacks", "by_severity", "by_status", "by_layer",
                    "detection_rate", "block_rate"):
            assert key in stats, f"Missing key '{key}' in get_attack_stats()"

    def test_total_attack_count_correct(self, logger):
        for i in range(5):
            logger.log_attack(layer_id="L04", attack_name=f"Attack {i}")
        stats = logger.get_attack_stats()
        assert stats["total_attacks"] == 5

    def test_severity_counts_correct(self, logger):
        logger.log_attack(layer_id="L04", attack_name="Crit 1", severity="CRITICAL")
        logger.log_attack(layer_id="L04", attack_name="High 1", severity="HIGH")
        logger.log_attack(layer_id="L04", attack_name="High 2", severity="HIGH")
        stats = logger.get_attack_stats()
        assert stats["by_severity"].get("CRITICAL", 0) == 1
        assert stats["by_severity"].get("HIGH", 0) == 2

    def test_by_layer_contains_inserted_layers(self, logger):
        logger.log_attack(layer_id="L15", attack_name="Golden Ticket", severity="CRITICAL")
        logger.log_attack(layer_id="L15", attack_name="Pass-the-Hash", severity="HIGH")
        stats = logger.get_attack_stats()
        assert "L15" in stats["by_layer"]
        assert stats["by_layer"]["L15"] == 2

    def test_detection_rate_range(self, logger):
        for i in range(10):
            status = "DETECTED" if i < 7 else "SUCCESS"
            logger.log_attack(layer_id="L04", attack_name=f"A{i}", status=status)
        stats = logger.get_attack_stats()
        assert 0.0 <= stats["detection_rate"] <= 100.0

    def test_empty_db_returns_zero_total(self, logger):
        stats = logger.get_attack_stats()
        assert stats["total_attacks"] == 0


# ---------------------------------------------------------------------------
# simulate_attack_session()
# ---------------------------------------------------------------------------

class TestSimulateAttackSession:
    def test_generates_entries(self, logger):
        """simulate_attack_session() should insert at least a few entries."""
        logger.simulate_attack_session()
        stats = logger.get_attack_stats()
        assert stats["total_attacks"] > 0

    def test_covers_multiple_layers(self, logger):
        logger.simulate_attack_session()
        stats = logger.get_attack_stats()
        assert len(stats["by_layer"]) >= 3, (
            "simulate_attack_session should cover at least 3 layers"
        )

    def test_entries_have_valid_severity(self, logger):
        logger.simulate_attack_session()
        logs = logger.get_recent_logs(limit=100)
        valid = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        for log in logs:
            assert log.severity in valid, f"Unexpected severity: {log.severity}"


# ---------------------------------------------------------------------------
# get_recent_logs() — limit parameter
# ---------------------------------------------------------------------------

class TestGetRecentLogs:
    def test_limit_respected(self, logger):
        for i in range(20):
            logger.log_attack(layer_id="L04", attack_name=f"A{i}")
        recent = logger.get_recent_logs(limit=5)
        assert len(recent) == 5

    def test_returns_list_of_attack_log(self, logger, sample_entry):
        logger.log_attack(**sample_entry)
        logs = logger.get_recent_logs(limit=10)
        assert isinstance(logs, list)
        assert all(isinstance(log, AttackLog) for log in logs)


# ---------------------------------------------------------------------------
# search_logs() — severity filter
# ---------------------------------------------------------------------------

class TestSearchLogs:
    def test_filter_by_severity_high(self, logger):
        logger.log_attack(layer_id="L04", attack_name="H1", severity="HIGH")
        logger.log_attack(layer_id="L04", attack_name="C1", severity="CRITICAL")
        logger.log_attack(layer_id="L10", attack_name="H2", severity="HIGH")

        results = logger.search_logs(severity="HIGH")
        assert len(results) == 2
        assert all(log.severity == "HIGH" for log in results)

    def test_filter_by_layer_and_severity(self, logger):
        logger.log_attack(layer_id="L04", attack_name="TLS-H", severity="HIGH")
        logger.log_attack(layer_id="L04", attack_name="TLS-C", severity="CRITICAL")
        logger.log_attack(layer_id="L10", attack_name="SSH-H", severity="HIGH")

        results = logger.search_logs(layer_id="L04", severity="HIGH")
        assert len(results) == 1
        assert results[0].attack_name == "TLS-H"

    def test_no_match_returns_empty_list(self, logger):
        results = logger.search_logs(severity="LOW")
        assert results == []
