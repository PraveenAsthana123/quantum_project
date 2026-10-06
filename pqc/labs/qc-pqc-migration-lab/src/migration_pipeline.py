"""
PQC Migration Pipeline — 7-Stage Enterprise Crypto Migration Framework
Implements NIST SP 800-208, CISA PQC Migration Guidance, and CNSA 2.0 recommendations.

Stages:
  1. DISCOVERY          — scan for classical crypto usage
  2. CRYPTO INVENTORY   — CBOM (Cryptographic Bill of Materials)
  3. DATA CLASSIFICATION — sensitivity + retention
  4. DEPENDENCY MAPPING — protocol stack dependencies
  5. QUANTUM RISK        — CRQC threat timeline scoring
  6. PROTOCOL ASSESSMENT — migration complexity per protocol
  7. ALGORITHM SELECTION — NIST-approved PQC replacement
"""

import json
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
from datetime import datetime


# ─── Enumerations ────────────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"


class MigrationStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    TESTING     = "TESTING"
    COMPLETED   = "COMPLETED"


class DataSensitivity(str, Enum):
    TOP_SECRET  = "TOP_SECRET"
    CONFIDENTIAL= "CONFIDENTIAL"
    INTERNAL    = "INTERNAL"
    PUBLIC      = "PUBLIC"


# ─── Data models ─────────────────────────────────────────────────────────────

@dataclass
class CryptoAsset:
    """A single cryptographic asset discovered in the enterprise."""
    asset_id: str
    name: str
    algorithm: str                   # e.g. "RSA-2048", "ECDSA-P256"
    key_size: int                    # bits
    usage: str                       # "TLS cert", "JWT signing", etc.
    location: str                    # service / tier
    expiry: Optional[str]            # ISO date or None
    dependents: List[str] = field(default_factory=list)
    data_sensitivity: DataSensitivity = DataSensitivity.INTERNAL
    data_retention_years: int = 3
    notes: str = ""

    # populated by pipeline stages
    cbom_entry: Dict[str, Any] = field(default_factory=dict)
    risk_score: int = 0
    risk_level: RiskLevel = RiskLevel.LOW
    recommended_replacement: str = ""
    migration_status: MigrationStatus = MigrationStatus.NOT_STARTED
    migration_priority: int = 99
    protocol_assessment: Dict[str, Any] = field(default_factory=dict)
    algorithm_selection: Dict[str, Any] = field(default_factory=dict)


# ─── Stage helpers ────────────────────────────────────────────────────────────

# Known vulnerable algorithms (CRQC breaks these via Shor's / Grover's)
SHOR_VULNERABLE = {
    "RSA-512", "RSA-1024", "RSA-2048", "RSA-3072", "RSA-4096",
    "ECDSA-P256", "ECDSA-P384", "ECDSA-P521",
    "ECDH-P256", "ECDH-P384", "ECDH-X25519",
    "DH-1024", "DH-2048", "DH-3072",
    "EdDSA-Ed25519", "EdDSA-Ed448",
    "DSA-1024", "DSA-2048",
}

GROVER_WEAKENED = {
    "AES-128",   # Grover halves effective bits → AES-128 ≈ 64-bit security
    "SHA-256",   # collision-finding weakened
    "HMAC-SHA1", "MD5",
}

QUANTUM_SAFE_ALREADY = {
    "AES-256", "AES-256-GCM", "AES-256-CBC",
    "SHA-384", "SHA-512", "SHA3-256", "SHA3-512",
    "HMAC-SHA256", "HMAC-SHA384",
    "ML-KEM-768", "ML-KEM-1024",
    "ML-DSA-65", "ML-DSA-87",
    "SLH-DSA-128s", "SLH-DSA-256s",
    "Falcon-512", "Falcon-1024",
}

# PQC replacement map
REPLACEMENT_MAP = {
    "RSA-2048":    "ML-DSA-65 (FIPS 204) for signatures, ML-KEM-768 (FIPS 203) for KEM",
    "RSA-4096":    "ML-DSA-87 (FIPS 204) or SLH-DSA-256s for signatures",
    "ECDSA-P256":  "ML-DSA-65 (FIPS 204)",
    "ECDSA-P384":  "ML-DSA-65 (FIPS 204)",
    "ECDH-P256":   "ML-KEM-768 (FIPS 203) + X25519 hybrid",
    "ECDH-X25519": "ML-KEM-768 (FIPS 203) + X25519 hybrid",
    "DH-2048":     "ML-KEM-768 (FIPS 203) for key agreement",
    "DH-3072":     "ML-KEM-1024 (FIPS 203) for key agreement",
    "AES-128":     "AES-256 (double key size; Grover-resistant)",
    "EdDSA-Ed25519": "ML-DSA-65 (FIPS 204)",
    "DSA-1024":    "ML-DSA-44 (FIPS 204) minimum",
}

# Migration complexity per algorithm
COMPLEXITY = {
    "RSA-2048":    ("HIGH",   "Many libraries/protocols embed RSA deeply"),
    "RSA-4096":    ("MEDIUM", "Smaller footprint than RSA-2048 typically"),
    "ECDSA-P256":  ("MEDIUM", "Well-understood migration path to ML-DSA"),
    "DH-2048":     ("HIGH",   "IKEv2/VPN protocol changes needed"),
    "AES-128":     ("LOW",    "Key rotation only, no protocol change"),
    "EdDSA-Ed25519": ("MEDIUM", "SSH / code signing paths to update"),
}


# ─── Pipeline stages ──────────────────────────────────────────────────────────

class Stage1Discovery:
    """Scan for classical crypto usage across the asset inventory."""

    def run(self, assets: List[CryptoAsset]) -> Dict[str, Any]:
        findings = []
        for a in assets:
            vulnerable = a.algorithm in SHOR_VULNERABLE
            weakened   = a.algorithm in GROVER_WEAKENED
            safe       = a.algorithm in QUANTUM_SAFE_ALREADY
            status = "VULNERABLE" if vulnerable else \
                     "WEAKENED" if weakened else \
                     "QUANTUM_SAFE" if safe else "UNKNOWN"
            findings.append({
                "asset_id": a.asset_id,
                "algorithm": a.algorithm,
                "status": status,
                "location": a.location,
            })

        summary = {
            "total_assets":    len(assets),
            "vulnerable":      sum(1 for f in findings if f["status"] == "VULNERABLE"),
            "weakened":        sum(1 for f in findings if f["status"] == "WEAKENED"),
            "quantum_safe":    sum(1 for f in findings if f["status"] == "QUANTUM_SAFE"),
            "unknown":         sum(1 for f in findings if f["status"] == "UNKNOWN"),
        }
        return {"stage": "DISCOVERY", "findings": findings, "summary": summary}


class Stage2CBOMInventory:
    """Build a Cryptographic Bill of Materials (CBOM)."""

    _CBOM_SCHEMA_VERSION = "1.4"  # CycloneDX CBOM 1.4

    def run(self, assets: List[CryptoAsset]) -> Dict[str, Any]:
        components = []
        for a in assets:
            entry = {
                "bom-ref":      a.asset_id,
                "type":         "cryptographic-asset",
                "name":         a.name,
                "cryptoProperties": {
                    "assetType":     "algorithm",
                    "algorithmProperties": {
                        "primitive":     self._primitive(a.algorithm),
                        "parameterSetIdentifier": str(a.key_size),
                        "classicalSecurityLevel": self._classical_level(a.algorithm, a.key_size),
                        "nistQuantumSecurityLevel": self._quantum_level(a.algorithm),
                        "cryptoFunctions": self._functions(a.algorithm),
                    },
                },
                "usage":        a.usage,
                "location":     a.location,
                "expiry":       a.expiry,
                "quantumSafe":  a.algorithm in QUANTUM_SAFE_ALREADY,
            }
            a.cbom_entry = entry
            components.append(entry)

        return {
            "stage":      "CBOM_INVENTORY",
            "schemaVersion": self._CBOM_SCHEMA_VERSION,
            "serialNumber": "urn:cbom:" + hex(int(time.time()))[2:],
            "components": components,
        }

    @staticmethod
    def _primitive(alg: str) -> str:
        if "RSA" in alg or "DSA" in alg or "ECDSA" in alg:  return "signature"
        if "DH" in alg or "ECDH" in alg or "KEM" in alg:   return "key-agree"
        if "AES" in alg:                                      return "ae"
        return "other"

    @staticmethod
    def _classical_level(alg: str, bits: int) -> int:
        """Bits of classical security."""
        if "RSA" in alg or "DH" in alg: return bits // 2   # sub-exp factor
        return bits

    @staticmethod
    def _quantum_level(alg: str) -> int:
        """NIST quantum security level (0 = broken by CRQC)."""
        if alg in SHOR_VULNERABLE: return 0
        if alg in GROVER_WEAKENED: return 1   # Grover halved
        levels = {"ML-KEM-512":1,"ML-KEM-768":3,"ML-KEM-1024":5,
                  "ML-DSA-44":2,"ML-DSA-65":3,"ML-DSA-87":5,
                  "AES-256":3,"AES-256-GCM":3}
        return levels.get(alg, 0)

    @staticmethod
    def _functions(alg: str) -> List[str]:
        if "DSA" in alg or "RSA" in alg: return ["sign","verify"]
        if "DH" in alg or "ECDH" in alg: return ["keyAgreement"]
        if "AES" in alg: return ["encrypt","decrypt"]
        return []


class Stage3DataClassification:
    """Classify data sensitivity and determine harvest-now-decrypt-later risk."""

    # Risk amplifier when HNDL risk is considered
    RETENTION_RISK_THRESHOLD = 5   # years — if data must stay secret > this, CRITICAL

    def run(self, assets: List[CryptoAsset]) -> Dict[str, Any]:
        classified = []
        for a in assets:
            hndl_risk = (a.data_retention_years >= self.RETENTION_RISK_THRESHOLD
                         and a.algorithm in SHOR_VULNERABLE)
            urgency = "IMMEDIATE" if hndl_risk else \
                      "HIGH" if a.data_sensitivity in (DataSensitivity.TOP_SECRET,
                                                        DataSensitivity.CONFIDENTIAL) else \
                      "MEDIUM"
            entry = {
                "asset_id":           a.asset_id,
                "sensitivity":        a.data_sensitivity.value,
                "retention_years":    a.data_retention_years,
                "hndl_risk":          hndl_risk,
                "migration_urgency":  urgency,
            }
            classified.append(entry)

        return {"stage": "DATA_CLASSIFICATION", "classifications": classified}


class Stage4DependencyMapping:
    """Map protocol-layer dependencies for each asset."""

    _PROTOCOL_LAYERS = {
        "TLS":       ["Application", "Session", "Transport"],
        "SSH":       ["Application", "Session", "Transport"],
        "IKEv2/VPN": ["Network", "Transport"],
        "JWT/OAuth": ["Application"],
        "S/MIME":    ["Application"],
        "Code Sign": ["Application", "CI/CD"],
        "DB Encrypt":["Data", "Application"],
        "PKI/CA":    ["Infrastructure"],
    }

    def run(self, assets: List[CryptoAsset]) -> Dict[str, Any]:
        mappings = []
        for a in assets:
            proto = self._infer_protocol(a)
            layers = self._PROTOCOL_LAYERS.get(proto, ["Unknown"])
            deps = a.dependents + self._synthetic_deps(a)
            entry = {
                "asset_id":     a.asset_id,
                "protocol":     proto,
                "layers":       layers,
                "dependents":   deps,
                "dep_count":    len(deps),
                "cross_team":   len(deps) > 5,
            }
            mappings.append(entry)

        return {"stage": "DEPENDENCY_MAPPING", "mappings": mappings}

    @staticmethod
    def _infer_protocol(a: CryptoAsset) -> str:
        u = a.usage.lower()
        if "tls" in u or "cert" in u or "ssl" in u: return "TLS"
        if "jwt" in u or "oauth" in u or "signing key" in u: return "JWT/OAuth"
        if "vpn" in u or "ikev" in u or "ipsec" in u: return "IKEv2/VPN"
        if "ssh" in u or "host key" in u: return "SSH"
        if "code sign" in u or "ci/cd" in u: return "Code Sign"
        if "database" in u or "db" in u: return "DB Encrypt"
        if "s/mime" in u or "email" in u: return "S/MIME"
        return "PKI/CA"

    @staticmethod
    def _synthetic_deps(a: CryptoAsset) -> List[str]:
        """Realistic synthetic dependent services based on asset type."""
        dep_map = {
            "JWT/OAuth":    ["auth-service", "api-gateway", "user-service",
                             "billing-service"] + [f"micro-svc-{i}" for i in range(1, 8)],
            "TLS":          ["nginx-lb", "cdn-origin", "health-check"],
            "IKEv2/VPN":    ["vpn-concentrator", "radius-server", "firewalls"],
            "Code Sign":    ["ci-pipeline", "artifact-registry", "deploy-agent"],
            "DB Encrypt":   ["hr-db", "finance-db", "audit-log"],
        }
        u = a.usage.lower()
        for key, deps in dep_map.items():
            if key.lower().split("/")[0] in u:
                return deps
        return []


class Stage5QuantumRiskAssessment:
    """Score each asset against CRQC threat timeline."""

    # NIST / Gartner CRQC timeline estimate
    CRQC_YEAR_CONSERVATIVE = 2035
    CRQC_YEAR_OPTIMISTIC   = 2030
    CURRENT_YEAR           = 2025

    # Scoring weights
    _W_ALGO     = 40   # algorithm vulnerability
    _W_HNDL     = 25   # harvest-now-decrypt-later window
    _W_IMPACT   = 20   # data sensitivity
    _W_TIMELINE = 15   # expiry vs CRQC window

    def run(self, assets: List[CryptoAsset],
            classifications: List[Dict]) -> Dict[str, Any]:
        cls_map = {c["asset_id"]: c for c in classifications}
        scored = []
        for a in assets:
            score = self._score(a, cls_map.get(a.asset_id, {}))
            a.risk_score = score
            a.risk_level = (RiskLevel.CRITICAL if score >= 80 else
                            RiskLevel.HIGH     if score >= 60 else
                            RiskLevel.MEDIUM   if score >= 40 else
                            RiskLevel.LOW)
            a.migration_priority = self._priority(a.risk_level, a.dependents)
            scored.append({
                "asset_id":   a.asset_id,
                "algorithm":  a.algorithm,
                "score":      score,
                "risk_level": a.risk_level.value,
                "priority":   a.migration_priority,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return {"stage": "QUANTUM_RISK", "scored_assets": scored}

    def _score(self, a: CryptoAsset, cls: Dict) -> int:
        s = 0
        # Algorithm vulnerability
        if a.algorithm in SHOR_VULNERABLE: s += self._W_ALGO
        elif a.algorithm in GROVER_WEAKENED: s += self._W_ALGO // 2

        # HNDL window
        if cls.get("hndl_risk"): s += self._W_HNDL
        elif a.data_retention_years >= 3: s += self._W_HNDL // 2

        # Data sensitivity
        impact_score = {DataSensitivity.TOP_SECRET: 20, DataSensitivity.CONFIDENTIAL: 16,
                        DataSensitivity.INTERNAL: 8, DataSensitivity.PUBLIC: 2}
        s += impact_score.get(a.data_sensitivity, 8)

        # Expiry before CRQC
        if a.expiry:
            try:
                exp_year = int(a.expiry[:4])
                if exp_year <= self.CRQC_YEAR_OPTIMISTIC: s += self._W_TIMELINE
                elif exp_year <= self.CRQC_YEAR_CONSERVATIVE: s += self._W_TIMELINE // 2
            except ValueError:
                pass

        return min(s, 100)

    @staticmethod
    def _priority(rl: RiskLevel, deps: List[str]) -> int:
        base = {RiskLevel.CRITICAL: 1, RiskLevel.HIGH: 2,
                RiskLevel.MEDIUM: 3, RiskLevel.LOW: 4}[rl]
        if len(deps) > 20: base = max(1, base - 1)   # high dep count → higher priority
        return base


class Stage6ProtocolAssessment:
    """Evaluate the migration path complexity for each protocol."""

    _PROTOCOL_DETAILS = {
        "TLS": {
            "pqc_support":    "Draft RFCs + OQS-OpenSSL provider (OpenSSL 3.4+)",
            "hybrid_mode":    "X25519+ML-KEM-768 (code point 0x11EC, IETF draft)",
            "cert_migration": "Replace RSA/ECDSA certs with ML-DSA-65 X.509v3",
            "timeline_months": 12,
            "rollback":       "Dual-stack classical + PQC for 6-month overlap",
            "risks":          ["Client library compatibility", "CA issuance lag"],
        },
        "JWT/OAuth": {
            "pqc_support":    "IETF draft-ietf-jose-fully-specified-algorithms",
            "hybrid_mode":    "Dual-token issuance (RS256 + ML-DSA-65) during transition",
            "cert_migration": "New JWKS endpoint with ML-DSA-65 keys",
            "timeline_months": 6,
            "rollback":       "Keep RS256 JWKS active until all clients updated",
            "risks":          ["Token size increase 4.8KB", "Client JWT library support"],
        },
        "IKEv2/VPN": {
            "pqc_support":    "RFC 9370 (IKEv2 PQC), StrongSwan 5.9.8+ ML-KEM",
            "hybrid_mode":    "X25519+ML-KEM-768 IKEv2 KEX (RFC 9370 additional KEX)",
            "cert_migration": "IKEv2 auth: ML-DSA-65 replacing RSA/ECDSA",
            "timeline_months": 18,
            "rollback":       "Maintain IKEv2 classical profile as fallback IKE_SA",
            "risks":          ["VPN client firmware updates", "Performance on embedded HW"],
        },
        "SSH": {
            "pqc_support":    "OpenSSH 9.0+ (sntrup761x25519-sha512 default)",
            "hybrid_mode":    "mlkem768x25519-sha256 (IETF draft-ietf-sshm-hybrid-kex)",
            "cert_migration": "ssh-mldsa65 host keys replacing ssh-ed25519",
            "timeline_months": 9,
            "rollback":       "Dual host keys (Ed25519 + ML-DSA-65) during rollout",
            "risks":          ["known_hosts re-acceptance", "Older SSH client versions"],
        },
        "Code Sign": {
            "pqc_support":    "Sigstore + ML-DSA-65 (RFC draft), MS Authenticode roadmap",
            "hybrid_mode":    "Dual-sign artifacts (RSA-4096 + ML-DSA-87)",
            "cert_migration": "Code-signing CA migrates to ML-DSA-87",
            "timeline_months": 24,
            "rollback":       "Keep RSA-4096 sig in artifact for legacy OS verification",
            "risks":          ["OS kernel signature verification not yet PQC"],
        },
        "DB Encrypt": {
            "pqc_support":    "AES-256 upgrade (no protocol change)",
            "hybrid_mode":    "N/A — symmetric encryption, not key-agreement",
            "cert_migration": "Key rotation to AES-256 master keys",
            "timeline_months": 3,
            "rollback":       "Dual-key decryption during rotation window",
            "risks":          ["Performance impact of re-encryption"],
        },
    }

    def run(self, assets: List[CryptoAsset],
            mappings: List[Dict]) -> Dict[str, Any]:
        map_lookup = {m["asset_id"]: m for m in mappings}
        assessments = []
        for a in assets:
            proto = map_lookup.get(a.asset_id, {}).get("protocol", "Unknown")
            detail = self._PROTOCOL_DETAILS.get(proto, {
                "pqc_support": "Research needed",
                "hybrid_mode": "TBD",
                "cert_migration": "TBD",
                "timeline_months": 24,
                "rollback": "TBD",
                "risks": [],
            })
            a.protocol_assessment = {"protocol": proto, **detail}
            assessments.append({"asset_id": a.asset_id, "protocol": proto, **detail})

        return {"stage": "PROTOCOL_ASSESSMENT", "assessments": assessments}


class Stage7AlgorithmSelection:
    """Recommend the specific PQC algorithm and parameter set for each asset."""

    _SELECTION_RATIONALE = {
        "ML-DSA-65": (
            "NIST Level 3 (AES-192 equivalent). Recommended for most enterprise signing "
            "workloads. FIPS 204 (August 2024). Replaces ECDSA-P256 and RSA-2048."
        ),
        "ML-DSA-87": (
            "NIST Level 5 (AES-256 equivalent). Recommended for long-lived code-signing "
            "certificates and CA root keys. Replaces RSA-4096."
        ),
        "ML-KEM-768": (
            "NIST Level 3. Recommended for most TLS/VPN key agreement. "
            "FIPS 203 (August 2024). Hybrid X25519+ML-KEM-768 for transition."
        ),
        "AES-256": (
            "Grover's algorithm halves effective bits of AES-128 to 64-bit security. "
            "AES-256 retains 128-bit security under Grover — quantum-safe."
        ),
    }

    def run(self, assets: List[CryptoAsset]) -> Dict[str, Any]:
        selections = []
        for a in assets:
            replacement = REPLACEMENT_MAP.get(a.algorithm,
                                               "No standard replacement found — review manually")
            primary_algo = replacement.split(" ")[0] if replacement else ""
            rationale    = self._SELECTION_RATIONALE.get(primary_algo, "")
            migration_steps = self._migration_steps(a)
            a.recommended_replacement = replacement
            a.algorithm_selection = {
                "recommended":      replacement,
                "primary_algorithm": primary_algo,
                "rationale":        rationale,
                "fips_reference":   self._fips_ref(primary_algo),
                "migration_steps":  migration_steps,
            }
            selections.append({
                "asset_id":      a.asset_id,
                "current":       a.algorithm,
                "recommended":   replacement,
                "fips":          self._fips_ref(primary_algo),
                "steps":         len(migration_steps),
            })

        return {"stage": "ALGORITHM_SELECTION", "selections": selections}

    @staticmethod
    def _fips_ref(algo: str) -> str:
        refs = {
            "ML-KEM": "NIST FIPS 203 (August 2024)",
            "ML-DSA": "NIST FIPS 204 (August 2024)",
            "SLH-DSA":"NIST FIPS 205 (August 2024)",
            "AES-256":"NIST FIPS 197 (already quantum-safe at 256-bit)",
        }
        for k, v in refs.items():
            if k in algo: return v
        return "NIST SP 800-208 guidance"

    @staticmethod
    def _migration_steps(a: CryptoAsset) -> List[str]:
        proto = a.protocol_assessment.get("protocol", "")
        steps_by_proto = {
            "TLS": [
                "Deploy OQS-OpenSSL provider on load balancers",
                "Enable X25519+ML-KEM-768 in TLS config (hybrid KEX)",
                "Submit ML-DSA-65 CSRs to CA",
                "Deploy hybrid cert chain",
                "Monitor for classical-only client fallback",
                "Retire classical cipher suites after 6-month window",
            ],
            "JWT/OAuth": [
                "Generate ML-DSA-65 JWKS key pair",
                "Publish new JWKS endpoint with both keys",
                "Update token issuer to dual-sign",
                "Update 47 dependent microservices to accept ML-DSA-65",
                "Monitor RS256 usage metrics",
                "Retire RS256 key after grace period",
            ],
            "IKEv2/VPN": [
                "Upgrade StrongSwan/Libreswan to PQC-capable version",
                "Configure RFC 9370 additional KEX policy",
                "Push updated VPN client config to 3000+ endpoints",
                "Test split-tunnel and full-tunnel modes",
                "Update firewall rules for increased IKE payload sizes",
                "Retire DH-2048 IKE proposal after rollout",
            ],
            "DB Encrypt": [
                "Identify all AES-128 encrypted tablespaces",
                "Schedule re-encryption maintenance windows",
                "Update application connection strings to new key IDs",
                "Verify HR + Finance data re-encrypted before audit",
            ],
            "Code Sign": [
                "Request ML-DSA-87 code-signing cert from issuing CA",
                "Update CI/CD pipeline signing step",
                "Dual-sign releases (RSA-4096 + ML-DSA-87) for 12 months",
                "Update OS/deployment agent trust anchors",
                "Retire RSA-4096 signing cert after rollout",
            ],
        }
        return steps_by_proto.get(proto, ["Review migration approach", "Pilot PQC library",
                                          "Update configuration", "Test", "Deploy"])


# ─── Master pipeline ──────────────────────────────────────────────────────────

class MigrationPipeline:
    """Orchestrates all 7 stages of the PQC migration pipeline."""

    def __init__(self):
        self.stage1 = Stage1Discovery()
        self.stage2 = Stage2CBOMInventory()
        self.stage3 = Stage3DataClassification()
        self.stage4 = Stage4DependencyMapping()
        self.stage5 = Stage5QuantumRiskAssessment()
        self.stage6 = Stage6ProtocolAssessment()
        self.stage7 = Stage7AlgorithmSelection()

    def run_full_pipeline(self, assets: List[CryptoAsset]) -> Dict[str, Any]:
        t_start = time.perf_counter()
        results = {}

        print(f"\n{'='*68}")
        print(f"  PQC MIGRATION PIPELINE — {len(assets)} assets")
        print(f"  NIST SP 800-208 | CISA PQC Guidance | CNSA 2.0")
        print(f"{'='*68}")

        # Stage 1
        print(f"\n[STAGE 1] DISCOVERY")
        r1 = self.stage1.run(assets)
        results["stage1"] = r1
        s = r1["summary"]
        print(f"  Vulnerable (SHOR): {s['vulnerable']}")
        print(f"  Weakened (GROVER): {s['weakened']}")
        print(f"  Quantum-safe     : {s['quantum_safe']}")
        print(f"  Unknown          : {s['unknown']}")
        for f in r1["findings"]:
            flag = {"VULNERABLE":"[!]","WEAKENED":"[~]","QUANTUM_SAFE":"[✓]"}.get(f["status"],"[?]")
            print(f"    {flag} {f['asset_id']}: {f['algorithm']} @ {f['location']} → {f['status']}")

        # Stage 2
        print(f"\n[STAGE 2] CRYPTO INVENTORY / CBOM")
        r2 = self.stage2.run(assets)
        results["stage2"] = r2
        print(f"  CBOM schema: CycloneDX {r2['schemaVersion']}")
        print(f"  Serial     : {r2['serialNumber']}")
        for c in r2["components"]:
            ap = c["cryptoProperties"]["algorithmProperties"]
            print(f"    {c['bom-ref']}: {c['name']}"
                  f"  classical_bits={ap['classicalSecurityLevel']}"
                  f"  quantum_level={ap['nistQuantumSecurityLevel']}"
                  f"  safe={c['quantumSafe']}")

        # Stage 3
        print(f"\n[STAGE 3] DATA + BUSINESS CLASSIFICATION")
        r3 = self.stage3.run(assets)
        results["stage3"] = r3
        for c in r3["classifications"]:
            hndl = "HNDL-RISK" if c["hndl_risk"] else "no-hndl"
            print(f"    {c['asset_id']}: sensitivity={c['sensitivity']}"
                  f"  retention={c['retention_years']}yr"
                  f"  urgency={c['migration_urgency']}"
                  f"  [{hndl}]")

        # Stage 4
        print(f"\n[STAGE 4] DEPENDENCY MAPPING")
        r4 = self.stage4.run(assets)
        results["stage4"] = r4
        for m in r4["mappings"]:
            cross = "CROSS-TEAM" if m["cross_team"] else ""
            print(f"    {m['asset_id']}: protocol={m['protocol']}"
                  f"  layers={m['layers']}"
                  f"  deps={m['dep_count']}  {cross}")

        # Stage 5
        print(f"\n[STAGE 5] QUANTUM RISK ASSESSMENT")
        r5 = self.stage5.run(assets, r3["classifications"])
        results["stage5"] = r5
        print(f"  {'Asset':<25} {'Algorithm':<18} {'Score':>5} {'Risk':<10} {'Priority'}")
        print(f"  {'-'*68}")
        for s in r5["scored_assets"]:
            bar = "█" * (s["score"] // 10) + "░" * (10 - s["score"] // 10)
            print(f"  {s['asset_id']:<25} {s['algorithm']:<18} {s['score']:>5}"
                  f"  {s['risk_level']:<10} P{s['priority']}  {bar}")

        # Stage 6
        print(f"\n[STAGE 6] PROTOCOL ASSESSMENT")
        r6 = self.stage6.run(assets, r4["mappings"])
        results["stage6"] = r6
        for a in r6["assessments"]:
            print(f"    {a['asset_id']} [{a['protocol']}]")
            print(f"      PQC support  : {a['pqc_support']}")
            print(f"      Hybrid mode  : {a['hybrid_mode']}")
            print(f"      Timeline     : {a['timeline_months']} months")
            print(f"      Risks        : {', '.join(a['risks'][:2])}")

        # Stage 7
        print(f"\n[STAGE 7] ALGORITHM / PARAMETER SELECTION")
        r7 = self.stage7.run(assets)
        results["stage7"] = r7
        for s in r7["selections"]:
            print(f"    {s['asset_id']}")
            print(f"      Current     : {s['current']}")
            print(f"      Recommended : {s['recommended']}")
            print(f"      FIPS ref    : {s['fips']}")
            print(f"      Steps       : {s['steps']} migration steps defined")

        # Summary
        elapsed = (time.perf_counter() - t_start) * 1000
        print(f"\n{'='*68}")
        print(f"  PIPELINE COMPLETE — {elapsed:.1f} ms")
        print(f"  CRITICAL assets  : {sum(1 for a in assets if a.risk_level==RiskLevel.CRITICAL)}")
        print(f"  HIGH risk        : {sum(1 for a in assets if a.risk_level==RiskLevel.HIGH)}")
        print(f"  MEDIUM risk      : {sum(1 for a in assets if a.risk_level==RiskLevel.MEDIUM)}")
        print(f"  LOW risk         : {sum(1 for a in assets if a.risk_level==RiskLevel.LOW)}")

        priority_order = sorted(assets, key=lambda a: (a.migration_priority, -a.risk_score))
        print(f"\n  RECOMMENDED MIGRATION ORDER:")
        for i, a in enumerate(priority_order, 1):
            print(f"  {i}. [{a.risk_level.value:<8}] P{a.migration_priority}"
                  f"  {a.asset_id}  ({a.algorithm} → {a.recommended_replacement.split('(')[0].strip()})")
        print(f"{'='*68}")

        results["summary"] = {
            "total":    len(assets),
            "critical": sum(1 for a in assets if a.risk_level == RiskLevel.CRITICAL),
            "high":     sum(1 for a in assets if a.risk_level == RiskLevel.HIGH),
            "elapsed_ms": elapsed,
        }
        return results


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    """Demo with realistic enterprise assets."""
    assets = [
        CryptoAsset(
            asset_id="CERT-WEB-001",
            name="RSA-2048 server certificate (web tier)",
            algorithm="RSA-2048",
            key_size=2048,
            usage="TLS certificate for api.example.com",
            location="web-tier / nginx",
            expiry="2026-03-15",
            dependents=["nginx-lb", "cdn-origin", "api-gateway"],
            data_sensitivity=DataSensitivity.CONFIDENTIAL,
            data_retention_years=5,
            notes="Wildcard cert covering 12 subdomains",
        ),
        CryptoAsset(
            asset_id="KEY-AUTH-002",
            name="ECDSA P-256 JWT signing key (auth service)",
            algorithm="ECDSA-P256",
            key_size=256,
            usage="JWT signing key for OAuth 2.0 / OIDC",
            location="auth-service / Kubernetes secret",
            expiry=None,
            dependents=[f"micro-svc-{i}" for i in range(1, 48)],
            data_sensitivity=DataSensitivity.CONFIDENTIAL,
            data_retention_years=7,
            notes="Used in 47 microservices; rotated quarterly",
        ),
        CryptoAsset(
            asset_id="VPN-IKE-003",
            name="DH-2048 VPN IKEv2 (network tier)",
            algorithm="DH-2048",
            key_size=2048,
            usage="IKEv2 key agreement for corporate VPN",
            location="network-tier / StrongSwan",
            expiry="2028-01-01",
            dependents=["vpn-concentrator", "radius-server"],
            data_sensitivity=DataSensitivity.CONFIDENTIAL,
            data_retention_years=10,
            notes="3000+ employee endpoints; session keys renewed every 8h",
        ),
        CryptoAsset(
            asset_id="DB-ENC-004",
            name="AES-128 database encryption (HR + Finance)",
            algorithm="AES-128",
            key_size=128,
            usage="Database at-rest encryption (tablespace)",
            location="data-tier / Oracle TDE",
            expiry=None,
            dependents=["hr-db", "finance-db", "audit-log"],
            data_sensitivity=DataSensitivity.TOP_SECRET,
            data_retention_years=15,
            notes="HR + Finance data; Grover weakens to ~64-bit security",
        ),
        CryptoAsset(
            asset_id="CERT-CODE-005",
            name="RSA-4096 code signing certificate (CI/CD)",
            algorithm="RSA-4096",
            key_size=4096,
            usage="Code signing for release artifacts",
            location="ci-cd / Jenkins",
            expiry="2027-06-30",
            dependents=["ci-pipeline", "artifact-registry", "deploy-agent"],
            data_sensitivity=DataSensitivity.INTERNAL,
            data_retention_years=10,
            notes="Signed artifacts must be verifiable for 10 years",
        ),
    ]

    pipeline = MigrationPipeline()
    pipeline.run_full_pipeline(assets)


if __name__ == "__main__":
    main()
