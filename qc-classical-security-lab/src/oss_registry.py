"""
OSS Registry — Classical Security Lab
Maps all 29 security layers to their open-source software stack.

Every entry carries: layer_id, layer_name, software (name, version, repo,
language, license, crypto_algorithm, quantum_vulnerable, cve_count,
last_updated), monitoring_tools.

Classes
-------
OSSRegistry
    get_layer_software(layer_id)      → layer dict
    get_quantum_vulnerable_software() → flat list of vulnerable packages
    get_all_software()                → flat list of all packages
    generate_sbom()                   → CycloneDX 1.4 dict
    get_stats()                       → summary statistics dict
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Registry data — 29 layers
# ---------------------------------------------------------------------------

_REGISTRY: list[dict[str, Any]] = [
    # ------------------------------------------------------------------
    # L01 Physical / Hardware
    # ------------------------------------------------------------------
    {
        "layer_id": "L01",
        "layer_name": "Physical / Hardware",
        "software": [
            {
                "name": "tpm2-tools",
                "version": "5.6",
                "repo": "https://github.com/tpm2-software/tpm2-tools",
                "language": "C",
                "license": "BSD-2-Clause",
                "crypto_algorithm": "PRNG",
                "quantum_vulnerable": False,
                "cve_count": 0,
                "last_updated": "2024-01-15",
            },
            {
                "name": "OpenSSL",
                "version": "3.2",
                "repo": "https://github.com/openssl/openssl",
                "language": "C",
                "license": "Apache-2.0",
                "crypto_algorithm": "RSA/ECDSA/AES",
                "quantum_vulnerable": True,
                "cve_count": 3,
                "last_updated": "2024-01-20",
            },
            {
                "name": "strongSwan",
                "version": "5.9",
                "repo": "https://github.com/strongswan/strongswan",
                "language": "C",
                "license": "GPL-2.0",
                "crypto_algorithm": "RSA/ECDSA",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-12-10",
            },
        ],
        "monitoring_tools": ["Prometheus node_exporter", "Grafana"],
    },
    # ------------------------------------------------------------------
    # L02 Data Link / MACsec
    # ------------------------------------------------------------------
    {
        "layer_id": "L02",
        "layer_name": "Data Link / MACsec",
        "software": [
            {
                "name": "wpa_supplicant",
                "version": "2.10",
                "repo": "https://w1.fi/wpa_supplicant",
                "language": "C",
                "license": "BSD",
                "crypto_algorithm": "AES-128+RSA EAP-TLS",
                "quantum_vulnerable": True,
                "cve_count": 2,
                "last_updated": "2023-11-05",
            },
            {
                "name": "iproute2",
                "version": "6.6",
                "repo": "https://github.com/iproute2/iproute2",
                "language": "C",
                "license": "GPL-2.0",
                "crypto_algorithm": "MACsec AES-128",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-12-01",
            },
            {
                "name": "hostapd",
                "version": "2.10",
                "repo": "https://w1.fi/hostapd",
                "language": "C",
                "license": "BSD",
                "crypto_algorithm": "WPA3/SAE",
                "quantum_vulnerable": False,
                "cve_count": 1,
                "last_updated": "2023-11-05",
            },
        ],
        "monitoring_tools": ["tcpdump", "Wireshark"],
    },
    # ------------------------------------------------------------------
    # L03 Network / IPsec
    # ------------------------------------------------------------------
    {
        "layer_id": "L03",
        "layer_name": "Network / IPsec",
        "software": [
            {
                "name": "strongSwan",
                "version": "5.9",
                "repo": "https://github.com/strongswan/strongswan",
                "language": "C",
                "license": "GPL-2.0",
                "crypto_algorithm": "IKEv2+DH-2048+RSA",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-12-10",
            },
            {
                "name": "Libreswan",
                "version": "4.12",
                "repo": "https://github.com/libreswan/libreswan",
                "language": "C",
                "license": "GPL-2.0",
                "crypto_algorithm": "IKEv2+DH+RSA",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-11-20",
            },
            {
                "name": "WireGuard-tools",
                "version": "1.0",
                "repo": "https://git.zx2c4.com/wireguard-tools",
                "language": "C",
                "license": "GPL-2.0",
                "crypto_algorithm": "Curve25519+ChaCha20",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2022-06-15",
            },
        ],
        "monitoring_tools": ["Prometheus", "Grafana", "Suricata"],
    },
    # ------------------------------------------------------------------
    # L04 TLS Transport
    # ------------------------------------------------------------------
    {
        "layer_id": "L04",
        "layer_name": "TLS Transport",
        "software": [
            {
                "name": "OpenSSL",
                "version": "3.2",
                "repo": "https://github.com/openssl/openssl",
                "language": "C",
                "license": "Apache-2.0",
                "crypto_algorithm": "ECDHE+ECDSA+AES-GCM",
                "quantum_vulnerable": True,
                "cve_count": 3,
                "last_updated": "2024-01-20",
            },
            {
                "name": "nginx",
                "version": "1.25",
                "repo": "https://github.com/nginx/nginx",
                "language": "C",
                "license": "BSD-2-Clause",
                "crypto_algorithm": "TLS1.3+RSA/ECDSA",
                "quantum_vulnerable": True,
                "cve_count": 2,
                "last_updated": "2023-12-20",
            },
            {
                "name": "Certbot",
                "version": "2.8",
                "repo": "https://github.com/certbot/certbot",
                "language": "Python",
                "license": "Apache-2.0",
                "crypto_algorithm": "RSA-2048+ECDSA",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-12-15",
            },
            {
                "name": "GnuTLS",
                "version": "3.8",
                "repo": "https://gitlab.com/gnutls/gnutls",
                "language": "C",
                "license": "LGPL-2.1",
                "crypto_algorithm": "RSA/ECDSA/TLS",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-11-30",
            },
        ],
        "monitoring_tools": ["testssl.sh", "sslyze", "Prometheus"],
    },
    # ------------------------------------------------------------------
    # L05 Session
    # ------------------------------------------------------------------
    {
        "layer_id": "L05",
        "layer_name": "Session",
        "software": [
            {
                "name": "OpenSSL",
                "version": "3.2",
                "repo": "https://github.com/openssl/openssl",
                "language": "C",
                "license": "Apache-2.0",
                "crypto_algorithm": "TLS session RSA-encrypted",
                "quantum_vulnerable": True,
                "cve_count": 3,
                "last_updated": "2024-01-20",
            },
            {
                "name": "Redis",
                "version": "7.2",
                "repo": "https://github.com/redis/redis",
                "language": "C",
                "license": "BSD-3-Clause",
                "crypto_algorithm": "HMAC session keys",
                "quantum_vulnerable": False,
                "cve_count": 1,
                "last_updated": "2023-11-01",
            },
        ],
        "monitoring_tools": ["Redis Insight", "session analytics"],
    },
    # ------------------------------------------------------------------
    # L06 X.509 PKI
    # ------------------------------------------------------------------
    {
        "layer_id": "L06",
        "layer_name": "X.509 PKI",
        "software": [
            {
                "name": "OpenSSL",
                "version": "3.2",
                "repo": "https://github.com/openssl/openssl",
                "language": "C",
                "license": "Apache-2.0",
                "crypto_algorithm": "RSA-4096 root CA",
                "quantum_vulnerable": True,
                "cve_count": 3,
                "last_updated": "2024-01-20",
            },
            {
                "name": "certstrap",
                "version": "1.3",
                "repo": "https://github.com/square/certstrap",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "RSA-2048/ECDSA",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-08-10",
            },
            {
                "name": "cfssl",
                "version": "1.6",
                "repo": "https://github.com/cloudflare/cfssl",
                "language": "Go",
                "license": "BSD-2-Clause",
                "crypto_algorithm": "RSA-2048/ECDSA",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-09-15",
            },
            {
                "name": "mkcert",
                "version": "1.4",
                "repo": "https://github.com/FiloSottile/mkcert",
                "language": "Go",
                "license": "ISC",
                "crypto_algorithm": "RSA-2048",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-06-01",
            },
            {
                "name": "EJBCA Community",
                "version": "7.11",
                "repo": "https://github.com/Keyfactor/ejbca-ce",
                "language": "Java",
                "license": "LGPL-2.1",
                "crypto_algorithm": "RSA/ECDSA PKI",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-12-05",
            },
            {
                "name": "step-ca",
                "version": "0.26",
                "repo": "https://github.com/smallstep/certificates",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "RSA/ECDSA CA",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2024-01-10",
            },
            {
                "name": "HashiCorp Vault",
                "version": "1.15",
                "repo": "https://github.com/hashicorp/vault",
                "language": "Go",
                "license": "MPL-2.0",
                "crypto_algorithm": "RSA/ECDSA PKI secrets",
                "quantum_vulnerable": True,
                "cve_count": 2,
                "last_updated": "2024-01-05",
            },
        ],
        "monitoring_tools": ["cert-manager", "certbot renewal monitoring"],
    },
    # ------------------------------------------------------------------
    # L07 HTTPS / Application
    # ------------------------------------------------------------------
    {
        "layer_id": "L07",
        "layer_name": "HTTPS / Application",
        "software": [
            {
                "name": "nginx",
                "version": "1.25",
                "repo": "https://github.com/nginx/nginx",
                "language": "C",
                "license": "BSD-2-Clause",
                "crypto_algorithm": "TLS1.3+RSA/ECDSA",
                "quantum_vulnerable": True,
                "cve_count": 2,
                "last_updated": "2023-12-20",
            },
            {
                "name": "Apache httpd",
                "version": "2.4",
                "repo": "https://github.com/apache/httpd",
                "language": "C",
                "license": "Apache-2.0",
                "crypto_algorithm": "TLS/RSA",
                "quantum_vulnerable": True,
                "cve_count": 4,
                "last_updated": "2023-12-18",
            },
            {
                "name": "Caddy",
                "version": "2.7",
                "repo": "https://github.com/caddyserver/caddy",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "TLS/ECDSA auto",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-12-01",
            },
            {
                "name": "HAProxy",
                "version": "2.8",
                "repo": "https://github.com/haproxy/haproxy",
                "language": "C",
                "license": "GPL-2.0",
                "crypto_algorithm": "TLS/RSA",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-10-15",
            },
        ],
        "monitoring_tools": ["Prometheus nginx_exporter", "OWASP ZAP"],
    },
    # ------------------------------------------------------------------
    # L08 JWT / Auth Tokens
    # ------------------------------------------------------------------
    {
        "layer_id": "L08",
        "layer_name": "JWT / Auth Tokens",
        "software": [
            {
                "name": "python-jose",
                "version": "3.3",
                "repo": "https://github.com/mpdavis/python-jose",
                "language": "Python",
                "license": "MIT",
                "crypto_algorithm": "JWT RS256/ES256",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2022-04-01",
            },
            {
                "name": "node-jsonwebtoken",
                "version": "9.0",
                "repo": "https://github.com/auth0/node-jsonwebtoken",
                "language": "JavaScript",
                "license": "MIT",
                "crypto_algorithm": "JWT RS256/HS256",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-07-01",
            },
            {
                "name": "Keycloak",
                "version": "23",
                "repo": "https://github.com/keycloak/keycloak",
                "language": "Java",
                "license": "Apache-2.0",
                "crypto_algorithm": "OIDC RS256/JWT",
                "quantum_vulnerable": True,
                "cve_count": 3,
                "last_updated": "2023-12-15",
            },
            {
                "name": "Dex",
                "version": "2.38",
                "repo": "https://github.com/dexidp/dex",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "OIDC RS256",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-12-10",
            },
        ],
        "monitoring_tools": ["Keycloak metrics", "JWT validation logs"],
    },
    # ------------------------------------------------------------------
    # L09 DNS / DNSSEC
    # ------------------------------------------------------------------
    {
        "layer_id": "L09",
        "layer_name": "DNS / DNSSEC",
        "software": [
            {
                "name": "BIND9",
                "version": "9.18",
                "repo": "https://github.com/isc-projects/bind9",
                "language": "C",
                "license": "MPL-2.0",
                "crypto_algorithm": "DNSSEC RSA/ECDSA",
                "quantum_vulnerable": True,
                "cve_count": 5,
                "last_updated": "2024-01-12",
            },
            {
                "name": "Unbound",
                "version": "1.19",
                "repo": "https://github.com/NLnetLabs/unbound",
                "language": "C",
                "license": "BSD-3-Clause",
                "crypto_algorithm": "DNSSEC validation",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2024-01-08",
            },
            {
                "name": "PowerDNS",
                "version": "4.8",
                "repo": "https://github.com/PowerDNS/pdns",
                "language": "C++",
                "license": "GPL-2.0",
                "crypto_algorithm": "DNSSEC RSA/ECDSA",
                "quantum_vulnerable": True,
                "cve_count": 2,
                "last_updated": "2023-12-20",
            },
            {
                "name": "CoreDNS",
                "version": "1.11",
                "repo": "https://github.com/coredns/coredns",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "DNS/TLS",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-11-15",
            },
        ],
        "monitoring_tools": ["Prometheus DNS metrics", "dnsviz"],
    },
    # ------------------------------------------------------------------
    # L10 SSH
    # ------------------------------------------------------------------
    {
        "layer_id": "L10",
        "layer_name": "SSH",
        "software": [
            {
                "name": "OpenSSH",
                "version": "9.5",
                "repo": "https://github.com/openssh/openssh-portable",
                "language": "C",
                "license": "BSD",
                "crypto_algorithm": "RSA-4096+ECDH (hybrid PQ available in 9.0+)",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-10-04",
            },
            {
                "name": "Paramiko",
                "version": "3.4",
                "repo": "https://github.com/paramiko/paramiko",
                "language": "Python",
                "license": "LGPL-2.1",
                "crypto_algorithm": "RSA/ECDSA SSH",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-12-01",
            },
            {
                "name": "Teleport",
                "version": "14",
                "repo": "https://github.com/gravitational/teleport",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "RSA/ECDSA",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-12-20",
            },
        ],
        "monitoring_tools": ["fail2ban", "SSH audit tool", "Wazuh"],
    },
    # ------------------------------------------------------------------
    # L11 Email S/MIME + PGP
    # ------------------------------------------------------------------
    {
        "layer_id": "L11",
        "layer_name": "Email S/MIME + PGP",
        "software": [
            {
                "name": "GnuPG",
                "version": "2.4",
                "repo": "https://github.com/gpg/gnupg",
                "language": "C",
                "license": "GPL-3.0",
                "crypto_algorithm": "RSA-4096/DSA PGP",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-11-30",
            },
            {
                "name": "Postfix",
                "version": "3.8",
                "repo": "https://github.com/vdukhovni/postfix",
                "language": "C",
                "license": "IPL",
                "crypto_algorithm": "TLS/RSA",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-10-01",
            },
            {
                "name": "Dovecot",
                "version": "2.3",
                "repo": "https://github.com/dovecot/core",
                "language": "C",
                "license": "MIT",
                "crypto_algorithm": "TLS/RSA",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-09-15",
            },
        ],
        "monitoring_tools": ["Postfix log monitoring", "mail security headers"],
    },
    # ------------------------------------------------------------------
    # L12 Code Signing
    # ------------------------------------------------------------------
    {
        "layer_id": "L12",
        "layer_name": "Code Signing",
        "software": [
            {
                "name": "GnuPG",
                "version": "2.4",
                "repo": "https://github.com/gpg/gnupg",
                "language": "C",
                "license": "GPL-3.0",
                "crypto_algorithm": "RSA/DSA commit signing",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-11-30",
            },
            {
                "name": "cosign",
                "version": "2.2",
                "repo": "https://github.com/sigstore/cosign",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "ECDSA OCI signing",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-12-12",
            },
            {
                "name": "in-toto",
                "version": "2.0",
                "repo": "https://github.com/in-toto/in-toto",
                "language": "Python",
                "license": "Apache-2.0",
                "crypto_algorithm": "RSA/ECDSA supply-chain attestation",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-10-20",
            },
            {
                "name": "Rekor",
                "version": "1.3",
                "repo": "https://github.com/sigstore/rekor",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "ECDSA transparency log",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-11-25",
            },
        ],
        "monitoring_tools": ["Sigstore transparency log verification"],
    },
    # ------------------------------------------------------------------
    # L13 VPN
    # ------------------------------------------------------------------
    {
        "layer_id": "L13",
        "layer_name": "VPN",
        "software": [
            {
                "name": "OpenVPN",
                "version": "2.6",
                "repo": "https://github.com/OpenVPN/openvpn",
                "language": "C",
                "license": "GPL-2.0",
                "crypto_algorithm": "TLS+RSA/ECDSA+DH",
                "quantum_vulnerable": True,
                "cve_count": 2,
                "last_updated": "2023-11-18",
            },
            {
                "name": "WireGuard-tools",
                "version": "1.0",
                "repo": "https://git.zx2c4.com/wireguard-tools",
                "language": "C",
                "license": "GPL-2.0",
                "crypto_algorithm": "Curve25519+Noise",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2022-06-15",
            },
            {
                "name": "strongSwan",
                "version": "5.9",
                "repo": "https://github.com/strongswan/strongswan",
                "language": "C",
                "license": "GPL-2.0",
                "crypto_algorithm": "IKEv2+DH",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-12-10",
            },
            {
                "name": "Tailscale",
                "version": "1.56",
                "repo": "https://github.com/tailscale/tailscale",
                "language": "Go",
                "license": "BSD-3-Clause",
                "crypto_algorithm": "WireGuard+Noise protocol",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2024-01-10",
            },
        ],
        "monitoring_tools": ["VPN metrics", "Prometheus"],
    },
    # ------------------------------------------------------------------
    # L14 HSM / Key Management
    # ------------------------------------------------------------------
    {
        "layer_id": "L14",
        "layer_name": "HSM / Key Management",
        "software": [
            {
                "name": "SoftHSM2",
                "version": "2.6",
                "repo": "https://github.com/opendnssec/SoftHSMv2",
                "language": "C++",
                "license": "BSD-2-Clause",
                "crypto_algorithm": "PKCS11+RSA-4096",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-05-01",
            },
            {
                "name": "HashiCorp Vault",
                "version": "1.15",
                "repo": "https://github.com/hashicorp/vault",
                "language": "Go",
                "license": "MPL-2.0",
                "crypto_algorithm": "RSA/AES key management",
                "quantum_vulnerable": True,
                "cve_count": 2,
                "last_updated": "2024-01-05",
            },
            {
                "name": "OpenSC",
                "version": "0.24",
                "repo": "https://github.com/OpenSC/OpenSC",
                "language": "C",
                "license": "LGPL-2.1",
                "crypto_algorithm": "PKCS11/RSA smart-card",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-12-01",
            },
        ],
        "monitoring_tools": ["Vault audit log", "key rotation metrics"],
    },
    # ------------------------------------------------------------------
    # L15 Identity / IAM
    # ------------------------------------------------------------------
    {
        "layer_id": "L15",
        "layer_name": "Identity / IAM",
        "software": [
            {
                "name": "Keycloak",
                "version": "23",
                "repo": "https://github.com/keycloak/keycloak",
                "language": "Java",
                "license": "Apache-2.0",
                "crypto_algorithm": "SAML RSA/OIDC RS256",
                "quantum_vulnerable": True,
                "cve_count": 3,
                "last_updated": "2023-12-15",
            },
            {
                "name": "OpenLDAP",
                "version": "2.6",
                "repo": "https://github.com/openldap/openldap",
                "language": "C",
                "license": "OpenLDAP",
                "crypto_algorithm": "LDAP/TLS",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-09-01",
            },
            {
                "name": "FreeIPA",
                "version": "4.11",
                "repo": "https://github.com/freeipa/freeipa",
                "language": "Python",
                "license": "GPL-3.0",
                "crypto_algorithm": "Kerberos+RSA",
                "quantum_vulnerable": True,
                "cve_count": 2,
                "last_updated": "2023-11-10",
            },
            {
                "name": "Authentik",
                "version": "2024.1",
                "repo": "https://github.com/goauthentik/authentik",
                "language": "Python",
                "license": "MIT",
                "crypto_algorithm": "OIDC RS256",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2024-01-15",
            },
        ],
        "monitoring_tools": ["LDAP monitor", "Keycloak events"],
    },
    # ------------------------------------------------------------------
    # L16 API Security
    # ------------------------------------------------------------------
    {
        "layer_id": "L16",
        "layer_name": "API Security",
        "software": [
            {
                "name": "Kong",
                "version": "3.5",
                "repo": "https://github.com/Kong/kong",
                "language": "Lua",
                "license": "Apache-2.0",
                "crypto_algorithm": "OAuth2+JWT RS256+mTLS",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-12-01",
            },
            {
                "name": "Traefik",
                "version": "3.0",
                "repo": "https://github.com/traefik/traefik",
                "language": "Go",
                "license": "MIT",
                "crypto_algorithm": "TLS+ECDSA",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-12-22",
            },
            {
                "name": "OAuth2-Proxy",
                "version": "7.6",
                "repo": "https://github.com/oauth2-proxy/oauth2-proxy",
                "language": "Go",
                "license": "MIT",
                "crypto_algorithm": "OAuth2/RS256",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-11-20",
            },
        ],
        "monitoring_tools": ["Kong Prometheus plugin", "API gateway metrics"],
    },
    # ------------------------------------------------------------------
    # L17 Database Encryption
    # ------------------------------------------------------------------
    {
        "layer_id": "L17",
        "layer_name": "Database Encryption",
        "software": [
            {
                "name": "PostgreSQL",
                "version": "16",
                "repo": "https://github.com/postgres/postgres",
                "language": "C",
                "license": "PostgreSQL",
                "crypto_algorithm": "TDE+TLS/RSA",
                "quantum_vulnerable": True,
                "cve_count": 2,
                "last_updated": "2023-11-09",
            },
            {
                "name": "pgcrypto",
                "version": "1.3",
                "repo": "https://github.com/postgres/postgres",
                "language": "C",
                "license": "PostgreSQL",
                "crypto_algorithm": "AES-256 TDE",
                "quantum_vulnerable": False,
                "cve_count": 0,
                "last_updated": "2023-11-09",
            },
            {
                "name": "OpenSSL",
                "version": "3.2",
                "repo": "https://github.com/openssl/openssl",
                "language": "C",
                "license": "Apache-2.0",
                "crypto_algorithm": "TLS for DB transport",
                "quantum_vulnerable": True,
                "cve_count": 3,
                "last_updated": "2024-01-20",
            },
        ],
        "monitoring_tools": ["pg_stat_ssl", "slow query log"],
    },
    # ------------------------------------------------------------------
    # L18 Blockchain
    # ------------------------------------------------------------------
    {
        "layer_id": "L18",
        "layer_name": "Blockchain",
        "software": [
            {
                "name": "Bitcoin Core",
                "version": "26.0",
                "repo": "https://github.com/bitcoin/bitcoin",
                "language": "C++",
                "license": "MIT",
                "crypto_algorithm": "ECDSA secp256k1",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-12-06",
            },
            {
                "name": "go-ethereum",
                "version": "1.13",
                "repo": "https://github.com/ethereum/go-ethereum",
                "language": "Go",
                "license": "LGPL-3.0",
                "crypto_algorithm": "ECDSA+SHA-256",
                "quantum_vulnerable": True,
                "cve_count": 2,
                "last_updated": "2023-12-05",
            },
            {
                "name": "Hyperledger Fabric",
                "version": "2.5",
                "repo": "https://github.com/hyperledger/fabric",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "ECDSA P-256",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-11-15",
            },
        ],
        "monitoring_tools": ["Blockchain explorer", "node metrics"],
    },
    # ------------------------------------------------------------------
    # L19 Container / Service Mesh
    # ------------------------------------------------------------------
    {
        "layer_id": "L19",
        "layer_name": "Container / Service Mesh",
        "software": [
            {
                "name": "containerd",
                "version": "1.7",
                "repo": "https://github.com/containerd/containerd",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "TLS+ECDSA",
                "quantum_vulnerable": True,
                "cve_count": 2,
                "last_updated": "2023-12-15",
            },
            {
                "name": "Istio",
                "version": "1.20",
                "repo": "https://github.com/istio/istio",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "mTLS ECDSA+SPIFFE",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-11-14",
            },
            {
                "name": "SPIRE",
                "version": "1.8",
                "repo": "https://github.com/spiffe/spire",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "ECDSA SVIDs",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-12-01",
            },
            {
                "name": "cert-manager",
                "version": "1.13",
                "repo": "https://github.com/cert-manager/cert-manager",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "RSA/ECDSA cert automation",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-12-01",
            },
        ],
        "monitoring_tools": ["Istio telemetry", "SPIRE metrics"],
    },
    # ------------------------------------------------------------------
    # L20 IoT / Embedded
    # ------------------------------------------------------------------
    {
        "layer_id": "L20",
        "layer_name": "IoT / Embedded",
        "software": [
            {
                "name": "Mosquitto",
                "version": "2.0",
                "repo": "https://github.com/eclipse/mosquitto",
                "language": "C",
                "license": "EPL-2.0",
                "crypto_algorithm": "TLS+RSA MQTT broker",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-09-05",
            },
            {
                "name": "mbedTLS",
                "version": "3.5",
                "repo": "https://github.com/Mbed-TLS/mbedtls",
                "language": "C",
                "license": "Apache-2.0",
                "crypto_algorithm": "ECC+RSA+DTLS",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-12-21",
            },
            {
                "name": "wolfSSL",
                "version": "5.7",
                "repo": "https://github.com/wolfSSL/wolfssl",
                "language": "C",
                "license": "GPL-2.0",
                "crypto_algorithm": "ECC/RSA IoT TLS",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2024-01-12",
            },
        ],
        "monitoring_tools": ["MQTT metrics", "IoT device health"],
    },
    # ------------------------------------------------------------------
    # L21 Mobile
    # ------------------------------------------------------------------
    {
        "layer_id": "L21",
        "layer_name": "Mobile",
        "software": [
            {
                "name": "OkHttp",
                "version": "4.12",
                "repo": "https://github.com/square/okhttp",
                "language": "Kotlin",
                "license": "Apache-2.0",
                "crypto_algorithm": "TLS+cert pinning+ECDSA",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-12-14",
            },
            {
                "name": "TrustKit-Android",
                "version": "2.0",
                "repo": "https://github.com/datatheorem/TrustKit-Android",
                "language": "Java",
                "license": "MIT",
                "crypto_algorithm": "cert pinning ECDSA",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2022-11-01",
            },
        ],
        "monitoring_tools": ["Certificate pinning failures", "TLS version metrics"],
    },
    # ------------------------------------------------------------------
    # L22 Firmware / Secure Boot
    # ------------------------------------------------------------------
    {
        "layer_id": "L22",
        "layer_name": "Firmware / Secure Boot",
        "software": [
            {
                "name": "UEFI OVMF (edk2)",
                "version": "202311",
                "repo": "https://github.com/tianocore/edk2",
                "language": "C",
                "license": "BSD-2-Clause",
                "crypto_algorithm": "RSA-2048 secure boot",
                "quantum_vulnerable": True,
                "cve_count": 2,
                "last_updated": "2023-11-10",
            },
            {
                "name": "Keylime",
                "version": "7.6",
                "repo": "https://github.com/keylime/keylime",
                "language": "Python",
                "license": "Apache-2.0",
                "crypto_algorithm": "TPM+RSA attestation",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-12-01",
            },
            {
                "name": "fwupd",
                "version": "1.9",
                "repo": "https://github.com/fwupd/fwupd",
                "language": "C",
                "license": "LGPL-2.1",
                "crypto_algorithm": "RSA firmware signing",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-12-20",
            },
        ],
        "monitoring_tools": ["TPM attestation status", "firmware version tracking"],
    },
    # ------------------------------------------------------------------
    # L23 DevSecOps / CI-CD
    # ------------------------------------------------------------------
    {
        "layer_id": "L23",
        "layer_name": "DevSecOps / CI-CD",
        "software": [
            {
                "name": "GnuPG",
                "version": "2.4",
                "repo": "https://github.com/gpg/gnupg",
                "language": "C",
                "license": "GPL-3.0",
                "crypto_algorithm": "Git commit signing RSA/ECDSA",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-11-30",
            },
            {
                "name": "HashiCorp Vault",
                "version": "1.15",
                "repo": "https://github.com/hashicorp/vault",
                "language": "Go",
                "license": "MPL-2.0",
                "crypto_algorithm": "Secrets RSA wrap",
                "quantum_vulnerable": True,
                "cve_count": 2,
                "last_updated": "2024-01-05",
            },
            {
                "name": "Trivy",
                "version": "0.48",
                "repo": "https://github.com/aquasecurity/trivy",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "SBOM/vuln scan (no crypto)",
                "quantum_vulnerable": False,
                "cve_count": 0,
                "last_updated": "2024-01-18",
            },
            {
                "name": "Syft",
                "version": "1.0",
                "repo": "https://github.com/anchore/syft",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "SBOM generation (no crypto)",
                "quantum_vulnerable": False,
                "cve_count": 0,
                "last_updated": "2024-01-10",
            },
        ],
        "monitoring_tools": ["Trivy scan results", "secrets detection alerts"],
    },
    # ------------------------------------------------------------------
    # L24 SIEM / Logging
    # ------------------------------------------------------------------
    {
        "layer_id": "L24",
        "layer_name": "SIEM / Logging",
        "software": [
            {
                "name": "Wazuh",
                "version": "4.7",
                "repo": "https://github.com/wazuh/wazuh",
                "language": "C/Python",
                "license": "GPL-2.0",
                "crypto_algorithm": "TLS agent auth ECDSA",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-12-20",
            },
            {
                "name": "Elasticsearch",
                "version": "8.11",
                "repo": "https://github.com/elastic/elasticsearch",
                "language": "Java",
                "license": "SSPL",
                "crypto_algorithm": "TLS/RSA cluster comms",
                "quantum_vulnerable": True,
                "cve_count": 2,
                "last_updated": "2023-12-14",
            },
            {
                "name": "Fluent Bit",
                "version": "3.0",
                "repo": "https://github.com/fluent/fluent-bit",
                "language": "C",
                "license": "Apache-2.0",
                "crypto_algorithm": "TLS/RSA log shipping",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2024-01-10",
            },
            {
                "name": "Vector",
                "version": "0.34",
                "repo": "https://github.com/vectordotdev/vector",
                "language": "Rust",
                "license": "MPL-2.0",
                "crypto_algorithm": "TLS/RSA log pipeline",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2024-01-15",
            },
        ],
        "monitoring_tools": ["SIEM itself is the monitor"],
    },
    # ------------------------------------------------------------------
    # L25 Zero Trust / SPIFFE
    # ------------------------------------------------------------------
    {
        "layer_id": "L25",
        "layer_name": "Zero Trust / SPIFFE",
        "software": [
            {
                "name": "SPIRE",
                "version": "1.8",
                "repo": "https://github.com/spiffe/spire",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "ECDSA SVIDs",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-12-01",
            },
            {
                "name": "Pomerium",
                "version": "0.25",
                "repo": "https://github.com/pomerium/pomerium",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "OIDC RS256+mTLS",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-12-20",
            },
            {
                "name": "Cilium",
                "version": "1.15",
                "repo": "https://github.com/cilium/cilium",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "mTLS+ECDSA eBPF policy",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2024-01-12",
            },
        ],
        "monitoring_tools": ["SPIRE health", "identity metrics"],
    },
    # ------------------------------------------------------------------
    # L26 Key Management / KMS
    # ------------------------------------------------------------------
    {
        "layer_id": "L26",
        "layer_name": "Key Management / KMS",
        "software": [
            {
                "name": "HashiCorp Vault",
                "version": "1.15",
                "repo": "https://github.com/hashicorp/vault",
                "language": "Go",
                "license": "MPL-2.0",
                "crypto_algorithm": "RSA-OAEP key wrap",
                "quantum_vulnerable": True,
                "cve_count": 2,
                "last_updated": "2024-01-05",
            },
            {
                "name": "Sealed Secrets",
                "version": "0.25",
                "repo": "https://github.com/bitnami-labs/sealed-secrets",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "RSA-4096 k8s secret encryption",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2024-01-08",
            },
            {
                "name": "SOPS",
                "version": "3.8",
                "repo": "https://github.com/getsops/sops",
                "language": "Go",
                "license": "MPL-2.0",
                "crypto_algorithm": "RSA/AES secret encryption",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-12-01",
            },
        ],
        "monitoring_tools": ["Vault metrics", "key rotation events"],
    },
    # ------------------------------------------------------------------
    # L27 Compliance
    # ------------------------------------------------------------------
    {
        "layer_id": "L27",
        "layer_name": "Compliance",
        "software": [
            {
                "name": "OpenSCAP",
                "version": "1.3",
                "repo": "https://github.com/OpenSCAP/openscap",
                "language": "C",
                "license": "LGPL-2.1",
                "crypto_algorithm": "FIPS 140-2 scanning",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-10-15",
            },
            {
                "name": "Inspec",
                "version": "5.22",
                "repo": "https://github.com/inspec/inspec",
                "language": "Ruby",
                "license": "Apache-2.0",
                "crypto_algorithm": "compliance checks (no crypto primitives)",
                "quantum_vulnerable": False,
                "cve_count": 0,
                "last_updated": "2023-12-01",
            },
            {
                "name": "Falco",
                "version": "0.37",
                "repo": "https://github.com/falcosecurity/falco",
                "language": "C++",
                "license": "Apache-2.0",
                "crypto_algorithm": "runtime security (no crypto primitives)",
                "quantum_vulnerable": False,
                "cve_count": 0,
                "last_updated": "2024-01-10",
            },
        ],
        "monitoring_tools": ["Compliance scan results", "policy violations"],
    },
    # ------------------------------------------------------------------
    # L28 Audit / Non-Repudiation
    # ------------------------------------------------------------------
    {
        "layer_id": "L28",
        "layer_name": "Audit / Non-Repudiation",
        "software": [
            {
                "name": "EJBCA Community",
                "version": "7.11",
                "repo": "https://github.com/Keyfactor/ejbca-ce",
                "language": "Java",
                "license": "LGPL-2.1",
                "crypto_algorithm": "RSA-2048 RFC 3161 timestamping",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2023-12-05",
            },
            {
                "name": "OpenTimestamps",
                "version": "0.7",
                "repo": "https://github.com/opentimestamps/opentimestamps-client",
                "language": "Python",
                "license": "LGPL-3.0",
                "crypto_algorithm": "SHA-256 blockchain anchoring",
                "quantum_vulnerable": False,
                "cve_count": 0,
                "last_updated": "2023-05-01",
            },
        ],
        "monitoring_tools": ["Timestamp validation", "audit trail completeness"],
    },
    # ------------------------------------------------------------------
    # L29 AI / ML Security
    # ------------------------------------------------------------------
    {
        "layer_id": "L29",
        "layer_name": "AI / ML Security",
        "software": [
            {
                "name": "cosign",
                "version": "2.2",
                "repo": "https://github.com/sigstore/cosign",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "ECDSA model/container signing",
                "quantum_vulnerable": True,
                "cve_count": 0,
                "last_updated": "2023-12-12",
            },
            {
                "name": "Trivy",
                "version": "0.48",
                "repo": "https://github.com/aquasecurity/trivy",
                "language": "Go",
                "license": "Apache-2.0",
                "crypto_algorithm": "container scanning (no crypto primitives)",
                "quantum_vulnerable": False,
                "cve_count": 0,
                "last_updated": "2024-01-18",
            },
            {
                "name": "ONNX Runtime",
                "version": "1.17",
                "repo": "https://github.com/microsoft/onnxruntime",
                "language": "C++",
                "license": "MIT",
                "crypto_algorithm": "model serving TLS/ECDSA",
                "quantum_vulnerable": True,
                "cve_count": 1,
                "last_updated": "2024-01-10",
            },
            {
                "name": "MLflow",
                "version": "2.9",
                "repo": "https://github.com/mlflow/mlflow",
                "language": "Python",
                "license": "Apache-2.0",
                "crypto_algorithm": "JWT RS256 API",
                "quantum_vulnerable": True,
                "cve_count": 2,
                "last_updated": "2023-12-20",
            },
        ],
        "monitoring_tools": ["Model drift detection", "API anomalies"],
    },
]


# ---------------------------------------------------------------------------
# OSSRegistry class
# ---------------------------------------------------------------------------

class OSSRegistry:
    """Read-only registry of all OSS packages across the 29 security layers."""

    def __init__(self) -> None:
        self._layers: list[dict[str, Any]] = _REGISTRY
        # Build a fast id → layer map
        self._id_map: dict[str, dict[str, Any]] = {
            layer["layer_id"]: layer for layer in self._layers
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_layer_software(self, layer_id: str) -> dict[str, Any] | None:
        """Return the full layer entry (including software list) for *layer_id*.

        Returns None if the layer_id is not found.
        """
        return self._id_map.get(layer_id.upper())

    def get_quantum_vulnerable_software(self) -> list[dict[str, Any]]:
        """Return a flat list of all software entries marked quantum_vulnerable=True.

        Each returned dict is augmented with 'layer_id' and 'layer_name'
        so callers can trace back to the originating layer.
        """
        vulnerable: list[dict[str, Any]] = []
        for layer in self._layers:
            for sw in layer["software"]:
                if sw["quantum_vulnerable"]:
                    entry = dict(sw)
                    entry["layer_id"] = layer["layer_id"]
                    entry["layer_name"] = layer["layer_name"]
                    vulnerable.append(entry)
        return vulnerable

    def get_all_software(self) -> list[dict[str, Any]]:
        """Return a flat list of every software entry across all 29 layers.

        Each entry is augmented with 'layer_id' and 'layer_name'.
        """
        all_sw: list[dict[str, Any]] = []
        for layer in self._layers:
            for sw in layer["software"]:
                entry = dict(sw)
                entry["layer_id"] = layer["layer_id"]
                entry["layer_name"] = layer["layer_name"]
                all_sw.append(entry)
        return all_sw

    def generate_sbom(self) -> dict[str, Any]:
        """Return a CycloneDX 1.4-format SBOM as a Python dict.

        The SBOM contains one component per unique (name, version) tuple.
        Multiple layers that share the same package (e.g. OpenSSL appearing
        in L01, L04, L05, L07, L17) produce a single component with all
        originating layer_ids recorded in the 'properties' list.
        """
        # Deduplicate by (name, version) while collecting all layer refs
        component_map: dict[tuple[str, str], dict[str, Any]] = {}
        for layer in self._layers:
            for sw in layer["software"]:
                key = (sw["name"], sw["version"])
                if key not in component_map:
                    component_map[key] = {
                        "type": "library",
                        "bom-ref": f"{sw['name'].lower().replace(' ', '-')}-{sw['version']}",
                        "name": sw["name"],
                        "version": sw["version"],
                        "purl": (
                            f"pkg:generic/{sw['name'].lower().replace(' ', '-')}@{sw['version']}"
                        ),
                        "licenses": [{"license": {"id": sw["license"]}}],
                        "externalReferences": [
                            {
                                "type": "vcs",
                                "url": sw["repo"],
                            }
                        ],
                        "properties": [
                            {"name": "language", "value": sw["language"]},
                            {
                                "name": "crypto_algorithm",
                                "value": sw["crypto_algorithm"],
                            },
                            {
                                "name": "quantum_vulnerable",
                                "value": str(sw["quantum_vulnerable"]).lower(),
                            },
                            {
                                "name": "cve_count",
                                "value": str(sw["cve_count"]),
                            },
                            {
                                "name": "last_updated",
                                "value": sw["last_updated"],
                            },
                            {
                                "name": "security_layer",
                                "value": layer["layer_id"],
                            },
                        ],
                    }
                else:
                    # Append additional layer reference
                    component_map[key]["properties"].append(
                        {"name": "security_layer", "value": layer["layer_id"]}
                    )

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        return {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "serialNumber": f"urn:uuid:{uuid.uuid4()}",
            "version": 1,
            "metadata": {
                "timestamp": now_iso,
                "tools": [
                    {
                        "vendor": "qc-classical-security-lab",
                        "name": "oss_registry",
                        "version": "1.0.0",
                    }
                ],
                "component": {
                    "type": "application",
                    "name": "qc-classical-security-lab",
                    "version": "1.0.0",
                    "description": (
                        "29-layer classical security stack — "
                        "OSS registry and SBOM for quantum-readiness analysis"
                    ),
                },
            },
            "components": list(component_map.values()),
        }

    def get_stats(self) -> dict[str, Any]:
        """Return summary statistics over the full OSS registry."""
        all_sw = self.get_all_software()

        total_packages = len(all_sw)
        vulnerable_count = sum(1 for sw in all_sw if sw["quantum_vulnerable"])
        total_cves = sum(sw["cve_count"] for sw in all_sw)

        # Count by language
        by_language: dict[str, int] = {}
        for sw in all_sw:
            lang = sw["language"]
            by_language[lang] = by_language.get(lang, 0) + 1

        # Count by license
        by_license: dict[str, int] = {}
        for sw in all_sw:
            lic = sw["license"]
            by_license[lic] = by_license.get(lic, 0) + 1

        # Unique packages (de-duplicated by name+version)
        unique_packages = len({(sw["name"], sw["version"]) for sw in all_sw})

        # Layers with any vulnerable software
        vulnerable_layers = sorted(
            {sw["layer_id"] for sw in all_sw if sw["quantum_vulnerable"]}
        )

        return {
            "total_package_instances": total_packages,
            "unique_packages": unique_packages,
            "quantum_vulnerable_instances": vulnerable_count,
            "quantum_safe_instances": total_packages - vulnerable_count,
            "vulnerability_percentage": round(
                vulnerable_count / total_packages * 100, 1
            ),
            "total_known_cves": total_cves,
            "layers_with_vulnerable_software": len(vulnerable_layers),
            "vulnerable_layer_ids": vulnerable_layers,
            "by_language": by_language,
            "by_license": by_license,
        }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    registry = OSSRegistry()

    print("=" * 70)
    print("OSS REGISTRY — Classical Security Lab (29 layers)")
    print("=" * 70)

    stats = registry.get_stats()
    print("\n--- Registry Stats ---")
    print(f"  Total package instances : {stats['total_package_instances']}")
    print(f"  Unique packages         : {stats['unique_packages']}")
    print(f"  Quantum-vulnerable      : {stats['quantum_vulnerable_instances']}"
          f" ({stats['vulnerability_percentage']}%)")
    print(f"  Quantum-safe            : {stats['quantum_safe_instances']}")
    print(f"  Total known CVEs        : {stats['total_known_cves']}")
    print(f"  Vulnerable layers       : {stats['layers_with_vulnerable_software']}/29")

    print("\n--- By Language ---")
    for lang, count in sorted(stats["by_language"].items(), key=lambda x: -x[1]):
        print(f"  {lang:<20} {count:>3}")

    print("\n--- By License ---")
    for lic, count in sorted(stats["by_license"].items(), key=lambda x: -x[1]):
        print(f"  {lic:<25} {count:>3}")

    print("\n--- Sample: L18 Blockchain (highest risk) ---")
    layer = registry.get_layer_software("L18")
    if layer:
        for sw in layer["software"]:
            vuln_flag = "VULNERABLE" if sw["quantum_vulnerable"] else "safe"
            print(
                f"  {sw['name']:25} v{sw['version']:<8}"
                f" {sw['crypto_algorithm']:<35} [{vuln_flag}]"
            )

    print("\n--- SBOM Serial Number ---")
    sbom = registry.generate_sbom()
    print(f"  {sbom['serialNumber']}")
    print(f"  Components: {len(sbom['components'])}")
    print()


if __name__ == "__main__":
    main()
