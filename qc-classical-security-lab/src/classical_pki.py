"""
Classical PKI Demo — RSA-2048, ECDSA P-256, X.509 Certificates
Demonstrates key generation, signing, verification, and certificate chains.
Shows quantum vulnerability of each component.

Quantum threat: RSA and ECDSA are both broken by Shor's algorithm.
"""

import time
import datetime
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography import x509
from cryptography.x509.oid import NameOID


# ---------------------------------------------------------------------------
# RSA-2048
# ---------------------------------------------------------------------------

def demo_rsa_2048():
    print("\n" + "=" * 60)
    print("RSA-2048 KEY GENERATION + SIGN + VERIFY")
    print("=" * 60)

    t0 = time.perf_counter()
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    keygen_ms = (time.perf_counter() - t0) * 1000

    public_key = private_key.public_key()
    message = b"Quantum-safe migration required by 2030 - NIST PQC"

    t0 = time.perf_counter()
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    sign_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    public_key.verify(
        signature,
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    verify_ms = (time.perf_counter() - t0) * 1000

    pub_bytes = public_key.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )

    print(f"  Key size        : 2048 bits")
    print(f"  Public key PEM  : {len(pub_bytes)} bytes")
    print(f"  Signature size  : {len(signature)} bytes")
    print(f"  Keygen time     : {keygen_ms:.2f} ms")
    print(f"  Sign time       : {sign_ms:.2f} ms")
    print(f"  Verify time     : {verify_ms:.2f} ms")
    print(f"  Verification    : PASS")
    print()
    print("  [QUANTUM THREAT] CRITICAL")
    print("  Algorithm       : Shor's algorithm (integer factorization)")
    print("  Logical qubits  : ~4,096 for RSA-2048")
    print("  Classical cost  : Sub-exponential (GNFS) — safe today")
    print("  Quantum cost    : Polynomial — broken with CRQC (~2030–2035)")

    return private_key, public_key


# ---------------------------------------------------------------------------
# ECDSA P-256
# ---------------------------------------------------------------------------

def demo_ecdsa_p256():
    print("\n" + "=" * 60)
    print("ECDSA P-256 KEY GENERATION + SIGN + VERIFY")
    print("=" * 60)

    t0 = time.perf_counter()
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    keygen_ms = (time.perf_counter() - t0) * 1000

    public_key = private_key.public_key()
    message = b"ECDSA is used in TLS 1.3, JWT ES256, and code signing"

    t0 = time.perf_counter()
    signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
    sign_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
    verify_ms = (time.perf_counter() - t0) * 1000

    pub_bytes = public_key.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )

    print(f"  Curve           : P-256 (secp256r1), 256-bit")
    print(f"  Public key PEM  : {len(pub_bytes)} bytes")
    print(f"  Signature size  : {len(signature)} bytes (DER-encoded)")
    print(f"  Keygen time     : {keygen_ms:.2f} ms")
    print(f"  Sign time       : {sign_ms:.2f} ms")
    print(f"  Verify time     : {verify_ms:.2f} ms")
    print(f"  Verification    : PASS")
    print()
    print("  [QUANTUM THREAT] CRITICAL")
    print("  Algorithm       : Shor's algorithm (discrete logarithm on EC)")
    print("  Logical qubits  : ~2,330 for P-256")
    print("  Classical cost  : Exponential — safe today")
    print("  Quantum cost    : Polynomial — broken with CRQC (~2030–2035)")

    return private_key, public_key


# ---------------------------------------------------------------------------
# X.509 Self-Signed Certificate (Root CA simulation)
# ---------------------------------------------------------------------------

def demo_x509_certificate(ca_key, issuer_name="Quantum Classical CA"):
    print("\n" + "=" * 60)
    print("X.509 SELF-SIGNED ROOT CA CERTIFICATE")
    print("=" * 60)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CA"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Ontario"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Quantum Security Lab"),
        x509.NameAttribute(NameOID.COMMON_NAME, issuer_name),
    ])

    t0 = time.perf_counter()
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None), critical=True
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256(), default_backend())
    )
    cert_ms = (time.perf_counter() - t0) * 1000

    cert_pem = cert.public_bytes(serialization.Encoding.PEM)

    print(f"  Subject/Issuer  : {issuer_name}")
    print(f"  Serial number   : {cert.serial_number}")
    print(f"  Not before      : {cert.not_valid_before_utc.date()}")
    print(f"  Not after       : {cert.not_valid_after_utc.date()} (+10 years)")
    print(f"  Signature algo  : sha256WithRSAEncryption")
    print(f"  Is CA           : True (BasicConstraints)")
    print(f"  Cert PEM size   : {len(cert_pem)} bytes")
    print(f"  Issue time      : {cert_ms:.2f} ms")
    print()
    print("  [QUANTUM THREAT] CRITICAL")
    print("  The X.509 cert chain relies on RSA-2048 signatures throughout.")
    print("  Compromising root CA key breaks entire trust chain.")
    print("  Migration target: ML-DSA (Dilithium) — FIPS 204")

    return cert


# ---------------------------------------------------------------------------
# Certificate chain: Root CA -> Intermediate CA -> End-Entity
# ---------------------------------------------------------------------------

def demo_certificate_chain():
    print("\n" + "=" * 60)
    print("X.509 CERTIFICATE CHAIN (Root → Intermediate → End-Entity)")
    print("=" * 60)

    # Root CA (RSA-2048)
    t0 = time.perf_counter()
    root_key = rsa.generate_private_key(65537, 2048, default_backend())
    root_name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "Quantum Lab Root CA"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Quantum Security Lab"),
    ])
    root_cert = (
        x509.CertificateBuilder()
        .subject_name(root_name)
        .issuer_name(root_name)
        .public_key(root_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=7300))
        .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
        .sign(root_key, hashes.SHA256(), default_backend())
    )

    # Intermediate CA (ECDSA P-256)
    int_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    int_name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "Quantum Lab Intermediate CA"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Quantum Security Lab"),
    ])
    int_cert = (
        x509.CertificateBuilder()
        .subject_name(int_name)
        .issuer_name(root_name)
        .public_key(int_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(root_key, hashes.SHA256(), default_backend())
    )

    # End-entity cert (ECDSA P-256)
    ee_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    ee_name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "api.quantum-bank.example"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Quantum Bank"),
    ])
    ee_cert = (
        x509.CertificateBuilder()
        .subject_name(ee_name)
        .issuer_name(int_name)
        .public_key(ee_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("api.quantum-bank.example")]),
            critical=False,
        )
        .sign(int_key, hashes.SHA256(), default_backend())
    )
    chain_ms = (time.perf_counter() - t0) * 1000

    print(f"  Root CA         : RSA-2048  | 20-year validity")
    print(f"  Intermediate CA : ECDSA P-256 | 10-year validity, signed by Root")
    print(f"  End-Entity      : ECDSA P-256 | 1-year validity, signed by Int CA")
    print(f"  Chain build ms  : {chain_ms:.2f} ms")
    print()
    print("  Chain verification (manual):")
    print(f"    Root signs Int CA  : sha256WithRSAEncryption")
    print(f"    Int CA signs EE    : sha256WithECDSAEncryption")
    print(f"    EE SAN             : api.quantum-bank.example")
    print()
    print("  [QUANTUM THREAT] CRITICAL")
    print("  Shor's breaks both RSA and ECDSA links in this chain.")
    print("  An attacker with CRQC can forge any intermediate or EE cert.")
    print("  Entire PKI hierarchy must migrate to ML-DSA / SLH-DSA.")

    return root_cert, int_cert, ee_cert


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print()
    print("##############################################################")
    print("#  CLASSICAL PKI DEMO — Quantum Portfolio Security Lab       #")
    print("#  Shows RSA-2048, ECDSA P-256, X.509 chain + threats        #")
    print("##############################################################")

    rsa_priv, rsa_pub = demo_rsa_2048()
    demo_ecdsa_p256()
    demo_x509_certificate(rsa_priv)
    demo_certificate_chain()

    print("\n" + "=" * 60)
    print("SUMMARY — PKI QUANTUM THREAT ASSESSMENT")
    print("=" * 60)
    print("  RSA-2048     : CRITICAL — broken by Shor's (~4096 qubits)")
    print("  ECDSA P-256  : CRITICAL — broken by Shor's (~2330 qubits)")
    print("  X.509 Chain  : CRITICAL — all signature links are vulnerable")
    print("  SHA-256 hash : MEDIUM   — Grover's halves collision resistance")
    print()
    print("  MIGRATION PATH:")
    print("    Signatures : ML-DSA (Dilithium)  — NIST FIPS 204")
    print("    Signatures : SLH-DSA (SPHINCS+)  — NIST FIPS 205")
    print("    KEM        : ML-KEM (Kyber)       — NIST FIPS 203")
    print("    Hashing    : SHA-384 / SHA-512    — Grover-resistant")
    print()


if __name__ == "__main__":
    main()
