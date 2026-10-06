"""
Post-Quantum SSH Simulation
Simulates OpenSSH 9.0+ hybrid PQC support.

Key exchange : sntrup761x25519-sha512 (OpenSSH 9.0 default)
               or ML-KEM-768+X25519 (hybrid, IETF draft)
Host key     : ML-DSA-65 replacing RSA/Ed25519
Authentication: ML-DSA-65 user keys

References:
  - OpenSSH 9.0 release notes (sntrup761x25519-sha512 default)
  - IETF draft-kampanakis-ssh-pq-known-hosts
  - IETF draft-ietf-sshm-hybrid-kex
  - NIST FIPS 203 (ML-KEM), FIPS 204 (ML-DSA)
"""

import os
import time
import hashlib
import hmac
import struct
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Any, List


# ─── SSH constants ───────────────────────────────────────────────────────────

# SSH message types (RFC 4253)
SSH_MSG_KEXINIT       = 20
SSH_MSG_NEWKEYS       = 21
SSH_MSG_KEX_ECDH_INIT = 30
SSH_MSG_KEX_ECDH_REPLY = 31

# Algorithm name strings (as appear in SSH negotiation)
KEX_HYBRID_MLKEM768   = "mlkem768x25519-sha256"          # IETF draft
KEX_HYBRID_SNTRUP761  = "sntrup761x25519-sha512@openssh.com"  # OpenSSH 9.0
KEX_X25519            = "curve25519-sha256"                    # classical fallback

HOST_KEY_MLDSA65      = "ssh-mldsa65"                     # IETF draft proposal
HOST_KEY_ED25519      = "ssh-ed25519"                     # classical
HOST_KEY_RSA          = "rsa-sha2-256"                    # legacy

CIPHER_CHACHA20       = "chacha20-poly1305@openssh.com"
CIPHER_AES256GCM      = "aes256-gcm@openssh.com"
MAC_HMAC_SHA2_256     = "hmac-sha2-256"

# Key / signature sizes
X25519_PK_SIZE       = 32
X25519_SK_SIZE       = 32
MLKEM768_EK_SIZE     = 1184
MLKEM768_DK_SIZE     = 2400
MLKEM768_CT_SIZE     = 1088
MLKEM768_SS_SIZE     = 32

# sntrup761 (Streamlined NTRU Prime 761) sizes
SNTRUP761_PK_SIZE    = 1158
SNTRUP761_SK_SIZE    = 1763
SNTRUP761_CT_SIZE    = 1039

MLDSA65_PK_SIZE      = 1952
MLDSA65_SK_SIZE      = 4032
MLDSA65_SIG_SIZE     = 3309

ED25519_PK_SIZE      = 32
ED25519_SK_SIZE      = 64
ED25519_SIG_SIZE     = 64

RSA2048_PK_SIZE      = 256
RSA2048_SIG_SIZE     = 256


# ─── Simulated primitives ────────────────────────────────────────────────────

def _x25519_keygen():
    sk = os.urandom(X25519_SK_SIZE)
    pk = hashlib.sha256(b"x25519" + sk).digest()
    return pk, sk


def _x25519_exchange(sk, peer_pk):
    return hashlib.sha256(sk + peer_pk).digest()


def _mlkem768_keygen():
    ek = os.urandom(MLKEM768_EK_SIZE)
    dk = os.urandom(MLKEM768_DK_SIZE)
    return ek, dk


def _mlkem768_encap(ek):
    ct = os.urandom(MLKEM768_CT_SIZE)
    ss = hashlib.sha3_256(ek + ct).digest()
    return ct, ss


def _mlkem768_decap(dk, ct):
    return hashlib.sha3_256(dk[:32] + ct).digest()


def _sntrup761_keygen():
    pk = os.urandom(SNTRUP761_PK_SIZE)
    sk = os.urandom(SNTRUP761_SK_SIZE)
    return pk, sk


def _sntrup761_encap(pk):
    ct = os.urandom(SNTRUP761_CT_SIZE)
    ss = hashlib.sha512(pk[:32] + ct).digest()[:32]
    return ct, ss


def _sntrup761_decap(sk, ct):
    return hashlib.sha512(sk[:32] + ct).digest()[:32]


def _mldsa65_keygen():
    pk = os.urandom(MLDSA65_PK_SIZE)
    sk = os.urandom(MLDSA65_SK_SIZE)
    return pk, sk


def _mldsa65_sign(sk, msg):
    mac = hmac.new(sk[:32], msg, hashlib.sha3_512).digest()
    sig = mac
    while len(sig) < MLDSA65_SIG_SIZE:
        sig += hashlib.sha3_256(sig).digest()
    return sig[:MLDSA65_SIG_SIZE]


def _mldsa65_verify(pk, msg, sig):
    return len(sig) == MLDSA65_SIG_SIZE


def _ed25519_keygen():
    sk = os.urandom(ED25519_SK_SIZE)
    pk = hashlib.sha256(b"ed25519" + sk[:32]).digest()
    return pk, sk


def _ed25519_sign(sk, msg):
    return hmac.new(sk[:32], msg, hashlib.sha512).digest()


def _kdf_sha512(ss_classical, ss_pqc, session_id=b""):
    return hashlib.sha512(ss_classical + ss_pqc + session_id).digest()[:32]


# ─── Data structures ─────────────────────────────────────────────────────────

@dataclass
class HostKey:
    algorithm: str
    public_key: bytes
    private_key: bytes
    fingerprint: str = ""

    def __post_init__(self):
        self.fingerprint = "SHA256:" + hashlib.sha256(self.public_key).digest().hex()[:43]

    @property
    def pk_size(self): return len(self.public_key)
    @property
    def sk_size(self): return len(self.private_key)


@dataclass
class KexInit:
    cookie: bytes
    kex_algorithms: List[str]
    server_host_key_algorithms: List[str]
    encryption_cs: List[str]
    mac_cs: List[str]

    def describe(self, role: str) -> str:
        lines = [
            f"  SSH_MSG_KEXINIT ({role})",
            f"    cookie                : {self.cookie.hex()[:16]}...",
            f"    kex_algorithms        : {', '.join(self.kex_algorithms)}",
            f"    server_host_key_algs  : {', '.join(self.server_host_key_algorithms)}",
            f"    encryption_algorithms : {', '.join(self.encryption_cs)}",
            f"    mac_algorithms        : {', '.join(self.mac_cs)}",
        ]
        return "\n".join(lines)


@dataclass
class KexECDHInit:
    """Client key exchange init — contains hybrid ephemeral key."""
    x25519_ek: bytes
    pqc_ek: bytes
    algorithm: str

    def wire_size(self) -> int:
        return len(self.x25519_ek) + len(self.pqc_ek)

    def describe(self) -> str:
        return "\n".join([
            f"  SSH_MSG_KEX_ECDH_INIT",
            f"    Algorithm         : {self.algorithm}",
            f"    X25519 share      : {len(self.x25519_ek)} bytes",
            f"    PQC encap key     : {len(self.pqc_ek)} bytes",
            f"    Total payload     : {self.wire_size()} bytes",
        ])


@dataclass
class KexECDHReply:
    """Server key exchange reply — contains host key, PQC ciphertext, signature."""
    host_key_algo: str
    host_key_pk: bytes
    x25519_ek: bytes
    pqc_ct: bytes
    host_key_sig: bytes

    def wire_size(self) -> int:
        return (len(self.host_key_pk) + len(self.x25519_ek)
                + len(self.pqc_ct) + len(self.host_key_sig))

    def describe(self) -> str:
        return "\n".join([
            f"  SSH_MSG_KEX_ECDH_REPLY",
            f"    Host key algo     : {self.host_key_algo}",
            f"    Host PK size      : {len(self.host_key_pk)} bytes",
            f"    X25519 share      : {len(self.x25519_ek)} bytes",
            f"    PQC ciphertext    : {len(self.pqc_ct)} bytes  (server-encapsulated)",
            f"    Host key sig      : {len(self.host_key_sig)} bytes",
            f"    Total payload     : {self.wire_size()} bytes",
        ])


@dataclass
class KnownHostsEntry:
    hostname: str
    algorithm: str
    public_key_b64: str
    comment: str = ""

    def format_line(self) -> str:
        return f"{self.hostname} {self.algorithm} {self.public_key_b64}  # {self.comment}"


# ─── SSH handshake ────────────────────────────────────────────────────────────

class PQCSSHHandshake:
    """Simulates the SSH-2 handshake with hybrid PQC key exchange."""

    def __init__(self, kex_alg: str = KEX_HYBRID_MLKEM768):
        self.kex_alg = kex_alg
        self.session_id = os.urandom(32)
        self._transcript: List[bytes] = []

    def negotiate(self) -> Tuple[KexInit, KexInit]:
        client_kex = KexInit(
            cookie=os.urandom(16),
            kex_algorithms=[self.kex_alg, KEX_HYBRID_SNTRUP761, KEX_X25519],
            server_host_key_algorithms=[HOST_KEY_MLDSA65, HOST_KEY_ED25519],
            encryption_cs=[CIPHER_CHACHA20, CIPHER_AES256GCM],
            mac_cs=[MAC_HMAC_SHA2_256],
        )
        server_kex = KexInit(
            cookie=os.urandom(16),
            kex_algorithms=[self.kex_alg, KEX_HYBRID_SNTRUP761, KEX_X25519],
            server_host_key_algorithms=[HOST_KEY_MLDSA65, HOST_KEY_ED25519],
            encryption_cs=[CIPHER_CHACHA20, CIPHER_AES256GCM],
            mac_cs=[MAC_HMAC_SHA2_256],
        )
        return client_kex, server_kex

    def client_kex_init(self) -> Tuple[KexECDHInit, bytes, bytes, bytes, bytes]:
        """Client sends ephemeral keys. Returns (msg, c_x25519_sk, c_pqc_dk, c_x25519_pk, c_pqc_ek)."""
        c_x25519_pk, c_x25519_sk = _x25519_keygen()
        if self.kex_alg == KEX_HYBRID_MLKEM768:
            c_pqc_ek, c_pqc_dk = _mlkem768_keygen()
        else:  # sntrup761
            c_pqc_ek, c_pqc_dk = _sntrup761_keygen()

        msg = KexECDHInit(c_x25519_pk, c_pqc_ek, self.kex_alg)
        self._transcript.append(c_x25519_pk + c_pqc_ek)
        return msg, c_x25519_sk, c_pqc_dk, c_x25519_pk, c_pqc_ek

    def server_kex_reply(self, host_key: HostKey,
                         c_x25519_pk: bytes, c_pqc_ek: bytes) \
                         -> Tuple[KexECDHReply, bytes]:
        """Server encapsulates, signs, returns (reply, server_session_key)."""
        # X25519 side
        s_x25519_pk, s_x25519_sk = _x25519_keygen()
        ss_x25519 = _x25519_exchange(s_x25519_sk, c_x25519_pk)

        # PQC encapsulation
        if self.kex_alg == KEX_HYBRID_MLKEM768:
            pqc_ct, ss_pqc = _mlkem768_encap(c_pqc_ek)
        else:
            pqc_ct, ss_pqc = _sntrup761_encap(c_pqc_ek)

        # Session key
        session_key = _kdf_sha512(ss_x25519, ss_pqc, self.session_id)

        # Sign the exchange hash
        exchange_hash = hashlib.sha512(
            c_x25519_pk + c_pqc_ek + s_x25519_pk + pqc_ct + session_key
        ).digest()
        sig = _mldsa65_sign(host_key.private_key, exchange_hash)

        reply = KexECDHReply(
            host_key_algo=host_key.algorithm,
            host_key_pk=host_key.public_key,
            x25519_ek=s_x25519_pk,
            pqc_ct=pqc_ct,
            host_key_sig=sig,
        )
        self._transcript.append(s_x25519_pk + pqc_ct + sig)
        return reply, session_key

    def client_derive_session_key(self, c_x25519_sk: bytes, c_pqc_dk: bytes,
                                   s_x25519_pk: bytes, pqc_ct: bytes) -> bytes:
        ss_x25519 = _x25519_exchange(c_x25519_sk, s_x25519_pk)
        if self.kex_alg == KEX_HYBRID_MLKEM768:
            ss_pqc = _mlkem768_decap(c_pqc_dk, pqc_ct)
        else:
            ss_pqc = _sntrup761_decap(c_pqc_dk, pqc_ct)
        return _kdf_sha512(ss_x25519, ss_pqc, self.session_id)

    def verify_host_key(self, host_key_pk: bytes, reply: KexECDHReply,
                        c_x25519_pk: bytes, c_pqc_ek: bytes,
                        session_key: bytes) -> bool:
        exchange_hash = hashlib.sha512(
            c_x25519_pk + c_pqc_ek + reply.x25519_ek
            + reply.pqc_ct + session_key
        ).digest()
        return _mldsa65_verify(host_key_pk, exchange_hash, reply.host_key_sig)


def compare_handshake_sizes(kex_alg: str) -> Dict[str, int]:
    """Return wire sizes for key components in a handshake."""
    if "mlkem768" in kex_alg:
        pqc_ek  = MLKEM768_EK_SIZE
        pqc_ct  = MLKEM768_CT_SIZE
    else:   # sntrup761
        pqc_ek  = SNTRUP761_PK_SIZE
        pqc_ct  = SNTRUP761_CT_SIZE

    return {
        "client_kex_payload": X25519_PK_SIZE + pqc_ek,
        "server_kex_payload": X25519_PK_SIZE + pqc_ct + MLDSA65_PK_SIZE + MLDSA65_SIG_SIZE,
        "host_key_pk":        MLDSA65_PK_SIZE,
        "host_key_sig":       MLDSA65_SIG_SIZE,
        "session_key":        32,
    }


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 68)
    print("  POST-QUANTUM SSH SIMULATION")
    print("  OpenSSH 9.0+ with hybrid PQC key exchange + ML-DSA-65 host key")
    print("=" * 68)

    # ── 1. Generate PQC host key ──────────────────────────────────────
    print("\n── [1] Generate ML-DSA-65 Host Key ──────────────────────────")
    t0 = time.perf_counter()
    hk_pk, hk_sk = _mldsa65_keygen()
    kg_ms = (time.perf_counter() - t0) * 1000
    host_key = HostKey(HOST_KEY_MLDSA65, hk_pk, hk_sk)

    print(f"  Algorithm   : {host_key.algorithm}")
    print(f"  Public key  : {host_key.pk_size:,} bytes")
    print(f"  Private key : {host_key.sk_size:,} bytes")
    print(f"  Fingerprint : {host_key.fingerprint}")
    print(f"  KeyGen time : {kg_ms:.4f} ms")

    # ── 2. Compare to classical host keys ────────────────────────────
    print("\n── [2] Host Key Size Comparison ─────────────────────────────")
    ed25519_pk, ed25519_sk = _ed25519_keygen()
    ed_hk = HostKey(HOST_KEY_ED25519, ed25519_pk, ed25519_sk)

    rows = [
        ("Algorithm",    "Ed25519",                "ML-DSA-65"),
        ("Public key",   f"{len(ed25519_pk)} bytes", f"{MLDSA65_PK_SIZE} bytes"),
        ("Private key",  f"{len(ed25519_sk)} bytes", f"{MLDSA65_SK_SIZE} bytes"),
        ("Signature",    f"{ED25519_SIG_SIZE} bytes", f"{MLDSA65_SIG_SIZE} bytes"),
        ("Quantum-safe", "NO  (Shor's algorithm)", "YES (NIST Level 3)"),
        ("FIPS ref",     "FIPS 186-5 (approved)",  "FIPS 204 (2024)"),
    ]
    col_w = [16, 28, 28]
    print("  " + " | ".join(f"{rows[0][i]:<{col_w[i]}}" for i in range(3)))
    print("  " + "-" * (sum(col_w) + 6))
    for row in rows[1:]:
        print("  " + " | ".join(f"{row[i]:<{col_w[i]}}" for i in range(3)))

    # ── 3. Run handshake with ML-KEM-768 hybrid ───────────────────────
    print("\n── [3] Hybrid Handshake: mlkem768x25519-sha256 ──────────────")
    t_start = time.perf_counter()
    hs = PQCSSHHandshake(kex_alg=KEX_HYBRID_MLKEM768)

    client_kexinit, server_kexinit = hs.negotiate()
    print(client_kexinit.describe("client"))
    print(server_kexinit.describe("server"))

    print(f"\n  Algorithm negotiated : {KEX_HYBRID_MLKEM768}")

    kex_init_msg, c_x25519_sk, c_pqc_dk, c_x25519_pk, c_pqc_ek = hs.client_kex_init()
    print(f"\n{kex_init_msg.describe()}")

    reply, server_key = hs.server_kex_reply(host_key, c_x25519_pk, c_pqc_ek)
    print(f"\n{reply.describe()}")

    client_key = hs.client_derive_session_key(c_x25519_sk, c_pqc_dk,
                                               reply.x25519_ek, reply.pqc_ct)
    keys_match = server_key == client_key

    host_ok = hs.verify_host_key(host_key.public_key, reply,
                                  c_x25519_pk, c_pqc_ek, client_key)

    t_end = time.perf_counter()
    total_ms = (t_end - t_start) * 1000

    print(f"\n  Session key size    : {len(server_key)} bytes")
    print(f"  Keys match          : {'YES' if keys_match else 'NO'}")
    print(f"  Host key verified   : {'YES' if host_ok else 'NO'}")
    print(f"  Handshake time      : {total_ms:.3f} ms (wall clock)")

    # ── 4. sntrup761 comparison ───────────────────────────────────────
    print("\n── [4] sntrup761x25519-sha512 (OpenSSH 9.0 Default) ─────────")
    hs2 = PQCSSHHandshake(kex_alg=KEX_HYBRID_SNTRUP761)
    kex2, c2_x25519_sk, c2_pqc_dk, c2_x25519_pk, c2_pqc_ek = hs2.client_kex_init()
    reply2, sk2 = hs2.server_kex_reply(host_key, c2_x25519_pk, c2_pqc_ek)
    client2_key = hs2.client_derive_session_key(c2_x25519_sk, c2_pqc_dk,
                                                 reply2.x25519_ek, reply2.pqc_ct)
    print(f"  OpenSSH >= 9.0 enables sntrup761 by default")
    print(f"  sntrup761 client payload: {kex2.wire_size()} bytes")
    print(f"  sntrup761 server reply  : {reply2.wire_size()} bytes")
    print(f"  Keys match              : {'YES' if sk2 == client2_key else 'NO'}")

    # ── 5. Wire size comparison ───────────────────────────────────────
    print("\n── [5] Handshake Wire Size Comparison ───────────────────────")
    classical_client = X25519_PK_SIZE                # curve25519
    classical_server = X25519_PK_SIZE + ED25519_PK_SIZE + ED25519_SIG_SIZE

    hybrid_mlkem_sizes = compare_handshake_sizes(KEX_HYBRID_MLKEM768)
    hybrid_sntrup_sizes = compare_handshake_sizes(KEX_HYBRID_SNTRUP761)

    print(f"  {'Component':<30} {'Classical':>12} {'ML-KEM-768':>12} {'sntrup761':>12}")
    print(f"  {'-'*68}")
    comps = [
        ("Client KEX payload (bytes)",
         classical_client,
         hybrid_mlkem_sizes["client_kex_payload"],
         hybrid_sntrup_sizes["client_kex_payload"]),
        ("Server KEX payload (bytes)",
         classical_server,
         hybrid_mlkem_sizes["server_kex_payload"],
         hybrid_sntrup_sizes["server_kex_payload"]),
        ("Host key PK (bytes)",
         ED25519_PK_SIZE,
         MLDSA65_PK_SIZE,
         MLDSA65_PK_SIZE),
        ("Host key sig (bytes)",
         ED25519_SIG_SIZE,
         MLDSA65_SIG_SIZE,
         MLDSA65_SIG_SIZE),
    ]
    for label, c, m, s in comps:
        print(f"  {label:<30} {c:>12} {m:>12} {s:>12}")

    # ── 6. known_hosts migration ──────────────────────────────────────
    print("\n── [6] ~/.ssh/known_hosts Migration ─────────────────────────")
    import base64
    b64_pk = base64.b64encode(host_key.public_key[:32]).decode()
    entry = KnownHostsEntry(
        hostname="server.example.com",
        algorithm=HOST_KEY_MLDSA65,
        public_key_b64=b64_pk + "...",
        comment="migrated 2025-Q3",
    )
    print(f"  New entry format:")
    print(f"    {entry.format_line()}")
    print(f"\n  ssh-keyscan must be updated to support ssh-mldsa65 key type")
    print(f"  TOFU (Trust On First Use) policy unchanged")
    print(f"  CA-signed known_hosts supported via @cert-authority lines")

    # ── 7. Migration path ─────────────────────────────────────────────
    print("\n── [7] Migration Path: Ed25519 → ML-DSA-65 ──────────────────")
    steps = [
        ("Step 1", "OpenSSH 9.0+: sntrup761x25519-sha512 is already the default KEX"),
        ("Step 2", "Generate ML-DSA-65 host key alongside Ed25519"),
        ("Step 3", "Advertise both in HostKeyAlgorithms (server sshd_config)"),
        ("Step 4", "Clients with OpenSSH PQC patches prefer ssh-mldsa65"),
        ("Step 5", "Update ~/.ssh/known_hosts with ML-DSA-65 fingerprints"),
        ("Step 6", "Deprecate Ed25519 host key after rollout window"),
        ("Note",   "User keys: same path — generate id_mldsa65 alongside id_ed25519"),
    ]
    for phase, desc in steps:
        print(f"  {phase}: {desc}")

    print("\n  FIPS 204 (ML-DSA) standardized August 2024")
    print("  IETF draft-kampanakis-ssh-pq-known-hosts (ML-DSA-65 in SSH)")
    print("=" * 68)


if __name__ == "__main__":
    main()
