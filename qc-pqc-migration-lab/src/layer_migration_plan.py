LAYER_PLANS = {
    "L01": {
        "name": "Physical Layer PRNG",
        "category": "Cryptographic Primitives",
        "phase": "P2",
        "old": {"protocol": "IPsec/PRNG", "algorithm": "SW-PRNG", "standard": "FIPS140-2"},
        "issues": [
            "Software PRNG entropy insufficient for quantum-era key generation",
            "FIPS140-2 entropy source validation outdated",
            "No hardware entropy injection at physical layer",
        ],
        "quantum_threat": {"severity": "LOW", "algorithm": "None", "year": 2035},
        "steps": [
            "Audit current PRNG entropy sources",
            "Procure QRNG hardware modules (IDQ/Quantis)",
            "Integrate QRNG output into OS entropy pool",
            "Validate against FIPS140-3 entropy requirements",
            "Deploy and monitor entropy health dashboards",
        ],
        "new": {"algorithm": "QRNG+AES-256-CTR-DRBG", "standard": "FIPS140-3", "hybrid_period": False},
        "effort": "2 months",
        "monitoring": [
            "Entropy pool depth (bits/sec)",
            "QRNG hardware health heartbeat",
            "FIPS140-3 self-test pass rate",
        ],
        "interview": [
            "QRNG eliminates classical entropy harvesting lag and PRNG prediction surface",
            "FIPS140-3 mandates continuous health testing; FIPS140-2 only required periodic tests",
        ],
    },
    "L02": {
        "name": "MACsec Link Encryption",
        "category": "Link Layer Security",
        "phase": "P1",
        "old": {"protocol": "MACsec/AES-128+RSA-EAP", "algorithm": "AES-128-GCM+RSA-2048", "standard": "IEEE802.1AE"},
        "issues": [
            "RSA-2048 EAP handshake vulnerable to Shor's algorithm harvest-now-decrypt-later",
            "AES-128 key agreement phase uses classical DH exposed to quantum speedup",
            "No post-quantum Secure Association Key (SAK) negotiation path",
        ],
        "quantum_threat": {"severity": "HIGH", "algorithm": "Shor's", "year": 2030},
        "steps": [
            "Upgrade MACsec EAP to ML-KEM-768 for SAK negotiation",
            "Retain AES-256-GCM for data-plane encryption (quantum-safe with 256-bit)",
            "Patch 802.1X supplicant and authenticator for PQC key exchange",
            "Stage rollout per network segment with hybrid fallback",
            "Validate interoperability with updated IEEE802.1AEdk draft",
        ],
        "new": {"algorithm": "ML-KEM-768 SAK + AES-256-GCM", "standard": "IEEE802.1AE+PQC-draft", "hybrid_period": True},
        "effort": "3 months",
        "monitoring": [
            "SAK renegotiation latency (ms)",
            "ML-KEM handshake error rate",
            "AES-256-GCM rekey frequency compliance",
        ],
        "interview": [
            "MACsec data plane is already quantum-safe with AES-256; only the key agreement needs PQC",
            "Hybrid period preserves IEEE802.1AE interop while PQC firmware matures across vendors",
        ],
    },
    "L03": {
        "name": "IPsec VPN Tunnels",
        "category": "Network Layer Encryption",
        "phase": "P0",
        "old": {"protocol": "IKEv2/DH-2048+RSA", "algorithm": "DH-2048+RSA-2048", "standard": "RFC7296"},
        "issues": [
            "IKEv2 DH-2048 key exchange fully broken by Shor's in future CRQC",
            "RSA authentication signature vulnerable to quantum factoring",
            "Harvest-now-decrypt-later attacks ongoing against captured IKE traffic",
        ],
        "quantum_threat": {"severity": "CRITICAL", "algorithm": "Shor's", "year": 2029},
        "steps": [
            "Enable ML-KEM-1024 KEM in IKEv2 via RFC9370 Additional Key Exchanges",
            "Replace RSA auth with ML-DSA-87 signatures per RFC9242",
            "Run hybrid DH+ML-KEM during transition for classical fallback",
            "Update StrongSwan/Libreswan to PQC-capable builds",
            "Regression-test all site-to-site and remote-access profiles",
        ],
        "new": {"algorithm": "ML-KEM-1024+ML-DSA-87", "standard": "RFC9242+RFC9370", "hybrid_period": True},
        "effort": "4 months",
        "monitoring": [
            "IKEv2 rekey latency with ML-KEM overhead (ms)",
            "SA establishment failure rate",
            "Hybrid fallback activation count (should trend to zero)",
        ],
        "interview": [
            "RFC9370 enables multiple KEMs in one IKEv2 exchange—no protocol redesign needed",
            "ML-DSA-87 (CRYSTALS-Dilithium) provides 256-bit post-quantum security for IKE auth",
        ],
    },
    "L04": {
        "name": "TLS 1.3 Transport",
        "category": "Transport Layer Security",
        "phase": "P0",
        "old": {"protocol": "TLS1.3/ECDHE+ECDSA", "algorithm": "X25519+ECDSA-P256", "standard": "RFC8446"},
        "issues": [
            "X25519 ECDH key exchange broken by Shor's algorithm on CRQC",
            "ECDSA certificate signatures vulnerable to quantum discrete-log attack",
            "HNDL attacks harvest TLS sessions now for future quantum decryption",
        ],
        "quantum_threat": {"severity": "CRITICAL", "algorithm": "Shor's", "year": 2029},
        "steps": [
            "Add X25519+ML-KEM-768 hybrid key share in ClientHello (IETF draft-ietf-tls-hybrid-design)",
            "Issue dual-cert chain: ECDSA leaf + ML-DSA-65 intermediate for compatibility",
            "Enable hybrid in reverse proxies (Nginx/Envoy) with BoringSSL-OQS or OpenSSL-OQS",
            "Run A/B traffic split: PQC-capable clients get hybrid, legacy get classical",
            "Cut over fully once >95% client PQC support confirmed",
        ],
        "new": {"algorithm": "X25519+ML-KEM-768 hybrid", "standard": "IETF-draft-tls-hybrid", "hybrid_period": True},
        "effort": "3 months",
        "monitoring": [
            "PQC handshake success rate vs classical fallback rate",
            "TLS ClientHello processing latency delta (ms)",
            "Certificate validation error rate post-swap",
        ],
        "interview": [
            "Hybrid X25519+ML-KEM-768 is IETF-recommended: classical security if PQC is broken, PQC safety if classical is broken",
            "BoringSSL-OQS and OpenSSL-OQS forks allow drop-in PQC without full TLS stack rewrite",
        ],
    },
    "L05": {
        "name": "Session Management",
        "category": "Session Layer",
        "phase": "P1",
        "old": {"protocol": "TLS-tickets/RSA-2048", "algorithm": "RSA-2048 ticket encryption", "standard": "RFC5077"},
        "issues": [
            "TLS session ticket keys encrypted with RSA-2048 broken by Shor's",
            "Long-lived tickets extend HNDL attack window beyond typical TLS session",
            "Session resumption bypasses PQC handshake if ticket key not migrated",
        ],
        "quantum_threat": {"severity": "HIGH", "algorithm": "Shor's", "year": 2030},
        "steps": [
            "Replace RSA-2048 ticket encryption key with ML-KEM-768 wrapping",
            "Reduce ticket lifetime from 24h to 4h to shrink HNDL window",
            "Invalidate all existing RSA-encrypted tickets on cutover day",
            "Implement ticket key rotation every 6 hours with automated HSM-backed rekey",
            "Monitor session resumption rates to detect client compatibility issues",
        ],
        "new": {"algorithm": "ML-KEM-768 ticket wrap + AES-256-GCM", "standard": "RFC5077+PQC-ext", "hybrid_period": False},
        "effort": "2 months",
        "monitoring": [
            "Session ticket cache hit rate",
            "Ticket decryption failure rate",
            "Average session key age (hours)",
        ],
        "interview": [
            "Session ticket migration is often overlooked—tickets can re-expose plaintext even after TLS handshake is PQC-upgraded",
            "Shorter ticket lifetimes are the zero-code risk reducer while ML-KEM wrapping is deployed",
        ],
    },
    "L06": {
        "name": "PKI / Certificate Authority",
        "category": "Public Key Infrastructure",
        "phase": "P0",
        "old": {"protocol": "X.509/RSA-4096", "algorithm": "RSA-4096", "standard": "RFC5280"},
        "issues": [
            "RSA-4096 root and intermediate CA keys broken by Shor's on CRQC",
            "All downstream certificates inherit quantum vulnerability from CA chain",
            "No current X.509 profile supports ML-DSA OIDs in standard PKI tooling",
        ],
        "quantum_threat": {"severity": "CRITICAL", "algorithm": "Shor's", "year": 2029},
        "steps": [
            "Stand up new PQC Root CA with ML-DSA-65 (OID per NIST-SP-800-208)",
            "Issue PQC Intermediate CAs cross-signed by existing RSA root for hybrid trust",
            "Migrate leaf cert issuance to ML-DSA-65; keep RSA leaf certs in parallel",
            "Update CRL/OCSP infrastructure to sign responses with ML-DSA",
            "Hard-cutover Root CA once all relying parties support PQC X.509",
        ],
        "new": {"algorithm": "ML-DSA-65", "standard": "NIST-SP-800-208+RFC5280-PQC", "hybrid_period": True},
        "effort": "6 months",
        "monitoring": [
            "PQC cert issuance ratio vs RSA cert issuance ratio",
            "OCSP response signing latency (ms)",
            "CRL download size delta (ML-DSA sigs are larger)",
        ],
        "interview": [
            "PKI migration is the critical path—every other layer's PQC upgrade depends on a functioning PQC CA chain",
            "Cross-signed hybrid roots enable zero-downtime transition: old relying parties trust RSA chain, new trust ML-DSA chain",
        ],
    },
    "L07": {
        "name": "HTTPS Application Layer",
        "category": "Application Protocol Security",
        "phase": "P0",
        "old": {"protocol": "HTTPS/RSA+ECDSA", "algorithm": "RSA-2048/ECDSA-P256 certs", "standard": "RFC9110"},
        "issues": [
            "ECDSA leaf certificates broken by Shor's discrete-log attack",
            "RSA server authentication fully broken by quantum factoring",
            "Web PKI trust anchors (browser roots) must accept ML-DSA before HTTPS is quantum-safe",
        ],
        "quantum_threat": {"severity": "CRITICAL", "algorithm": "Shor's", "year": 2029},
        "steps": [
            "Obtain ML-DSA-65 server certificate from PQC-capable CA",
            "Configure Nginx/Apache/Envoy to serve hybrid TLS with PQC cert",
            "Submit ML-DSA root to major browser root programs (Apple, Mozilla, Google)",
            "Enable HSTS with long max-age to prevent downgrade to classical",
            "Monitor CT logs for unauthorized classical cert issuance post-migration",
        ],
        "new": {"algorithm": "Hybrid TLS + ML-DSA-65 cert", "standard": "RFC9110+IETF-draft-tls-hybrid", "hybrid_period": True},
        "effort": "4 months",
        "monitoring": [
            "Browser PQC negotiation success rate",
            "HSTS header presence rate across all endpoints",
            "CT log anomaly count for domain",
        ],
        "interview": [
            "HTTPS PQC depends on browser root program acceptance of ML-DSA—timeline is a browser vendor dependency, not just internal PKI",
            "Hybrid TLS (X25519+ML-KEM-768) protects key exchange today; ML-DSA cert protects server auth",
        ],
    },
    "L08": {
        "name": "JWT / API Auth Tokens",
        "category": "Identity & Access Tokens",
        "phase": "P0",
        "old": {"protocol": "JWT/RS256 RSA-2048", "algorithm": "RS256 (RSA-2048)", "standard": "RFC7519"},
        "issues": [
            "RS256 RSA-2048 JWT signatures broken by Shor's factoring attack",
            "Long-lived JWTs (24h+) extend the harvest-now window significantly",
            "JOSE ecosystem (libraries) lacks stable ML-DSA algorithm identifiers",
        ],
        "quantum_threat": {"severity": "CRITICAL", "algorithm": "Shor's", "year": 2029},
        "steps": [
            "Register ML-DSA-65 algorithm identifier in JOSE draft (draft-ietf-jose-pqc-kem)",
            "Update token signing service to use ML-DSA-65 private key from HSM",
            "Shorten JWT TTL to 1 hour to limit HNDL window during hybrid period",
            "Update all relying parties to verify ML-DSA-65 signatures",
            "Deprecate RS256 issuer key after all consumers migrated",
        ],
        "new": {"algorithm": "ML-DSA-65 (JOSE-PQC)", "standard": "JOSE-draft-ietf-jose-pqc", "hybrid_period": True},
        "effort": "3 months",
        "monitoring": [
            "JWT signing latency (ML-DSA-65 vs RS256 baseline ms)",
            "Token verification failure rate at relying parties",
            "Proportion of tokens signed with ML-DSA vs RS256",
        ],
        "interview": [
            "JWTs are a silent HNDL vector—signed tokens captured today can be forged later once RSA keys are broken",
            "ML-DSA-65 signatures are ~3.3KB vs RS256 ~256B; payload size impact must be measured on API gateways",
        ],
    },
    "L09": {
        "name": "DNSSEC",
        "category": "DNS Security",
        "phase": "P1",
        "old": {"protocol": "DNSSEC/RSA-2048", "algorithm": "RSASHA256/RSA-2048", "standard": "RFC4033"},
        "issues": [
            "RSASHA256 ZSK and KSK broken by Shor's factoring on CRQC",
            "DNS response forgery enables BGP-level MitM if DNSSEC is compromised",
            "Falcon-512 signatures increase DNS response size beyond UDP 512B limit",
        ],
        "quantum_threat": {"severity": "CRITICAL", "algorithm": "Shor's", "year": 2030},
        "steps": [
            "Adopt Falcon-512 as DNSSEC signing algorithm (IETF-PQC-DNSSEC draft)",
            "Increase EDNS0 buffer size to 4096 to accommodate larger PQC signatures",
            "Perform algorithm rollover per RFC6781: add Falcon ZSK, dual-sign zone, retire RSA ZSK",
            "Coordinate KSK rollover with parent zone registrar for DS record update",
            "Enable DNS-over-TLS/HTTPS with PQC TLS to protect query privacy",
        ],
        "new": {"algorithm": "Falcon-512", "standard": "IETF-draft-ietf-dnsop-dnssec-pqc", "hybrid_period": True},
        "effort": "4 months",
        "monitoring": [
            "DNSSEC validation success rate",
            "DNS response size distribution (flag large responses >1500B)",
            "Zone signing key rollover duration (days)",
        ],
        "interview": [
            "DNSSEC PQC rollover is operationally complex—RFC6781 dual-signing must be followed exactly to avoid validation failures",
            "Falcon-512 was chosen over ML-DSA for DNSSEC due to smaller signature size (~690B vs ~2.4KB), critical for DNS",
        ],
    },
    "L10": {
        "name": "SSH Remote Access",
        "category": "Remote Access Protocol",
        "phase": "P0",
        "old": {"protocol": "SSH-2/RSA+ECDH", "algorithm": "RSA-2048+curve25519-sha256", "standard": "RFC4251"},
        "issues": [
            "curve25519-sha256 ECDH key exchange broken by Shor's on CRQC",
            "RSA host keys and user auth keys vulnerable to quantum factoring",
            "SSH sessions recorded now can be decrypted post-CRQC (HNDL)",
        ],
        "quantum_threat": {"severity": "CRITICAL", "algorithm": "Shor's", "year": 2029},
        "steps": [
            "Upgrade to OpenSSH 9.0+ which ships sntrup761x25519-sha512 hybrid KEX by default",
            "Generate ML-DSA-65 host keys and add to known_hosts / SSHFP DNS records",
            "Migrate user auth from RSA keys to ML-DSA-65 keys",
            "Enforce sntrup761 KEX via sshd_config KexAlgorithms directive",
            "Rotate all legacy RSA host keys after migration window closes",
        ],
        "new": {"algorithm": "sntrup761+ML-DSA-65", "standard": "OpenSSH9.0+IETF-sshpqc-draft", "hybrid_period": True},
        "effort": "2 months",
        "monitoring": [
            "sntrup761 KEX negotiation success rate",
            "RSA key auth attempt rate (should trend to zero)",
            "SSH session establishment latency delta (ms)",
        ],
        "interview": [
            "OpenSSH 9.0 ships sntrup761 hybrid by default—SSH is one of the easiest PQC wins, just upgrade the binary",
            "Host key migration requires SSHFP DNS record updates and known_hosts fleet rotation—often underestimated effort",
        ],
    },
    "L11": {
        "name": "Email Security (S/MIME + PGP)",
        "category": "Email Security",
        "phase": "P2",
        "old": {"protocol": "S/MIME+PGP/RSA-4096", "algorithm": "RSA-4096+AES-256", "standard": "RFC5751"},
        "issues": [
            "RSA-4096 S/MIME and PGP key encryption broken by Shor's",
            "Long-term email archives harvested today decryptable post-CRQC",
            "OpenPGP PQC standard still in draft; MUA support minimal",
        ],
        "quantum_threat": {"severity": "CRITICAL", "algorithm": "Shor's", "year": 2031},
        "steps": [
            "Generate ML-DSA-65+ML-KEM-768 PGP keys per OpenPGP-PQC draft",
            "Publish PQC keys to keyservers alongside existing RSA keys (dual-key period)",
            "Update MUA (Thunderbird, Evolution) to PQC-capable plugin versions",
            "Re-encrypt long-term email archives with ML-KEM-768 session keys",
            "Deprecate RSA PGP keys once all frequent correspondents support PQC",
        ],
        "new": {"algorithm": "ML-DSA-65+ML-KEM-768", "standard": "draft-ietf-openpgp-pqc", "hybrid_period": True},
        "effort": "5 months",
        "monitoring": [
            "PQC key adoption rate among email contacts",
            "Email encryption fallback-to-RSA rate",
            "Archive re-encryption job completion percentage",
        ],
        "interview": [
            "Email has the worst HNDL profile—messages are stored for years, so harvest-now-decrypt-later is not theoretical",
            "OpenPGP PQC draft is not yet RFC; deploying requires careful version negotiation to avoid decrypt failures",
        ],
    },
    "L12": {
        "name": "Code Signing",
        "category": "Software Supply Chain",
        "phase": "P1",
        "old": {"protocol": "GPG+cosign/RSA+ECDSA", "algorithm": "RSA-4096+ECDSA-P256", "standard": "RFC4880"},
        "issues": [
            "ECDSA code signatures broken by Shor's—malicious code could be backdated and forged",
            "RSA GPG signing keys for package repositories vulnerable to quantum factoring",
            "cosign ECDSA transparency log entries insufficient once ECDSA is broken",
        ],
        "quantum_threat": {"severity": "CRITICAL", "algorithm": "Shor's", "year": 2030},
        "steps": [
            "Generate ML-DSA-65 GPG signing key for package repository",
            "Update cosign to use ML-DSA-65 signing (sigstore/cosign PQC branch)",
            "Re-sign all existing release artifacts with ML-DSA-65 key",
            "Distribute updated trust anchors (public keys) to all build pipelines",
            "Enforce PQC signature verification in CI/CD gate checks",
        ],
        "new": {"algorithm": "ML-DSA-65", "standard": "NIST-FIPS-204+sigstore-pqc", "hybrid_period": True},
        "effort": "3 months",
        "monitoring": [
            "PQC signature verification pass rate in CI/CD",
            "Legacy ECDSA signature acceptance rate (should trend to zero)",
            "Signing key HSM utilization and latency (ms)",
        ],
        "interview": [
            "Code signing is supply-chain critical—a forged quantum-era signature on a malicious binary is an undetectable attack",
            "Re-signing past artifacts with ML-DSA creates a clean forward-looking provenance chain even if old ECDSA sigs are later broken",
        ],
    },
    "L13": {
        "name": "VPN Infrastructure",
        "category": "Network Security",
        "phase": "P0",
        "old": {"protocol": "WireGuard+OpenVPN/Curve25519+DH", "algorithm": "Curve25519+DH-2048", "standard": "RFC8902"},
        "issues": [
            "WireGuard Curve25519 handshake broken by Shor's on CRQC",
            "OpenVPN DH-2048 key agreement fully quantum-vulnerable",
            "All VPN tunnel traffic subject to HNDL harvest attacks",
        ],
        "quantum_threat": {"severity": "CRITICAL", "algorithm": "Shor's", "year": 2029},
        "steps": [
            "Apply WireGuard-PQ patch (wireguard-pq) to replace Curve25519 with ML-KEM-768 hybrid",
            "Update OpenVPN to 2.7+ with ML-KEM TLS 1.3 integration",
            "Regenerate all VPN peer static keys using ML-DSA-65 for authentication",
            "Deploy hybrid configuration: ML-KEM+Curve25519 during transition",
            "Validate split-tunnel and full-tunnel traffic flows post-migration",
        ],
        "new": {"algorithm": "WG-PQ-patch+ML-KEM-768", "standard": "RFC8902+WG-PQ-draft", "hybrid_period": True},
        "effort": "3 months",
        "monitoring": [
            "VPN handshake latency with ML-KEM overhead (ms)",
            "Tunnel establishment failure rate",
            "Hybrid fallback to classical negotiation rate",
        ],
        "interview": [
            "WireGuard's minimalist design makes PQC patching easier than OpenVPN—fewer crypto negotiation states",
            "VPN infrastructure often protects the most sensitive inter-datacenter traffic—P0 priority for HNDL protection",
        ],
    },
    "L14": {
        "name": "Hardware Security Modules",
        "category": "Key Management Hardware",
        "phase": "P0",
        "old": {"protocol": "PKCS11/RSA-4096-wrap", "algorithm": "RSA-4096 key wrapping", "standard": "FIPS140-2"},
        "issues": [
            "RSA-4096 key wrapping in HSM broken by Shor's—wrapped keys exposed post-CRQC",
            "FIPS140-2 validation does not cover ML-KEM/ML-DSA algorithms",
            "HSM firmware update cycle often 12-18 months; PQC support requires vendor roadmap alignment",
        ],
        "quantum_threat": {"severity": "CRITICAL", "algorithm": "Shor's", "year": 2029},
        "steps": [
            "Obtain FIPS140-3 validated HSM with ML-KEM-768 and ML-DSA-65 support (Thales/Utimaco/AWS-CloudHSM)",
            "Migrate all key wrapping from RSA-4096 to ML-KEM-768",
            "Re-enroll all application credentials against new PQC HSM partitions",
            "Update PKCS#11 shim layer to expose ML-KEM/ML-DSA mechanisms",
            "Zeroize and decommission FIPS140-2 RSA key material",
        ],
        "new": {"algorithm": "ML-KEM-768 wrap+ML-DSA-65", "standard": "FIPS140-3+PKCS11-PQC", "hybrid_period": False},
        "effort": "6 months",
        "monitoring": [
            "HSM key operation throughput (ops/sec) under ML-KEM load",
            "Key wrapping operation latency (ms) vs RSA baseline",
            "FIPS140-3 continuous self-test failure rate",
        ],
        "interview": [
            "HSM is the trust anchor for all crypto—if HSM key wrapping is broken, every derived key is compromised regardless of algorithm",
            "FIPS140-3 validation lag for new HSM firmware is the #1 procurement risk; start vendor conversations 18 months ahead",
        ],
    },
    "L15": {
        "name": "Identity & Access Management",
        "category": "IAM / Federation",
        "phase": "P1",
        "old": {"protocol": "SAML+OIDC/RSA-2048", "algorithm": "RSA-2048 SAML assertions+OIDC id_token", "standard": "SAML2.0"},
        "issues": [
            "SAML assertion signatures (RSA-2048) broken by Shor's—identity forgery post-CRQC",
            "OIDC id_token RS256 signing vulnerable to quantum factoring",
            "IdP metadata exchange uses RSA encryption; entire federation chain exposed",
        ],
        "quantum_threat": {"severity": "CRITICAL", "algorithm": "Shor's", "year": 2030},
        "steps": [
            "Update IdP (Keycloak/Okta) to sign SAML assertions with ML-DSA-65",
            "Switch OIDC id_token signing to ML-DSA-65 JOSE algorithm",
            "Re-publish IdP metadata with PQC signing certificate",
            "Update all SP metadata to trust PQC signing certs",
            "Enforce PQC assertion signatures in SP validation logic",
        ],
        "new": {"algorithm": "ML-DSA-65 SAML+JOSE-PQC OIDC", "standard": "SAML2.0+JOSE-PQC-draft", "hybrid_period": True},
        "effort": "4 months",
        "monitoring": [
            "SAML assertion validation success rate with ML-DSA signatures",
            "OIDC token issuance latency delta (ms)",
            "SP federation error rate during hybrid rollout",
        ],
        "interview": [
            "SAML and OIDC are identity federation fabrics—quantum-forged assertions grant lateral movement across entire enterprise",
            "Keycloak 23+ has ML-DSA JOSE support in experimental mode; production readiness assessment is required before rollout",
        ],
    },
    "L16": {
        "name": "API Gateway Security",
        "category": "API Security",
        "phase": "P0",
        "old": {"protocol": "OAuth2+mTLS/RS256+ECDSA", "algorithm": "RS256 JWT+ECDSA mTLS", "standard": "RFC6749"},
        "issues": [
            "RS256 OAuth2 access token signatures broken by Shor's",
            "ECDSA mTLS client certificates vulnerable to quantum discrete-log attack",
            "API gateway is the control plane entry—quantum compromise enables full lateral movement",
        ],
        "quantum_threat": {"severity": "CRITICAL", "algorithm": "Shor's", "year": 2029},
        "steps": [
            "Replace RS256 OAuth2 JWT signing with ML-DSA-65 (JOSE-PQC draft)",
            "Reissue all mTLS client certificates with ML-DSA-65 from PQC CA",
            "Update Kong/Apigee/AWS-APIGW to validate ML-DSA JWT and mTLS certs",
            "Implement hybrid JWT: dual-sign RS256+ML-DSA during transition",
            "Revoke all ECDSA mTLS client certs after PQC certs deployed",
        ],
        "new": {"algorithm": "ML-DSA-65 JWT+ML-DSA mTLS", "standard": "RFC6749+JOSE-PQC-draft", "hybrid_period": True},
        "effort": "3 months",
        "monitoring": [
            "API gateway JWT validation error rate",
            "mTLS handshake failure rate post-cert rotation",
            "ML-DSA signature verification throughput (req/sec)",
        ],
        "interview": [
            "API gateway is the quantum attack blast radius multiplier—one broken RS256 key compromises all API consumers",
            "Dual-sign JWT (RS256+ML-DSA-65) enables zero-downtime migration: old clients verify RS256, new clients verify ML-DSA-65",
        ],
    },
    "L17": {
        "name": "Database Encryption (TDE)",
        "category": "Data at Rest Encryption",
        "phase": "P1",
        "old": {"protocol": "TDE+TLS/AES-256+RSA-backup", "algorithm": "AES-256-CBC TDE + RSA-2048 backup key wrap", "standard": "FIPS140-2"},
        "issues": [
            "RSA-2048 backup encryption key wrap broken by Shor's—database backup decryptable post-CRQC",
            "TDE key escrow often uses RSA wrapping in external KMS—PQC gap if KMS not updated",
            "AES-256 data encryption itself is quantum-safe (Grover halves to 128-bit—still acceptable)",
        ],
        "quantum_threat": {"severity": "MEDIUM", "algorithm": "Grover's", "year": 2035},
        "steps": [
            "Retain AES-256-CBC/GCM for TDE data encryption (quantum-safe with current key size)",
            "Replace RSA-2048 backup key wrap with ML-KEM-768 in KMS",
            "Update TDE key escrow export format to use ML-KEM-768 wrapped envelope",
            "Validate backup/restore roundtrip with ML-KEM-wrapped keys",
            "Audit all database backup scripts for hardcoded RSA key references",
        ],
        "new": {"algorithm": "AES-256-GCM TDE + ML-KEM-768 backup wrap", "standard": "FIPS140-3", "hybrid_period": False},
        "effort": "2 months",
        "monitoring": [
            "Backup encryption job completion time with ML-KEM wrap",
            "TDE key rotation success rate",
            "Backup restore test latency (hrs) quarterly",
        ],
        "interview": [
            "AES-256 TDE is already quantum-safe for data at rest—only the key wrapping layer needs PQC, not the full TDE re-key",
            "Grover's attack halves AES key security: AES-256→128-bit effective, AES-128→64-bit effective (unacceptable); AES-256 is the threshold",
        ],
    },
    "L18": {
        "name": "Blockchain / Distributed Ledger",
        "category": "Distributed Systems Security",
        "phase": "P0",
        "old": {"protocol": "ECDSA-secp256k1", "algorithm": "ECDSA-secp256k1", "standard": "EIP-155"},
        "issues": [
            "ECDSA-secp256k1 wallet signatures fully broken by Shor's—all assets transferable by attacker",
            "Exposed public keys (spent UTXO/addresses) enable retrospective key recovery on CRQC",
            "Blockchain immutability means old transactions can be replayed with forged signatures",
        ],
        "quantum_threat": {"severity": "CRITICAL", "algorithm": "Shor's", "year": 2029},
        "steps": [
            "Define Falcon-512 transaction signature scheme for chain-level upgrade (EIP/BIP proposal)",
            "Implement parallel Falcon-512 signature verification in validator nodes",
            "Migrate wallet key generation to Falcon-512 with address scheme update",
            "Enforce mandatory migration deadline: all ECDSA addresses must be migrated by block N",
            "Burn/freeze ECDSA-only addresses post-deadline to prevent quantum theft",
        ],
        "new": {"algorithm": "Falcon-512", "standard": "PQC-BIP/EIP-proposal", "hybrid_period": True},
        "effort": "12 months",
        "monitoring": [
            "PQC wallet adoption rate (% of addresses migrated)",
            "Falcon-512 transaction validation throughput (tx/sec)",
            "Legacy ECDSA transaction ratio in mempool",
        ],
        "interview": [
            "Blockchain is uniquely risky: all public keys are on-chain and permanently exposed—Shor's attack is replay, not just future interception",
            "Falcon-512 was selected over ML-DSA for blockchain due to smaller signature size (~690B)—critical for on-chain storage cost",
        ],
    },
    "L19": {
        "name": "Container / Service Mesh Security",
        "category": "Cloud-Native Security",
        "phase": "P0",
        "old": {"protocol": "Istio-mTLS/ECDSA", "algorithm": "ECDSA-P256 SVIDs+mTLS", "standard": "SPIFFE"},
        "issues": [
            "Istio ECDSA SVID certificates broken by Shor's—lateral movement across all service mesh",
            "SPIFFE workload identity depends on ECDSA signing in intermediate CA",
            "High cert rotation frequency (1hr TTL) helps but does not eliminate HNDL risk",
        ],
        "quantum_threat": {"severity": "CRITICAL", "algorithm": "Shor's", "year": 2029},
        "steps": [
            "Configure SPIRE to issue ML-DSA-65 SVIDs for all workload identities",
            "Update Istio control plane (istiod) to validate ML-DSA SVID signatures",
            "Re-issue all sidecar proxy certificates with ML-DSA-65 from PQC intermediate CA",
            "Enable hybrid mTLS during rollout: sidecar accepts both ECDSA and ML-DSA SVIDs",
            "Force-rotate all ECDSA SVIDs after mesh-wide ML-DSA rollout confirmed",
        ],
        "new": {"algorithm": "ML-DSA-65 SVIDs+PQC mTLS", "standard": "SPIFFE+NIST-FIPS-204", "hybrid_period": True},
        "effort": "4 months",
        "monitoring": [
            "SVID rotation success rate per workload",
            "mTLS connection establishment latency with ML-DSA (ms)",
            "SPIRE attestation failure rate",
        ],
        "interview": [
            "Service mesh is the east-west control plane—quantum-compromised SVIDs enable silent lateral movement between every microservice",
            "SPIRE's pluggable CA interface makes ML-DSA-65 SVID issuance feasible without full Istio fork",
        ],
    },
    "L20": {
        "name": "IoT / Edge Device Security",
        "category": "Embedded & IoT Security",
        "phase": "P2",
        "old": {"protocol": "DTLS1.2/ECC+RSA", "algorithm": "ECC-P256+RSA-2048", "standard": "RFC6347"},
        "issues": [
            "DTLS 1.2 ECC handshake broken by Shor's on CRQC",
            "IoT devices often have 5-10 year lifespans—CRQC arrives before natural device replacement",
            "Constrained devices (Cortex-M0+) may lack compute for ML-KEM/Falcon without hardware accel",
        ],
        "quantum_threat": {"severity": "CRITICAL", "algorithm": "Shor's", "year": 2031},
        "steps": [
            "Evaluate Falcon-512 on target MCU class (benchmark cycles/key-op)",
            "Adopt DTLS 1.3 with ML-KEM-512 (lower security level for constrained devices)",
            "Implement over-the-air (OTA) firmware update with ML-DSA-65 signed images",
            "Deploy edge gateway as PQC termination proxy for legacy devices that can't be upgraded",
            "Define device EOL policy: no new DTLS1.2 ECC devices after 2027",
        ],
        "new": {"algorithm": "Falcon-512+DTLS1.3+ML-KEM-512", "standard": "NIST-SP-800-213+RFC9147", "hybrid_period": True},
        "effort": "8 months",
        "monitoring": [
            "OTA update success rate with ML-DSA signed firmware",
            "DTLS 1.3 handshake latency on constrained devices (ms)",
            "PQC-capable device ratio in fleet",
        ],
        "interview": [
            "IoT is the hardest PQC problem: long device lifetimes + constrained compute + no easy in-field upgrade path",
            "PQC gateway proxy pattern is the pragmatic bridge: upgrade infrastructure, proxy for legacy devices, enforce device EOL policy",
        ],
    },
    "L21": {
        "name": "Mobile App Security",
        "category": "Mobile Security",
        "phase": "P2",
        "old": {"protocol": "CertPin+FIDO2/ECDSA", "algorithm": "ECDSA-P256 attestation+cert pin", "standard": "FIDO2"},
        "issues": [
            "FIDO2 ECDSA authenticator attestation broken by Shor's—device registration forgeable post-CRQC",
            "Certificate pinning with ECDSA pins becomes invalid after quantum cert migration",
            "FIDO Alliance ML-DSA FIDO2 spec still in development—no shipping authenticators yet",
        ],
        "quantum_threat": {"severity": "HIGH", "algorithm": "Shor's", "year": 2032},
        "steps": [
            "Track FIDO Alliance PQC working group output for ML-DSA FIDO2 authenticator spec",
            "Update mobile app TLS pinning to accept both ECDSA and ML-DSA cert chains (hybrid pins)",
            "Implement app-layer ML-DSA signature for sensitive API requests as interim measure",
            "Prepare mobile SDK update pipeline for rapid PQC cert pin rollout",
            "Migrate to ML-DSA FIDO2 authenticators once hardware/spec finalizes (est. 2026-2027)",
        ],
        "new": {"algorithm": "ML-DSA-65 FIDO2 (in-dev)", "standard": "FIDO2-PQC-draft", "hybrid_period": True},
        "effort": "6 months",
        "monitoring": [
            "App TLS pin validation failure rate during hybrid period",
            "Mobile FIDO2 authentication success rate",
            "PQC-capable authenticator adoption rate in user base",
        ],
        "interview": [
            "Mobile PQC is hardware-gated: ML-DSA FIDO2 requires secure enclave firmware updates from Apple/Google—external dependency",
            "Hybrid pinning (accept both ECDSA and ML-DSA chains) prevents cert-pin breakage during TLS migration",
        ],
    },
    "L22": {
        "name": "Firmware / UEFI Secure Boot",
        "category": "Platform Integrity",
        "phase": "P1",
        "old": {"protocol": "UEFI/RSA-2048", "algorithm": "RSA-2048 Secure Boot signing", "standard": "UEFI-spec"},
        "issues": [
            "RSA-2048 UEFI Secure Boot signing key broken by Shor's—malicious firmware injectable post-CRQC",
            "Platform Key (PK) and Key Exchange Keys (KEK) use RSA—full boot chain compromised",
            "UEFI db/dbx update mechanism must be modified to carry ML-DSA-65 signatures",
        ],
        "quantum_threat": {"severity": "CRITICAL", "algorithm": "Shor's", "year": 2030},
        "steps": [
            "Generate ML-DSA-65 Platform Key and enroll in UEFI firmware (NIST-SP-800-193)",
            "Update OEM/ODM firmware signing pipeline to use ML-DSA-65",
            "Publish updated UEFI Secure Boot db with ML-DSA-65 signed boot managers",
            "Deploy firmware update across device fleet via LVFS/fwupd PQC-signed capsules",
            "Revoke RSA-2048 PK from UEFI db after all devices migrated",
        ],
        "new": {"algorithm": "ML-DSA-65 UEFI Secure Boot", "standard": "NIST-SP-800-193+UEFI-PQC", "hybrid_period": True},
        "effort": "9 months",
        "monitoring": [
            "Secure Boot validation failure rate post-migration",
            "Firmware update capsule delivery success rate",
            "RSA Secure Boot fallback count (should be zero after cutover)",
        ],
        "interview": [
            "UEFI Secure Boot migration is platform-level: requires OEM cooperation to re-sign firmware with ML-DSA-65",
            "A compromised Secure Boot chain is pre-OS—no amount of OS-level PQC protects against a quantum-forged bootloader",
        ],
    },
    "L23": {
        "name": "DevSecOps Pipeline",
        "category": "CI/CD Security",
        "phase": "P1",
        "old": {"protocol": "GPG+Vault/RSA+ECDSA", "algorithm": "RSA-4096 GPG+ECDSA Vault transit", "standard": "RFC4880"},
        "issues": [
            "HashiCorp Vault transit engine RSA/ECDSA keys broken by Shor's—secret wrapping compromised",
            "GPG signing keys for CI artifact attestation vulnerable to quantum factoring",
            "Pipeline secrets transmitted via RSA-wrapped channels subject to HNDL",
        ],
        "quantum_threat": {"severity": "HIGH", "algorithm": "Shor's", "year": 2030},
        "steps": [
            "Enable Vault ML-KEM-768 transit key type (requires Vault 1.16+ with PQC plugin)",
            "Migrate CI pipeline GPG signing to ML-DSA-65 keys",
            "Re-encrypt all Vault-stored secrets with ML-KEM-768 wrapping",
            "Update GitHub Actions/GitLab CI secret injection to use ML-KEM-wrapped envelopes",
            "Audit all pipeline yaml for hardcoded RSA-wrapped secret references",
        ],
        "new": {"algorithm": "ML-DSA-65 GPG+ML-KEM-768 Vault", "standard": "RFC4880-PQC+Vault-PQC", "hybrid_period": True},
        "effort": "3 months",
        "monitoring": [
            "Vault transit key operation latency (ms) with ML-KEM",
            "CI artifact signature verification pass rate",
            "Secret rotation job success rate",
        ],
        "interview": [
            "DevSecOps PQC migration unblocks all downstream deployments—pipelines must sign PQC artifacts before any PQC service can ship",
            "Vault transit ML-KEM is the secret zero for CI secrets; migrate it first before touching individual service secret stores",
        ],
    },
    "L24": {
        "name": "SIEM / Log Security",
        "category": "Security Monitoring",
        "phase": "P2",
        "old": {"protocol": "TLS-log/RSA+ECDSA", "algorithm": "TLS1.2 ECDSA log shipping", "standard": "RFC5424"},
        "issues": [
            "ECDSA TLS agent certificates for log shipping vulnerable to Shor's",
            "Syslog integrity signatures (if any) use ECDSA—log tamper detection broken post-CRQC",
            "SIEM data classified as lower priority but contains forensic evidence of future HNDL attacks",
        ],
        "quantum_threat": {"severity": "MEDIUM", "algorithm": "Grover's", "year": 2035},
        "steps": [
            "Upgrade log shipper TLS to hybrid PQC (same TLS migration as L04)",
            "Issue ML-DSA-65 agent certs for Filebeat/Fluentd/Vector log shippers",
            "Enable log integrity signing with ML-DSA-65 at shipper level",
            "Validate SIEM ingestion pipeline compatibility with larger PQC log headers",
            "Archive historical logs with PQC-encrypted long-term storage",
        ],
        "new": {"algorithm": "Hybrid TLS + ML-DSA-65 agent certs", "standard": "RFC5424+IETF-TLS-hybrid", "hybrid_period": True},
        "effort": "2 months",
        "monitoring": [
            "Log shipper TLS handshake success rate",
            "Log integrity verification failure count",
            "SIEM ingestion lag with larger PQC-signed log headers (ms)",
        ],
        "interview": [
            "SIEM PQC is P2 because Grover's only halves symmetric key strength—AES-256 log encryption stays safe with current key sizes",
            "Log integrity signing with ML-DSA provides tamper-evident audit trails; critical for post-quantum forensics of HNDL incidents",
        ],
    },
    "L25": {
        "name": "Zero Trust Network Access",
        "category": "Zero Trust Architecture",
        "phase": "P1",
        "old": {"protocol": "SPIFFE+OIDC/ECDSA", "algorithm": "ECDSA SVID+OIDC id_token", "standard": "RFC8705"},
        "issues": [
            "ECDSA SPIFFE SVIDs broken by Shor's—zero trust identity forgeable post-CRQC",
            "OIDC continuous authentication tokens use RS256/ECDSA—broken by Shor's",
            "Policy enforcement depends on identity integrity; quantum-broken identity = zero trust collapse",
        ],
        "quantum_threat": {"severity": "HIGH", "algorithm": "Shor's", "year": 2030},
        "steps": [
            "Migrate SPIRE SVID issuance to ML-DSA-65 (see also L19 for container mesh)",
            "Update ZTNA policy engine to validate ML-DSA-65 identity assertions",
            "Switch OIDC continuous auth tokens to ML-DSA-65 JOSE signing",
            "Update device trust attestation certificates to ML-DSA-65 from PQC CA",
            "Enforce PQC-only SVID acceptance in all ZT policy evaluation points",
        ],
        "new": {"algorithm": "ML-DSA-65 SVIDs+PQC-OIDC", "standard": "SPIFFE-PQC+JOSE-PQC-draft", "hybrid_period": True},
        "effort": "4 months",
        "monitoring": [
            "ZTNA policy evaluation latency with ML-DSA identity verification (ms)",
            "SVID validation failure rate per workload class",
            "OIDC token reissuance rate during hybrid period",
        ],
        "interview": [
            "Zero Trust's 'never trust, always verify' collapses if the verification mechanism (ECDSA) is quantum-broken—PQC is ZT's existential requirement",
            "SPIFFE+SPIRE pluggable CA means ML-DSA-65 SVID migration doesn't require replacing the entire ZT control plane",
        ],
    },
    "L26": {
        "name": "Key Management Service (KMS)",
        "category": "Key Management",
        "phase": "P0",
        "old": {"protocol": "Vault+SOPS/RSA-OAEP", "algorithm": "RSA-OAEP-2048 key wrap", "standard": "RFC8017"},
        "issues": [
            "RSA-OAEP key wrapping in Vault broken by Shor's—all wrapped keys compromised post-CRQC",
            "SOPS file encryption uses RSA/ECDSA master keys—infrastructure-as-code secrets exposed",
            "KMS is the root of trust for all other layer key material—highest blast radius if compromised",
        ],
        "quantum_threat": {"severity": "CRITICAL", "algorithm": "Shor's", "year": 2029},
        "steps": [
            "Enable ML-KEM-768 key wrapping in Vault transit engine (Vault 1.16+ PQC plugin)",
            "Migrate SOPS master key to age-x25519+ML-KEM-768 hybrid recipient",
            "Re-wrap all Vault-stored key material with ML-KEM-768",
            "Update KMS API clients to request ML-KEM-768 wrapped data keys",
            "Revoke RSA-OAEP master keys in KMS after all consumers migrated",
        ],
        "new": {"algorithm": "ML-KEM-768 wrap+SOPS-age", "standard": "RFC9180+Vault-PQC-transit", "hybrid_period": False},
        "effort": "4 months",
        "monitoring": [
            "KMS key wrap/unwrap latency (ms) with ML-KEM vs RSA baseline",
            "Data key generation throughput (keys/sec)",
            "RSA-OAEP wrap request count (should be zero after migration)",
        ],
        "interview": [
            "KMS is the crown jewel—ML-KEM-768 wrap migration here transitively protects every key derived from KMS master keys",
            "SOPS age backend supports hybrid recipients (x25519+ML-KEM); SOPS migration is infrastructure-as-code secret rotation at scale",
        ],
    },
    "L27": {
        "name": "Compliance & Policy Framework",
        "category": "Governance & Compliance",
        "phase": "P1",
        "old": {"protocol": "FIPS140-2", "algorithm": "CNSA-1.0 algorithm suite", "standard": "CNSA-1.0"},
        "issues": [
            "FIPS140-2 does not validate ML-KEM/ML-DSA/Falcon—compliance gap for PQC deployments",
            "CNSA 1.0 sunset by NSA: RSA-3072+, ECDH P-384, AES-256—must migrate to CNSA 2.0",
            "Existing compliance controls (SOC2/PCI-DSS) reference classical algo requirements; need PQC addenda",
        ],
        "quantum_threat": {"severity": "HIGH", "algorithm": "Shor's", "year": 2030},
        "steps": [
            "Map current crypto inventory to CNSA 2.0 requirements (NSA CNSA 2.0 advisory)",
            "Identify FIPS140-3 validated modules for each PQC algorithm needed",
            "Update security policies to reference FIPS140-3 and CNSA 2.0 as mandatory standards",
            "Engage PCI-DSS/SOC2 auditors to establish PQC readiness as audit criterion",
            "Publish internal PQC migration roadmap as compliance evidence artifact",
        ],
        "new": {"algorithm": "FIPS140-3+CNSA-2.0 suite", "standard": "FIPS140-3+CNSA-2.0", "hybrid_period": False},
        "effort": "3 months",
        "monitoring": [
            "Percentage of crypto inventory mapped to CNSA 2.0",
            "FIPS140-3 validated module coverage for deployed algorithms",
            "Open compliance exceptions count related to classical crypto",
        ],
        "interview": [
            "CNSA 2.0 is NSA's mandatory PQC migration directive for national security systems—private sector should treat it as the gold standard roadmap",
            "Compliance framework updates are a P1 enabler: without updated policies, PQC deployments create audit findings rather than resolve them",
        ],
    },
    "L28": {
        "name": "Audit Logging & Timestamps",
        "category": "Audit & Non-repudiation",
        "phase": "P1",
        "old": {"protocol": "RFC3161/RSA-2048", "algorithm": "RSA-2048 trusted timestamp", "standard": "RFC3161"},
        "issues": [
            "RFC3161 TSA RSA-2048 signatures broken by Shor's—timestamped audit evidence forged post-CRQC",
            "Long-term non-repudiation of audit logs requires signature longevity beyond CRQC arrival",
            "Legal and regulatory admissibility of audit evidence depends on unforgeable timestamps",
        ],
        "quantum_threat": {"severity": "CRITICAL", "algorithm": "Shor's", "year": 2030},
        "steps": [
            "Deploy SLH-DSA (SPHINCS+) based Timestamp Authority for long-term hash-based signature security",
            "Integrate PQC TSA with audit log pipeline (Elasticsearch/Splunk log commit intervals)",
            "Re-timestamp critical historical audit logs with SLH-DSA counter-signatures",
            "Align with ETSI EN 319 102-1 for PQC-based long-term validation (LTV)",
            "Update document signing workflows to use PQC timestamps for EIDAS/eSign compliance",
        ],
        "new": {"algorithm": "SLH-DSA timestamps", "standard": "ETSI-EN-319+RFC3161-PQC", "hybrid_period": False},
        "effort": "3 months",
        "monitoring": [
            "TSA timestamp issuance latency (SLH-DSA vs RSA ms)",
            "Audit log timestamp validation failure rate",
            "SLH-DSA key hash tree remaining capacity (% exhausted)",
        ],
        "interview": [
            "SLH-DSA (SPHINCS+) is preferred for timestamping: hash-based signature security is not dependent on any algebraic hardness assumption",
            "ETSI EN 319 102-1 LTV framework enables audit evidence to remain legally valid beyond the lifetime of any underlying algorithm",
        ],
    },
    "L29": {
        "name": "AI/ML Model Security",
        "category": "AI/ML Pipeline Security",
        "phase": "P1",
        "old": {"protocol": "cosign+MLflow/ECDSA+RS256", "algorithm": "ECDSA-P256 cosign + RS256 model registry JWT", "standard": "none"},
        "issues": [
            "ECDSA cosign model signatures broken by Shor's—poisoned models injectable without detection",
            "MLflow RS256 JWT authentication for model registry access vulnerable to quantum factoring",
            "AI model supply chain has no established PQC signing standard yet",
        ],
        "quantum_threat": {"severity": "HIGH", "algorithm": "Shor's", "year": 2030},
        "steps": [
            "Integrate ML-DSA-65 into cosign signing workflow for model artifacts",
            "Update MLflow model registry auth to use ML-DSA-65 JWT (JOSE-PQC draft)",
            "Establish model provenance policy: every registered model must have ML-DSA-65 signature",
            "Implement model SBOM with PQC-signed attestation in CI/CD pipeline",
            "Validate model integrity at inference load time against ML-DSA-65 signatures",
        ],
        "new": {"algorithm": "ML-DSA-65 model signing", "standard": "NIST-FIPS-204+sigstore-pqc", "hybrid_period": True},
        "effort": "3 months",
        "monitoring": [
            "Model signature verification pass rate at deployment",
            "ML-DSA signing latency per model artifact (ms)",
            "Unsigned model deployment attempt count (should be zero)",
        ],
        "interview": [
            "AI model signing is an emerging supply-chain requirement—quantum-forged model signatures enable silent model substitution at inference",
            "ML-DSA-65 via cosign+sigstore integrates into existing GitOps pipelines; adoption path mirrors container image signing migration",
        ],
    },
}


class LayerMigrationPlan:
    def get_layer(self, layer_id):
        return LAYER_PLANS[layer_id]

    def get_all(self):
        return list(LAYER_PLANS.values())

    def get_critical(self):
        return [p for p in LAYER_PLANS.values() if p["quantum_threat"]["severity"] == "CRITICAL"]

    def by_phase(self):
        result = {}
        for lid, plan in LAYER_PLANS.items():
            ph = plan["phase"]
            result.setdefault(ph, {})[lid] = plan
        return result

    def summary_table(self):
        hdr = f"{'ID':<5} {'Phase':<6} {'Old Algo':<28} {'Threat':<10} {'New Algo':<35} {'Effort'}"
        print(hdr)
        print("-" * len(hdr))
        for lid, p in LAYER_PLANS.items():
            print(
                f"{lid:<5} {p['phase']:<6} {p['old']['algorithm'][:27]:<28} "
                f"{p['quantum_threat']['severity']:<10} {p['new']['algorithm'][:34]:<35} {p['effort']}"
            )

    def layer_report(self, layer_id):
        p = LAYER_PLANS[layer_id]
        qt = p["quantum_threat"]
        print(f"\n{'='*60}")
        print(f"Layer: {layer_id} — {p['name']}")
        print(f"Category : {p['category']}")
        print(f"Phase    : {p['phase']}  |  Effort: {p['effort']}")
        print(f"Old      : {p['old']['protocol']} / {p['old']['algorithm']} ({p['old']['standard']})")
        print(f"New      : {p['new']['algorithm']} ({p['new']['standard']})")
        print(f"Hybrid   : {p['new']['hybrid_period']}")
        print(f"Threat   : {qt['severity']} via {qt['algorithm']} ~{qt['year']}")
        print(f"\nIssues:")
        for i, iss in enumerate(p["issues"], 1):
            print(f"  {i}. {iss}")
        print(f"\nMigration Steps:")
        for i, s in enumerate(p["steps"], 1):
            print(f"  {i}. {s}")
        print(f"\nMonitoring:")
        for m in p["monitoring"]:
            print(f"  - {m}")
        print(f"\nInterview Talking Points:")
        for tp in p["interview"]:
            print(f"  * {tp}")
        print("=" * 60)

    def interview_guide(self):
        print(f"\n{'='*70}")
        print("INTERVIEW GUIDE — PQC Migration Talking Points by Layer")
        print("=" * 70)
        for lid, p in LAYER_PLANS.items():
            print(f"\n[{lid}] {p['name']} (Phase {p['phase']}, {p['quantum_threat']['severity']})")
            for tp in p["interview"]:
                print(f"  • {tp}")


def main():
    lmp = LayerMigrationPlan()
    print("\n=== PQC LAYER MIGRATION SUMMARY TABLE ===\n")
    lmp.summary_table()
    p0 = lmp.by_phase().get("P0", {})
    print(f"\nP0 (Critical/Immediate) layers: {len(p0)} — {', '.join(p0.keys())}")
    lmp.layer_report("L04")
    lmp.interview_guide()


if __name__ == "__main__":
    main()
