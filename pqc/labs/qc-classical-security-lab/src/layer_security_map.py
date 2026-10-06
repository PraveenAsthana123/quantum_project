"""
29-Layer Network/Security Map — Classical Cryptography
Maps every layer from L1 Physical to L29 AI/ML Security to its
classical cryptographic algorithms and quantum vulnerability assessment.

Prints a formatted table with:
  - Layer number and name
  - Classical algorithms in use
  - Quantum vulnerability level (CRITICAL/HIGH/MEDIUM/LOW/NONE)
  - Breaking quantum algorithm (Shor's/Grover's/None)
  - PQC migration path
"""

import time
from dataclasses import dataclass, field
from typing import List


@dataclass
class SecurityLayer:
    number: int
    name: str
    description: str
    classical_algorithms: List[str]
    quantum_vulnerability: str    # CRITICAL / HIGH / MEDIUM / LOW / NONE
    breaking_algorithm: str       # Shor's / Grover's / Both / None
    affected_components: str
    pqc_migration: str
    notes: str


# ---------------------------------------------------------------------------
# 29-layer definitions
# ---------------------------------------------------------------------------

LAYERS: List[SecurityLayer] = [
    SecurityLayer(
        number=1,
        name="Physical",
        description="RF/optical transmission, hardware security modules",
        classical_algorithms=["RF signal scrambling", "Optical fiber (no crypto)", "Physical tamper protection"],
        quantum_vulnerability="LOW",
        breaking_algorithm="None",
        affected_components="HSM tamper detection (non-crypto)",
        pqc_migration="No cryptographic migration needed; quantum sensing may affect RF eavesdropping detection",
        notes="Physical layer does not use public-key crypto. Quantum sensing (L25) is a future concern for optical fiber tapping.",
    ),
    SecurityLayer(
        number=2,
        name="Data Link",
        description="MACsec (IEEE 802.1AE) — Layer 2 encryption",
        classical_algorithms=["MACsec AES-128-GCM", "MACsec AES-256-GCM", "EAP-TLS for 802.1X (RSA/ECDSA)", "Pre-Shared Key or MKA (EAPOL)"],
        quantum_vulnerability="MEDIUM",
        breaking_algorithm="Grover's (AES-128)",
        affected_components="MACsec AES-128 key size; 802.1X EAP-TLS certificate auth",
        pqc_migration="Upgrade MACsec to AES-256-GCM; replace EAP-TLS certs with ML-DSA",
        notes="AES-128 provides only 64-bit post-quantum security. 802.1X RADIUS may use RSA certs — upgrade to PQC.",
    ),
    SecurityLayer(
        number=3,
        name="Network",
        description="IPsec ESP, IKEv2 key exchange, IP-layer encryption",
        classical_algorithms=["IPsec ESP AES-256-CBC", "IPsec ESP AES-256-GCM", "IKEv2 DH Group 14 (2048-bit MODP)", "IKEv2 ECDH P-256", "HMAC-SHA256 integrity"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="IKEv2 DH and ECDH key exchange — full session key compromise",
        pqc_migration="IKEv2 with ML-KEM-768 (RFC 9370 hybrid); keep AES-256-GCM for ESP",
        notes="DH-2048 broken by Shor's (~4096 qubits). HNDL: captured VPN traffic decryptable with CRQC.",
    ),
    SecurityLayer(
        number=4,
        name="Transport",
        description="TLS 1.3 — dominant transport security protocol",
        classical_algorithms=["TLS 1.3 ECDHE (P-256, X25519)", "TLS 1.3 ECDSA authentication", "AES-256-GCM record layer", "HKDF-SHA256 key schedule", "RSA-2048 (TLS 1.2 legacy)"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="ECDHE key exchange and ECDSA/RSA certificate auth",
        pqc_migration="X25519+ML-KEM-768 hybrid (IETF draft-ietf-tls-hybrid-design); ML-DSA certs",
        notes="Google/Cloudflare already deploy X25519+MLKEM768 hybrid in Chrome/Cloudflare. IETF standardizing.",
    ),
    SecurityLayer(
        number=5,
        name="Session",
        description="SSL/TLS session tickets, session resumption",
        classical_algorithms=["TLS session ticket encryption (AES-128 or AES-256)", "Session ticket HMAC (SHA-256)", "RSA session key encryption (legacy TLS 1.2)"],
        quantum_vulnerability="HIGH",
        breaking_algorithm="Shor's",
        affected_components="RSA session key wrapping in TLS 1.2; ticket encryption key lifetime",
        pqc_migration="Deprecate RSA key transport (already removed in TLS 1.3); shorten ticket lifetime; PFS by default",
        notes="TLS 1.3 eliminates RSA key transport. Legacy TLS 1.2 session resumption uses RSA — disable immediately.",
    ),
    SecurityLayer(
        number=6,
        name="Presentation",
        description="X.509 certificates, ASN.1 encoding, data format security",
        classical_algorithms=["X.509 v3 certificates", "RSA-2048 / RSA-4096 signatures", "ECDSA P-256 / P-384 signatures", "SHA-256 / SHA-384 digests", "PKCS #8 private key encoding"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="All certificate signatures; entire PKI trust chain",
        pqc_migration="Issue dual-algorithm certs (RSA+ML-DSA hybrid) transitionally; migrate root CA to ML-DSA or SLH-DSA",
        notes="Root CA migration is the hardest part — long-lived certs. NIST FIPS 204/205 published Aug 2024.",
    ),
    SecurityLayer(
        number=7,
        name="Application",
        description="HTTPS, REST API security, OAuth 2.0, browser security",
        classical_algorithms=["HTTPS (TLS 1.3 underneath)", "JWT RS256 / ES256 for API auth", "OAuth 2.0 client_secret_basic (HMAC)", "CORS, CSP, HSTS (policy, not crypto)", "Cookie HMAC-SHA256 signing"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="JWT RS256/ES256 signing keys; HTTPS certificate chain",
        pqc_migration="Replace JWT RS256/ES256 with ML-DSA JWT (IETF draft-ietf-cose-dilithium); keep HMAC HS256",
        notes="Application JWT tokens signed with RSA/ECDSA are forgeable with CRQC. OAuth refresh tokens are long-lived — priority.",
    ),
    SecurityLayer(
        number=8,
        name="PKI",
        description="Certificate Authority hierarchy, OCSP, CRL infrastructure",
        classical_algorithms=["Root CA RSA-4096 self-signed", "Intermediate CA RSA-2048 or ECDSA P-256", "OCSP responses signed with ECDSA", "CRL signed with RSA/ECDSA", "PKCS #12 key stores"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="Every certificate signature in the entire internet PKI",
        pqc_migration="New NIST-recommended CA hierarchy using SLH-DSA (stateless, no key state) for root; ML-DSA for issuing CA",
        notes="Entire WebPKI (Let's Encrypt, DigiCert, etc.) must migrate. CA/Browser Forum timeline: post-2026.",
    ),
    SecurityLayer(
        number=9,
        name="DNS",
        description="DNSSEC — DNS Security Extensions, DoT/DoH",
        classical_algorithms=["DNSSEC RSA/SHA-256 zone signing", "DNSSEC ECDSA P-256 (RFC 6605)", "DNS-over-TLS (DoT) — TLS 1.3", "DNS-over-HTTPS (DoH) — TLS 1.3"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="DNSSEC zone signing keys (ZSK and KSK); DoT/DoH TLS",
        pqc_migration="DNSSEC ML-DSA (IETF draft-ietf-dnsop-dnssec-pqc); DoT/DoH follows TLS migration",
        notes="DNSSEC cache poisoning becomes trivial with CRQC. Root KSK (RSA-2048) must be replaced urgently.",
    ),
    SecurityLayer(
        number=10,
        name="SSH",
        description="Secure Shell — remote administration, Git, SFTP",
        classical_algorithms=["RSA-2048/4096 host keys", "ECDSA P-256 host keys", "Ed25519 user keys", "ECDH P-256 / X25519 key exchange", "AES-256-CTR bulk cipher", "HMAC-SHA256 MAC"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="Host key authentication; user key authentication; ECDH session key",
        pqc_migration="OpenSSH 9.x: mlkem768nistp256 hybrid KEx; ML-DSA host/user keys (draft); regenerate ~/.ssh/ keys",
        notes="GitHub, GitLab, all CI/CD pipelines use SSH. Key infrastructure change required across all servers.",
    ),
    SecurityLayer(
        number=11,
        name="Email",
        description="S/MIME, PGP/GPG, email transport (SMTP STARTTLS)",
        classical_algorithms=["S/MIME RSA-2048 encryption + signing", "PGP RSA-2048/4096 key pairs", "PGP DSA-1024 (legacy)", "SMTP STARTTLS (TLS 1.3)"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="S/MIME and PGP private keys; all encrypted email archive",
        pqc_migration="PQC S/MIME (IETF draft-ietf-lamps-pq-smime); PGP with ML-KEM+ML-DSA (draft-ietf-openpgp-pqc)",
        notes="Archived encrypted email is at HNDL risk. Long-lived PGP web-of-trust keys need fresh PQC key generation.",
    ),
    SecurityLayer(
        number=12,
        name="Code Signing",
        description="Software supply chain integrity — Authenticode, GPG, Sigstore",
        classical_algorithms=["Authenticode RSA-2048 / ECDSA P-256", "GPG RSA-4096 package signing (APT, RPM)", "macOS code signing ECDSA P-256", "Sigstore ECDSA P-256 (cosign)"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="Every signed binary, kernel module, package, and container image",
        pqc_migration="Sigstore PQC milestone 2025; OS vendors to adopt ML-DSA for code signing certs",
        notes="Supply chain attack: CRQC forges RSA/ECDSA code signature → malicious software appears legitimate.",
    ),
    SecurityLayer(
        number=13,
        name="VPN",
        description="IPsec/IKEv2, OpenVPN, WireGuard tunnels",
        classical_algorithms=["IKEv2 DH Group 14/16 (MODP 2048/4096)", "OpenVPN TLS 1.3 with ECDHE", "WireGuard X25519 key exchange", "AES-256-CBC/GCM bulk cipher", "DTLS 1.2/1.3 for UDP tunnels"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="Key exchange in all tunnel establishment; HNDL on captured traffic",
        pqc_migration="WireGuard: experimental ML-KEM patches; IKEv2: RFC 9370 hybrid; OpenVPN: --tls-group mlkem768",
        notes="All VPN protocols expose key exchange to Shor's. Bulk traffic (AES-256) safe but session keys not.",
    ),
    SecurityLayer(
        number=14,
        name="HSM / KMS",
        description="Hardware Security Modules, Key Management Systems",
        classical_algorithms=["RSA-4096 key wrapping", "AES-256 KEK (Key Encryption Key)", "ECDSA P-384 signing inside HSM", "PKCS #11 / KMIP interfaces"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="RSA-4096 key wrapping broken; all keys wrapped with RSA exposed",
        pqc_migration="HSM firmware upgrade to support ML-KEM/ML-DSA (Thales/SafeNet PQC roadmap 2025-2027); new PQC KMS APIs",
        notes="HSM is the root of trust. Migration is hardware/firmware-constrained. Must re-wrap all keys with PQC KEK.",
    ),
    SecurityLayer(
        number=15,
        name="Identity",
        description="SAML 2.0, OIDC/OAuth, Kerberos, LDAP",
        classical_algorithms=["SAML 2.0 RSA-SHA256 assertions", "OIDC JWT RS256 / ES256 ID tokens", "Kerberos AES-256 ticket encryption", "Active Directory ECDSA DC certs"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="SAML assertions forgeable; OIDC ID tokens forgeable; AD DC certificates",
        pqc_migration="OIDC PQC JWT (IETF WG); SAML PQC XML-DSig update; Kerberos already AES — extend key sizes",
        notes="Identity federation (Okta, Azure AD) uses RS256 JWT. CRQC allows forging any identity assertion.",
    ),
    SecurityLayer(
        number=16,
        name="API Security",
        description="OAuth 2.0, JWT, mTLS for microservice auth",
        classical_algorithms=["OAuth 2.0 client credentials (RSA/ECDSA JWT)", "mTLS (ECDSA P-256 client certs)", "JWT RS256/ES256 bearer tokens", "API key HMAC-SHA256 signing"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="JWT signing keys; mTLS client certs; OAuth server certs",
        pqc_migration="Replace RS256/ES256 with ML-DSA JWT; mTLS with ML-DSA client certs; shorten token TTLs",
        notes="Zero-trust API fabric relies entirely on JWT/mTLS. Single CRQC operator can impersonate any service.",
    ),
    SecurityLayer(
        number=17,
        name="Database",
        description="TDE, column encryption, TLS for DB connections",
        classical_algorithms=["TDE AES-256 (SQL Server, Oracle, PostgreSQL)", "Column encryption AES-256 with RSA-2048 key wrapping", "TLS 1.3 client-server transport", "HMAC-SHA256 data integrity"],
        quantum_vulnerability="HIGH",
        breaking_algorithm="Shor's",
        affected_components="RSA key wrapping of column encryption keys; TLS cert chain",
        pqc_migration="Replace RSA key wrapping with ML-KEM-768; TLS follows transport layer migration",
        notes="TDE data encryption (AES-256) is PQ-safe. Key wrapping (RSA-2048) is the vulnerable link.",
    ),
    SecurityLayer(
        number=18,
        name="Blockchain",
        description="Bitcoin, Ethereum, enterprise DLT — public-key cryptography",
        classical_algorithms=["ECDSA secp256k1 (Bitcoin/Ethereum signing)", "SHA-256 (Bitcoin PoW, Merkle tree)", "SHA-3/Keccak (Ethereum state hashing)", "BLS-12-381 (Ethereum 2.0 validator sigs)"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="Every private key controlling BTC/ETH wallet; validator keys",
        pqc_migration="Active research: NIST-approved lattice sigs for blockchain (Ethereum PQC WG, 2024); wallet migration required",
        notes="~4M BTC in P2PK addresses expose public key on-chain — immediately extractable by Shor's. HNDL imminent.",
    ),
    SecurityLayer(
        number=19,
        name="Container",
        description="Service mesh (Istio/Linkerd mTLS), container image signing",
        classical_algorithms=["Istio mTLS ECDSA P-256 workload certs", "SPIFFE/SPIRE ECDSA SVID certs", "Sigstore cosign ECDSA P-256 image signing", "OCI Notary v2 RSA/ECDSA signatures"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="All service-to-service mTLS; container image provenance chain",
        pqc_migration="SPIRE ML-DSA SVID (draft 2025); cosign PQC mode; Notary v2 ML-DSA signature plugin",
        notes="Cloud-native zero trust depends entirely on short-lived ECDSA certs. Migration must happen at SPIRE/cert-manager layer.",
    ),
    SecurityLayer(
        number=20,
        name="IoT",
        description="DTLS 1.2/1.3, ECC constrained devices, MQTT over TLS",
        classical_algorithms=["DTLS 1.2 ECDHE/PSK", "ECDH P-256 on ARM Cortex-M (mbed TLS)", "AES-128-CCM / AES-128-GCM (constrained)", "MQTT over TLS 1.3"],
        quantum_vulnerability="HIGH",
        breaking_algorithm="Both",
        affected_components="ECDH key exchange; AES-128 provides only 64-bit PQ security",
        pqc_migration="LWC PQC for IoT: CRYSTALS-Kyber-512 (smallest ML-KEM); NIST LWC (ASCON for AE); device firmware upgrade",
        notes="Resource-constrained devices can run Kyber-512/Dilithium-2. NIST LWC competition winner ASCON for small devices.",
    ),
    SecurityLayer(
        number=21,
        name="Mobile",
        description="Certificate pinning, ECDH in mobile apps, keystore APIs",
        classical_algorithms=["Android Keystore ECDSA P-256 (TEE-backed)", "iOS Secure Enclave ECDH P-256", "Certificate pinning (SHA-256 of ECDSA cert)", "TLS 1.3 in mobile HTTP stacks"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="Secure Enclave/TEE ECDSA keys; pinned cert public key hashes become forgeable",
        pqc_migration="Apple/Google TEE firmware PQC support (roadmap 2026+); re-issue pinned certs with ML-DSA",
        notes="Certificate pinning breaks with CRQC: adversary forges cert matching pinned ECDSA public key hash.",
    ),
    SecurityLayer(
        number=22,
        name="Firmware",
        description="Secure boot chain, firmware signing, UEFI Secure Boot",
        classical_algorithms=["UEFI Secure Boot RSA-2048 (Microsoft KEK)", "U-Boot ECDSA P-256 image verification", "Measured boot TPM2 (SHA-256 PCR)", "OTA firmware signing RSA/ECDSA"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="UEFI db/KEK/PK RSA keys; OTA firmware signing key",
        pqc_migration="UEFI Forum PQC Secure Boot spec (draft 2024); TPM 2.0 profile for ML-DSA (TCG WG)",
        notes="Compromising UEFI Secure Boot RSA key allows persistent firmware rootkit installation.",
    ),
    SecurityLayer(
        number=23,
        name="DevSecOps",
        description="Git commit signing, CI/CD secrets, artifact signing",
        classical_algorithms=["Git commit signing ECDSA P-256 (SSH-based)", "GPG RSA-4096 commit signing", "CI/CD secret encryption (RSA/ECDSA JWT)", "SOPS age/RSA file encryption"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="Git commit non-repudiation; CI/CD pipeline secrets; artifact provenance",
        pqc_migration="GitLab/GitHub PQC signing (roadmap); Sigstore Fulcio ML-DSA; SOPS ML-KEM mode",
        notes="Forging commit signatures enables supply chain attacks. Priority for software factories.",
    ),
    SecurityLayer(
        number=24,
        name="SIEM",
        description="Log shipping security, SIEM agent authentication",
        classical_algorithms=["TLS 1.3 for log transport (Elastic/Splunk)", "ECDSA mTLS agent auth", "JWT ES256 for API access", "AES-256 at-rest encryption"],
        quantum_vulnerability="HIGH",
        breaking_algorithm="Shor's",
        affected_components="TLS log transport; ECDSA agent certificates",
        pqc_migration="SIEM TLS follows transport layer PQC migration; agent certs to ML-DSA",
        notes="Encrypted log streams captured today can be decrypted with CRQC — forensic evidence integrity at risk.",
    ),
    SecurityLayer(
        number=25,
        name="Zero Trust",
        description="mTLS service mesh, SPIFFE/SPIRE, continuous verification",
        classical_algorithms=["SPIFFE SVID X.509 ECDSA P-256", "Istio workload cert ECDSA P-256", "OPA policy JWT RS256", "mTLS AES-256-GCM record"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="All workload identity (SVID); policy evaluation JWT tokens",
        pqc_migration="SPIRE ML-DSA SVID issuance; IETF WIMSE WG including PQC; cert-manager PQC issuer",
        notes="Zero Trust assumes workload identity via certs. CRQC allows impersonating any workload.",
    ),
    SecurityLayer(
        number=26,
        name="Key Management",
        description="PKCS#11 HSM, Vault, KMIP key lifecycle",
        classical_algorithms=["PKCS#11 RSA-4096 key wrapping", "HashiCorp Vault Transit AES-256 + RSA", "KMIP RSA-2048/ECDSA P-256 over TLS", "AWS KMS RSA key transport"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="RSA key wrapping broken — all wrapped keys exposed; Vault TLS cert chain",
        pqc_migration="Vault ML-KEM transit key type (HashiCorp roadmap 2025); PKCS#11 PQC profile (OASIS); AWS KMS PQC beta",
        notes="KMS is highest-impact layer: compromise exposes ALL encrypted data protected by managed keys.",
    ),
    SecurityLayer(
        number=27,
        name="Compliance",
        description="FIPS 140-2/3, PCI-DSS, HIPAA, SOC 2 — standards compliance",
        classical_algorithms=["FIPS 140-2 approved: RSA-2048+, AES-128+, SHA-1+ (legacy)", "PCI-DSS TLS 1.2/1.3 requirement", "HIPAA AES-256 PHI encryption", "SOC 2 RSA/ECDSA audit signing"],
        quantum_vulnerability="MEDIUM",
        breaking_algorithm="Both",
        affected_components="FIPS 140-2 algorithms become non-compliant post-quantum era; audit trail signatures",
        pqc_migration="FIPS 140-3 being updated; NIST IR 8547 (2024) deprecates RSA/ECC by 2035; adopt FIPS 203/204/205",
        notes="Compliance frameworks are lagging. NIST IR 8547 provides the official deprecation timeline.",
    ),
    SecurityLayer(
        number=28,
        name="Audit",
        description="Trusted timestamping, digital evidence chain, long-term signatures",
        classical_algorithms=["RFC 3161 Trusted Timestamp RSA-SHA256", "Digital evidence signing ECDSA P-256", "Long-term signature XAdES-LTA (RSA)", "Archive PDF signing PAdES (RSA/ECDSA)"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="Legal non-repudiation of all digitally signed documents; court evidence",
        pqc_migration="ETSI ESI PQC archive signatures (EN 319 100-series update); RFC 3161 bis with ML-DSA",
        notes="Timestamped documents signed with RSA/ECDSA have no long-term legal standing in CRQC era. Archive re-signing urgent.",
    ),
    SecurityLayer(
        number=29,
        name="AI/ML Security",
        description="Model signing, ML API authentication, federated learning security",
        classical_algorithms=["Model weight signing ECDSA P-256 (Sigstore/cosign)", "ML API JWT RS256/ES256 bearer tokens", "Federated learning gradient encryption AES-256", "Differential privacy HMAC-SHA256 budget tracking"],
        quantum_vulnerability="CRITICAL",
        breaking_algorithm="Shor's",
        affected_components="Model provenance signatures (forgeable); API JWT tokens (forgeable)",
        pqc_migration="ML model signing with ML-DSA (Sigstore PQC); ML API JWT with ML-DSA; AES-256 for gradients OK",
        notes="AI supply chain integrity relies on ECDSA model signing. A forged model signature enables adversarial model substitution.",
    ),
]


# ---------------------------------------------------------------------------
# Vulnerability counts and ANSI color helpers
# ---------------------------------------------------------------------------

SEVERITY_COLOR = {
    "CRITICAL": "\033[91m",
    "HIGH":     "\033[93m",
    "MEDIUM":   "\033[94m",
    "LOW":      "\033[92m",
    "NONE":     "\033[97m",
}
RESET = "\033[0m"


def colored(text: str, severity: str) -> str:
    return f"{SEVERITY_COLOR.get(severity, '')}{text}{RESET}"


# ---------------------------------------------------------------------------
# Table printer (compact)
# ---------------------------------------------------------------------------

def print_layer_table(layers: List[SecurityLayer]):
    print("\n" + "=" * 130)
    print("29-LAYER SECURITY MAP — CLASSICAL CRYPTO + QUANTUM VULNERABILITY")
    print("=" * 130)
    print(
        f"  {'L#':<4} {'LAYER NAME':<16} {'CLASSICAL ALGORITHMS (primary)':<45} "
        f"{'QV':<10} {'QUANTUM ATTACK':<18} {'PQC MIGRATION'}"
    )
    print("  " + "-" * 126)

    for layer in layers:
        primary_algos = ", ".join(layer.classical_algorithms[:2])
        if len(layer.classical_algorithms) > 2:
            primary_algos += f" (+{len(layer.classical_algorithms)-2} more)"
        migration_short = layer.pqc_migration[:40] + "..." if len(layer.pqc_migration) > 43 else layer.pqc_migration

        print(
            f"  L{layer.number:<3} {layer.name:<16} {primary_algos:<45} "
            f"{layer.quantum_vulnerability:<10} {layer.breaking_algorithm:<18} {migration_short}"
        )

    print("  " + "-" * 126)


# ---------------------------------------------------------------------------
# Detailed per-layer report
# ---------------------------------------------------------------------------

def print_detailed_layer(layer: SecurityLayer):
    print(f"\n  {'─'*70}")
    print(f"  L{layer.number:02d} — {layer.name.upper()}")
    print(f"  {'─'*70}")
    print(f"    Description    : {layer.description}")
    print(f"    Algorithms     :")
    for alg in layer.classical_algorithms:
        print(f"      • {alg}")
    print(f"    Quantum vuln   : {layer.quantum_vulnerability}")
    print(f"    Quantum attack : {layer.breaking_algorithm}")
    print(f"    Affected       : {layer.affected_components}")
    print(f"    PQC migration  : {layer.pqc_migration}")
    print(f"    Notes          : {layer.notes}")


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def print_statistics(layers: List[SecurityLayer]):
    from collections import Counter
    vuln_count = Counter(l.quantum_vulnerability for l in layers)
    attack_count = Counter(l.breaking_algorithm for l in layers)

    print("\n" + "=" * 60)
    print("LAYER VULNERABILITY STATISTICS")
    print("=" * 60)

    print("  Vulnerability distribution:")
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"]:
        count = vuln_count.get(sev, 0)
        pct   = count / len(layers) * 100
        bar   = "█" * count
        print(f"    {sev:<10} : {count:>2} layers ({pct:4.0f}%)  {bar}")

    print()
    print("  Breaking algorithm:")
    for alg, cnt in sorted(attack_count.items(), key=lambda x: -x[1]):
        print(f"    {alg:<22} : {cnt:>2} layers")

    critical = [l for l in layers if l.quantum_vulnerability == "CRITICAL"]
    print()
    print(f"  Total layers analyzed    : {len(layers)}")
    print(f"  Critical quantum risk    : {len(critical)} / {len(layers)}")
    print(f"  Safe without change      : {sum(1 for l in layers if l.quantum_vulnerability in ('LOW', 'NONE'))}")
    print()
    print("  Highest priority migration layers:")
    for layer in critical[:5]:
        print(f"    L{layer.number:02d} {layer.name:<16} — {layer.breaking_algorithm}")


# ---------------------------------------------------------------------------
# Urgency matrix
# ---------------------------------------------------------------------------

def print_urgency_matrix(layers: List[SecurityLayer]):
    print("\n" + "=" * 60)
    print("PQC MIGRATION URGENCY MATRIX")
    print("=" * 60)
    print("""
  TIER 1 — MIGRATE NOW (HNDL risk today):
    L3  Network   (IKEv2 DH-2048)
    L4  Transport (TLS 1.3 ECDHE)
    L6  Pres.     (X.509 / RSA-2048 certs)
    L8  PKI       (CA hierarchy)
    L13 VPN       (WireGuard / IPsec)
    L26 KMS       (Vault / HSM key wrapping)

  TIER 2 — MIGRATE BEFORE 2028:
    L7  Application (JWT RS256/ES256)
    L10 SSH         (host keys / user keys)
    L15 Identity    (SAML / OIDC JWT)
    L16 API         (OAuth mTLS)
    L22 Firmware    (UEFI Secure Boot)
    L28 Audit       (TSA timestamps)

  TIER 3 — PLANNED MIGRATION (2026–2030):
    L2  DataLink    (MACsec AES-128 → AES-256)
    L11 Email       (S/MIME / PGP re-keying)
    L12 Code Signing (Authenticode)
    L18 Blockchain   (wallet migration research)
    L19 Container    (cosign / Notary v2)
    L20 IoT          (constrained device LWC PQC)
    L29 AI/ML        (model signing, API tokens)

  ALREADY SAFE OR MINOR ACTION:
    L1  Physical    (no crypto migration)
    L17 Database    (AES-256 TDE safe; fix RSA key wrap)
    L27 Compliance  (follow NIST IR 8547 timeline)
  """)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print()
    print("##############################################################")
    print("#  29-LAYER SECURITY MAP — CLASSICAL CRYPTOGRAPHY           #")
    print("#  Quantum vulnerability per network/security layer         #")
    print("##############################################################")

    t0 = time.perf_counter()

    print_layer_table(LAYERS)

    print("\n\nDETAILED REPORT — CRITICAL LAYERS")
    for layer in LAYERS:
        if layer.quantum_vulnerability == "CRITICAL":
            print_detailed_layer(layer)

    print_statistics(LAYERS)
    print_urgency_matrix(LAYERS)

    elapsed = (time.perf_counter() - t0) * 1000
    print(f"  Map generated in {elapsed:.2f} ms")
    print()


if __name__ == "__main__":
    main()
