"""
Classical TLS 1.3 Handshake Simulation
Demonstrates ECDHE key exchange, ECDSA authentication, AES-256-GCM symmetric encryption.
Shows protocol steps with timing benchmarks and quantum threat analysis.

TLS 1.3 handshake flow:
  1. ClientHello  (supported cipher suites, client random, key_share)
  2. ServerHello  (selected cipher suite, server random, key_share)
  3. {EncryptedExtensions, Certificate, CertificateVerify, Finished}
  4. {Finished} <- Client
  5. Application data with AES-256-GCM
"""

import os
import time
import struct
import hashlib
import hmac as hmac_module
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import ECDH
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF, HKDFExpand


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    """HKDF-Extract per RFC 5869."""
    if salt is None:
        salt = bytes(32)
    return hmac_module.new(salt, ikm, hashlib.sha256).digest()


def hkdf_expand_label(secret: bytes, label: str, context: bytes, length: int) -> bytes:
    """TLS 1.3 HKDF-Expand-Label."""
    tls_label = b"tls13 " + label.encode()
    hkdf_label = (
        struct.pack(">H", length)
        + struct.pack("B", len(tls_label))
        + tls_label
        + struct.pack("B", len(context))
        + context
    )
    return HKDFExpand(
        algorithm=hashes.SHA256(),
        length=length,
        info=hkdf_label,
        backend=default_backend(),
    ).derive(secret)


def derive_traffic_keys(shared_secret: bytes, client_random: bytes, server_random: bytes):
    """Derive TLS 1.3 traffic keys from ECDHE shared secret."""
    # Early secret
    early_secret = hkdf_extract(None, b"\x00" * 32)

    # Handshake secret
    derived_secret = hkdf_expand_label(early_secret, "derived", b"", 32)
    handshake_secret = hkdf_extract(derived_secret, shared_secret)

    # Master secret
    derived_secret2 = hkdf_expand_label(handshake_secret, "derived", b"", 32)
    master_secret = hkdf_extract(derived_secret2, b"\x00" * 32)

    transcript_hash = hashlib.sha256(client_random + server_random).digest()

    client_traffic = hkdf_expand_label(master_secret, "c ap traffic", transcript_hash, 32)
    server_traffic = hkdf_expand_label(master_secret, "s ap traffic", transcript_hash, 32)

    # AES-256-GCM needs 32-byte key + 12-byte IV
    client_key = hkdf_expand_label(client_traffic, "key", b"", 32)
    client_iv  = hkdf_expand_label(client_traffic, "iv",  b"", 12)
    server_key = hkdf_expand_label(server_traffic, "key", b"", 32)
    server_iv  = hkdf_expand_label(server_traffic, "iv",  b"", 12)

    return client_key, client_iv, server_key, server_iv


# ---------------------------------------------------------------------------
# Step-by-step TLS 1.3 simulation
# ---------------------------------------------------------------------------

def step_client_hello():
    print("\n  [Step 1] ClientHello")
    client_random = os.urandom(32)

    # Client generates ephemeral ECDHE key pair (key_share extension)
    t0 = time.perf_counter()
    client_ecdhe_priv = ec.generate_private_key(ec.SECP256R1(), default_backend())
    keygen_ms = (time.perf_counter() - t0) * 1000

    client_pub_bytes = client_ecdhe_priv.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    print(f"    client_random        : {client_random.hex()[:32]}...")
    print(f"    key_share curve      : secp256r1 (P-256)")
    print(f"    key_share pubkey     : {client_pub_bytes.hex()[:32]}... ({len(client_pub_bytes)} bytes)")
    print(f"    supported_groups     : [secp256r1, x25519, secp384r1]")
    print(f"    cipher_suites        : [TLS_AES_256_GCM_SHA384, TLS_AES_128_GCM_SHA256]")
    print(f"    ECDHE keygen time    : {keygen_ms:.3f} ms")
    return client_random, client_ecdhe_priv


def step_server_hello(client_ecdhe_priv):
    print("\n  [Step 2] ServerHello + Certificate + CertificateVerify")
    server_random = os.urandom(32)

    # Server generates ephemeral ECDHE key pair
    t0 = time.perf_counter()
    server_ecdhe_priv = ec.generate_private_key(ec.SECP256R1(), default_backend())
    server_auth_priv  = ec.generate_private_key(ec.SECP256R1(), default_backend())
    keygen_ms = (time.perf_counter() - t0) * 1000

    server_pub_bytes = server_ecdhe_priv.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    print(f"    server_random        : {server_random.hex()[:32]}...")
    print(f"    selected cipher      : TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384")
    print(f"    key_share pubkey     : {server_pub_bytes.hex()[:32]}... ({len(server_pub_bytes)} bytes)")
    print(f"    ECDHE keygen time    : {keygen_ms:.3f} ms")
    return server_random, server_ecdhe_priv, server_auth_priv


def step_ecdhe_key_exchange(client_ecdhe_priv, server_ecdhe_priv):
    print("\n  [Step 3] ECDHE Key Exchange — Shared Secret Derivation")

    t0 = time.perf_counter()
    # Client side
    client_shared = client_ecdhe_priv.exchange(ECDH(), server_ecdhe_priv.public_key())
    # Server side (same result)
    server_shared = server_ecdhe_priv.exchange(ECDH(), client_ecdhe_priv.public_key())
    exchange_ms = (time.perf_counter() - t0) * 1000

    assert client_shared == server_shared, "ECDHE key agreement failed!"

    print(f"    ECDHE group          : P-256 (secp256r1)")
    print(f"    Shared secret        : {client_shared.hex()[:32]}... ({len(client_shared)} bytes)")
    print(f"    Client == Server     : MATCH")
    print(f"    Exchange time        : {exchange_ms:.3f} ms")
    print()
    print(f"    [QUANTUM THREAT] CRITICAL — Shor's solves ECDH discrete log")
    print(f"    Qubits needed        : ~2,330 logical qubits for P-256")
    print(f"    Migration target     : ML-KEM-768 (Kyber) — FIPS 203")

    return client_shared


def step_server_authenticate(server_auth_priv, handshake_bytes: bytes):
    print("\n  [Step 4] Server Authentication (CertificateVerify — ECDSA)")

    t0 = time.perf_counter()
    signature = server_auth_priv.sign(handshake_bytes, ec.ECDSA(hashes.SHA256()))
    sign_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    server_auth_priv.public_key().verify(signature, handshake_bytes, ec.ECDSA(hashes.SHA256()))
    verify_ms = (time.perf_counter() - t0) * 1000

    print(f"    Auth algorithm       : ECDSA with SHA-256")
    print(f"    Signature size       : {len(signature)} bytes")
    print(f"    Sign time            : {sign_ms:.3f} ms")
    print(f"    Verify time          : {verify_ms:.3f} ms")
    print(f"    Verification         : PASS")
    print()
    print(f"    [QUANTUM THREAT] CRITICAL — Shor's breaks ECDSA P-256")
    print(f"    Migration target     : ML-DSA-65 (Dilithium) — FIPS 204")

    return signature


def step_derive_keys(shared_secret, client_random, server_random):
    print("\n  [Step 5] Traffic Key Derivation (HKDF-SHA256)")

    t0 = time.perf_counter()
    c_key, c_iv, s_key, s_iv = derive_traffic_keys(shared_secret, client_random, server_random)
    kdf_ms = (time.perf_counter() - t0) * 1000

    print(f"    KDF                  : HKDF-SHA256 (TLS 1.3 key schedule)")
    print(f"    Client write key     : {c_key.hex()[:32]}... (32 bytes, AES-256)")
    print(f"    Client write IV      : {c_iv.hex()} (12 bytes, GCM nonce base)")
    print(f"    Server write key     : {s_key.hex()[:32]}... (32 bytes, AES-256)")
    print(f"    Server write IV      : {s_iv.hex()} (12 bytes, GCM nonce base)")
    print(f"    KDF time             : {kdf_ms:.3f} ms")
    print()
    print(f"    [QUANTUM THREAT] LOW — AES-256-GCM resists Grover's")
    print(f"    Grover's effect      : 256-bit -> 128-bit effective security")
    print(f"    AES-256 post-quantum : NIST recommends keep AES-256, not AES-128")

    return c_key, c_iv, s_key, s_iv


def step_application_data(server_key, server_iv, client_key, client_iv):
    print("\n  [Step 6] Application Data — AES-256-GCM Encryption")

    plaintext = b"GET /api/v1/account/balance HTTP/1.1\r\nHost: quantum-bank.example\r\n\r\n"
    additional_data = b"TLS13 record header"

    server_gcm = AESGCM(server_key)
    client_gcm = AESGCM(client_key)

    # Server encrypts response (server write key)
    t0 = time.perf_counter()
    nonce = server_iv[:12]
    ciphertext = server_gcm.encrypt(nonce, plaintext, additional_data)
    enc_ms = (time.perf_counter() - t0) * 1000

    # Client decrypts using the same server_write_key (TLS: both parties derive same key)
    # In this simulation server_key == client-side server_read_key (derived identically)
    t0 = time.perf_counter()
    recovered = server_gcm.decrypt(nonce, ciphertext, additional_data)
    dec_ms = (time.perf_counter() - t0) * 1000

    print(f"    Cipher               : AES-256-GCM")
    print(f"    Plaintext size       : {len(plaintext)} bytes")
    print(f"    Ciphertext size      : {len(ciphertext)} bytes (+ 16-byte GHASH tag)")
    print(f"    AAD                  : '{additional_data.decode()}'")
    print(f"    Encrypt time         : {enc_ms:.3f} ms")
    print(f"    Decrypt time         : {dec_ms:.3f} ms")
    print(f"    Integrity check      : PASS (GHASH authentication tag)")
    print(f"    Recovered plaintext  : {recovered[:40]}...")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print()
    print("##############################################################")
    print("#  CLASSICAL TLS 1.3 HANDSHAKE SIMULATION                   #")
    print("#  ECDHE + ECDSA + AES-256-GCM + HKDF-SHA256                #")
    print("##############################################################")

    t_total = time.perf_counter()

    client_random, client_ecdhe_priv = step_client_hello()
    server_random, server_ecdhe_priv, server_auth_priv = step_server_hello(client_ecdhe_priv)

    shared_secret = step_ecdhe_key_exchange(client_ecdhe_priv, server_ecdhe_priv)

    handshake_transcript = client_random + server_random + shared_secret
    step_server_authenticate(server_auth_priv, handshake_transcript)

    c_key, c_iv, s_key, s_iv = step_derive_keys(shared_secret, client_random, server_random)
    step_application_data(s_key, s_iv, c_key, c_iv)

    total_ms = (time.perf_counter() - t_total) * 1000

    print("\n" + "=" * 60)
    print("TLS 1.3 HANDSHAKE SUMMARY")
    print("=" * 60)
    print(f"  Total handshake time   : {total_ms:.2f} ms")
    print()
    print("  COMPONENT              CLASSICAL STATUS  QUANTUM STATUS")
    print("  ECDHE (P-256)          Secure (~2^128)   CRITICAL (Shor's)")
    print("  ECDSA auth (P-256)     Secure (~2^128)   CRITICAL (Shor's)")
    print("  AES-256-GCM            Secure (128-bit)  LOW  (Grover halves)")
    print("  HKDF-SHA256            Secure            LOW  (minor impact)")
    print()
    print("  POST-QUANTUM MIGRATION:")
    print("    ECDHE  → ML-KEM-768 (Kyber)   — FIPS 203")
    print("    ECDSA  → ML-DSA-65 (Dilithium) — FIPS 204")
    print("    AES    → Keep AES-256-GCM")
    print("    HKDF   → Keep SHA-256 (or upgrade to SHA-384)")
    print()


if __name__ == "__main__":
    main()
