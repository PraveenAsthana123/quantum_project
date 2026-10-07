"""
Shor's Algorithm ECC Attack Simulation
=======================================
Simulates Shor's Algorithm breaking Elliptic Curve Cryptography (ECC).
Covers ECDSA, ECDH, and implications for Bitcoin/Ethereum (secp256k1).

References:
- Roetteler et al. (2017). Quantum resource estimates for computing elliptic curve
  discrete logarithms. ASIACRYPT 2017. (Logical qubit formula: ~9n)
- NSA CNSA 2.0 (2022) — requires migration away from ECDH/ECDSA.
- NIST IR 8413 (2022) — PQC status report.

Educational use only — demonstrates defensive security concepts.
"""

import math


# ─────────────────────────────────────────────────────────────────────────────
# ECC Curve Resource Table (Roetteler et al. 2017 estimates)
# ─────────────────────────────────────────────────────────────────────────────
ECC_CURVES = {
    "P-256": {
        "bits":              256,
        "logical_qubits":    2330,
        "physical_qubits":   3_000_000,
        "used_in":           ["TLS 1.3", "HTTPS", "ECDSA signatures", "JWT (ES256)"],
        "nist_status":       "DEPRECATED — migrate to ML-KEM/ML-DSA",
        "classical_security": 128,
    },
    "P-384": {
        "bits":              384,
        "logical_qubits":    3484,
        "physical_qubits":   4_500_000,
        "used_in":           ["NSS (National Security Systems)", "Suite B", "DoD TLS"],
        "nist_status":       "DEPRECATED — CNSA 2.0 requires removal by 2030",
        "classical_security": 192,
    },
    "P-521": {
        "bits":              521,
        "logical_qubits":    4715,
        "physical_qubits":   6_000_000,
        "used_in":           ["High-assurance government systems"],
        "nist_status":       "DEPRECATED — quantum security = 0 bits",
        "classical_security": 260,
    },
    "secp256k1": {
        "bits":              256,
        "logical_qubits":    2330,
        "physical_qubits":   3_000_000,
        "used_in":           ["Bitcoin (BTC)", "Ethereum (ETH)", "ECDSA wallet signatures"],
        "nist_status":       "NOT STANDARDIZED BY NIST — crypto-asset use at extreme risk",
        "classical_security": 128,
    },
    "Ed25519": {
        "bits":              255,
        "logical_qubits":    2322,
        "physical_qubits":   3_000_000,
        "used_in":           ["SSH keys", "Signal", "Tor", "OpenSSH default"],
        "nist_status":       "DEPRECATED — pending NIST guidance (EdDSA)",
        "classical_security": 128,
    },
}

# Approximate crypto-asset values at risk (conservative estimates)
CRYPTO_MARKET = {
    "Bitcoin":  {"symbol": "BTC", "market_cap_usd": 1_300_000_000_000,
                  "curve": "secp256k1", "scheme": "ECDSA"},
    "Ethereum": {"symbol": "ETH", "market_cap_usd": 450_000_000_000,
                  "curve": "secp256k1", "scheme": "ECDSA"},
}


class ShorsECCAttack:
    """
    Simulates Shor's Algorithm solving the Elliptic Curve Discrete Logarithm
    Problem (ECDLP), recovering private keys from public keys.
    """

    # ── 1. Explain ECDLP ──────────────────────────────────────────────────────

    def explain_ecdlp(self) -> None:
        """Explain the ECDLP and why Shor's Algorithm solves it."""
        print("\n" + "="*70)
        print("  ELLIPTIC CURVE DISCRETE LOGARITHM PROBLEM (ECDLP)")
        print("="*70)
        print("""
WHAT IS AN ELLIPTIC CURVE?
──────────────────────────
  An elliptic curve over a finite field F_p is the set of points (x, y) satisfying:
    y² ≡ x³ + ax + b  (mod p)
  plus a "point at infinity" O (the group identity).

  Point addition P + Q = R is defined geometrically (chord-and-tangent rule)
  and is the group operation. Repeated addition gives scalar multiplication:
    k × G = G + G + G + ... + G   (k times)

THE ECDLP
─────────
  Given:   public key Q = k × G
           G = known base point (generator), Q = public key
  Find:    k = private key

  For a 256-bit curve: k ∈ [1, 2²⁵⁶]
  Best classical attack: Pohlig-Hellman + Baby-step Giant-step → O(√p) ≈ 2¹²⁸ operations
  Quantum attack (Shor's): O(n³) quantum gates → polynomial time

WHY SHOR'S WORKS ON ECDLP
──────────────────────────
  Shor's Algorithm solves the HIDDEN SUBGROUP PROBLEM (HSP) in abelian groups.
  Both integer factorization (RSA) and ECDLP reduce to the HSP:

  For ECDLP:
    Define function f: Z_r × Z_r → <G>
      f(a, b) = a×G + b×Q  =  (a + b×k)×G
    The hidden subgroup is {(a,b) : a + b×k ≡ 0 (mod r)}
    QFT over Z_r × Z_r reveals k directly.

  Quantum Phase Estimation + Quantum Fourier Transform → k in polynomial time.
  Once k is known, ALL transactions/signatures made with that key are forgeable.
""")

    # ── 2. Resource estimation ────────────────────────────────────────────────

    def estimate_resources(self, curve_name: str, bits: int = None) -> dict:
        """
        Estimate quantum resources to attack ECC curve.
        Formula: logical_qubits ≈ 9n (Roetteler et al. 2017).
        Physical qubits assume ~1500:1 surface code overhead for ECC
        (higher than RSA due to more complex arithmetic circuits).
        """
        if curve_name in ECC_CURVES:
            curve = ECC_CURVES[curve_name]
            n = curve["bits"]
        elif bits is not None:
            n = bits
            curve = {
                "logical_qubits":    9 * n,
                "physical_qubits":   9 * n * 1500,
                "used_in":           ["custom curve"],
                "nist_status":       "unknown",
                "classical_security": n // 2,
            }
        else:
            raise ValueError(f"Unknown curve: {curve_name}. Provide bits parameter.")

        logical  = curve["logical_qubits"]
        physical = curve["physical_qubits"]

        # Runtime estimate: roughly proportional to n² gates at ~10^9 gates/second
        gate_count = 500 * (n ** 3)   # rough Roetteler estimate
        runtime_s  = gate_count / 1e9
        if runtime_s < 3600:
            runtime_str = f"~{runtime_s/60:.0f} minutes"
        elif runtime_s < 86400:
            runtime_str = f"~{runtime_s/3600:.1f} hours"
        else:
            runtime_str = f"~{runtime_s/86400:.1f} days"

        return {
            "curve":             curve_name,
            "bits":              n,
            "classical_security": curve["classical_security"],
            "post_quantum_security": 0,
            "logical_qubits":    logical,
            "physical_qubits":   physical,
            "gate_count_approx": f"~{gate_count:,}",
            "crqc_runtime":      runtime_str,
            "used_in":           curve.get("used_in", []),
            "nist_status":       curve.get("nist_status", "unknown"),
        }

    # ── 3. Bitcoin/Ethereum impact ────────────────────────────────────────────

    def bitcoin_impact(self) -> None:
        """
        Show value of Bitcoin and Ethereum at risk from quantum attack on ECDSA.
        """
        print("\n" + "="*70)
        print("  QUANTUM ATTACK IMPACT ON CRYPTO ASSETS")
        print("="*70)

        total_at_risk = sum(a["market_cap_usd"] for a in CRYPTO_MARKET.values())

        print(f"""
ATTACK VECTOR
─────────────
  Bitcoin and Ethereum both use secp256k1 + ECDSA.
  A quantum computer running Shor's Algorithm can:

  1. Scan the public blockchain for public keys exposed in transactions.
     (Pre-P2PKH addresses and reused addresses expose the public key directly)
  2. Run Shor's Algorithm → recover private key k from public key Q = k×G.
  3. Sign fraudulent transactions spending those funds.
  4. Entire process per key: ~8 hours on a mature CRQC (same circuit as RSA-2048).

EXPOSED ADDRESSES (estimates)
──────────────────────────────
  Bitcoin addresses with exposed public keys (P2PK/reused P2PKH): ~4 million BTC
  Estimated value at known exposed addresses: ~$240 billion USD
  Ethereum EOA accounts (all expose public key after first tx): >98% of ETH supply

MARKET CAPITALIZATION AT RISK
──────────────────────────────""")

        for name, data in CRYPTO_MARKET.items():
            mc_t = data["market_cap_usd"] / 1e12
            print(f"  {name} ({data['symbol']}):  ${mc_t:.2f} trillion  |  Curve: {data['curve']}  |  Scheme: {data['scheme']}")

        total_t = total_at_risk / 1e12
        print(f"\n  TOTAL DIRECT EXPOSURE:  ${total_t:.2f} trillion USD")
        print(f"  Additional systemic risk from market panic: unquantifiable\n")

        print("""MIGRATION STATUS
────────────────
  Bitcoin has no governance mechanism for protocol-level PQC migration.
  Ethereum is researching quantum-resistant signatures (EIP proposals).
  No major blockchain has deployed production PQC signature scheme.
  Timeline pressure: HNDL attacks can harvest public keys NOW for later decryption.

RECOMMENDATION
──────────────
  Move funds to fresh quantum-resistant addresses (Taproot + PQC hybrid) when
  standards finalize. Watch NIST FIPS 204 (ML-DSA) integration proposals.
""")

    # ── 4. Full demonstration ─────────────────────────────────────────────────

    def demonstrate_attack(self) -> None:
        """
        Show public key Q = k*G, explain how Shor's recovers k.
        Uses P-256 as example (secp256k1 identical structure).
        """
        print("\n" + "="*70)
        print("  QUANTUM ATTACK DEMONSTRATION — ECDSA on P-256")
        print("="*70)
        print("""
SETUP — P-256 KEY PAIR
──────────────────────
  Curve:        NIST P-256 (secp256r1)
  Prime p:      2²⁵⁶ - 2²²⁴ + 2¹⁹² + 2⁹⁶ - 1  (78-digit prime)
  Base point G: (known standard value, 256-bit coordinates)
  Order r:      2²⁵⁶ - 4319055...  (256-bit prime)

  Private key:  k  (random 256-bit integer, NEVER transmitted)
  Public key:   Q = k × G  (elliptic curve point, transmitted openly)

  TLS handshake, JWT ES256, SSH ecdsa-sha2-nistp256 — all expose Q.

CLASSICAL DIFFICULTY
────────────────────
  Given Q and G, find k such that Q = k × G.
  Best classical algorithm (Pollard's rho): O(√r) ≈ 2¹²⁸ operations.
  At 10¹⁸ ops/second (all world's compute): 3.4 × 10²⁰ years.
  PRACTICALLY IMPOSSIBLE classically.

QUANTUM ATTACK STEPS
────────────────────
  Step 1 — Encode problem into quantum registers:
    |0⟩^⊗n |0⟩^⊗n  →  two 256-qubit registers

  Step 2 — Create uniform superposition:
    Apply H⊗²ⁿ:  (1/r) Σ_{a,b} |a⟩|b⟩

  Step 3 — Quantum oracle for elliptic curve group law:
    Compute |a⟩|b⟩ → |a⟩|b⟩|a×G + b×Q⟩
    This requires quantum arithmetic for point addition on P-256.
    Circuit depth: ~9 × 256 = 2304 logical qubits (Roetteler 2017)

  Step 4 — Measure the third register:
    Collapses to a fixed point P = a₀G + b₀Q
    First two registers now entangled in coset state.

  Step 5 — Quantum Fourier Transform over Z_r × Z_r:
    Peaks at integer multiples of (k, -1) → directly yields k!

  Step 6 — Classical post-processing:
    Continued fraction algorithm extracts k from QFT measurement.
    PRIVATE KEY k RECOVERED.

  Step 7 — Forge signatures:
    ECDSA sign(m) = (r, s) where s = k⁻¹(H(m) + r×privkey) mod n
    With recovered k, forge valid signature for ANY message.
    Impersonate TLS server, forge JWT tokens, drain Bitcoin wallets.

RESOURCE SUMMARY (P-256 / secp256k1)
──────────────────────────────────────
  Logical qubits:    2,330
  Physical qubits:   ~3,000,000  (surface code, 1500:1 overhead)
  Circuit depth:     ~500 billion gates
  CRQC runtime:      ~8–12 hours

  One quantum computer breaks every P-256 key ever generated.
  TLS becomes transparent. Every HTTPS session retroactively exposed.
""")

    # ── Main ──────────────────────────────────────────────────────────────────

    def _print_resource_table(self) -> None:
        print("\n  ECC QUANTUM ATTACK RESOURCE REQUIREMENTS")
        print("  " + "-"*75)
        print(f"  {'Curve':<12} {'Bits':<6} {'Classical Sec':<16} {'Logical Q':<12} {'Physical Q':<18} {'Status'}")
        print("  " + "-"*75)
        for name in ["P-256", "P-384", "P-521", "secp256k1", "Ed25519"]:
            r = self.estimate_resources(name)
            phys = f"{r['physical_qubits']:,}"
            print(f"  {name:<12} {r['bits']:<6} {r['classical_security']:<16} {r['logical_qubits']:<12,} {phys:<18} BROKEN")
        print()


def main():
    attacker = ShorsECCAttack()

    attacker.explain_ecdlp()

    print("\n")
    attacker._print_resource_table()

    attacker.bitcoin_impact()

    attacker.demonstrate_attack()

    print("  SECURITY RECOMMENDATION")
    print("  " + "-"*65)
    print("  ALL ECC curves (P-256, P-384, P-521, secp256k1, Ed25519) are")
    print("  broken by Shor's Algorithm on a CRQC. Quantum security = 0 bits.")
    print("  Migrate to: ML-KEM-768 (FIPS 203), ML-DSA-65 (FIPS 204)")
    print("  Crypto-assets: watch NIST PQC integration proposals for blockchains.")
    print()


if __name__ == "__main__":
    main()
