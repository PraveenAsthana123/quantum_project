"""
Classical JWT Demo — HMAC-SHA256 (HS256), RS256, ES256
Shows token generation, verification, timing benchmarks.
Includes replay attack vulnerability demonstration.
Shows quantum threat assessment per algorithm.

JWT structure: base64url(header).base64url(payload).signature
"""

import os
import time
import json
import hmac
import base64
import hashlib
import struct
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend


# ---------------------------------------------------------------------------
# Base64url helpers
# ---------------------------------------------------------------------------

def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s)


def encode_header_payload(header: dict, payload: dict) -> str:
    h = b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    return f"{h}.{p}"


# ---------------------------------------------------------------------------
# HS256 — HMAC-SHA256
# ---------------------------------------------------------------------------

def demo_hs256():
    print("\n" + "=" * 60)
    print("JWT HS256 — HMAC-SHA256 (Symmetric Shared Secret)")
    print("=" * 60)

    secret = os.urandom(32)
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": "user-42",
        "name": "Praveen Asthana",
        "role": "admin",
        "iat": 1727740800,
        "exp": 1727744400,
        "jti": b64url_encode(os.urandom(16)),
    }

    signing_input = encode_header_payload(header, payload)

    t0 = time.perf_counter()
    sig = hmac.new(secret, signing_input.encode(), hashlib.sha256).digest()
    sign_ms = (time.perf_counter() - t0) * 1000

    token = f"{signing_input}.{b64url_encode(sig)}"

    # Verify
    t0 = time.perf_counter()
    parts = token.split(".")
    check_input = f"{parts[0]}.{parts[1]}"
    expected = hmac.new(secret, check_input.encode(), hashlib.sha256).digest()
    actual   = b64url_decode(parts[2])
    valid = hmac.compare_digest(expected, actual)
    verify_ms = (time.perf_counter() - t0) * 1000

    print(f"  Algorithm        : HS256 (HMAC-SHA256)")
    print(f"  Secret key size  : {len(secret)*8} bits")
    print(f"  Token length     : {len(token)} chars")
    print(f"  Sign time        : {sign_ms:.3f} ms")
    print(f"  Verify time      : {verify_ms:.3f} ms")
    print(f"  Signature valid  : {valid}")
    print(f"  Token (preview)  : {token[:60]}...")
    print()
    print("  [SECURITY NOTE]  HS256 requires shared secret — both sides")
    print("                   must possess the same key. Not suitable for")
    print("                   distributed microservice verification.")
    print()
    print("  [QUANTUM THREAT] LOW")
    print("  HMAC-SHA256 is not broken by Shor's or Grover's in a useful way.")
    print("  Key secrecy (32-byte) is the main risk — not algorithm weakness.")

    return token, secret


# ---------------------------------------------------------------------------
# RS256 — RSA-PKCS1v15-SHA256
# ---------------------------------------------------------------------------

def demo_rs256():
    print("\n" + "=" * 60)
    print("JWT RS256 — RSA-2048 + SHA-256 (Asymmetric)")
    print("=" * 60)

    t0 = time.perf_counter()
    private_key = rsa.generate_private_key(65537, 2048, default_backend())
    keygen_ms = (time.perf_counter() - t0) * 1000

    header = {"alg": "RS256", "typ": "JWT", "kid": "rsa-2048-v1"}
    payload = {
        "iss": "https://auth.quantum-bank.example",
        "sub": "svc-account-api",
        "aud": "https://api.quantum-bank.example",
        "iat": 1727740800,
        "exp": 1727744400,
        "scope": "read:balance write:transfer",
        "jti": b64url_encode(os.urandom(16)),
    }

    signing_input = encode_header_payload(header, payload)

    t0 = time.perf_counter()
    signature = private_key.sign(
        signing_input.encode(),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    sign_ms = (time.perf_counter() - t0) * 1000

    token = f"{signing_input}.{b64url_encode(signature)}"

    # Verify with public key
    public_key = private_key.public_key()
    t0 = time.perf_counter()
    parts = token.split(".")
    check_input = f"{parts[0]}.{parts[1]}"
    decoded_sig = b64url_decode(parts[2])
    public_key.verify(decoded_sig, check_input.encode(), padding.PKCS1v15(), hashes.SHA256())
    verify_ms = (time.perf_counter() - t0) * 1000

    # JWK public key (simplified)
    pub_numbers = public_key.public_key().key_size if hasattr(public_key, "public_key") else 2048

    print(f"  Algorithm        : RS256 (RSA-PKCS1v15-SHA256)")
    print(f"  RSA key size     : 2048 bits")
    print(f"  Keygen time      : {keygen_ms:.2f} ms")
    print(f"  Token length     : {len(token)} chars")
    print(f"  Signature size   : {len(signature)} bytes")
    print(f"  Sign time        : {sign_ms:.3f} ms")
    print(f"  Verify time      : {verify_ms:.3f} ms")
    print(f"  Signature valid  : PASS")
    print(f"  Token (preview)  : {token[:60]}...")
    print()
    print("  [QUANTUM THREAT] CRITICAL")
    print("  Shor's algorithm factors RSA-2048 modulus.")
    print("  Attacker can derive private key from public JWK endpoint.")
    print("  All issued tokens become forgeable with CRQC.")
    print("  Migration target : ECDSA P-256 (short term) → ML-DSA (PQC)")

    return token, private_key


# ---------------------------------------------------------------------------
# ES256 — ECDSA P-256 + SHA-256
# ---------------------------------------------------------------------------

def demo_es256():
    print("\n" + "=" * 60)
    print("JWT ES256 — ECDSA P-256 + SHA-256 (Compact Asymmetric)")
    print("=" * 60)

    t0 = time.perf_counter()
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    keygen_ms = (time.perf_counter() - t0) * 1000

    header = {"alg": "ES256", "typ": "JWT", "kid": "ecdsa-p256-v1"}
    payload = {
        "iss": "https://auth.quantum-bank.example",
        "sub": "mobile-client-001",
        "aud": "https://api.quantum-bank.example",
        "iat": 1727740800,
        "exp": 1727744400,
        "jti": b64url_encode(os.urandom(16)),
    }

    signing_input = encode_header_payload(header, payload)

    t0 = time.perf_counter()
    signature_der = private_key.sign(signing_input.encode(), ec.ECDSA(hashes.SHA256()))
    sign_ms = (time.perf_counter() - t0) * 1000

    # ES256 uses fixed-size (r || s) 64-byte format, not DER
    token = f"{signing_input}.{b64url_encode(signature_der)}"

    # Verify
    public_key = private_key.public_key()
    t0 = time.perf_counter()
    parts = token.split(".")
    check_input = f"{parts[0]}.{parts[1]}"
    decoded_sig = b64url_decode(parts[2])
    public_key.verify(decoded_sig, check_input.encode(), ec.ECDSA(hashes.SHA256()))
    verify_ms = (time.perf_counter() - t0) * 1000

    print(f"  Algorithm        : ES256 (ECDSA-P256-SHA256)")
    print(f"  EC curve         : P-256 (secp256r1), 256-bit")
    print(f"  Keygen time      : {keygen_ms:.3f} ms")
    print(f"  Token length     : {len(token)} chars")
    print(f"  Signature size   : {len(signature_der)} bytes (DER)")
    print(f"  Sign time        : {sign_ms:.3f} ms")
    print(f"  Verify time      : {verify_ms:.3f} ms")
    print(f"  Signature valid  : PASS")
    print(f"  Token (preview)  : {token[:60]}...")
    print()
    print("  [QUANTUM THREAT] CRITICAL")
    print("  Shor's solves ECDLP — private key extractable from public key.")
    print("  Smaller signature than RS256 but same quantum vulnerability.")
    print("  Migration target : ML-DSA-44 (Dilithium2) — FIPS 204")

    return token, private_key


# ---------------------------------------------------------------------------
# Replay Attack Vulnerability Demo
# ---------------------------------------------------------------------------

def demo_replay_attack(hs256_token: str, hs256_secret: bytes):
    print("\n" + "=" * 60)
    print("JWT REPLAY ATTACK VULNERABILITY DEMO")
    print("=" * 60)

    print("  Scenario: Attacker captures a valid JWT and replays it.")
    print()

    parts = hs256_token.split(".")
    payload_bytes = b64url_decode(parts[1])
    payload = json.loads(payload_bytes)

    print(f"  Captured token   : {hs256_token[:60]}...")
    print(f"  Decoded payload  :")
    for k, v in payload.items():
        print(f"    {k:10} : {v}")

    print()
    print("  Attack 1: Replay the exact token on a different endpoint")
    print("    → Succeeds if server does not validate 'aud' claim")
    print("    → Fix: Always validate 'aud', 'iss', and 'sub'")

    print()
    print("  Attack 2: Modify payload without resigning (alg:none attack)")
    # Craft a forged token with alg:none
    forged_header  = {"alg": "none", "typ": "JWT"}
    forged_payload = dict(payload)
    forged_payload["role"] = "superadmin"
    forged_input = encode_header_payload(forged_header, forged_payload)
    forged_token = f"{forged_input}."

    print(f"    Forged token     : {forged_token[:60]}...")
    print(f"    Modified claim   : role=superadmin")
    print("    → Accepted by naive JWT libs that allow 'alg:none'")
    print("    → Fix: Whitelist allowed algorithms; NEVER accept 'none'")

    print()
    print("  Attack 3: JWT ID (jti) absence → indefinite replay window")
    payload_no_jti = {k: v for k, v in payload.items() if k != "jti"}
    signing_input = encode_header_payload({"alg": "HS256", "typ": "JWT"}, payload_no_jti)
    sig = hmac.new(hs256_secret, signing_input.encode(), hashlib.sha256).digest()
    token_no_jti = f"{signing_input}.{b64url_encode(sig)}"
    print(f"    Token without jti: {token_no_jti[:60]}...")
    print("    → Without 'jti' server cannot detect replay of same token")
    print("    → Fix: Include 'jti'; maintain server-side revocation list")

    print()
    print("  [QUANTUM ANGLE] Pre-harvest-now-decrypt-later attacks")
    print("    Adversary captures tokens today, decrypts with CRQC in 2030")
    print("    Long-lived tokens (OAuth refresh tokens) are highest risk")
    print("    Fix: Reduce token lifetime; rotate signing keys frequently")


# ---------------------------------------------------------------------------
# Algorithm comparison table
# ---------------------------------------------------------------------------

def demo_comparison_table():
    print("\n" + "=" * 60)
    print("JWT ALGORITHM COMPARISON + QUANTUM THREAT MATRIX")
    print("=" * 60)

    rows = [
        ("HS256", "HMAC-SHA256",      "Symmetric", "256-bit", "LOW",      "None",   "< ~10 ms",  "Key secrecy only"),
        ("RS256", "RSA-PKCS1v15",     "Asymmetric","2048-bit","CRITICAL", "Shor's", "~50-200 ms","~4096 logical qubits"),
        ("RS384", "RSA-PKCS1v15",     "Asymmetric","3072-bit","CRITICAL", "Shor's", "~100-400ms","~6144 logical qubits"),
        ("ES256", "ECDSA-P256",       "Asymmetric","256-bit", "CRITICAL", "Shor's", "< 5 ms",    "~2330 logical qubits"),
        ("ES384", "ECDSA-P384",       "Asymmetric","384-bit", "CRITICAL", "Shor's", "< 5 ms",    "~3484 logical qubits"),
        ("EdDSA", "Ed25519",          "Asymmetric","256-bit", "CRITICAL", "Shor's", "< 2 ms",    "~2330 logical qubits"),
    ]

    print(f"  {'ALG':<8} {'PRIMITIVE':<20} {'TYPE':<12} {'KEY':<10} {'QUANTUM':<10} {'ATTACK':<8} {'LATENCY':<12} {'NOTES'}")
    print("  " + "-" * 100)
    for row in rows:
        print(f"  {row[0]:<8} {row[1]:<20} {row[2]:<12} {row[3]:<10} {row[4]:<10} {row[5]:<8} {row[6]:<12} {row[7]}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print()
    print("##############################################################")
    print("#  CLASSICAL JWT DEMO — HS256 / RS256 / ES256               #")
    print("#  Token generation, verification, replay attacks, threats   #")
    print("##############################################################")

    hs256_token, hs256_secret = demo_hs256()
    demo_rs256()
    demo_es256()
    demo_replay_attack(hs256_token, hs256_secret)
    demo_comparison_table()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("  HS256  : Quantum-safe in terms of algorithm; key management risk")
    print("  RS256  : CRITICAL — RSA-2048 broken by Shor's algorithm")
    print("  ES256  : CRITICAL — ECDSA P-256 broken by Shor's algorithm")
    print()
    print("  PQC JWT migration path:")
    print("    Short-term  : Reduce token lifetimes, rotate keys aggressively")
    print("    Medium-term : Hybrid JWT (ES256 + ML-DSA-44) in custom alg field")
    print("    Long-term   : ML-DSA-44 as sole signing algorithm (IETF WG active)")
    print()


if __name__ == "__main__":
    main()
