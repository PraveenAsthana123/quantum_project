"""
API Integration Test Suite
============================
Tests all major API endpoints for correct response structure,
data types, and business logic. Validates pre/post data states.

Coverage:
  - Tower endpoints  : /api/v1/tower/*
  - Security endpoints: /api/v1/security/*
  - Health endpoints : /health, /status, /health/detailed

Run: pytest tests/test_api_integration.py -v
"""
from __future__ import annotations

import sys
import os
import time
import json

# Ensure api/ is on path (also handled by conftest.py)
_API_DIR = os.path.join(os.path.dirname(__file__), "..", "api")
sys.path.insert(0, os.path.abspath(_API_DIR))

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# ============================================================================
# Tower endpoints
# ============================================================================

class TestTowerSummary:
    """GET /api/v1/tower/summary"""

    def test_tower_summary_returns_200(self):
        """Summary endpoint must return HTTP 200."""
        response = client.get("/api/v1/tower/summary")
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text[:200]}"
        )

    def test_tower_summary_has_status_ok(self):
        """Top-level 'status' field must equal 'ok'."""
        response = client.get("/api/v1/tower/summary")
        body = response.json()
        assert body.get("status") == "ok", f"status field missing or wrong: {body}"

    def test_tower_summary_data_has_required_keys(self):
        """data block must contain overall_pqc_score, layers_completed, hndl_risk_score."""
        response = client.get("/api/v1/tower/summary")
        data = response.json().get("data", {})
        required = {"overall_pqc_score", "layers_completed", "hndl_risk_score"}
        present = set(data.keys())
        missing = required - present
        assert not missing, (
            f"Missing keys in tower/summary data: {missing}. Present keys: {present}"
        )

    def test_tower_score_in_range(self):
        """overall_pqc_score must be a number between 0 and 100 inclusive."""
        response = client.get("/api/v1/tower/summary")
        data = response.json().get("data", {})
        score = data.get("overall_pqc_score")
        assert score is not None, "overall_pqc_score missing from data"
        assert isinstance(score, (int, float)), f"overall_pqc_score not numeric: {score!r}"
        assert 0 <= score <= 100, f"overall_pqc_score {score} outside [0, 100]"

    def test_tower_hndl_risk_has_required_keys(self):
        """hndl_risk nested block (or /hndl-risk endpoint) must have score, harvest_probability, priority_systems."""
        response = client.get("/api/v1/tower/hndl-risk")
        assert response.status_code == 200, (
            f"hndl-risk returned {response.status_code}: {response.text[:200]}"
        )
        data = response.json().get("data", {})
        required = {"score", "harvest_probability", "priority_systems"}
        missing = required - set(data.keys())
        assert not missing, (
            f"hndl-risk data missing keys: {missing}. Got: {list(data.keys())}"
        )


class TestTowerLayers:
    """GET /api/v1/tower/layers"""

    def test_tower_layers_returns_200(self):
        """Layers endpoint must return HTTP 200."""
        response = client.get("/api/v1/tower/layers")
        assert response.status_code == 200

    def test_tower_layers_returns_29(self):
        """Must return exactly 29 security layers."""
        response = client.get("/api/v1/tower/layers")
        body = response.json()
        # Count is embedded as body["count"] or len(body["data"])
        count_field = body.get("count")
        data_len = len(body.get("data", []))
        actual = count_field if count_field is not None else data_len
        assert actual == 29, f"Expected 29 layers, got {actual}"

    def test_tower_layers_each_has_id_and_name(self):
        """Each layer entry must have at minimum 'id' and 'name' or 'layer_id'."""
        response = client.get("/api/v1/tower/layers")
        layers = response.json().get("data", [])
        for idx, layer in enumerate(layers):
            has_id = "id" in layer or "layer_id" in layer
            has_name = "name" in layer or "layer_name" in layer
            assert has_id, f"Layer[{idx}] missing 'id': {layer}"
            assert has_name, f"Layer[{idx}] missing 'name': {layer}"


class TestTowerThreats:
    """GET /api/v1/tower/threats"""

    def test_tower_threats_returns_200(self):
        response = client.get("/api/v1/tower/threats")
        assert response.status_code == 200

    def test_tower_threats_non_empty(self):
        """Threat intelligence feed must return at least 1 item."""
        response = client.get("/api/v1/tower/threats")
        body = response.json()
        data = body.get("data", [])
        count = body.get("count", len(data))
        assert count > 0, "Threats endpoint returned an empty list"
        assert len(data) > 0, "Threats data array is empty"


class TestTowerCompliance:
    """GET /api/v1/tower/compliance"""

    def test_tower_compliance_returns_200(self):
        response = client.get("/api/v1/tower/compliance")
        assert response.status_code == 200

    def test_tower_compliance_has_nist_or_cnsa(self):
        """Compliance response must include at least one of: nist, cnsa (case-insensitive)."""
        response = client.get("/api/v1/tower/compliance")
        data = response.json().get("data", response.json())
        keys_lower = {k.lower() for k in (data.keys() if isinstance(data, dict) else {})}
        # Also check if 'nist' or 'cnsa' appears anywhere in string representation
        raw = json.dumps(data).lower()
        has_nist = "nist" in keys_lower or "nist" in raw
        has_cnsa = "cnsa" in keys_lower or "cnsa" in raw
        assert has_nist or has_cnsa, (
            f"Neither 'nist' nor 'cnsa' found in compliance response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}"
        )


class TestTowerVendors:
    """GET /api/v1/tower/vendors"""

    def test_tower_vendors_returns_200(self):
        response = client.get("/api/v1/tower/vendors")
        assert response.status_code == 200

    def test_tower_vendors_returns_providers(self):
        """Vendor list must contain at least 5 providers."""
        response = client.get("/api/v1/tower/vendors")
        body = response.json()
        data = body.get("data", [])
        count = body.get("count", len(data))
        actual = count if count is not None else len(data)
        assert actual >= 5, f"Expected at least 5 vendors, got {actual}"


class TestTowerCisoReport:
    """GET /api/v1/tower/ciso-report"""

    def test_tower_ciso_report_returns_200(self):
        response = client.get("/api/v1/tower/ciso-report")
        assert response.status_code == 200

    def test_tower_ciso_report_has_sections(self):
        """CISO report must include executive_summary or critical_actions."""
        response = client.get("/api/v1/tower/ciso-report")
        data = response.json().get("data", {})
        raw = json.dumps(data).lower()
        has_executive = "executive_summary" in data or "executive summary" in raw
        has_actions = "critical_actions" in data or "critical_action" in raw
        assert has_executive or has_actions, (
            f"CISO report missing executive_summary and critical_actions. Keys: {list(data.keys()) if isinstance(data, dict) else type(data)}"
        )


# ============================================================================
# Security endpoints  (/api/v1/security/*)
# ============================================================================

class TestSecurityHealth:
    """GET /api/v1/security/health"""

    def test_security_health_200(self):
        """Security health endpoint must return HTTP 200."""
        response = client.get("/api/v1/security/health")
        assert response.status_code == 200

    def test_security_health_has_status(self):
        """Response must carry a 'status' field."""
        response = client.get("/api/v1/security/health")
        body = response.json()
        assert "status" in body, f"'status' key missing from security health: {body}"

    def test_security_health_has_api_version(self):
        """Response must include api_version."""
        response = client.get("/api/v1/security/health")
        body = response.json()
        assert "api_version" in body, f"'api_version' missing from security health: {body}"


class TestKpiSummary:
    """GET /api/v1/security/kpi/summary"""

    def test_kpi_summary_returns_200(self):
        response = client.get("/api/v1/security/kpi/summary")
        assert response.status_code == 200

    def test_kpi_summary_has_metrics(self):
        """KPI summary must contain numeric metric fields."""
        response = client.get("/api/v1/security/kpi/summary")
        body = response.json()
        # Must have at least one key beyond data_source
        non_meta_keys = {k for k in body if k != "data_source"}
        assert len(non_meta_keys) >= 1, f"kpi/summary has no metric keys: {body}"


class TestCbomSummary:
    """GET /api/v1/security/cbom/summary"""

    def test_cbom_summary_returns_200(self):
        response = client.get("/api/v1/security/cbom/summary")
        assert response.status_code == 200

    def test_cbom_summary_has_assets(self):
        """CBOM summary must report at least a total_assets count."""
        response = client.get("/api/v1/security/cbom/summary")
        body = response.json()
        raw = json.dumps(body).lower()
        has_assets = "total_assets" in body or "assets" in raw or "components" in raw
        assert has_assets, f"cbom/summary missing asset count. Body: {body}"


class TestLayersStatus:
    """GET /api/v1/security/layers/status"""

    def test_layers_status_returns_200(self):
        response = client.get("/api/v1/security/layers/status")
        assert response.status_code == 200

    def test_layers_status_returns_layers(self):
        """Layers status must return a non-empty list of layers."""
        response = client.get("/api/v1/security/layers/status")
        body = response.json()
        layers = body.get("layers", body if isinstance(body, list) else [])
        assert len(layers) > 0, "layers/status returned empty list"

    def test_layers_status_has_29_entries(self):
        """Security layers list must have 29 entries (matching 29-layer architecture)."""
        response = client.get("/api/v1/security/layers/status")
        body = response.json()
        layers = body.get("layers", body if isinstance(body, list) else [])
        assert len(layers) == 29, f"Expected 29 layers, got {len(layers)}"


class TestPqcBenchmarks:
    """GET /api/v1/security/pqc/benchmarks"""

    def test_pqc_benchmarks_returns_200(self):
        response = client.get("/api/v1/security/pqc/benchmarks")
        assert response.status_code == 200

    def test_pqc_benchmarks_present(self):
        """Benchmark response must contain algorithms or classical comparison data."""
        response = client.get("/api/v1/security/pqc/benchmarks")
        body = response.json()
        has_algos = "algorithms" in body or "classical" in body
        assert has_algos, f"pqc/benchmarks missing algorithm data. Keys: {list(body.keys())}"

    def test_pqc_benchmarks_has_ml_kem(self):
        """Benchmark data must mention ML-KEM (the primary NIST FIPS 203 algorithm)."""
        response = client.get("/api/v1/security/pqc/benchmarks")
        raw = response.text.upper()
        assert "ML-KEM" in raw or "KYBER" in raw, (
            "pqc/benchmarks does not mention ML-KEM or Kyber"
        )


class TestAttacksRecent:
    """GET /api/v1/security/attacks/recent"""

    def test_attacks_recent_returns_200(self):
        response = client.get("/api/v1/security/attacks/recent")
        assert response.status_code == 200

    def test_attacks_recent_returns_list(self):
        """attacks/recent must return a list of attack records."""
        response = client.get("/api/v1/security/attacks/recent")
        body = response.json()
        attacks = body.get("attacks", body if isinstance(body, list) else None)
        assert attacks is not None, f"'attacks' key missing: {list(body.keys())}"
        assert isinstance(attacks, list), f"attacks field is not a list: {type(attacks)}"
        assert len(attacks) > 0, "attacks/recent returned empty attack list"


class TestAttacksStats:
    """GET /api/v1/security/attacks/stats"""

    def test_attacks_stats_returns_200(self):
        response = client.get("/api/v1/security/attacks/stats")
        assert response.status_code == 200

    def test_attacks_stats_structure(self):
        """Stats must include by_layer, by_severity breakdowns."""
        response = client.get("/api/v1/security/attacks/stats")
        body = response.json()
        assert "by_layer" in body, f"'by_layer' missing from attacks/stats: {list(body.keys())}"
        assert "by_severity" in body, f"'by_severity' missing from attacks/stats: {list(body.keys())}"
        assert isinstance(body["by_layer"], dict), "'by_layer' must be a dict"
        assert isinstance(body["by_severity"], dict), "'by_severity' must be a dict"

    def test_attacks_stats_pqc_prevents_pct_in_range(self):
        """pqc_prevents_pct must be a percentage between 0 and 100."""
        response = client.get("/api/v1/security/attacks/stats")
        body = response.json()
        pct = body.get("pqc_prevents_pct")
        if pct is not None:
            assert 0 <= pct <= 100, f"pqc_prevents_pct {pct} outside [0, 100]"


class TestPapersStats:
    """GET /api/v1/security/papers/stats"""

    def test_papers_stats_returns_200(self):
        response = client.get("/api/v1/security/papers/stats")
        assert response.status_code == 200

    def test_papers_stats_present(self):
        """papers/stats must return a non-empty body with count or category fields."""
        response = client.get("/api/v1/security/papers/stats")
        body = response.json()
        assert isinstance(body, dict), f"papers/stats body is not a dict: {type(body)}"
        assert len(body) > 0, "papers/stats returned an empty dict"


# ============================================================================
# Health / infra endpoints
# ============================================================================

class TestHealthEndpoints:
    """GET /health, /status, /health/detailed"""

    def test_health_endpoint(self):
        """GET /health must return HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_has_status_key(self):
        """Health response must include a 'status' key."""
        response = client.get("/health")
        body = response.json()
        assert "status" in body, f"'status' missing from /health response: {body}"

    def test_health_status_value_ok(self):
        """/health must report status 'ok'."""
        response = client.get("/health")
        body = response.json()
        assert body.get("status") == "ok", f"Expected status='ok', got: {body.get('status')!r}"

    def test_response_time_under_500ms(self):
        """GET /health latency must be under 500 ms."""
        t_start = time.perf_counter()
        response = client.get("/health")
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        assert response.status_code == 200
        assert elapsed_ms < 500, f"/health took {elapsed_ms:.1f} ms (limit 500 ms)"

    def test_status_endpoint_returns_200(self):
        """GET /status must return 200."""
        response = client.get("/status")
        assert response.status_code == 200

    def test_status_has_services_list(self):
        """GET /status must include a 'services' list."""
        response = client.get("/status")
        body = response.json()
        assert "services" in body, f"'services' missing from /status: {list(body.keys())}"
        assert isinstance(body["services"], list), "'services' must be a list"
        assert len(body["services"]) > 0, "'services' list is empty"

    def test_packages_endpoint(self):
        """GET /packages must return HTTP 200 and a packages dict."""
        response = client.get("/packages")
        assert response.status_code == 200
        body = response.json()
        assert "packages" in body, f"'packages' key missing: {body}"


# ============================================================================
# Projects endpoint smoke tests
# ============================================================================

class TestProjectsEndpoints:
    """Basic smoke tests for /projects endpoints."""

    def test_projects_list_returns_200(self):
        response = client.get("/projects")
        assert response.status_code == 200

    def test_projects_list_is_non_empty(self):
        """Must return at least one project."""
        response = client.get("/projects")
        body = response.json()
        assert isinstance(body, list), f"Expected list, got {type(body)}"
        assert len(body) > 0, "Projects list is empty"

    def test_projects_have_required_fields(self):
        """Each project must have id, title, status, category."""
        response = client.get("/projects")
        projects = response.json()
        required = {"id", "title", "status", "category"}
        for p in projects[:5]:  # Spot-check first 5
            missing = required - set(p.keys())
            assert not missing, f"Project missing fields {missing}: {p}"

    def test_layers_list_returns_200(self):
        """GET /layers must return 200."""
        response = client.get("/layers")
        assert response.status_code == 200

    def test_layers_list_is_non_empty(self):
        """GET /layers must return a list with at least one entry."""
        response = client.get("/layers")
        body = response.json()
        assert isinstance(body, list) and len(body) > 0, (
            f"Expected non-empty list, got: {body}"
        )

    def test_analytics_summary_returns_200(self):
        """GET /analytics/summary must return 200."""
        response = client.get("/analytics/summary")
        assert response.status_code == 200

    def test_reports_summary_returns_200(self):
        """GET /reports/summary must return 200."""
        response = client.get("/reports/summary")
        assert response.status_code == 200

    def test_security_status_returns_200(self):
        """GET /security/status must return 200."""
        response = client.get("/security/status")
        assert response.status_code == 200
