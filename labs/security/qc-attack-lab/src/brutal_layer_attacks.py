"""
brutal_layer_attacks.py
=======================
Comprehensive Brutal Attack Simulation Module — All 29 Security Layers

Maps every security layer to real CVEs, real offensive tools, and MITRE ATT&CK
techniques. Every attack includes classical vs PQC outcome comparison.

PURPOSE: Educational and defensive security only. Understanding offensive
techniques is required for building robust quantum-safe defenses.

Author: Quantum Security Lab
Layer Coverage: L01–L29 (all 29 layers)
"""

from __future__ import annotations

import datetime
import textwrap
from typing import Any

# ---------------------------------------------------------------------------
# Attack data — keyed by layer_id
# ---------------------------------------------------------------------------

LAYER_ATTACKS: dict[str, dict[str, Any]] = {

    # -----------------------------------------------------------------------
    # L01 — Physical / Hardware
    # -----------------------------------------------------------------------
    "L01": {
        "layer_id": "L01",
        "layer_name": "Physical / Hardware",
        "attacks": [
            {
                "name": "Cold Boot Attack",
                "cve": "N/A",
                "tool": "msramdump",
                "technique": "T1005",
                "description": (
                    "RAM chips retain data for seconds to minutes after power loss when "
                    "cooled with compressed air or liquid nitrogen. The attacker physically "
                    "removes DIMMs, transplants them into a read device, and dumps full "
                    "memory contents. Crypto keys resident in RAM (RSA private key, AES "
                    "session keys) are extracted with automated key-finder tools."
                ),
                "impact": "RSA private key extracted from RAM; all encrypted data and sessions compromised.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "HIGH — ML-DSA/ML-KEM keys still reside in RAM during operation; "
                    "cold boot risk identical at hardware level until RAM encryption is deployed."
                ),
                "detection": "Physical access logs, tamper-evident chassis seals, RAM encryption status monitoring.",
                "defense": (
                    "Deploy RAM encryption (AMD SME/SEV or Intel TME), enable power-off-on-tamper "
                    "chassis policy, use memory-safe key zeroisation on process exit."
                ),
            },
            {
                "name": "TPM Key Extraction",
                "cve": "CVE-2023-1017 / CVE-2023-1018",
                "tool": "TPMGenie",
                "technique": "T1553.006",
                "description": (
                    "CVE-2023-1017/1018 are heap buffer overflows in the TPM2 reference "
                    "implementation triggered by oversized TPM2_PCR_Extend and similar "
                    "commands. An attacker with local or bus-level access sends malformed "
                    "TPM2 commands, achieves arbitrary code execution inside the TPM "
                    "firmware, and exports the RSA Endorsement Key (EK). TPMGenie intercepts "
                    "the TPM SPI bus to replay and forge TPM commands."
                ),
                "impact": "Device identity permanently compromised; all TPM-sealed secrets retrievable.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "CRITICAL until TPM 3.0 with ML-KEM/ML-DSA is deployed; "
                    "CVE exists in TPM firmware, not in algorithm choice."
                ),
                "detection": "TPM audit log anomalies, PCR measurement deviations, TPM bus traffic monitoring.",
                "defense": (
                    "Upgrade to FIPS 140-3 TPM 3.0 firmware, restrict TPM SPI bus physical access, "
                    "apply vendor firmware patches immediately."
                ),
            },
            {
                "name": "PRNG Seed Prediction",
                "cve": "CVE-2008-0166",
                "tool": "custom exploit (Debian OpenSSL key predictor)",
                "technique": "T1600",
                "description": (
                    "CVE-2008-0166: Debian's OpenSSL patch accidentally removed PRNG seeding "
                    "from all sources except the process PID (32-bit range). An attacker "
                    "pre-generates all ~65,536 possible RSA keys for each affected PID, "
                    "producing a lookup table. Any RSA key generated on a Debian/Ubuntu system "
                    "during the vulnerable window can be recovered instantly."
                ),
                "impact": "All RSA/DSA keys generated on affected systems guessable; SSH host keys, TLS certs all compromised.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "RESOLVED by QRNG — quantum random number generators provide true entropy "
                    "immune to seed prediction; PQC algorithms also require proper entropy."
                ),
                "detection": "Entropy pool monitoring (/proc/sys/kernel/random/entropy_avail), key generation rate anomalies.",
                "defense": (
                    "Use QRNG or hardware RNG (RDRAND + /dev/random hybrid), monitor entropy levels, "
                    "audit key generation code for PRNG seeding."
                ),
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L02 — Data Link / MACsec
    # -----------------------------------------------------------------------
    "L02": {
        "layer_id": "L02",
        "layer_name": "Data Link / MACsec",
        "attacks": [
            {
                "name": "ARP Spoofing",
                "cve": "N/A",
                "tool": "arpspoof / ettercap",
                "technique": "T1557.002",
                "description": (
                    "ARP has no authentication; any host can broadcast an ARP reply claiming "
                    "any IP-to-MAC mapping. The attacker sends gratuitous ARP replies poisoning "
                    "the cache of all hosts on the subnet, redirecting traffic through the "
                    "attacker's machine. Ettercap automates MITM, ARP cache poisoning, and "
                    "selective payload modification."
                ),
                "impact": "Full MITM on entire subnet; all unencrypted traffic readable and modifiable.",
                "classical_result": "HIGH",
                "pqc_result": (
                    "HIGH — L2 attack is crypto-agnostic; PQC does not address ARP; "
                    "Dynamic ARP Inspection (DAI) is the control."
                ),
                "detection": "ARP anomaly detection (arpwatch), VLAN isolation, duplicate MAC/IP alerts.",
                "defense": "Enable Dynamic ARP Inspection on managed switches, use 802.1X port authentication, VLAN micro-segmentation.",
            },
            {
                "name": "EAP-TLS RSA Downgrade",
                "cve": "N/A",
                "tool": "hostapd-wpe",
                "technique": "T1557",
                "description": (
                    "hostapd-wpe is a rogue access point tool that accepts any EAP method "
                    "the client offers. By presenting only EAP-MD5 or EAP-TTLS/PAP options, "
                    "the attacker downgrades from EAP-TLS, capturing credential hashes or "
                    "RSA handshake material. Offline dictionary attack or RSA premaster "
                    "secret recovery follows."
                ),
                "impact": "Network access bypass; credential hash captured for offline cracking.",
                "classical_result": "HIGH",
                "pqc_result": (
                    "MITIGATED — ML-KEM EAP-TLS profile (RFC draft) eliminates RSA "
                    "downgrade path; attacker must still handle lattice key exchange."
                ),
                "detection": "EAP method negotiation monitoring, rogue AP detection via WIDS.",
                "defense": "Force EAP-TLS only in RADIUS policy, deploy WIDS, strict certificate validation.",
            },
            {
                "name": "MACsec SAK Key Recovery",
                "cve": "N/A",
                "tool": "custom (Shor's algorithm on CRQC)",
                "technique": "T1040",
                "description": (
                    "MACsec Session Authentication Key (SAK) distribution uses RSA-based "
                    "key agreement in MKA (MACsec Key Agreement protocol). A cryptographically "
                    "relevant quantum computer runs Shor's algorithm on the RSA public key "
                    "used during SAK exchange, recovering the RSA private key and deriving "
                    "the SAK. All MACsec-protected frames on the segment are decrypted."
                ),
                "impact": "All MACsec-encrypted L2 traffic decrypted retroactively and in real time.",
                "classical_result": "CRITICAL (quantum-era)",
                "pqc_result": (
                    "SAFE — ML-KEM SAK distribution replaces RSA; Shor's algorithm "
                    "cannot solve Module-LWE in polynomial time."
                ),
                "detection": "Quantum capability threat intelligence monitoring, unusual traffic volume on MACsec segments.",
                "defense": "Deploy ML-KEM-based MKA SAK distribution, use quantum-safe IKEv2 for rekeying.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L03 — Network / IPsec
    # -----------------------------------------------------------------------
    "L03": {
        "layer_id": "L03",
        "layer_name": "Network / IPsec",
        "attacks": [
            {
                "name": "IKEv2 Aggressive Mode PSK Crack",
                "cve": "CVE-2015-7183",
                "tool": "ike-scan + psk-crack",
                "technique": "T1040",
                "description": (
                    "IKEv2 aggressive mode sends the preshared key (PSK) hash in the clear "
                    "as part of the IKE_AUTH exchange. CVE-2015-7183 affects NSS-based "
                    "implementations. ike-scan captures the challenge-response hash; "
                    "psk-crack runs offline dictionary or brute-force against it, "
                    "recovering the PSK without any active attack on the VPN gateway."
                ),
                "impact": "VPN authentication bypass; attacker establishes legitimate IPsec tunnel.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — PSK is crypto-agnostic; Shor's does not help crack "
                    "a random 256-bit PSK; operational security failure, not algorithm failure."
                ),
                "detection": "IKEv2 mode negotiation monitoring, alert on aggressive mode usage.",
                "defense": "Force IKEv2 main mode only, use certificate-based auth instead of PSK, enforce minimum PSK entropy.",
            },
            {
                "name": "DH-2048 Quantum Break (Shor)",
                "cve": "N/A",
                "tool": "Shor's algorithm on CRQC",
                "technique": "T1600",
                "description": (
                    "IPsec IKEv2 Diffie-Hellman group 14 (DH-2048) is the most common "
                    "deployment. A CRQC runs Shor's algorithm factoring the DH modulus, "
                    "recovering the shared secret from passively captured IKE_SA_INIT "
                    "messages. No active attack on the endpoint is needed; archived "
                    "captures are retroactively decrypted."
                ),
                "impact": "All IPsec sessions using DH-2048 decrypted; VPN confidentiality eliminated.",
                "classical_result": "CRITICAL (quantum-era)",
                "pqc_result": (
                    "SAFE — RFC 9242 ML-KEM-1024 replaces DH in IKEv2; "
                    "lattice problem not solvable by Shor's."
                ),
                "detection": "Monitor for unusual IKEv2 SA negotiation patterns; deploy quantum threat intelligence.",
                "defense": "Implement RFC 9242 Post-Quantum IKEv2 with ML-KEM-1024 hybrid; renegotiate all long-lived SAs.",
            },
            {
                "name": "Logjam DH-512/768 Downgrade",
                "cve": "CVE-2015-4000",
                "tool": "custom GNFS factoring",
                "technique": "T1040",
                "description": (
                    "CVE-2015-4000 (Logjam): TLS/IPsec implementations accepting export-grade "
                    "DH (512-bit) or DHE_EXPORT can be downgraded by an active MITM. "
                    "Number Field Sieve (GNFS) factors a 512-bit DH modulus in hours on "
                    "commodity hardware, recovering the session key. 768-bit groups were "
                    "factored in academic settings; 1024-bit is feasible for nation-states."
                ),
                "impact": "IPsec session key recovered; all encrypted traffic decryptable in near real time.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "ELIMINATED — DH removed entirely in PQ IKEv2 (RFC 9242); "
                    "ML-KEM replaces DH, no weak groups possible."
                ),
                "detection": "Monitor DH group negotiation in IKEv2; alert on groups < 2048-bit.",
                "defense": "Disable all DH groups < 3072-bit, disable export cipher suites, enforce ML-KEM.",
            },
            {
                "name": "strongSwan RCE (CVE-2023-41913)",
                "cve": "CVE-2023-41913",
                "tool": "custom PoC exploit",
                "technique": "T1190",
                "description": (
                    "CVE-2023-41913: Heap buffer overflow in strongSwan's charon VPN daemon "
                    "in the handling of certificate-in-psk payloads. A remote unauthenticated "
                    "attacker sends a crafted IKEv2 packet triggering the overflow, achieving "
                    "remote code execution as the charon process user (typically root or "
                    "a privileged daemon account)."
                ),
                "impact": "Full VPN gateway compromise; attacker controls all IPsec policy and routing.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "CRITICAL — CVE is unrelated to cryptographic algorithm; "
                    "PQC migration does not patch this; apply vendor patch immediately."
                ),
                "detection": "IDS signatures for CVE-2023-41913, crash monitoring for charon daemon.",
                "defense": "Patch strongSwan immediately to 5.9.13+; run charon in restrictive seccomp/AppArmor profile.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L04 — TLS Transport
    # -----------------------------------------------------------------------
    "L04": {
        "layer_id": "L04",
        "layer_name": "TLS Transport",
        "attacks": [
            {
                "name": "Heartbleed",
                "cve": "CVE-2014-0160",
                "tool": "heartbleed-poc",
                "technique": "T1040",
                "description": (
                    "CVE-2014-0160: OpenSSL's TLS heartbeat extension fails to validate the "
                    "heartbeat payload length field, allowing an attacker to read up to 64 KB "
                    "of server heap memory per request without authentication. Repeated "
                    "requests eventually expose the RSA private key, session tokens, passwords, "
                    "and any secret resident in the OpenSSL process heap."
                ),
                "impact": "CRITICAL — RSA private key exposed; all past and future TLS sessions decryptable; session tokens allow account hijacking.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "CRITICAL until patched — Heartbleed is an implementation bug in OpenSSL, "
                    "not a cryptographic weakness; ML-KEM keys in a vulnerable OpenSSL build "
                    "are equally exposed. Patch first, then migrate algorithms."
                ),
                "detection": "IDS signatures for anomalous heartbeat requests, memory monitoring, OpenSSL version auditing.",
                "defense": "Patch OpenSSL to 1.0.1g+; revoke and reissue all certificates; rotate all session secrets.",
            },
            {
                "name": "BEAST Attack",
                "cve": "CVE-2011-3389",
                "tool": "BEAST.py",
                "technique": "T1040",
                "description": (
                    "CVE-2011-3389 (BEAST — Browser Exploit Against SSL/TLS): TLS 1.0 and SSL 3.0 "
                    "use CBC mode with a predictable IV (previous ciphertext block). A chosen-plaintext "
                    "attack allows a MITM to inject chosen blocks into an existing TLS session, "
                    "iteratively decrypting the session cookie one byte at a time."
                ),
                "impact": "Session cookie theft; full authenticated session hijacking.",
                "classical_result": "HIGH",
                "pqc_result": (
                    "MITIGATED — TLS 1.3 (mandatory in PQC migration) removes CBC mode "
                    "entirely, using only AEAD ciphers; BEAST is structurally impossible in TLS 1.3."
                ),
                "detection": "TLS version monitoring; alert on TLS 1.0/SSL 3.0 negotiation.",
                "defense": "Enforce TLS 1.3 only; disable TLS 1.0, TLS 1.1, SSL 3.0 at load balancer and application.",
            },
            {
                "name": "POODLE",
                "cve": "CVE-2014-3566",
                "tool": "poodle-poc",
                "technique": "T1040",
                "description": (
                    "CVE-2014-3566 (POODLE — Padding Oracle On Downgraded Legacy Encryption): "
                    "SSL 3.0 CBC uses undefined padding; a MITM forces a TLS downgrade by "
                    "injecting TCP RST packets until the client falls back to SSL 3.0. "
                    "The CBC padding oracle allows block-by-block decryption of the session "
                    "cookie, requiring ~256 requests per byte."
                ),
                "impact": "Session cookie theft; authenticated session hijacking for any SSLv3-fallback capable server.",
                "classical_result": "HIGH",
                "pqc_result": (
                    "ELIMINATED — TLS 1.3 is mandatory in PQC deployments; "
                    "no downgrade fallback to SSL 3.0 is possible."
                ),
                "detection": "SSL version monitoring; alert on SSL 3.0 negotiation attempts.",
                "defense": "Disable SSL 3.0 and TLS 1.2 with CBC cipher suites; enforce TLS 1.3 + AEAD.",
            },
            {
                "name": "ROBOT Attack",
                "cve": "CVE-2017-13099",
                "tool": "robot-detect",
                "technique": "T1040",
                "description": (
                    "ROBOT (Return Of Bleichenbacher's Oracle Threat): CVE-2017-13099 revives the "
                    "1998 Bleichenbacher RSA PKCS#1 v1.5 padding oracle. Sending ~1,000,000 "
                    "crafted RSA ciphertext queries to a vulnerable TLS server leaks whether "
                    "padding is valid, allowing recovery of the RSA-encrypted premaster secret "
                    "and thus decryption of the session."
                ),
                "impact": "TLS session key recovered; all intercepted sessions decryptable in minutes to hours.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "ELIMINATED — ML-KEM replaces RSA key exchange entirely; "
                    "there is no RSA ciphertext to query a padding oracle against."
                ),
                "detection": "Monitor for high-volume RSA decrypt requests to the same origin; TLS handshake anomaly detection.",
                "defense": "Disable RSA key exchange (RSA_WITH_* cipher suites); enforce ECDHE or ML-KEM only.",
            },
            {
                "name": "DROWN",
                "cve": "CVE-2016-0800",
                "tool": "drown-attack",
                "technique": "T1040",
                "description": (
                    "CVE-2016-0800 (DROWN — Decrypting RSA with Obsolete and Weakened eNcryption): "
                    "If any server shares an RSA private key with an SSLv2-enabled server, "
                    "the SSLv2 export-grade RSA oracle can be exploited to recover the "
                    "RSA private key used in modern TLS connections. A server with SSLv2 "
                    "disabled is still vulnerable if a different server uses the same key."
                ),
                "impact": "RSA private key exposed across all servers sharing it; all TLS sessions retroactively decryptable.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "ELIMINATED — RSA key exchange removed from TLS; ML-KEM has no SSLv2 legacy "
                    "compatibility surface; no shared-key cross-protocol oracle possible."
                ),
                "detection": "SSLv2 monitoring on all servers; certificate key reuse auditing.",
                "defense": "Disable SSLv2 on ALL servers sharing RSA private keys; use unique keys per server; migrate to ML-KEM.",
            },
            {
                "name": "HNDL Harvest-Now-Decrypt-Later (Quantum)",
                "cve": "N/A",
                "tool": "passive capture + future Shor's algorithm",
                "technique": "T1040",
                "description": (
                    "Nation-state adversaries passively record all ECDHE TLS traffic today "
                    "(2024–2026). When a cryptographically relevant quantum computer (CRQC) "
                    "becomes available (~2030–2033), Shor's algorithm recovers ECDHE private "
                    "keys from public key material in the archived handshakes, decrypting "
                    "all retroactively captured sessions."
                ),
                "impact": "All ECDHE TLS sessions captured today become retroactively decryptable; long-lived sensitive data fully exposed.",
                "classical_result": "CRITICAL (quantum-era)",
                "pqc_result": (
                    "SAFE — ML-KEM hybrid TLS (NIST SP 800-227) provides IND-CCA2 security; "
                    "even if ECDHE is broken by Shor's, ML-KEM component remains quantum-safe."
                ),
                "detection": "Unusual large-scale encrypted traffic exfiltration to foreign infrastructure; bulk TLS session archiving.",
                "defense": "Deploy hybrid TLS 1.3 with X25519+ML-KEM-768 NOW; do not wait for CRQC — HNDL attacks accumulate.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L05 — Session Layer
    # -----------------------------------------------------------------------
    "L05": {
        "layer_id": "L05",
        "layer_name": "Session Layer",
        "attacks": [
            {
                "name": "Session Fixation",
                "cve": "CVE-2011-2940",
                "tool": "Burp Suite",
                "technique": "T1550.004",
                "description": (
                    "The attacker obtains a valid pre-authentication session ID (e.g. from "
                    "a cookie-based application that issues session IDs before login). "
                    "The victim is tricked into using that ID; after the victim authenticates, "
                    "the session is now authenticated and the attacker—who knows the ID—"
                    "has full access without credentials."
                ),
                "impact": "Account takeover without needing the victim's password.",
                "classical_result": "HIGH",
                "pqc_result": (
                    "UNCHANGED — session fixation is an application session management bug, "
                    "not a cryptographic weakness; PQC migration does not address it."
                ),
                "detection": "Monitor for session IDs that survive authentication without regeneration.",
                "defense": "Regenerate session ID on every authentication event; enforce SameSite=Strict cookies.",
            },
            {
                "name": "Session Ticket Key Theft (Quantum)",
                "cve": "N/A",
                "tool": "custom + Shor's algorithm on CRQC",
                "technique": "T1552",
                "description": (
                    "TLS session tickets are encrypted with a server-side session ticket key "
                    "derived from or protected by an RSA-2048 key. A CRQC running Shor's "
                    "algorithm recovers the RSA private key from the public key, decrypts the "
                    "session ticket key, and decrypts all resumed TLS sessions. Bulk session "
                    "ticket collection via passive capture yields a mass decryption archive."
                ),
                "impact": "All TLS session resumptions compromised; session secrets, auth tokens, and user data exposed.",
                "classical_result": "CRITICAL (quantum-era)",
                "pqc_result": (
                    "SAFE — ML-KEM-768 session ticket encryption; frequent rotation policy "
                    "(every 6 hours) limits retroactive exposure window."
                ),
                "detection": "Monitor for bulk session ticket requests, anomalous TLS resumption rates.",
                "defense": "Rotate session ticket keys every 6 hours; migrate ticket key protection to ML-KEM; disable session tickets in high-sensitivity contexts.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L06 — X.509 PKI
    # -----------------------------------------------------------------------
    "L06": {
        "layer_id": "L06",
        "layer_name": "X.509 PKI",
        "attacks": [
            {
                "name": "CA Private Key Compromise (DigiNotar-style)",
                "cve": "CVE-2011-3026",
                "tool": "mimikatz (key extraction from CA server memory)",
                "technique": "T1553.004",
                "description": (
                    "The 2011 DigiNotar breach: attackers compromised the CA server OS, "
                    "used mimikatz to extract the RSA-4096 CA private key from memory or "
                    "disk storage. With the CA private key, they issued fraudulent certificates "
                    "for *.google.com and other major domains. The attack went undetected "
                    "for months, enabling MITM on targeted populations."
                ),
                "impact": "Full PKI trust broken; MITM on any HTTPS domain whose CA chain includes the compromised CA.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "CRITICAL until HSM-protected — ML-DSA CA key improves algorithm security "
                    "but CA server compromise still allows key export unless an HSM is used."
                ),
                "detection": "Certificate Transparency (CT) log monitoring; alert on unexpected certificate issuance.",
                "defense": "Air-gapped offline root CA; HSM for all CA private keys (FIPS 140-3 Level 3+); CT log enforcement.",
            },
            {
                "name": "Quantum CA Attack (Shor on RSA-4096)",
                "cve": "N/A",
                "tool": "Shor's algorithm on CRQC",
                "technique": "T1553.004",
                "description": (
                    "A CRQC runs Shor's algorithm on the RSA-4096 root CA public key "
                    "embedded in every browser and OS trust store. Recovery of the private "
                    "key allows forging certificates for any domain. Because root CA keys "
                    "have 20-year lifetimes, HNDL-captured CT log data provides the public "
                    "key without needing to compromise any CA server."
                ),
                "impact": "All TLS trust globally broken; retroactive forgery of any certificate; complete internet MITM.",
                "classical_result": "CRITICAL (quantum-era)",
                "pqc_result": (
                    "SAFE — ML-DSA-87 root CA creates quantum-safe trust anchor; "
                    "RSA-4096 public key is no longer present in the certificate chain."
                ),
                "detection": "CT log anomalies, certificate transparency monitoring.",
                "defense": "Migrate root and intermediate CAs to ML-DSA-87 NOW; include ML-DSA in all issued certificates.",
            },
            {
                "name": "Certificate Spoofing via MD5 Collision",
                "cve": "CVE-2008-0166",
                "tool": "hashclash",
                "technique": "T1553.004",
                "description": (
                    "MD5 is collision-vulnerable; in 2008 researchers used a cluster of "
                    "200 PlayStations to generate a rogue CA certificate sharing the same "
                    "MD5 hash as a legitimately signed certificate. The CA's signature "
                    "covers the MD5 hash, which is shared by both the legitimate and rogue "
                    "certificates, making the rogue one appear validly signed."
                ),
                "impact": "HTTPS MITM for any domain; browser shows valid padlock for attacker-controlled certificate.",
                "classical_result": "HIGH",
                "pqc_result": (
                    "ELIMINATED — SHA-256 and SHA-3 (used in ML-DSA) have no known "
                    "collision attacks; MD5 is forbidden in FIPS 140-3 and modern CAs."
                ),
                "detection": "Certificate algorithm monitoring; alert on MD5 signatures in any cert.",
                "defense": "Never issue certificates with MD5; enforce SHA-256/SHA-384 minimum at CA policy level.",
            },
            {
                "name": "OCSP Stapling Bypass",
                "cve": "CVE-2016-7056",
                "tool": "custom",
                "technique": "T1553",
                "description": (
                    "CVE-2016-7056: When OCSP stapling is not mandatory, a server presenting "
                    "a revoked certificate simply omits the OCSP staple. Clients that do "
                    "not enforce OCSP-Must-Staple accept the certificate as valid. An "
                    "attacker who has obtained a revoked certificate continues to use it "
                    "indefinitely for impersonation."
                ),
                "impact": "Revoked certificates accepted as valid; impersonation of legitimate servers after key compromise.",
                "classical_result": "HIGH",
                "pqc_result": (
                    "UNCHANGED — OCSP stapling bypass is a PKI revocation infrastructure issue; "
                    "PQC algorithm migration does not affect revocation checking."
                ),
                "detection": "OCSP response presence monitoring; alert on missing staples for Must-Staple certificates.",
                "defense": "Enforce OCSP-Must-Staple extension in all issued certificates; deploy CRLite or OCSP fetch fallback.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L07 — HTTPS / Application
    # -----------------------------------------------------------------------
    "L07": {
        "layer_id": "L07",
        "layer_name": "HTTPS / Application",
        "attacks": [
            {
                "name": "SSRF (Server-Side Request Forgery)",
                "cve": "CVE-2019-1040",
                "tool": "Burp Suite + SSRFmap",
                "technique": "T1090",
                "description": (
                    "The attacker crafts a URL parameter or request body that causes the "
                    "server to make an HTTP request to attacker-controlled destinations. "
                    "In cloud environments, the IMDS endpoint (169.254.169.254 for AWS "
                    "IMDSv1) returns IAM role credentials with a single unauthenticated "
                    "request, providing full cloud account access."
                ),
                "impact": "Cloud credential theft; internal service access; metadata exposure; lateral movement to any internal network segment.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — SSRF is an application logic vulnerability; "
                    "PQC addresses cryptographic algorithm risk, not server-side request routing."
                ),
                "detection": "Outbound HTTP request monitoring from application tier, WAF SSRF rule sets.",
                "defense": "Block RFC-1918 and metadata IP ranges at application egress; enforce IMDSv2 (token-required); input validation.",
            },
            {
                "name": "HTTP Request Smuggling",
                "cve": "CVE-2019-18277",
                "tool": "smuggler.py",
                "technique": "T1190",
                "description": (
                    "CVE-2019-18277: HAProxy and similar reverse proxies parse HTTP/1.1 "
                    "Content-Length and Transfer-Encoding headers differently from backend "
                    "servers. The attacker crafts ambiguous requests that the proxy forwards "
                    "as one request but the backend interprets as two, prepending attacker "
                    "data to a subsequent victim's request—bypassing WAF rules and "
                    "poisoning shared caches."
                ),
                "impact": "WAF bypass; cache poisoning; credential theft from subsequent requests; full request hijacking.",
                "classical_result": "HIGH",
                "pqc_result": (
                    "UNCHANGED — HTTP parsing vulnerability; PQC migration does not affect "
                    "L7 HTTP header parsing logic."
                ),
                "detection": "HTTP parsing anomaly detection at reverse proxy layer; alert on conflicting Content-Length/Transfer-Encoding.",
                "defense": "Normalize HTTP/1.1 at proxy layer; enforce HTTP/2+ where possible; disable chunked encoding on sensitive paths.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L08 — JWT / Auth Tokens
    # -----------------------------------------------------------------------
    "L08": {
        "layer_id": "L08",
        "layer_name": "JWT / Auth Tokens",
        "attacks": [
            {
                "name": "JWT Algorithm Confusion (RS256 → HS256)",
                "cve": "CVE-2015-9235",
                "tool": "jwt_tool.py",
                "technique": "T1550.001",
                "description": (
                    "CVE-2015-9235: When a server verifies JWT signatures using the algorithm "
                    "specified in the token header without validating it against an allowed "
                    "list, an attacker changes 'alg: RS256' to 'alg: HS256' and signs the "
                    "forged token with the RSA public key (which is publicly known). The "
                    "server verifies HS256 using the RSA public key as HMAC secret—succeeding."
                ),
                "impact": "Complete authentication bypass; forge tokens for any user identity including admin.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "MITIGATED — ML-DSA JWT does not have a symmetric-equivalent confusion "
                    "attack; lattice signature verification is structurally distinct."
                ),
                "detection": "Server-side algorithm enforcement monitoring; alert on algorithm field mismatch.",
                "defense": "Never trust algorithm from token header; hardcode allowed algorithm server-side; use jwt library with strict alg enforcement.",
            },
            {
                "name": "JWT None Algorithm",
                "cve": "CVE-2016-10555",
                "tool": "jwt_tool.py",
                "technique": "T1550.001",
                "description": (
                    "CVE-2016-10555: JWT spec allows 'alg: none', meaning no signature. "
                    "Vulnerable libraries accept unsigned tokens if the header declares "
                    "alg: none. The attacker removes the signature, sets alg: none, and "
                    "modifies any claim (user ID, role) to arbitrary values."
                ),
                "impact": "Authentication bypass for any account; privilege escalation to any role.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "MITIGATED — ML-DSA JWT requires a valid lattice signature; "
                    "'none' algorithm cannot be satisfied by a hash-only approach."
                ),
                "detection": "Alert on 'alg: none' in JWT headers; JWT validation failure rate monitoring.",
                "defense": "Whitelist specific algorithms (RS256, ML-DSA); reject any token with alg: none; use strict JWT libraries.",
            },
            {
                "name": "JWT Secret Brute Force",
                "cve": "N/A",
                "tool": "hashcat + jwt2john",
                "technique": "T1110.002",
                "description": (
                    "HS256 JWT tokens are signed with a shared HMAC secret. jwt2john converts "
                    "a captured JWT into hashcat format; hashcat runs GPU-accelerated offline "
                    "dictionary and brute-force attacks. Secrets shorter than 256 bits or "
                    "derived from common words are cracked in seconds to hours."
                ),
                "impact": "Forge tokens for any user identity; full authentication bypass.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "ELIMINATED — ML-DSA uses public-key cryptography; "
                    "there is no shared secret to brute force."
                ),
                "detection": "Monitor for rapid JWT validation failures indicating offline attack with captured tokens.",
                "defense": "Use RS256 or ML-DSA (asymmetric); if HS256 is required, use a cryptographically random 512-bit secret.",
            },
            {
                "name": "JWT KID SQL/Path Injection",
                "cve": "N/A",
                "tool": "jwt_tool.py",
                "technique": "T1190",
                "description": (
                    "The JWT 'kid' (Key ID) header parameter tells the server which key "
                    "to use for verification. If the server passes 'kid' directly to a "
                    "database query or file path lookup without sanitization, the attacker "
                    "injects SQL (e.g. kid: \"1' OR '1'='1\") or a path traversal "
                    "(kid: '../../etc/shadow') to point to a known key they control."
                ),
                "impact": "Forge tokens for any user; SQL injection secondary impact; file disclosure.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — key ID injection is an application validation bug; "
                    "ML-DSA uses standard structured key IDs but same sanitization rules apply."
                ),
                "detection": "Monitor kid parameter values; SQL injection detection in key lookup queries.",
                "defense": "Whitelist valid key IDs; parameterize all database queries; never use kid as a file path directly.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L09 — DNS / DNSSEC
    # -----------------------------------------------------------------------
    "L09": {
        "layer_id": "L09",
        "layer_name": "DNS / DNSSEC",
        "attacks": [
            {
                "name": "DNS Cache Poisoning (Kaminsky Attack)",
                "cve": "CVE-2008-1447",
                "tool": "nsd-poisoner",
                "technique": "T1557.002",
                "description": (
                    "CVE-2008-1447 (Kaminsky): DNS resolvers use a 16-bit transaction ID "
                    "and a semi-random source port. The attacker floods the resolver with "
                    "forged responses for a target domain, racing legitimate responses. "
                    "With ~65,536 possible TXIDs, success probability per second is high. "
                    "Poisoned cache redirects all clients to attacker-controlled IP."
                ),
                "impact": "Redirect all DNS queries for target domain to attacker; enables phishing, MITM, credential theft at scale.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — Kaminsky attack exploits UDP randomness weakness, not cryptography; "
                    "DNSSEC with any signature algorithm (including Falcon-512) is the fix."
                ),
                "detection": "DNS anomaly detection (BIND response rate limiting), DNSSEC validation failures.",
                "defense": "Deploy DNSSEC + DNS-over-TLS (DoT) + QNAME minimization; enable source port randomization.",
            },
            {
                "name": "DNSSEC RSA Zone Signing Key Break (Quantum)",
                "cve": "N/A",
                "tool": "Shor's algorithm on CRQC",
                "technique": "T1600",
                "description": (
                    "DNSSEC Zone Signing Keys (ZSK) are typically RSA-2048. A CRQC runs "
                    "Shor's algorithm on the public ZSK to recover the private key. "
                    "The attacker then forges DNSSEC-signed records for any subdomain in "
                    "the zone, making cache-poisoned records appear DNSSEC-valid to "
                    "all validating resolvers."
                ),
                "impact": "Full DNS trust broken for zone; DNSSEC-signed fraudulent records accepted by all validators.",
                "classical_result": "CRITICAL (quantum-era)",
                "pqc_result": (
                    "SAFE — Falcon-512 DNSSEC (IETF draft) provides quantum-resistant signatures; "
                    "Shor's algorithm cannot solve NTRU lattice problems."
                ),
                "detection": "DNSSEC validation errors; unexpected RRSIG record changes; CT-for-DNS monitoring.",
                "defense": "Migrate DNSSEC ZSK/KSK to Falcon-512 per IETF draft; plan quantum-safe key rollover schedule.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L10 — SSH
    # -----------------------------------------------------------------------
    "L10": {
        "layer_id": "L10",
        "layer_name": "SSH",
        "attacks": [
            {
                "name": "OpenSSH Agent Forwarding RCE",
                "cve": "CVE-2023-38408",
                "tool": "PoC exploit (CVE-2023-38408)",
                "technique": "T1563.001",
                "description": (
                    "CVE-2023-38408: When SSH agent forwarding is enabled, the forwarded "
                    "agent socket is accessible on the remote host. A malicious remote host "
                    "(or attacker with access to it) loads a crafted PKCS#11 library via "
                    "the agent socket, triggering code execution on the SSH client machine—"
                    "the opposite direction from a normal SSH session."
                ),
                "impact": "Full client-side RCE; all secrets on the client machine accessible; lateral movement from compromised bastion.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — agent forwarding RCE is independent of key algorithm; "
                    "ML-DSA keys forwarded through an agent are equally vulnerable."
                ),
                "detection": "SSH agent forwarding usage monitoring; alert on ForwardAgent connections to non-bastion hosts.",
                "defense": "Disable SSH agent forwarding entirely (ForwardAgent no); use ssh-add -c for user-confirmation on each key use.",
            },
            {
                "name": "SSH Host Key TOFU Abuse",
                "cve": "N/A",
                "tool": "evilgrade / DNS spoofing",
                "technique": "T1557",
                "description": (
                    "SSH Trust-On-First-Use (TOFU): on first connection to a host, the "
                    "client accepts any host key without verification. An attacker MITM "
                    "on the first connection (via DNS spoofing or ARP poisoning) substitutes "
                    "their own host key. The victim's known_hosts is now poisoned; all "
                    "subsequent sessions are intercepted."
                ),
                "impact": "All SSH sessions to the target host intercepted; credentials, commands, and data exposed.",
                "classical_result": "HIGH",
                "pqc_result": (
                    "SAME RISK — ML-DSA host keys still subject to TOFU abuse on first connect; "
                    "algorithm strength is irrelevant if the wrong key is trusted."
                ),
                "detection": "known_hosts change monitoring; alert on first-connection to production hosts.",
                "defense": "Distribute host keys via configuration management (Ansible/Puppet) before first connection; disable TOFU in SSH config.",
            },
            {
                "name": "Terrapin Attack",
                "cve": "CVE-2023-48795",
                "tool": "Terrapin scanner",
                "technique": "T1040",
                "description": (
                    "CVE-2023-48795 (Terrapin): A prefix truncation attack on SSH Binary "
                    "Packet Protocol using ChaCha20-Poly1305 or CBC-EtM ciphers. An active "
                    "MITM can remove the first few messages of an SSH handshake without "
                    "detection, disabling security extensions such as keystroke timing "
                    "protection and Strict-KEX."
                ),
                "impact": "SSH security extensions disabled; keystroke timing side-channel enabled; connection downgraded.",
                "classical_result": "HIGH",
                "pqc_result": (
                    "UNCHANGED — Terrapin attacks the SSH BPP framing layer, not the key "
                    "exchange algorithm; PQC key types are not relevant to this framing attack."
                ),
                "detection": "SSH handshake negotiation monitoring; deploy Terrapin scanner to audit all SSH endpoints.",
                "defense": "Patch OpenSSH to 9.6+; disable ChaCha20-Poly1305 and CBC-EtM if unpatched; enable Strict-KEX.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L11 — Email S/MIME + PGP
    # -----------------------------------------------------------------------
    "L11": {
        "layer_id": "L11",
        "layer_name": "Email S/MIME + PGP",
        "attacks": [
            {
                "name": "EFAIL",
                "cve": "CVE-2017-17688 / CVE-2017-17689",
                "tool": "efail-poc",
                "technique": "T1114",
                "description": (
                    "EFAIL exploits email clients that render HTML after decrypting S/MIME "
                    "or PGP messages. The attacker wraps the encrypted ciphertext in a crafted "
                    "multipart MIME message containing an HTML img tag with an attacker-controlled "
                    "URL. When the client decrypts and renders the HTML, the plaintext is "
                    "appended to the URL in an outbound HTTP request."
                ),
                "impact": "All stored encrypted email decrypted and exfiltrated to attacker's server.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — EFAIL exploits MIME parsing and HTML rendering, not the "
                    "encryption algorithm; ML-KEM-encrypted emails are equally vulnerable "
                    "in an HTML-rendering client."
                ),
                "detection": "Outbound HTTP from email client with unusual URL patterns; HTML content in encrypted email monitoring.",
                "defense": "Disable HTML rendering in email client; decrypt emails in isolated offline environment; use S/MIME with Content-Type integrity.",
            },
            {
                "name": "PGP RSA Key Break (Quantum)",
                "cve": "N/A",
                "tool": "Shor's algorithm on CRQC",
                "technique": "T1600",
                "description": (
                    "OpenPGP RSA-4096 public keys are published on public keyservers. A CRQC "
                    "runs Shor's on these public keys, recovering private keys for any "
                    "target. Archived encrypted emails—including attachments containing IP, "
                    "legal documents, or clinical data—are decrypted in bulk."
                ),
                "impact": "All historically encrypted PGP email decryptable; no forward secrecy in PGP means all past emails exposed.",
                "classical_result": "CRITICAL (quantum-era)",
                "pqc_result": (
                    "SAFE — OpenPGP PQC draft (ML-DSA-65 + ML-KEM-768 hybrid) is quantum-resistant; "
                    "forward secrecy must be added via ephemeral ML-KEM subkeys."
                ),
                "detection": "Monitor PGP key server queries for bulk key downloads (reconnaissance for HNDL).",
                "defense": "Migrate PGP keys to PQC hybrid NOW; add ephemeral ML-KEM subkeys for forward secrecy; re-encrypt critical archived email.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L12 — Code Signing
    # -----------------------------------------------------------------------
    "L12": {
        "layer_id": "L12",
        "layer_name": "Code Signing",
        "attacks": [
            {
                "name": "Codecov CI/CD Supply Chain Injection",
                "cve": "N/A (2021 incident)",
                "tool": "MITM on CI/CD upload script",
                "technique": "T1195.002",
                "description": (
                    "In 2021, attackers compromised the Codecov bash uploader script hosted "
                    "on GCP. CI/CD pipelines downloading the script executed attacker code "
                    "that exfiltrated all environment variables—including code-signing keys, "
                    "cloud credentials, and secrets—to an attacker-controlled server. "
                    "The malicious code was present for two months before discovery."
                ),
                "impact": "All downstream CI/CD secrets exfiltrated; code-signing keys compromised; malicious code signed with legitimate keys.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — supply chain compromise steals the key material directly; "
                    "ML-DSA signing key is equally at risk if CI/CD environment is compromised."
                ),
                "detection": "Build script integrity monitoring (hash verification before execution); CI/CD secret scanning.",
                "defense": "Reproducible builds; in-toto provenance attestation; sign build scripts; rotate all CI/CD secrets post-incident.",
            },
            {
                "name": "SolarWinds-style Build System Backdoor",
                "cve": "CVE-2020-10148",
                "tool": "SUNBURST backdoor technique",
                "technique": "T1195.002",
                "description": (
                    "CVE-2020-10148 (SolarWinds Orion): Attackers compromised the SolarWinds "
                    "build system and injected SUNBURST malware into the Orion software "
                    "build pipeline before the code-signing step. The resulting installers "
                    "carried valid Authenticode RSA signatures, bypassing all code-signing "
                    "verification at 18,000+ customers."
                ),
                "impact": "Nation-state level supply chain compromise; 18,000 signed malicious updates deployed; zero trust in code signatures.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — build system compromise inserts malicious code before signing; "
                    "the algorithm used (RSA or ML-DSA) does not prevent pre-signing injection."
                ),
                "detection": "Binary transparency logs; code change auditing; build environment integrity monitoring.",
                "defense": "Multi-party build signing (M-of-N signers); binary transparency log; ephemeral immutable build environments.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L13 — VPN
    # -----------------------------------------------------------------------
    "L13": {
        "layer_id": "L13",
        "layer_name": "VPN",
        "attacks": [
            {
                "name": "WireGuard Curve25519 Quantum Break",
                "cve": "N/A",
                "tool": "Shor's algorithm on CRQC",
                "technique": "T1600",
                "description": (
                    "WireGuard uses Curve25519 (X25519) for ECDH key exchange. A CRQC running "
                    "Shor's algorithm on the elliptic curve discrete logarithm problem recovers "
                    "the Curve25519 private key from the public key broadcast in WireGuard "
                    "handshake messages. All WireGuard tunnel session keys derivable; "
                    "retroactive decryption of captured traffic possible."
                ),
                "impact": "All WireGuard VPN tunnels decryptable; zero confidentiality for any VPN traffic ever captured.",
                "classical_result": "CRITICAL (quantum-era)",
                "pqc_result": (
                    "SAFE — WireGuard PQ patch (ML-KEM-768 hybrid with X25519) provides "
                    "quantum-safe key exchange; session keys no longer derivable via Shor's."
                ),
                "detection": "Threat intelligence monitoring for CRQC capability announcements; bulk VPN traffic archiving detection.",
                "defense": "Deploy WireGuard PQ patch immediately; use hybrid X25519+ML-KEM-768 mode.",
            },
            {
                "name": "OpenVPN Heartbleed via OpenSSL",
                "cve": "CVE-2014-0160",
                "tool": "heartbleed-poc",
                "technique": "T1040",
                "description": (
                    "OpenVPN relies on OpenSSL for its TLS control channel. On vulnerable "
                    "OpenSSL versions, the Heartbleed bug (CVE-2014-0160) applies to the "
                    "OpenVPN TLS handshake. An attacker sends crafted heartbeat messages "
                    "to the OpenVPN management interface or TLS port, reading server memory "
                    "containing the VPN server's RSA private key."
                ),
                "impact": "OpenVPN server private key exposed; attacker can impersonate VPN server and decrypt all client traffic.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — Heartbleed is an OpenSSL implementation bug; "
                    "patching OpenSSL is required regardless of algorithm choice."
                ),
                "detection": "IDS signatures for Heartbleed probe patterns; OpenSSL version auditing.",
                "defense": "Patch OpenSSL; revoke and regenerate all VPN certificates; enable certificate pinning in VPN clients.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L14 — HSM / Key Management
    # -----------------------------------------------------------------------
    "L14": {
        "layer_id": "L14",
        "layer_name": "HSM / Key Management",
        "attacks": [
            {
                "name": "HashiCorp Vault Unseal Key Share Theft",
                "cve": "N/A",
                "tool": "custom (memory scraping + social engineering)",
                "technique": "T1552",
                "description": (
                    "HashiCorp Vault uses Shamir Secret Sharing to split the master unseal key "
                    "into N shares. During the unsealing ceremony, key holders input their "
                    "shares. An attacker with endpoint access to a key holder's machine "
                    "scrapes the share from memory or intercepts it in transit. "
                    "With a threshold number of shares, the master key is reconstructed."
                ),
                "impact": "Full Vault compromise; all secrets, certificates, and encryption keys exposed.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — Shamir share theft is an operational security issue; "
                    "PQC does not protect key ceremony operational procedures."
                ),
                "detection": "Unseal ceremony audit logging; monitor for anomalous unseal key input timing or locations.",
                "defense": "Hardware security tokens (YubiHSM) for unseal key shares; strict ceremony procedures; Auto-Unseal with KMS in production.",
            },
            {
                "name": "Vault RSA Key Wrapping Break (Quantum)",
                "cve": "N/A",
                "tool": "Shor's algorithm on CRQC",
                "technique": "T1600",
                "description": (
                    "Vault's Transit secrets engine uses RSA-4096 to wrap Data Encryption Keys "
                    "(DEKs). A CRQC applies Shor's to the RSA-4096 key wrapping key, recovering "
                    "the private key. All DEKs can then be unwrapped; all data encrypted "
                    "with those DEKs—across all applications using Vault—is decryptable."
                ),
                "impact": "All Vault-protected data across all applications decryptable; enterprise-wide cryptographic failure.",
                "classical_result": "CRITICAL (quantum-era)",
                "pqc_result": (
                    "SAFE — ML-KEM-1024 key wrapping in Vault's Transit engine; "
                    "RSA-4096 key wrapping key no longer present."
                ),
                "detection": "Monitor DEK decrypt operation volumes; anomalous bulk decryption requests.",
                "defense": "Migrate Vault Transit engine to ML-KEM-1024 key wrapping; re-wrap all active DEKs.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L15 — Identity / IAM
    # -----------------------------------------------------------------------
    "L15": {
        "layer_id": "L15",
        "layer_name": "Identity / IAM",
        "attacks": [
            {
                "name": "Golden Ticket Attack",
                "cve": "N/A",
                "tool": "mimikatz",
                "technique": "T1558.001",
                "description": (
                    "mimikatz's 'kerberos::golden' command requires only the krbtgt account "
                    "NTLM hash (the Kerberos KDC master key). With this hash, the attacker "
                    "crafts Kerberos Ticket Granting Tickets (TGTs) with arbitrary SIDs, "
                    "group memberships, and indefinite validity. The forged TGT bypasses "
                    "all AD authentication for any service, for any user, indefinitely."
                ),
                "impact": "Full Active Directory domain compromise; persistent access survives password resets.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "PARTIALLY MITIGATED — PKINIT with ML-DSA adds quantum-safe authentication "
                    "but does not prevent krbtgt hash theft; Golden Ticket requires krbtgt "
                    "key rotation + Kerberos Armoring (FAST) as the primary control."
                ),
                "detection": "Alert on TGT lifetimes exceeding domain policy (> 10 hours); Kerberos ticket anomaly detection.",
                "defense": "Rotate krbtgt twice; enable Kerberos Armoring (FAST); EDR on all Domain Controllers; privileged access workstations.",
            },
            {
                "name": "SAML Signature Wrapping Attack",
                "cve": "CVE-2012-6081",
                "tool": "SAML Raider (Burp Suite extension)",
                "technique": "T1606.002",
                "description": (
                    "CVE-2012-6081: SAML XML signature verification can be tricked by "
                    "XML Signature Wrapping (XSW). The attacker copies a legitimate signed "
                    "SAML assertion, inserts a forged assertion with different attributes "
                    "(e.g., admin:true), and wraps the legitimate signed XML around it. "
                    "The verifier validates the signature (which covers the original) but "
                    "uses the forged, unsigned assertion for authorization decisions."
                ),
                "impact": "SSO authentication bypass for any user including admin; no valid credential required.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "MITIGATED — ML-DSA SAML assertions require a valid lattice signature; "
                    "forged unsigned assertions will fail ML-DSA verification."
                ),
                "detection": "SAML assertion content validation monitoring; alert on unexpected role/attribute elevation.",
                "defense": "Strict XPath evaluation in SAML parsing; validate signature covers the exact assertion being used; schema validation.",
            },
            {
                "name": "Pass-the-Hash",
                "cve": "N/A",
                "tool": "mimikatz",
                "technique": "T1550.002",
                "description": (
                    "mimikatz's 'sekurlsa::pth' extracts NTLM hashes from LSASS memory "
                    "without needing to crack them. Windows authentication protocols "
                    "(NTLM, NTLMv2) accept the raw hash as a credential; the attacker "
                    "authenticates to any Windows service as the compromised user without "
                    "ever knowing the plaintext password."
                ),
                "impact": "Lateral movement across entire domain; admin access to any system where compromised user has rights.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — NTLM hash authentication is not public-key crypto; "
                    "PQC migration does not address NTLM hash extraction."
                ),
                "detection": "EDR memory access monitoring on LSASS; alert on NTLM authentication from non-expected sources.",
                "defense": "Deploy Credential Guard (VBS-protected LSASS); disable NTLM; enforce Kerberos with PKINIT.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L16 — API Security
    # -----------------------------------------------------------------------
    "L16": {
        "layer_id": "L16",
        "layer_name": "API Security",
        "attacks": [
            {
                "name": "BOLA / IDOR (Broken Object Level Authorization)",
                "cve": "N/A (OWASP API Security Top 10, API-1)",
                "tool": "Burp Suite",
                "technique": "T1190",
                "description": (
                    "REST APIs return user-specific objects via sequential or guessable IDs "
                    "(e.g., /api/accounts/1234). Without server-side authorization checks "
                    "verifying the requesting user owns the object, any authenticated user "
                    "can enumerate IDs and access any other user's data by changing the "
                    "ID parameter."
                ),
                "impact": "Mass data exposure; all user records, financial data, PII accessible to any authenticated user.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — BOLA/IDOR is an authorization logic vulnerability; "
                    "PQC addresses cryptographic keys, not API authorization enforcement."
                ),
                "detection": "API access pattern anomaly detection; monitor for sequential ID enumeration patterns.",
                "defense": "Enforce object-level authorization on every API endpoint; use opaque UUIDs; API gateway authorization policies.",
            },
            {
                "name": "API Key Hardcoded in Source (Secret Leakage)",
                "cve": "N/A",
                "tool": "gitleaks / trufflehog",
                "technique": "T1552.001",
                "description": (
                    "API keys, tokens, and secrets accidentally committed to public or "
                    "semi-private Git repositories are found within hours by automated tools "
                    "like trufflehog and Shhgit continuously scanning GitHub. The attacker "
                    "uses the discovered key to access all API endpoints the key authorizes."
                ),
                "impact": "Full API access; data exfiltration; account hijacking; cloud resource abuse at attacker's will.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — secret leakage in Git is an operational security issue; "
                    "PQC does not protect accidentally committed secrets."
                ),
                "detection": "Secret scanning in CI/CD (gitleaks pre-commit hooks); GitHub Advanced Security secret scanning.",
                "defense": "HashiCorp Vault or AWS Secrets Manager for all API keys; pre-commit hooks block secrets; rotate keys immediately on detection.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L17 — Database
    # -----------------------------------------------------------------------
    "L17": {
        "layer_id": "L17",
        "layer_name": "Database",
        "attacks": [
            {
                "name": "SQL Injection",
                "cve": "CVE-2007-0882",
                "tool": "sqlmap",
                "technique": "T1190",
                "description": (
                    "Unsanitized user input is concatenated into SQL queries. sqlmap automates "
                    "detection and exploitation of SQL injection, supporting time-based blind, "
                    "boolean-based blind, UNION-based, and error-based extraction. On MSSQL, "
                    "xp_cmdshell enables OS command execution. On MySQL, LOAD_FILE and INTO "
                    "OUTFILE enable file system access."
                ),
                "impact": "Entire database dumped; OS command execution on some databases; credential extraction.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — SQL injection is an application-layer input validation failure; "
                    "PQC does not affect database query parsing."
                ),
                "detection": "WAF SQL injection signatures; database query anomaly detection; application-layer input monitoring.",
                "defense": "Parameterized queries (prepared statements); ORM with query builder; least-privilege database accounts; WAF.",
            },
            {
                "name": "Database Backup Encryption Key Break (Quantum)",
                "cve": "N/A",
                "tool": "Shor's algorithm on CRQC",
                "technique": "T1600",
                "description": (
                    "Enterprise database backups are encrypted with RSA-2048 key wrapping "
                    "around symmetric DEKs. A CRQC recovers the RSA private key, unwraps "
                    "the DEK, and decrypts all database backups. Organisations retaining "
                    "backups for 7+ years expose 7 years of historical data."
                ),
                "impact": "Complete historical database exposure including all PII, financial records, and cryptographic keys stored in DB.",
                "classical_result": "CRITICAL (quantum-era)",
                "pqc_result": (
                    "SAFE — ML-KEM-768 backup encryption; symmetric AES-256 DEKs remain secure; "
                    "Grover's algorithm provides only quadratic speedup against AES-256."
                ),
                "detection": "Monitor backup key usage; anomalous bulk backup decryption requests.",
                "defense": "Migrate backup encryption key wrapping to ML-KEM-768; re-encrypt all retained backups; key rotation policy.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L18 — Blockchain
    # -----------------------------------------------------------------------
    "L18": {
        "layer_id": "L18",
        "layer_name": "Blockchain",
        "attacks": [
            {
                "name": "ECDSA Private Key Recovery (Weak k-value)",
                "cve": "CVE-2010-5141 (Sony PS3 incident)",
                "tool": "custom lattice attack / ECDSA nonce recovery",
                "technique": "T1642",
                "description": (
                    "ECDSA security requires the nonce k to be unique and unpredictable per "
                    "signature. Sony's PS3 used a constant k across all signatures. With two "
                    "signatures sharing the same k, the private key is recoverable via simple "
                    "algebra. Cryptocurrency implementations with biased or reused k values "
                    "are similarly vulnerable to lattice attacks using ~20-50 signatures."
                ),
                "impact": "Complete wallet private key recovery; all funds stolen; identity fully impersonated.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "MITIGATED — Falcon-512 lattice signatures use deterministic randomness "
                    "without a k-value; the NTRU lattice structure removes this attack class entirely."
                ),
                "detection": "Monitor signing k-value entropy; detect duplicate or low-entropy k values in on-chain signature analysis.",
                "defense": "Deterministic ECDSA (RFC 6979); migrate to Falcon-512 wallets; hardware wallet with certified RNG.",
            },
            {
                "name": "Quantum Wallet Attack (Shor on ECDSA)",
                "cve": "N/A",
                "tool": "Shor's algorithm on CRQC",
                "technique": "T1642",
                "description": (
                    "Bitcoin P2PK and P2PKH addresses expose the ECDSA public key on-chain. "
                    "A CRQC running Shor's algorithm on the secp256k1 elliptic curve recovers "
                    "the private key from the public key. Approximately 4 million BTC in "
                    "P2PK addresses (including Satoshi's coins) are immediately vulnerable. "
                    "P2PKH addresses expose the public key only when spending, creating a "
                    "race condition."
                ),
                "impact": "All exposed-public-key cryptocurrency wallets drained; trillions in crypto assets at risk.",
                "classical_result": "CRITICAL (quantum-era)",
                "pqc_result": (
                    "SAFE — Falcon-512 wallets and PQC Bitcoin proposals (SNOVA, etc.); "
                    "Shor's algorithm cannot solve NTRU lattice hard problems."
                ),
                "detection": "Quantum computer capability monitoring; unusual P2PK spending patterns suggesting key recovery.",
                "defense": "Migrate to PQC wallets before CRQC; use P2TR (Taproot) addresses to delay public key exposure; emergency migration protocols.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L19 — Container / Service Mesh
    # -----------------------------------------------------------------------
    "L19": {
        "layer_id": "L19",
        "layer_name": "Container / Service Mesh",
        "attacks": [
            {
                "name": "Container Escape via runc (CVE-2019-5736)",
                "cve": "CVE-2019-5736",
                "tool": "CVE-2019-5736-PoC",
                "technique": "T1611",
                "description": (
                    "CVE-2019-5736: runc (the container runtime used by Docker and Kubernetes) "
                    "allows a malicious container to overwrite the host's runc binary during "
                    "exec operations. The attacker runs a malicious process inside the container "
                    "that races to replace /proc/self/exe (which points to runc) with a "
                    "malicious binary, executing as root on the host."
                ),
                "impact": "Full host system compromise from within a container; escape from all container isolation.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — container runtime vulnerability is unrelated to cryptographic "
                    "algorithm; PQC does not affect container isolation mechanisms."
                ),
                "detection": "Falco container escape detection rules; monitor for /proc/self/exe write attempts.",
                "defense": "Patch runc; use rootless containers; deploy seccomp/AppArmor profiles; Kata Containers for additional isolation.",
            },
            {
                "name": "Istio mTLS Bypass (CVE-2022-21701)",
                "cve": "CVE-2022-21701",
                "tool": "custom exploit",
                "technique": "T1557",
                "description": (
                    "CVE-2022-21701: Istio's PeerAuthentication policy misconfiguration or "
                    "version-specific bugs allow services to bypass mTLS enforcement. "
                    "Traffic marked as PERMISSIVE mode falls back to plaintext; attackers "
                    "with network access to the service mesh can send unauthenticated "
                    "service-to-service requests bypassing all Istio authorization policies."
                ),
                "impact": "Internal microservice-to-microservice communication compromised; all service mesh authorization bypassed.",
                "classical_result": "HIGH",
                "pqc_result": (
                    "UNCHANGED — mTLS bypass exploits policy misconfiguration; "
                    "ML-DSA mTLS certificates still require proper PeerAuthentication enforcement."
                ),
                "detection": "mTLS enforcement monitoring; alert on plaintext service mesh traffic; Istio audit log anomalies.",
                "defense": "Set PeerAuthentication to STRICT mode globally; regular Istio security configuration audits; GitOps for mesh policy.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L20 — IoT
    # -----------------------------------------------------------------------
    "L20": {
        "layer_id": "L20",
        "layer_name": "IoT",
        "attacks": [
            {
                "name": "Firmware Extraction and Hardcoded Key Recovery",
                "cve": "N/A",
                "tool": "binwalk + strings + Ghidra",
                "technique": "T1592",
                "description": (
                    "binwalk extracts filesystem images from IoT firmware; strings and Ghidra "
                    "disassembly reveal hardcoded RSA private keys, TLS certificates, and "
                    "device-specific credentials embedded in firmware. A single device "
                    "purchase provides keys that decrypt communications across the entire "
                    "device fleet if per-device keys are not used."
                ),
                "impact": "Mass compromise of device fleet; all encrypted device communications decryptable; remote command injection.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "PARTIALLY MITIGATED — Falcon-512 keys in firmware are still extractable; "
                    "a Hardware Security Element (HSE/SE050) prevents key extraction by design."
                ),
                "detection": "Firmware integrity monitoring; DeviceID certificate rotation anomaly detection.",
                "defense": "Hardware Security Element (NXP SE050) for all key storage; no hardcoded keys; per-device certificate provisioning.",
            },
            {
                "name": "MQTT Credential Theft (CVE-2018-12551)",
                "cve": "CVE-2018-12551",
                "tool": "mqtt-pwn",
                "technique": "T1040",
                "description": (
                    "CVE-2018-12551: MQTT brokers with weak or absent authentication allow "
                    "any client to subscribe to wildcard topics (#). mqtt-pwn automates "
                    "discovery of open MQTT brokers, subscribes to all topics, and captures "
                    "plaintext device telemetry, commands, and credentials. Many industrial "
                    "IoT deployments run MQTT without TLS."
                ),
                "impact": "Complete IoT system telemetry visibility; command injection into industrial devices; device credential exposure.",
                "classical_result": "HIGH",
                "pqc_result": (
                    "UNCHANGED — MQTT authentication weakness is protocol-level; "
                    "PQC does not address broker authentication policy."
                ),
                "detection": "MQTT subscription anomaly monitoring; alert on wildcard # subscriptions from unknown clients.",
                "defense": "Mandatory TLS + client certificate authentication for MQTT; per-device ACL; disable anonymous access.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L21 — Mobile
    # -----------------------------------------------------------------------
    "L21": {
        "layer_id": "L21",
        "layer_name": "Mobile",
        "attacks": [
            {
                "name": "Certificate Pinning Bypass via Frida",
                "cve": "N/A",
                "tool": "objection / frida",
                "technique": "T1539",
                "description": (
                    "Frida is a dynamic instrumentation toolkit. objection automates "
                    "certificate pinning bypass by hooking TrustManager, SSLPeerUnverifiedException, "
                    "and OkHttp pinning logic at runtime. Running on a rooted/jailbroken "
                    "device, the hook disables certificate validation, allowing Burp Suite "
                    "to MITM all app traffic."
                ),
                "impact": "All application TLS traffic interceptable; API credentials, session tokens, and user data exposed.",
                "classical_result": "HIGH",
                "pqc_result": (
                    "SAME RISK — PQC TLS certificates are equally bypassable if "
                    "the certificate validation code is patched out via Frida."
                ),
                "detection": "Jailbreak/root detection in application; emulation detection; hook detection.",
                "defense": "Certificate pinning + anti-Frida/anti-debug code; Play Integrity API (Android); runtime integrity checks.",
            },
            {
                "name": "FIDO2 ECDSA Authenticator Key Recovery (Quantum)",
                "cve": "N/A",
                "tool": "Shor's algorithm on CRQC",
                "technique": "T1600",
                "description": (
                    "FIDO2 WebAuthn authenticators use ECDSA P-256 as the default credential "
                    "type. The public key is registered with relying parties. A CRQC runs "
                    "Shor's on the ECDSA P-256 public key, recovering the authenticator "
                    "private key. The attacker can then impersonate any FIDO2 authenticator "
                    "for passwordless authentication to any relying party."
                ),
                "impact": "Impersonate any FIDO2 hardware token; bypass passwordless authentication for any account.",
                "classical_result": "CRITICAL (quantum-era)",
                "pqc_result": (
                    "MITIGATED (future) — FIDO2 ML-DSA credential type is under FIDO Alliance "
                    "specification; migration path exists once standardized."
                ),
                "detection": "Authenticator attestation monitoring; alert on authenticator key usage from unexpected locations.",
                "defense": "Migrate to PQC FIDO2 credential types when standardized; monitor FIDO Alliance PQC specification progress.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L22 — Firmware / Secure Boot
    # -----------------------------------------------------------------------
    "L22": {
        "layer_id": "L22",
        "layer_name": "Firmware / Secure Boot",
        "attacks": [
            {
                "name": "BootHole GRUB2 Secure Boot Bypass",
                "cve": "CVE-2020-10713",
                "tool": "BootHole-exploit",
                "technique": "T1542.001",
                "description": (
                    "CVE-2020-10713 (BootHole): Buffer overflow in GRUB2's parsing of "
                    "grub.cfg configuration file. Since grub.cfg is not itself Secure Boot "
                    "signed, a malicious grub.cfg triggers the overflow before the kernel "
                    "is loaded, executing attacker code in the GRUB context—before Secure "
                    "Boot measurements are completed—installing a persistent bootkit."
                ),
                "impact": "Persistent pre-OS malware; Secure Boot bypassed; full kernel-level compromise survives reinstallation.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — BootHole is a buffer overflow in GRUB2; "
                    "replacing Secure Boot RSA with ML-DSA does not patch the grub.cfg parsing bug."
                ),
                "detection": "Secure Boot PCR measurement monitoring; unexpected grub.cfg modification detection.",
                "defense": "Patch GRUB2; update UEFI DBX revocation list to revoke vulnerable GRUB2 binaries; sign grub.cfg.",
            },
            {
                "name": "TPM PCR Replay Attack",
                "cve": "CVE-2021-3544",
                "tool": "custom TPM attack tooling",
                "technique": "T1542",
                "description": (
                    "CVE-2021-3544: TPM PCR (Platform Configuration Register) values from "
                    "a known-good system state can be replayed during attestation if the "
                    "attestation protocol does not enforce freshness. An attacker replays "
                    "golden PCR values to a modified system's TPM during attestation, "
                    "making it appear unmodified even after firmware or OS tampering."
                ),
                "impact": "Firmware tampering goes undetected; compromised system certified as trusted; attestation-based access granted.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "MITIGATED — TPM 3.0 with ML-KEM attestation and nonce-based quotes; "
                    "freshness nonce prevents replay of static PCR values."
                ),
                "detection": "TPM quote freshness verification; monitor attestation nonce reuse.",
                "defense": "Nonce-based TPM attestation (fresh nonce per quote); deploy TPM 3.0 with FIPS 140-3 ML-KEM support.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L23 — DevSecOps / CI-CD
    # -----------------------------------------------------------------------
    "L23": {
        "layer_id": "L23",
        "layer_name": "DevSecOps / CI-CD",
        "attacks": [
            {
                "name": "CI/CD Pipeline Injection (XZ Utils 2024 style)",
                "cve": "N/A (XZ Utils CVE-2024-3094)",
                "tool": "malicious pull request / insider threat",
                "technique": "T1195.002",
                "description": (
                    "CVE-2024-3094 (XZ Utils): A social engineering campaign over 2 years "
                    "established trust as an open-source maintainer, then injected a backdoor "
                    "into the XZ Utils compression library. The backdoor modified systemd's "
                    "sshd integration to allow unauthenticated RSA key-based RCE. The "
                    "malicious code ran in CI/CD pipelines and was signed with legitimate keys."
                ),
                "impact": "Supply chain compromise of all released software; nation-state backdoor in infrastructure package affecting millions of systems.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — code injection before the signing step is not an algorithm "
                    "vulnerability; both RSA and ML-DSA signing are neutralized by pre-signing injection."
                ),
                "detection": "Build environment integrity monitoring; diff-based commit review; binary reproducibility verification.",
                "defense": "Ephemeral build environments; reproducible builds; multi-party code review; in-toto provenance; SLSA level 3+.",
            },
            {
                "name": "GPG Commit Signing Key Break (Quantum)",
                "cve": "N/A",
                "tool": "Shor's algorithm on CRQC",
                "technique": "T1600",
                "description": (
                    "Developer GPG keys used for git commit signing are typically RSA-4096 "
                    "or ECDSA. Public keys are on keyservers. A CRQC recovers the private "
                    "signing key, allowing arbitrary commit signatures. All signed commits "
                    "in repositories using commit signature verification become forgeable, "
                    "breaking audit trails and code provenance."
                ),
                "impact": "All commit signatures forgeable; complete code provenance compromise; fraudulent commits appear legitimate.",
                "classical_result": "CRITICAL (quantum-era)",
                "pqc_result": (
                    "SAFE — ML-DSA GPG keys (OpenPGP PQC draft RFC 9580) quantum-resistant; "
                    "Shor's cannot recover ML-DSA private keys."
                ),
                "detection": "Commit signature anomaly detection; unusual signing key changes in Git history.",
                "defense": "Migrate all developer GPG keys to ML-DSA per OpenPGP PQC draft; binary transparency log for all releases.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L24 — SIEM / Logging
    # -----------------------------------------------------------------------
    "L24": {
        "layer_id": "L24",
        "layer_name": "SIEM / Logging",
        "attacks": [
            {
                "name": "Log Injection via CRLF",
                "cve": "N/A",
                "tool": "custom exploit / Burp Suite",
                "technique": "T1565.002",
                "description": (
                    "Application log entries containing unsanitized user input allow injection "
                    "of CRLF (\\r\\n) characters. Injected lines create fake log events that "
                    "appear to come from legitimate sources, covering attacker tracks. "
                    "Injecting entries with earlier timestamps creates retrospective false "
                    "audit trails. Log aggregation pipelines may split entries incorrectly."
                ),
                "impact": "Attacker's real activity hidden; false exculpatory evidence injected; forensic investigation corrupted.",
                "classical_result": "HIGH",
                "pqc_result": (
                    "UNCHANGED — log injection is an application input sanitization issue; "
                    "PQC does not affect log entry parsing."
                ),
                "detection": "Log integrity validation via HMAC-SHA256 chain per entry; alert on unexpected log line count gaps.",
                "defense": "Structured logging (JSON with no free-form string interpolation); HMAC-SHA256 log chain; real-time SIEM shipping.",
            },
            {
                "name": "Wazuh SIEM Agent RCE (CVE-2023-34268)",
                "cve": "CVE-2023-34268",
                "tool": "PoC exploit for CVE-2023-34268",
                "technique": "T1505",
                "description": (
                    "CVE-2023-34268: Buffer overflow vulnerability in Wazuh agent versions "
                    "prior to 4.5.3. An attacker with network access to the Wazuh manager "
                    "or able to send crafted messages to the agent port can trigger the "
                    "overflow, achieving RCE on the monitored endpoint. The attacker can "
                    "then disable logging, inject false telemetry, and blind the SIEM."
                ),
                "impact": "SIEM monitoring disabled on compromised endpoint; attacker can exfiltrate data invisibly; false telemetry poisons SOC analysis.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — CVE is in Wazuh agent C code, not cryptographic algorithm; "
                    "patching is required regardless of PQC migration."
                ),
                "detection": "Agent health heartbeat monitoring; alert on agent process crash or restart.",
                "defense": "Patch Wazuh to 4.5.3+; principle of least privilege for Wazuh agent; network segmentation for SIEM infrastructure.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L25 — Zero Trust / SPIFFE
    # -----------------------------------------------------------------------
    "L25": {
        "layer_id": "L25",
        "layer_name": "Zero Trust / SPIFFE",
        "attacks": [
            {
                "name": "SPIFFE SVID Forgery (Quantum)",
                "cve": "N/A",
                "tool": "Shor's algorithm on CRQC",
                "technique": "T1600",
                "description": (
                    "SPIFFE SVIDs (SPIRE Verifiable Identity Documents) are X.509 certificates "
                    "signed with the SPIRE server's ECDSA P-256 key. A CRQC recovers the "
                    "ECDSA private signing key, allowing forgery of SVIDs for any workload "
                    "identity in the mesh. All zero-trust policy decisions based on SVID "
                    "verification are bypassed."
                ),
                "impact": "Complete zero-trust model bypass; any workload identity impersonable; all service mesh policies defeated.",
                "classical_result": "CRITICAL (quantum-era)",
                "pqc_result": (
                    "SAFE — ML-DSA SVIDs make SVID forgery computationally infeasible; "
                    "Module-LWE hard problem not solvable by Shor's."
                ),
                "detection": "SVID issuance rate anomaly monitoring; alert on SVIDs with unexpected SPIFFE IDs.",
                "defense": "Migrate SPIRE to ML-DSA SVID signing; frequent SVID rotation (1-hour TTL); certificate transparency for SVIDs.",
            },
            {
                "name": "OIDC Token Forgery (Quantum)",
                "cve": "N/A",
                "tool": "Shor's algorithm on CRQC",
                "technique": "T1600",
                "description": (
                    "OIDC identity providers sign tokens with RS256 (RSA-2048 or RSA-4096). "
                    "A CRQC recovers the OIDC provider's RS256 signing key, enabling "
                    "forgery of identity tokens for any sub claim (user identity). All "
                    "applications accepting OIDC tokens from the provider are compromised; "
                    "any OAuth2-protected resource is accessible."
                ),
                "impact": "Full SSO system bypass; forge identity tokens for any user including service accounts with elevated permissions.",
                "classical_result": "CRITICAL (quantum-era)",
                "pqc_result": (
                    "SAFE — ML-DSA OIDC tokens; RS256 signing key replaced; "
                    "token forgery requires solving Module-LWE."
                ),
                "detection": "OIDC token validation failure monitoring; alert on tokens with unusual claims or lifetimes.",
                "defense": "Migrate OIDC provider to ML-DSA token signing; enforce short token lifetimes (15 min max); OIDC discovery endpoint monitoring.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L26 — Key Management / KMS
    # -----------------------------------------------------------------------
    "L26": {
        "layer_id": "L26",
        "layer_name": "Key Management / KMS",
        "attacks": [
            {
                "name": "Vault High-Privilege Token Theft (CVE-2023-2197)",
                "cve": "CVE-2023-2197",
                "tool": "custom (token extraction from logs/memory)",
                "technique": "T1552",
                "description": (
                    "CVE-2023-2197: Vault tokens leaked in application logs, environment "
                    "variables, or memory dumps. High-privilege root/admin tokens with long "
                    "or infinite TTLs give complete Vault access. An attacker finds a leaked "
                    "token in a Kubernetes secret, log aggregation system, or CI/CD environment "
                    "variable and uses it to access all secrets."
                ),
                "impact": "All Vault secrets and keys exposed; all applications using Vault compromised; encryption keys retrievable.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — token theft is an operational security and secret management "
                    "issue; PQC algorithm migration does not protect leaked tokens."
                ),
                "detection": "Vault audit log monitoring for unusual token usage patterns; alert on root token activity outside of ceremonies.",
                "defense": "Short-lived tokens (TTL ≤ 1 hour); token accessor monitoring; Vault Sentinel policies; never log tokens.",
            },
            {
                "name": "SOPS Master Key Break (Quantum)",
                "cve": "N/A",
                "tool": "Shor's algorithm on CRQC",
                "technique": "T1600",
                "description": (
                    "Mozilla SOPS encrypts secrets files using RSA-4096 or age encryption "
                    "as master keys. Repositories containing SOPS-encrypted secrets (common "
                    "in GitOps workflows) are publicly or semi-publicly accessible. "
                    "A CRQC recovering the RSA-4096 SOPS master key decrypts all "
                    "encrypted secrets files in all repositories."
                ),
                "impact": "All secrets in all GitOps repositories decryptable; database passwords, API keys, TLS certificates all exposed.",
                "classical_result": "CRITICAL (quantum-era)",
                "pqc_result": (
                    "SAFE — migrate SOPS to age + ML-KEM key; age's X25519 replaced by ML-KEM; "
                    "RSA-4096 master key no longer in use."
                ),
                "detection": "SOPS key usage monitoring; alert on bulk SOPS decryption operations.",
                "defense": "Migrate SOPS to age + ML-KEM hybrid; re-encrypt all SOPS-protected files; rotate all secrets post-migration.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L27 — Compliance
    # -----------------------------------------------------------------------
    "L27": {
        "layer_id": "L27",
        "layer_name": "Compliance",
        "attacks": [
            {
                "name": "Compliance Drift via IaC Misconfiguration",
                "cve": "N/A",
                "tool": "Prowler / Checkov",
                "technique": "T1562",
                "description": (
                    "Infrastructure as Code (IaC) configurations drift from compliant "
                    "baselines when developers modify resources directly in the cloud console "
                    "without updating IaC. Prowler and Checkov continuously scan for "
                    "non-compliant resources. Attackers specifically target drift—misconfigured "
                    "S3 buckets, open security groups, disabled audit logs—as low-resistance "
                    "entry points."
                ),
                "impact": "PCI-DSS violations; data breach via misconfigured storage; regulatory fines; undetected attacker persistence.",
                "classical_result": "HIGH",
                "pqc_result": (
                    "UNCHANGED — compliance drift is an IaC governance issue; "
                    "PQC migration does not automatically enforce cloud compliance controls."
                ),
                "detection": "Continuous CSPM scanning (Prowler, Wiz, Orca); alert on any deviation from IaC-defined state.",
                "defense": "Policy-as-code (OPA, Sentinel); CSPM integrated into CI/CD; detect and auto-remediate drift; cloud config immutability.",
            },
            {
                "name": "FIPS 140-2 vs FIPS 140-3 Algorithm Gap",
                "cve": "N/A",
                "tool": "NIST SP 800-140 algorithm assessment",
                "technique": "T1600",
                "description": (
                    "FIPS 140-2 approved algorithm list includes SHA-1 and 2-key 3DES, "
                    "both cryptographically weak. Organizations using FIPS 140-2 validated "
                    "modules may implement SHA-1 for digital signatures or 2-key 3DES for "
                    "encryption and remain technically 'compliant' while being cryptographically "
                    "insecure. FIPS 140-3 (effective Sept 2026) removes these."
                ),
                "impact": "False compliance assurance; systems using SHA-1 or 2-key 3DES vulnerable while believing they meet FIPS requirements.",
                "classical_result": "HIGH",
                "pqc_result": (
                    "RESOLVED — FIPS 140-3 required for PQC compliance; "
                    "FIPS 140-3 removes SHA-1 and 2-key 3DES; ML-KEM/ML-DSA are FIPS 140-3 approved."
                ),
                "detection": "Algorithm usage auditing; FIPS module version inventory; automated cipher suite scanning.",
                "defense": "Upgrade all modules to FIPS 140-3 validated; remove SHA-1 and 2-key 3DES from all configurations.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L28 — Audit / Non-Repudiation
    # -----------------------------------------------------------------------
    "L28": {
        "layer_id": "L28",
        "layer_name": "Audit / Non-Repudiation",
        "attacks": [
            {
                "name": "Timestamp Authority Key Break (Quantum)",
                "cve": "N/A",
                "tool": "Shor's algorithm on CRQC",
                "technique": "T1600",
                "description": (
                    "RFC 3161 Trusted Timestamps use RSA-2048 signing by a Timestamp "
                    "Authority (TSA). A CRQC recovers the TSA's RSA private key, allowing "
                    "retroactive forgery of timestamps for any document. Forged timestamps "
                    "allow backdating malicious code signatures, legal documents, or "
                    "financial records."
                ),
                "impact": "All timestamped evidence tampered; audit non-repudiation eliminated; legal/forensic evidence invalidated.",
                "classical_result": "CRITICAL (quantum-era)",
                "pqc_result": (
                    "SAFE — SLH-DSA (SPHINCS+) for RFC 3161 TSA is stateless hash-based; "
                    "quantum-safe by construction; no lattice or factoring assumption required."
                ),
                "detection": "Timestamp certificate chain validation; CT-style monitoring for TSA certificate changes.",
                "defense": "Migrate TSA to SLH-DSA (FIPS 205); dual-timestamp with independent TSAs; long-term archive validation (LTV).",
            },
            {
                "name": "Audit Log Deletion",
                "cve": "N/A",
                "tool": "manual / privileged insider",
                "technique": "T1070",
                "description": (
                    "A privileged attacker (or compromised admin account) deletes audit "
                    "logs stored on the compromised system before they are shipped to a "
                    "remote SIEM. Local log deletion removes evidence of the initial "
                    "compromise, lateral movement, data exfiltration, and persistence "
                    "mechanisms, making incident response reconstruction impossible."
                ),
                "impact": "No forensic evidence of compromise; incident timeline unrecoverable; compliance audit failures.",
                "classical_result": "HIGH",
                "pqc_result": (
                    "UNCHANGED — log deletion is an access control and log pipeline issue; "
                    "PQC does not protect logs from privileged deletion."
                ),
                "detection": "Log completeness monitoring (gaps or unexpected silence = alert); real-time SIEM streaming before local storage.",
                "defense": "Write-once log storage (AWS S3 Object Lock, WORM storage); real-time SIEM shipping; immutable log chain with HMAC.",
            },
        ],
    },

    # -----------------------------------------------------------------------
    # L29 — AI / ML Security
    # -----------------------------------------------------------------------
    "L29": {
        "layer_id": "L29",
        "layer_name": "AI / ML Security",
        "attacks": [
            {
                "name": "Model Poisoning via Backdoored Training Data",
                "cve": "N/A",
                "tool": "BadNets / backdoor injection framework",
                "technique": "T1565",
                "description": (
                    "BadNets demonstrates that injecting a small percentage (< 1%) of "
                    "backdoored samples into training data causes a neural network to "
                    "misclassify any input containing a specific trigger pattern. An "
                    "attacker with access to the training pipeline injects fraudulent "
                    "transactions labeled as legitimate, causing the fraud detection "
                    "model to approve attacker-controlled patterns."
                ),
                "impact": "ML fraud detection model compromised; specific transaction patterns bypass detection indefinitely.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — model poisoning is an ML security issue; "
                    "PQC addresses cryptographic key security, not model training data integrity."
                ),
                "detection": "Model drift monitoring; input distribution analysis; certified defense (activation clustering) for backdoor detection.",
                "defense": "Data sanitization pipelines; certified defenses (spectral signatures, activation clustering); strict data provenance; differential privacy.",
            },
            {
                "name": "Prompt Injection via Malicious Alert Content",
                "cve": "N/A",
                "tool": "custom LLM adversarial attack (Garak testing framework)",
                "technique": "T1190",
                "description": (
                    "LLM-powered SIEM systems summarize security alerts automatically. "
                    "An attacker embeds prompt injection payloads in monitored content "
                    "(e.g., a web request, a log entry, or malware C2 traffic). When "
                    "the payload is ingested and processed by the LLM, it overrides the "
                    "system prompt, instructing the model to suppress or falsify the "
                    "security summary, hiding critical alerts from analysts."
                ),
                "impact": "Critical security alerts suppressed; attacker activity rendered invisible to AI-powered security monitoring.",
                "classical_result": "CRITICAL",
                "pqc_result": (
                    "UNCHANGED — prompt injection is an LLM architectural vulnerability; "
                    "PQC does not protect LLM input processing pipelines."
                ),
                "detection": "LLM output monitoring; Garak adversarial testing of SIEM LLM; anomaly detection on summarization outputs.",
                "defense": "Output filtering and sandboxing; never render LLM output as trusted commands; separate LLM from action execution plane.",
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# BrutalLayerAttacks class
# ---------------------------------------------------------------------------

class BrutalLayerAttacks:
    """
    Comprehensive attack simulation across all 29 security layers.

    All data is educational and defensive. Understanding attack mechanics
    is required for building quantum-safe defenses.
    """

    def __init__(self) -> None:
        self._data = LAYER_ATTACKS

    # ------------------------------------------------------------------
    # Core queries
    # ------------------------------------------------------------------

    def get_layer_attacks(self, layer_id: str) -> dict[str, Any] | None:
        """Return the full attack dict for a given layer_id (e.g. 'L04')."""
        lid = layer_id.upper()
        return self._data.get(lid)

    def get_critical_attacks(self) -> list[dict[str, Any]]:
        """Return all attacks where classical_result starts with 'CRITICAL'."""
        results: list[dict[str, Any]] = []
        for layer in self._data.values():
            for attack in layer["attacks"]:
                if attack["classical_result"].upper().startswith("CRITICAL"):
                    results.append({**attack, "_layer": layer["layer_id"], "_layer_name": layer["layer_name"]})
        return results

    def get_quantum_attacks(self) -> list[dict[str, Any]]:
        """Return all attacks that leverage Shor's or Grover's quantum algorithms."""
        quantum_keywords = ("shor", "grover", "crqc", "quantum computer", "shor's")
        results: list[dict[str, Any]] = []
        for layer in self._data.values():
            for attack in layer["attacks"]:
                combined = (attack["tool"] + " " + attack["description"]).lower()
                if any(kw in combined for kw in quantum_keywords):
                    results.append({**attack, "_layer": layer["layer_id"], "_layer_name": layer["layer_name"]})
        return results

    def get_by_tool(self, tool_name: str) -> list[dict[str, Any]]:
        """Return all attacks using a specific tool (case-insensitive partial match)."""
        needle = tool_name.lower()
        results: list[dict[str, Any]] = []
        for layer in self._data.values():
            for attack in layer["attacks"]:
                if needle in attack["tool"].lower():
                    results.append({**attack, "_layer": layer["layer_id"], "_layer_name": layer["layer_name"]})
        return results

    def count_by_layer(self) -> dict[str, int]:
        """Return {layer_id: attack_count} for all layers."""
        return {
            lid: len(ldata["attacks"])
            for lid, ldata in sorted(self._data.items())
        }

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def simulate_attack(self, layer_id: str, attack_name: str) -> str:
        """
        Run a simulated attack timeline for a specific attack.
        Returns a multi-line string with a full narrative timeline.
        """
        layer = self.get_layer_attacks(layer_id)
        if layer is None:
            return f"[ERROR] Layer {layer_id} not found."

        attack: dict[str, Any] | None = None
        for a in layer["attacks"]:
            if attack_name.lower() in a["name"].lower():
                attack = a
                break
        if attack is None:
            return f"[ERROR] Attack '{attack_name}' not found in layer {layer_id}."

        now = datetime.datetime.now(datetime.timezone.utc)
        start_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        lines = [
            "=" * 72,
            f"  BRUTAL ATTACK SIMULATION — {layer_id} / {layer['layer_name']}",
            "=" * 72,
            f"  Attack        : {attack['name']}",
            f"  CVE           : {attack['cve']}",
            f"  Tool          : {attack['tool']}",
            f"  MITRE         : {attack['technique']}",
            f"  Simulation at : {start_iso}",
            "  Purpose       : EDUCATIONAL / DEFENSIVE SECURITY ONLY",
            "-" * 72,
            "",
            "  [PHASE 1 — RECONNAISSANCE]  T+0:00",
            "  Attacker identifies target system exposing the vulnerable surface.",
            f"  Tool selected : {attack['tool']}",
            "",
            "  [PHASE 2 — INITIAL ACCESS / EXPLOIT]  T+0:05",
        ]
        # Wrap description paragraphs
        for sent in attack["description"].split(". "):
            sent = sent.strip()
            if sent:
                wrapped = textwrap.fill(f"  {sent}.", width=70, subsequent_indent="      ")
                lines.append(wrapped)
        lines += [
            "",
            "  [PHASE 3 — EXPLOITATION SUCCESSFUL]  T+0:30",
            f"  Impact : {attack['impact']}",
            "",
            "  [PHASE 4 — CLASSICAL SYSTEM OUTCOME]",
            f"  Status : {attack['classical_result']}",
            "  The target system using classical cryptography is compromised.",
            "",
            "  [PHASE 5 — PQC-MIGRATED SYSTEM OUTCOME]",
        ]
        pqc_wrapped = textwrap.fill(
            f"  {attack['pqc_result']}",
            width=70,
            subsequent_indent="      ",
        )
        lines.append(pqc_wrapped)
        lines += [
            "",
            "  [PHASE 6 — DETECTION INDICATORS]",
        ]
        for det in attack["detection"].split(";"):
            det = det.strip()
            if det:
                lines.append(f"  → {det}")
        lines += [
            "",
            "  [PHASE 7 — DEFENSIVE COUNTERMEASURES]",
        ]
        for dfc in attack["defense"].split(";"):
            dfc = dfc.strip()
            if dfc:
                lines.append(f"  ✓ {dfc}")
        lines += [
            "",
            "-" * 72,
            "  [SIMULATION COMPLETE]",
            "  All findings are for defensive understanding only.",
            "=" * 72,
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def generate_attack_report(self, layer_id: str) -> str:
        """Generate a full attack report for a layer (all attacks documented)."""
        layer = self.get_layer_attacks(layer_id)
        if layer is None:
            return f"[ERROR] Layer {layer_id} not found."

        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        lines = [
            "=" * 72,
            f"  ATTACK REPORT: {layer['layer_id']} — {layer['layer_name']}",
            f"  Generated: {now}",
            f"  Total Attacks: {len(layer['attacks'])}",
            "=" * 72,
        ]
        for i, attack in enumerate(layer["attacks"], 1):
            lines += [
                "",
                f"  [{i}] {attack['name']}",
                f"      CVE       : {attack['cve']}",
                f"      Tool      : {attack['tool']}",
                f"      MITRE     : {attack['technique']}",
                f"      Impact    : {attack['impact']}",
                f"      Classical : {attack['classical_result']}",
                f"      PQC       : {attack['pqc_result']}",
                "      ─" * 18,
                f"      Desc      : {textwrap.fill(attack['description'], width=64, subsequent_indent=' ' * 18)}",
                f"      Detect    : {attack['detection']}",
                f"      Defense   : {attack['defense']}",
            ]
        lines += ["", "=" * 72]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    lab = BrutalLayerAttacks()

    # ------------------------------------------------------------------
    # 1. Attack count per layer
    # ------------------------------------------------------------------
    print("\n" + "=" * 72)
    print("  QUANTUM SECURITY LAB — BRUTAL ATTACK SIMULATION MODULE")
    print("  All 29 Layers × Real CVEs × Real Tools × MITRE ATT&CK")
    print("  Educational / Defensive Security Only")
    print("=" * 72)

    print("\n[1] ATTACK COUNT PER LAYER")
    print("-" * 40)
    counts = lab.count_by_layer()
    total_attacks = sum(counts.values())
    for lid, cnt in counts.items():
        ldata = lab.get_layer_attacks(lid)
        layer_name = ldata["layer_name"] if ldata else "?"
        bar = "█" * cnt
        print(f"  {lid}  {layer_name:<35}  {cnt:2d}  {bar}")
    print(f"\n  TOTAL: {total_attacks} attacks across {len(counts)} layers")

    # ------------------------------------------------------------------
    # 2. Top 10 most critical attacks
    # ------------------------------------------------------------------
    print("\n\n[2] TOP 10 MOST CRITICAL ATTACKS (classical_result = CRITICAL)")
    print("-" * 72)
    critical = lab.get_critical_attacks()
    for i, attack in enumerate(critical[:10], 1):
        print(f"  {i:2d}. [{attack['_layer']}] {attack['name']}")
        print(f"       CVE: {attack['cve']}  |  Tool: {attack['tool']}")
        print(f"       Classical: {attack['classical_result']}")
        print(f"       PQC:       {attack['pqc_result'][:80]}...")
        print()
    print(f"  (Total CRITICAL attacks: {len(critical)})")

    # ------------------------------------------------------------------
    # 3. Simulate Heartbleed on L04
    # ------------------------------------------------------------------
    print("\n\n[3] FULL ATTACK SIMULATION: L04 / Heartbleed")
    print(lab.simulate_attack("L04", "Heartbleed"))

    # ------------------------------------------------------------------
    # 4. All quantum-specific attacks
    # ------------------------------------------------------------------
    print("\n\n[4] ALL QUANTUM-SPECIFIC ATTACKS (Shor's / Grover's / CRQC)")
    print("-" * 72)
    quantum_attacks = lab.get_quantum_attacks()
    for i, a in enumerate(quantum_attacks, 1):
        print(f"  {i:2d}. [{a['_layer']}] {a['name']}")
        print(f"       Tool: {a['tool']}")
        print(f"       Classical: {a['classical_result']}")
        print(f"       PQC:       {a['pqc_result'][:72]}...")
        print()
    print(f"  Total quantum-specific attacks: {len(quantum_attacks)}")

    # ------------------------------------------------------------------
    # 5. Classical vs PQC outcome comparison table
    # ------------------------------------------------------------------
    print("\n\n[5] CLASSICAL vs PQC OUTCOME COMPARISON — ALL ATTACKS")
    print("-" * 72)
    print(f"  {'Layer':<6} {'Attack':<42} {'Classical':<16} {'PQC Outcome'}")
    print("  " + "-" * 68)
    for lid, ldata in sorted(LAYER_ATTACKS.items()):
        for attack in ldata["attacks"]:
            classical = attack["classical_result"]
            pqc_short = attack["pqc_result"][:36].rstrip() + ("…" if len(attack["pqc_result"]) > 36 else "")
            name_short = attack["name"][:40]
            print(f"  {lid:<6} {name_short:<42} {classical:<16} {pqc_short}")
    print()

    print("=" * 72)
    print("  SIMULATION COMPLETE — All 29 layers covered.")
    print("  Use generate_attack_report(layer_id) for full per-layer detail.")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    main()
