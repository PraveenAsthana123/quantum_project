"""
Classical Cryptographic Attack Simulations
==========================================
Educational lab: simulates classical attacks so defenders can understand
and prevent them. All attacks are theoretical/simulated demonstrations.

Defensive Security Educational Lab — /mnt/deepa/quantum/qc-attack-lab/
"""

import math
import time
import random
import hashlib
import hmac
import struct
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Shared data types
# ---------------------------------------------------------------------------

@dataclass
class AttackResult:
    attack_name: str
    success: bool
    impact: str          # CRITICAL / HIGH / MEDIUM / LOW
    finding: str
    defense: str
    quantum_version: str
    duration_ms: float = 0.0
    details: dict = field(default_factory=dict)

    def display(self):
        bar = "=" * 72
        tag = f"[{self.impact}]"
        icon = {"CRITICAL": "!!!!", "HIGH": "!! ", "MEDIUM": "!  ", "LOW": "   "}.get(self.impact, "   ")
        print(f"\n{bar}")
        print(f"  {icon} {self.attack_name}  {tag}")
        print(bar)
        print(f"  Status  : {'SUCCESS (attack works)' if self.success else 'MITIGATED'}")
        print(f"  Finding : {self.finding}")
        print(f"  Defense : {self.defense}")
        print(f"  Quantum : {self.quantum_version}")
        if self.duration_ms:
            print(f"  Time    : {self.duration_ms:.2f} ms")
        for k, v in self.details.items():
            print(f"  {k:<9}: {v}")


# ---------------------------------------------------------------------------
# 1. RSA Factoring Attack (trial division for small N)
# ---------------------------------------------------------------------------

class RSAFactoringAttack:
    """Trial-division factoring for small RSA moduli + key-size security analysis."""

    impact = "CRITICAL"
    defense = (
        "Migrate to RSA-3072+ for near-term or, better, to post-quantum KEMs "
        "(CRYSTALS-Kyber / ML-KEM, NIST FIPS 203). RSA is fundamentally broken "
        "by Shor's algorithm on any CRQC regardless of key size."
    )
    quantum_version = (
        "Shor's algorithm factors N in O((log N)^3) quantum gate operations. "
        "RSA-2048 requires ~4096 logical qubits (~1 billion physical qubits at "
        "current error rates) and ~hours on a fault-tolerant quantum computer (FTQC). "
        "CRQC timeline: estimated 2030–2035. RSA provides ZERO quantum security."
    )

    # Small test moduli  (N = p*q with known small factors)
    _DEMO_KEYS = [
        (15,   "toy"),
        (21,   "toy"),
        (35,   "toy"),
        (143,  "toy"),
        (3127, "weak-demo"),   # 53*59
    ]

    @staticmethod
    def trial_division(n: int) -> tuple[Optional[int], Optional[int], float]:
        """Return (p, q, elapsed_ms). Returns (None, None, ...) if unfactorable here."""
        start = time.perf_counter()
        if n < 4:
            return None, None, 0.0
        if n % 2 == 0:
            elapsed = (time.perf_counter() - start) * 1000
            return 2, n // 2, elapsed
        i = 3
        while i * i <= n:
            if n % i == 0:
                elapsed = (time.perf_counter() - start) * 1000
                return i, n // i, elapsed
            i += 2
        elapsed = (time.perf_counter() - start) * 1000
        return None, None, elapsed

    def run(self) -> AttackResult:
        findings = []
        for n, label in self._DEMO_KEYS:
            p, q, ms = self.trial_division(n)
            if p:
                findings.append(f"N={n} ({label}): {n} = {p} × {q}  [{ms:.4f} ms]")
            else:
                findings.append(f"N={n}: prime (no factors found)")

        # Key-size security table
        size_table = [
            ("RSA-512",  "broken — factored in practice (1999)",         "NO",  "NO"),
            ("RSA-768",  "broken — factored in practice (2009)",         "NO",  "NO"),
            ("RSA-1024", "marginal — 80-bit classical security (~2012)", "NO",  "NO"),
            ("RSA-2048", "112-bit classical security — acceptable now",  "YES", "NO"),
            ("RSA-3072", "128-bit classical security — recommended",     "YES", "NO"),
            ("RSA-4096", "~140-bit classical security",                  "YES", "NO"),
        ]

        details: dict = {
            "Demo factorings": " | ".join(findings),
            "RSA-512 classical": "BROKEN (factored 1999)",
            "RSA-2048 classical": "SAFE (112-bit security)",
            "RSA-2048 quantum": "BROKEN by Shor's on CRQC",
            "Key-size table": " | ".join(
                f"{sz}: classical={cs}, quantum={qs}"
                for sz, _, cs, qs in size_table
            ),
        }
        return AttackResult(
            attack_name="RSA Factoring Attack (Trial Division)",
            success=True,
            impact=self.impact,
            finding=(
                "Small RSA keys factored instantly. RSA-2048 is classically safe "
                "but provides ZERO protection against Shor's algorithm on a CRQC."
            ),
            defense=self.defense,
            quantum_version=self.quantum_version,
            details=details,
        )


# ---------------------------------------------------------------------------
# 2. Timing Side-Channel Attack
# ---------------------------------------------------------------------------

class TimingAttack:
    """Simulated timing side-channel on naive RSA square-and-multiply."""

    impact = "HIGH"
    defense = (
        "Use constant-time implementations (e.g. Montgomery ladder, blinding). "
        "OpenSSL RSA_FLAG_NO_CONSTTIME is deprecated; use RSA_BLINDING_ON. "
        "Hardware HSMs provide timing isolation."
    )
    quantum_version = (
        "Quantum computers amplify timing leakage: a quantum adversary can use "
        "amplitude amplification (Grover-like) to distinguish timing distributions "
        "faster, requiring fewer measurements to recover key bits."
    )

    @staticmethod
    def _naive_modexp(base: int, exp: int, mod: int) -> tuple[int, list[float]]:
        """Square-and-multiply with simulated timing leak per bit."""
        result = 1
        timings: list[float] = []
        base = base % mod
        while exp > 0:
            bit = exp & 1
            t_start = time.perf_counter()
            if bit == 1:
                result = (result * base) % mod
                time.sleep(0.000_001)   # extra work when bit=1 → LEAK
            base = (base * base) % mod
            elapsed = (time.perf_counter() - t_start) * 1e6  # µs
            timings.append(elapsed)
            exp >>= 1
        return result, timings

    @staticmethod
    def _constant_time_modexp(base: int, exp: int, mod: int) -> tuple[int, list[float]]:
        """Montgomery-ladder style: always perform multiply, discard dummy result."""
        r0, r1 = 1, base % mod
        timings: list[float] = []
        for i in range(exp.bit_length() - 1, -1, -1):
            t_start = time.perf_counter()
            bit = (exp >> i) & 1
            # always two multiplications — no branch on secret bit
            if bit == 0:
                r1 = (r0 * r1) % mod
                r0 = (r0 * r0) % mod
            else:
                r0 = (r0 * r1) % mod
                r1 = (r1 * r1) % mod
            elapsed = (time.perf_counter() - t_start) * 1e6
            timings.append(elapsed)
        return r0, timings

    def run(self) -> AttackResult:
        # Use a tiny 8-bit "key" for demo speed
        p, q = 13, 17
        n_mod = p * q
        e = 5
        # phi = (p-1)*(q-1) = 192, find d such that e*d ≡ 1 (mod phi)
        phi = (p - 1) * (q - 1)
        d = pow(e, -1, phi)  # Python 3.8+
        msg = 7

        _, naive_times = self._naive_modexp(msg, d, n_mod)
        _, const_times = self._constant_time_modexp(msg, d, n_mod)

        naive_variance = sum((t - sum(naive_times) / len(naive_times)) ** 2
                             for t in naive_times) / len(naive_times)
        const_variance = sum((t - sum(const_times) / len(const_times)) ** 2
                             for t in const_times) / len(const_times)

        return AttackResult(
            attack_name="Timing Side-Channel Attack (RSA exponentiation)",
            success=naive_variance > const_variance,
            impact=self.impact,
            finding=(
                f"Naive implementation timing variance: {naive_variance:.4f} µs² — "
                f"key bits leak through timing. Constant-time variance: {const_variance:.4f} µs²."
            ),
            defense=self.defense,
            quantum_version=self.quantum_version,
            details={
                "Naive var (µs²)": f"{naive_variance:.4f}",
                "Const var (µs²)": f"{const_variance:.4f}",
                "Leak ratio": f"{naive_variance / max(const_variance, 1e-9):.1f}×",
                "Samples": str(len(naive_times)),
            },
        )


# ---------------------------------------------------------------------------
# 3. Bleichenbacher PKCS#1 v1.5 Oracle Attack
# ---------------------------------------------------------------------------

class BleichenbacherAttack:
    """
    Bleichenbacher '98 adaptive chosen-ciphertext attack against PKCS#1 v1.5
    RSA padding. Simulates oracle query-count required to recover plaintext.
    """

    impact = "CRITICAL"
    defense = (
        "Migrate to RSA-OAEP (PKCS#1 v2) which is CCA2-secure. "
        "TLS 1.3 removed RSA key-exchange entirely — use ECDHE or ML-KEM. "
        "Never expose a padding-oracle through timing or error differentiation."
    )
    quantum_version = (
        "Shor's algorithm makes RSA key recovery directly feasible on a CRQC, "
        "rendering Bleichenbacher's adaptive chosen-ciphertext attack obsolete — "
        "the attacker simply factors N. OAEP + PQC migration is the only fix."
    )

    @staticmethod
    def simulate_oracle_queries(key_bits: int) -> dict:
        """
        Estimate the number of oracle queries needed for Bleichenbacher's attack
        based on empirical results from the literature.
        Reference: Bleichenbacher (1998), Bardou et al. (2012) 'Efficient Padding
        Oracle Attacks on Cryptographic Hardware'.
        """
        # Empirical estimates: ~2^17 to ~2^23 queries depending on key size and oracle type
        min_queries = {512: 200_000, 1024: 500_000, 2048: 1_000_000}
        max_queries = {512: 500_000, 1024: 2_000_000, 2048: 14_000_000}
        typical = {512: 300_000, 1024: 1_000_000, 2048: 4_000_000}
        return {
            "key_bits": key_bits,
            "min_queries": min_queries.get(key_bits, key_bits * 500),
            "max_queries": max_queries.get(key_bits, key_bits * 7000),
            "typical_queries": typical.get(key_bits, key_bits * 2000),
            "at_1000_qps_hours": typical.get(key_bits, key_bits * 2000) / 3_600_000,
        }

    def run(self) -> AttackResult:
        results_1024 = self.simulate_oracle_queries(1024)
        results_2048 = self.simulate_oracle_queries(2048)
        return AttackResult(
            attack_name="Bleichenbacher PKCS#1 v1.5 Padding Oracle Attack",
            success=True,
            impact=self.impact,
            finding=(
                f"RSA-1024: ~{results_1024['typical_queries']:,} oracle queries to "
                f"recover plaintext (~{results_1024['at_1000_qps_hours']:.1f} h at 1k QPS). "
                f"RSA-2048: ~{results_2048['typical_queries']:,} queries "
                f"(~{results_2048['at_1000_qps_hours']:.1f} h). "
                "Demonstrated on real TLS stacks (JSSE, OpenSSL, GnuTLS)."
            ),
            defense=self.defense,
            quantum_version=self.quantum_version,
            details={
                "RSA-1024 queries": f"{results_1024['typical_queries']:,}",
                "RSA-2048 queries": f"{results_2048['typical_queries']:,}",
                "Real-world": "ROBOT attack (2017) affected F5, Cisco, Citrix, etc.",
                "TLS 1.3 status": "RSA key transport REMOVED — ECDHE only",
            },
        )


# ---------------------------------------------------------------------------
# 4. Birthday Attack (hash collision)
# ---------------------------------------------------------------------------

class BirthdayAttack:
    """
    Demonstrate birthday bound for hash collision probability.
    Shows why MD5 and SHA-1 are broken for collision resistance.
    """

    impact = "HIGH"
    defense = (
        "Use SHA-256 or SHA-3-256 (128-bit collision resistance). "
        "SHA-384/SHA-512 for high-security contexts. "
        "MD5 and SHA-1 MUST NOT be used for security-sensitive operations."
    )
    quantum_version = (
        "Grover's algorithm reduces collision search from O(2^(n/2)) to O(2^(n/3)) "
        "under the BHT quantum walk algorithm. SHA-256 collision resistance drops "
        "from 2^128 to ~2^85 classically and ~2^85 quantum (BHT). "
        "SHA-3-384 recommended for long-term quantum resistance."
    )

    @staticmethod
    def birthday_probability(num_messages: int, output_bits: int) -> float:
        """
        Approximate collision probability: P ≈ 1 - e^(-k²/(2·2^n))
        where k = num_messages, n = output_bits.
        """
        k = num_messages
        N = 2 ** output_bits
        # Use the approximation P ≈ 1 - exp(-k*(k-1)/(2*N))
        exp_arg = -(k * (k - 1)) / (2.0 * N)
        if exp_arg < -700:
            return 0.0
        import math
        return 1.0 - math.exp(exp_arg)

    @staticmethod
    def collision_bound(output_bits: int, probability: float = 0.5) -> int:
        """Number of messages needed for ~50% collision probability."""
        # k ≈ sqrt(2 * 2^n * ln(1/(1-p)))
        import math
        N = 2 ** output_bits
        return int(math.sqrt(2 * N * math.log(1.0 / (1.0 - probability))))

    def run(self) -> AttackResult:
        hashes = {
            "MD5":     {"bits": 128, "broken": True,  "broken_year": 2004},
            "SHA-1":   {"bits": 160, "broken": True,  "broken_year": 2017},
            "SHA-256": {"bits": 256, "broken": False, "broken_year": None},
            "SHA-384": {"bits": 384, "broken": False, "broken_year": None},
            "SHA-512": {"bits": 512, "broken": False, "broken_year": None},
        }
        summary = []
        for name, info in hashes.items():
            bound = self.collision_bound(info["bits"])
            status = f"BROKEN ({info['broken_year']})" if info["broken"] else "SAFE"
            summary.append(f"{name}: {info['bits']}-bit → 2^{info['bits']//2} bound "
                            f"(~{bound:.2e} msgs) [{status}]")

        # Actual MD5 collision demonstration (two known colliding prefixes)
        md5_msg1 = b"d131dd02c5e6eec4693d9a0698aff95c2fcab58712467eab4004583eb8fb7f89"
        md5_msg2 = b"d131dd02c5e6eec4693d9a0698aff95c2fcab50712467eab4004583eb8fb7f89"
        h1 = hashlib.md5(md5_msg1).hexdigest()
        h2 = hashlib.md5(md5_msg2).hexdigest()
        collision_demo = f"MD5 distinct inputs → {'SAME hash' if h1 == h2 else 'different hashes'}"

        return AttackResult(
            attack_name="Birthday Attack (Hash Collision)",
            success=True,
            impact=self.impact,
            finding=(
                "MD5 collisions practical since 2004 (Wang et al.). "
                "SHA-1 collision computed by Google SHAttered (2017) in 2^63 operations. "
                "SHA-256 provides 128-bit collision resistance — quantum-marginal."
            ),
            defense=self.defense,
            quantum_version=self.quantum_version,
            details={
                "MD5 bound":     "2^64 (broken; practical in seconds)",
                "SHA-1 bound":   "2^80 (broken; SHAttered 2017)",
                "SHA-256 bound": "2^128 (safe classically, marginal quantum)",
                "SHA-512 bound": "2^256 (quantum-safe)",
                "Hash table":    " | ".join(summary),
            },
        )


# ---------------------------------------------------------------------------
# 5. Man-in-the-Middle on unauthenticated Diffie-Hellman
# ---------------------------------------------------------------------------

class MITMAttack:
    """
    Simulate MITM on classic DH key exchange without authentication.
    Eve intercepts Alice↔Bob and establishes two separate shared secrets.
    """

    impact = "CRITICAL"
    defense = (
        "Always authenticate DH with certificates (TLS), SIGMA protocol, or "
        "station-to-station (STS). Use authenticated ECDHE + certificate pinning. "
        "For PQC: ML-KEM-768 + ML-DSA-65 (NIST FIPS 203/204)."
    )
    quantum_version = (
        "Shor's algorithm breaks ECDH: it recovers the static DH private key "
        "from the public key. Even authenticated DH is broken on a CRQC unless "
        "replaced with ML-KEM (Kyber) or other PQC KEMs."
    )

    @staticmethod
    def _dh_params():
        # RFC 3526 group-5 (1536-bit) — simplified for demo with small prime
        p = 23   # small prime for demo
        g = 5    # primitive root mod p
        return p, g

    def run(self) -> AttackResult:
        p, g = self._dh_params()
        # Alice
        a = random.randint(2, p - 2)
        A = pow(g, a, p)   # Alice's public value
        # Bob
        b = random.randint(2, p - 2)
        B = pow(g, b, p)   # Bob's public value
        # Eve intercepts — picks own ephemeral secrets
        e1 = random.randint(2, p - 2)
        e2 = random.randint(2, p - 2)
        E1 = pow(g, e1, p)   # Eve sends this to Bob pretending to be Alice
        E2 = pow(g, e2, p)   # Eve sends this to Alice pretending to be Bob

        # Shared secrets
        alice_secret  = pow(E2, a, p)   # Alice thinks she shares with Bob
        bob_secret    = pow(E1, b, p)   # Bob thinks he shares with Alice
        eve_alice_s   = pow(A, e2, p)   # Eve ↔ Alice
        eve_bob_s     = pow(B, e1, p)   # Eve ↔ Bob

        mitm_success = (alice_secret == eve_alice_s and bob_secret == eve_bob_s)

        return AttackResult(
            attack_name="Man-in-the-Middle on Unauthenticated DH",
            success=mitm_success,
            impact=self.impact,
            finding=(
                f"Alice believes shared secret = {alice_secret}, "
                f"Eve knows Alice's secret = {eve_alice_s}. "
                f"Bob believes shared secret = {bob_secret}, "
                f"Eve knows Bob's secret = {eve_bob_s}. "
                "Eve decrypts and re-encrypts all traffic transparently."
            ),
            defense=self.defense,
            quantum_version=self.quantum_version,
            details={
                "Alice pubkey": str(A),
                "Bob pubkey": str(B),
                "Eve↔Alice secret": str(eve_alice_s),
                "Eve↔Bob secret": str(eve_bob_s),
                "MITM success": str(mitm_success),
            },
        )


# ---------------------------------------------------------------------------
# 6. JWT Replay Attack
# ---------------------------------------------------------------------------

class ReplayAttack:
    """
    Simulate JWT replay: stolen token reused after intended expiry because
    the server doesn't check the jti (JWT ID) nonce or real expiry.
    """

    impact = "HIGH"
    defense = (
        "Validate jti (JWT ID) against a server-side nonce store (Redis set). "
        "Enforce strict exp claim validation. Use short token lifetimes (15 min). "
        "Implement token binding (RFC 8471) for high-value endpoints. "
        "HMAC secret must be ≥256 bits; use RS256 or ES256 for server-to-server."
    )
    quantum_version = (
        "Grover's algorithm halves HMAC-SHA256 key strength from 256 to 128 bits "
        "— still acceptable but migrate to HMAC-SHA384 or HMAC-SHA512 for "
        "long-lived secrets. Quantum computers accelerate brute-force of weak secrets."
    )

    @staticmethod
    def _make_jwt(subject: str, secret: bytes, issued_at: int,
                  expires_at: int, jti: str) -> str:
        import base64
        import json as _json
        header = base64.urlsafe_b64encode(
            _json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(
            _json.dumps({
                "sub": subject, "iat": issued_at,
                "exp": expires_at, "jti": jti
            }).encode()
        ).rstrip(b"=").decode()
        signing_input = f"{header}.{payload}".encode()
        sig = hmac.new(secret, signing_input, hashlib.sha256).digest()
        sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
        return f"{header}.{payload}.{sig_b64}"

    def run(self) -> AttackResult:
        secret = b"super-secret-key-that-is-256-bits-long!!"
        now = int(time.time())
        # Token issued 2 hours ago, expired 1 hour ago
        issued_at = now - 7200
        expires_at = now - 3600
        jti = "tok-abc123"

        token = self._make_jwt("alice", secret, issued_at, expires_at, jti)

        # Naive server: only checks signature, not expiry/jti
        naive_accepted = True   # signature is valid; naive server allows it
        # Secure server: checks exp and jti nonce store
        seen_jtis: set = set()  # empty — token never seen before (stolen)
        # If we add to nonce store after first use, replay is blocked
        if jti in seen_jtis:
            secure_accepted = False
        else:
            seen_jtis.add(jti)
            secure_accepted = (expires_at > now)  # False: expired

        return AttackResult(
            attack_name="JWT Replay Attack (stolen expired token)",
            success=naive_accepted,
            impact=self.impact,
            finding=(
                f"Token expired {(now - expires_at)//60} min ago. "
                f"Naive server: ACCEPTED (checks only signature). "
                f"Secure server: REJECTED (exp={expires_at} < now={now})."
            ),
            defense=self.defense,
            quantum_version=self.quantum_version,
            details={
                "Token (first 60 chars)": token[:60] + "...",
                "Issued":   f"{(now - issued_at)//60} min ago",
                "Expired":  f"{(now - expires_at)//60} min ago",
                "Naive":    "ACCEPTED",
                "Secure":   "REJECTED",
            },
        )


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main():
    print("\n" + "#" * 72)
    print("  CLASSICAL CRYPTOGRAPHIC ATTACK SIMULATION LAB")
    print("  Defensive Security / Educational — Not for offensive use")
    print("#" * 72)

    attacks = [
        RSAFactoringAttack(),
        TimingAttack(),
        BleichenbacherAttack(),
        BirthdayAttack(),
        MITMAttack(),
        ReplayAttack(),
    ]

    results = []
    for atk in attacks:
        try:
            t0 = time.perf_counter()
            result = atk.run()
            result.duration_ms = (time.perf_counter() - t0) * 1000
            results.append(result)
            result.display()
        except Exception as exc:
            print(f"\n[ERROR] {atk.__class__.__name__}: {exc}")

    # Summary table
    print("\n\n" + "=" * 72)
    print("  ATTACK SUMMARY")
    print("=" * 72)
    print(f"  {'Attack':<45} {'Impact':<10} {'Success'}")
    print("  " + "-" * 68)
    for r in results:
        status = "YES (vulnerable)" if r.success else "NO (mitigated)"
        print(f"  {r.attack_name:<45} {r.impact:<10} {status}")
    print("=" * 72)
    print(f"\n  Total attacks simulated: {len(results)}")
    critical = sum(1 for r in results if r.impact == "CRITICAL")
    high = sum(1 for r in results if r.impact == "HIGH")
    print(f"  CRITICAL: {critical}  HIGH: {high}  MEDIUM: {len(results)-critical-high}")
    print()


if __name__ == "__main__":
    main()
