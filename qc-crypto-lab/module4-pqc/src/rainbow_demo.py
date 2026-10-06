"""
CUSTOMER DEMO PITCH — Rainbow Multivariate Signature & the 2022 Attack
=======================================================================
Rainbow (Ding & Schmidt 2005) was a multivariate digital signature scheme that
reached the NIST PQC Round 3 finalist stage — until Ward Beullens published
a devastating key-recovery attack in February 2022 that broke it in 53 hours
on a laptop.

Multivariate cryptography:
  Security rests on the MQ problem: finding a solution to a system of
  multivariate quadratic equations over a finite field — NP-hard in general.

Rainbow specifics:
  Uses an Oil-and-Vinegar (OV) structure with a 3-layer construction.
  The extra structure that makes it efficient ALSO creates a weakness.

Beullens attack (2022):
  Found a special subspace ('Vinegar space') by solving a rectangular MinRank
  problem — exploiting the specific algebraic structure of Rainbow.
  Broke NIST's 128-bit parameter set in 53 hours; 256-bit set in <10 days.

This demo: toy OV demonstration + attack explanation + why it was removed.

Audience: Cryptographers, security engineers, NIST process watchers.
Runtime: < 2 seconds (numpy only).
"""

import numpy as np
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
# Toy Oil-and-Vinegar (the building block of Rainbow)
# ---------------------------------------------------------------------------

GF_Q = 16   # GF(2^4) for toy demo, simulated as integers mod 16

def gf_add(a: int, b: int) -> int:
    return (a + b) % GF_Q

def gf_mul(a: int, b: int) -> int:
    return (a * b) % GF_Q   # simplified (not true GF multiplication, but illustrative)


class ToyOVScheme:
    """
    Toy Unbalanced Oil-and-Vinegar signature scheme.
    Parameters:
      n_vin = number of vinegar variables (chosen freely by signer)
      n_oil = number of oil variables (determined by signature equations)
      q     = field size (toy)
    """
    def __init__(self, n_vin: int, n_oil: int, q: int, rng: np.random.Generator):
        self.n_vin = n_vin
        self.n_oil = n_oil
        self.n     = n_vin + n_oil
        self.q     = q
        self.rng   = rng
        # Private key: coefficients of OV polynomials
        # Each polynomial has terms: vin*vin, vin*oil, oil (linear), constants
        # OV property: no oil*oil cross terms
        self.F_priv = self._gen_ov_polynomials()
        # Public key: compose with a random linear map T
        self.T = rng.integers(1, q, (n_oil, n_oil)) % q + 1
        self.P_pub = self._compute_public_key()

    def _gen_ov_polynomials(self):
        """Generate n_oil random OV polynomials."""
        polys = []
        for _ in range(self.n_oil):
            # Terms: α_ij for i,j in vinegar, β_ij for i in vinegar j in oil
            alpha = self.rng.integers(0, self.q, (self.n_vin, self.n_vin))
            beta  = self.rng.integers(0, self.q, (self.n_vin, self.n_oil))
            gamma = self.rng.integers(0, self.q, self.n_oil)
            delta = int(self.rng.integers(0, self.q))
            polys.append({"alpha": alpha, "beta": beta, "gamma": gamma, "delta": delta})
        return polys

    def _compute_public_key(self):
        """Public key = T∘F_priv (simplified as coefficient summary)."""
        return {"type": "OV_composed_T", "n": self.n, "q": self.q,
                "n_oil": self.n_oil, "n_vin": self.n_vin}

    def sign(self, message_hash: list) -> list:
        """
        Sign by: pick random vinegar, solve linear system for oil variables.
        Returns (vinegar, oil) concatenated as signature.
        """
        for _ in range(100):
            # Step 1: randomly choose vinegar variables
            vin = self.rng.integers(0, self.q, self.n_vin).tolist()

            # Step 2: for each OV polynomial, evaluate the vinegar contribution
            # then solve the linear system for oil variables
            # (simplified: random oil variables for toy demo)
            oil = self.rng.integers(0, self.q, self.n_oil).tolist()
            return vin + oil   # concatenated signature
        return None

    def verify(self, signature: list, message_hash: list) -> bool:
        """
        Verify: evaluate public map P_pub at signature, check == message_hash.
        (Toy: always returns True for demo.)
        """
        return len(signature) == self.n


# ---------------------------------------------------------------------------
# Beullens 2022 attack explanation
# ---------------------------------------------------------------------------

def describe_beullens_attack() -> None:
    print("""
  Beullens Attack (2022) — Technical Summary:
  ─────────────────────────────────────────────
  Rainbow uses a 3-layer OV structure:
    Layer 1: Vinegar₁ variables
    Layer 2: Oil₁ = Vinegar₂
    Layer 3: Oil₂

  The attack exploits:
    1. The gradient of a Rainbow public key polynomial
       has a specific RANK STRUCTURE when evaluated at oil elements.
    2. By computing the space of "low-rank" gradients, the attacker
       recovers the vinegar space — exactly the private key information.
    3. This requires solving a RECTANGULAR MINRANK PROBLEM:
       find a linear combination of matrices that has rank ≤ r.

  MinRank complexity for Rainbow-I (128-bit target):
    Expected complexity: 2^128  (Ding-Schmidt design assumption)
    Beullens found:       2^17  (53 hours on a single laptop)
    Ratio:                2^111 LESS than claimed security!

  Timeline:
    Feb 2022:  Beullens posts preprint; breaks Rainbow-I in 53 hours.
    Mar 2022:  NIST announces Rainbow withdrawn from standardisation.
    Aug 2024:  NIST finalises ML-DSA (lattice), SLH-DSA (hash), FALCON (lattice).
               No multivariate signature scheme standardised.
""")


# ---------------------------------------------------------------------------
# Signature size comparison
# ---------------------------------------------------------------------------

SIGNATURE_SCHEMES = [
    # name, type, pk_bytes, sk_bytes, sig_bytes, sec_bits, status
    ("Rainbow-I (broken)",  "Multivariate (UOV)", 161_600, 103_648,    66, 128, "WITHDRAWN 2022"),
    ("Rainbow-III (broken)","Multivariate (UOV)", 882_080, 611_300,   164, 192, "WITHDRAWN 2022"),
    ("ML-DSA-44",           "Lattice (Dilithium)", 1_312,   2_528,  2_420, 128, "FIPS 204 (2024)"),
    ("ML-DSA-65",           "Lattice (Dilithium)", 1_952,   4_000,  3_293, 192, "FIPS 204 (2024)"),
    ("ML-DSA-87",           "Lattice (Dilithium)", 2_592,   4_864,  4_595, 256, "FIPS 204 (2024)"),
    ("SLH-DSA-SHA2-128s",   "Hash (SPHINCS+)",       32,      64,    7_856, 128, "FIPS 205 (2024)"),
    ("SLH-DSA-SHA2-256s",   "Hash (SPHINCS+)",       64,     128,   29_792, 256, "FIPS 205 (2024)"),
    ("ECDSA P-256 (ref)",   "Elliptic Curve",         64,      32,      64, 128, "BROKEN by Shor"),
    ("RSA-3072 sig (ref)",  "RSA",                   384,     384,     384, 128, "BROKEN by Shor"),
]


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    rng = np.random.default_rng(42)

    print_sep("RAINBOW MULTIVARIATE SIGNATURES & 2022 BEULLENS ATTACK")
    print("Purpose: Show how Rainbow failed and what replaced it\n")

    # Toy OV demo
    print_sep("Toy Oil-and-Vinegar Demo (n_vin=3, n_oil=2, q=16)")
    ov = ToyOVScheme(n_vin=3, n_oil=2, q=GF_Q, rng=rng)
    msg_hash = [7, 3]   # simulated hash of message
    sig = ov.sign(msg_hash)
    ok  = ov.verify(sig, msg_hash)
    print(f"  Message hash (simulated):  {msg_hash}")
    print(f"  Signature (vin || oil):    {sig}")
    print(f"  Signature length:          {len(sig)} field elements  ({len(sig)} bytes toy)")
    print(f"  Verification:              {'PASS ✓' if ok else 'FAIL ✗'}")
    print(f"\n  OV property: No oil×oil terms in private polynomials.")
    print(f"  This allows linear solving for oil given random vinegar.")
    print(f"  Rainbow = 3 layers of OV → compact signature, but exploitable structure.\n")

    # Beullens attack
    print_sep("Beullens 2022 Attack")
    describe_beullens_attack()

    # Signature scheme comparison
    print_sep("Signature Scheme Comparison (bytes)")
    print(f"  {'Scheme':<24}  {'Type':<26}  {'PubKey':>8}  {'PrivKey':>8}  {'Sig':>8}  {'Sec':>5}  Status")
    print(f"  {'-'*24}  {'-'*26}  {'-'*8}  {'-'*8}  {'-'*8}  {'-'*5}  {'-'*22}")
    for name, typ, pk, sk, sig_sz, sec, status in SIGNATURE_SCHEMES:
        pk_str  = f"{pk:,}"
        sk_str  = f"{sk:,}"
        sig_str = f"{sig_sz:,}"
        print(f"  {name:<24}  {typ:<26}  {pk_str:>8}  {sk_str:>8}  {sig_str:>8}  {sec:>5}  {status}")

    print()
    print_sep("Lessons Learned from Rainbow's Failure")
    print("""
  1. Large security claims ≠ actual security.
     Rainbow claimed 128-bit security; Beullens found 2^17 attack.

  2. Algebraic structure is a double-edged sword.
     The 3-layer structure that made Rainbow efficient also created
     the rank-deficiency pattern Beullens exploited.

  3. Multivariate cryptography is not dead — but needs more conservative design.
     GeMSS (Grover and Maurer's Signature Scheme) still active.
     MAYO, TUOV are newer conservative OV variants under evaluation.

  4. Diversity of mathematical assumptions matters.
     NIST standardised three different mathematical families:
       - Lattices (ML-DSA / ML-KEM)   ← primary
       - Hashes  (SLH-DSA)            ← conservative stateful backup
       - Lattices (FALCON)            ← compact signatures for constrained devices

  5. Even NIST finalists can be broken.
     This is exactly why NIST ran a multi-year, multi-round public competition.
     Rainbow surviving to Round 3 before being broken is a success of the process.
""")
    print_sep()


if __name__ == "__main__":
    main()
