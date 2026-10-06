"""
Defense Playbook — Per-Attack Mitigation Guide
===============================================
Maps every attack in the quantum attack lab to:
  - Immediate mitigation (action today)
  - Short-term fix (1–30 days)
  - Long-term solution (PQC migration timeline)
  - Monitoring metric
  - Compliance requirement addressed

Defensive Security Educational Lab — /mnt/deepa/quantum/qc-attack-lab/
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlaybookEntry:
    attack: str
    attack_type: str             # Classical / Quantum / AI
    threat_level: str            # CRITICAL / HIGH / MEDIUM
    immediate: str               # What to do RIGHT NOW (< 24 hours)
    short_term: str              # 1–30 days
    long_term: str               # PQC migration / architectural fix
    monitoring_metric: str       # What KPI/signal to track
    compliance: str              # Standard(s) addressed
    nist_pqc_migration: str      # NIST PQC algorithm to adopt
    references: list[str] = field(default_factory=list)

    def display(self):
        bar = "-" * 76
        threat_icons = {
            "CRITICAL": "[!!!] CRITICAL",
            "HIGH":     "[!! ] HIGH    ",
            "MEDIUM":   "[ ! ] MEDIUM  ",
        }
        print(f"\n{bar}")
        print(f"  {threat_icons.get(self.threat_level, self.threat_level)}  "
              f"{self.attack}  [{self.attack_type}]")
        print(bar)
        print(f"  IMMEDIATE (< 24h)  : {self.immediate}")
        print(f"  SHORT-TERM (1-30d) : {self.short_term}")
        print(f"  LONG-TERM (PQC)    : {self.long_term}")
        print(f"  MONITOR            : {self.monitoring_metric}")
        print(f"  COMPLIANCE         : {self.compliance}")
        print(f"  NIST PQC MIGRATION : {self.nist_pqc_migration}")
        if self.references:
            print(f"  REFERENCES         : {' | '.join(self.references)}")


# ---------------------------------------------------------------------------
# Playbook data
# ---------------------------------------------------------------------------

PLAYBOOK: list[PlaybookEntry] = [

    PlaybookEntry(
        attack="RSA Factoring Attack",
        attack_type="Classical + Quantum (Shor's)",
        threat_level="CRITICAL",
        immediate=(
            "1. Inventory all RSA keys ≤ 2048-bit in certificates, SSH, TLS, signing keys. "
            "2. Block/revoke any RSA-512/1024 keys immediately. "
            "3. Enable HSM-backed key storage — prevent key export."
        ),
        short_term=(
            "1. Replace RSA-2048 certificates with ECDSA P-256 or P-384 (short-term). "
            "2. Enforce RSA minimum key size = 3072 in PKI policy. "
            "3. Scan configs with 'grep -r rsa_key_bits' in Nginx/Apache/OpenSSH configs. "
            "4. Audit TLS cipher suites: disable RSA key exchange (not RSA auth)."
        ),
        long_term=(
            "1. Deploy CRYSTALS-Kyber (ML-KEM, NIST FIPS 203) for all key encapsulation. "
            "2. Hybrid mode: ML-KEM-768 + ECDHE-256 until ecosystem matures. "
            "3. Target: all internal services migrated by 2028, external by 2030. "
            "4. CNSA 2.0: ML-KEM-1024 for national security systems."
        ),
        monitoring_metric=(
            "% of active certificates using RSA < 3072; "
            "factoring attack alerts (IDS on small-N moduli); "
            "PQC migration progress dashboard (# keys migrated / total)"
        ),
        compliance=(
            "NIST SP 800-131A Rev.2 (key deprecation), "
            "NSA CNSA 2.0 (2022), "
            "FIPS 140-3 (HSM requirements), "
            "PCI DSS 4.0 (§6.2.4)"
        ),
        nist_pqc_migration=(
            "ML-KEM (CRYSTALS-Kyber) — NIST FIPS 203 (2024). "
            "Replaces all RSA key encapsulation. "
            "Available in: liboqs, BoringSSL, AWS-LC, OpenSSL 3.x (experimental)."
        ),
        references=[
            "NIST FIPS 203 (2024)",
            "NSA CNSA 2.0 Suite (2022)",
            "RFC 9180 (HPKE — hybrid KEM)",
        ],
    ),

    PlaybookEntry(
        attack="ECDSA Discrete Log Attack (Shor's)",
        attack_type="Quantum (Shor's)",
        threat_level="CRITICAL",
        immediate=(
            "1. Audit all ECDSA signing keys (code signing, document signing, TLS auth). "
            "2. Identify long-lived ECDSA keys (CA roots, hardware signing keys). "
            "3. Flag all keys with retention > 7 years for priority migration."
        ),
        short_term=(
            "1. Issue new TLS/code-signing certificates — use hybrid ECDSA + ML-DSA if supported. "
            "2. Update SSH config: 'HostKeyAlgorithms ecdsa-sha2-*' → add 'ssh-dilithium'. "
            "3. Review blockchain/DeFi integrations using secp256k1 — add quantum-safe layer."
        ),
        long_term=(
            "1. Migrate to ML-DSA (CRYSTALS-Dilithium, NIST FIPS 204) for all signatures. "
            "2. Alternatively: SLH-DSA (SPHINCS+, NIST FIPS 205) for stateless signing. "
            "3. Bitcoin/Ethereum: P2QRH addresses (BIP-360 proposal). "
            "4. X.509 PKI: OQS-based CA hierarchy."
        ),
        monitoring_metric=(
            "# ECDSA keys with retention > CRQC horizon; "
            "new certificate issuance rate using PQC algorithms; "
            "ECDH key exchange % in TLS session logs"
        ),
        compliance=(
            "NIST SP 800-208 (stateful hash-based signatures), "
            "NSA CNSA 2.0, "
            "FIPS 186-5 (ECDSA), "
            "ETSI TR 103 744 (quantum-safe migration)"
        ),
        nist_pqc_migration=(
            "ML-DSA (CRYSTALS-Dilithium) — NIST FIPS 204 (2024) for digital signatures. "
            "SLH-DSA (SPHINCS+) — NIST FIPS 205 (2024) for stateless high-assurance signing. "
            "FN-DSA (FALCON) — NIST FIPS 206 (2024) for compact signatures."
        ),
        references=[
            "NIST FIPS 204 (2024)",
            "NIST FIPS 205 (2024)",
            "Roetteler et al. (2017) ECDLP quantum resources",
        ],
    ),

    PlaybookEntry(
        attack="AES Brute Force (Grover's Algorithm)",
        attack_type="Quantum (Grover's)",
        threat_level="HIGH",
        immediate=(
            "1. Audit all symmetric key sizes — flag AES-128 endpoints for upgrade. "
            "2. For data encrypted today with AES-128 needing > 10yr secrecy: re-encrypt with AES-256 now. "
            "3. Disable 3DES, DES, RC4 immediately."
        ),
        short_term=(
            "1. Mandate AES-256 in all new encryption configurations (TLS, disk, DB). "
            "2. Update key derivation: PBKDF2-SHA256 → PBKDF2-SHA512 or Argon2id with 256-bit output. "
            "3. Enforce AES-256-GCM in TLS 1.3 cipher suite configuration."
        ),
        long_term=(
            "AES-256 is QUANTUM-SAFE per NIST (128-bit effective security after Grover's). "
            "1. Maintain AES-256 as the standard. No algorithm migration needed — only key-size migration. "
            "2. Review in 2030 as quantum hardware advances (Grover's AES-128 attack remains expensive)."
        ),
        monitoring_metric=(
            "% of encrypted data stores using AES-256 vs AES-128; "
            "TLS negotiated cipher suite distribution; "
            "key rotation frequency for high-value data"
        ),
        compliance=(
            "NIST SP 800-57 Part 1 Rev.5 (key management), "
            "FIPS 197 (AES), "
            "PCI DSS 4.0 §3.5.1 (strong cryptography), "
            "HIPAA §164.312(a)(2)(iv)"
        ),
        nist_pqc_migration=(
            "No algorithm change needed — upgrade key size to 256-bit. "
            "AES-256-GCM remains the NIST-recommended symmetric cipher for the quantum era."
        ),
        references=[
            "NIST SP 800-175B Rev.1 (2020)",
            "Grassl et al. (2016) AES quantum security",
            "Jaques & Schanck (2020) depth-efficient quantum AES circuits",
        ],
    ),

    PlaybookEntry(
        attack="Harvest Now, Decrypt Later (HNDL)",
        attack_type="Quantum (Future CRQC)",
        threat_level="CRITICAL",
        immediate=(
            "1. Enable Perfect Forward Secrecy (PFS) on ALL TLS endpoints NOW — "
            "   limits HNDL blast radius to per-session keys. "
            "2. Identify and classify long-lived encrypted archives (S3, tape, NAS). "
            "3. Disable static RSA key exchange (non-PFS TLS cipher suites)."
        ),
        short_term=(
            "1. Deploy hybrid PQC-TLS: ML-KEM-768 + X25519 in TLS 1.3 "
            "   (supported by Chrome 116+, Firefox 119+, Cloudflare). "
            "2. Re-encrypt highest-risk archives with AES-256 + ML-KEM protected keys. "
            "3. Implement TLS traffic logging to detect HNDL-style exfiltration."
        ),
        long_term=(
            "1. Full PQC deployment: ML-KEM-1024 for all key agreement by 2028. "
            "2. Retroactive data migration: identify all data needing >7yr confidentiality "
            "   and re-encrypt with PQC keys. "
            "3. HSM support for ML-KEM (Thales Luna, AWS CloudHSM roadmap). "
            "4. CNSA 2.0 requirement: ML-KEM-1024 for NSS by 2030."
        ),
        monitoring_metric=(
            "TLS session PFS adoption rate (must be 100%); "
            "ML-KEM deployment % across internal services; "
            "encrypted exfiltration volume anomalies (SIEM rule); "
            "data classified as 'long-retention + sensitive' re-encrypted count"
        ),
        compliance=(
            "NSA CNSA 2.0 (2022) — mandatory PQC timeline, "
            "CISA PQC Initiative (2022), "
            "OMB M-23-02 (US Federal — PQC migration by FY2035), "
            "GDPR Article 32 (appropriate technical measures)"
        ),
        nist_pqc_migration=(
            "ML-KEM-768 (NIST FIPS 203) in hybrid mode with X25519 immediately. "
            "ML-KEM-1024 for high-assurance / national security data. "
            "Reference implementation: CIRCL (Cloudflare), liboqs (Open Quantum Safe)."
        ),
        references=[
            "NSA CNSA 2.0 Advisory (2022)",
            "CISA Quantum Readiness (2023)",
            "OMB M-23-02 (2023)",
            "RFC 9180 (HPKE)",
        ],
    ),

    PlaybookEntry(
        attack="Man-in-the-Middle (Unauthenticated DH)",
        attack_type="Classical",
        threat_level="CRITICAL",
        immediate=(
            "1. Enforce certificate pinning for high-value endpoints. "
            "2. Enable HSTS (Strict-Transport-Security) with preloading. "
            "3. Audit network infrastructure for rogue ARP/BGP/DNS entries."
        ),
        short_term=(
            "1. Deploy mutual TLS (mTLS) for service-to-service communication. "
            "2. Implement DANE (DNS-based Authentication of Named Entities) for email. "
            "3. Use SIGMA-protocol or STS for all DH-based key exchanges."
        ),
        long_term=(
            "1. Full PKI migration to ML-DSA-signed certificates. "
            "2. Zero-trust architecture: never trust network position. "
            "3. Certificate Transparency (CT) log monitoring for fraudulent certs."
        ),
        monitoring_metric=(
            "ARP spoofing alerts; BGP prefix hijacking monitoring; "
            "TLS certificate validation failures; "
            "HSTS preload coverage %"
        ),
        compliance=(
            "NIST SP 800-52 Rev.2 (TLS guidelines), "
            "PCI DSS 4.0 §6.2.4, "
            "FIPS 140-3 §4.9.1 (key establishment)"
        ),
        nist_pqc_migration=(
            "Hybrid X25519+ML-KEM-768 in TLS 1.3 for key exchange. "
            "ML-DSA-signed TLS certificates for authentication. "
            "Both are needed: ML-KEM for confidentiality, ML-DSA for authentication."
        ),
        references=[
            "RFC 8446 §4.2.7 (TLS 1.3 key share)",
            "NIST SP 800-52 Rev.2",
        ],
    ),

    PlaybookEntry(
        attack="Timing Side-Channel Attack",
        attack_type="Classical (amplified by AI/Quantum)",
        threat_level="HIGH",
        immediate=(
            "1. Check OpenSSL/BoringSSL version — ensure RSA blinding enabled. "
            "2. Disable RSA_FLAG_NO_CONSTTIME in any custom crypto code. "
            "3. Run TVLA (Test Vector Leakage Assessment) on hardware crypto modules."
        ),
        short_term=(
            "1. Replace naive modular exponentiation with Montgomery ladder. "
            "2. Add jitter/noise to response times (carefully — may not be sufficient alone). "
            "3. Deploy constant-time crypto library: libsodium, HACL*, EverCrypt. "
            "4. Run automated timing analysis (tlsfuzzer, dudect)."
        ),
        long_term=(
            "1. Migrate to PQC algorithms designed with constant-time from ground up. "
            "2. Formal verification of timing properties (EasyCrypt, Jasmin). "
            "3. Hardware security modules with physical shielding for high-value keys."
        ),
        monitoring_metric=(
            "Response time variance per endpoint per operation type (< 0.1ms² target); "
            "TVLA T-statistic (must be < 4.5 for FIPS 140-3); "
            "automated timing test pass/fail in CI/CD"
        ),
        compliance=(
            "FIPS 140-3 (Physical security, timing resistance), "
            "Common Criteria (EAL4+ timing attack resistance), "
            "NIST SP 800-131A Rev.2"
        ),
        nist_pqc_migration=(
            "ML-KEM and ML-DSA reference implementations are constant-time by specification. "
            "liboqs provides validated constant-time PQC implementations."
        ),
        references=[
            "Kocher (1996) timing attacks on RSA",
            "NIST FIPS 140-3 (2019)",
            "dudect (2017) constant-time testing framework",
        ],
    ),

    PlaybookEntry(
        attack="JWT Replay Attack",
        attack_type="Classical",
        threat_level="HIGH",
        immediate=(
            "1. Reduce JWT expiry to 15 minutes for all authenticated endpoints. "
            "2. Deploy jti (JWT ID) nonce validation with Redis/DynamoDB nonce store. "
            "3. Revoke all active tokens if replay attack suspected."
        ),
        short_term=(
            "1. Implement token binding (RFC 8471) to bind tokens to TLS session. "
            "2. Add IP binding check (with awareness of VPN/proxy false positives). "
            "3. Enforce RS256 or ES256 over HS256 for service-to-service tokens. "
            "4. Implement refresh token rotation with single-use enforcement."
        ),
        long_term=(
            "1. Move to PKCE + short-lived access tokens (OAuth 2.1). "
            "2. Continuous access evaluation (CAE) per RFC 9396 — real-time token revocation. "
            "3. Zero-trust: re-authenticate on every sensitive operation."
        ),
        monitoring_metric=(
            "JTI nonce collision rate (must be 0); "
            "expired token usage attempts per hour; "
            "token lifetime distribution; "
            "alg=none/null rejection rate"
        ),
        compliance=(
            "RFC 7519 (JWT), RFC 9449 (DPoP), "
            "OAuth 2.0 Security BCP (RFC 9700), "
            "NIST SP 800-63B (digital identity)"
        ),
        nist_pqc_migration=(
            "JWT signing: replace RS256/ES256 with ML-DSA-based JWTs once RFC adopts PQC "
            "(IETF PQUIP WG active). "
            "Short-term: use ES256 (ECDSA P-256) — stronger than RS256, smaller tokens."
        ),
        references=[
            "RFC 7519 (JWT)", "RFC 9449 (DPoP)", "RFC 9700 (OAuth 2.0 Security BCP)",
        ],
    ),

    PlaybookEntry(
        attack="AI Adversarial ML Attack (FGSM)",
        attack_type="AI/ML",
        threat_level="HIGH",
        immediate=(
            "1. Activate input validation on ML API endpoints (range checks, type checks). "
            "2. Monitor prediction confidence distribution — anomalous low confidence = adversarial. "
            "3. Disable model confidence scores in public API responses (return label only)."
        ),
        short_term=(
            "1. Deploy adversarial training: augment training set with FGSM/PGD examples. "
            "2. Add input preprocessing defenses: spatial smoothing, feature squeezing. "
            "3. Set up adversarial example detection (LID detector, Mahalanobis distance)."
        ),
        long_term=(
            "1. Certified defenses: randomized smoothing (Cohen et al. 2019) — "
            "   provides L2-certified robustness radius ρ. "
            "2. Ensemble adversarial training for production models. "
            "3. Formal verification of ML robustness properties (Reluplex, α-β-CROWN)."
        ),
        monitoring_metric=(
            "Prediction confidence distribution (alert on systematic low-confidence queries); "
            "input feature distribution drift (KS test vs baseline); "
            "adversarial detection rate from LID/Mahalanobis detector"
        ),
        compliance=(
            "EU AI Act Article 15 (robustness and accuracy), "
            "NIST AI RMF (Govern 1.2, Measure 2.5), "
            "ISO/IEC 42001 (AI management system)"
        ),
        nist_pqc_migration=(
            "N/A — adversarial ML is not a cryptographic attack. "
            "However: quantum adversaries can find adversarial examples faster (Grover). "
            "Defense: certified bounds that are quantum-adversary-resistant."
        ),
        references=[
            "Goodfellow et al. (2015) FGSM",
            "Cohen et al. (2019) Certified Adversarial Robustness",
            "NIST AI RMF (2023)",
        ],
    ),

    PlaybookEntry(
        attack="Model Extraction Attack",
        attack_type="AI/ML",
        threat_level="HIGH",
        immediate=(
            "1. Enable API rate limiting: max 1000 queries/hour per user/IP. "
            "2. Log all API queries for anomaly detection (systematic scanning pattern). "
            "3. Return label-only responses — suppress probability scores for sensitive models."
        ),
        short_term=(
            "1. Add output perturbation: calibrated noise to probabilities (reduces fidelity). "
            "2. Implement query watermarking: embed IP-traceable signals in outputs. "
            "3. Detect systematic grid-search query patterns (entropy of input distribution)."
        ),
        long_term=(
            "1. Serve models behind secure enclaves (Intel SGX, AMD SEV) — "
            "   model weights never leave encrypted memory. "
            "2. Federated inference: model stays on-device. "
            "3. Model watermarking for legal attribution (Adi et al. 2018)."
        ),
        monitoring_metric=(
            "API query rate per user (alert > 500/hour); "
            "query input entropy (low entropy = systematic extraction); "
            "model output diversity (alert on low diversity = extraction run)"
        ),
        compliance=(
            "GDPR Article 22 (automated decision making), "
            "EU AI Act Article 28 (high-risk AI obligations), "
            "Trade secret / IP protection"
        ),
        nist_pqc_migration="N/A — not a cryptographic attack.",
        references=[
            "Tramèr et al. (2016) Stealing ML Models",
            "Adi et al. (2018) Turning your weakness into strength (watermarking)",
        ],
    ),

    PlaybookEntry(
        attack="Prompt Injection Attack (LLM)",
        attack_type="AI/ML",
        threat_level="CRITICAL",
        immediate=(
            "1. Add injection pattern filter on all LLM API inputs (keyword + semantic). "
            "2. Implement output content filter — block PII/secret exfiltration in responses. "
            "3. Revoke any LLM tool-use permissions that allow direct data access."
        ),
        short_term=(
            "1. Implement privilege separation: LLM cannot directly query databases. "
            "   Use a sandboxed tool layer with explicit allow-list of actions. "
            "2. Add canary tokens in system prompt — detect if they appear in output. "
            "3. Sanitize ALL retrieved documents in RAG pipelines before passing to LLM. "
            "4. Implement LLM output validation against schema (structured outputs only)."
        ),
        long_term=(
            "1. Constitutional AI / RLHF tuning for prompt injection resistance. "
            "2. Formal threat modeling of every LLM tool-use pathway. "
            "3. Red-team LLM applications on a continuous basis. "
            "4. AI Firewall (PromptGuard, LlamaGuard) in production pipeline."
        ),
        monitoring_metric=(
            "Injection detection rate by filter; "
            "system prompt leakage attempts (canary token triggers); "
            "anomalous tool-use sequences (privilege escalation pattern)"
        ),
        compliance=(
            "OWASP LLM Top 10 (LLM01 — Prompt Injection), "
            "NIST AI RMF (Measure 2.6 — AI red-teaming), "
            "EU AI Act Article 9 (risk management)"
        ),
        nist_pqc_migration="N/A — not a cryptographic attack.",
        references=[
            "Perez & Ribeiro (2022) Prompt Injection",
            "OWASP LLM Top 10 (2023)",
            "Greshake et al. (2023) Indirect Prompt Injection",
        ],
    ),
]


# ---------------------------------------------------------------------------
# Summary table builder
# ---------------------------------------------------------------------------

def print_summary_table(playbook: list[PlaybookEntry]):
    print("\n\n" + "=" * 76)
    print("  DEFENSE PLAYBOOK — SUMMARY TABLE")
    print("=" * 76)
    print(f"  {'Attack':<38} {'Type':<20} {'Threat':<10} {'PQC Algorithm'}")
    print("  " + "-" * 72)
    for entry in playbook:
        pqc = entry.nist_pqc_migration[:30] if len(entry.nist_pqc_migration) > 30 else entry.nist_pqc_migration
        print(
            f"  {entry.attack[:38]:<38} "
            f"{entry.attack_type[:20]:<20} "
            f"{entry.threat_level:<10} "
            f"{pqc}"
        )
    print("=" * 76)


def print_migration_timeline():
    print("\n\n" + "=" * 76)
    print("  PQC MIGRATION TIMELINE")
    print("=" * 76)
    timeline = [
        ("NOW (2026)",   "Enable PFS (ECDHE) on all TLS; disable RSA-1024/SHA-1; deploy AES-256"),
        ("2026–2027",    "Hybrid ML-KEM-768 + X25519 in TLS; hybrid ML-DSA + ECDSA certs"),
        ("2027–2028",    "Full ML-KEM deployment; internal PKI migrated to ML-DSA"),
        ("2028–2030",    "External-facing PQC complete; CNSA 2.0 compliance for gov systems"),
        ("2030+",        "RSA/ECDSA fully deprecated; ML-KEM-1024/ML-DSA only"),
        ("2033–2035",    "CRQC estimated arrival window — must be complete by this date"),
    ]
    for year, action in timeline:
        print(f"  {year:<14}  {action}")
    print("=" * 76)


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main():
    print("\n" + "#" * 76)
    print("  QUANTUM SECURITY DEFENSE PLAYBOOK")
    print("  Per-Attack Mitigation Guide: Immediate → Short-term → Long-term")
    print("#" * 76)

    for entry in PLAYBOOK:
        entry.display()

    print_summary_table(PLAYBOOK)
    print_migration_timeline()

    # Compliance coverage summary
    print("\n\n  COMPLIANCE STANDARDS ADDRESSED:")
    standards = set()
    for e in PLAYBOOK:
        for s in e.compliance.split(","):
            standards.add(s.strip().split(" ")[0])
    for s in sorted(standards):
        print(f"    • {s}")

    critical_attacks = [e for e in PLAYBOOK if e.threat_level == "CRITICAL"]
    print(f"\n  Total attacks covered: {len(PLAYBOOK)}")
    print(f"  CRITICAL-level attacks: {len(critical_attacks)}")
    print(f"  Compliance standards addressed: {len(standards)}")
    print()


if __name__ == "__main__":
    main()
