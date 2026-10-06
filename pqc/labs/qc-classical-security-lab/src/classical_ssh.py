"""
Classical SSH Protocol Simulation
Demonstrates RSA/ECDSA host key authentication, DH key exchange,
AES-256-CTR bulk cipher, and HMAC-SHA256 MAC.

SSH-2 handshake steps:
  1. Version exchange
  2. Algorithm negotiation (SSH_MSG_KEXINIT)
  3. DH key exchange (SSH_MSG_KEXDH_INIT / REPLY)
  4. New keys (SSH_MSG_NEWKEYS)
  5. User authentication (SSH_MSG_USERAUTH_REQUEST)
  6. Channel open + data transfer

This is a simulation — no actual socket connections.
"""

import os
import time
import hashlib
import hmac as hmac_module
import struct
from cryptography.hazmat.primitives.asymmetric import rsa, ec, dh, padding
from cryptography.hazmat.primitives.asymmetric.ec import ECDH
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


# ---------------------------------------------------------------------------
# Step 1: Version Exchange
# ---------------------------------------------------------------------------

def step_version_exchange():
    print("\n  [Step 1] SSH Version Exchange")
    client_version = "SSH-2.0-OpenSSH_9.4"
    server_version = "SSH-2.0-OpenSSH_9.4"
    print(f"    Client → Server : {client_version}")
    print(f"    Server → Client : {server_version}")
    print(f"    Agreed version  : SSH-2.0")
    return client_version, server_version


# ---------------------------------------------------------------------------
# Step 2: Algorithm Negotiation
# ---------------------------------------------------------------------------

def step_kexinit():
    print("\n  [Step 2] Algorithm Negotiation (SSH_MSG_KEXINIT)")

    client_algos = {
        "kex_algorithms":              "ecdh-sha2-nistp256,diffie-hellman-group14-sha256",
        "server_host_key_algorithms":  "ecdsa-sha2-nistp256,rsa-sha2-256",
        "encryption_c2s":              "aes256-ctr,aes128-ctr,chacha20-poly1305",
        "encryption_s2c":              "aes256-ctr,aes128-ctr,chacha20-poly1305",
        "mac_c2s":                     "hmac-sha2-256,hmac-sha2-512",
        "mac_s2c":                     "hmac-sha2-256,hmac-sha2-512",
        "compression_c2s":             "none,zlib@openssh.com",
        "compression_s2c":             "none,zlib@openssh.com",
    }
    negotiated = {
        "kex_algorithm":     "ecdh-sha2-nistp256",
        "host_key_algo":     "ecdsa-sha2-nistp256",
        "encryption":        "aes256-ctr",
        "mac":               "hmac-sha2-256",
        "compression":       "none",
    }

    for k, v in client_algos.items():
        print(f"    {k:<35} : {v.split(',')[0]}")
    print()
    print("    Negotiated:")
    for k, v in negotiated.items():
        print(f"    {k:<35} : {v}")

    print()
    print("    [QUANTUM THREAT] ecdh-sha2-nistp256 → CRITICAL (Shor's)")
    print("    [QUANTUM THREAT] ecdsa-sha2-nistp256 → CRITICAL (Shor's)")
    print("    Migration: mlkem768nistp256 (hybrid) → pure ML-KEM-768")

    return negotiated


# ---------------------------------------------------------------------------
# Step 3: DH / ECDH Key Exchange
# ---------------------------------------------------------------------------

def step_ecdh_kex():
    print("\n  [Step 3] ECDH Key Exchange (ecdh-sha2-nistp256)")

    t0 = time.perf_counter()
    client_ecdh_priv = ec.generate_private_key(ec.SECP256R1(), default_backend())
    server_ecdh_priv = ec.generate_private_key(ec.SECP256R1(), default_backend())
    keygen_ms = (time.perf_counter() - t0) * 1000

    client_pub = client_ecdh_priv.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    server_pub = server_ecdh_priv.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )

    t0 = time.perf_counter()
    shared_k = client_ecdh_priv.exchange(ECDH(), server_ecdh_priv.public_key())
    kex_ms = (time.perf_counter() - t0) * 1000

    # SSH exchange hash H = hash(V_C || V_S || I_C || I_S || K_S || Q_C || Q_S || K)
    exchange_hash = hashlib.sha256(
        client_pub + server_pub + shared_k
    ).digest()

    print(f"    Curve              : P-256 (secp256r1)")
    print(f"    Client ephemeral   : {client_pub.hex()[:32]}... ({len(client_pub)} bytes)")
    print(f"    Server ephemeral   : {server_pub.hex()[:32]}... ({len(server_pub)} bytes)")
    print(f"    Shared secret (K)  : {shared_k.hex()[:32]}... ({len(shared_k)} bytes)")
    print(f"    Exchange hash (H)  : {exchange_hash.hex()}")
    print(f"    Keygen time        : {keygen_ms:.3f} ms")
    print(f"    ECDH exchange time : {kex_ms:.3f} ms")
    print()
    print("    [QUANTUM THREAT] CRITICAL — Shor's breaks ECDLP for P-256")
    print("    Logical qubits     : ~2,330 for P-256")
    print("    Migration target   : ML-KEM-768 (Kyber) — FIPS 203")

    return shared_k, exchange_hash


# ---------------------------------------------------------------------------
# Step 4: Host Key Authentication (Server proves identity)
# ---------------------------------------------------------------------------

def step_host_key_auth(exchange_hash: bytes):
    print("\n  [Step 4] Host Key Authentication (SSH_MSG_KEXECDH_REPLY)")

    # Server's long-term RSA host key
    t0 = time.perf_counter()
    server_rsa_priv = rsa.generate_private_key(65537, 2048, default_backend())
    rsa_keygen_ms = (time.perf_counter() - t0) * 1000

    # Server's long-term ECDSA host key
    t0 = time.perf_counter()
    server_ecdsa_priv = ec.generate_private_key(ec.SECP256R1(), default_backend())
    ecdsa_keygen_ms = (time.perf_counter() - t0) * 1000

    # Server signs exchange hash with ECDSA
    t0 = time.perf_counter()
    host_sig = server_ecdsa_priv.sign(exchange_hash, ec.ECDSA(hashes.SHA256()))
    sign_ms = (time.perf_counter() - t0) * 1000

    # Client verifies
    t0 = time.perf_counter()
    server_ecdsa_priv.public_key().verify(host_sig, exchange_hash, ec.ECDSA(hashes.SHA256()))
    verify_ms = (time.perf_counter() - t0) * 1000

    rsa_pub_pem = server_rsa_priv.public_key().public_bytes(
        serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH
    )

    print(f"    RSA host key       : {len(rsa_pub_pem)} bytes OpenSSH format")
    print(f"    RSA keygen time    : {rsa_keygen_ms:.2f} ms")
    print(f"    ECDSA host key     : P-256, used for active session")
    print(f"    ECDSA keygen time  : {ecdsa_keygen_ms:.3f} ms")
    print(f"    Signature over H   : {host_sig.hex()[:32]}... ({len(host_sig)} bytes)")
    print(f"    Sign time          : {sign_ms:.3f} ms")
    print(f"    Verify time        : {verify_ms:.3f} ms")
    print(f"    Host auth result   : PASS")
    print()
    print("    [QUANTUM THREAT] CRITICAL")
    print("    RSA-2048 host key   : broken by Shor's (~4096 qubits)")
    print("    ECDSA P-256 key     : broken by Shor's (~2330 qubits)")
    print("    TOFU (trust-on-first-use) model stores classical pubkey.")
    print("    Migration: host key must transition to ML-DSA.")
    print("    OpenSSH 9.x: mlkem768nistp256 hybrid KEM available now.")

    return server_ecdsa_priv


# ---------------------------------------------------------------------------
# Step 5: Key Derivation — SSH_MSG_NEWKEYS
# ---------------------------------------------------------------------------

def step_newkeys(shared_secret: bytes, exchange_hash: bytes):
    print("\n  [Step 5] SSH New Keys — Key Derivation (SSH_MSG_NEWKEYS)")

    # SSH key derivation: K_n = hash(K || H || X || session_id)
    # X = 'A'..'F' for different key material
    def ssh_derive(letter: bytes, length: int) -> bytes:
        key = hashlib.sha256(shared_secret + exchange_hash + letter).digest()
        # Extend if needed
        while len(key) < length:
            key += hashlib.sha256(shared_secret + exchange_hash + key).digest()
        return key[:length]

    t0 = time.perf_counter()
    iv_c2s    = ssh_derive(b"A", 16)   # 128-bit IV for AES-256-CTR
    iv_s2c    = ssh_derive(b"B", 16)
    enc_c2s   = ssh_derive(b"C", 32)   # 256-bit AES key
    enc_s2c   = ssh_derive(b"D", 32)
    mac_c2s   = ssh_derive(b"E", 32)   # 256-bit HMAC key
    mac_s2c   = ssh_derive(b"F", 32)
    kdf_ms = (time.perf_counter() - t0) * 1000

    print(f"    KDF                : SHA-256 (K || H || X || session_id)")
    print(f"    IV (C→S)           : {iv_c2s.hex()} (16 bytes)")
    print(f"    IV (S→C)           : {iv_s2c.hex()} (16 bytes)")
    print(f"    Enc key (C→S)      : {enc_c2s.hex()[:32]}... (32 bytes, AES-256)")
    print(f"    Enc key (S→C)      : {enc_s2c.hex()[:32]}... (32 bytes, AES-256)")
    print(f"    MAC key (C→S)      : {mac_c2s.hex()[:32]}... (32 bytes, HMAC-SHA256)")
    print(f"    MAC key (S→C)      : {mac_s2c.hex()[:32]}... (32 bytes, HMAC-SHA256)")
    print(f"    KDF time           : {kdf_ms:.3f} ms")

    return enc_c2s, iv_c2s, mac_c2s


# ---------------------------------------------------------------------------
# Step 6: Data Transfer — AES-256-CTR + HMAC-SHA256
# ---------------------------------------------------------------------------

def step_channel_data(enc_key: bytes, iv: bytes, mac_key: bytes):
    print("\n  [Step 6] Channel Data Transfer — AES-256-CTR + HMAC-SHA256")

    command = b"ls -la /home/praveen/quantum-projects"
    response = b"total 42\ndrwxr-xr-x 30 praveen praveen 4096 Oct 1 2026 .\n"

    # AES-256-CTR encryption of command
    t0 = time.perf_counter()
    cipher = Cipher(
        algorithms.AES(enc_key),
        modes.CTR(iv),
        backend=default_backend(),
    )
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(command) + encryptor.finalize()
    enc_ms = (time.perf_counter() - t0) * 1000

    # HMAC-SHA256 over sequence_number + ciphertext
    seq_num = struct.pack(">I", 1)
    mac_tag = hmac_module.new(mac_key, seq_num + ciphertext, "sha256").digest()

    # Decrypt
    t0 = time.perf_counter()
    decryptor = Cipher(
        algorithms.AES(enc_key), modes.CTR(iv), backend=default_backend()
    ).decryptor()
    recovered = decryptor.update(ciphertext) + decryptor.finalize()
    dec_ms = (time.perf_counter() - t0) * 1000

    # Verify MAC
    expected_mac = hmac_module.new(mac_key, seq_num + ciphertext, "sha256").digest()
    mac_valid = hmac_module.compare_digest(mac_tag, expected_mac)

    print(f"    Bulk cipher        : AES-256-CTR")
    print(f"    MAC                : HMAC-SHA256")
    print(f"    Command            : {command.decode()}")
    print(f"    Ciphertext         : {ciphertext.hex()[:40]}...")
    print(f"    MAC tag            : {mac_tag.hex()}")
    print(f"    Encrypt time       : {enc_ms:.3f} ms")
    print(f"    Decrypt time       : {dec_ms:.3f} ms")
    print(f"    MAC verify         : {'PASS' if mac_valid else 'FAIL'}")
    print(f"    Recovered command  : {recovered.decode()}")
    print()
    print("    [QUANTUM THREAT] LOW — AES-256-CTR resists Grover's attack")
    print("    Effective security : 128 bits post-quantum (acceptable)")
    print("    HMAC-SHA256        : LOW quantum threat (pre-image resistance)")


# ---------------------------------------------------------------------------
# User Authentication Simulation
# ---------------------------------------------------------------------------

def step_user_auth():
    print("\n  [Step 7] User Authentication (publickey method)")

    t0 = time.perf_counter()
    user_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    keygen_ms = (time.perf_counter() - t0) * 1000

    auth_data = b"SSH2 USERAUTH REQUEST: praveen @ quantum-bank-server"
    t0 = time.perf_counter()
    auth_sig = user_key.sign(auth_data, ec.ECDSA(hashes.SHA256()))
    sign_ms = (time.perf_counter() - t0) * 1000

    user_key.public_key().verify(auth_sig, auth_data, ec.ECDSA(hashes.SHA256()))

    pub_openssh = user_key.public_key().public_bytes(
        serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH
    )

    print(f"    Auth method        : publickey (ecdsa-sha2-nistp256)")
    print(f"    User key           : ECDSA P-256")
    print(f"    OpenSSH pubkey     : ecdsa-sha2-nistp256 {pub_openssh.decode().split()[1][:20]}...")
    print(f"    Keygen time        : {keygen_ms:.3f} ms")
    print(f"    Auth sign time     : {sign_ms:.3f} ms")
    print(f"    Auth result        : PASS")
    print()
    print("    [QUANTUM THREAT] CRITICAL")
    print("    User ECDSA key broken by Shor's algorithm.")
    print("    ~/.ssh/id_ecdsa public key exposed → private key derivable.")
    print("    Migration: generate new ML-DSA key pair; update authorized_keys.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print()
    print("##############################################################")
    print("#  CLASSICAL SSH PROTOCOL SIMULATION                        #")
    print("#  ECDH KEx + ECDSA Auth + AES-256-CTR + HMAC-SHA256        #")
    print("##############################################################")

    t_total = time.perf_counter()

    step_version_exchange()
    step_kexinit()
    shared_k, exchange_hash = step_ecdh_kex()
    step_host_key_auth(exchange_hash)
    enc_key, iv, mac_key = step_newkeys(shared_k, exchange_hash)
    step_channel_data(enc_key, iv, mac_key)
    step_user_auth()

    total_ms = (time.perf_counter() - t_total) * 1000

    print("\n" + "=" * 60)
    print("SSH PROTOCOL QUANTUM THREAT SUMMARY")
    print("=" * 60)
    print(f"  Total simulation time  : {total_ms:.2f} ms")
    print()
    print("  COMPONENT              SEVERITY   QUANTUM ATTACK")
    print("  ECDH key exchange      CRITICAL   Shor's (ECDLP on P-256)")
    print("  ECDSA host key         CRITICAL   Shor's (ECDLP on P-256)")
    print("  RSA host key           CRITICAL   Shor's (factoring 2048)")
    print("  ECDSA user auth key    CRITICAL   Shor's (ECDLP on P-256)")
    print("  AES-256-CTR bulk       LOW        Grover's (128-bit secure)")
    print("  HMAC-SHA256 MAC        LOW        Grover's (minor)")
    print()
    print("  MIGRATION PATH (RFC draft-ietf-sshm-*):")
    print("    KEx      : mlkem768nistp256 (hybrid, OpenSSH 9.x available)")
    print("    Host key : sk-ssh-ml-dsa-65 (OpenSSH PQC WG, 2025 draft)")
    print("    User key : sk-ssh-ml-dsa-44 (FIPS 204)")
    print("    Bulk     : Keep AES-256-CTR or chacha20-poly1305")
    print()


if __name__ == "__main__":
    main()
