"""
test_sbom_generator.py — pytest tests for qc-classical-security-lab/src/sbom_generator.py.

Covers:
  - SBOMGenerator instantiation.
  - generate_sbom() returns a CycloneDX 1.4 dict with 'components' key.
  - Each SBOM component has name, version, type, and purl fields.
  - generate_cbom() returns valid CycloneDX 1.6 JSON (serialisable).
  - Each CBOM component has 'cryptoProperties' with algorithm and
    quantumSafe fields.
  - RSA components in CBOM have quantumSafe=False.
  - At least one quantum-safe component exists in the CBOM.
  - quantum_risk_report() returns a dict with 'components' and 'summary'.
  - Risk report identifies CRITICAL-risk packages (RSA/ECDSA).
  - The SBOM and CBOM are non-empty (registry covers 29 layers).

conftest.py already inserted src/ into sys.path.
"""
import json
import pytest

# conftest.py already inserted src/ into sys.path
from sbom_generator import SBOMGenerator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def generator() -> SBOMGenerator:
    return SBOMGenerator()


@pytest.fixture(scope="module")
def sbom(generator) -> dict:
    return generator.generate_sbom()


@pytest.fixture(scope="module")
def cbom(generator) -> dict:
    return generator.generate_cbom()


@pytest.fixture(scope="module")
def risk_report(generator) -> dict:
    return generator.quantum_risk_report()


# ---------------------------------------------------------------------------
# SBOMGenerator instantiation
# ---------------------------------------------------------------------------

class TestSBOMGeneratorInit:
    def test_instantiation(self):
        gen = SBOMGenerator()
        assert gen is not None

    def test_has_generate_sbom(self):
        gen = SBOMGenerator()
        assert callable(getattr(gen, "generate_sbom", None))

    def test_has_generate_cbom(self):
        gen = SBOMGenerator()
        assert callable(getattr(gen, "generate_cbom", None))

    def test_has_quantum_risk_report(self):
        gen = SBOMGenerator()
        assert callable(getattr(gen, "quantum_risk_report", None))


# ---------------------------------------------------------------------------
# generate_sbom() — CycloneDX 1.4 structure
# ---------------------------------------------------------------------------

class TestGenerateSBOM:
    def test_returns_dict(self, sbom):
        assert isinstance(sbom, dict)

    def test_has_components_key(self, sbom):
        assert "components" in sbom, "SBOM must have a 'components' key"

    def test_components_is_nonempty_list(self, sbom):
        assert isinstance(sbom["components"], list)
        assert len(sbom["components"]) > 0, "SBOM should contain at least one component"

    def test_each_component_has_name(self, sbom):
        for comp in sbom["components"]:
            assert "name" in comp, f"Component missing 'name': {comp}"

    def test_each_component_has_version(self, sbom):
        for comp in sbom["components"]:
            assert "version" in comp, f"Component missing 'version': {comp}"

    def test_each_component_has_type(self, sbom):
        for comp in sbom["components"]:
            assert "type" in comp, f"Component missing 'type': {comp}"

    def test_each_component_type_is_library(self, sbom):
        for comp in sbom["components"]:
            assert comp["type"] == "library", (
                f"Expected 'library', got '{comp['type']}' for {comp.get('name')}"
            )

    def test_each_component_has_purl(self, sbom):
        for comp in sbom["components"]:
            assert "purl" in comp, f"Component missing 'purl': {comp.get('name')}"
            assert comp["purl"].startswith("pkg:"), (
                f"purl should start with 'pkg:' — got '{comp['purl']}'"
            )

    def test_sbom_is_json_serialisable(self, sbom):
        try:
            serialised = json.dumps(sbom)
        except (TypeError, ValueError) as exc:
            pytest.fail(f"SBOM is not JSON-serialisable: {exc}")
        assert len(serialised) > 100

    def test_covers_many_components(self, sbom):
        """29-layer stack should produce a substantial component list."""
        assert len(sbom["components"]) >= 10, (
            f"Expected ≥10 components for 29-layer stack, got {len(sbom['components'])}"
        )

    def test_components_have_properties(self, sbom):
        """Each component should have a 'properties' list (carries layer_id etc.)."""
        for comp in sbom["components"]:
            assert "properties" in comp, f"Component {comp.get('name')} missing 'properties'"
            assert isinstance(comp["properties"], list)


# ---------------------------------------------------------------------------
# generate_cbom() — CycloneDX 1.6 CBOM structure
# ---------------------------------------------------------------------------

class TestGenerateCBOM:
    def test_returns_dict(self, cbom):
        assert isinstance(cbom, dict)

    def test_is_json_serialisable(self, cbom):
        try:
            serialised = json.dumps(cbom)
        except (TypeError, ValueError) as exc:
            pytest.fail(f"CBOM is not JSON-serialisable: {exc}")
        assert len(serialised) > 100

    def test_has_components_key(self, cbom):
        assert "components" in cbom

    def test_components_nonempty(self, cbom):
        assert len(cbom["components"]) > 0

    def test_spec_version_1_6(self, cbom):
        assert cbom.get("specVersion") == "1.6", (
            f"Expected specVersion '1.6', got '{cbom.get('specVersion')}'"
        )

    def test_bom_format_cyclonedx(self, cbom):
        assert cbom.get("bomFormat") == "CycloneDX"

    def test_each_component_has_crypto_properties(self, cbom):
        for comp in cbom["components"]:
            assert "cryptoProperties" in comp, (
                f"CBOM component '{comp.get('name')}' missing 'cryptoProperties'"
            )

    def test_crypto_properties_has_quantum_safe(self, cbom):
        for comp in cbom["components"]:
            cp = comp["cryptoProperties"]
            assert "quantumSafe" in cp, (
                f"cryptoProperties for '{comp.get('name')}' missing 'quantumSafe'"
            )
            assert isinstance(cp["quantumSafe"], bool)

    def test_crypto_properties_has_algorithm_name(self, cbom):
        for comp in cbom["components"]:
            cp = comp["cryptoProperties"]
            assert "algorithmProperties" in cp
            assert "name" in cp["algorithmProperties"]

    def test_rsa_components_not_quantum_safe(self, cbom):
        """Any component whose algorithm contains RSA should be quantumSafe=False."""
        rsa_comps = [
            c for c in cbom["components"]
            if "RSA" in c["cryptoProperties"]["algorithmProperties"]["name"].upper()
        ]
        assert rsa_comps, "CBOM should include at least one RSA component"
        for comp in rsa_comps:
            assert comp["cryptoProperties"]["quantumSafe"] is False, (
                f"RSA component '{comp['name']}' should have quantumSafe=False"
            )

    def test_at_least_one_quantum_safe_component(self, cbom):
        """The 29-layer stack contains AES-256, SHA-512, etc. — some are quantum-safe."""
        safe = [c for c in cbom["components"] if c["cryptoProperties"]["quantumSafe"] is True]
        assert safe, "CBOM should contain at least one quantum-safe component"

    def test_has_metadata(self, cbom):
        assert "metadata" in cbom

    def test_has_serial_number(self, cbom):
        assert "serialNumber" in cbom
        assert cbom["serialNumber"].startswith("urn:uuid:")


# ---------------------------------------------------------------------------
# quantum_risk_report()
# ---------------------------------------------------------------------------

class TestQuantumRiskReport:
    def test_returns_dict(self, risk_report):
        assert isinstance(risk_report, dict)

    def test_has_components_key(self, risk_report):
        assert "components" in risk_report

    def test_components_nonempty(self, risk_report):
        assert len(risk_report["components"]) > 0

    def test_has_summary_key(self, risk_report):
        assert "summary" in risk_report

    def test_summary_has_critical(self, risk_report):
        assert "CRITICAL" in risk_report["summary"]

    def test_summary_has_all_risk_levels(self, risk_report):
        for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            assert level in risk_report["summary"], f"Summary missing risk level '{level}'"

    def test_each_component_has_quantum_risk(self, risk_report):
        valid_risks = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        for comp in risk_report["components"]:
            assert "quantum_risk" in comp, f"Component {comp.get('name')} missing 'quantum_risk'"
            assert comp["quantum_risk"] in valid_risks

    def test_rsa_components_are_critical(self, risk_report):
        """RSA is broken by Shor's → CRITICAL risk."""
        rsa_comps = [
            c for c in risk_report["components"]
            if "RSA" in c.get("crypto_algorithm", "").upper()
               and not any(pqc in c.get("crypto_algorithm", "")
                           for pqc in ("ML-KEM", "ML-DSA", "KYBER"))
        ]
        assert rsa_comps, "Risk report should include at least one RSA component"
        for comp in rsa_comps:
            assert comp["quantum_risk"] == "CRITICAL", (
                f"RSA component '{comp['name']}' should be CRITICAL risk, "
                f"got '{comp['quantum_risk']}'"
            )

    def test_total_unique_packages_positive(self, risk_report):
        assert risk_report.get("total_unique_packages", 0) > 0

    def test_components_sorted_critical_first(self, risk_report):
        """Report should put CRITICAL items before LOW."""
        risks = [c["quantum_risk"] for c in risk_report["components"]]
        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        ordered = sorted(risks, key=lambda r: order.get(r, 9))
        assert risks == ordered, "Risk report components should be sorted CRITICAL → LOW"

    def test_each_component_has_migration_priority(self, risk_report):
        valid = {"P0", "P1", "P2", "P3"}
        for comp in risk_report["components"]:
            assert "migration_priority" in comp
            assert comp["migration_priority"] in valid

    def test_each_component_has_breaking_algorithm(self, risk_report):
        for comp in risk_report["components"]:
            assert "breaking_algorithm" in comp
            assert isinstance(comp["breaking_algorithm"], str)
