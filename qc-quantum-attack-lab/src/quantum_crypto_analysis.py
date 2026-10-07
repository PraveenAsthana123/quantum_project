"""
Quantum Cryptographic Threat Analysis
======================================
Comprehensive analysis of ALL cryptographic primitives against quantum attacks.
Includes the complete threat matrix, system risk analyzer, migration priority
generator, and explanation of quantum advantage.

References:
- NIST FIPS 203 (2024): ML-KEM (Module Lattice Key Encapsulation Mechanism)
- NIST FIPS 204 (2024): ML-DSA (Module Lattice Digital Signature Algorithm)
- NIST FIPS 205 (2024): SLH-DSA (Stateless Hash-Based Digital Signature)
- NIST SP 800-208 (2020): Recommendation for Stateful HBS
- Bernstein et al. (2017): CRYSTALS-Kyber, CRYSTALS-Dilithium
- Aumasson & Bernstein (2012): SipHash

Educational use only — demonstrates defensive security concepts.
"""

from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Master Cryptographic Threat Matrix
# Based on NIST SP 800-131A, NIST IR 8105, NSA CNSA 2.0
# ─────────────────────────────────────────────────────────────────────────────

CRYPTO_THREAT_MATRIX = [
    # Asymmetric — Shor's Algorithm — BROKEN
    {
        "primitive":         "RSA-2048",
        "category":          "Asymmetric (Key Exchange / Signature)",
        "classical_bits":    112,
        "pq_bits":           0,
        "quantum_algorithm": "Shor's",
        "status":            "BROKEN",
        "impact":            "Private key recoverable from public key in ~8 hours on CRQC",
        "migrate_to":        "ML-KEM-768 (FIPS 203) + ML-DSA-65 (FIPS 204)",
        "urgency":           "CRITICAL — start migration immediately",
        "hndl_risk":         True,
    },
    {
        "primitive":         "RSA-4096",
        "category":          "Asymmetric (Key Exchange / Signature)",
        "classical_bits":    140,
        "pq_bits":           0,
        "quantum_algorithm": "Shor's",
        "status":            "BROKEN",
        "impact":            "Same vulnerability as RSA-2048; larger key only adds hours",
        "migrate_to":        "ML-KEM-768 (FIPS 203) + ML-DSA-65 (FIPS 204)",
        "urgency":           "CRITICAL — larger key buys no fundamental safety",
        "hndl_risk":         True,
    },
    {
        "primitive":         "ECDSA P-256",
        "category":          "Asymmetric (Signature)",
        "classical_bits":    128,
        "pq_bits":           0,
        "quantum_algorithm": "Shor's",
        "status":            "BROKEN",
        "impact":            "Private key recoverable → forge ANY signature; break TLS, JWT",
        "migrate_to":        "ML-DSA-65 (FIPS 204)",
        "urgency":           "CRITICAL",
        "hndl_risk":         True,
    },
    {
        "primitive":         "ECDH P-256",
        "category":          "Asymmetric (Key Exchange)",
        "classical_bits":    128,
        "pq_bits":           0,
        "quantum_algorithm": "Shor's",
        "status":            "BROKEN",
        "impact":            "TLS session keys recoverable even with Perfect Forward Secrecy",
        "migrate_to":        "ML-KEM-768 (FIPS 203)",
        "urgency":           "CRITICAL — PFS does not protect against quantum ECDLP",
        "hndl_risk":         True,
    },
    {
        "primitive":         "ECDSA P-384",
        "category":          "Asymmetric (Signature)",
        "classical_bits":    192,
        "pq_bits":           0,
        "quantum_algorithm": "Shor's",
        "status":            "BROKEN",
        "impact":            "NSS/Suite B signatures broken; DoD at risk",
        "migrate_to":        "ML-DSA-87 (FIPS 204) for Suite B replacement",
        "urgency":           "CRITICAL — CNSA 2.0 deadline 2030",
        "hndl_risk":         True,
    },
    {
        "primitive":         "DH-2048",
        "category":          "Asymmetric (Key Exchange)",
        "classical_bits":    112,
        "pq_bits":           0,
        "quantum_algorithm": "Shor's",
        "status":            "BROKEN",
        "impact":            "VPN IKE, SSH DH group exchange broken",
        "migrate_to":        "ML-KEM-768 (FIPS 203)",
        "urgency":           "CRITICAL",
        "hndl_risk":         True,
    },
    {
        "primitive":         "Ed25519",
        "category":          "Asymmetric (Signature)",
        "classical_bits":    128,
        "pq_bits":           0,
        "quantum_algorithm": "Shor's",
        "status":            "BROKEN",
        "impact":            "SSH default keys, Signal, Tor hidden services all broken",
        "migrate_to":        "ML-DSA-65 (FIPS 204) or SLH-DSA-128s (FIPS 205)",
        "urgency":           "CRITICAL",
        "hndl_risk":         True,
    },
    # Symmetric — Grover's Algorithm — WEAKENED or SAFE
    {
        "primitive":         "AES-128",
        "category":          "Symmetric (Encryption)",
        "classical_bits":    128,
        "pq_bits":           64,
        "quantum_algorithm": "Grover's",
        "status":            "WEAKENED",
        "impact":            "Effective security halved to 64 bits — below NIST 112-bit threshold",
        "migrate_to":        "AES-256",
        "urgency":           "HIGH — upgrade in progress systems",
        "hndl_risk":         False,
    },
    {
        "primitive":         "AES-192",
        "category":          "Symmetric (Encryption)",
        "classical_bits":    192,
        "pq_bits":           96,
        "quantum_algorithm": "Grover's",
        "status":            "WEAKENED",
        "impact":            "96-bit quantum security — below NIST 128-bit target",
        "migrate_to":        "AES-256",
        "urgency":           "MEDIUM — plan migration",
        "hndl_risk":         False,
    },
    {
        "primitive":         "AES-256",
        "category":          "Symmetric (Encryption)",
        "classical_bits":    256,
        "pq_bits":           128,
        "quantum_algorithm": "Grover's",
        "status":            "SAFE",
        "impact":            "128-bit quantum security — meets NIST long-term target",
        "migrate_to":        "Already quantum-safe",
        "urgency":           "NONE",
        "hndl_risk":         False,
    },
    {
        "primitive":         "ChaCha20-256",
        "category":          "Symmetric (Encryption)",
        "classical_bits":    256,
        "pq_bits":           128,
        "quantum_algorithm": "Grover's",
        "status":            "SAFE",
        "impact":            "128-bit quantum security — safe",
        "migrate_to":        "Already quantum-safe",
        "urgency":           "NONE",
        "hndl_risk":         False,
    },
    # Hash functions
    {
        "primitive":         "SHA-256",
        "category":          "Hash Function",
        "classical_bits":    256,
        "pq_bits":           128,
        "quantum_algorithm": "Grover's (preimage)",
        "status":            "SAFE",
        "impact":            "Preimage: 128-bit quantum security. Collision: 2^85 (marginal)",
        "migrate_to":        "SHA-384 or SHA-3-256 for highest assurance",
        "urgency":           "LOW — monitor",
        "hndl_risk":         False,
    },
    {
        "primitive":         "SHA-3-256",
        "category":          "Hash Function",
        "classical_bits":    256,
        "pq_bits":           128,
        "quantum_algorithm": "Grover's (preimage)",
        "status":            "SAFE",
        "impact":            "Same quantum security as SHA-256; different construction",
        "migrate_to":        "Already acceptable",
        "urgency":           "NONE",
        "hndl_risk":         False,
    },
    {
        "primitive":         "SHA-384",
        "category":          "Hash Function",
        "classical_bits":    384,
        "pq_bits":           192,
        "quantum_algorithm": "Grover's (preimage)",
        "status":            "SAFE",
        "impact":            "Both preimage and collision safe post-quantum",
        "migrate_to":        "Already quantum-safe",
        "urgency":           "NONE",
        "hndl_risk":         False,
    },
    {
        "primitive":         "MD5",
        "category":          "Hash Function",
        "classical_bits":    128,
        "pq_bits":           0,
        "quantum_algorithm": "Already broken classically",
        "status":            "ALREADY BROKEN",
        "impact":            "Collision found classically (Wang 2004) — retire immediately",
        "migrate_to":        "SHA-256 or SHA-3-256",
        "urgency":           "IMMEDIATE — no quantum needed to break this",
        "hndl_risk":         False,
    },
    {
        "primitive":         "SHA-1",
        "category":          "Hash Function",
        "classical_bits":    160,
        "pq_bits":           0,
        "quantum_algorithm": "Already broken classically",
        "status":            "ALREADY BROKEN",
        "impact":            "SHAttered (2017) — first practical collision. Retire immediately.",
        "migrate_to":        "SHA-256 or SHA-3-256",
        "urgency":           "IMMEDIATE",
        "hndl_risk":         False,
    },
    # Post-Quantum SAFE algorithms
    {
        "primitive":         "ML-KEM-768",
        "category":          "PQC Key Encapsulation (NIST FIPS 203)",
        "classical_bits":    None,
        "pq_bits":           184,
        "quantum_algorithm": "None known",
        "status":            "QUANTUM-SAFE",
        "impact":            "Standardized NIST replacement for RSA/ECDH key exchange",
        "migrate_to":        "Already the migration target",
        "urgency":           "DEPLOY — recommended standard",
        "hndl_risk":         False,
    },
    {
        "primitive":         "ML-DSA-65",
        "category":          "PQC Signature (NIST FIPS 204)",
        "classical_bits":    None,
        "pq_bits":           138,
        "quantum_algorithm": "None known",
        "status":            "QUANTUM-SAFE",
        "impact":            "Standardized NIST replacement for ECDSA/RSA signatures",
        "migrate_to":        "Already the migration target",
        "urgency":           "DEPLOY — recommended standard",
        "hndl_risk":         False,
    },
    {
        "primitive":         "SLH-DSA-128s",
        "category":          "PQC Signature (NIST FIPS 205)",
        "classical_bits":    None,
        "pq_bits":           128,
        "quantum_algorithm": "None known",
        "status":            "QUANTUM-SAFE",
        "impact":            "Hash-based signature — conservative, no lattice assumptions",
        "migrate_to":        "Already the migration target",
        "urgency":           "DEPLOY — use where lattice concerns exist",
        "hndl_risk":         False,
    },
    {
        "primitive":         "XMSS / LMS",
        "category":          "PQC Signature (NIST SP 800-208)",
        "classical_bits":    None,
        "pq_bits":           256,
        "quantum_algorithm": "None known",
        "status":            "QUANTUM-SAFE",
        "impact":            "Stateful HBS — highest security, requires state management",
        "migrate_to":        "Already the migration target (firmware signing, HSMs)",
        "urgency":           "DEPLOY for firmware/code signing",
        "hndl_risk":         False,
    },
]


class QuantumThreatAnalyzer:
    """
    Analyzes a cryptographic system configuration against quantum threats.
    Takes a dict of algorithm usages and returns overall system risk.
    """

    def analyze_system(self, crypto_config: dict) -> dict:
        """
        Analyze a system's crypto configuration.

        crypto_config format:
          {
            "use_case": "TLS termination",
            "algorithms": {
              "key_exchange": "ECDHE-P256",
              "authentication": "RSA-2048",
              "bulk_encryption": "AES-256",
              "mac": "SHA-256",
            }
          }

        Returns overall risk level and per-component analysis.
        """
        use_case   = crypto_config.get("use_case", "Unknown system")
        algorithms = crypto_config.get("algorithms", {})

        results       = []
        critical_count = 0
        high_count     = 0

        # Build a quick lookup from the threat matrix
        matrix_by_name = {}
        for row in CRYPTO_THREAT_MATRIX:
            key = row["primitive"].lower().replace(" ", "-").replace("_", "-")
            matrix_by_name[key] = row
            # Also index by shorter names
            matrix_by_name[row["primitive"].lower()] = row

        for role, alg_name in algorithms.items():
            # Normalize
            lookup_key = alg_name.lower().replace("_", "-").replace(" ", "-")
            entry = matrix_by_name.get(lookup_key)
            if not entry:
                # Fuzzy match
                for k, v in matrix_by_name.items():
                    if lookup_key in k or k in lookup_key:
                        entry = v
                        break

            if entry:
                status = entry["status"]
                urgency = entry["urgency"].split(" — ")[0]
                if status == "BROKEN":
                    critical_count += 1
                elif status == "WEAKENED":
                    high_count += 1
                results.append({
                    "role":        role,
                    "algorithm":   alg_name,
                    "status":      status,
                    "pq_bits":     entry["pq_bits"],
                    "migrate_to":  entry["migrate_to"],
                    "hndl_risk":   entry["hndl_risk"],
                })
            else:
                results.append({
                    "role":      role,
                    "algorithm": alg_name,
                    "status":    "UNKNOWN — manual review required",
                    "pq_bits":   "?",
                    "migrate_to": "Assess against NIST FIPS 203/204/205",
                    "hndl_risk": True,   # conservative
                })

        if critical_count > 0:
            overall = "CRITICAL"
        elif high_count > 0:
            overall = "HIGH"
        else:
            overall = "LOW — system appears quantum-ready"

        return {
            "use_case":       use_case,
            "overall_risk":   overall,
            "critical_count": critical_count,
            "high_count":     high_count,
            "components":     results,
        }

    # ── Migration priority ────────────────────────────────────────────────────

    def generate_migration_priority(self) -> list:
        """Sort vulnerable algorithms by migration urgency."""
        priorities = []
        for row in CRYPTO_THREAT_MATRIX:
            if row["status"] in ("BROKEN", "WEAKENED", "ALREADY BROKEN"):
                urgency_map = {
                    "CRITICAL":   1,
                    "HIGH":       2,
                    "MEDIUM":     3,
                    "IMMEDIATE":  0,
                    "LOW":        4,
                    "NONE":       5,
                }
                urgency_label = row["urgency"].split(" — ")[0]
                sort_key = urgency_map.get(urgency_label, 9)
                priorities.append((sort_key, row))

        priorities.sort(key=lambda x: x[0])
        return [p[1] for p in priorities]

    # ── Explain quantum advantage ─────────────────────────────────────────────

    def explain_quantum_advantage(self) -> None:
        """Clear explanation of why quantum computers break RSA/ECC but not AES-256/SHA-256."""
        print("\n" + "="*70)
        print("  WHY QUANTUM COMPUTERS BREAK RSA/ECC BUT NOT AES-256/SHA-256")
        print("="*70)
        print("""
THE KEY DISTINCTION: PROBLEM STRUCTURE
───────────────────────────────────────

  Quantum computers offer exponential speedup ONLY on problems with
  specific mathematical structure — specifically, problems that reduce to
  the Hidden Subgroup Problem (HSP) in abelian groups.

  RSA / Diffie-Hellman / ECC: HAVE this structure.
  AES / SHA-256 / ChaCha20:   DO NOT have this structure.

RSA AND ECC — WHY QUANTUM BREAKS THEM COMPLETELY
──────────────────────────────────────────────────
  RSA security relies on integer factorization:
    Given N = p × q (two large primes), find p and q.
  ECC security relies on the elliptic curve discrete logarithm:
    Given Q = k × G, find k.

  Both problems are instances of the Hidden Subgroup Problem in Z_N.
  Shor's Algorithm (1994) solves HSP using:
    1. Quantum Fourier Transform (QFT) — finds periodicity in quantum superposition
    2. Classical continued fractions — extracts the answer from QFT output

  Classical complexity:  O(exp(n^(1/3))) for RSA — subexponential but huge
  Quantum complexity:    O(n³) — POLYNOMIAL — fundamentally different

  This is not a "better computer" speedup — it's an algorithmic breakthrough.
  No amount of larger RSA keys provides safety: RSA-1,000,000 is also broken.

AES-256 — WHY QUANTUM ONLY WEAKENS IT (AND NOT FATALLY)
─────────────────────────────────────────────────────────
  AES security relies on:
    Finding a key k ∈ {0,1}^n such that AES_k(P) = C (given P and C).
  This is an UNSTRUCTURED SEARCH problem — no periodicity, no group structure.

  Grover's Algorithm provides quadratic speedup for ANY unstructured search:
    Classical: O(2^n) — try every key
    Quantum:   O(√(2^n)) = O(2^(n/2)) — Grover's amplitude amplification

  For AES-256 (n=256):
    Classical: 2^256 operations ≈ 10^77 — infeasible forever
    Quantum:   2^128 operations ≈ 3 × 10^38 — still infeasible

  KEY INSIGHT: Grover is a square-root speedup, not an exponential speedup.
  Doubling the key length (128→256) restores security.
  This is not true for RSA — doubling bits (2048→4096) only adds hours on a CRQC.

SHA-256 — WHY QUANTUM CANNOT BREAK IT
────────────────────────────────────────
  SHA-256 preimage: find m s.t. SHA(m) = h.
  Again, unstructured search → Grover gives √ speedup only.
  SHA-256 preimage: classical 2^256 → quantum 2^128 — still infeasible.
  SHA-256 collision: classical 2^128 → quantum 2^85 — marginal but still safe.

SUMMARY TABLE: QUANTUM SPEEDUP BY PROBLEM TYPE
────────────────────────────────────────────────
  Problem type          Classical     Quantum      Algorithm   Verdict
  ─────────────────     ─────────     ──────────   ─────────── ──────────────
  Integer factoring     exp(n^1/3)    poly(n)      Shor's      RSA BROKEN
  Elliptic curve DLP    O(√p)         poly(n)      Shor's      ECC BROKEN
  Symmetric key search  O(2^n)        O(2^(n/2))   Grover's    AES-128 WEAK
  Preimage search       O(2^n)        O(2^(n/2))   Grover's    SHA-256 SAFE (2^128)
  No structure (NP)     exp           √ speedup    Grover's    Quadratic only

  The quantum computing threat is ASYMMETRIC:
  → Asymmetric crypto (RSA/ECC/DH): catastrophic, unconditional break
  → Symmetric crypto (AES-256+):    manageable with key-length doubling
  → Hash functions (SHA-256+):      safe at current sizes
""")


# ─────────────────────────────────────────────────────────────────────────────
# Formatted output helpers
# ─────────────────────────────────────────────────────────────────────────────

def print_threat_matrix() -> None:
    print("\n" + "="*70)
    print("  COMPLETE QUANTUM CRYPTOGRAPHIC THREAT MATRIX")
    print("="*70)
    print(f"\n  {'Primitive':<22} {'Classical':<12} {'Post-Q':<10} {'Quantum Algo':<18} {'Status'}")
    print(f"  {'─'*72}")

    for row in CRYPTO_THREAT_MATRIX:
        cls_str = f"{row['classical_bits']} bits" if row["classical_bits"] else "N/A"
        pq_str  = f"{row['pq_bits']} bits"        if isinstance(row["pq_bits"], int) and row["pq_bits"] > 0 \
                  else ("0 bits" if row["pq_bits"] == 0 else "N/A")
        print(f"  {row['primitive']:<22} {cls_str:<12} {pq_str:<10} {row['quantum_algorithm']:<18} {row['status']}")
    print()


def print_migration_plan(analyzer: QuantumThreatAnalyzer) -> None:
    priorities = analyzer.generate_migration_priority()
    print("\n" + "="*70)
    print("  PQC MIGRATION PRIORITY ORDER")
    print("  (ordered by urgency, most critical first)")
    print("="*70)

    for i, row in enumerate(priorities, 1):
        hndl = " [HNDL ACTIVE]" if row["hndl_risk"] else ""
        print(f"\n  {i:>2}. {row['primitive']}{hndl}")
        print(f"      Status:   {row['status']}")
        print(f"      Urgency:  {row['urgency']}")
        print(f"      Migrate:  {row['migrate_to']}")
    print()


def main():
    analyzer = QuantumThreatAnalyzer()

    print("\n" + "#"*70)
    print("#  QUANTUM CRYPTOGRAPHIC THREAT ANALYSIS")
    print("#  Complete threat matrix + system analyzer + migration plan")
    print("#"*70)

    # 1 — Print matrix
    print_threat_matrix()

    # 2 — Analyze sample system configurations
    systems = [
        {
            "use_case": "Typical enterprise HTTPS (pre-migration)",
            "algorithms": {
                "key_exchange":     "ECDHE-P256",
                "authentication":   "RSA-2048",
                "bulk_encryption":  "AES-256",
                "message_auth":     "SHA-256",
            },
        },
        {
            "use_case": "Legacy VPN (OpenVPN default config)",
            "algorithms": {
                "key_exchange":     "DH-2048",
                "authentication":   "RSA-2048",
                "bulk_encryption":  "AES-128",
                "hmac":             "SHA-1",
            },
        },
        {
            "use_case": "Post-quantum migrated TLS (target state)",
            "algorithms": {
                "key_exchange":     "ML-KEM-768",
                "authentication":   "ML-DSA-65",
                "bulk_encryption":  "AES-256",
                "message_auth":     "SHA-384",
            },
        },
    ]

    print("  SYSTEM RISK ANALYSIS")
    print("  " + "-"*65)
    for config in systems:
        result = analyzer.analyze_system(config)
        print(f"\n  System: {result['use_case']}")
        print(f"  Overall Risk: {result['overall_risk']}")
        print(f"  {'Role':<22} {'Algorithm':<20} {'Status':<20} {'PQ Bits':<10} {'HNDL'}")
        print(f"  {'─'*75}")
        for comp in result["components"]:
            hndl = "YES" if comp["hndl_risk"] else "no"
            pq   = str(comp["pq_bits"])
            print(f"  {comp['role']:<22} {comp['algorithm']:<20} {comp['status']:<20} {pq:<10} {hndl}")

    # 3 — Migration priorities
    print_migration_plan(analyzer)

    # 4 — Explain quantum advantage
    analyzer.explain_quantum_advantage()

    print("  NIST PQC STANDARDS (published 2024)")
    print("  " + "-"*65)
    standards = [
        ("FIPS 203", "ML-KEM",    "Key encapsulation / key exchange (replaces RSA, ECDH)",   "2024"),
        ("FIPS 204", "ML-DSA",    "Digital signatures (replaces ECDSA, RSA-PSS)",             "2024"),
        ("FIPS 205", "SLH-DSA",   "Hash-based signatures (conservative, no lattice risk)",    "2024"),
        ("FIPS 206", "FN-DSA",    "Signature (Falcon, NTRU lattice)",                         "2025 est."),
    ]
    print(f"  {'Standard':<10} {'Algorithm':<12} {'Purpose':<48} {'Published'}")
    print(f"  {'─'*78}")
    for std, alg, purpose, year in standards:
        print(f"  {std:<10} {alg:<12} {purpose:<48} {year}")
    print()


if __name__ == "__main__":
    main()
