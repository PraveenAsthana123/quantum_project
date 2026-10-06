"""
Classical VPN Simulation — IPsec/IKEv2
Demonstrates:
  - IKEv2 SA negotiation
  - DH Group 14 (2048-bit MODP) key exchange
  - PRF-HMAC-SHA256 key derivation (SKEYSEED, KEYMAT)
  - AES-256-CBC encryption
  - HMAC-SHA256 integrity
  - IPsec ESP (Encapsulating Security Payload) packet simulation

References: RFC 7296 (IKEv2), RFC 4303 (ESP)
"""

import os
import time
import hashlib
import hmac as hmac_module
import struct
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7


# ---------------------------------------------------------------------------
# DH Group 14 parameters (RFC 3526, 2048-bit MODP)
# ---------------------------------------------------------------------------

# Truncated for simulation — use a real 2048-bit prime in production
DH_G14_P_HEX = (
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
    "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
    "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
    "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
    "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
    "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
    "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
    "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"
    "DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
    "15728E5A8AACAA68FFFFFFFFFFFFFFFF"
)
DH_G14_P = int(DH_G14_P_HEX, 16)
DH_G14_G = 2


# ---------------------------------------------------------------------------
# Simplified DH Group 14 key exchange (pure Python — avoids OpenSSL DH params API)
# ---------------------------------------------------------------------------

def dh_generate_keypair(p: int, g: int):
    """Generate a DH key pair using raw modular arithmetic."""
    priv = int.from_bytes(os.urandom(32), "big") % (p - 2) + 2
    pub  = pow(g, priv, p)
    return priv, pub


def dh_compute_shared(their_pub: int, my_priv: int, p: int) -> bytes:
    shared_int = pow(their_pub, my_priv, p)
    byte_len = (shared_int.bit_length() + 7) // 8
    return shared_int.to_bytes(byte_len, "big")


# ---------------------------------------------------------------------------
# IKEv2 PRF and Key Derivation (RFC 7296 §2.14)
# ---------------------------------------------------------------------------

def prf(key: bytes, data: bytes) -> bytes:
    """PRF = HMAC-SHA256."""
    return hmac_module.new(key, data, hashlib.sha256).digest()


def prf_plus(key: bytes, data: bytes, length: int) -> bytes:
    """prf+ key derivation for KEYMAT."""
    result = b""
    t = b""
    i = 1
    while len(result) < length:
        t = prf(key, t + data + bytes([i]))
        result += t
        i += 1
    return result[:length]


def derive_ikev2_keys(
    dh_shared: bytes,
    ni: bytes,
    nr: bytes,
    spi_i: bytes,
    spi_r: bytes,
):
    """
    IKEv2 key schedule (simplified):
      SKEYSEED = prf(Ni | Nr, g^ir)
      {SK_d | SK_ai | SK_ar | SK_ei | SK_er | SK_pi | SK_pr}
               = prf+(SKEYSEED, Ni | Nr | SPIi | SPIr)
    """
    skeyseed = prf(ni + nr, dh_shared)
    keymat   = prf_plus(skeyseed, ni + nr + spi_i + spi_r, 7 * 32)

    keys = {
        "SK_d":  keymat[0:32],    # Child SA key material PRF key
        "SK_ai": keymat[32:64],   # Auth key Initiator→Responder
        "SK_ar": keymat[64:96],   # Auth key Responder→Initiator
        "SK_ei": keymat[96:128],  # Enc key Initiator→Responder (AES-256)
        "SK_er": keymat[128:160], # Enc key Responder→Initiator (AES-256)
        "SK_pi": keymat[160:192], # AUTH payload PRF key (initiator)
        "SK_pr": keymat[192:224], # AUTH payload PRF key (responder)
    }
    return skeyseed, keys


# ---------------------------------------------------------------------------
# IKEv2 Phase 1: IKE_SA_INIT
# ---------------------------------------------------------------------------

def step_ike_sa_init():
    print("\n  [Step 1] IKE_SA_INIT — SA Negotiation + DH Exchange")

    spi_i = os.urandom(8)
    spi_r = os.urandom(8)
    ni    = os.urandom(32)
    nr    = os.urandom(32)

    proposed = {
        "encryption":  "ENCR_AES_CBC_256 (id=12)",
        "integrity":   "AUTH_HMAC_SHA2_256_128 (id=12)",
        "prf":         "PRF_HMAC_SHA2_256 (id=5)",
        "dh_group":    "DH Group 14 — 2048-bit MODP (id=14)",
    }
    print(f"    IKE SPIi           : {spi_i.hex()}")
    print(f"    IKE SPIr           : {spi_r.hex()}")
    print(f"    Nonce Ni           : {ni.hex()[:32]}... (32 bytes)")
    print(f"    Nonce Nr           : {nr.hex()[:32]}... (32 bytes)")
    print()
    print("    Proposed IKE SA:")
    for k, v in proposed.items():
        print(f"      {k:<16} : {v}")

    return spi_i, spi_r, ni, nr


# ---------------------------------------------------------------------------
# IKEv2 Phase 1: DH Group 14 Key Exchange
# ---------------------------------------------------------------------------

def step_dh_exchange():
    print("\n  [Step 2] DH Group 14 Key Exchange (2048-bit MODP)")

    t0 = time.perf_counter()
    init_priv, init_pub = dh_generate_keypair(DH_G14_P, DH_G14_G)
    resp_priv, resp_pub = dh_generate_keypair(DH_G14_P, DH_G14_G)
    keygen_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    shared_init = dh_compute_shared(resp_pub, init_priv, DH_G14_P)
    shared_resp = dh_compute_shared(init_pub, resp_priv, DH_G14_P)
    dh_ms = (time.perf_counter() - t0) * 1000

    assert shared_init == shared_resp, "DH shared secret mismatch!"

    print(f"    DH group           : Group 14 (2048-bit MODP, RFC 3526)")
    print(f"    Initiator pubkey   : {init_pub.bit_length()} bits, {hex(init_pub)[:20]}...")
    print(f"    Responder pubkey   : {resp_pub.bit_length()} bits, {hex(resp_pub)[:20]}...")
    print(f"    Shared secret      : {len(shared_init)} bytes, {shared_init.hex()[:32]}...")
    print(f"    Keygen time        : {keygen_ms:.2f} ms")
    print(f"    DH compute time    : {dh_ms:.2f} ms")
    print()
    print("    [QUANTUM THREAT] CRITICAL")
    print("    Algorithm           : Shor's solves discrete log mod p")
    print("    DH Group 14 (2048)  : ~4096 logical qubits to break")
    print("    DH Group 16 (4096)  : ~8192 logical qubits — not CRQC-safe")
    print("    Migration target    : ML-KEM-768 for IKEv2 (RFC draft active)")

    return shared_init


# ---------------------------------------------------------------------------
# IKEv2 Phase 1: Key Derivation (SKEYSEED)
# ---------------------------------------------------------------------------

def step_key_derivation(shared_secret: bytes, ni: bytes, nr: bytes, spi_i: bytes, spi_r: bytes):
    print("\n  [Step 3] IKEv2 Key Derivation (SKEYSEED + prf+)")

    t0 = time.perf_counter()
    skeyseed, keys = derive_ikev2_keys(shared_secret, ni, nr, spi_i, spi_r)
    kdf_ms = (time.perf_counter() - t0) * 1000

    print(f"    SKEYSEED           : {skeyseed.hex()}")
    print(f"    SK_d               : {keys['SK_d'].hex()[:32]}... (child SA PRF)")
    print(f"    SK_ei (enc init)   : {keys['SK_ei'].hex()[:32]}... (AES-256 key)")
    print(f"    SK_er (enc resp)   : {keys['SK_er'].hex()[:32]}... (AES-256 key)")
    print(f"    SK_ai (auth init)  : {keys['SK_ai'].hex()[:32]}... (HMAC-SHA256)")
    print(f"    SK_ar (auth resp)  : {keys['SK_ar'].hex()[:32]}... (HMAC-SHA256)")
    print(f"    KDF time           : {kdf_ms:.3f} ms")

    return keys


# ---------------------------------------------------------------------------
# IKEv2 Phase 2: Child SA + IPsec ESP
# ---------------------------------------------------------------------------

def step_child_sa_and_esp(keys: dict):
    print("\n  [Step 4] IKE_AUTH + Child SA Establishment")

    child_spi_i = os.urandom(4)
    child_spi_r = os.urandom(4)
    child_ni    = os.urandom(32)
    child_nr    = os.urandom(32)

    # Child SA keys derived from SK_d
    child_keymat = prf_plus(keys["SK_d"], child_ni + child_nr + child_spi_i + child_spi_r, 64)
    child_enc = child_keymat[:32]   # AES-256-CBC
    child_mac = child_keymat[32:64] # HMAC-SHA256

    print(f"    Child SA SPIi      : {child_spi_i.hex()}")
    print(f"    Child SA SPIr      : {child_spi_r.hex()}")
    print(f"    Child enc key      : {child_enc.hex()[:32]}... (AES-256-CBC)")
    print(f"    Child MAC key      : {child_mac.hex()[:32]}... (HMAC-SHA256)")

    print()
    print("  [Step 5] IPsec ESP Packet — AES-256-CBC + HMAC-SHA256")

    # Original IP payload
    ip_payload = b"\x45\x00" + b"\x00" * 18 + b"GET /api/v1/account HTTP/1.1\r\n\r\n"

    # AES-256-CBC requires PKCS7 padding
    padder   = PKCS7(128).padder()
    padded   = padder.update(ip_payload) + padder.finalize()
    iv_bytes = os.urandom(16)

    t0 = time.perf_counter()
    cipher = Cipher(
        algorithms.AES(child_enc),
        modes.CBC(iv_bytes),
        backend=default_backend(),
    )
    enc = cipher.encryptor()
    esp_cipher = enc.update(padded) + enc.finalize()
    enc_ms = (time.perf_counter() - t0) * 1000

    # ESP header: SPI (4) + Sequence (4) + IV (16) + ciphertext
    esp_seq = struct.pack(">I", 1)
    esp_hdr = child_spi_i + esp_seq + iv_bytes
    esp_pkt = esp_hdr + esp_cipher

    # HMAC-SHA256 over ESP header + ciphertext (ICV = first 16 bytes)
    icv_full = hmac_module.new(child_mac, esp_pkt, hashlib.sha256).digest()
    icv      = icv_full[:16]

    # Decrypt for verification
    t0 = time.perf_counter()
    dec  = Cipher(
        algorithms.AES(child_enc), modes.CBC(iv_bytes), backend=default_backend()
    ).decryptor()
    padded_out = dec.update(esp_cipher) + dec.finalize()
    unpadder   = PKCS7(128).unpadder()
    recovered  = unpadder.update(padded_out) + unpadder.finalize()
    dec_ms     = (time.perf_counter() - t0) * 1000

    print(f"    Cipher             : AES-256-CBC")
    print(f"    IV                 : {iv_bytes.hex()}")
    print(f"    Original payload   : {len(ip_payload)} bytes")
    print(f"    ESP packet size    : {len(esp_pkt)} bytes (hdr+IV+cipher)")
    print(f"    ICV (HMAC-SHA256)  : {icv.hex()} (16 bytes)")
    print(f"    Encrypt time       : {enc_ms:.3f} ms")
    print(f"    Decrypt time       : {dec_ms:.3f} ms")
    print(f"    Payload integrity  : {'PASS' if recovered == ip_payload else 'FAIL'}")
    print()
    print("    [QUANTUM THREAT] LOW — AES-256-CBC resists Grover's (128-bit)")
    print("    HMAC-SHA256 ICV    : LOW — Grover's gives minor speedup only")

    return child_enc, iv_bytes


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print()
    print("##############################################################")
    print("#  CLASSICAL IPsec/IKEv2 VPN SIMULATION                     #")
    print("#  DH Group14 + AES-256-CBC + HMAC-SHA256 + ESP              #")
    print("##############################################################")

    t_total = time.perf_counter()

    spi_i, spi_r, ni, nr = step_ike_sa_init()
    shared_secret = step_dh_exchange()
    keys = step_key_derivation(shared_secret, ni, nr, spi_i, spi_r)
    step_child_sa_and_esp(keys)

    total_ms = (time.perf_counter() - t_total) * 1000

    print("\n" + "=" * 60)
    print("IPsec/IKEv2 QUANTUM THREAT SUMMARY")
    print("=" * 60)
    print(f"  Total simulation time  : {total_ms:.2f} ms")
    print()
    print("  COMPONENT              SEVERITY   ALGORITHM")
    print("  DH Group 14 (2048)     CRITICAL   Shor's (discrete log mod p)")
    print("  DH Group 16 (4096)     CRITICAL   Shor's (larger but same class)")
    print("  AES-256-CBC bulk       LOW        Grover's (128-bit post-PQ)")
    print("  HMAC-SHA256 integrity  LOW        Grover's (minor pre-image)")
    print("  PRF-HMAC-SHA256        LOW        Grover's (minor)")
    print()
    print("  MIGRATION PLAN:")
    print("    IKEv2 KEx    : ML-KEM-1024 or hybrid ECDH+ML-KEM (RFC 9370)")
    print("    IKEv2 Auth   : ML-DSA-65 or hybrid ECDSA+ML-DSA")
    print("    Child SA enc : Keep AES-256-CBC or move to AES-256-GCM")
    print("    Child SA MAC : Keep HMAC-SHA256 (AES-256-GCM includes MAC)")
    print()
    print("  Timeline: NIST IR 8547 recommends migration by 2030.")
    print("  Harvest-now-decrypt-later: VPN traffic captured today is")
    print("  retroactively decryptable once DH group 14 is broken.")
    print()


if __name__ == "__main__":
    main()
