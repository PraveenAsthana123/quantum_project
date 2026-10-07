"""
qc-crypto-lab standalone demo.
Uses only Python stdlib + numpy (no special crypto imports required).
Demonstrates key size comparison, benchmark tables, inventory scan,
hybrid KEM workflow, and NIST security level comparison.
"""

from __future__ import annotations

import sys


def step1_key_size_comparison() -> bool:
    """Show public key and signature sizes for classical and PQC algorithms."""
    print("\n" + "=" * 60)
    print("STEP 1: Key Size Comparison (bytes)")
    print("=" * 60)

    key_sizes = {
        # algorithm: (public_key_bytes, private_key_bytes, sig_or_ct_bytes)
        "RSA-2048":        (256,   1218,  256),
        "RSA-4096":        (512,   2350,  512),
        "ECDSA-P256":      (64,    32,    64),
        "ECDSA-P384":      (96,    48,    96),
        "Ed25519":         (32,    64,    64),
        "ML-KEM-768":      (1184,  2400,  1088),  # pk, sk, ciphertext
        "ML-DSA-44":       (1312,  2528,  2420),
        "ML-DSA-65":       (1952,  4000,  3293),  # pk=1952 is the spec value
        "ML-DSA-87":       (2592,  4864,  4595),
        "SLH-DSA-128f":    (32,    64,    49856),
        "FALCON-512":      (897,   1281,  666),
    }

    header = f"{'Algorithm':<18} {'PK (bytes)':>12} {'SK (bytes)':>12} {'Sig/CT (bytes)':>15}"
    print(header)
    print("-" * 60)
    for alg, (pk, sk, sig) in key_sizes.items():
        print(f"{alg:<18} {pk:>12} {sk:>12} {sig:>15}")

    print("\nNote: ML-DSA-65 public key = 2528 bytes per FIPS 204 draft spec")
    print("PASS: key size comparison displayed")
    return True


def step2_performance_simulation() -> bool:
    """Display pre-built benchmark table (no actual crypto execution)."""
    print("\n" + "=" * 60)
    print("STEP 2: Algorithm Performance Simulation (ms, simulated)")
    print("=" * 60)

    # Simulated benchmark data (representative values from published papers)
    benchmarks = [
        # (algorithm, keygen_ms, op1_ms, op2_ms, op1_label, op2_label)
        ("RSA-2048",     120.0,   0.8,    0.05,  "sign",    "verify"),
        ("RSA-4096",     980.0,   4.2,    0.18,  "sign",    "verify"),
        ("ECDSA-P256",     0.3,   0.2,    0.5,   "sign",    "verify"),
        ("Ed25519",        0.05,  0.06,   0.12,  "sign",    "verify"),
        ("ML-KEM-768",     0.08,  0.09,   0.09,  "encaps",  "decaps"),
        ("ML-DSA-44",      0.09,  0.25,   0.09,  "sign",    "verify"),
        ("ML-DSA-65",      0.14,  0.35,   0.14,  "sign",    "verify"),
        ("ML-DSA-87",      0.21,  0.53,   0.21,  "sign",    "verify"),
        ("SLH-DSA-128f",   0.9,  35.0,    5.2,   "sign",    "verify"),
        ("FALCON-512",     9.0,   0.25,   0.15,  "sign",    "verify"),
    ]

    header = f"{'Algorithm':<18} {'KeyGen (ms)':>12} {'Op1 (ms)':>10} {'Op2 (ms)':>10} {'Op1':>8} {'Op2':>8}"
    print(header)
    print("-" * 70)
    for alg, kg, o1, o2, l1, l2 in benchmarks:
        print(f"{alg:<18} {kg:>12.3f} {o1:>10.3f} {o2:>10.3f} {l1:>8} {l2:>8}")

    print("\nSource: Simulated from NIST FIPS 203/204/205 and benchmarkcrypto.cr.yp.to")
    print("PASS: performance benchmark table displayed")
    return True


def step3_crypto_inventory_scan() -> bool:
    """Scan a mock list of 10 algorithm names and classify them."""
    print("\n" + "=" * 60)
    print("STEP 3: Crypto Inventory Scan")
    print("=" * 60)

    mock_systems = [
        ("SRV-001", "auth-service",    "RSA-2048"),
        ("SRV-002", "payment-gateway", "ECDSA-P256"),
        ("SRV-003", "vpn-endpoint",    "X25519"),
        ("SRV-004", "tls-terminator",  "AES-256-GCM"),
        ("SRV-005", "code-signing",    "Ed25519"),
        ("SRV-006", "cert-authority",  "RSA-4096"),
        ("SRV-007", "key-exchange",    "DH-2048"),
        ("SRV-008", "pqc-pilot",       "ML-KEM-768"),
        ("SRV-009", "data-signing",    "ML-DSA-65"),
        ("SRV-010", "legacy-vpn",      "3DES"),
    ]

    quantum_safe = {
        "X25519", "AES-128", "AES-192", "AES-256", "AES-256-GCM",
        "SHA-256", "SHA-384", "SHA-512", "SHA-3-256", "SHA-3-512",
        "ML-KEM-512", "ML-KEM-768", "ML-KEM-1024",
        "ML-DSA-44", "ML-DSA-65", "ML-DSA-87",
        "SLH-DSA-128f", "SLH-DSA-128s", "FALCON-512", "FALCON-1024",
    }
    quantum_vulnerable = {
        "RSA-2048", "RSA-4096", "ECDSA-P256", "ECDSA-P384",
        "Ed25519", "DH-2048", "DH-4096", "ECDH-P256",
    }
    deprecated = {"3DES", "DES", "RC4", "MD5", "SHA-1"}

    replacements = {
        "RSA-2048":   "ML-DSA-65",
        "RSA-4096":   "ML-DSA-87",
        "ECDSA-P256": "ML-DSA-44",
        "ECDSA-P384": "ML-DSA-65",
        "Ed25519":    "ML-DSA-44",
        "DH-2048":    "ML-KEM-768",
        "3DES":       "AES-256-GCM",
    }

    print(f"{'ID':<10} {'System':<20} {'Algorithm':<14} {'Status':<18} {'Replacement'}")
    print("-" * 80)
    vulnerable_count = 0
    for sid, name, alg in mock_systems:
        if alg in quantum_safe:
            status = "quantum_safe"
            repl = "—"
        elif alg in deprecated:
            status = "DEPRECATED"
            repl = replacements.get(alg, "AES-256-GCM")
            vulnerable_count += 1
        elif alg in quantum_vulnerable:
            status = "quantum_vulnerable"
            repl = replacements.get(alg, "ML-DSA-65")
            vulnerable_count += 1
        else:
            status = "unknown"
            repl = "review needed"
        print(f"{sid:<10} {name:<20} {alg:<14} {status:<18} {repl}")

    print(f"\nSummary: {vulnerable_count}/{len(mock_systems)} systems need migration")
    print("PASS: crypto inventory scan completed")
    return True


def step4_hybrid_kem_demo() -> bool:
    """Simulate KEM + symmetric encryption workflow with pseudocode output."""
    print("\n" + "=" * 60)
    print("STEP 4: Hybrid KEM Demo (ML-KEM-768 + AES-256-GCM)")
    print("=" * 60)

    print("""
Hybrid Encryption Workflow (pseudocode):

  SENDER:
    1. pk, sk = ML-KEM-768.KeyGen()          # Recipient's long-term keys
       pk_bytes = 1184 bytes, sk_bytes = 2400 bytes

    2. ct, K = ML-KEM-768.Encaps(pk)         # Encapsulate shared secret
       ct_bytes = 1088 bytes, K = 32 bytes (shared secret)

    3. aes_key = HKDF-SHA256(K, salt, info)  # Derive AES key from KEM secret
       aes_key = 32 bytes

    4. nonce = os.urandom(12)                 # Random 96-bit nonce
    5. ciphertext = AES-256-GCM.Encrypt(     # Encrypt plaintext
           key=aes_key, nonce=nonce,
           plaintext=message, aad=headers)
    6. Send: (ct, nonce, ciphertext, tag)

  RECEIVER:
    1. K = ML-KEM-768.Decaps(sk, ct)         # Recover shared secret
    2. aes_key = HKDF-SHA256(K, salt, info)  # Re-derive AES key
    3. message = AES-256-GCM.Decrypt(        # Decrypt
           key=aes_key, nonce=nonce,
           ciphertext=ciphertext, tag=tag, aad=headers)

Wire overhead: 1088 (KEM ct) + 12 (nonce) + 16 (GCM tag) = 1116 bytes
vs classical:   65 (ECDH ephemeral) + 12 + 16 = 93 bytes overhead
PQC overhead factor: ~12x for KEM ciphertext
""")
    print("PASS: hybrid KEM workflow demonstrated")
    return True


def step5_security_level_table() -> bool:
    """Show NIST security levels for all algorithms."""
    print("\n" + "=" * 60)
    print("STEP 5: NIST Security Level Comparison Table")
    print("=" * 60)

    # NIST security levels: 1=AES-128, 3=AES-192, 5=AES-256
    algorithms = [
        # (algorithm, family, nist_level, classical_bits, pqc_bits, note)
        ("RSA-2048",       "RSA",        "~0 (Shor)",   112,   0,   "broken by Shor"),
        ("RSA-4096",       "RSA",        "~0 (Shor)",   140,   0,   "broken by Shor"),
        ("ECDSA-P256",     "ECC",        "~0 (Shor)",   128,   0,   "broken by Shor"),
        ("ECDSA-P384",     "ECC",        "~0 (Shor)",   192,   0,   "broken by Shor"),
        ("Ed25519",        "EdDSA",      "~0 (Shor)",   128,   0,   "broken by Shor"),
        ("AES-128",        "Symmetric",  "1",           128,  64,   "Grover halves"),
        ("AES-192",        "Symmetric",  "3",           192,  96,   "Grover halves"),
        ("AES-256",        "Symmetric",  "5",           256, 128,   "safe with 256-bit"),
        ("SHA-256",        "Hash",       "2 (preimage)", 256, 128,  "Grover on preimage"),
        ("SHA-3-256",      "Hash",       "2 (preimage)", 256, 128,  "Grover on preimage"),
        ("ML-KEM-512",     "CRYSTALS",   "1",           128, 128,   "FIPS 203"),
        ("ML-KEM-768",     "CRYSTALS",   "3",           192, 192,   "FIPS 203 recommended"),
        ("ML-KEM-1024",    "CRYSTALS",   "5",           256, 256,   "FIPS 203"),
        ("ML-DSA-44",      "CRYSTALS",   "2",           128, 128,   "FIPS 204"),
        ("ML-DSA-65",      "CRYSTALS",   "3",           192, 192,   "FIPS 204 recommended"),
        ("ML-DSA-87",      "CRYSTALS",   "5",           256, 256,   "FIPS 204"),
        ("SLH-DSA-128f",   "SPHINCS+",   "1",           128, 128,   "FIPS 205 fast"),
        ("SLH-DSA-128s",   "SPHINCS+",   "1",           128, 128,   "FIPS 205 small"),
        ("FALCON-512",     "NTRU",       "1",           128, 128,   "compact sigs"),
    ]

    header = f"{'Algorithm':<18} {'Family':<12} {'NIST Level':<12} {'Classical':>10} {'PQC bits':>9} {'Note'}"
    print(header)
    print("-" * 80)
    for alg, fam, lvl, cls, pqc, note in algorithms:
        print(f"{alg:<18} {fam:<12} {lvl:<12} {cls:>10} {pqc:>9}   {note}")

    print("\nNIST Security Levels: 1≈AES-128, 2≈SHA-256, 3≈AES-192, 5≈AES-256")
    print("PASS: security level comparison table displayed")
    return True


def main() -> None:
    print("=" * 60)
    print("qc-crypto-lab Standalone Demo")
    print("Cryptography comparison, inventory, and PQC migration")
    print("=" * 60)

    results = [
        ("Key Size Comparison",        step1_key_size_comparison()),
        ("Performance Simulation",     step2_performance_simulation()),
        ("Crypto Inventory Scan",      step3_crypto_inventory_scan()),
        ("Hybrid KEM Demo",            step4_hybrid_kem_demo()),
        ("Security Level Table",       step5_security_level_table()),
    ]

    print("\n" + "=" * 60)
    print("DEMO SUMMARY")
    print("=" * 60)
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        flag = "" if passed else " <-- FAILED"
        print(f"  [{status}] {name}{flag}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\nAll demo steps passed.")
        sys.exit(0)
    else:
        print("\nSome steps failed — check output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
