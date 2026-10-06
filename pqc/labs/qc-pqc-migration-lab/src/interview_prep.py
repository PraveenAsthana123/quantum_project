"""
PQC Interview Preparation
Structured Q&A for post-quantum cryptography and PKI migration roles.
Covers:
  - OLD system: classical crypto challenges per layer
  - NEW system: PQC migration strategy, algorithms, and protocol details
  - Technical depth: FIPS 203/204/205/206, CNSA 2.0, IETF drafts, NIST SP 800-208
"""

from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class QA:
    question: str
    answer: str
    tags: List[str]
    depth: str   # "conceptual" | "technical" | "hands-on"


# ─── OLD SYSTEM: Classical Crypto Challenges ──────────────────────────────────

OLD_SYSTEM_QA: List[QA] = [
    QA(
        question="Q1. Why is RSA-2048 no longer considered long-term secure?",
        answer=(
            "RSA security relies on the hardness of integer factorization. "
            "Shor's algorithm (1994) factors an n-bit RSA modulus in polynomial time — "
            "O(n³) quantum gate operations — on a Cryptographically Relevant Quantum Computer "
            "(CRQC). A 2048-bit modulus requires approximately 4,000 error-corrected logical "
            "qubits with ~10^7 T-gates. While no CRQC exists today, NIST, NSA, and CISA all "
            "recommend beginning migration NOW due to the 'harvest now, decrypt later' (HNDL) "
            "threat: adversaries are storing TLS sessions today to decrypt once a CRQC "
            "is available. For data with ≥10-year confidentiality requirements (health, "
            "finance, national security), the threat is already present."
        ),
        tags=["RSA", "Shor", "HNDL", "CRQC"],
        depth="technical",
    ),
    QA(
        question="Q2. In the TLS layer, what is the specific vulnerability and what does harvest-now-decrypt-later mean in practice?",
        answer=(
            "In TLS 1.2 and 1.3, the certificate uses RSA or ECDSA which is vulnerable to "
            "Shor's algorithm. Even though TLS 1.3 provides Perfect Forward Secrecy (PFS) "
            "via ephemeral ECDHE — meaning the session key is not derivable from the private key "
            "alone — the attacker doesn't need to break the session key directly. Instead, they "
            "record the full TLS handshake (ClientHello, ServerHello, Certificate, "
            "CertificateVerify, Finished) and the ciphertext stream. Once a CRQC is available, "
            "they break the RSA/ECDSA private key from the public key in the Certificate message, "
            "then recompute the Finished MAC and derive the session key. "
            "ECDHE ephemeral keys are ALSO broken via Shor's ECDLP solver — they only provide "
            "forward secrecy against classical theft, not quantum decryption. "
            "Practical HNDL example: a nation-state records all TLS sessions to a government "
            "contractor in 2024 and decrypts them in 2032 when a CRQC is operational."
        ),
        tags=["TLS", "HNDL", "ECDHE", "PFS", "Shor"],
        depth="technical",
    ),
    QA(
        question="Q3. How does Grover's algorithm affect symmetric encryption and which key sizes are still safe?",
        answer=(
            "Grover's algorithm provides a quadratic speedup for unstructured search — it finds "
            "a pre-image for a hash function in O(√2^n) = O(2^{n/2}) operations instead of 2^n. "
            "For AES: a CRQC running Grover against AES-128 has effective security of 64 bits — "
            "borderline acceptable but no longer best practice. AES-256 retains 128-bit security "
            "under Grover (2^256/2 = 2^128), which is considered quantum-safe. "
            "SHA-256 collision resistance drops from 2^128 to 2^85 under Grover — still large "
            "but NIST recommends SHA-384 or SHA3-256 for new deployments. "
            "Key action: upgrade AES-128 → AES-256 (NIST SP 800-131Ar3 disallows AES-128 "
            "for sensitive data after 2030). Bulk TLS traffic uses AES-256-GCM already in "
            "TLS_AES_256_GCM_SHA384 — the cipher itself is fine; only the key agreement and "
            "certificate auth need PQC migration."
        ),
        tags=["Grover", "AES", "symmetric", "SHA"],
        depth="technical",
    ),
    QA(
        question="Q4. Why is ECDSA (elliptic curve) also vulnerable — isn't it different from RSA?",
        answer=(
            "ECDSA, ECDH, and Ed25519 rely on the hardness of the Elliptic Curve Discrete "
            "Logarithm Problem (ECDLP): given P = kG, find the scalar k. "
            "Shor's algorithm has a straightforward generalization to ECDLP — it uses the "
            "quantum Fourier transform to find the order of the group, solving ECDLP in "
            "O(n³) gate operations for an n-bit curve. "
            "A 256-bit elliptic curve (P-256, secp256k1) is broken by a CRQC with ~2,330 "
            "logical qubits (Roetteler et al. 2017). This is SMALLER than the qubit count "
            "for RSA-2048 (~4,000 logical qubits), meaning ECC is actually MORE vulnerable "
            "to quantum attack per bit of security. "
            "Consequence: JWT (RS256/ES256), TLS certificates, SSH Ed25519 host keys, "
            "ECDHE session key exchange — all broken simultaneously."
        ),
        tags=["ECDSA", "ECDLP", "elliptic curve", "Shor"],
        depth="technical",
    ),
    QA(
        question="Q5. What makes PKI migration particularly hard compared to, say, rotating a symmetric key?",
        answer=(
            "Symmetric key rotation is operationally straightforward: generate a new key, "
            "re-encrypt data, delete the old key. The algorithm (AES-256) doesn't change. "
            "PKI migration requires changing the algorithm itself across an entire trust chain: "
            "1. Root CA: re-key with ML-DSA-87; distribute new root cert to ALL trust stores "
            "   (OS, browser, Java JVM, mobile OSes) — this takes 2+ years for browser roots. "
            "2. Intermediate CAs: re-key and re-sign by new root. "
            "3. End-entity certs: thousands of servers need new CSRs, new certs, new private keys. "
            "4. Client software: TLS libraries (OpenSSL, BoringSSL, NSS) must support the new "
            "   algorithm — not all versions do. "
            "5. Protocol negotiation: clients and servers must negotiate a common PQC algorithm "
            "   set during the hybrid transition period. "
            "6. Certificate size: an ML-DSA-65 cert chain is ~6x larger than an RSA chain, "
            "   stressing CDNs, UDP/DTLS, and embedded devices. "
            "Migration window: NIST estimates 10-15 years for full PKI ecosystem migration."
        ),
        tags=["PKI", "X.509", "trust store", "migration complexity"],
        depth="technical",
    ),
    QA(
        question="Q6. What is a CBOM and why is it the first deliverable in a PQC migration program?",
        answer=(
            "CBOM = Cryptographic Bill of Materials. Analogous to SBOM (Software BOM) but "
            "catalogs all cryptographic assets: algorithms, key sizes, certificate subjects/expiry, "
            "protocol versions, and where they're used. "
            "Format: CycloneDX 1.4+ defines a CBOM JSON schema with 'cryptographic-asset' "
            "component type, algorithmProperties (primitive, parameterSetIdentifier, "
            "classicalSecurityLevel, nistQuantumSecurityLevel, cryptoFunctions). "
            "Why first: you can't migrate what you haven't found. "
            "In a large enterprise, cryptographic usage is scattered across: "
            "TLS termination configs, application code (Java KeyStore, OpenSSL calls), "
            "databases (TDE keys), HSMs (wrapping keys), VPN profiles (IKEv2 proposals), "
            "SSH daemon configs, JWT signing keys (Kubernetes secrets), firmware (RSA PKCS#7 sigs). "
            "NIST IR 8547 (2024) formally introduces the CBOM concept and provides the "
            "schema basis for enterprise PQC inventories."
        ),
        tags=["CBOM", "inventory", "CycloneDX", "NIST IR 8547"],
        depth="technical",
    ),
    QA(
        question="Q7. In the JWT/auth layer, how does the vulnerability manifest beyond the signing key?",
        answer=(
            "A JWT signed with RS256 (RSA-2048-SHA256) carries the RSA public key fingerprint "
            "in its JWK Set (JWKS). An attacker who harvests JWTs today and breaks the RSA private "
            "key later can forge valid JWTs for any subject/scope — including admin tokens — "
            "without interacting with the auth server. "
            "The attacker doesn't need to break TLS to get the JWTs: JWTs appear in mobile app "
            "network captures, in server logs (Authorization header), in browser local storage. "
            "Secondary risk: the JWKS endpoint itself is served over TLS. If the TLS cert is also "
            "RSA/ECDSA, MITM via a future CRQC lets an attacker replace the JWKS with their own "
            "forged ML-DSA keys — intercepting auth silently. "
            "Scope of impact: in a microservices architecture, one compromised JWT signing key "
            "typically affects every service that trusts the JWKS endpoint — often 30-100+ services."
        ),
        tags=["JWT", "RS256", "JWKS", "OAuth", "OIDC"],
        depth="technical",
    ),
    QA(
        question="Q8. In the VPN/IKEv2 layer, why is DH-2048 the highest priority fix even though it's 2048-bit?",
        answer=(
            "IKEv2 uses Diffie-Hellman key exchange to establish the IKE_SA and CHILD_SA. "
            "With DH-2048 (MODP group 14), the session key is derived from g^{xy} mod p — "
            "the discrete logarithm problem in a multiplicative group. "
            "Shor's algorithm solves DLP in a cyclic group in O(n³) operations for n-bit p. "
            "DH-2048 requires ~4,000 logical qubits — same order as RSA-2048. "
            "VPN sessions often have long rekeying intervals (8 hours or more) and carry "
            "extremely sensitive traffic: M&A negotiations, HR records, financial forecasts, "
            "IP transfers. VPN data is particularly attractive for HNDL because it aggregates "
            "all enterprise traffic in one place. "
            "Additionally, VPN sessions may have thousands of concurrent SA negotiations, "
            "amplifying the attack surface. "
            "RFC 9370 (IKEv2 PQC, 2023) defines the 'Additional Key Exchange' (AKE) mechanism "
            "to add ML-KEM-768 alongside the classical DH group — this is the production fix."
        ),
        tags=["VPN", "IKEv2", "DH", "RFC 9370", "HNDL"],
        depth="technical",
    ),
    QA(
        question="Q9. How does the code signing / firmware signing layer become a long-term vulnerability?",
        answer=(
            "Code and firmware signatures have an unusual property: the signed artifact persists "
            "long after the signing event. A firmware binary signed with RSA-4096 in 2024 might "
            "still be deployed on embedded devices in 2040. "
            "If a CRQC breaks the RSA-4096 signing key at any future time, an attacker can "
            "forge signatures on malicious firmware and push it to any device that trusts the "
            "original CA — with no revocation mechanism on embedded devices to stop it. "
            "This creates a permanent supply chain vulnerability: "
            "1. Attacker breaks old RSA signing key in 2033. "
            "2. Attacker signs malicious firmware with forged signature. "
            "3. Devices still running the update client accept the forged signature. "
            "4. Millions of IoT/embedded devices compromised via silent update. "
            "NIST recommendation: dual-sign with both RSA-4096 (for legacy verifiers) and "
            "ML-DSA-87 (for PQC-capable verifiers) starting now. "
            "CNSA 2.0 mandates SLH-DSA-256s for software signing at NSS levels (2030 deadline)."
        ),
        tags=["code signing", "firmware", "supply chain", "SLH-DSA", "CNSA 2.0"],
        depth="technical",
    ),
    QA(
        question="Q10. What is the 'store now, decrypt later' threat and what is the realistic CRQC timeline?",
        answer=(
            "HNDL (Harvest Now, Decrypt Later) is the strategy of capturing encrypted traffic "
            "today and storing it until a CRQC is available to decrypt it. "
            "The threat is already active: intelligence agencies and well-funded adversaries have "
            "the storage capacity to record internet backbone traffic. "
            "CRQC timeline estimates (as of 2024): "
            "  - NSA CNSA 2.0 (2022): begin migration immediately; mandates completion by 2030 "
            "    for NSS systems. "
            "  - NIST (2024): 'a CRQC capable of breaking RSA-2048 may be available by 2030-2035' "
            "    (conservative estimate; some argue sooner). "
            "  - Gartner: 'by 2029, information encrypted today will be decryptable by quantum' "
            "    (2023 research). "
            "  - IBM/Google: current noisy intermediate-scale quantum (NISQ) devices have "
            "    ~1000 physical qubits; logical qubits via error correction are the bottleneck. "
            "Key point: the CRQC doesn't need to exist at COLLECTION time — only at DECRYPTION "
            "time. Any data collected today with a confidentiality requirement beyond ~5 years "
            "is at risk TODAY, regardless of when a CRQC is built."
        ),
        tags=["HNDL", "CRQC", "timeline", "NSA", "Gartner"],
        depth="conceptual",
    ),
]


# ─── NEW SYSTEM: PQC Migration Q&A ────────────────────────────────────────────

NEW_SYSTEM_QA: List[QA] = [
    QA(
        question="Q1. How do FIPS 203, 204, and 205 resolve the classical crypto vulnerabilities, and what are their OIDs?",
        answer=(
            "NIST standardized three PQC algorithms in August 2024 to replace all SHOR-vulnerable "
            "classical algorithms: "
            "\n"
            "FIPS 203 — ML-KEM (Module-Lattice-based Key Encapsulation Mechanism): "
            "  Replaces X25519, ECDH, DH, RSA-OAEP for key agreement. "
            "  Three parameter sets: ML-KEM-512 (L1), ML-KEM-768 (L3, recommended), ML-KEM-1024 (L5). "
            "  OIDs: 2.16.840.1.101.3.4.4.{1,2,3} for 512/768/1024. "
            "  Security basis: Module-LWE (Learning With Errors) — best known quantum attack "
            "  is BKZ lattice sieving at ~2^{150} operations for ML-KEM-768. "
            "\n"
            "FIPS 204 — ML-DSA (Module-Lattice-based Digital Signature Algorithm): "
            "  Replaces RSA-2048, ECDSA, Ed25519 for digital signatures. "
            "  Three parameter sets: ML-DSA-44 (L2), ML-DSA-65 (L3), ML-DSA-87 (L5). "
            "  OIDs: 2.16.840.1.101.3.4.3.{17,18,19} for 44/65/87. "
            "  Security basis: Module-SIS (Short Integer Solution) + Module-LWE. "
            "\n"
            "FIPS 205 — SLH-DSA (Stateless Hash-Based Digital Signature Algorithm): "
            "  Replaces RSA/ECDSA where hash-based security assumptions are preferred "
            "  (firmware signing, long-lived certificates). "
            "  Based on SPHINCS+ with tiny keys (32B PK) but large sigs (7-50KB). "
            "  Conservative choice: security depends only on hash function properties. "
            "\n"
            "FIPS 206 (draft) — FN-DSA (Falcon-based): "
            "  Compact signatures (~666B for Falcon-512) via NTRU lattices. "
            "  Not yet standardized; complex Gaussian sampling makes implementation harder."
        ),
        tags=["FIPS 203", "FIPS 204", "FIPS 205", "ML-KEM", "ML-DSA", "SLH-DSA", "OID"],
        depth="technical",
    ),
    QA(
        question="Q2. What is CNSA 2.0 and how does it differ from CNSA 1.0?",
        answer=(
            "CNSA (Commercial National Security Algorithm Suite) is NSA's approved algorithm "
            "list for protecting NSS (National Security Systems) — U.S. government, defense, "
            "and cleared contractor systems. "
            "\n"
            "CNSA 1.0 (2015): AES-256, SHA-384, RSA-3072 (minimum), ECDSA-P384, DH-3072, "
            "X25519/X448 — all classical. "
            "\n"
            "CNSA 2.0 (2022): REPLACES CNSA 1.0 entirely. Mandates: "
            "  - Key agreement: ML-KEM-1024 ONLY (X25519 no longer sufficient) "
            "  - Signatures  : ML-DSA-87 ONLY (ECDSA-P384 no longer sufficient) "
            "  - SW signing  : SLH-DSA-256s ONLY "
            "  - Symmetric   : AES-256 (unchanged) "
            "  - Hash        : SHA-384 / SHA-512 (unchanged) "
            "  Timeline: NSS systems must complete migration by 2030 for all categories. "
            "  Vendor guidance: products sold to U.S. government must support CNSA 2.0 by 2025 "
            "  (already effective for new acquisitions). "
            "\n"
            "Key difference from FIPS: CNSA 2.0 uses only L5 parameter sets (ML-KEM-1024, "
            "ML-DSA-87) whereas NIST FIPS allows L3 (ML-KEM-768, ML-DSA-65) for non-NSS. "
            "Enterprises not bound by NSS can use L3, saving ~30% bandwidth overhead."
        ),
        tags=["CNSA 2.0", "NSA", "NSS", "ML-KEM-1024", "ML-DSA-87"],
        depth="technical",
    ),
    QA(
        question="Q3. In the TLS layer, how does the hybrid design work and why is the hybrid approach necessary?",
        answer=(
            "The hybrid design for TLS 1.3 is defined in IETF draft-ietf-tls-hybrid-design. "
            "It combines a classical algorithm (X25519) and a PQC algorithm (ML-KEM-768) for "
            "key exchange, so the session is secure if EITHER algorithm is unbroken. "
            "\n"
            "Why hybrid: ML-KEM is new (standardized 2024). If a cryptographic flaw is "
            "discovered in ML-KEM before full migration, a hybrid session still relies on "
            "X25519 for security. This is the 'crypto agility' principle: don't bet everything "
            "on one new algorithm. "
            "\n"
            "Mechanism: "
            "1. Client sends KeyShare for X25519+ML-KEM-768 (group 0x11EC per IANA draft). "
            "2. Server generates X25519 ephemeral key and encapsulates into client's ML-KEM-768 "
            "   encapsulation key. "
            "3. Both sides compute: master_secret = HKDF(ss_X25519 || ss_ML-KEM-768). "
            "   (Draft mandates concatenation with KDF, not XOR, per Section 3.2.) "
            "4. Certificate uses ML-DSA-65 for server authentication (separate from KEX). "
            "\n"
            "IETF code points (draft-ietf-tls-ecdhe-mlkem): "
            "  0x11EC = X25519MLKEM768 "
            "  0x11ED = X25519MLKEM1024 "
            "\n"
            "Already deployed: Cloudflare enabled hybrid TLS in 2023; Chrome enabled it "
            "experimentally in 2023 (X25519Kyber768Draft00, precursor to IETF draft). "
            "Google enabled it for all Chrome/Android connections by 2024."
        ),
        tags=["TLS", "hybrid", "X25519", "ML-KEM-768", "IETF draft", "HKDF"],
        depth="technical",
    ),
    QA(
        question="Q4. Walk through the JWT migration from RS256 to ML-DSA-65. What are the practical challenges?",
        answer=(
            "Migration steps: "
            "1. Key generation: generate ML-DSA-65 key pair (PK=1952B, SK=4032B). "
            "2. JWKS update: publish new JWKS endpoint with both RS256 and ML-DSA-65 keys; "
            "   use different kid values. JOSE header: {\"alg\":\"ML-DSA-65\",\"typ\":\"JWT\",\"kid\":\"pqc-001\"}. "
            "3. Dual-sign tokens: issue both RS256 and ML-DSA-65 tokens, or use "
            "   X-Alt-Token header for the RS256 fallback. "
            "4. Service migration: update 47+ microservices to accept ML-DSA-65 tokens; "
            "   each needs an updated JWT verification library. "
            "5. Deprecate RS256: after all consumers migrated, mark RS256 JWKS key as "
            "   x-deprecated; reject RS256 tokens for sensitive scopes first. "
            "\n"
            "Practical challenges: "
            "  - Token size: ML-DSA-65 JWT = ~4.8KB vs RS256 JWT ~1.2KB (4x larger). "
            "    Impact: HTTP headers, mobile bandwidth, auth service throughput. "
            "  - Library support: python-jwt, jjwt (Java), nimbus-jose-jwt need PQC updates. "
            "    jose-py, python-jose — not yet updated as of 2024. "
            "  - OID/algorithm identifier: 'ML-DSA-65' not yet in IANA JOSE algorithm registry "
            "    (IETF draft-ietf-jose-fully-specified-algorithms). "
            "  - FIDO2 / WebAuthn: FIDO Alliance roadmap for PQC; CBOR encoding needs updates. "
            "\n"
            "IETF references: "
            "  draft-ietf-jose-fully-specified-algorithms "
            "  draft-ietf-oauth-pqca (PQC for OAuth/OIDC)"
        ),
        tags=["JWT", "RS256", "ML-DSA-65", "JWKS", "IETF", "token size"],
        depth="technical",
    ),
    QA(
        question="Q5. How does the IKEv2 VPN layer migrate using RFC 9370?",
        answer=(
            "RFC 9370 (May 2023): 'Multiple Key Exchanges in IKEv2' — adds an 'Additional Key "
            "Exchange' (AKE) mechanism that allows one or more extra key exchanges after the "
            "initial Diffie-Hellman in IKE_SA_INIT. "
            "\n"
            "Hybrid IKEv2 flow: "
            "1. IKE_SA_INIT: exchange X25519 or DH-3072 ephemeral keys (classical). "
            "2. New IKE_INTERMEDIATE exchange: client sends ML-KEM-768 encapsulation key; "
            "   server encapsulates and returns ciphertext. "
            "3. Master session key: PRF(classical_ss, pqc_ss, nonces) — both contribute. "
            "4. IKE AUTH: server presents ML-DSA-65 certificate for authentication. "
            "\n"
            "Implementation: StrongSwan 5.9.8+ supports ML-KEM-768 + X25519 hybrid; "
            "libreswan 4.10+ has experimental support. "
            "Cisco, Palo Alto: roadmap items for 2025-2026. "
            "\n"
            "Deployment challenges: "
            "  - VPN clients: ~3000 employee endpoints need updated VPN software. "
            "  - Firewall: IKEv2 UDP/500 payload size increases with ML-KEM CT (1088B extra); "
            "    fragmentation rules may need adjustment. "
            "  - Legacy: Windows built-in IKEv2 client doesn't yet support RFC 9370 PQC; "
            "    requires third-party VPN client. "
            "\n"
            "CNSA 2.0 mandates full PQC VPN by 2025 for NSS; enterprises should target 2027."
        ),
        tags=["VPN", "IKEv2", "RFC 9370", "ML-KEM-768", "StrongSwan"],
        depth="technical",
    ),
    QA(
        question="Q6. Explain the X.509v3 PQC OID extensions and what changes in the certificate format.",
        answer=(
            "NIST assigned OIDs for all FIPS 203/204/205 algorithms under the arc "
            "2.16.840.1.101.3.4 (nistAlgorithms): "
            "\n"
            "ML-DSA (FIPS 204) signing OIDs: "
            "  id-ML-DSA-44  = 2.16.840.1.101.3.4.3.17 "
            "  id-ML-DSA-65  = 2.16.840.1.101.3.4.3.18  ← recommended "
            "  id-ML-DSA-87  = 2.16.840.1.101.3.4.3.19 "
            "\n"
            "ML-KEM (FIPS 203) KEM OIDs: "
            "  id-ML-KEM-512  = 2.16.840.1.101.3.4.4.1 "
            "  id-ML-KEM-768  = 2.16.840.1.101.3.4.4.2 "
            "  id-ML-KEM-1024 = 2.16.840.1.101.3.4.4.3 "
            "\n"
            "X.509v3 changes: "
            "  - subjectPublicKeyInfo.algorithm OID: set to id-ML-DSA-65. "
            "  - SubjectPublicKey: 1952 bytes (ML-DSA-65 PK) vs 256 bytes (RSA-2048). "
            "  - Signature: 3309 bytes (ML-DSA-65) vs 256 bytes (RSA-2048). "
            "  - Total cert size: ~6-8KB vs ~1.2KB for RSA cert. "
            "  - AlgorithmIdentifier.parameters: absent (NULL replaced with empty). "
            "\n"
            "Hybrid cert: IETF draft-ietf-lamps-pq-composite-sigs adds a 'composite' "
            "SubjectPublicKeyInfo containing both ECDSA-P256 and ML-DSA-65 keys. "
            "draft-ietf-lamps-pq-composite-kem adds X25519 + ML-KEM-768 in one cert. "
            "\n"
            "CA readiness: DigiCert, Sectigo announced ML-DSA-65 cert issuance roadmap "
            "for 2025. Let's Encrypt: horizon 2025-2026."
        ),
        tags=["X.509", "OID", "FIPS 204", "certificate", "LAMPS", "composite"],
        depth="technical",
    ),
    QA(
        question="Q7. How do you handle the certificate size increase in TLS without breaking CDN or embedded clients?",
        answer=(
            "ML-DSA-65 cert chain is ~6-8KB vs ~2KB for RSA. Mitigation strategies: "
            "\n"
            "1. OCSP stapling: server staples OCSP response, reducing separate CA roundtrip. "
            "   Especially important since ML-DSA OCSP response is also larger. "
            "\n"
            "2. TLS record fragmentation: TLS 1.3 max record = 16KB; a 6KB cert fits in one "
            "   record, so no fragmentation issue for most cases. "
            "\n"
            "3. Certificate compression (RFC 8879): compress cert bytes with zlib/brotli; "
            "   ML-DSA-65 PK and sigs compress ~30-40% due to their structure. "
            "\n"
            "4. Hybrid period optimization: during transition, use ML-DSA-65 for leaf cert "
            "   but retain RSA-2048 intermediate (clients that don't support PQC still "
            "   validate the chain via the RSA intermediate). "
            "\n"
            "5. Short-lived certs: ACME protocol (Let's Encrypt) model — 24-hour certs via "
            "   automated renewal; no CRL needed if certs expire quickly. "
            "\n"
            "6. QUIC/HTTP3: QUIC uses UDP with 1280B max initial packet; PQC handshake "
            "   requires multiple QUIC packets. IETF draft-ietf-quic-pqc addresses this. "
            "\n"
            "7. CDN: Cloudflare, Fastly, Akamai must upgrade their TLS termination stack; "
            "   all three have announced PQC roadmaps. Cloudflare already deployed hybrid KEX."
        ),
        tags=["certificate size", "CDN", "OCSP", "RFC 8879", "QUIC", "fragmentation"],
        depth="technical",
    ),
    QA(
        question="Q8. What does NIST SP 800-208 cover and when is SLH-DSA preferred over ML-DSA?",
        answer=(
            "NIST SP 800-208 (2020): 'Recommendation for Stateful Hash-Based Signature Schemes' "
            "covers LMS (Leighton-Micali Signature) and XMSS (eXtended Merkle Signature Scheme). "
            "These are STATEFUL: the signer must track a monotonically increasing state counter "
            "to avoid signing with the same one-time key twice (catastrophic if violated). "
            "\n"
            "FIPS 205 SLH-DSA (SPHINCS+) is STATELESS: no state to track, so no operational risk. "
            "SP 800-208 is a separate, earlier standard for specific use cases. "
            "\n"
            "When to prefer SLH-DSA over ML-DSA: "
            "  1. Conservative security model: SLH-DSA security depends ONLY on the hash "
            "     function (SHA-256, SHA-512, or SHAKE); no lattice math involved. "
            "     If lattice cryptanalysis advances, ML-DSA is more exposed. "
            "  2. Firmware signing (CNSA 2.0 mandates SLH-DSA-256s). "
            "  3. Long-lived signatures (code that must be verifiable in 30 years). "
            "  4. Very low signing frequency (SLH-DSA-128s: sign ~68ms but tiny keys 32B). "
            "\n"
            "When to prefer ML-DSA over SLH-DSA: "
            "  1. High-frequency signing: ML-DSA-65 sign = 0.59ms vs SLH-DSA-128s sign = 68ms. "
            "  2. Bandwidth-constrained: ML-DSA-65 sig = 3309B vs SLH-DSA-128s sig = 7856B. "
            "  3. Interactive protocols: TLS, SSH, JWT — must sign per-session. "
            "\n"
            "Practical split: use ML-DSA-65 for TLS/JWT/SSH; use SLH-DSA-256s for firmware/SW signing."
        ),
        tags=["SP 800-208", "SLH-DSA", "ML-DSA", "stateless", "firmware", "CNSA 2.0"],
        depth="technical",
    ),
    QA(
        question="Q9. How would you approach migrating a legacy COBOL mainframe application that uses RSA-1024 for inter-system auth?",
        answer=(
            "This is a common scenario in banking and insurance (IBM Z-series mainframes). "
            "Steps: "
            "\n"
            "1. CBOM audit: identify where RSA-1024 is called — RACF key rings, "
            "   GSKIT (IBM's SSL stack), application-level RSA calls in COBOL via "
            "   IBM Cryptographic Services Facility (ICSF). "
            "\n"
            "2. ICSF assessment: IBM has a PQC roadmap for ICSF; ML-KEM-768 and ML-DSA-65 "
            "   are planned for z/OS 3.1+ (2024-2025). "
            "\n"
            "3. Network boundary approach: if COBOL application talks to modern services over "
            "   TCP/IP, TLS-terminate at a modern API gateway (NGINX + OQS-OpenSSL) — the "
            "   mainframe sees TLS 1.2, the gateway presents TLS 1.3 PQC to the outside. "
            "   This is the 'PQC proxy' pattern and works without touching COBOL. "
            "\n"
            "4. RACF key migration: RACF can hold X.509 certificates in key rings. "
            "   IBM Key Management Interoperability Protocol (KMIP) updated for PQC "
            "   in IBM Security Key Lifecycle Manager 4.x. "
            "\n"
            "5. Application layer: if the COBOL calls are to encrypt/sign data (not TLS), "
            "   encapsulate in a PQC-capable microservice; COBOL calls the microservice "
            "   via CICS/MQ — mainframe doesn't change. "
            "\n"
            "Timeline: IBM Z mainframe PQC timeline 2025-2030; PQC proxy approach available now."
        ),
        tags=["mainframe", "COBOL", "ICSF", "IBM", "legacy", "PQC proxy"],
        depth="hands-on",
    ),
    QA(
        question="Q10. What is crypto agility and why is it a design principle, not just a PQC concern?",
        answer=(
            "Crypto agility is the ability to swap cryptographic algorithms in a system without "
            "architectural changes to the surrounding application logic. "
            "\n"
            "Why it matters beyond PQC: "
            "  - SHA-1 deprecation (2017): browsers had to remove SHA-1 cert support; "
            "    systems without crypto agility required major refactoring. "
            "  - MD5 collision attacks (2004-2012): certificate forgery was possible because "
            "    some CAs still issued MD5-signed certs. "
            "  - 3DES deprecation (Sweet32, 2016): TLS cipher suites needed update. "
            "  - RSA-512/1024: already considered broken classically. "
            "\n"
            "Design patterns for crypto agility: "
            "  1. Algorithm negotiation: TLS already does this (cipher_suites list). "
            "     Extend to PQC: supported_groups, signature_algorithms extensions. "
            "  2. Key abstraction: store 'key type + key material' not just key bytes. "
            "     PKCS#11, JCE, CNG all support this. "
            "  3. Algorithm registry: externalise algorithm selection to config "
            "     (e.g., crypto.properties in Java, openssl.cnf providers). "
            "  4. CBOM + automated scanning: detect algorithm usage via SAST/DAST tools "
            "     (IBM CBOM toolkit, Quantum Xchange Phio TX scanner). "
            "\n"
            "NIST IR 8547 (2024) formalizes the CBOM + agility requirement for federal systems. "
            "Cloud providers: AWS KMS, Azure Key Vault, GCP KMS all on PQC roadmaps for 2025."
        ),
        tags=["crypto agility", "design", "CBOM", "PKCS#11", "NIST IR 8547"],
        depth="conceptual",
    ),
]


# ─── Print helpers ────────────────────────────────────────────────────────────

def _print_section(title: str, qas: List[QA], tag_filter: str = None):
    filtered = [qa for qa in qas if tag_filter is None or tag_filter in qa.tags]
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)
    for qa in filtered:
        print(f"\n{'─'*80}")
        print(f"  {qa.question}")
        print(f"  Depth: {qa.depth}   Tags: {', '.join(qa.tags[:5])}")
        print(f"{'─'*80}")
        for line in qa.answer.split("\n"):
            print(f"  {line}")


def print_layer_perspective():
    """Print per-layer old/new perspective summary."""
    print("\n" + "=" * 80)
    print("  PER-LAYER: OLD vs NEW")
    print("=" * 80)
    layers = [
        ("TLS (Transport Layer Security)",
         "ECDHE + RSA/ECDSA cert — ECDHE broken by Shor's ECDLP; cert broken too",
         "X25519+ML-KEM-768 hybrid KEX (0x11EC) + ML-DSA-65 cert (IETF draft-ietf-tls-hybrid-design)"),
        ("SSH",
         "curve25519-sha256 KEX + Ed25519 host key — both broken by Shor's",
         "sntrup761x25519-sha512 (OpenSSH 9.0 default) + ssh-mldsa65 host key"),
        ("JWT / OAuth",
         "RS256 (RSA-2048) or ES256 (ECDSA-P256) — broken by Shor's; forged tokens possible",
         "ML-DSA-65 JWT (IETF draft-ietf-jose-fully-specified-algorithms); dual-token during transition"),
        ("VPN / IKEv2",
         "DH-2048 MODP (RFC 3526 Group 14) — DLP broken by Shor's",
         "ML-KEM-768 + X25519 Additional Key Exchange per RFC 9370; StrongSwan 5.9.8+"),
        ("PKI / X.509",
         "RSA-2048/4096 or ECDSA-P256/P384 certificates — signing key breakable",
         "ML-DSA-65 (L3) or ML-DSA-87 (L5/CNSA 2.0); OID 2.16.840.1.101.3.4.3.18"),
        ("Code Signing",
         "RSA-4096 Authenticode / ECDSA — forged signatures possible post-CRQC",
         "ML-DSA-87 + SLH-DSA-256s (CNSA 2.0 mandate); dual-sign during transition"),
        ("Database at-rest",
         "AES-128-CBC — Grover halves to 64-bit effective security",
         "AES-256-GCM — quantum-safe at 128-bit post-Grover; key rotation only"),
        ("HSM / Key Management",
         "RSA-2048 wrapping keys — wrapped key material breakable if wrapping key broken",
         "ML-KEM-768 encapsulation keys; IBM ICSF + AWS KMS PQC roadmap"),
    ]
    for layer, old, new in layers:
        print(f"\n  [{layer}]")
        print(f"    OLD: {old}")
        print(f"    NEW: {new}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("  PQC INTERVIEW PREPARATION")
    print("  Post-Quantum Cryptography: Migration, Architecture, and Protocol Depth")
    print("=" * 80)

    _print_section("PART 1: OLD SYSTEM — Classical Crypto Challenges (10 Q&As)",
                   OLD_SYSTEM_QA)

    _print_section("PART 2: NEW SYSTEM — PQC Migration & Solutions (10 Q&As)",
                   NEW_SYSTEM_QA)

    print_layer_perspective()

    print("\n" + "=" * 80)
    print("  QUICK REFERENCE: KEY FACTS FOR INTERVIEWS")
    print("=" * 80)
    facts = [
        "FIPS 203 = ML-KEM (Aug 2024) | FIPS 204 = ML-DSA (Aug 2024) | FIPS 205 = SLH-DSA (Aug 2024)",
        "ML-DSA-65 OID: 2.16.840.1.101.3.4.3.18  |  ML-KEM-768 OID: 2.16.840.1.101.3.4.4.2",
        "ML-DSA-65: PK=1952B, SK=4032B, Sig=3309B  |  ML-KEM-768: EK=1184B, CT=1088B",
        "RSA-2048 broken by Shor's with ~4000 logical qubits  |  ECDSA-P256 with ~2330 qubits",
        "AES-128 → 64-bit quantum security (Grover)  |  AES-256 → 128-bit quantum security (safe)",
        "TLS hybrid group: X25519+ML-KEM-768 = 0x11EC (draft-ietf-tls-ecdhe-mlkem)",
        "OpenSSH 9.0 default KEX: sntrup761x25519-sha512@openssh.com",
        "VPN PQC: RFC 9370 (IKEv2 Additional Key Exchange)  |  StrongSwan 5.9.8+",
        "CNSA 2.0 mandates ML-KEM-1024 + ML-DSA-87 + SLH-DSA-256s for NSS by 2030",
        "HNDL threat: data collected TODAY with ≥5yr retention is at risk from future CRQC",
        "CBOM = CycloneDX 1.4 Cryptographic Bill of Materials (NIST IR 8547)",
        "JWT size: RS256=~1.2KB  →  ML-DSA-65=~4.8KB  (4x larger due to sig)",
    ]
    for f in facts:
        print(f"  • {f}")

    print("\n  RECOMMENDED READING:")
    refs = [
        "NIST FIPS 203/204/205 (August 2024) — primary standards",
        "NSA CNSA 2.0 (September 2022) — NSS requirements",
        "NIST IR 8547 (2024) — PQC transition for federal systems",
        "NIST SP 800-208 (2020) — LMS/XMSS stateful hash-based signatures",
        "NIST SP 800-131Ar3 (draft 2024) — algorithm deprecation timeline",
        "RFC 9370 (2023) — IKEv2 Additional Key Exchange (PQC VPN)",
        "IETF draft-ietf-tls-hybrid-design — TLS 1.3 hybrid KEX",
        "IETF draft-ietf-tls-ecdhe-mlkem — X25519+ML-KEM-768 code points",
        "IETF draft-ietf-lamps-pq-composite-sigs — X.509 composite certs",
        "CycloneDX CBOM 1.4 schema — cryptographic inventory format",
    ]
    for r in refs:
        print(f"  → {r}")
    print("=" * 80)


if __name__ == "__main__":
    main()
