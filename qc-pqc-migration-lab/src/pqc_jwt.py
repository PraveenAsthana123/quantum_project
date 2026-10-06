"""
PQC JWT — ML-DSA-65 (FIPS 204) JSON Web Token
Simulates the migration path: RS256 → ML-DSA-65
Shows dual-token issuance during transition period.

References:
  - IETF draft-ietf-jose-fully-specified-algorithms
  - IETF draft-ietf-oauth-pqca (PQC for OAuth/OIDC)
  - NIST FIPS 204 (ML-DSA)
"""

import os
import time
import json
import base64
import hashlib
import hmac
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


# ─── Constants ───────────────────────────────────────────────────────────────

# Algorithm identifiers (IANA JOSE registry + IETF draft proposals)
ALG_RS256      = "RS256"
ALG_ES256      = "ES256"
ALG_ML_DSA_44  = "ML-DSA-44"
ALG_ML_DSA_65  = "ML-DSA-65"   # NIST Security Level 3 — recommended
ALG_ML_DSA_87  = "ML-DSA-87"

# Realistic key/signature sizes (bytes)
RSA2048_PK_SIZE  = 256
RSA2048_SK_SIZE  = 2349
RSA2048_SIG_SIZE = 256

MLDSA65_PK_SIZE  = 1952
MLDSA65_SK_SIZE  = 4032
MLDSA65_SIG_SIZE = 3309

# Typical token component sizes (bytes) for comparison
RS256_HEADER_B64      = 36    # {"alg":"RS256","typ":"JWT"}
RS256_PAYLOAD_B64     = 200   # standard claims
RS256_SIG_B64         = 344   # base64url(256B)
RS256_TOTAL           = RS256_HEADER_B64 + RS256_PAYLOAD_B64 + RS256_SIG_B64 + 2  # dots

MLDSA65_HEADER_B64    = 44    # {"alg":"ML-DSA-65","typ":"JWT"}
MLDSA65_SIG_B64       = 4412  # base64url(3309B) = ceil(3309*4/3) = 4412
MLDSA65_TOTAL         = MLDSA65_HEADER_B64 + RS256_PAYLOAD_B64 + MLDSA65_SIG_B64 + 2


# ─── Simulated crypto primitives ────────────────────────────────────────────

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = (-len(s)) % 4
    return base64.urlsafe_b64decode(s + "=" * pad)


def _sim_rsa2048_keygen() -> Tuple[bytes, bytes]:
    return os.urandom(RSA2048_PK_SIZE), os.urandom(RSA2048_SK_SIZE)


def _sim_rsa2048_sign(sk: bytes, data: bytes) -> bytes:
    mac = hmac.new(sk[:32], data, hashlib.sha256).digest()
    sig = mac
    while len(sig) < RSA2048_SIG_SIZE:
        sig += hashlib.sha256(sig).digest()
    return sig[:RSA2048_SIG_SIZE]


def _sim_mldsa65_keygen() -> Tuple[bytes, bytes]:
    return os.urandom(MLDSA65_PK_SIZE), os.urandom(MLDSA65_SK_SIZE)


def _sim_mldsa65_sign(sk: bytes, data: bytes) -> bytes:
    mac = hmac.new(sk[:32], data, hashlib.sha3_512).digest()
    sig = mac
    while len(sig) < MLDSA65_SIG_SIZE:
        sig += hashlib.sha3_256(sig).digest()
    return sig[:MLDSA65_SIG_SIZE]


def _sim_mldsa65_verify(pk: bytes, data: bytes, sig: bytes) -> bool:
    return len(sig) == MLDSA65_SIG_SIZE


def _sim_rsa2048_verify(pk: bytes, data: bytes, sig: bytes) -> bool:
    return len(sig) == RSA2048_SIG_SIZE


# ─── JWT implementation ──────────────────────────────────────────────────────

@dataclass
class JWTKey:
    algorithm: str
    public_key: bytes
    private_key: bytes
    key_id: str = ""

    def __post_init__(self):
        if not self.key_id:
            self.key_id = hashlib.sha256(self.public_key[:32]).hexdigest()[:8]


def _make_claims(subject: str, issuer: str, audience: str,
                 extra: Dict[str, Any] = None) -> Dict[str, Any]:
    now = int(time.time())
    claims = {
        "iss": issuer,
        "sub": subject,
        "aud": audience,
        "iat": now,
        "exp": now + 3600,
        "jti": os.urandom(8).hex(),
        "scope": "openid profile email",
        "roles": ["user", "api:read"],
    }
    if extra:
        claims.update(extra)
    return claims


class PQCJWTSigner:
    """Issues JWTs signed with ML-DSA-65."""

    def __init__(self, key: JWTKey):
        self.key = key

    def sign(self, claims: Dict[str, Any]) -> str:
        header = {"alg": self.key.algorithm, "typ": "JWT", "kid": self.key.key_id}
        h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
        p = _b64url_encode(json.dumps(claims, separators=(",", ":")).encode())
        signing_input = f"{h}.{p}".encode()

        if self.key.algorithm in (ALG_ML_DSA_44, ALG_ML_DSA_65, ALG_ML_DSA_87):
            sig_bytes = _sim_mldsa65_sign(self.key.private_key, signing_input)
        elif self.key.algorithm == ALG_RS256:
            sig_bytes = _sim_rsa2048_sign(self.key.private_key, signing_input)
        else:
            sig_bytes = hmac.new(self.key.private_key[:32],
                                 signing_input, hashlib.sha256).digest()

        s = _b64url_encode(sig_bytes)
        return f"{h}.{p}.{s}"

    def verify(self, token: str) -> Tuple[bool, Dict[str, Any]]:
        parts = token.split(".")
        if len(parts) != 3:
            return False, {}
        h, p, s = parts
        signing_input = f"{h}.{p}".encode()
        sig_bytes = _b64url_decode(s)
        header = json.loads(_b64url_decode(h))
        claims = json.loads(_b64url_decode(p))

        alg = header.get("alg", "")
        if alg in (ALG_ML_DSA_44, ALG_ML_DSA_65, ALG_ML_DSA_87):
            ok = _sim_mldsa65_verify(self.key.public_key, signing_input, sig_bytes)
        elif alg == ALG_RS256:
            ok = _sim_rsa2048_verify(self.key.public_key, signing_input, sig_bytes)
        else:
            ok = False

        return ok, claims if ok else {}


class DualTokenIssuer:
    """
    Issues both RS256 and ML-DSA-65 tokens during the migration window.
    Clients that support PQC verify with ML-DSA-65; legacy clients fall back to RS256.
    """

    def __init__(self):
        rsa_pk, rsa_sk = _sim_rsa2048_keygen()
        self.rsa_key = JWTKey(ALG_RS256, rsa_pk, rsa_sk)

        pqc_pk, pqc_sk = _sim_mldsa65_keygen()
        self.pqc_key = JWTKey(ALG_ML_DSA_65, pqc_pk, pqc_sk)

        self.rsa_signer = PQCJWTSigner(self.rsa_key)
        self.pqc_signer = PQCJWTSigner(self.pqc_key)

    def issue(self, claims: Dict[str, Any]) -> Dict[str, str]:
        return {
            "rs256_token":    self.rsa_signer.sign(claims),
            "mldsa65_token":  self.pqc_signer.sign(claims),
        }


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  PQC JWT SIMULATION — RS256 → ML-DSA-65 (FIPS 204)")
    print("=" * 65)

    # ── 1. Key generation ─────────────────────────────────────────────
    print("\n── [1] ML-DSA-65 Key Generation ─────────────────────────────")
    t0 = time.perf_counter()
    pqc_pk, pqc_sk = _sim_mldsa65_keygen()
    kg_ms = (time.perf_counter() - t0) * 1000
    kid = hashlib.sha256(pqc_pk[:32]).hexdigest()[:8]
    print(f"  Algorithm  : ML-DSA-65 (FIPS 204 / Dilithium3)")
    print(f"  Public key : {len(pqc_pk):,} bytes")
    print(f"  Private key: {len(pqc_sk):,} bytes")
    print(f"  Key ID     : {kid}")
    print(f"  KeyGen time: {kg_ms:.4f} ms")

    # ── 2. Single ML-DSA-65 token ────────────────────────────────────
    print("\n── [2] Sign a JWT with ML-DSA-65 ────────────────────────────")
    pqc_key = JWTKey(ALG_ML_DSA_65, pqc_pk, pqc_sk)
    signer  = PQCJWTSigner(pqc_key)
    claims  = _make_claims("user-42", "auth.example.com",
                            "api.example.com",
                            {"email": "alice@example.com", "org": "ExampleCorp"})

    t0 = time.perf_counter()
    token = signer.sign(claims)
    sign_ms = (time.perf_counter() - t0) * 1000

    print(f"  Header : {{\"alg\":\"ML-DSA-65\",\"typ\":\"JWT\",\"kid\":\"{kid}\"}}")
    print(f"  Token structure: <header>.<payload>.<signature>")
    print(f"  Token length   : {len(token):,} bytes")
    print(f"  Signature part : {len(token.split('.')[2]):,} chars "
          f"(base64url of {MLDSA65_SIG_SIZE} bytes)")
    print(f"  Sign time      : {sign_ms:.4f} ms")

    # ── 3. Verify ────────────────────────────────────────────────────
    t0 = time.perf_counter()
    ok, decoded = signer.verify(token)
    verify_ms = (time.perf_counter() - t0) * 1000
    print(f"\n── [3] Verify ML-DSA-65 Token ───────────────────────────────")
    print(f"  Verification : {'PASS' if ok else 'FAIL'}")
    print(f"  Verify time  : {verify_ms:.4f} ms")
    if ok:
        print(f"  Decoded sub  : {decoded.get('sub')}")
        print(f"  Decoded iss  : {decoded.get('iss')}")
        print(f"  Decoded scope: {decoded.get('scope')}")

    # ── 4. Token size comparison ─────────────────────────────────────
    print("\n── [4] Token Size: RS256 vs ML-DSA-65 ───────────────────────")
    rsa_pk, rsa_sk = _sim_rsa2048_keygen()
    rsa_key = JWTKey(ALG_RS256, rsa_pk, rsa_sk)
    rsa_signer = PQCJWTSigner(rsa_key)
    rsa_token  = rsa_signer.sign(claims)

    rows = [
        ("Metric",           "RS256",                     "ML-DSA-65"),
        ("Algorithm",        "RSA-2048 + SHA-256",        "ML-DSA-65 (FIPS 204)"),
        ("Token length",     f"{len(rsa_token):,} chars", f"{len(token):,} chars"),
        ("Signature size",   f"{RSA2048_SIG_SIZE} bytes", f"{MLDSA65_SIG_SIZE} bytes"),
        ("Sig (base64url)",  f"{len(rsa_token.split('.')[2]):,} chars",
                             f"{len(token.split('.')[2]):,} chars"),
        ("Public key size",  f"{RSA2048_PK_SIZE} bytes",  f"{MLDSA65_PK_SIZE} bytes"),
        ("Quantum-safe",     "NO (Shor's algorithm)",     "YES (NIST Level 3)"),
        ("FIPS reference",   "FIPS 186-4 (deprecated)",  "FIPS 204 (2024)"),
    ]
    col_w = [26, 28, 28]
    header = "  " + " | ".join(f"{rows[0][i]:<{col_w[i]}}" for i in range(3))
    print(header)
    print("  " + "-" * (sum(col_w) + 6))
    for row in rows[1:]:
        print("  " + " | ".join(f"{row[i]:<{col_w[i]}}" for i in range(3)))

    size_ratio = len(token) / len(rsa_token)
    print(f"\n  ML-DSA-65 JWT is {size_ratio:.1f}x larger than RS256 JWT")
    print(f"  Mitigation: compress claims, use short-lived tokens,")
    print(f"              move signature to header in HTTP/2 trailers")

    # ── 5. Dual-token migration approach ─────────────────────────────
    print("\n── [5] Dual-Token Issuer (Migration Window) ─────────────────")
    issuer = DualTokenIssuer()
    dual   = issuer.issue(claims)

    rs256_tok  = dual["rs256_token"]
    mldsa_tok  = dual["mldsa65_token"]
    print(f"  RS256    token: {len(rs256_tok):,} chars  (legacy clients)")
    print(f"  ML-DSA-65 token: {len(mldsa_tok):,} chars  (PQC-capable clients)")
    print(f"")
    print(f"  Authorization header (PQC client):")
    print(f"    Authorization: Bearer <ML-DSA-65 token>")
    print(f"    X-Alt-Token:   Bearer <RS256 token>  (fallback)")
    print(f"")
    print(f"  JWKS endpoint would expose two keys:")
    print(f"    kid={issuer.rsa_key.key_id[:8]}  alg=RS256      (legacy)")
    print(f"    kid={issuer.pqc_key.key_id[:8]}  alg=ML-DSA-65  (PQC)")

    # ── 6. Migration roadmap ──────────────────────────────────────────
    print("\n── [6] Migration Roadmap: RS256 → ML-DSA-65 ─────────────────")
    steps = [
        ("Phase 1", "Deploy ML-DSA-65 JWKS endpoint alongside RS256"),
        ("Phase 2", "Issue dual tokens; PQC-capable services prefer ML-DSA-65"),
        ("Phase 3", "Flag RS256 as deprecated in JWKS (x-deprecated: true)"),
        ("Phase 4", "Require ML-DSA-65 for sensitive scopes (admin, write)"),
        ("Phase 5", "Retire RS256 JWKS key; reject RS256 tokens"),
    ]
    for phase, desc in steps:
        print(f"  {phase}: {desc}")

    print("\n  IETF references:")
    print("    draft-ietf-jose-fully-specified-algorithms")
    print("    draft-ietf-oauth-pqca")
    print("    NIST SP 800-131Ar3 (disallows RSA-2048 after 2030)")
    print("=" * 65)


if __name__ == "__main__":
    main()
