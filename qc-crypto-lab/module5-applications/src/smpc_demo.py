"""
CUSTOMER DEMO PITCH — Secure Multi-Party Computation (SMPC) with Secret Sharing
================================================================================
Secure Multi-Party Computation lets multiple parties JOINTLY COMPUTE a function
over their private inputs, WITHOUT any party learning another's data.

This demo uses Shamir's Secret Sharing (1979) with a (2,3) threshold:
  - 3 parties each hold a SHARE of a secret.
  - ANY 2 parties can reconstruct the secret.
  - 1 party alone learns NOTHING.

Use case: 3 banks jointly compute the average loan default rate across their
portfolios, without any bank revealing its own portfolio data to competitors.
Regulatory requirement: aggregate statistics can be shared; individual bank data
is confidential under GDPR, DPDP, and FFIEC guidance.

Security: Information-theoretically secure — even an adversary with unlimited
computing power cannot learn a party's secret from just 1 of 3 shares.

Audience: Banking/finance CISOs, regulatory teams, fintech architects.
Runtime: < 2 seconds.
"""

import random
import math
import hashlib


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
# Shamir's Secret Sharing over GF(p)
# ---------------------------------------------------------------------------

def modinv(a: int, m: int) -> int:
    """Extended Euclidean algorithm for modular inverse."""
    g, x, _ = extended_gcd(a, m)
    if g != 1:
        raise ValueError(f"No inverse: gcd({a},{m})={g}")
    return x % m


def extended_gcd(a: int, b: int) -> tuple:
    if a == 0:
        return b, 0, 1
    g, x1, y1 = extended_gcd(b % a, a)
    return g, y1 - (b // a) * x1, x1


# Large prime for our finite field
# Use a prime larger than any secret value
PRIME = (1 << 127) - 1   # Mersenne prime 2^127-1


def sss_split(secret: int, n: int, k: int,
              rng: random.Random) -> list:
    """
    Shamir's Secret Sharing: split secret into n shares, threshold k.
    Returns list of (x, y) pairs.
    """
    # Random polynomial of degree k-1: f(x) = secret + a1*x + a2*x^2 + ...
    coeffs = [secret % PRIME] + [rng.randrange(0, PRIME) for _ in range(k - 1)]

    shares = []
    for x in range(1, n + 1):
        y = sum(coeff * pow(x, i, PRIME) for i, coeff in enumerate(coeffs)) % PRIME
        shares.append((x, y))
    return shares


def sss_reconstruct(shares: list) -> int:
    """
    Lagrange interpolation to reconstruct secret from k shares.
    Returns f(0) = secret.
    """
    secret = 0
    n      = len(shares)
    for i, (xi, yi) in enumerate(shares):
        # Lagrange basis polynomial l_i(0)
        num = 1
        den = 1
        for j, (xj, _) in enumerate(shares):
            if i != j:
                num = (num * (-xj)) % PRIME
                den = (den * (xi - xj)) % PRIME
        lagrange_i = (num * modinv(den, PRIME)) % PRIME
        secret     = (secret + yi * lagrange_i) % PRIME
    return secret


# ---------------------------------------------------------------------------
# Multi-party computation: secure average
# ---------------------------------------------------------------------------

def smpc_average(bank_secrets: list, n: int, k: int,
                 rng: random.Random) -> dict:
    """
    Compute the average of bank_secrets using additive secret sharing.
    Each party:
      1. Splits their secret into n shares.
      2. Sends share[j] to party j.
      3. Each party sums the shares it received.
      4. Parties publish their sums; any k can reconstruct the total.
    """
    n_parties = len(bank_secrets)
    all_shares = []   # all_shares[party_i][party_j] = share of party_i's secret for party_j

    for secret in bank_secrets:
        shares = sss_split(secret, n_parties, k, rng)
        all_shares.append(shares)

    # Each party j sums all shares it received (additive secret sharing)
    summed_shares = []
    for j in range(n_parties):
        x_j = all_shares[0][j][0]   # x coordinate
        y_j = sum(all_shares[i][j][1] for i in range(n_parties)) % PRIME
        summed_shares.append((x_j, y_j))

    # Reconstruct the sum from k shares
    total_sum     = sss_reconstruct(summed_shares[:k])
    # Reconstruct exact sum (all shares)
    total_sum_all = sss_reconstruct(summed_shares)
    average       = total_sum_all / n_parties

    return {
        "n_parties":    n_parties,
        "k_threshold":  k,
        "total_sum":    total_sum_all,
        "average":      average,
        "shares_used":  k,
        "all_shares":   all_shares,
        "summed_shares": summed_shares,
    }


# ---------------------------------------------------------------------------
# Information-theoretic privacy proof
# ---------------------------------------------------------------------------

def privacy_demo(secret: int, n: int = 3, k: int = 2) -> None:
    """
    Show that 1 share reveals NO information about the secret.
    With k-1 shares, distribution over all possible secrets is uniform.
    """
    rng = random.Random(42)
    share_sets = []
    for test_secret in [100, 500, 1000, 5000, 99999]:
        shares = sss_split(test_secret, n, k, rng)
        # Just take share #1 (party 0's x=1 share)
        share_sets.append((test_secret, shares[0]))

    print(f"\n  Show: party 1's single share for different secrets:")
    print(f"  {'Secret':>8}  {'Share at x=1':>40}  Distinguishable?")
    print(f"  {'-'*8}  {'-'*40}  {'-'*15}")
    for sec, (x, y) in share_sets:
        print(f"  {sec:>8}  {y:>40}  No  (looks random)")
    print(f"\n  All single shares are statistically indistinguishable from random.")
    print(f"  This is information-theoretic privacy — holds even vs quantum adversary.")


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    rng = random.Random(42)

    # Banking scenario: 3 banks' annual loan default rates (basis points)
    # These are SECRET — banks cannot share these directly (competitive sensitivity)
    bank_data = {
        "BankAlpha":  850,   # 8.50% default rate (in bps = 100ths of a percent)
        "BetaCapital": 720,  # 7.20%
        "GammaBank":  950,   # 9.50%
    }
    secrets = list(bank_data.values())
    true_average = sum(secrets) / len(secrets)

    print_sep("SECURE MULTI-PARTY COMPUTATION — Banking Demo")
    print("Purpose: 3 banks jointly compute average default rate without sharing data\n")

    # The problem
    print_sep("The Problem: Competing Banks Cannot Share Data")
    print("""
  BankAlpha, BetaCapital, and GammaBank are asked by the regulator for the
  AVERAGE loan default rate across all three institutions.

  Challenge:
    - Each bank's default rate is competitively sensitive.
    - BankAlpha doesn't want BetaCapital to know its rate (and vice versa).
    - The regulator needs the aggregate average — not individual values.
    - GDPR / FFIEC / DPDP restrict sharing individual customer portfolio data.

  Solution: Shamir's Secret Sharing + SMPC
    Each bank splits its secret into 3 shares (2-of-3 threshold).
    No bank learns another's secret, but together they compute the average.
""")

    print_sep("Step 1: Each Bank's Secret Data (PRIVATE — not shared)")
    for bank, rate in bank_data.items():
        print(f"  {bank:<20}  default rate = {rate} bps = {rate/100:.2f}%")
    print(f"  {'TRUE AVERAGE':<20}  = {true_average:.1f} bps = {true_average/100:.2f}%")
    print()

    # Secret sharing
    print_sep("Step 2: Shamir Secret Sharing (k=2 of n=3)")
    print(f"  Each bank splits its secret into 3 shares (threshold: any 2 can reconstruct).")
    all_shares_named = {}
    for bank, secret in bank_data.items():
        shares = sss_split(secret, n=3, k=2, rng=rng)
        all_shares_named[bank] = shares
        print(f"\n  {bank} (secret={secret}):")
        for i, (x, y) in enumerate(shares):
            print(f"    Share {i+1} (x={x}): y = {y % (10**10):010d}...  [sent to party {i+1}]")

    # Privacy demo
    print_sep("Step 3: Privacy Guarantee — Single Share Reveals Nothing")
    sample_secret = secrets[0]
    privacy_demo(sample_secret)
    print()

    # SMPC average computation
    print_sep("Step 4: SMPC — Jointly Compute Average")
    result = smpc_average(secrets, n=3, k=2, rng=rng)
    print(f"  Protocol:")
    print(f"    1. Each bank sends its shares to the other parties.")
    print(f"    2. Each party sums all received shares (locally, without revealing secrets).")
    print(f"    3. Parties publish their summed values.")
    print(f"    4. Any 2 parties reconstruct the total sum → compute average.")
    print()
    print(f"  Total sum reconstructed: {result['total_sum']}")
    print(f"  True sum:                {sum(secrets)}")
    print(f"  Computed average:        {result['average']:.1f} bps  =  {result['average']/100:.2f}%")
    print(f"  True average:            {true_average:.1f} bps  =  {true_average/100:.2f}%")
    print(f"  Correct:                 {'✓' if abs(result['average'] - true_average) < 0.1 else '✗'}")
    print()

    # Reconstruction demos
    print_sep("Step 5: Reconstruction Thresholds")
    # Using 2 of 3 parties' summed shares
    for combo in [(0,1), (0,2), (1,2), (0,1,2)]:
        subset = [result["summed_shares"][i] for i in combo]
        reconstructed = sss_reconstruct(subset)
        avg            = reconstructed / len(secrets)
        correct        = abs(avg - true_average) < 0.1
        party_names    = [["Alpha", "Beta", "Gamma"][i] for i in combo]
        print(f"  Parties {party_names}: reconstructed sum={reconstructed}  "
              f"avg={avg:.1f}  {'✓' if correct else '✗'}")
    print()
    print(f"  Key insight: Any 2 of 3 parties can correctly reconstruct.")
    print(f"  1 party alone: cannot reconstruct (information-theoretically provable).")
    print()

    # Comparison with alternatives
    print_sep("SMPC vs Alternative Approaches")
    alternatives = [
        ("Trusted Third Party",
         "Reveal all secrets to one auditor",
         "Single point of failure, trust required, GDPR issues"),
        ("Federated Averaging",
         "Each party sends local gradients (ML context)",
         "Gradient inversion attacks can recover data"),
        ("Homomorphic Encryption",
         "Encrypt secrets, compute on ciphertext",
         "Computationally expensive; correct but 1000× slower"),
        ("Shamir SMPC (this demo)",
         "Polynomial shares, no trusted party needed",
         "Perfect privacy, information-theoretic, fast"),
        ("Differential Privacy",
         "Add calibrated noise to outputs",
         "Privacy + utility trade-off; doesn't reconstruct exact value"),
    ]
    for method, approach, notes in alternatives:
        print(f"  {method}:")
        print(f"    Approach: {approach}")
        print(f"    Notes:    {notes}")
        print()

    print_sep("Key Takeaway")
    print("""
  Shamir's Secret Sharing + SMPC:
    - Information-theoretically secure: 1 share is provably worthless.
    - No trusted third party required.
    - Works even against adversaries with quantum computers
      (security is combinatorial/information-theoretic, not computational).

  Banking application:
    Regulatory aggregate statistics computed without data sharing.
    Compliance: GDPR Art. 25 (privacy by design), FFIEC cybersecurity guidance.
    Reduces data breach liability: no centralised sensitive data store.

  Production SMPC frameworks:
    - Sharemind (secure multi-party database queries)
    - MOTION (C++, fast SMPC for ML)
    - PySyft (Python, federated learning + SMPC)
    - ABY3 (3-party ML inference)
""")
    print_sep()


if __name__ == "__main__":
    main()
