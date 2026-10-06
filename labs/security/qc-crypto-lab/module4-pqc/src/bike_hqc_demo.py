"""
CUSTOMER DEMO PITCH — BIKE and HQC vs ML-KEM Comparison
=========================================================
BIKE (Bit Flipping Key Encapsulation) and HQC (Hamming Quasi-Cyclic) are
alternative post-quantum KEMs based on code-based cryptography, submitted to
the NIST PQC process.

Unlike McEliece (random Goppa codes), BIKE and HQC use STRUCTURED codes
(quasi-cyclic LDPC and Reed-Muller codes) for compact keys.

This demo is a conceptual comparison — no large-scale simulation needed.
We show key/ciphertext sizes, security levels, decapsulation failure rates,
and operation timings for the three schemes.

Audience: Security architects, procurement teams, interview panels.
Runtime: < 2 seconds (no Qiskit needed).
"""

import math


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_sep(title: str = "") -> None:
    w = 68
    if title:
        p = (w - len(title) - 2) // 2
        print("=" * p + f" {title} " + "=" * (w - p - len(title) - 2))
    else:
        print("=" * w)


# ---------------------------------------------------------------------------
# Scheme parameter tables
# ---------------------------------------------------------------------------

# Source: NIST PQC Round 4 submissions + NIST SP 800-227 draft
SCHEMES = {
    "ML-KEM-512": {
        "type": "Lattice (Module-LWE)",
        "security_bits": 128,
        "pk_bytes":   800,
        "sk_bytes":  1632,
        "ct_bytes":   768,
        "ss_bytes":    32,
        "failure_rate": "2^-139",
        "keygen_us":    16,
        "encaps_us":    21,
        "decaps_us":    22,
        "nist_status": "Standard (FIPS 203)",
        "pq_safe": True,
        "notes": "Primary recommendation",
    },
    "ML-KEM-768": {
        "type": "Lattice (Module-LWE)",
        "security_bits": 192,
        "pk_bytes":  1184,
        "sk_bytes":  2400,
        "ct_bytes":  1088,
        "ss_bytes":    32,
        "failure_rate": "2^-164",
        "keygen_us":    25,
        "encaps_us":    28,
        "decaps_us":    29,
        "nist_status": "Standard (FIPS 203)",
        "pq_safe": True,
        "notes": "Recommended for most applications",
    },
    "ML-KEM-1024": {
        "type": "Lattice (Module-LWE)",
        "security_bits": 256,
        "pk_bytes":  1568,
        "sk_bytes":  3168,
        "ct_bytes":  1568,
        "ss_bytes":    32,
        "failure_rate": "2^-174",
        "keygen_us":    38,
        "encaps_us":    42,
        "decaps_us":    43,
        "nist_status": "Standard (FIPS 203)",
        "pq_safe": True,
        "notes": "Top security level",
    },
    "BIKE-L1": {
        "type": "Code (QC-MDPC)",
        "security_bits": 128,
        "pk_bytes":  1541,
        "sk_bytes":  3110,
        "ct_bytes":  1573,
        "ss_bytes":    32,
        "failure_rate": "2^-32 (residual)",
        "keygen_us":   600,
        "encaps_us":   700,
        "decaps_us":   700,
        "nist_status": "Round 4 Candidate (NIST SP 800-227 alt.)",
        "pq_safe": True,
        "notes": "Larger failure rate is a concern",
    },
    "BIKE-L3": {
        "type": "Code (QC-MDPC)",
        "security_bits": 192,
        "pk_bytes":  3083,
        "sk_bytes":  6206,
        "ct_bytes":  3115,
        "ss_bytes":    32,
        "failure_rate": "2^-64",
        "keygen_us":  1800,
        "encaps_us":  1900,
        "decaps_us":  1900,
        "nist_status": "Round 4 Candidate",
        "pq_safe": True,
        "notes": "Reduced failure rate at L3",
    },
    "HQC-128": {
        "type": "Code (QC Reed-Muller)",
        "security_bits": 128,
        "pk_bytes":  2249,
        "sk_bytes":  2289,
        "ct_bytes":  4481,
        "ss_bytes":    64,
        "failure_rate": "2^-128",
        "keygen_us":   150,
        "encaps_us":   200,
        "decaps_us":   800,
        "nist_status": "Round 4 Candidate",
        "pq_safe": True,
        "notes": "Large ciphertext",
    },
    "HQC-192": {
        "type": "Code (QC Reed-Muller)",
        "security_bits": 192,
        "pk_bytes":  4522,
        "sk_bytes":  4562,
        "ct_bytes":  9026,
        "ss_bytes":    64,
        "failure_rate": "2^-192",
        "keygen_us":   350,
        "encaps_us":   450,
        "decaps_us":  2000,
        "nist_status": "Round 4 Candidate",
        "pq_safe": True,
        "notes": "Very large ciphertext",
    },
}


def bar_chart(value: int, max_value: int, width: int = 25) -> str:
    filled = int(value / max_value * width)
    return "#" * filled + "." * (width - filled)


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    print_sep("BIKE & HQC vs ML-KEM — PQC KEM COMPARISON")
    print("Purpose: Compare post-quantum KEMs on size, speed, failure rate, status\n")

    # Size comparison
    print_sep("1. Key and Ciphertext Sizes (bytes)")
    max_pk = max(s["pk_bytes"] for s in SCHEMES.values())
    print(f"  {'Scheme':<14}  {'Type':<26}  {'PubKey':>7}  {'PrivKey':>7}  {'CT':>7}  {'SS':>5}  Visual (PubKey)")
    print(f"  {'-'*14}  {'-'*26}  {'-'*7}  {'-'*7}  {'-'*7}  {'-'*5}  {'-'*28}")
    for name, s in SCHEMES.items():
        bar = bar_chart(s["pk_bytes"], max_pk, width=25)
        print(f"  {name:<14}  {s['type']:<26}  {s['pk_bytes']:>7}  {s['sk_bytes']:>7}  "
              f"{s['ct_bytes']:>7}  {s['ss_bytes']:>5}  {bar}")

    print()

    # Speed comparison
    print_sep("2. Operation Speed (microseconds, reference hardware)")
    print(f"  {'Scheme':<14}  {'KeyGen (µs)':>12}  {'Encaps (µs)':>12}  {'Decaps (µs)':>12}  Notes")
    print(f"  {'-'*14}  {'-'*12}  {'-'*12}  {'-'*12}  {'-'*30}")
    for name, s in SCHEMES.items():
        print(f"  {name:<14}  {s['keygen_us']:>12}  {s['encaps_us']:>12}  {s['decaps_us']:>12}  {s['notes']}")

    print()

    # Failure rates
    print_sep("3. Decapsulation Failure Rates")
    print("""
  A 'decapsulation failure' means Alice and Bob derive DIFFERENT shared secrets
  even with no adversary — a correctness failure, not a security failure.
  Any failure means the session cannot be established.
  """)
    print(f"  {'Scheme':<14}  {'Failure Rate':>16}  {'Interpretation'}")
    print(f"  {'-'*14}  {'-'*16}  {'-'*50}")
    for name, s in SCHEMES.items():
        fr = s["failure_rate"]
        interp = "Negligible — crypto-standard" if "128" in fr or "139" in fr or \
                 "164" in fr or "174" in fr or "192" in fr or "64" in fr else \
                 "Moderate — may require retry logic"
        print(f"  {name:<14}  {fr:>16}  {interp}")

    print()

    # Security levels
    print_sep("4. Security Level vs NIST Category")
    print(f"  {'Scheme':<14}  {'Sec (bits)':>10}  {'NIST Cat.':>10}  {'PQ Safe':>8}  Status")
    print(f"  {'-'*14}  {'-'*10}  {'-'*10}  {'-'*8}  {'-'*40}")
    cat_map = {128: "Cat. 1", 192: "Cat. 3", 256: "Cat. 5"}
    for name, s in SCHEMES.items():
        cat = cat_map.get(s["security_bits"], "—")
        print(f"  {name:<14}  {s['security_bits']:>10}  {cat:>10}  {'Yes':>8}  {s['nist_status']}")

    print()

    # Algorithm selection guide
    print_sep("5. Algorithm Selection Guide")
    print("""
  Use case → Recommended scheme:

  General TLS/HTTPS key exchange:
    → ML-KEM-768 (FIPS 203, 1.1 KB public key, fast, NIST standard)

  Government/military (CNSA 2.0 requirements):
    → ML-KEM-1024 (FIPS 203, 256-bit security)

  Constrained IoT devices (minimal RAM):
    → ML-KEM-512 (smallest ML-KEM variant, still 128-bit PQ security)

  Defense-in-depth (hedge against ML-KEM breakthrough):
    → Hybrid: ML-KEM-768 + BIKE-L1  or  ML-KEM-768 + HQC-128
      (different mathematical foundations — break both = much harder)

  Long-term archival (decades):
    → McEliece-348864 (46-year analysis confidence) + ML-KEM hybrid

  High-speed server applications:
    → ML-KEM (10–50µs) vs BIKE (600–1900µs) vs HQC (150–2000µs)
    → ML-KEM wins on speed by 10–50× margin
""")

    print_sep("6. Mathematical Foundations Summary")
    rows = [
        ("ML-KEM",    "Module-LWE over rings",   "Lattice problems",    "1 year grid"),
        ("BIKE",      "QC-MDPC codes",            "Syndrome decoding",   "Sparser code"),
        ("HQC",       "Quasi-cyclic codes",       "NP-hard decoding",    "Structured codes"),
        ("McEliece",  "Binary Goppa codes",       "General decoding",    "46-year analysis"),
        ("RSA (ref)", "Integer factorisation",    "BROKEN by Shor",      "N/A"),
        ("ECDH (ref)","Discrete log on EC",       "BROKEN by Shor",      "N/A"),
    ]
    print(f"  {'Scheme':<12}  {'Math basis':<30}  {'Hard problem':<24}  Notes")
    print(f"  {'-'*12}  {'-'*30}  {'-'*24}  {'-'*25}")
    for name, basis, problem, note in rows:
        print(f"  {name:<12}  {basis:<30}  {problem:<24}  {note}")

    print()
    print_sep("Key Takeaway")
    print("""
  ML-KEM is the clear primary choice: fastest, smallest, NIST-standardized.
  BIKE and HQC offer code-based diversity — valuable insurance if an unexpected
  lattice attack emerges (very unlikely, but defense-in-depth is good practice).

  Practical migration path:
    1. Replace RSA/ECDH key exchange with ML-KEM-768 immediately.
    2. Add BIKE-L1 or HQC-128 as a secondary KEM for high-value sessions.
    3. Keep AES-256 for bulk encryption (Grover-resistant).
    4. Replace ECDSA/RSA signatures with ML-DSA or SLH-DSA (FIPS 204/205).
    Timeline: complete before 2030 per NIST/NSA CNSA 2.0 guidance.
""")
    print_sep()


if __name__ == "__main__":
    main()
