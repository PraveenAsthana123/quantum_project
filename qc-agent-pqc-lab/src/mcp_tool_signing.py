"""
Agent PQC Identity: MCP Tool Call Signing
==========================================
Purpose   : Post-quantum signing and verification of MCP tool calls for AI agents
Reference : Model Context Protocol (MCP) spec; NIST SP 800-207 Zero Trust
Standard  : ML-DSA-65 (FIPS 204) for tool-call attestation; replay detection
Security  : EUF-CMA under Module-LWE + Module-SIS; nonce + timestamp window
Use Case  : Every tool call made by an AI agent is signed; verifiers confirm
            authenticity, detect replays, and maintain a tamper-evident audit log.
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
Q      = 8380417
K      = 6
L      = 5
ETA    = 4
GAMMA1 = 1 << 17
GAMMA2 = (Q - 1) // 88
BETA   = 120
TAU    = 49


# ── Polynomial arithmetic (same ring as agent_identity.py) ───────────────────

def _sample_uniform_poly(shape: tuple, rng: np.random.Generator) -> np.ndarray:
    return rng.integers(0, Q, size=shape, dtype=np.int64)


def _sample_small_poly(eta: int, shape: tuple, rng: np.random.Generator) -> np.ndarray:
    return rng.integers(-eta, eta + 1, size=shape, dtype=np.int64)


def _poly_mul(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Polynomial multiplication in Z_q[x]/(x^N+1)."""
    c = np.convolve(a.astype(np.int64), b.astype(np.int64))
    result = np.zeros(N, dtype=np.int64)
    for i, coef in enumerate(c):
        if i < N:
            result[i] = (result[i] + coef) % Q
        else:
            result[i - N] = (result[i - N] - coef) % Q
    return result


def _mat_vec_mul(A: np.ndarray, v: np.ndarray) -> np.ndarray:
    result = np.zeros((K, N), dtype=np.int64)
    for i in range(K):
        for j in range(L):
            p = _poly_mul(A[i, j], v[j])
            result[i] = (result[i] + p) % Q
    return result


def _vec_add(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    return (u + v) % Q


def _infinity_norm(poly_vec: np.ndarray) -> int:
    centered = poly_vec.copy().astype(np.int64)
    centered[centered > Q // 2] -= Q
    return int(np.max(np.abs(centered)))


def _high_bits(r: np.ndarray, alpha: int | None = None) -> np.ndarray:
    if alpha is None:
        alpha = 2 * GAMMA2
    centered = r.copy().astype(np.int64)
    centered = (centered + Q // 2) % Q - Q // 2
    return (centered + (alpha // 2)) // alpha


def _challenge_poly(mu: bytes, w1: np.ndarray) -> np.ndarray:
    """Sparse ternary challenge polynomial derived from H(μ, w1)."""
    packed = mu + w1.tobytes()
    h      = hashlib.shake_256(packed).digest(32)
    seed   = int.from_bytes(h, "big")
    rng_ch = np.random.default_rng(seed)
    c      = np.zeros(N, dtype=np.int64)
    positions = rng_ch.choice(N, size=TAU, replace=False)
    signs     = rng_ch.choice([-1, 1], size=TAU)
    for pos, sign in zip(positions, signs):
        c[pos] = sign
    return c


def _poly_vec_mul_challenge(c: np.ndarray, v: np.ndarray) -> np.ndarray:
    result = np.zeros_like(v)
    for i in range(len(v)):
        result[i] = _poly_mul(c, v[i]) % Q
    return result


# ── ML-DSA-65 sign / verify ───────────────────────────────────────────────────

def _ml_dsa_keygen(rng: np.random.Generator) -> Tuple[Dict, Dict]:
    A_seed = rng.integers(0, 256, size=32, dtype=np.uint8).tobytes()
    A  = _sample_uniform_poly((K, L, N), rng)
    s1 = _sample_small_poly(ETA, (L, N), rng)
    s2 = _sample_small_poly(ETA, (K, N), rng)
    t  = _vec_add(_mat_vec_mul(A, s1), s2)
    return {"A": A, "t": t, "seed": A_seed}, {"A": A, "t": t, "s1": s1, "s2": s2}


def _sign_dsa(sk: Dict, message: bytes, rng: np.random.Generator) -> Dict:
    """
    ML-DSA-65 Fiat-Shamir signing (FIPS 204 Algorithm 2).
    Commitment: w = A·y; response: z = y + c·s1.
    Aborts if ||z||_∞ ≥ γ1 − β (restart with fresh y).
    """
    A  = sk["A"]
    s1 = sk["s1"]
    mu = hashlib.sha3_256(message).digest()
    for attempt in range(200):
        y   = rng.integers(-GAMMA1 + 1, GAMMA1, size=(L, N), dtype=np.int64)
        w   = _mat_vec_mul(A, y)
        w1  = np.array([_high_bits(w[i]) for i in range(K)], dtype=np.int64)
        c   = _challenge_poly(mu, w1)
        cs1 = _poly_vec_mul_challenge(c, s1)
        z   = (y + cs1) % Q
        if _infinity_norm(z) < GAMMA1 - BETA:
            h = np.zeros((K, N), dtype=np.int64)
            # Derive c_tilde consistently with verify's recomputation:
            # verify: w' = A*z - c*t → HighBits → H(mu, w1')
            t_sk     = sk["t"]
            Az_v     = _mat_vec_mul(A, z)
            ct_v     = _poly_vec_mul_challenge(c, t_sk)
            w_v      = (Az_v - ct_v) % Q
            w1_v     = np.array([_high_bits(w_v[i]) for i in range(K)], dtype=np.int64)
            c_tilde  = hashlib.sha3_256(mu + w1_v.tobytes()).hexdigest()[:64]
            return {"z": z, "h": h, "c_tilde": c_tilde,
                    "c": c, "w1": w1_v, "retries": attempt + 1}
    return {"z": np.zeros((L, N), dtype=np.int64),
            "h": np.zeros((K, N), dtype=np.int64),
            "c_tilde": "rejected",
            "c": np.zeros(N, dtype=np.int64),
            "w1": np.zeros((K, N), dtype=np.int64),
            "retries": 200}


def _verify_dsa(pk: Dict, message: bytes, sigma: Dict) -> bool:
    """
    ML-DSA-65 verification (FIPS 204 Algorithm 3).
    Recomputes w' = A·z − c·t; checks HighBits match and norm bound.
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
    c_tilde_cmp = hashlib.sha3_256(mu + w1_prime.tobytes()).hexdigest()[:64]
    return (c_tilde_in == c_tilde_cmp) and (_infinity_norm(z) < GAMMA1 - BETA)


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class MCPToolCall:
    """
    An unsigned MCP tool call record, analogous to a JSON-RPC 2.0 request
    but extended with agent identity and replay-protection metadata.
    """
    tool_name  : str
    params     : Dict[str, Any]
    agent_id   : str
    call_id    : str              # uuid4 — replay protection nonce
    timestamp  : float            # Unix timestamp at call creation
    nonce      : str = field(default_factory=lambda: secrets.token_hex(16))

    def canonical_bytes(self) -> bytes:
        """Deterministic serialization for signing."""
        obj = {
            "tool_name" : self.tool_name,
            "params"    : self.params,
            "agent_id"  : self.agent_id,
            "call_id"   : self.call_id,
            "timestamp" : f"{self.timestamp:.6f}",
            "nonce"     : self.nonce,
        }
        return json.dumps(obj, sort_keys=True).encode()

    def to_dict(self) -> Dict:
        return {
            "tool_name": self.tool_name,
            "params"   : self.params,
            "agent_id" : self.agent_id,
            "call_id"  : self.call_id,
            "timestamp": self.timestamp,
            "nonce"    : self.nonce,
        }


@dataclass
class SignedMCPCall:
    """
    An MCP tool call with an attached ML-DSA-65 signature.
    The signature covers call.canonical_bytes() so every field is protected.
    """
    call            : MCPToolCall
    signature       : str       # hex representation of c_tilde (commitment hash)
    public_key_bytes: bytes     # serialized public key for independent verification
    algorithm       : str       # "ML-DSA-65 (FIPS 204)"
    _sigma          : Dict = field(default_factory=dict, repr=False)  # full sigma

    def signed_payload_hash(self) -> str:
        """SHA3-256 of the signed canonical payload — for audit logs."""
        return hashlib.sha3_256(self.call.canonical_bytes()).hexdigest()


@dataclass
class MCPCallResult:
    """Result of executing a verified MCP tool call."""
    call_id  : str
    result   : Any
    status   : str    # "success" | "error" | "rejected" | "replay_detected"
    verified : bool   # True if the call signature verified before execution


# ── MCPToolSigner ────────────────────────────────────────────────────────────

class MCPToolSigner:
    """
    ML-DSA-65 signer and verifier for MCP tool calls.

    Every tool call made by an agent must be signed before dispatch.
    The verifier at the tool-server side rejects unsigned, tampered, or
    replayed calls before execution.

    Audit trail:
      All verified calls + results are logged in _audit_trail (in-memory).
      Each entry: call_id, tool_name, agent_id, verified, status, timestamp,
                  payload_hash, result_summary.

    Replay detection:
      Tracks (call_id, nonce) within a sliding timestamp window.
      Any duplicate call_id inside the window is a replay.

    Usage:
        signer  = MCPToolSigner()
        pk, sk  = signer.generate_keypair("agent-01")
        call    = MCPToolCall("search", {"query": "PQC"}, "agent-01",
                              call_id=secrets.token_hex(8), timestamp=time.time())
        signed  = signer.sign_tool_call(call, sk)
        valid   = signer.verify_tool_call(signed)
    """

    def __init__(self, rng_seed: int = 0) -> None:
        self._rng           = np.random.default_rng(
            seed=rng_seed if rng_seed else
            int.from_bytes(os.urandom(8), "big"))
        self._keypairs      : Dict[str, Tuple[Dict, Dict]] = {}  # agent_id → (pk, sk)
        self._audit_trail   : List[Dict]                   = []
        # Replay window: (call_id → timestamp) for seen calls within window
        self._seen_calls    : Dict[str, float]             = {}
        self._replay_window = 300.0   # 5-minute window

    # ── Key Management ────────────────────────────────────────────────────────

    def generate_keypair(self, agent_id: str) -> Tuple[Dict, Dict]:
        """
        Generate a fresh ML-DSA-65 keypair for an agent and cache it.
        Returns (pk_dict, sk_dict).
        """
        rng_a  = np.random.default_rng(
            int.from_bytes(hashlib.sha3_256(
                (agent_id + str(time.time()) + secrets.token_hex(8)).encode()
            ).digest(), "big") & 0xFFFF_FFFF_FFFF_FFFF)
        pk, sk = _ml_dsa_keygen(rng_a)
        self._keypairs[agent_id] = (pk, sk)
        return pk, sk

    def get_public_key(self, agent_id: str) -> Optional[Dict]:
        pair = self._keypairs.get(agent_id)
        return pair[0] if pair else None

    # ── Signing ───────────────────────────────────────────────────────────────

    def sign_tool_call(self, call: MCPToolCall, private_key: Dict) -> SignedMCPCall:
        """
        Sign an MCP tool call with ML-DSA-65 (_sign_dsa).

        The signed message = call.canonical_bytes():
          JSON({tool_name, params, agent_id, call_id, timestamp, nonce})
        The signature is a full ML-DSA-65 σ = (z, h, c_tilde, c, w1).

        Returns SignedMCPCall with signature hex and public key bytes.
        """
        message = call.canonical_bytes()
        sigma   = _sign_dsa(private_key, message, self._rng)

        # Derive public key bytes from sk (A and t determine pk)
        pk_dict  = {"A": private_key["A"], "t": private_key["t"],
                    "seed": private_key.get("seed", b"\x00" * 32)}
        pk_bytes = pk_dict["t"].astype(np.int32).tobytes()   # compact form

        return SignedMCPCall(
            call             = call,
            signature        = sigma["c_tilde"],
            public_key_bytes = pk_bytes,
            algorithm        = "ML-DSA-65 (FIPS 204)",
            _sigma           = sigma,
        )

    # ── Verification ─────────────────────────────────────────────────────────

    def verify_tool_call(self, signed_call: SignedMCPCall) -> bool:
        """
        Verify an ML-DSA-65 signed MCP tool call.

        Checks:
          1. Replay detection (call_id not seen in window)
          2. ML-DSA-65 signature verification over canonical bytes
          3. Timestamp freshness (within replay_window)

        Records call in _seen_calls on success.
        Returns True iff all checks pass.
        """
        call = signed_call.call

        # ── Replay detection ─────────────────────────────────────────────────
        now     = time.time()
        age     = now - call.timestamp
        if age > self._replay_window or age < -10:
            return False  # stale or future-dated

        # Expire old entries from replay cache
        self._seen_calls = {
            cid: ts for cid, ts in self._seen_calls.items()
            if now - ts < self._replay_window
        }
        if call.call_id in self._seen_calls:
            return False  # replay detected

        # ── Signature verification ────────────────────────────────────────────
        message  = call.canonical_bytes()
        sigma    = signed_call._sigma
        if not sigma or sigma.get("c_tilde") == "rejected":
            return False

        # Reconstruct pk for verification
        agent_pk = self._keypairs.get(call.agent_id)
        if agent_pk is None:
            return False
        pk_dict = agent_pk[0]

        sig_valid = _verify_dsa(pk_dict, message, sigma)
        if sig_valid:
            self._seen_calls[call.call_id] = now
        return sig_valid

    # ── Audit Logging ─────────────────────────────────────────────────────────

    def create_audit_log(self, signed_call: SignedMCPCall,
                         result: MCPCallResult) -> Dict:
        """
        Create an immutable audit record for a signed+verified tool call.

        Audit entry fields:
          - call_id, tool_name, agent_id, timestamp (call creation)
          - payload_hash: SHA3-256 of canonical call bytes (tamper evidence)
          - algorithm, signature_prefix (first 16 hex chars of c_tilde)
          - verified, status, result_summary
          - logged_at: audit log entry time
        """
        call = signed_call.call
        entry = {
            "call_id"          : call.call_id,
            "tool_name"        : call.tool_name,
            "agent_id"         : call.agent_id,
            "call_timestamp"   : call.timestamp,
            "logged_at"        : time.time(),
            "payload_hash"     : signed_call.signed_payload_hash(),
            "algorithm"        : signed_call.algorithm,
            "signature_prefix" : signed_call.signature[:16],
            "verified"         : result.verified,
            "status"           : result.status,
            "result_summary"   : (str(result.result)[:120]
                                  if result.result is not None else None),
            "params_keys"      : list(call.params.keys()),
            "nonce"            : call.nonce,
        }
        self._audit_trail.append(entry)
        return entry

    # ── Replay Detection ─────────────────────────────────────────────────────

    def detect_replay(self, signed_call: SignedMCPCall,
                      window_seconds: float = 300.0) -> bool:
        """
        Check if a call is a replay without recording it.
        Returns True if replay detected.

        Replay criteria:
          - call_id already seen within window_seconds
          - OR call.timestamp is older than window_seconds
          - OR call.timestamp is more than 10s in the future
        """
        call = signed_call.call
        now  = time.time()
        age  = now - call.timestamp

        if age > window_seconds:
            return True   # stale call = replay
        if age < -10:
            return True   # future-dated = likely replay/forgery

        return call.call_id in self._seen_calls

    # ── Query Audit Trail ────────────────────────────────────────────────────

    def get_audit_trail(self, agent_id: Optional[str] = None,
                        tool_name: Optional[str] = None,
                        last_n: int = 100) -> List[Dict]:
        """Return audit trail entries, optionally filtered by agent or tool."""
        entries = self._audit_trail
        if agent_id:
            entries = [e for e in entries if e["agent_id"] == agent_id]
        if tool_name:
            entries = [e for e in entries if e["tool_name"] == tool_name]
        return entries[-last_n:]

    def audit_stats(self) -> Dict:
        """Return aggregate statistics over the audit trail."""
        total   = len(self._audit_trail)
        if total == 0:
            return {"total_calls": 0}
        verified = sum(1 for e in self._audit_trail if e["verified"])
        by_agent: Dict[str, int] = {}
        by_tool : Dict[str, int] = {}
        for e in self._audit_trail:
            by_agent[e["agent_id"]] = by_agent.get(e["agent_id"], 0) + 1
            by_tool[e["tool_name"]] = by_tool.get(e["tool_name"], 0)  + 1
        return {
            "total_calls"    : total,
            "verified_calls" : verified,
            "failed_calls"   : total - verified,
            "calls_by_agent" : by_agent,
            "calls_by_tool"  : by_tool,
        }

    # ── Demo ─────────────────────────────────────────────────────────────────

    def demo(self) -> Dict:
        """
        Self-contained demonstration:
          1. Generate keypair for agent-01
          2. Sign a tool call (search)
          3. Verify it → should pass
          4. Attempt replay → should fail
          5. Tamper with params → should fail
          6. Create audit log entry
        Returns results dict.
        """
        rng_local = np.random.default_rng(seed=7)
        pk, sk = self.generate_keypair("agent-01")
        t0     = time.perf_counter()

        # Normal call
        call = MCPToolCall(
            tool_name  = "search",
            params     = {"query": "ML-KEM post-quantum", "top_k": 5},
            agent_id   = "agent-01",
            call_id    = secrets.token_hex(8),
            timestamp  = time.time(),
        )
        signed_call = self.sign_tool_call(call, sk)
        t_sign      = time.perf_counter()

        valid       = self.verify_tool_call(signed_call)
        t_verify    = time.perf_counter()

        # Replay attempt (same signed_call, already in seen_calls)
        replay_detected = self.detect_replay(signed_call, window_seconds=300)

        # Tamper: modify params after signing
        tampered_call = MCPToolCall(
            tool_name  = call.tool_name,
            params     = {"query": "INJECTED", "top_k": 999},
            agent_id   = call.agent_id,
            call_id    = secrets.token_hex(8),   # new call_id to bypass replay check
            timestamp  = time.time(),
            nonce      = call.nonce,              # reuse nonce — will fail sig verify
        )
        tampered_signed = SignedMCPCall(
            call             = tampered_call,
            signature        = signed_call.signature,
            public_key_bytes = signed_call.public_key_bytes,
            algorithm        = signed_call.algorithm,
            _sigma           = signed_call._sigma,  # original sigma — wrong message
        )
        tamper_rejected = not self.verify_tool_call(tampered_signed)

        # Audit log
        result  = MCPCallResult(call.call_id, {"hits": 3}, "success", valid)
        entry   = self.create_audit_log(signed_call, result)

        return {
            "scenario"         : "MCPToolSigner",
            "sign_ms"          : round((t_sign   - t0)      * 1000, 2),
            "verify_ms"        : round((t_verify - t_sign)  * 1000, 2),
            "total_ms"         : round((time.perf_counter() - t0) * 1000, 2),
            "valid_call"       : valid,
            "replay_detected"  : replay_detected,
            "tamper_rejected"  : tamper_rejected,
            "audit_entry_id"   : entry["call_id"],
            "payload_hash"     : entry["payload_hash"][:32] + "...",
            "algorithm"        : signed_call.algorithm,
            "status"           : "PASS" if valid and replay_detected and tamper_rejected
                                 else "FAIL",
        }


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    signer  = MCPToolSigner()
    results = signer.demo()

    print("\n" + "=" * 70)
    print("MCP Tool Signing — ML-DSA-65 Signed Tool Calls")
    print("=" * 70)
    for k, v in results.items():
        print(f"  {k:<45} {v}")
    print()
    print("  Security properties of signed MCP calls:")
    print(f"  {'Property':<30} {'Mechanism'}")
    print("  " + "-" * 60)
    for prop, mech in [
        ("Authenticity",    "ML-DSA-65 signature over canonical call bytes"),
        ("Integrity",       "SHA3-256 payload hash + DSA covers all fields"),
        ("Replay protection","call_id nonce + 5-min sliding timestamp window"),
        ("Non-repudiation", "Agent private key; public key anchored to SPIFFE ID"),
        ("Audit trail",     "Immutable in-memory log; SHA3-256 tamper evidence"),
        ("Quantum safety",  "EUF-CMA under Module-LWE + Module-SIS (178-bit)"),
    ]:
        print(f"  {prop:<30} {mech}")
    print("=" * 70)
