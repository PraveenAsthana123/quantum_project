"""
Interview Attack Preparation
=============================
Q&A preparation for discussing cryptographic attacks and quantum security
in technical interviews (Principal Security Engineer, PQC Architect, etc.)

Defensive Security Educational Lab — /mnt/deepa/quantum/qc-attack-lab/
"""

from dataclasses import dataclass, field


@dataclass
class QA:
    section: str
    question: str
    answer: str
    key_phrases: list[str] = field(default_factory=list)
    follow_up: str = ""

    def display(self, number: int):
        print(f"\n  Q{number}: {self.question}")
        print(f"  {'─' * 72}")
        # Wrap answer at ~80 chars for readability
        words = self.answer.split()
        line, lines = [], []
        for word in words:
            line.append(word)
            if len(" ".join(line)) > 78:
                lines.append("  A: " + " ".join(line[:-1]) if len(lines) == 0 else "     " + " ".join(line[:-1]))
                line = [word]
        if line:
            lines.append(("  A: " if not lines else "     ") + " ".join(line))
        # Simpler approach: just indent the whole answer
        answer_lines = self.answer.split(". ")
        print(f"  A: {answer_lines[0]}.")
        for sentence in answer_lines[1:]:
            if sentence.strip():
                print(f"     {sentence.strip()}.")
        if self.key_phrases:
            print(f"  ★  Key phrases: {' | '.join(self.key_phrases)}")
        if self.follow_up:
            print(f"  ↳  Follow-up: {self.follow_up}")


# ---------------------------------------------------------------------------
# Section 1: Classical Cryptographic Vulnerabilities
# ---------------------------------------------------------------------------

SECTION_1: list[QA] = [

    QA(
        section="Classical Crypto Vulnerabilities",
        question="Why is RSA-2048 considered 'safe' classically but still on the migration list?",
        answer=(
            "RSA-2048 provides approximately 112 bits of classical security — meaning the best "
            "known classical algorithm (GNFS) requires roughly 2^112 operations to factor a "
            "2048-bit modulus, which is computationally infeasible today. "
            "However, RSA provides zero bits of quantum security against Shor's algorithm "
            "running on a fault-tolerant quantum computer (FTQC). "
            "Shor's algorithm reduces factoring from sub-exponential classical difficulty — "
            "O(exp((log N)^(1/3))) — to polynomial quantum time — specifically O((log N)^3) "
            "quantum gate operations. "
            "Gidney and Ekerå (2021) showed RSA-2048 can be factored in ~8 hours using "
            "20 million noisy qubits on an FTQC. "
            "The migration urgency comes from HNDL: adversaries recording today's RSA-protected "
            "traffic can decrypt it retroactively once a CRQC exists (~2030–2035)."
        ),
        key_phrases=["112-bit classical", "zero quantum security", "Shor's O((log N)^3)", "HNDL", "CRQC 2030-2035"],
        follow_up="What is the NIST-recommended replacement for RSA key exchange?",
    ),

    QA(
        section="Classical Crypto Vulnerabilities",
        question="Explain the Bleichenbacher '98 attack and why it's still relevant in 2026.",
        answer=(
            "The Bleichenbacher '98 attack is an adaptive chosen-ciphertext attack against "
            "RSA with PKCS#1 v1.5 padding. The attacker queries a padding oracle — any system "
            "that distinguishes 'correctly padded' from 'incorrectly padded' RSA ciphertexts, "
            "even through timing differences or different error codes. "
            "By sending millions of crafted ciphertexts (typically 1–14 million queries for "
            "RSA-2048), the attacker narrows down the plaintext using interval arithmetic. "
            "It remains relevant because: (1) PKCS#1 v1.5 is still widely deployed in legacy "
            "TLS 1.2 stacks; (2) the ROBOT attack (2017) found it in F5, Cisco, Citrix, "
            "Facebook, and PayPal; (3) any timing difference in error handling creates an oracle. "
            "Defense: use RSA-OAEP (PKCS#1 v2), which is CCA2-secure; TLS 1.3 removes "
            "RSA key transport entirely."
        ),
        key_phrases=["padding oracle", "adaptive chosen-ciphertext", "1M queries", "ROBOT 2017", "RSA-OAEP CCA2"],
        follow_up="What makes RSA-OAEP resistant to this attack?",
    ),

    QA(
        section="Classical Crypto Vulnerabilities",
        question="What is a timing side-channel attack and how does constant-time code defend against it?",
        answer=(
            "A timing side-channel attack exploits measurable differences in execution time "
            "to infer secret information. In naive RSA square-and-multiply, the exponentiation "
            "loop performs an extra multiplication when a key bit is 1 — leaking key bits "
            "through response time measurements, even over a network. "
            "Kocher (1996) demonstrated this with ~1000 timing measurements on smart cards. "
            "Constant-time implementations eliminate secret-dependent branches: "
            "the Montgomery ladder always performs two multiplications per bit regardless of "
            "the bit value, discarding one result — the total work is identical for 0 and 1 bits. "
            "The key principle: no branch, no memory access pattern, no loop count should "
            "depend on secret data. "
            "OpenSSL's RSA blinding adds a random mask r to the message before exponentiation "
            "and removes it after, so each operation sees a different value even for the same input. "
            "In hardware, TVLA (Test Vector Leakage Assessment) with t-test statistics below 4.5 "
            "is required for FIPS 140-3 certification."
        ),
        key_phrases=["secret-dependent branch", "Montgomery ladder", "RSA blinding", "TVLA", "FIPS 140-3"],
        follow_up="How does AI (machine learning) amplify timing attacks?",
    ),

    QA(
        section="Classical Crypto Vulnerabilities",
        question="Explain the birthday attack and why SHA-1 is considered broken.",
        answer=(
            "The birthday attack exploits the birthday paradox: for a hash function with "
            "n-bit output, you expect a collision after approximately 2^(n/2) random inputs "
            "— not 2^n. This is the birthday bound. "
            "SHA-1 has a 160-bit output, so the birthday bound is 2^80. "
            "In 2005, Wang et al. found a theoretical collision attack in 2^69 operations. "
            "In 2017, Google's SHAttered project computed the first real SHA-1 collision "
            "using ~2^63.1 operations — specifically two different PDF files with identical "
            "SHA-1 hashes. This took ~6,500 CPU-years and ~110 GPU-years. "
            "SHA-1 is now banned in TLS certificates (RFC 8181), code signing, and "
            "most security protocols. "
            "SHA-256 provides 2^128 collision resistance (birthday bound of 256-bit output), "
            "which is safe classically. "
            "Quantum note: the BHT quantum walk algorithm reduces SHA-256 collision resistance "
            "to 2^85 — marginal, so SHA-384 is preferred for long-term security."
        ),
        key_phrases=["birthday bound 2^(n/2)", "SHAttered 2017", "2^63.1", "SHA-384 preferred", "BHT algorithm"],
        follow_up="What does Grover's algorithm do to SHA-256 preimage resistance?",
    ),

    QA(
        section="Classical Crypto Vulnerabilities",
        question="Describe a man-in-the-middle attack on unauthenticated Diffie-Hellman.",
        answer=(
            "In classic (unauthenticated) Diffie-Hellman, Alice and Bob exchange public "
            "values g^a and g^b over an untrusted channel. Eve, positioned on the network, "
            "intercepts both values and substitutes her own: she sends g^e1 to Bob pretending "
            "to be Alice, and g^e2 to Alice pretending to be Bob. "
            "Now Alice computes shared secret S_AE = g^(a*e2) with Eve, "
            "and Bob computes S_BE = g^(b*e1) with Eve — neither with each other. "
            "Eve decrypts traffic from Alice with S_AE, re-encrypts it with S_BE, and forwards "
            "to Bob — neither party detects the interception. "
            "This is why DH without authentication is known as 'anonymous DH' and is removed "
            "from TLS 1.3. "
            "The fix is always to authenticate DH with certificates (SIGMA protocol, STS), "
            "or use pre-shared keys. "
            "In TLS 1.3, ECDHE ephemeral keys are authenticated with the server's certificate "
            "via a CertificateVerify message signed with the server's private key."
        ),
        key_phrases=["anonymous DH", "unauthenticated", "SIGMA protocol", "CertificateVerify", "TLS 1.3 ECDHE"],
        follow_up="How does mTLS prevent this attack in microservices?",
    ),

    QA(
        section="Classical Crypto Vulnerabilities",
        question="What is JWT algorithm confusion and how do you prevent it?",
        answer=(
            "JWT algorithm confusion occurs when an attacker manipulates the 'alg' header field "
            "in a JSON Web Token to trick the server into accepting an invalid signature. "
            "The classic variant is the 'alg=none' attack: the attacker removes the signature, "
            "sets alg=none, and submits the token — a naive server that trusts the header's "
            "algorithm field accepts it as 'unsigned but valid'. "
            "A second variant is RS256-to-HS256 confusion: if a server accepts both, an attacker "
            "signs the token with HS256 using the server's RSA public key as the HMAC secret "
            "(which is public knowledge) and the server verifies it thinking it's HS256. "
            "Prevention: (1) hard-code the expected algorithm server-side — never read it from "
            "the token header; (2) reject 'none' and 'null' algorithms unconditionally; "
            "(3) use separate keys for different algorithms; (4) validate jti and exp claims. "
            "The JOSE security BCP (RFC 8725) documents all JWT implementation pitfalls."
        ),
        key_phrases=["alg=none", "RS256-to-HS256", "hard-code algorithm", "RFC 8725", "jti validation"],
        follow_up="What is DPoP and how does it prevent JWT replay?",
    ),

    QA(
        section="Classical Crypto Vulnerabilities",
        question="How does a padding oracle attack work at a conceptual level?",
        answer=(
            "A padding oracle is any system that reveals whether a decrypted ciphertext has "
            "valid padding — through an error message, timing difference, or behavior difference. "
            "In PKCS#7 block cipher padding (used in CBC mode), the last block must end with "
            "N bytes each equal to N (e.g., 4 bytes of 0x04). "
            "The Padding Oracle On Downgraded Legacy Encryption (POODLE) and BEAST attacks "
            "exploit this in SSL/TLS. "
            "The attacker modifies the second-to-last ciphertext block and sends the modified "
            "ciphertext for decryption, observing whether the oracle says 'valid padding'. "
            "By systematically XOR-ing the modified byte and observing valid/invalid responses, "
            "the attacker recovers the plaintext byte by byte — at most 256 queries per byte. "
            "Defense: authenticated encryption (AES-GCM) replaces MAC-then-encrypt, "
            "eliminating the padding step entirely. "
            "AES-GCM provides both confidentiality and integrity — any ciphertext modification "
            "is detected by the authentication tag check before decryption even begins."
        ),
        key_phrases=["CBC padding", "POODLE", "256 queries per byte", "AES-GCM", "authenticate then decrypt"],
        follow_up="What is the 'Manger attack' and how does it relate to Bleichenbacher?",
    ),

    QA(
        section="Classical Crypto Vulnerabilities",
        question="What is nonce reuse in AES-GCM and why is it catastrophic?",
        answer=(
            "AES-GCM (Galois/Counter Mode) requires a unique nonce (IV) for every encryption "
            "operation with the same key. If the same nonce is used twice with the same key — "
            "even once — the entire security breaks down. "
            "AES-GCM produces a keystream K = AES(key, nonce || counter). "
            "If nonce N is reused for two plaintexts P1 and P2, the ciphertexts are: "
            "C1 = P1 XOR K and C2 = P2 XOR K. "
            "C1 XOR C2 = P1 XOR P2 — the attacker now has the XOR of the two plaintexts. "
            "If either plaintext is known or partially known (e.g., HTTP headers), "
            "the other is trivially recovered. "
            "Worse: nonce reuse in AES-GCM also leaks the authentication key H = AES(key, 0), "
            "allowing the attacker to forge arbitrary authenticated ciphertexts (full authentication break). "
            "The Forbidden Attack (Joux 2006) and Nonce Disrespect (Bock et al. 2016, TLS) "
            "demonstrate this on real systems. "
            "Defense: use deterministic nonce derivation (counter + key ID), or "
            "AES-GCM-SIV (RFC 8452) which is nonce-misuse resistant by design."
        ),
        key_phrases=["nonce reuse", "keystream XOR", "Forbidden Attack", "H-key forgery", "AES-GCM-SIV"],
        follow_up="What is misuse-resistant authenticated encryption and when do you need it?",
    ),
]


# ---------------------------------------------------------------------------
# Section 2: Quantum Computing Attacks
# ---------------------------------------------------------------------------

SECTION_2: list[QA] = [

    QA(
        section="Quantum Computing Attacks",
        question="Explain Shor's algorithm in plain terms and its impact on RSA.",
        answer=(
            "Shor's algorithm (1994) is a quantum algorithm for integer factorization and "
            "discrete logarithm that runs in polynomial time on a quantum computer. "
            "The classical difficulty of RSA relies on the fact that factoring N = p*q is "
            "believed to require sub-exponential time classically — specifically O(exp(c*(log N)^(1/3))) "
            "for the General Number Field Sieve. "
            "Shor's reduces this to O((log N)^3) quantum gate operations by exploiting quantum "
            "parallelism and the quantum Fourier transform to find the period r of f(x) = a^x mod N. "
            "Once r is found, with high probability gcd(a^(r/2) ± 1, N) gives the factors p and q. "
            "For RSA-2048, this requires approximately 4,098 logical qubits (Gidney & Ekerå 2021). "
            "With current physical qubit error rates (~0.1%), achieving 4,098 logical qubits "
            "requires approximately 1 billion physical qubits using surface code error correction. "
            "A CRQC (Cryptographically Relevant Quantum Computer) capable of this is estimated "
            "at 2030–2035. "
            "The implication: RSA-2048 provides ZERO quantum security regardless of key size."
        ),
        key_phrases=["O((log N)^3)", "quantum Fourier transform", "period finding", "4098 logical qubits", "CRQC 2030-2035"],
        follow_up="What is the difference between logical and physical qubits?",
    ),

    QA(
        section="Quantum Computing Attacks",
        question="How does Grover's algorithm affect symmetric cryptography (AES)?",
        answer=(
            "Grover's algorithm (1996) provides a quadratic speedup for unstructured search. "
            "For a function with N possible inputs, classical exhaustive search requires O(N) "
            "operations; Grover's requires O(√N). "
            "Applied to AES key search: AES-128 has 2^128 possible keys. "
            "Grover's reduces this to O(√(2^128)) = O(2^64) operations — providing 64 bits "
            "of effective quantum security. "
            "NIST considers 2^64 as borderline acceptable (below their 128-bit security threshold), "
            "so AES-128 is classified as CRITICAL concern in the quantum era. "
            "AES-256 has 2^256 keys; Grover's reduces to O(2^128) — this is ACCEPTABLE "
            "and AES-256 is quantum-safe. "
            "Important caveat: Grover's speedup for AES is limited by circuit depth — "
            "the AES oracle circuit has high depth, so the quantum speedup is offset by "
            "the per-iteration cost. Practical quantum attacks on AES-128 require "
            "~2953 logical qubits and significant gate depth (Grassl et al. 2016). "
            "The practical recommendation: upgrade to AES-256 for all applications."
        ),
        key_phrases=["O(√N) quadratic speedup", "64-bit effective security", "AES-256 quantum-safe", "2953 logical qubits", "Grassl 2016"],
        follow_up="Why is the quadratic speedup of Grover's less dramatic than Shor's exponential speedup?",
    ),

    QA(
        section="Quantum Computing Attacks",
        question="What is the difference between Shor's and Grover's impact on cryptography?",
        answer=(
            "Shor's algorithm provides an EXPONENTIAL quantum speedup over the best classical "
            "algorithms for factoring and discrete logarithm. "
            "This breaks RSA, DSA, ECDSA, ECDH, and DH completely — all public-key cryptography "
            "based on these mathematical problems is fundamentally compromised. "
            "The security reduction is catastrophic: RSA-2048 drops from 112-bit classical "
            "security to 0-bit quantum security. Algorithm replacement is mandatory. "
            "Grover's algorithm provides only a QUADRATIC speedup for symmetric key search. "
            "This halves the effective key length: AES-128 → 64-bit effective security (bad), "
            "AES-256 → 128-bit effective security (acceptable). "
            "The fix for Grover's is simple: double key sizes. AES-256 is already quantum-safe. "
            "The practical implication: public-key cryptography (RSA, ECC) requires full "
            "algorithm replacement with PQC (ML-KEM, ML-DSA); symmetric cryptography (AES, SHA) "
            "requires only key size increases."
        ),
        key_phrases=["exponential vs quadratic", "algorithm replacement vs key doubling", "ML-KEM ML-DSA", "0-bit quantum security", "AES-256 sufficient"],
        follow_up="Name the four NIST PQC standardized algorithms and what they replace.",
    ),

    QA(
        section="Quantum Computing Attacks",
        question="Explain the quantum resource requirements for attacking ECDSA P-256.",
        answer=(
            "ECDSA P-256 security relies on the elliptic curve discrete logarithm problem (ECDLP): "
            "given a public key Q = d*G, recover the private scalar d. "
            "Classically, the best ECDLP algorithm is Pollard's rho with O(√p) operations "
            "on a p-element group — giving 128-bit security for P-256. "
            "Shor's algorithm has an ECDLP variant (Roetteler et al. 2017) that requires "
            "approximately 2,330 logical qubits for P-256. "
            "The Toffoli gate count is approximately 8.1 × 10^11 — much higher than RSA "
            "factoring per qubit because elliptic curve arithmetic requires deeper circuits. "
            "Importantly, ECDSA exposes the private key from ANY signed message — "
            "the public key is published in every certificate and blockchain transaction. "
            "This makes HNDL particularly dangerous for ECDSA: every Bitcoin UTXO with an "
            "exposed public key is vulnerable retroactively once a CRQC exists. "
            "Defense: ML-DSA (CRYSTALS-Dilithium) for signatures, ML-KEM for ECDH replacement."
        ),
        key_phrases=["2330 logical qubits", "Roetteler 2017", "8.1e11 Toffoli gates", "private key from any signature", "Bitcoin UTXO risk"],
        follow_up="Why does ECDSA with nonce reuse (k-reuse) immediately expose the private key even classically?",
    ),

    QA(
        section="Quantum Computing Attacks",
        question="What does 'logical qubit' mean vs 'physical qubit', and why does the gap matter for CRQC timelines?",
        answer=(
            "A physical qubit is an actual quantum hardware element (superconducting transmon, "
            "trapped ion, photonic, spin qubit). Current physical qubits have error rates "
            "of 0.1–1% per gate operation — far too noisy for Shor's algorithm. "
            "A logical qubit is an error-corrected qubit constructed from many physical qubits "
            "using a quantum error-correcting code (e.g., surface code, LDPC codes). "
            "Surface code requires approximately 1,000 physical qubits per logical qubit "
            "at a 0.1% physical error rate to achieve fault-tolerant operation. "
            "For RSA-2048 (4,098 logical qubits), this implies roughly 4 million physical qubits "
            "at 0.1% error rate — some estimates (Gidney & Ekerå 2021) optimize to ~20 million "
            "physical qubits using magic state distillation factories. "
            "Current state-of-the-art: IBM Heron (133 qubits), Google Willow (105 qubits). "
            "The gap from ~100 physical qubits to 20 million at sufficient fidelity is the "
            "primary reason CRQC timelines are 2030–2035 rather than imminent. "
            "However, the HNDL threat means this gap does NOT reduce urgency for data with "
            "10+ year confidentiality requirements."
        ),
        key_phrases=["1000 physical per logical", "20 million physical qubits", "surface code", "IBM Heron Google Willow", "HNDL urgency unchanged"],
        follow_up="What is magic state distillation and why does it dominate qubit overhead?",
    ),

    QA(
        section="Quantum Computing Attacks",
        question="Name the four NIST PQC standardized algorithms and what each replaces.",
        answer=(
            "In August 2024, NIST finalized four post-quantum cryptography standards: "
            "1. FIPS 203 — ML-KEM (Module Lattice-based Key Encapsulation Mechanism, "
            "from CRYSTALS-Kyber). Replaces RSA and ECDH for key encapsulation and "
            "key exchange. Security levels: ML-KEM-512 (L1), ML-KEM-768 (L3), ML-KEM-1024 (L5). "
            "2. FIPS 204 — ML-DSA (Module Lattice-based Digital Signature Algorithm, "
            "from CRYSTALS-Dilithium). Replaces RSA and ECDSA for digital signatures. "
            "3. FIPS 205 — SLH-DSA (Stateless Hash-based Digital Signature Algorithm, "
            "from SPHINCS+). Hash-based signatures — security relies only on hash function "
            "security, not lattice hardness. Larger signatures but different trust model. "
            "4. FIPS 206 — FN-DSA (Fast Fourier lattice-based Compact Signatures, from FALCON). "
            "Compact signatures — smaller than ML-DSA, used where bandwidth is constrained. "
            "ML-KEM is the primary recommendation for TLS and key agreement. "
            "ML-DSA is the primary recommendation for code signing and certificates. "
            "SLH-DSA is preferred when long-term signature verification without lattice assumptions is needed."
        ),
        key_phrases=["FIPS 203 ML-KEM", "FIPS 204 ML-DSA", "FIPS 205 SLH-DSA", "FIPS 206 FN-DSA", "August 2024"],
        follow_up="What is hybrid PQC and why is it recommended during the transition period?",
    ),

    QA(
        section="Quantum Computing Attacks",
        question="What is a cryptographically relevant quantum computer (CRQC)?",
        answer=(
            "A CRQC is a quantum computer with sufficient logical qubits, gate fidelity, "
            "and error correction to run Shor's algorithm to factor RSA-2048 or solve "
            "ECDLP for P-256 in a practical timeframe (hours to days). "
            "This distinguishes it from NISQ (Noisy Intermediate-Scale Quantum) devices "
            "like today's IBM/Google hardware, which have too many errors and too few qubits "
            "for cryptographically meaningful computation. "
            "A CRQC requires: approximately 4,000+ logical qubits (error-corrected), "
            "millions of physical qubits, sustained operation for hours, and cycle times "
            "in the microsecond range. "
            "The NSA has stated it believes CRQCs are 'technically feasible' and that "
            "nation-state adversaries are actively pursuing them. "
            "The CNSA 2.0 suite (2022) mandates PQC migration not because a CRQC exists "
            "but because of HNDL: classified data intercepted today with 30-year secrecy "
            "requirements must be protected against a CRQC arriving in 2030. "
            "The phrase 'quantum-safe' specifically means secure against a CRQC — "
            "security against NISQ devices is a much lower bar."
        ),
        key_phrases=["CRQC vs NISQ", "4000+ logical qubits", "HNDL motivates urgency", "CNSA 2.0", "NSA technically feasible"],
        follow_up="What is the difference between quantum-safe and quantum-resistant?",
    ),

    QA(
        section="Quantum Computing Attacks",
        question="Explain hybrid PQC and why NIST recommends it during the transition period.",
        answer=(
            "Hybrid PQC combines a classical algorithm (e.g., ECDHE X25519) with a "
            "post-quantum algorithm (e.g., ML-KEM-768) in the same key exchange or signature. "
            "For key exchange: the shared secret is derived from BOTH algorithms — "
            "typically via a KDF: K = KDF(classical_secret || pqc_secret). "
            "This provides security as long as AT LEAST ONE of the two algorithms is secure. "
            "If ML-KEM has an undiscovered weakness (lattice hardness assumptions are newer "
            "than RSA's 40-year track record), the classical component still provides security. "
            "If a CRQC breaks ECDHE, the ML-KEM component still provides quantum security. "
            "Chrome 116+ uses X25519Kyber768 hybrid by default in TLS 1.3. "
            "Cloudflare, Google, and Cloudflare have deployed it at scale. "
            "NIST SP 800-227 (IPD 2024) explicitly recommends hybrid for the transition period "
            "until PQC algorithms accumulate real-world trust and cryptanalysis history. "
            "The hybrid period is expected to end ~2030 when PQC-only is sufficient."
        ),
        key_phrases=["security if ONE is secure", "X25519Kyber768", "Chrome 116+", "KDF combination", "NIST SP 800-227"],
        follow_up="What is the IETF standardization status of hybrid PQC in TLS?",
    ),
]


# ---------------------------------------------------------------------------
# Section 3: HNDL — Harvest Now Decrypt Later
# ---------------------------------------------------------------------------

SECTION_3: list[QA] = [

    QA(
        section="HNDL — Harvest Now Decrypt Later",
        question="What is HNDL and why is it described as an 'active threat' today?",
        answer=(
            "Harvest Now, Decrypt Later (HNDL) is the strategy of intercepting and storing "
            "encrypted network traffic today, with the intent to decrypt it retroactively "
            "once a Cryptographically Relevant Quantum Computer (CRQC) exists. "
            "It is an 'active threat' TODAY because: (1) nation-state adversaries can "
            "passively intercept traffic at internet exchange points, submarine cables, "
            "and compromised infrastructure — storage costs are near zero at scale; "
            "(2) RSA and ECDH do NOT provide forward secrecy by default — a static "
            "RSA private key that is later factored decrypts ALL past sessions; "
            "(3) the NSA, CISA, and NIST have all acknowledged HNDL in official advisories "
            "(NSA CNSA 2.0, 2022; CISA Quantum Readiness, 2023). "
            "The critical insight: the security decision must be made TODAY based on how long "
            "the data needs to remain confidential, not when the CRQC will actually arrive. "
            "A TLS session carrying health records today with a 25-year confidentiality "
            "requirement is ALREADY at risk — even if a CRQC is still 9 years away."
        ),
        key_phrases=["intercept today, decrypt later", "zero storage cost", "no forward secrecy", "NSA CNSA 2.0", "data lifetime decides urgency"],
        follow_up="How does perfect forward secrecy (PFS) limit HNDL blast radius?",
    ),

    QA(
        section="HNDL — Harvest Now Decrypt Later",
        question="How does perfect forward secrecy (PFS) reduce HNDL risk?",
        answer=(
            "Perfect Forward Secrecy uses ephemeral key exchange: a new Diffie-Hellman or "
            "ECDHE key pair is generated for each TLS session, and the ephemeral private key "
            "is destroyed immediately after the session ends. "
            "This means compromising the server's long-term RSA or ECDSA certificate private key "
            "does NOT allow decrypting past sessions — those sessions used ephemeral keys "
            "that no longer exist. "
            "HNDL with PFS still allows collecting encrypted traffic, but each session's "
            "ephemeral key would need to be individually attacked via Shor's algorithm — "
            "this is far less practical than a single server private key compromise. "
            "However, PFS does NOT fully defeat HNDL if the ephemeral keys are ECDHE — "
            "Shor's algorithm still breaks the ephemeral ECDH. "
            "The complete defense combines PFS (ECDHE or ML-KEM ephemeral) with PQC: "
            "ephemeral ML-KEM (FIPS 203) for the key exchange, so each session's ephemeral "
            "KEM secret is quantum-safe. "
            "TLS 1.3 mandates ephemeral key exchange — static RSA key transport was removed."
        ),
        key_phrases=["ephemeral key destroyed", "past session protection", "still broken by Shor's on ECDHE", "ML-KEM ephemeral", "TLS 1.3 mandates PFS"],
        follow_up="Does TLS 1.3 fully protect against HNDL?",
    ),

    QA(
        section="HNDL — Harvest Now Decrypt Later",
        question="Which data categories are most at risk from HNDL and why?",
        answer=(
            "HNDL risk is proportional to: (data sensitivity) × (retention lifetime > CRQC horizon). "
            "CRITICAL risk categories: "
            "(1) Government/military communications with classification lifetimes of 25–50 years "
            "— the NSA explicitly targets these with CNSA 2.0 by 2030. "
            "(2) Intellectual property and trade secrets that provide competitive advantage "
            "for more than 7–10 years. "
            "(3) Medical records — HIPAA requires 6-year retention, but medical conditions "
            "have lifetime sensitivity implications. "
            "(4) Financial records — bank account details, credit files, tax records with "
            "7+ year retention requirements. "
            "(5) Cryptocurrency private keys and blockchain transactions — any UTXO with an "
            "exposed public key is retroactively at risk. "
            "(6) Long-lived TLS certificates (multi-year) protecting financial/government sites. "
            "LOWER risk: session data like streaming video, real-time analytics, "
            "publicly available content — even if decrypted, the harm is negligible. "
            "The governance tool is a data inventory: for each data class, "
            "assess sensitivity × retention years × current encryption algorithm."
        ),
        key_phrases=["sensitivity × retention > CRQC", "NSA CNSA 2.0 by 2030", "Bitcoin UTXO", "data inventory", "medical lifetime sensitivity"],
        follow_up="What is the OMB M-23-02 memo and what does it require?",
    ),

    QA(
        section="HNDL — Harvest Now Decrypt Later",
        question="What is the regulatory response to HNDL risk?",
        answer=(
            "Several major regulatory and governmental bodies have issued HNDL-specific guidance: "
            "NSA CNSA 2.0 (September 2022): National Security Systems must adopt ML-KEM, ML-DSA, "
            "and SLH-DSA, with transition timelines: software/firmware by 2025, "
            "ML-KEM in key agreement by 2026, full NSS compliance by 2030, RSA/ECDSA deprecated by 2033. "
            "OMB M-23-02 (December 2022): US federal agencies must inventory cryptographic systems "
            "by 2023 and migrate to PQC by FY2035. "
            "CISA PQC Initiative (2022–2024): published migration guides for critical infrastructure "
            "sectors (energy, finance, healthcare, water). "
            "NIST IR 8413 (2022): status report on NIST PQC standardization candidates. "
            "ETSI TR 103 744 (2023): European framework for quantum-safe migration. "
            "GDPR (Article 32): 'appropriate technical measures' — HNDL risk means RSA-only "
            "encryption may no longer qualify as 'appropriate' for sensitive personal data. "
            "The key regulatory message: the migration window is NOW, not when CRQCs arrive."
        ),
        key_phrases=["CNSA 2.0 2030 deadline", "OMB M-23-02 FY2035", "CISA critical infrastructure", "GDPR appropriate measures", "migration window NOW"],
        follow_up="What is the NIST PQC migration playbook for federal agencies?",
    ),

    QA(
        section="HNDL — Harvest Now Decrypt Later",
        question="How do you calculate the urgency score for HNDL for a specific dataset?",
        answer=(
            "HNDL urgency = max(0, retention_years - years_until_CRQC) × sensitivity_weight. "
            "Step 1: Estimate years until CRQC. Consensus: 2030–2035; use 2033 as midpoint. "
            "With current year 2026, that is 7 years. "
            "Step 2: Classify data retention lifetime. "
            "Medical PHI: 25 years. Financial: 7 years. IP/Trade secrets: 10 years. "
            "Government classified: 25–50 years. "
            "Step 3: If retention > 7 years, the data will still be sensitive when CRQC arrives. "
            "Step 4: Apply sensitivity weight: government=5, medical/financial=4, IP=3, commercial=2. "
            "Step 5: urgency score = (retention - 7) × weight. "
            "Example: PHI with 25yr retention, encrypted with RSA today: (25-7)×4 = 72 → CRITICAL. "
            "Example: Session logs, 30-day retention: (0.08-7) is negative → LOW risk. "
            "Mitigation reduces the score: hybrid ML-KEM deployment halves the score; "
            "data deletion reduces retention_years; re-encryption to PQC sets urgency to 0. "
            "This framework is used to prioritize migration order across a large estate."
        ),
        key_phrases=["retention - CRQC years", "sensitivity weight", "PHI 25yr = CRITICAL", "hybrid halves score", "prioritize migration"],
        follow_up="How would you present this urgency analysis to a non-technical CISO?",
    ),
]


# ---------------------------------------------------------------------------
# Section 4: AI-Enhanced Cryptographic Attacks
# ---------------------------------------------------------------------------

SECTION_4: list[QA] = [

    QA(
        section="AI Attacks on Cryptographic Systems",
        question="How does machine learning improve side-channel analysis attacks?",
        answer=(
            "Classical side-channel analysis (Differential Power Analysis, DPA) requires "
            "statistical models of how a specific implementation leaks information — "
            "typically correlation between intermediate cipher values and power consumption. "
            "Deep Learning Side-Channel Analysis (DLSCA) eliminates this model requirement: "
            "a convolutional or multi-layer perceptron network learns the leakage function "
            "directly from oscilloscope power traces labeled with the target key byte. "
            "Maghrebi et al. (2016) showed DL-SCA achieves >99% key byte recovery with "
            "under 1,000 traces — 50× fewer than CPA. "
            "The ASCAD dataset (Benadjila et al. 2020) provides standardized benchmark traces. "
            "Key advantages of DL-SCA: handles misalignment and noise that defeats CPA; "
            "works on implementations with countermeasures (masking, shuffling) by learning "
            "higher-order interactions; generalizes across identical device batches. "
            "Defense: masking (splitting secret into multiple shares), shuffling, "
            "TVLA validation with ≥10,000 traces at FIPS 140-3 EAL5+ targets, "
            "noise injection via white noise oscillators."
        ),
        key_phrases=["DLSCA", "1000 traces vs 50000", "ASCAD dataset", "handles countermeasures", "masking defense"],
        follow_up="What is the TVLA t-statistic threshold for FIPS 140-3?",
    ),

    QA(
        section="AI Attacks on Cryptographic Systems",
        question="What is neural network differential cryptanalysis?",
        answer=(
            "Classical differential cryptanalysis finds input pairs with specific XOR differences "
            "that propagate through cipher rounds with high probability, revealing key information. "
            "Neural network differential cryptanalysis, introduced by Gohr (CRYPTO 2019), trains "
            "a binary classifier to distinguish real ciphertext pairs with a target difference "
            "from random pairs. "
            "For the lightweight cipher Speck-32/64 (7 rounds), Gohr's neural distinguisher "
            "outperformed all known classical distinguishers, achieving higher accuracy with "
            "fewer chosen plaintexts. "
            "The network learns non-linear differential characteristics that human analysts "
            "and classical probability-based methods miss. "
            "Subsequent work applied this to Simon, PRESENT, and reduced-round AES. "
            "No full-round AES neural distinguisher has been found — AES's design (wide trail) "
            "makes differential characteristics vanishingly rare for the full 10 rounds. "
            "The broader implication: AI can find non-trivial structural weaknesses in ciphers "
            "faster than manual cryptanalysis, accelerating the discovery of real CVEs in "
            "custom/proprietary cipher implementations. "
            "Defense: use vetted, publicly analyzed ciphers (AES, ChaCha20) rather than custom designs."
        ),
        key_phrases=["Gohr CRYPTO 2019", "Speck-32/64", "beats classical", "non-linear differentials", "use AES not custom"],
        follow_up="Why is AES more resistant to neural differential cryptanalysis than Speck?",
    ),

    QA(
        section="AI Attacks on Cryptographic Systems",
        question="Explain how LLMs accelerate vulnerability discovery in cryptographic code.",
        answer=(
            "Large language models fine-tuned on security datasets (CVEs, CWE, crypto library "
            "source code) can assist cryptographic vulnerability discovery in several ways: "
            "(1) Pattern matching at scale: LLMs can scan thousands of crypto library implementations "
            "for known anti-patterns (nonce reuse, weak key generation, timing-sensitive branches) "
            "faster than manual review. "
            "(2) Cross-language analysis: the same LLM can identify RSA-PKCS1v15 misuse in Python, "
            "Java, Rust, and C — knowledge transfer across languages. "
            "(3) Code generation for exploit scaffolding: given a CVE description and target code, "
            "LLMs generate proof-of-concept test cases for padding oracle or timing attacks. "
            "(4) Pearce et al. (2023) showed GPT-4 identified ~40% of known crypto CVEs when given "
            "the relevant source code context, outperforming static analysis tools on subtle issues. "
            "Limitations: LLMs hallucinate CVEs, miss context-dependent vulnerabilities "
            "(multi-file state), and cannot verify exploitability. "
            "Defense implication: crypto code review MUST include LLM-assisted scanning as a layer "
            "alongside formal verification (HACL*, EverCrypt) and dynamic analysis (fuzzing)."
        ),
        key_phrases=["Pearce 2023 40%", "cross-language", "scaffolding PoCs", "hallucination limit", "HACL* EverCrypt"],
        follow_up="What is formal verification of cryptographic code and which libraries use it?",
    ),

    QA(
        section="AI Attacks on Cryptographic Systems",
        question="How does AI-powered social engineering threaten cryptographic key material?",
        answer=(
            "Even the strongest cryptographic algorithm is defeated if the key material is stolen "
            "via human deception — the 'weakest link' principle. "
            "AI-generated deepfakes dramatically lower the barrier for this: "
            "(1) Voice cloning: adversary creates a real-time deepfake of the CISO's voice "
            "to authorize an emergency HSM export over phone — no sophisticated intrusion needed. "
            "Real case: Ferrari (2024), CFO impersonated via AI voice clone, USD 25M transferred. "
            "(2) Video deepfake: in a key ceremony (HSM initialization), a deepfaked video call "
            "impersonates a trusted party to manipulate the quorum decision. "
            "(3) LLM-crafted spearphishing: AI generates hyper-personalized phishing emails "
            "referencing real recent projects, colleagues, and internal terminology to steal "
            "credentials for HSM management consoles. "
            "(4) AI-assisted OSINT: LLM aggregates LinkedIn, GitHub, and leaked databases to "
            "build detailed profiles of cryptographic custodians for targeted social engineering. "
            "Defense: M-of-N secret sharing (Shamir's Secret Sharing) for HSM key ceremonies; "
            "out-of-band identity verification (pre-agreed challenge-response, not phone); "
            "deepfake detection tools at video conference entry points; "
            "zero-trust access policies for key management systems."
        ),
        key_phrases=["Ferrari deepfake $25M", "Shamir's Secret Sharing", "out-of-band verification", "key ceremony quorum", "OSINT + LLM"],
        follow_up="What is M-of-N secret sharing and how is it used in HSM key ceremonies?",
    ),

    QA(
        section="AI Attacks on Cryptographic Systems",
        question="What is the OWASP LLM Top 10 and which items affect cryptographic security?",
        answer=(
            "The OWASP LLM Top 10 (2023) catalogs the most critical security risks in "
            "LLM-based applications. Items most relevant to cryptographic and key management security: "
            "LLM01 — Prompt Injection: attackers manipulate LLM behavior via crafted inputs, "
            "potentially exfiltrating API keys, secrets, or PII from the LLM's context. "
            "Especially dangerous in RAG pipelines where retrieved documents can contain injections. "
            "LLM02 — Insecure Output Handling: LLM outputs used in SQL queries, shell commands, "
            "or key generation without sanitization — indirect injection path to crypto operations. "
            "LLM06 — Sensitive Information Disclosure: LLM trained on or given access to "
            "API keys, private keys, or secrets may leak them in responses. "
            "LLM08 — Excessive Agency: LLM given file system or network access can exfiltrate "
            "private key files if tricked via prompt injection. "
            "LLM09 — Overreliance: developers trusting LLM-generated cryptographic code without "
            "expert review — common source of nonce reuse, weak key generation, and algorithm misuse. "
            "Defense: privilege separation between LLM and key management systems; "
            "output validation; never store secrets in LLM context; "
            "red-team every LLM tool-use pathway for injection vectors."
        ),
        key_phrases=["LLM01 Prompt Injection", "LLM06 secret disclosure", "LLM08 excessive agency", "RAG injection", "LLM09 crypto misuse"],
        follow_up="How would you architect a zero-trust boundary between an LLM agent and an HSM?",
    ),
]


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main():
    print("\n" + "#" * 76)
    print("  INTERVIEW ATTACK PREPARATION — QUANTUM SECURITY PORTFOLIO")
    print("  Topics: Classical Crypto, Quantum Attacks, HNDL, AI Attacks")
    print("#" * 76)

    sections = [
        ("SECTION 1: Classical Cryptographic Vulnerabilities", SECTION_1),
        ("SECTION 2: How Quantum Computers Break Encryption", SECTION_2),
        ("SECTION 3: Harvest Now Decrypt Later (HNDL)", SECTION_3),
        ("SECTION 4: AI Attacks on Cryptographic Systems",  SECTION_4),
    ]

    overall_count = 0
    for section_title, qas in sections:
        print(f"\n\n{'=' * 76}")
        print(f"  {section_title}")
        print(f"{'=' * 76}")
        for i, qa in enumerate(qas, 1):
            overall_count += 1
            qa.display(overall_count)

    print(f"\n\n{'=' * 76}")
    print(f"  TOTAL: {overall_count} Interview Q&As across {len(sections)} sections")
    print("=" * 76)
    print()
    print("  CHEAT SHEET — Key Technical Numbers to Memorize:")
    cheatsheet = [
        ("Shor's complexity",      "O((log N)^3) vs classical O(exp(c*(log N)^(1/3)))"),
        ("RSA-2048 logical qubits","~4,098 (Gidney & Ekerå 2021)"),
        ("RSA-2048 physical est.", "~20M qubits at 0.1% error (surface code)"),
        ("P-256 logical qubits",   "~2,330 (Roetteler et al. 2017)"),
        ("Grover's speedup",       "O(√N) — halves effective key length"),
        ("AES-128 quantum bits",   "64-bit effective (CRITICAL)"),
        ("AES-256 quantum bits",   "128-bit effective (SAFE)"),
        ("SHA-256 collision BHT",  "2^85.3 (BHT quantum walk)"),
        ("CRQC timeline",          "Consensus: 2030–2035"),
        ("NIST FIPS 203",          "ML-KEM (Kyber) — replaces RSA/ECDH"),
        ("NIST FIPS 204",          "ML-DSA (Dilithium) — replaces RSA/ECDSA"),
        ("NIST FIPS 205",          "SLH-DSA (SPHINCS+) — hash-based sigs"),
        ("NIST FIPS 206",          "FN-DSA (FALCON) — compact sigs"),
        ("Chrome hybrid PQC",      "X25519Kyber768 (Chrome 116+, TLS 1.3)"),
        ("NSA CNSA 2.0 deadline",  "2030 for NSS; RSA/ECDSA deprecated 2033"),
    ]
    print()
    for label, value in cheatsheet:
        print(f"  {label:<28}: {value}")
    print()


if __name__ == "__main__":
    main()
