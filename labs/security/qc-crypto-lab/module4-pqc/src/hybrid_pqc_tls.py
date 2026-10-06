"""
CUSTOMER DEMO PITCH — Hybrid PQC TLS 1.3 Handshake
====================================================
During the transition period (now through ~2030), we CANNOT simply swap RSA/ECDH
for ML-KEM.  Reasons:
  1. If ML-KEM has an undiscovered flaw, we want classical crypto as backup.
  2. Hardware Security Modules, PKI infrastructure, and TLS stacks need time to update.
  3. IETF RFC 8446 (TLS 1.3) requires explicit support for new KEMs.

Hybrid KEM (IETF draft-ietf-tls-hybrid-design):
  Combine X25519 (classical ECDH) + ML-KEM-768 (post-quantum) in a single handshake.
  The combined shared secret: ss = HKDF(ss_classical || ss_pqc)

Security argument:
  - If X25519 is broken (Shor), ML-KEM-768 still provides 192-bit PQ security.
  - If ML-KEM-768 is broken (unknown future attack), X25519 still provides 128-bit classical security.
  - An adversary must break BOTH simultaneously to compromise the session.

This demo simulates the hybrid TLS 1.3 handshake using Python's cryptography library
and numpy (no actual X25519/ML-KEM hardware needed — we use random bytes as stand-ins
for shared secrets to demonstrate the key derivation flow).

Audience: TLS engineers, security architects, CISO staff, interview panels.
Runtime: < 2 seconds.
"""

import os
import hashlib
import hmac
import struct
import json


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_sep(title: str = "") -> None:
    w = 68
    if title:
        p = (w - len(title) - 2) // 2
        print("=" * p + f" {title} " + "=" * (w - p - len(title) - 2))
    else:
        print("=" * w)


def hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    """HKDF-Extract (RFC 5869)."""
    if not salt:
        salt = bytes(32)
    return hmac.new(salt, ikm, hashlib.sha256).digest()


def hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
    """HKDF-Expand (RFC 5869)."""
    hash_len = 32   # SHA-256
    n = (length + hash_len - 1) // hash_len
    okm = b""
    t   = b""
    for i in range(1, n + 1):
        t = hmac.new(prk, t + info + bytes([i]), hashlib.sha256).digest()
        okm += t
    return okm[:length]


def hkdf(ikm: bytes, salt: bytes, info: bytes, length: int) -> bytes:
    prk = hkdf_extract(salt, ikm)
    return hkdf_expand(prk, info, length)


# ---------------------------------------------------------------------------
# Simulated KEM operations (stand-ins for real X25519 + ML-KEM)
# ---------------------------------------------------------------------------

class SimulatedX25519:
    """Simulate X25519 ECDH key exchange."""
    KEY_SIZE = 32

    def __init__(self, seed: bytes = None):
        self.private_key = os.urandom(32) if not seed else hashlib.sha256(seed).digest()
        # Public key = hash of private (stand-in for actual Curve25519 scalar multiplication)
        self.public_key  = hashlib.sha256(b"x25519_pub_" + self.private_key).digest()

    def encapsulate(self, peer_public: bytes) -> tuple:
        """Client encapsulates: generates ephemeral, computes shared secret."""
        ephemeral_priv = os.urandom(32)
        ephemeral_pub  = hashlib.sha256(b"x25519_ephem_" + ephemeral_priv).digest()
        # Shared secret = H(ephemeral_priv || peer_public)
        shared_secret  = hashlib.sha256(ephemeral_priv + peer_public).digest()
        return ephemeral_pub, shared_secret

    def decapsulate(self, ephemeral_pub: bytes) -> bytes:
        """Server decapsulates: computes shared secret from ephemeral."""
        return hashlib.sha256(self.private_key[:16] + ephemeral_pub[:16]).digest()


class SimulatedMLKEM768:
    """Simulate ML-KEM-768 key encapsulation."""
    PK_SIZE = 1184
    SK_SIZE = 2400
    CT_SIZE = 1088
    SS_SIZE = 32

    def __init__(self, seed: bytes = None):
        rnd = seed or os.urandom(64)
        self.private_key = hashlib.sha512(b"mlkem_sk_" + rnd).digest()
        self.public_key  = hashlib.sha512(b"mlkem_pk_" + rnd).digest()[:self.PK_SIZE // 16]

    def encapsulate(self, public_key: bytes) -> tuple:
        """Encapsulate: returns (ciphertext, shared_secret)."""
        rand       = os.urandom(32)
        ciphertext = hashlib.sha256(rand + public_key).digest()
        shared_secret = hashlib.sha256(b"mlkem_ss_" + rand + public_key).digest()
        return ciphertext, shared_secret

    def decapsulate(self, ciphertext: bytes) -> bytes:
        """Decapsulate: recover shared_secret from ciphertext."""
        return hashlib.sha256(b"mlkem_ss_" + self.private_key[:8] + ciphertext).digest()


# ---------------------------------------------------------------------------
# Hybrid TLS 1.3 handshake simulation
# ---------------------------------------------------------------------------

def hybrid_tls13_handshake(verbose: bool = True) -> dict:
    """
    Simulate a hybrid TLS 1.3 handshake with X25519 + ML-KEM-768.
    Returns the session keys and transcript for demo purposes.
    """
    steps = []

    # --- Server setup ---
    server_x = SimulatedX25519(seed=b"server_static")
    server_k  = SimulatedMLKEM768(seed=b"server_static_mlkem")

    steps.append(("Server", "KeyGen", {
        "x25519_pub":  server_x.public_key.hex()[:16] + "...",
        "mlkem_pub":   server_k.public_key.hex()[:16] + "...",
    }))

    # --- Client Hello ---
    client_hello = {
        "supported_groups":      ["x25519_mlkem768", "x25519", "secp256r1"],
        "supported_versions":    ["TLS 1.3"],
        "key_share_groups":      ["x25519_mlkem768"],
    }
    steps.append(("Client", "ClientHello", client_hello))

    # --- Server Hello ---
    server_hello = {
        "selected_version": "TLS 1.3",
        "selected_group":   "x25519_mlkem768 (hybrid)",
        "cipher_suite":     "TLS_AES_256_GCM_SHA384",
    }
    steps.append(("Server", "ServerHello", server_hello))

    # --- Key Exchange ---
    # Client generates X25519 ephemeral and encapsulates against server's X25519 pub
    client_x_ephem_pub, ss_x_client = server_x.encapsulate(server_x.public_key)
    # Client generates ML-KEM ciphertext encapsulating server's ML-KEM public key
    mlkem_ct, ss_k_client = server_k.encapsulate(server_k.public_key)

    steps.append(("Client", "KeyShare (ClientHello ext.)", {
        "x25519_ephemeral_pub": client_x_ephem_pub.hex()[:16] + "...",
        "mlkem_ciphertext":     mlkem_ct.hex()[:16] + "...",
    }))

    # --- Server processes ---
    ss_x_server = server_x.decapsulate(client_x_ephem_pub)
    ss_k_server = server_k.decapsulate(mlkem_ct)

    steps.append(("Server", "Decapsulate", {
        "ss_x25519_matches":  ss_x_client == ss_x_server,
        "ss_mlkem_matches":   ss_k_client == ss_k_server,
    }))

    # --- Hybrid key combination ---
    # IETF draft: combined_ss = HKDF(ss_classical || ss_pqc, label)
    combined_ikm     = ss_x_client + ss_k_client
    hybrid_label     = b"hybrid X25519+MLKEM768"
    master_secret    = hkdf(combined_ikm, b"", hybrid_label, 32)

    # TLS 1.3 key derivation
    handshake_secret = hkdf(master_secret, b"", b"tls13 handshake secret", 32)
    client_app_key   = hkdf(handshake_secret, b"", b"tls13 client application traffic secret", 32)
    server_app_key   = hkdf(handshake_secret, b"", b"tls13 server application traffic secret", 32)

    steps.append(("Both", "HKDF Key Derivation", {
        "combined_ikm_size":    f"{len(combined_ikm)} bytes (32 X25519 + 32 ML-KEM)",
        "master_secret":        master_secret.hex()[:32] + "...",
        "client_app_key":       client_app_key.hex()[:16] + "...",
        "server_app_key":       server_app_key.hex()[:16] + "...",
    }))

    return {
        "steps":          steps,
        "ss_x_classical": ss_x_client.hex(),
        "ss_k_pqc":       ss_k_client.hex(),
        "master_secret":  master_secret.hex(),
        "client_app_key": client_app_key.hex(),
        "server_app_key": server_app_key.hex(),
    }


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    print_sep("HYBRID PQC TLS 1.3 HANDSHAKE DEMO")
    print("Purpose: Show X25519 + ML-KEM-768 dual KEM with HKDF combination\n")

    # Run handshake
    result = hybrid_tls13_handshake()

    print_sep("Handshake Transcript")
    for actor, step_name, data in result["steps"]:
        print(f"\n  [{actor}]  {step_name}")
        if isinstance(data, dict):
            for k, v in data.items():
                print(f"    {k}: {v}")
        else:
            print(f"    {data}")

    print()
    print_sep("Shared Secrets")
    print(f"  X25519 shared secret (classical):  {result['ss_x_classical'][:32]}...")
    print(f"  ML-KEM-768 shared secret (PQC):    {result['ss_k_pqc'][:32]}...")
    print(f"  Combined (HKDF):                   {result['master_secret'][:32]}...")
    print(f"  Client AES-256-GCM key:            {result['client_app_key'][:32]}...")
    print(f"  Server AES-256-GCM key:            {result['server_app_key'][:32]}...")

    print()
    print_sep("Key Sizes in Hybrid Handshake")
    items = [
        ("X25519 public key",       32,    "Classical ECDH"),
        ("ML-KEM-768 public key", 1184,    "PQC KEM"),
        ("X25519 ephemeral pub",    32,    "Client's ephemeral"),
        ("ML-KEM-768 ciphertext", 1088,    "PQC encapsulation"),
        ("Combined ClientHello ext.", 1120, "X25519 + ML-KEM (total key_share)"),
        ("Master secret",           32,    "HKDF output"),
        ("Session key (AES-256)",   32,    "128-bit blocks"),
    ]
    max_sz = max(sz for _, sz, _ in items)
    print(f"  {'Item':<35}  {'Bytes':>7}  {'Bar':<20}  Notes")
    print(f"  {'-'*35}  {'-'*7}  {'-'*20}  {'-'*30}")
    for name, sz, note in items:
        bar = "#" * int(sz / max_sz * 20)
        print(f"  {name:<35}  {sz:>7}  {bar:<20}  {note}")

    print()
    print_sep("Security Argument for Hybrid")
    print("""
  Adversary must break BOTH X25519 AND ML-KEM-768 simultaneously to compromise
  the session.  The HKDF combiner ensures neither individual secret helps:

    If ONLY X25519 is broken (by Shor's algorithm):
      Attacker learns ss_classical.
      But master_secret = HKDF(ss_classical || ss_pqc).
      Without ss_pqc, HKDF output is computationally indistinguishable from random.

    If ONLY ML-KEM-768 is broken (hypothetical future attack):
      Attacker learns ss_pqc.
      But master_secret = HKDF(ss_classical || ss_pqc).
      Without ss_classical, HKDF output is computationally indistinguishable from random.

  This is formally proven in the IND-CCA2 security model (Bindel et al. 2019).

  IETF standardisation:
    draft-ietf-tls-hybrid-design (active, 2024)
    x25519_mlkem768 (code point 0x11ec, TLS 1.3 extension)
    Already deployed by Google Chrome (since 2023), Cloudflare, AWS.
""")

    print_sep("Deployment Readiness")
    print("""
  Ready NOW:
    OpenSSL 3.5+:       ML-KEM and hybrid TLS support
    AWS KMS:            ML-KEM hybrid key exchange (2024)
    Cloudflare:         X25519+ML-KEM hybrid default for select endpoints
    Google Chrome:      x25519Kyber768 enabled (2023)

  Needed for full transition:
    Certificate signatures: ML-DSA (replacing ECDSA in X.509 certificates)
    PKI infrastructure: Root CAs issuing ML-DSA certificates
    HSM support: Hardware Security Modules with ML-KEM/ML-DSA firmware
    Timeline: 2028–2030 for full ecosystem migration
""")
    print_sep()


if __name__ == "__main__":
    main()
