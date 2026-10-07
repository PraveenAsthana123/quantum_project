"""
Grover's Algorithm Attack Simulation
=====================================
Simulates Grover's Algorithm attacks on symmetric cryptography (AES),
hash functions (SHA), and password hashing schemes.

Key principle: Grover's provides quadratic speedup for unstructured search.
  Classical: O(N) search over N items
  Quantum:   O(√N) search — halves the effective security in bits.

References:
- Grover, L.K. (1996). A fast quantum mechanical algorithm for database search.
- NIST SP 800-57 Part 1 Rev 5 (2020) — key management recommendation.
- Bernstein & Lange (2017). Post-quantum cryptography. Nature.
- NIST IR 8105 (2016) — Report on post-quantum cryptography.

Educational use only — demonstrates defensive security concepts.
"""

import math
from typing import NamedTuple


# ─────────────────────────────────────────────────────────────────────────────
# Grover iteration count: π/4 × √(2^n) for n-bit keyspace
# ─────────────────────────────────────────────────────────────────────────────

def grover_iterations(key_bits: int) -> float:
    """Number of Grover oracle calls needed: π/4 × √(2^n)."""
    return (math.pi / 4) * math.sqrt(2 ** key_bits)


def quantum_security_bits(classical_bits: int) -> int:
    """Grover halves security: classical 128-bit → quantum 64-bit."""
    return classical_bits // 2


# ─────────────────────────────────────────────────────────────────────────────
# AES Attack
# ─────────────────────────────────────────────────────────────────────────────

class GroversAESAttack:
    """
    Grover's Algorithm against AES key search.

    Grover oracle: circuit that checks whether a candidate key k decrypts
    a known ciphertext C to a known plaintext P.
    Each oracle evaluation ≈ one AES circuit = ~thousands of Toffoli gates.
    """

    AES_DATA = {
        128: {
            "classical_ops":     2**128,
            "quantum_ops":       2**64,
            "quantum_sec_bits":  64,
            "grover_iterations": grover_iterations(128),
            "oracle_gate_count": "~6,000 Toffoli gates per evaluation",
            "logical_qubits":    "~2,953 (Jaques et al. 2020)",
            "threat_level":      "CRITICAL",
            "nist_verdict":      "MOVE TO AES-256 — quantum security insufficient",
            "note":              "NIST explicitly recommends doubling AES key length",
        },
        192: {
            "classical_ops":     2**192,
            "quantum_ops":       2**96,
            "quantum_sec_bits":  96,
            "grover_iterations": grover_iterations(192),
            "oracle_gate_count": "~8,400 Toffoli gates per evaluation",
            "logical_qubits":    "~3,400 (estimated)",
            "threat_level":      "HIGH",
            "nist_verdict":      "INSUFFICIENT — below 128-bit quantum security target",
            "note":              "96-bit quantum security below NIST 128-bit minimum",
        },
        256: {
            "classical_ops":     2**256,
            "quantum_ops":       2**128,
            "quantum_sec_bits":  128,
            "grover_iterations": grover_iterations(256),
            "oracle_gate_count": "~10,800 Toffoli gates per evaluation",
            "logical_qubits":    "~6,681 (Jaques et al. 2020)",
            "threat_level":      "SAFE",
            "nist_verdict":      "QUANTUM-RESISTANT — 128-bit quantum security maintained",
            "note":              "Recommended by NIST for long-term quantum security",
        },
    }

    def analyze(self, key_bits: int) -> dict:
        """Full Grover analysis for AES-{key_bits}."""
        return self.AES_DATA.get(key_bits, {})

    def print_analysis(self) -> None:
        print("\n" + "="*70)
        print("  GROVER'S ALGORITHM vs AES")
        print("="*70)
        print("""
HOW THE ATTACK WORKS
────────────────────
  1. Adversary has: known plaintext P, ciphertext C = AES_k(P)
  2. Build quantum oracle O_k: |k⟩|0⟩ → |k⟩|AES_k(P)⟩
     Oracle flips phase of |k⟩ if AES_k(P) = C.
  3. Repeat Grover iteration (Oracle + Diffusion operator): π/4 × √N times.
  4. Measure: correct key k with probability ≥ 1/2.

  Each oracle call requires implementing full AES in reversible quantum logic:
  SubBytes (S-box via Boyar-Peralta circuit), ShiftRows, MixColumns, AddRoundKey.
  One oracle ≈ 6,000–10,000 Toffoli gates depending on AES key size.
""")
        for bits in [128, 192, 256]:
            d = self.AES_DATA[bits]
            print(f"  AES-{bits}")
            print(f"  {'─'*50}")
            print(f"    Classical security:   2^{bits} operations")
            print(f"    Quantum security:     2^{quantum_security_bits(bits)} operations  "
                  f"(Grover halves bit-security)")
            print(f"    Grover iterations:    {d['grover_iterations']:.2e}")
            print(f"    Oracle circuit:       {d['oracle_gate_count']}")
            print(f"    Logical qubits:       {d['logical_qubits']}")
            print(f"    Threat level:         {d['threat_level']}")
            print(f"    NIST verdict:         {d['nist_verdict']}")
            print(f"    Note:                 {d['note']}")
            print()

        print("""  KEY INSIGHT
  ───────────
  Grover does NOT break AES the way Shor breaks RSA.
  RSA: quantum security = 0 bits (exponential → polynomial speedup).
  AES: quantum security = n/2 bits (polynomial → polynomial speedup).

  AES-128 with 64-bit quantum security is dangerous.
  AES-256 with 128-bit quantum security meets NIST's quantum target.
  Rule of thumb: double your symmetric key length for quantum safety.
""")


# ─────────────────────────────────────────────────────────────────────────────
# SHA Attack
# ─────────────────────────────────────────────────────────────────────────────

class GroversSHAAttack:
    """
    Grover's Algorithm against SHA hash functions.

    Two attack types:
    - Preimage: find m such that SHA(m) = h  (needs √(2^n) queries)
    - Collision: find m1≠m2 with SHA(m1)=SHA(m2)  (birthday + Grover: 2^(n/3))
    """

    SHA_DATA = {
        "MD5": {
            "bits": 128,
            "classical_preimage":  "2^128",
            "classical_collision": "2^64 → BROKEN (classical birthday)",
            "quantum_preimage":    "2^64",
            "quantum_collision":   "2^43 (Brassard-Hoyer-Tapp)",
            "broken_classically":  True,
            "threat_level":        "ALREADY BROKEN (classically) — retire immediately",
            "note":                "Wang et al. 2004 — collisions in <2^24 ops",
        },
        "SHA-1": {
            "bits": 160,
            "classical_preimage":  "2^160",
            "classical_collision": "2^63.1 → BROKEN (SHAttered 2017)",
            "quantum_preimage":    "2^80",
            "quantum_collision":   "2^53",
            "broken_classically":  True,
            "threat_level":        "ALREADY BROKEN (classically) — retire immediately",
            "note":                "Stevens et al. 2017 — first practical SHA-1 collision",
        },
        "SHA-256": {
            "bits": 256,
            "classical_preimage":  "2^256",
            "classical_collision": "2^128",
            "quantum_preimage":    "2^128  (SAFE)",
            "quantum_collision":   "2^85  (Brassard-Hoyer-Tapp — marginal)",
            "broken_classically":  False,
            "threat_level":        "SAFE (preimage) / MARGINAL (collision)",
            "note":                "Bitcoin mining (SHA-256d) faces Grover speedup but remains practical",
        },
        "SHA-3-256": {
            "bits": 256,
            "classical_preimage":  "2^256",
            "classical_collision": "2^128",
            "quantum_preimage":    "2^128  (SAFE)",
            "quantum_collision":   "2^85  (marginal, same as SHA-256)",
            "broken_classically":  False,
            "threat_level":        "SAFE (preimage) / MARGINAL (collision)",
            "note":                "Keccak sponge structure; collision resistance marginal but acceptable",
        },
        "SHA-384": {
            "bits": 384,
            "classical_preimage":  "2^384",
            "classical_collision": "2^192",
            "quantum_preimage":    "2^192  (SAFE)",
            "quantum_collision":   "2^128  (SAFE — meets NIST target)",
            "broken_classically":  False,
            "threat_level":        "SAFE",
            "note":                "Recommended for long-term quantum-resistant hashing",
        },
        "SHA-512": {
            "bits": 512,
            "classical_preimage":  "2^512",
            "classical_collision": "2^256",
            "quantum_preimage":    "2^256  (SAFE)",
            "quantum_collision":   "2^171  (SAFE)",
            "broken_classically":  False,
            "threat_level":        "SAFE",
            "note":                "Best available hash security; use SHA-512/256 for efficiency",
        },
    }

    def print_analysis(self) -> None:
        print("\n" + "="*70)
        print("  GROVER'S ALGORITHM vs SHA HASH FUNCTIONS")
        print("="*70)
        print("""
ATTACK TYPES
────────────
  Preimage attack:  Given h, find m s.t. SHA(m) = h
                    Grover: O(√(2^n)) = O(2^(n/2)) — halves security
  Collision attack: Find any m1 ≠ m2 s.t. SHA(m1) = SHA(m2)
                    Quantum (Brassard-Hoyer-Tapp): O(2^(n/3)) — reduces by 1/3
                    Note: Birthday bound classically is O(2^(n/2))
""")
        print(f"  {'Algorithm':<12} {'Bits':<6} {'Q-Preimage':<18} {'Q-Collision':<22} {'Status'}")
        print(f"  {'─'*78}")
        for name, d in self.SHA_DATA.items():
            status = "BROKEN" if d["broken_classically"] else d["threat_level"].split()[0]
            print(f"  {name:<12} {d['bits']:<6} {d['quantum_preimage']:<18} {d['quantum_collision']:<22} {status}")
        print()

        print("""  DETAILED NOTES
  ──────────────
  MD5/SHA-1: Do NOT use for any security purpose. Classically broken.
             Quantum attack is irrelevant — they're already dead.

  SHA-256:   Preimage is safe (128-bit quantum security).
             Collision is marginal (2^85) — still safe but monitor.
             NIST considers SHA-256 acceptable for signatures through 2030.

  SHA-384+:  Both preimage and collision are safe post-quantum.
             Recommended for code signing, certificates, long-lived data.

  BITCOIN NOTE:
  Bitcoin mining is double-SHA-256 (SHA-256d). Grover's would give a √2^256
  speedup in nonce search. However, Bitcoin's difficulty adjusts dynamically —
  a quantum miner would dominate the network, not break the hash.
  Real risk: preimage on transaction IDs for specific historical blocks.
""")


# ─────────────────────────────────────────────────────────────────────────────
# Password Attack
# ─────────────────────────────────────────────────────────────────────────────

class GroversPasswordAttack:
    """
    Grover's Algorithm against password hashing (bcrypt, PBKDF2, Argon2).
    Key insight: memory-hard password hashing resists Grover's more than AES.
    """

    # Keyspace sizes
    CHARSETS = {
        "numeric-8":         {"chars": 10, "length": 8, "space": 10**8,
                               "desc": "8-digit PIN"},
        "alpha-lower-8":     {"chars": 26, "length": 8, "space": 26**8,
                               "desc": "8 lowercase letters"},
        "alpha-mixed-8":     {"chars": 52, "length": 8, "space": 52**8,
                               "desc": "8 mixed-case letters"},
        "printable-8":       {"chars": 95, "length": 8, "space": 95**8,
                               "desc": "8 printable ASCII chars"},
        "printable-12":      {"chars": 95, "length": 12, "space": 95**12,
                               "desc": "12 printable ASCII chars"},
        "printable-20":      {"chars": 95, "length": 20, "space": 95**20,
                               "desc": "20 printable ASCII chars (passphrase)"},
    }

    PASSWORD_HASHERS = {
        "bcrypt-12": {
            "iterations":     4096,       # 2^12 rounds
            "inner_hash":     "SHA-512",
            "ops_per_guess":  4096 * 1,   # ~4096 SHA-like operations
            "time_per_guess_ns": 300_000_000,  # ~300ms CPU
            "note":           "Memory-hard; parallelization limited by 4KB state",
        },
        "PBKDF2-SHA256-100k": {
            "iterations":     100_000,
            "inner_hash":     "SHA-256",
            "ops_per_guess":  100_000,
            "time_per_guess_ns": 50_000_000,  # ~50ms CPU
            "note":           "Not memory-hard; GPU-parallelizable",
        },
        "Argon2id": {
            "iterations":     3,
            "inner_hash":     "Blake2b (memory-hard)",
            "ops_per_guess":  65_536,      # memory_cost KB × time_cost
            "time_per_guess_ns": 500_000_000,  # ~500ms with 64MB memory
            "note":           "Best current standard; memory-hard defeats quantum parallelism",
        },
    }

    def analyze(self, charset_key: str, hasher_key: str) -> dict:
        """Analyze Grover's attack on a specific password + hasher combination."""
        cs  = self.CHARSETS[charset_key]
        ph  = self.PASSWORD_HASHERS[hasher_key]
        N   = cs["space"]

        classical_guesses = N
        quantum_guesses   = math.sqrt(N)   # Grover's √N

        # Time in seconds (Grover oracle = one hash evaluation × circuit overhead)
        # Quantum overhead: ~100x classical per oracle evaluation (rough estimate)
        quantum_overhead = 100
        tpg_s = ph["time_per_guess_ns"] / 1e9

        classical_time_s = classical_guesses * tpg_s
        quantum_time_s   = quantum_guesses * tpg_s * quantum_overhead

        def fmt_time(seconds: float) -> str:
            if seconds < 1:
                return f"{seconds*1000:.1f} ms"
            elif seconds < 60:
                return f"{seconds:.1f} seconds"
            elif seconds < 3600:
                return f"{seconds/60:.1f} minutes"
            elif seconds < 86400:
                return f"{seconds/3600:.1f} hours"
            elif seconds < 365*86400:
                return f"{seconds/86400:.1f} days"
            elif seconds < 1e6*365*86400:
                return f"{seconds/(365*86400):.2e} years"
            else:
                return f"{seconds/(365*86400):.2e} years (effectively infinite)"

        return {
            "charset":            cs["desc"],
            "hasher":             hasher_key,
            "password_space":     N,
            "classical_guesses":  classical_guesses,
            "quantum_guesses":    quantum_guesses,
            "classical_time":     fmt_time(classical_time_s),
            "quantum_time":       fmt_time(quantum_time_s),
            "grover_speedup":     f"√{N:.2e} = {quantum_guesses:.2e}x speedup",
            "practical_threat":   "HIGH" if quantum_time_s < 86400 else
                                  ("MEDIUM" if quantum_time_s < 365*86400 else "LOW"),
        }

    def print_analysis(self) -> None:
        print("\n" + "="*70)
        print("  GROVER'S ALGORITHM vs PASSWORD HASHING")
        print("="*70)
        print("""
KEY INSIGHT
───────────
  Grover's gives √N speedup for password search, but:
  1. Memory-hard hashers (bcrypt, Argon2id) limit quantum oracle parallelism.
  2. Each Grover oracle call = one hash evaluation (expensive classically + quantum).
  3. Practical attack requires quantum RAM (QRAM) — not yet built at scale.

  The real risk is NOT Grover's directly — it is:
  a) Classical GPU cracking with leaked hashes (use high-cost hashers NOW).
  b) Brute-force on migrated PQC systems that still use short passwords.
  c) HNDL: long-lived credentials encrypted with weak classical schemes.
""")

        # Print a selection of cases
        cases = [
            ("printable-8",  "bcrypt-12",         "Short password, good hasher"),
            ("printable-8",  "PBKDF2-SHA256-100k", "Short password, moderate hasher"),
            ("printable-12", "Argon2id",           "Medium password, best hasher"),
            ("printable-20", "Argon2id",           "Passphrase, best hasher"),
            ("numeric-8",    "PBKDF2-SHA256-100k", "PIN, moderate hasher — DANGEROUS"),
        ]

        print(f"  {'Charset':<30} {'Hasher':<24} {'Quantum Time':<22} {'Threat'}")
        print(f"  {'─'*88}")
        for charset_key, hasher_key, label in cases:
            r = self.analyze(charset_key, hasher_key)
            print(f"  {r['charset']:<30} {r['hasher']:<24} {r['quantum_time']:<22} {r['practical_threat']}")
        print()

        print("""  RECOMMENDATIONS
  ───────────────
  1. Always use Argon2id (OWASP recommendation) for new password systems.
  2. bcrypt cost=12 or higher is acceptable; bcrypt cost<10 needs upgrading.
  3. PBKDF2 with <100k iterations is marginal; 600k (OWASP 2023) preferred.
  4. Minimum 12 characters; enforce 20+ for high-value accounts.
  5. Grover's on passwords is a future concern; classical GPU cracking is NOW.
  6. Post-quantum TLS is critical for protecting passwords in transit.
""")


# ─────────────────────────────────────────────────────────────────────────────
# Combined threat table
# ─────────────────────────────────────────────────────────────────────────────

def print_threat_table() -> None:
    print("\n" + "="*70)
    print("  GROVER'S ALGORITHM — COMPLETE THREAT SUMMARY TABLE")
    print("="*70)

    rows = [
        # (Algorithm, Classical bits, Quantum bits, Verdict)
        ("AES-128",           128, 64,  "CRITICAL — upgrade to AES-256"),
        ("AES-192",           192, 96,  "HIGH — below 128-bit quantum target"),
        ("AES-256",           256, 128, "SAFE — 128-bit quantum security"),
        ("ChaCha20-256",      256, 128, "SAFE — 128-bit quantum security"),
        ("MD5",               128, "BROKEN", "ALREADY BROKEN classically"),
        ("SHA-1",             160, "BROKEN", "ALREADY BROKEN classically"),
        ("SHA-256 preimage",  256, 128, "SAFE"),
        ("SHA-256 collision", 128, 85,  "MARGINAL — monitor"),
        ("SHA-384",           384, 192, "SAFE"),
        ("SHA-512",           512, 256, "SAFE"),
        ("bcrypt-12",         ">64", ">32", "SAFE (memory-hard, high cost)"),
        ("Argon2id",          ">64", ">32", "SAFE (best current standard)"),
        ("PBKDF2-SHA256-1k",  64,   32,  "WEAK — increase iterations"),
    ]

    print(f"\n  {'Algorithm':<28} {'Classical Sec':<16} {'Quantum Sec':<14} {'Verdict'}")
    print(f"  {'─'*80}")
    for row in rows:
        alg, cls, q, verdict = row
        cls_str = str(cls) if isinstance(cls, str) else f"{cls} bits"
        q_str   = str(q) if isinstance(q, str) else f"{q} bits"
        print(f"  {alg:<28} {cls_str:<16} {q_str:<14} {verdict}")
    print()


def main():
    print("\n" + "#"*70)
    print("#  GROVER'S ALGORITHM QUANTUM ATTACK ANALYSIS")
    print("#  Symmetric Cryptography, Hash Functions, Passwords")
    print("#"*70)

    aes = GroversAESAttack()
    aes.print_analysis()

    sha = GroversSHAAttack()
    sha.print_analysis()

    pwd = GroversPasswordAttack()
    pwd.print_analysis()

    print_threat_table()

    print("  BOTTOM LINE")
    print("  " + "-"*65)
    print("  Grover's algorithm HALVES effective key/hash size.")
    print("  AES-128, SHA-1, MD5 are either broken or critically weakened.")
    print("  AES-256 and SHA-256+ remain safe at ≥128-bit quantum security.")
    print("  Shor's breaks asymmetric (RSA/ECC) completely — far more severe.")
    print("  Priority 1: Migrate RSA/ECC to ML-KEM/ML-DSA.")
    print("  Priority 2: Move AES-128 deployments to AES-256.")
    print()


if __name__ == "__main__":
    main()
