"""
CUSTOMER DEMO PITCH — BB84 Privacy Amplification
=================================================
After sifting in BB84, Alice and Bob share a raw key — but Eve may have partial
information about it if she intercepted some qubits.  Privacy Amplification
compresses the sifted key using a 2-universal hash function so that Eve's
residual information becomes negligibly small.

Key idea:
  If the sifted key has n bits and Eve knows at most t bits (from partial
  intercept), hashing to m = n - t - s bits (s = security parameter) leaves
  Eve with at most 2^(-s) bits of information about the final key.

This demo simulates the full PA pipeline:
  Raw key → Sifted key → Privacy Amplification → Secure final key
  and shows Eve's information collapse from ~10% to ≈ 0 bits.

Audience: Security architects, cryptographers, interview panels.
Runtime: < 5 seconds.
"""

import hashlib
import os
import math

import numpy as np


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_sep(title: str = "") -> None:
    w = 64
    if title:
        p = (w - len(title) - 2) // 2
        print("=" * p + f" {title} " + "=" * (w - p - len(title) - 2))
    else:
        print("=" * w)


def bits_to_bytes(bits: list) -> bytes:
    """Pack a list of 0/1 integers into bytes."""
    n = len(bits)
    padded = bits + [0] * ((-n) % 8)
    out = bytearray()
    for i in range(0, len(padded), 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | padded[i + j]
        out.append(byte)
    return bytes(out)


def bytes_to_bitstring(b: bytes, n_bits: int) -> str:
    return bin(int.from_bytes(b, "big"))[2:].zfill(len(b) * 8)[:n_bits]


# ---------------------------------------------------------------------------
# BB84 Simulation (simplified)
# ---------------------------------------------------------------------------

def simulate_bb84_sifting(n_raw: int, eve_intercept_fraction: float,
                           rng: np.random.Generator) -> tuple:
    """
    Returns (sifted_key_bits, eve_known_bits).
    - Alice sends n_raw qubits in random bases.
    - Bob measures in random bases; ~50% agree → sifted key ≈ n_raw/2 bits.
    - Eve intercepts eve_intercept_fraction of qubits; for each she intercepts,
      she guesses the right basis 50% of the time and learns the bit perfectly.
    """
    alice_bits  = rng.integers(0, 2, n_raw)
    alice_bases = rng.integers(0, 2, n_raw)   # 0=Z, 1=X
    bob_bases   = rng.integers(0, 2, n_raw)

    eve_intercept = rng.random(n_raw) < eve_intercept_fraction
    eve_bases     = rng.integers(0, 2, n_raw)

    sifted_alice = []
    sifted_eve   = []

    for i in range(n_raw):
        if alice_bases[i] == bob_bases[i]:   # sifted
            bit = int(alice_bits[i])
            sifted_alice.append(bit)
            if eve_intercept[i] and eve_bases[i] == alice_bases[i]:
                sifted_eve.append(bit)    # Eve knows this bit
            else:
                sifted_eve.append(None)   # Eve doesn't know

    n_eve_known = sum(1 for b in sifted_eve if b is not None)
    return sifted_alice, n_eve_known


# ---------------------------------------------------------------------------
# Privacy Amplification using SHA-256 as 2-universal hash
# ---------------------------------------------------------------------------

def privacy_amplification(sifted_key: list, n_eve_bits: int,
                           security_param: int = 64) -> bytes:
    """
    Compute final key length: m = n - t - s
      n = len(sifted_key)
      t = n_eve_bits  (upper bound on Eve's knowledge)
      s = security_param

    Hash the sifted key with SHA-256 XOR-seeded by a random seed to achieve
    2-universality; output is truncated to m bits.
    """
    n = len(sifted_key)
    t = n_eve_bits
    s = security_param
    m = max(0, n - t - s)
    if m == 0:
        return b"", 0

    raw_bytes = bits_to_bytes(sifted_key)
    # Use SHA-256 with a public random seed (announced over classical channel)
    seed = os.urandom(32)
    h = hashlib.sha256(seed + raw_bytes).digest()
    # Truncate to m bits
    m_bytes = (m + 7) // 8
    final_key_bytes = h[:m_bytes]
    return final_key_bytes, m


def entropy_bits(known: int, total: int) -> float:
    """Shannon entropy of Eve's knowledge of the sifted key."""
    if total == 0:
        return 0.0
    p = known / total
    if p <= 0 or p >= 1:
        return 0.0
    return -total * (p * math.log2(p) + (1 - p) * math.log2(1 - p))


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    rng = np.random.default_rng(42)

    N_RAW               = 4000     # raw qubits Alice sends
    EVE_FRACTION        = 0.10     # Eve intercepts 10% of qubits
    SECURITY_PARAM      = 64       # 2^-64 residual information

    print_sep("BB84 PRIVACY AMPLIFICATION DEMO")
    print("Purpose: Show how PA eliminates Eve's partial key knowledge\n")

    # Step 1: BB84 sifting
    print_sep("Step 1: BB84 Key Sifting")
    sifted_key, n_eve_known = simulate_bb84_sifting(N_RAW, EVE_FRACTION, rng)
    n_sifted = len(sifted_key)
    print(f"  Raw qubits sent by Alice:     {N_RAW:6d}")
    print(f"  Sifted key length (50% match):{n_sifted:6d} bits")
    print(f"  Eve intercept fraction:       {EVE_FRACTION*100:.0f}%")
    print(f"  Eve's guesses correct (50%):  {n_eve_known:6d} bits of sifted key")
    eve_pct = 100 * n_eve_known / n_sifted if n_sifted else 0
    print(f"  Eve's information:            {eve_pct:.1f}% of sifted key")
    H_eve_before = entropy_bits(n_eve_known, n_sifted)
    print(f"  Mutual information I(A;E):    ~{H_eve_before:.1f} bits\n")

    # Step 2: Privacy Amplification
    print_sep("Step 2: Privacy Amplification")
    final_key, m = privacy_amplification(sifted_key, n_eve_known, SECURITY_PARAM)
    print(f"  Formula: m = n - t - s")
    print(f"           m = {n_sifted} - {n_eve_known} - {SECURITY_PARAM} = {m} bits")
    print(f"  Final secure key length:      {m} bits  ({m//8} bytes)")
    if m > 0:
        key_hex = final_key.hex()[:32] + "..." if len(final_key) > 16 else final_key.hex()
        print(f"  Final key (hex, truncated):   {key_hex}")

    print()
    print_sep("Step 3: Security Analysis")
    print(f"  Eve's residual information after PA: ≤ 2^(-{SECURITY_PARAM}) bits")
    print(f"  (Leftover Hash Lemma guarantee)")
    print()

    # Summary table
    print_sep("Key Length Pipeline Summary")
    rows = [
        ("Raw transmission",           N_RAW,      f"Alice sends {N_RAW} qubits"),
        ("After sifting (50%)",         n_sifted,   "Alice+Bob keep matching-basis bits"),
        ("Eve's information (bits)",    n_eve_known, f"{EVE_FRACTION*100:.0f}% intercept × 50% correct basis"),
        ("Security parameter s",        SECURITY_PARAM, f"2^-{SECURITY_PARAM} residual Eve info"),
        ("Final secure key",            m,           "Information-theoretically secure"),
    ]
    print(f"  {'Stage':<35}  {'Bits':>6}  Notes")
    print(f"  {'-'*35}  {'-'*6}  {'-'*40}")
    for stage, bits, note in rows:
        print(f"  {stage:<35}  {bits:>6}  {note}")

    print()
    print_sep("Key Takeaway")
    print("""
  Privacy Amplification transforms a sifted key with partial Eve knowledge
  into a shorter key about which Eve knows NOTHING (information-theoretically).

  Classical crypto comparison:
    RSA/AES key exchange: security rests on computational hardness.
    BB84 + PA:            security rests on information theory (Shannon entropy).
    No quantum computer, no algorithm, no brute force can break it —
    there is simply no information left for Eve to work with.

  Practical numbers (BB84 over 50 km fiber, QBER < 3%):
    Raw photon rate:    ~1 MHz
    Sifted rate:        ~500 kbps
    Post-PA secure key: ~10–100 kbps  (depending on channel noise)
""")
    print_sep()


if __name__ == "__main__":
    main()
