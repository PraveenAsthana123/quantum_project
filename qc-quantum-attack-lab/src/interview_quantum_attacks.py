"""
Interview Preparation: Quantum Attacks on Cryptography
=========================================================
10 expert-level Q&A pairs covering quantum attacks, HNDL, migration strategy,
and post-quantum standards. Designed for Principal Security Engineer,
Platform Architect, and Solution Architect interviews.

Each answer: technically precise, interview-ready, 150–200 words.

Educational use only — demonstrates defensive security concepts.
"""

QA_PAIRS = [
    # ─────────────────────────────────────────────────────────────────────────
    {
        "id":       1,
        "question": "Explain Shor's algorithm to a non-technical executive.",
        "level":    "Strategic / Executive",
        "answer": """
Imagine RSA encryption as a combination lock whose security comes from a math problem:
multiplying two giant prime numbers together is easy, but factoring the result back into
those primes takes so long that classical computers would need billions of years.

Shor's algorithm exploits a phenomenon unique to quantum computers called superposition —
the ability to explore an enormous number of possibilities simultaneously rather than one
at a time. It essentially finds a mathematical "rhythm" hidden inside the factoring problem
using a technique called the Quantum Fourier Transform, reducing what is an exponential
problem to a manageable, polynomial one.

The practical consequence: a sufficiently powerful quantum computer could factor a 2048-bit
RSA key — the standard for most of today's secure communications — in approximately 8 hours
rather than billions of years. Every TLS certificate, VPN, digital signature, and encrypted
email that depends on RSA or elliptic curve cryptography becomes retroactively readable. This
is not a faster computer doing the same work — it is a fundamentally different algorithm that
removes the mathematical hardness entirely.
""",
    },
    # ─────────────────────────────────────────────────────────────────────────
    {
        "id":       2,
        "question": "Why can't we just double RSA key sizes to be safe against quantum?",
        "level":    "Technical Depth",
        "answer": """
Doubling RSA key sizes works against classical attackers because integer factoring has
sub-exponential classical complexity — doubling key bits more than doubles the work. But
Shor's Algorithm has polynomial quantum complexity: O(n³) quantum operations where n is
the key bit-length.

For RSA-2048: approximately 4,099 logical qubits, ~8 hours on a CRQC (Gidney & Ekerå 2021).
For RSA-4096: approximately 8,195 logical qubits, ~4 days on the same machine.

Doubling the key only adds about 4 days — it does not change the asymptotic complexity
class. The quantum computer now solves a modestly harder instance of the same polynomial
problem. There is no key size that makes RSA quantum-safe; the mathematical structure that
Shor's exploits (the hidden subgroup in the multiplicative group mod N) is inherent to
RSA's construction, not its key length.

This is categorically different from AES, where doubling key size (128→256 bits)
restores full security because Grover's speedup is only quadratic. RSA has no analog.
The correct response is to migrate to lattice-based or hash-based algorithms where no
quantum speedup of this type is known.
""",
    },
    # ─────────────────────────────────────────────────────────────────────────
    {
        "id":       3,
        "question": "What is the difference between the Shor's and Grover's quantum threat?",
        "level":    "Technical Depth",
        "answer": """
Shor's and Grover's algorithms represent two completely different threat profiles.

Shor's Algorithm solves the Hidden Subgroup Problem in abelian groups — integer factoring
and discrete logarithm problems both reduce to this. For RSA and ECC, this provides an
exponential-to-polynomial speedup: classical sub-exponential complexity becomes polynomial
O(n³). The quantum security of RSA-2048 is effectively zero bits — no key size fixes it.

Grover's Algorithm solves unstructured search quadratically. For a keyspace of size 2^n,
Grover needs O(2^(n/2)) operations instead of O(2^n). Applied to AES: the effective
security is halved. AES-128 drops to 64-bit quantum security (CRITICAL). AES-256 drops
to 128-bit quantum security (SAFE by NIST standards).

The operational difference: Shor's demands immediate migration for all asymmetric
cryptography — no key length compensates. Grover's is manageable by doubling symmetric
key lengths. This is why NIST's guidance is nuanced: migrate all RSA/ECC to ML-KEM/ML-DSA,
but upgrading AES-128 to AES-256 is sufficient for symmetric systems. Hash functions
(SHA-256+) retain adequate security at current sizes.
""",
    },
    # ─────────────────────────────────────────────────────────────────────────
    {
        "id":       4,
        "question": "What is HNDL and how urgent is the threat today?",
        "level":    "Strategic / Risk",
        "answer": """
HNDL — Harvest Now, Decrypt Later — is the strategy of capturing and archiving
encrypted traffic today with the intent to decrypt it once a Cryptographically
Relevant Quantum Computer (CRQC) becomes available. It is not a future threat;
it is an active operation today.

Nation-state adversaries intercept and store encrypted communications at fiber
interception points, compromised routers, and cloud infrastructure. Storage costs
are negligible at scale — storing 2+ exabytes per year of targeted TLS traffic costs
under $20 million, trivial for a tier-one intelligence budget.

The urgency is defined by data retention requirements versus the CRQC timeline. If
your organization handles classified communications, 30-year financial records,
pharmaceutical patents, or military intelligence, any data encrypted today under
RSA or ECDH must be assumed potentially readable in 2033. The Mosca Inequality frames
it precisely: if migration_years + protection_required_years > years_until_CRQC,
you are already late.

In practice: a government agency using TLS 1.3 with ECDHE-P256 today is creating
traffic that adversaries will decrypt in 7 years. Even TLS Perfect Forward Secrecy
does not help — Shor's Algorithm recovers the ECDH private key directly from the
public key, retroactively compromising all ephemeral sessions.
""",
    },
    # ─────────────────────────────────────────────────────────────────────────
    {
        "id":       5,
        "question": "Which systems need to migrate to post-quantum cryptography first?",
        "level":    "Architecture / Prioritization",
        "answer": """
Priority should be determined by the intersection of three factors: HNDL sensitivity,
data retention period, and migration complexity. The ordering I recommend:

First: Any system transmitting data with multi-decade protection requirements —
classified government communications, military systems, long-duration financial
instruments (30-year bonds), and pharmaceutical IP with 20-year patent periods.
These face active HNDL risk now.

Second: PKI infrastructure — root CAs, code signing pipelines, and certificate
authorities. A quantum-compromised root CA invalidates every certificate signed
downstream, making CA migration a platform-level dependency for everything else.

Third: TLS termination for sensitive APIs and microservices. Deploy hybrid
X25519+ML-KEM-768 key exchange (now supported in Cloudflare, Google Chrome, AWS)
as an interim measure before full certificate migration.

Fourth: VPN and remote access (IKEv2, OpenVPN) — replace DH/ECDH with ML-KEM,
RSA/ECDSA authentication with ML-DSA.

Fifth: SSH infrastructure, code signing, firmware signing.

Lower urgency but required: internal HR, general email, and consumer-facing HTTPS
with short-lived data. The constraint is usually engineering capacity, not technical
feasibility — maintain a live CBOM to track progress and identify gaps.
""",
    },
    # ─────────────────────────────────────────────────────────────────────────
    {
        "id":       6,
        "question": "How long until quantum computers break RSA-2048?",
        "level":    "Technical Uncertainty / Executive Comms",
        "answer": """
The honest answer is a range with stated confidence levels, not a single date.
Based on published hardware roadmaps and independent academic assessments:

Optimistic (10% probability): 2029. Assumes rapid breakthrough in error correction
overhead and qubit connectivity. This is a planning bound — assume it is possible,
do not assume it is inevitable by that date.

Moderate (50% probability): 2033. Consistent with IBM's published roadmap targeting
100,000 physical qubits with fault tolerance, Google Willow's below-threshold error
correction milestone, and the Gidney & Ekerå (2021) resource estimate of ~4 million
physical qubits for RSA-2048.

Conservative (90% probability): 2038. Even accounting for significant engineering
barriers — qubit connectivity, classical control electronics, cryogenic scaling —
this horizon is achievable.

The critical insight for planning: enterprise-wide cryptographic migration takes
3–7 years. A 2033 target with a 3-year migration cycle means organizations must
begin NOW to complete before the moderate estimate. The data you are encrypting
today under RSA must remain secure past 2033 — which means RSA is the wrong
choice starting today, not starting in 2030.
""",
    },
    # ─────────────────────────────────────────────────────────────────────────
    {
        "id":       7,
        "question": "Is AES-256 quantum-safe?",
        "level":    "Technical Precision",
        "answer": """
Yes — with an important technical nuance worth demonstrating in an interview.

AES-256 is quantum-safe because Grover's Algorithm provides only a quadratic
speedup for key search, reducing effective security from 256 bits to 128 bits.
NIST's post-quantum security target is 128 bits; AES-256 meets this threshold.
The 2^128 quantum operations required remain computationally infeasible even for
the most aggressive CRQC projections.

AES-128, however, is not quantum-safe. Grover's reduces it to 64-bit effective
security, which is below NIST's 112-bit minimum threshold and well below the
128-bit quantum security target. This is why NIST SP 800-131A explicitly
recommends transitioning from AES-128 to AES-256 as part of quantum readiness.

The deeper principle: Grover's speedup applies to all unstructured search problems
and cannot be overcome by any structural improvement to AES. The correct mitigation
is simply key length — 256-bit keys absorb the quadratic speedup and remain secure.
This is categorically different from RSA and ECC, where no key length provides
safety against Shor's exponential-to-polynomial speedup.

For exam-style precision: AES-256 offers 128-bit post-quantum security; AES-128
offers 64-bit post-quantum security.
""",
    },
    # ─────────────────────────────────────────────────────────────────────────
    {
        "id":       8,
        "question": "What NIST post-quantum standards should we adopt, and on what timeline?",
        "level":    "Standards / Architecture",
        "answer": """
NIST finalized its first three post-quantum cryptographic standards in August 2024:

FIPS 203 — ML-KEM (Module Lattice Key Encapsulation Mechanism, originally CRYSTALS-Kyber):
replaces RSA and ECDH for key exchange and key encapsulation. ML-KEM-768 provides 184-bit
post-quantum security and is the recommended default. Deploy in TLS 1.3 (hybrid
X25519+ML-KEM-768 is already deployed by Cloudflare, Google, AWS).

FIPS 204 — ML-DSA (Module Lattice Digital Signature Algorithm, originally CRYSTALS-Dilithium):
replaces ECDSA and RSA-PSS for digital signatures. ML-DSA-65 is the recommended level.
Use for TLS certificates, code signing, JWT, and SSH keys.

FIPS 205 — SLH-DSA (Stateless Hash-Based Digital Signature, originally SPHINCS+): hash-based
signatures with no lattice assumptions. Larger signatures but conservative security. Preferred
where lattice assumptions are a concern or for firmware/TPM signing.

FIPS 206 (FN-DSA / Falcon): expected 2025 — NTRU lattice-based signature, smaller than ML-DSA.

Timeline recommendation: TLS key exchange (ML-KEM hybrid) immediately; PKI/certificate
migration by 2027; full RSA/ECDSA retirement by 2030. Follow NSA CNSA 2.0 deadlines for
any National Security System scope.
""",
    },
    # ─────────────────────────────────────────────────────────────────────────
    {
        "id":       9,
        "question": "How do we test whether our PQC migration is complete?",
        "level":    "Operations / Engineering",
        "answer": """
Completing a PQC migration requires four verification layers, not just a feature flag audit:

First, build and maintain a Cryptographic Bill of Materials (CBOM). Tools like
IBM's CBOM generation tooling, Keyfactor, or custom scripts scanning TLS handshakes,
code dependencies, JVM/OpenSSL configurations, and HSM slot assignments provide an
inventory. A CBOM is your ground truth — you cannot migrate what you cannot enumerate.

Second, automated TLS handshake scanning. Use tools like testssl.sh, SSLyze, or
custom OpenSSL probes to verify that every endpoint negotiates ML-KEM (FIPS 203)
for key exchange and rejects legacy RSA/ECDH-only ciphers. This catches misconfigured
load balancers and legacy microservices missed by manual audits.

Third, certificate chain verification. Confirm that all certificates in the chain
(leaf, intermediate, root) use ML-DSA or SLH-DSA, not legacy ECDSA/RSA. Certificate
transparency logs and internal CA inventory tools help here.

Fourth, crypto agility testing. Verify the system can update cryptographic primitives
without application redeployment — a configuration-driven or library-abstracted
cryptographic layer means future algorithm changes can be deployed as configuration,
not code changes. This is the non-negotiable architectural property that prevents
the current migration situation from recurring.
""",
    },
    # ─────────────────────────────────────────────────────────────────────────
    {
        "id":       10,
        "question": "What is crypto agility and why does it matter for enterprise migration?",
        "level":    "Architecture / Long-Term",
        "answer": """
Crypto agility is the architectural property that allows a system to switch
cryptographic algorithms, key sizes, or primitives through configuration — not
through code changes or service redeployment. It is the single most important
engineering principle for long-term cryptographic resilience.

Its importance for the current PQC migration is direct: systems without crypto
agility require application-layer changes to every service that handles keys,
certificates, or signatures. In a typical enterprise with hundreds of microservices,
legacy JVM applications, hardware security modules, and embedded systems, this
becomes a multi-year rearchitecture project rather than a controlled migration.

With crypto agility, the cryptographic primitive is abstracted behind an interface
or configuration layer. When NIST standardizes a new algorithm or deprecates an
existing one, the change propagates via a configuration update — analogous to how
TLS cipher suite negotiation already works in modern TLS stacks.

Concrete implementation: maintain a centralized key management service (HashiCorp
Vault, AWS KMS, Azure Key Vault) with algorithm-neutral API abstractions; enforce
that no application hardcodes RSA or EC key types; use a library-level abstraction
(OpenSSL's ENGINE API, Java JCA provider interface, Bouncy Castle) that exposes
algorithm selection as a runtime parameter. The cost of building this now is small
relative to the cost of migrating a crypto-agility-less system under time pressure.
""",
    },
]


def print_qa(qa: dict, verbose: bool = True) -> None:
    """Print a single Q&A pair, formatted for terminal output."""
    print(f"\n{'─'*70}")
    print(f"  Q{qa['id']:02d}  [{qa['level']}]")
    print(f"  QUESTION: {qa['question']}")
    print(f"{'─'*70}")
    if verbose:
        # Clean up leading/trailing whitespace in answer
        answer = qa["answer"].strip()
        # Word-wrap to ~68 chars for readability
        words  = answer.split()
        line   = "  "
        for word in words:
            if len(line) + len(word) + 1 > 68:
                print(line)
                line = "  " + word
            else:
                line += (" " if line.strip() else "") + word
        if line.strip():
            print(line)


def print_quick_reference() -> None:
    """One-line summary of each Q&A for rapid review."""
    print("\n" + "="*70)
    print("  QUICK REFERENCE — 10 QUANTUM ATTACK INTERVIEW TOPICS")
    print("="*70)
    summaries = [
        (1,  "Shor's = quantum superposition finds RSA period → factors in hours"),
        (2,  "Doubling RSA keys only adds days on CRQC; polynomial complexity unchanged"),
        (3,  "Shor's = exponential→poly (RSA/ECC broken); Grover's = quadratic (AES weakened)"),
        (4,  "HNDL is active NOW; encrypted traffic collected today, decrypted in 2033"),
        (5,  "Migrate by HNDL sensitivity: gov/military/pharma first, then PKI, TLS, VPN"),
        (6,  "RSA-2048 breaks by 2029 (10%), 2033 (50%), 2038 (90%); 3-yr migration cycle"),
        (7,  "AES-256 = SAFE (128-bit PQ security); AES-128 = CRITICAL (64-bit → upgrade)"),
        (8,  "FIPS 203 ML-KEM (key exchange) + FIPS 204 ML-DSA (signatures) + FIPS 205 SLH-DSA"),
        (9,  "Verify via CBOM + TLS handshake scanning + cert chain audit + agility test"),
        (10, "Crypto agility = algorithm switchable via config not code; enables rapid response"),
    ]
    for num, summary in summaries:
        print(f"  Q{num:02d}: {summary}")
    print()


def main():
    print("\n" + "#"*70)
    print("#  QUANTUM ATTACK INTERVIEW PREPARATION")
    print("#  10 Expert Q&As for Principal / Architect Level Roles")
    print("#"*70)

    print_quick_reference()

    print("\n" + "="*70)
    print("  FULL Q&A ANSWERS")
    print("="*70)
    for qa in QA_PAIRS:
        print_qa(qa, verbose=True)

    print(f"\n{'─'*70}")
    print(f"  Total: {len(QA_PAIRS)} Q&As covering Shor's, Grover's, HNDL, migration,")
    print(f"         NIST standards, crypto agility, and verification strategy.")
    print()


if __name__ == "__main__":
    main()
