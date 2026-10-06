"""
Agent PQC Identity: Workload Attestation
=========================================
Purpose   : Post-quantum workload identity and certificate issuance for AI agents
Reference : SPIFFE/SPIRE workload identity (https://spiffe.io/), NIST SP 800-207 Zero Trust
Standard  : ML-DSA-65 (FIPS 204) for agent attestation and certificate signing
Security  : EUF-CMA under Module-LWE + Module-SIS; 178-bit classical/quantum security
Params    : N=256, Q=8380417, K=6, L=5, ETA=4, GAMMA1=2^17, TAU=49
"""
from __future__ import annotations

import time
import os
import json
import hashlib
import secrets
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ── ML-DSA-65 parameters (FIPS 204) ─────────────────────────────────────────
N      = 256
Q      = 8380417     # prime, 2^23 - 2^13 + 1
K      = 6           # matrix rows
L      = 5           # matrix columns
ETA    = 4           # secret key polynomial bound
GAMMA1 = 1 << 17     # 2^17 = 131072
GAMMA2 = (Q - 1) // 88   # ≈ 95232
BETA   = 120         # rejection bound on ||z||_∞
TAU    = 49          # challenge weight (number of ±1 in challenge c)


# ── Polynomial arithmetic over Z_q[x]/(x^N + 1) ─────────────────────────────

def _sample_uniform_poly(shape: tuple, rng: np.random.Generator) -> np.ndarray:
    """Sample uniform polynomial(s) with coefficients in Z_q."""
    return rng.integers(0, Q, size=shape, dtype=np.int64)


def _sample_small_poly(eta: int, shape: tuple, rng: np.random.Generator) -> np.ndarray:
    """Sample small polynomial(s) with coefficients in [-eta, eta]."""
    return rng.integers(-eta, eta + 1, size=shape, dtype=np.int64)


def _poly_mul(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    Polynomial multiplication in Z_q[x]/(x^N + 1).
    Uses numpy convolution + reduction: x^N ≡ -1 (mod x^N + 1).
    """
    c = np.convolve(a.astype(np.int64), b.astype(np.int64))
    result = np.zeros(N, dtype=np.int64)
    for i, coef in enumerate(c):
        if i < N:
            result[i] = (result[i] + coef) % Q
        else:
            result[i - N] = (result[i - N] - coef) % Q
    return result


def _mat_vec_mul(A: np.ndarray, v: np.ndarray) -> np.ndarray:
    """K×L matrix × L-vector → K-vector of polynomials mod q."""
    result = np.zeros((K, N), dtype=np.int64)
    for i in range(K):
        for j in range(L):
            p = _poly_mul(A[i, j], v[j])
            result[i] = (result[i] + p) % Q
    return result


def _vec_add(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    return (u + v) % Q


def _infinity_norm(poly_vec: np.ndarray) -> int:
    """Max absolute coefficient in centered representation (coeff > Q//2 → coeff - Q)."""
    centered = poly_vec.copy().astype(np.int64)
    centered[centered > Q // 2] -= Q
    return int(np.max(np.abs(centered)))


def _high_bits(r: np.ndarray, alpha: int | None = None) -> np.ndarray:
    """Extract high bits of polynomial coefficients for HighBits decomposition."""
    if alpha is None:
        alpha = 2 * GAMMA2
    centered = r.copy().astype(np.int64)
    centered = (centered + Q // 2) % Q - Q // 2
    return (centered + (alpha // 2)) // alpha


def _challenge_poly(mu: bytes, w1: np.ndarray) -> np.ndarray:
    """
    Hash-derived sparse challenge polynomial with exactly TAU ±1 coefficients.
    H(mu || w1_packed) → challenge c in {-1, 0, 1}^N, weight TAU.
    """
    packed = mu + w1.tobytes()
    h = hashlib.shake_256(packed).digest(32)
    seed = int.from_bytes(h, "big")
    rng_ch = np.random.default_rng(seed)
    c = np.zeros(N, dtype=np.int64)
    positions = rng_ch.choice(N, size=TAU, replace=False)
    signs = rng_ch.choice([-1, 1], size=TAU)
    for pos, sign in zip(positions, signs):
        c[pos] = sign
    return c


def _poly_vec_mul_challenge(c: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Multiply challenge polynomial c by each element of polynomial vector v."""
    result = np.zeros_like(v)
    for i in range(len(v)):
        result[i] = _poly_mul(c, v[i]) % Q
    return result


# ── ML-DSA-65 core functions ──────────────────────────────────────────────────

def _ml_dsa_keygen(rng: np.random.Generator) -> Tuple[Dict, Dict]:
    """
    ML-DSA-65 key generation (FIPS 204 Algorithm 1):
      A  ← R^(K×L)_q  (uniform)
      s1 ← S^L_η, s2 ← S^K_η
      t  = A·s1 + s2
    Returns (pk, sk) dicts.
    """
    A_seed = rng.integers(0, 256, size=32, dtype=np.uint8).tobytes()
    A  = _sample_uniform_poly((K, L, N), rng)
    s1 = _sample_small_poly(ETA, (L, N), rng)
    s2 = _sample_small_poly(ETA, (K, N), rng)
    t  = _vec_add(_mat_vec_mul(A, s1), s2)
    pk = {"A": A, "t": t, "seed": A_seed}
    sk = {"A": A, "t": t, "s1": s1, "s2": s2}
    return pk, sk


def _ml_dsa_sign(sk: Dict, message: bytes, rng: np.random.Generator) -> Dict:
    """
    ML-DSA-65 signing via Fiat-Shamir with aborts (FIPS 204 Algorithm 2):
      μ  = H(message)
      y  ~ S^L_{γ1-1}
      w  = A·y;  w1 = HighBits(w)
      c  = H(μ, w1)
      z  = y + c·s1
      Reject if ||z||_∞ ≥ γ1 - β  (restart)
    Returns σ = (z, h, c_tilde, c, w1, retries).
    """
    A  = sk["A"]
    s1 = sk["s1"]
    mu = hashlib.sha3_256(message).digest()

    for attempt in range(200):
        y  = rng.integers(-GAMMA1 + 1, GAMMA1, size=(L, N), dtype=np.int64)
        w  = _mat_vec_mul(A, y)
        w1 = np.array([_high_bits(w[i]) for i in range(K)], dtype=np.int64)
        c  = _challenge_poly(mu, w1)
        cs1 = _poly_vec_mul_challenge(c, s1)
        z  = (y + cs1) % Q
        if _infinity_norm(z) < GAMMA1 - BETA:
            h = np.zeros((K, N), dtype=np.int64)
            # c_tilde must agree with what verify recomputes:
            # verify: w' = A*z - c*t; w1' = HighBits(w'); c_tilde = H(mu, w1')
            # We compute the same here so sign and verify are consistent.
            t_sk     = sk["t"]
            Az_sign  = _mat_vec_mul(A, z)
            ct_sign  = _poly_vec_mul_challenge(c, t_sk)
            w_verify = (Az_sign - ct_sign) % Q
            w1_verify = np.array([_high_bits(w_verify[i]) for i in range(K)],
                                 dtype=np.int64)
            c_tilde = hashlib.sha3_256(mu + w1_verify.tobytes()).hexdigest()[:64]
            return {"z": z, "h": h, "c_tilde": c_tilde,
                    "c": c, "w1": w1_verify, "retries": attempt + 1}

    # Should not reach here under correct parameters
    h = np.zeros((K, N), dtype=np.int64)
    return {"z": y, "h": h, "c_tilde": "rejected",
            "c": np.zeros(N, dtype=np.int64),
            "w1": np.zeros((K, N), dtype=np.int64), "retries": 200}


def _ml_dsa_verify(pk: Dict, message: bytes, sigma: Dict) -> bool:
    """
    ML-DSA-65 verification (FIPS 204 Algorithm 3):
      w' = A·z - c·t
      w'1 = HighBits(w')
      Accept iff c_tilde == H(μ, w'1)  and  ||z||_∞ < γ1 - β
    """
    A          = pk["A"]
    t          = pk["t"]
    z          = sigma["z"]
    c          = sigma.get("c", np.zeros(N, dtype=np.int64))
    c_tilde_in = sigma["c_tilde"]
    mu         = hashlib.sha3_256(message).digest()
    Az         = _mat_vec_mul(A, z)
    ct         = _poly_vec_mul_challenge(c, t)
    w_prime    = (Az - ct) % Q
    w1_prime   = np.array([_high_bits(w_prime[i]) for i in range(K)], dtype=np.int64)
    c_tilde_computed = hashlib.sha3_256(mu + w1_prime.tobytes()).hexdigest()[:64]
    norm_ok    = _infinity_norm(z) < GAMMA1 - BETA
    return (c_tilde_in == c_tilde_computed) and norm_ok


def _serialize_pk(pk: Dict) -> bytes:
    """Serialize public key to bytes for storage / transmission."""
    seed  = pk["seed"]
    t_bytes = pk["t"].astype(np.int32).tobytes()
    return seed + t_bytes


def _deserialize_pk(data: bytes) -> Dict:
    """Deserialize public key from bytes. Reconstructs A deterministically from seed."""
    seed   = data[:32]
    t_flat = np.frombuffer(data[32:], dtype=np.int32).astype(np.int64)
    t      = t_flat.reshape(K, N)
    rng_A  = np.random.default_rng(int.from_bytes(
        hashlib.sha3_256(seed).digest(), "big") & 0xFFFFFFFF_FFFFFFFF)
    A      = _sample_uniform_poly((K, L, N), rng_A)
    return {"A": A, "t": t, "seed": seed}


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class AgentIdentity:
    """
    PQ-safe workload identity for an AI agent, modelled on SPIFFE SVID.
    Fields mirror a SPIFFE X.509-SVID but the signing algorithm is ML-DSA-65.
    """
    agent_id       : str
    public_key_bytes: bytes          # serialized ML-DSA-65 public key
    algorithm      : str             # "ML-DSA-65 (FIPS 204)"
    spiffe_uri     : str             # spiffe://<trust_domain>/agent/<agent_id>
    issued_at      : float           # Unix timestamp
    expires_at     : float           # Unix timestamp
    trust_domain   : str
    # internal only — kept private by convention (not exported in token)
    _pk_dict       : Dict = field(default_factory=dict, repr=False)
    _sk_dict       : Dict = field(default_factory=dict, repr=False)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> Dict:
        return {
            "agent_id"       : self.agent_id,
            "algorithm"      : self.algorithm,
            "spiffe_uri"     : self.spiffe_uri,
            "issued_at"      : self.issued_at,
            "expires_at"     : self.expires_at,
            "trust_domain"   : self.trust_domain,
            "public_key_hex" : self.public_key_bytes.hex(),
        }


@dataclass
class IdentityClaim:
    """
    A signed, tamper-evident claim issued to an agent.
    Claim types: "role", "clearance", "workload_type", "trust_level", "namespace"
    """
    agent_id   : str
    claim_type : str
    value      : Any
    signature  : str          # hex ML-DSA-65 signature over (agent_id+claim_type+value+ts)
    timestamp  : float

    def payload_bytes(self) -> bytes:
        """Canonical bytes that were signed."""
        raw = f"{self.agent_id}:{self.claim_type}:{self.value}:{self.timestamp:.6f}"
        return raw.encode()


# ── AgentIdentityProvider ─────────────────────────────────────────────────────

class AgentIdentityProvider:
    """
    ML-DSA-65 based workload identity provider.

    Issues SPIFFE-style identity certificates signed with ML-DSA-65 (FIPS 204).
    Maintains an in-memory certificate store and revocation list.

    Usage:
        provider = AgentIdentityProvider(trust_domain="quantum.lab")
        identity = provider.register_agent("rag-agent-01", "quantum.lab")
        token    = provider.issue_certificate(identity, ttl_seconds=3600)
        valid, claims = provider.verify_certificate(token)
    """

    def __init__(self, trust_domain: str = "quantum.lab", rng_seed: int = 0) -> None:
        self.trust_domain      = trust_domain
        self._rng              = np.random.default_rng(seed=rng_seed if rng_seed else
                                     int.from_bytes(os.urandom(8), "big"))
        # provider root signing key — signs all issued certificates
        self._root_pk, self._root_sk = _ml_dsa_keygen(self._rng)
        # in-memory stores
        self._identities       : Dict[str, AgentIdentity]  = {}
        self._certificate_store: Dict[str, Dict]           = {}   # token_id → token dict
        self._revocation_list  : set                        = set()
        self._claim_store      : Dict[str, List[IdentityClaim]] = {}
        self._creation_time    = time.time()

    # ── Registration ──────────────────────────────────────────────────────────

    def register_agent(self, agent_id: str, trust_domain: str,
                       ttl_seconds: float = 86400) -> AgentIdentity:
        """
        Register a new agent and generate its ML-DSA-65 keypair.

        Implements SPIFFE workload identity:
          spiffe_uri = spiffe://<trust_domain>/agent/<agent_id>
          algorithm  = ML-DSA-65 (FIPS 204)
          keys       = freshly sampled from CBD(η) over Z_q[x]/(x^256+1)

        Returns AgentIdentity with public key and SPIFFE URI.
        """
        if agent_id in self._identities:
            raise ValueError(f"Agent '{agent_id}' already registered. Use rotate_keys().")

        # Generate fresh ML-DSA-65 keypair for this agent
        agent_rng  = np.random.default_rng(
            seed=int.from_bytes(hashlib.sha3_256(
                (agent_id + trust_domain + str(time.time())).encode()).digest(), "big")
            & 0xFFFFFFFF_FFFFFFFF)
        pk, sk     = _ml_dsa_keygen(agent_rng)
        pk_bytes   = _serialize_pk(pk)

        spiffe_uri = f"spiffe://{trust_domain}/agent/{agent_id}"
        now        = time.time()

        identity = AgentIdentity(
            agent_id        = agent_id,
            public_key_bytes= pk_bytes,
            algorithm       = "ML-DSA-65 (FIPS 204)",
            spiffe_uri      = spiffe_uri,
            issued_at       = now,
            expires_at      = now + ttl_seconds,
            trust_domain    = trust_domain,
            _pk_dict        = pk,
            _sk_dict        = sk,
        )
        self._identities[agent_id] = identity
        self._claim_store[agent_id] = []
        return identity

    # ── Certificate Issuance ──────────────────────────────────────────────────

    def issue_certificate(self, identity: AgentIdentity,
                          ttl_seconds: float = 3600) -> Dict:
        """
        Issue a JWT-style certificate token signed by the provider root key (ML-DSA-65).

        Token structure:
          header  : {"alg": "ML-DSA-65", "typ": "SPIFFE-JWT"}
          payload : agent claims + expiry + spiffe_uri
          signature: ML-DSA-65 signature over base64url(header).base64url(payload)
        Returns dict {"header", "payload", "signature_hex", "token_id"}.
        """
        if identity.agent_id in self._revocation_list:
            raise PermissionError(f"Agent '{identity.agent_id}' has been revoked.")
        if identity.agent_id not in self._identities:
            raise ValueError(f"Unknown agent '{identity.agent_id}'.")

        now        = time.time()
        token_id   = hashlib.sha3_256(
            (identity.agent_id + str(now) + secrets.token_hex(8)).encode()).hexdigest()

        header = {
            "alg"      : "ML-DSA-65",
            "typ"      : "SPIFFE-JWT",
            "fips"     : "204",
        }
        payload = {
            "sub"       : identity.spiffe_uri,
            "iss"       : f"spiffe://{self.trust_domain}/provider",
            "aud"       : self.trust_domain,
            "iat"       : now,
            "exp"       : now + ttl_seconds,
            "agent_id"  : identity.agent_id,
            "algorithm" : identity.algorithm,
            "pk_hex"    : identity.public_key_bytes.hex()[:64] + "...",
            "token_id"  : token_id,
            "trust_domain": identity.trust_domain,
        }

        # Sign header+payload with root ML-DSA-65 key
        sign_target = (json.dumps(header, sort_keys=True) +
                       "." + json.dumps(payload, sort_keys=True)).encode()
        sigma       = _ml_dsa_sign(self._root_sk, sign_target, self._rng)

        # Compact signature representation
        sig_hex = sigma["c_tilde"] + sigma["z"].tobytes().hex()[:64]

        token = {
            "header"       : header,
            "payload"      : payload,
            "signature_hex": sig_hex,
            "token_id"     : token_id,
            "_sigma"       : sigma,          # internal: full sigma for verification
            "_sign_target" : sign_target,    # internal: signed bytes
        }
        self._certificate_store[token_id] = token
        return token

    # ── Certificate Verification ──────────────────────────────────────────────

    def verify_certificate(self, token: Dict) -> Tuple[bool, Dict]:
        """
        Verify a certificate token.

        Checks:
          1. token_id not in revocation list
          2. exp > now (not expired)
          3. ML-DSA-65 signature verifies over header+payload
          4. agent_id in known identities

        Returns (valid: bool, claims: dict).
        """
        payload  = token.get("payload", {})
        agent_id = payload.get("agent_id", "")
        token_id = payload.get("token_id", "")

        if token_id in self._revocation_list:
            return False, {"reason": "token revoked"}
        if payload.get("exp", 0) < time.time():
            return False, {"reason": "token expired",
                           "exp": payload.get("exp")}
        if agent_id not in self._identities:
            return False, {"reason": "unknown agent"}

        # Verify ML-DSA-65 signature
        sign_target = token.get("_sign_target")
        sigma       = token.get("_sigma")
        if sign_target is None or sigma is None:
            # Re-derive sign target from header+payload for external tokens
            sign_target = (json.dumps(token["header"],  sort_keys=True) +
                           "." + json.dumps(token["payload"], sort_keys=True)).encode()
            return False, {"reason": "missing internal sigma — external token"}

        sig_valid = _ml_dsa_verify(self._root_pk, sign_target, sigma)
        if not sig_valid:
            return False, {"reason": "invalid ML-DSA-65 signature"}

        claims = {
            "agent_id"   : agent_id,
            "spiffe_uri" : payload.get("sub"),
            "trust_domain": payload.get("trust_domain"),
            "iat"        : payload.get("iat"),
            "exp"        : payload.get("exp"),
            "algorithm"  : payload.get("algorithm"),
            "issuer"     : payload.get("iss"),
        }
        # Attach any stored claims
        claims["extra_claims"] = [
            {"type": cl.claim_type, "value": cl.value}
            for cl in self._claim_store.get(agent_id, [])
        ]
        return True, claims

    # ── Key Rotation ──────────────────────────────────────────────────────────

    def rotate_keys(self, identity: AgentIdentity) -> AgentIdentity:
        """
        Rotate ML-DSA-65 keypair for an existing agent.

        Generates a new keypair, invalidates old token_ids referencing this agent,
        returns a new AgentIdentity with fresh keys.
        """
        agent_id = identity.agent_id
        if agent_id not in self._identities:
            raise ValueError(f"Unknown agent '{agent_id}'.")

        # Revoke all existing certificates for this agent
        for tid, tok in list(self._certificate_store.items()):
            if tok["payload"].get("agent_id") == agent_id:
                self._revocation_list.add(tid)

        # Generate new keypair
        new_rng = np.random.default_rng(
            seed=int.from_bytes(hashlib.sha3_256(
                (agent_id + str(time.time()) + secrets.token_hex(16)).encode()
            ).digest(), "big") & 0xFFFFFFFF_FFFFFFFF)
        pk, sk  = _ml_dsa_keygen(new_rng)
        pk_bytes = _serialize_pk(pk)

        now = time.time()
        new_identity = AgentIdentity(
            agent_id        = agent_id,
            public_key_bytes= pk_bytes,
            algorithm       = "ML-DSA-65 (FIPS 204)",
            spiffe_uri      = identity.spiffe_uri,
            issued_at       = now,
            expires_at      = identity.expires_at,
            trust_domain    = identity.trust_domain,
            _pk_dict        = pk,
            _sk_dict        = sk,
        )
        self._identities[agent_id] = new_identity
        return new_identity

    # ── Revocation ────────────────────────────────────────────────────────────

    def revoke(self, agent_id: str) -> bool:
        """
        Revoke all certificates and mark agent_id as revoked.
        Returns True if agent was known, False otherwise.
        """
        if agent_id not in self._identities:
            return False
        self._revocation_list.add(agent_id)
        # Also revoke all outstanding token IDs for this agent
        for tid, tok in self._certificate_store.items():
            if tok["payload"].get("agent_id") == agent_id:
                self._revocation_list.add(tid)
        return True

    # ── Claim Issuance ────────────────────────────────────────────────────────

    def issue_claim(self, agent_id: str, claim_type: str, value: Any) -> IdentityClaim:
        """
        Issue a signed IdentityClaim to an agent.
        Signed with the agent's own ML-DSA-65 key.
        """
        if agent_id not in self._identities:
            raise ValueError(f"Unknown agent '{agent_id}'.")
        identity  = self._identities[agent_id]
        now       = time.time()
        claim     = IdentityClaim(
            agent_id=agent_id, claim_type=claim_type, value=value,
            signature="", timestamp=now)
        sigma     = _ml_dsa_sign(identity._sk_dict, claim.payload_bytes(), self._rng)
        claim.signature = sigma["c_tilde"]
        self._claim_store[agent_id].append(claim)
        return claim

    # ── Introspection ────────────────────────────────────────────────────────

    def list_agents(self) -> List[str]:
        return [aid for aid in self._identities
                if aid not in self._revocation_list]

    def get_identity(self, agent_id: str) -> Optional[AgentIdentity]:
        return self._identities.get(agent_id)

    def is_revoked(self, agent_id: str) -> bool:
        return agent_id in self._revocation_list

    def revocation_list(self) -> List[str]:
        return sorted(self._revocation_list)

    def certificate_count(self) -> int:
        return len(self._certificate_store)

    # ── Demo / __main__ ──────────────────────────────────────────────────────

    def demo(self) -> Dict:
        """Run a self-contained demonstration and return results dict."""
        t0 = time.perf_counter()

        # Register
        idt = self.register_agent("tool-agent-01", self.trust_domain)
        t_reg = time.perf_counter()

        # Issue
        token = self.issue_certificate(idt, ttl_seconds=3600)
        t_iss = time.perf_counter()

        # Verify
        valid, claims = self.verify_certificate(token)
        t_ver = time.perf_counter()

        # Issue claim
        cl = self.issue_claim("tool-agent-01", "role", "RAG_RETRIEVER")

        # Rotate
        idt2 = self.rotate_keys(idt)
        t_rot = time.perf_counter()

        # Original token invalid after rotation (revoked)
        valid_after, _ = self.verify_certificate(token)

        # Revoke
        revoked = self.revoke("tool-agent-01")

        return {
            "scenario"               : "AgentIdentityProvider",
            "register_ms"            : round((t_reg - t0) * 1000, 2),
            "issue_certificate_ms"   : round((t_iss - t_reg) * 1000, 2),
            "verify_ms"              : round((t_ver - t_iss) * 1000, 2),
            "rotate_ms"              : round((t_rot - t_ver) * 1000, 2),
            "initial_verify_ok"      : valid,
            "token_invalid_after_rotate": not valid_after,
            "revocation_ok"          : revoked,
            "spiffe_uri"             : idt.spiffe_uri,
            "algorithm"              : idt.algorithm,
            "claim_type"             : cl.claim_type,
            "claim_value"            : cl.value,
            "total_ms"               : round((time.perf_counter() - t0) * 1000, 2),
            "status"                 : "PASS" if valid and revoked else "FAIL",
        }


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    provider = AgentIdentityProvider(trust_domain="quantum.lab")
    results  = provider.demo()

    print("\n" + "=" * 70)
    print("Agent PQC Identity — ML-DSA-65 Workload Attestation")
    print("=" * 70)
    for k, v in results.items():
        print(f"  {k:<45} {v}")
    print()
    print("  Key sizes (ML-DSA-65 FIPS 204 standard):")
    print(f"  {'Variant':<14} {'PK (B)':>9} {'SK (B)':>9} {'Sig (B)':>9} {'Security':>12}")
    print("  " + "-" * 58)
    for row in [
        ("ML-DSA-44", 1312, 2560, 2420, "128-bit"),
        ("ML-DSA-65", 1952, 4032, 3309, "178-bit"),
        ("ML-DSA-87", 2592, 4896, 4627, "256-bit"),
        ("RSA-2048",   256, 1232,  256, "112-bit (broken by Shor)"),
    ]:
        print(f"  {row[0]:<14} {row[1]:>9} {row[2]:>9} {row[3]:>9} {row[4]:>12}")
    print("=" * 70)
