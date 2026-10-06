"""
CUSTOMER DEMO PITCH — Learning With Errors (LWE)
=================================================
LWE (Regev 2005) is the mathematical problem underlying ML-KEM (CRYSTALS-Kyber),
the NIST-standardized post-quantum key encapsulation mechanism.

The problem:
  Given a matrix A (public), find secret vector s such that b ≈ A·s (mod q)
  where b = A·s + e and e is a small random error vector.
  "Solving LWE" = recovering s from (A, b).

Why it's hard:
  - Without the error e: linear algebra → trivial (Gaussian elimination).
  - With the error e: becomes NP-hard in the worst case (Ajtai 1996).
  - Best quantum algorithms (LLL, BKZ) require sub-exponential time.
  - Shor's algorithm provides NO speedup for LWE.

This demo creates a toy LWE instance (n=4, q=97), encrypts a message,
decrypts it, and shows the hardness parameters for real schemes.

Audience: Cryptographers, security architects, interview panels.
Runtime: < 2 seconds (numpy only).
"""

import numpy as np
import math


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_sep(title: str = "") -> None:
    w = 66
    if title:
        p = (w - len(title) - 2) // 2
        print("=" * p + f" {title} " + "=" * (w - p - len(title) - 2))
    else:
        print("=" * w)


# ---------------------------------------------------------------------------
# Toy LWE parameters
# ---------------------------------------------------------------------------

N = 4    # dimension
Q = 97   # modulus (small prime for demo)


def sample_discrete_gaussian(size: tuple, std: float, q: int,
                              rng: np.random.Generator) -> np.ndarray:
    """Sample from discrete Gaussian (mod q)."""
    e = rng.normal(0, std, size).round().astype(int) % q
    return e


# ---------------------------------------------------------------------------
# LWE Key Generation
# ---------------------------------------------------------------------------

def lwe_keygen(n: int, q: int, sigma: float,
               rng: np.random.Generator) -> dict:
    """
    Alice generates:
      s  = secret key (uniform mod q)
      A  = public matrix (uniform mod q)  shape: (m, n)
      e  = error vector, small ~ N(0, σ)
      b  = (A·s + e) mod q  (public)
    """
    m = 2 * n   # number of samples
    s = rng.integers(0, q, n)
    A = rng.integers(0, q, (m, n))
    e = sample_discrete_gaussian((m,), sigma, q, rng)
    b = (A @ s + e) % q
    return {"s": s, "A": A, "e": e, "b": b, "n": n, "q": q, "sigma": sigma}


# ---------------------------------------------------------------------------
# LWE Encryption (simple binary message)
# ---------------------------------------------------------------------------

def lwe_encrypt(message_bit: int, A: np.ndarray, b: np.ndarray,
                n: int, q: int, rng: np.random.Generator) -> dict:
    """
    Encrypt one bit using LWE public key (A, b).
    Choose random r ∈ {0,1}^m, compute:
      u = A^T · r (mod q)
      v = b^T · r + ⌊q/2⌋ · message (mod q)
    """
    m = A.shape[0]
    r = rng.integers(0, 2, m)
    u = (A.T @ r) % q
    v = (int(b @ r) + (q // 2) * message_bit) % q
    return {"u": u, "v": v, "message_bit": message_bit}


def lwe_decrypt(u: np.ndarray, v: int, s: np.ndarray, q: int) -> int:
    """
    Decrypt: compute phase = v - s^T · u (mod q).
    If phase is close to 0 → message = 0
    If phase is close to q/2 → message = 1
    """
    phase = (v - int(s @ u)) % q
    # Round to nearest of {0, q/2}
    dist0   = min(phase, q - phase)
    dist_q2 = min(abs(phase - q // 2), abs(phase - (q - q // 2)))
    return 0 if dist0 < dist_q2 else 1


# ---------------------------------------------------------------------------
# Hardness demonstration
# ---------------------------------------------------------------------------

def attempt_lwe_brute_force(A: np.ndarray, b: np.ndarray, q: int, n: int,
                             max_attempts: int = 500) -> tuple:
    """
    Attempt brute-force recovery of s by trying random vectors.
    For small n and q this is feasible; for real parameters it's impossible.
    """
    rng_bf = np.random.default_rng(1)
    for attempt in range(max_attempts):
        s_guess = rng_bf.integers(0, q, n)
        residual = (b - A @ s_guess) % q
        # Check if residual is 'small' (all entries < 3*sigma)
        # For sigma=2, threshold = 6
        max_resid = np.max(np.minimum(residual, q - residual))
        if max_resid < 6:
            return s_guess, attempt + 1
    return None, max_attempts


# ---------------------------------------------------------------------------
# Real scheme parameters
# ---------------------------------------------------------------------------

REAL_SCHEMES = [
    # name,   n,     q,      sigma,  security, PQ-secure
    ("ML-KEM-512",   256,  3329,  0.8,  128, "Yes"),
    ("ML-KEM-768",   384,  3329,  1.0,  192, "Yes"),
    ("ML-KEM-1024",  512,  3329,  1.0,  256, "Yes"),
    ("ML-DSA-44",    1024, 8380417, 1.0, 128, "Yes"),
    ("ML-DSA-65",    1536, 8380417, 1.0, 192, "Yes"),
    ("NTRU-HPS-509", 509,  2048, 0.67, 128, "Yes"),
    ("RSA-2048 (ref)", 2048, None, None, 112, "NO — broken by Shor"),
]


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    rng = np.random.default_rng(42)
    sigma = 2.0   # small error standard deviation

    print_sep("LEARNING WITH ERRORS (LWE) DEMO")
    print(f"  Toy parameters: n={N}, q={Q}, σ={sigma}")
    print(f"  Real ML-KEM: n=256-512, q=3329, σ≈1.0\n")

    # Key generation
    print_sep("LWE Key Generation")
    keys = lwe_keygen(N, Q, sigma, rng)
    print(f"  Secret key s:  {keys['s']}")
    print(f"  Public A (first 4 rows):")
    for row in keys["A"][:4]:
        print(f"    {row}")
    print(f"  Error e:       {keys['e']}")
    print(f"  b = A·s+e mod {Q}: {keys['b']}")
    # Verify
    b_ideal = (keys["A"] @ keys["s"]) % Q
    print(f"  b_ideal (no e):   {b_ideal}")
    print(f"  |b - b_ideal|:    {np.abs(keys['b'].astype(int) - b_ideal.astype(int))}")
    print()

    # Encryption / Decryption
    print_sep("LWE Encrypt/Decrypt Demo (single bit)")
    for msg_bit in [0, 1]:
        ct = lwe_encrypt(msg_bit, keys["A"], keys["b"], N, Q, rng)
        dec = lwe_decrypt(ct["u"], ct["v"], keys["s"], Q)
        print(f"  message={msg_bit}  →  u={ct['u']}  v={ct['v']:3d}  →  decrypted={dec}  "
              f"{'✓' if dec == msg_bit else '✗ FAIL'}")
    print()

    # Multi-bit demo
    print_sep("4-bit Message Demo")
    message = [1, 0, 1, 1]
    print(f"  Original message: {message}")
    decrypted = []
    for bit in message:
        ct  = lwe_encrypt(bit, keys["A"], keys["b"], N, Q, rng)
        dec = lwe_decrypt(ct["u"], ct["v"], keys["s"], Q)
        decrypted.append(dec)
    print(f"  Decrypted:        {decrypted}")
    print(f"  Match: {'✓' if message == decrypted else '✗'}\n")

    # Hardness demonstration
    print_sep("Hardness: Brute-Force Attack on Toy LWE")
    print(f"  Trying random vectors to find s (max 500 attempts)...")
    s_found, n_att = attempt_lwe_brute_force(keys["A"], keys["b"], Q, N)
    if s_found is not None:
        correct = np.array_equal(s_found % Q, keys["s"])
        print(f"  Found s after {n_att} attempts: {s_found}  {'(correct ✓)' if correct else '(wrong ✗)'}")
    else:
        print(f"  Not found in {n_att} random attempts.")
    print(f"  Total keyspace size: {Q}^{N} = {Q**N:,}  (toy; exhaustible)")
    print(f"  ML-KEM-768 keyspace: 3329^384 ≈ 2^3752  (completely infeasible)\n")

    # Real scheme parameters
    print_sep("Real LWE-Based Scheme Parameters")
    print(f"  {'Scheme':<18}  {'n':>5}  {'q':>8}  {'σ':>5}  {'Sec (bits)':>11}  {'PQ-Safe?'}")
    print(f"  {'-'*18}  {'-'*5}  {'-'*8}  {'-'*5}  {'-'*11}  {'-'*10}")
    for name, n, q, sig, sec, pq in REAL_SCHEMES:
        q_str   = str(q) if q else "N/A"
        sig_str = str(sig) if sig else "N/A"
        print(f"  {name:<18}  {n:>5}  {q_str:>8}  {sig_str:>5}  {sec:>11}  {pq}")

    print()
    print_sep("Key Takeaway")
    print("""
  LWE is the mathematical foundation of NIST-standardized post-quantum cryptography.
  Three reasons it resists quantum attacks:

  1. Shor's algorithm attacks the PERIOD-FINDING structure of RSA/ECC.
     LWE has no periodic structure → Shor provides ZERO speedup.

  2. Grover's algorithm searches unsorted spaces in O(√N).
     LWE hardness relies on worst-case lattice problems — Grover cannot
     efficiently search the exponentially large solution space.

  3. The best known quantum algorithm for LWE (lattice sieving via quantum walk)
     gives only a CONSTANT FACTOR speedup — easily compensated by increasing n.
     ML-KEM-1024 provides 256 bits of post-quantum security.

  Timeline: ML-KEM (FIPS 203) was standardized by NIST in August 2024.
  Migration target: all TLS, SSH, code-signing, and key exchange by 2030.
""")
    print_sep()


if __name__ == "__main__":
    main()
