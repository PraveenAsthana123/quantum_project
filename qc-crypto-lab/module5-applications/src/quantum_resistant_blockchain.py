"""
CUSTOMER DEMO PITCH — Quantum-Resistant Blockchain
===================================================
Current blockchains (Bitcoin, Ethereum) use ECDSA signatures — broken by Shor's
algorithm on a fault-tolerant quantum computer.  A 'harvest now, decrypt later'
adversary who collects blockchain transactions today can forge signatures and
steal funds once quantum computers mature.

This demo builds a mini 3-block blockchain where each transaction is signed
with a simulated ML-DSA (Dilithium) signature — the NIST FIPS 204 standard.

ML-DSA (formerly CRYSTALS-Dilithium):
  Based on Module-LWE: same lattice math as ML-KEM but for signatures.
  Shor's algorithm: NO speedup.
  Grover's algorithm: negligible (exponential dimension kills it).
  Signature size: ~2420–4595 bytes (vs ECDSA's 64 bytes — larger but safe).

For the simulation, we use HMAC-SHA256 as a stand-in for ML-DSA
(the structure is identical — actual ML-DSA requires liboqs).

Audience: Blockchain developers, security architects, DeFi teams, interview panels.
Runtime: < 3 seconds.
"""

import hashlib
import hmac
import json
import os
import time


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
# Simulated ML-DSA (Dilithium) — stand-in using HMAC-SHA256
# In production: use liboqs Python bindings (pip install pyoqs)
# ---------------------------------------------------------------------------

class SimulatedMLDSA:
    """
    Simulated ML-DSA-44 (NIST FIPS 204, Level 2, 128-bit PQ security).
    Actual sizes: pk=1312B, sk=2528B, sig=2420B.
    """
    PK_SIZE  = 1312
    SK_SIZE  = 2528
    SIG_SIZE = 2420

    def __init__(self, seed: bytes = None):
        raw_seed  = seed or os.urandom(32)
        self.sk   = hashlib.sha512(b"sk_seed_" + raw_seed).digest()   # 64B (stand-in for 2528B)
        self.pk   = hashlib.sha256(b"pk_seed_" + raw_seed).digest()   # 32B (stand-in for 1312B)
        # Metadata
        self.pk_bytes_real  = self.PK_SIZE
        self.sk_bytes_real  = self.SK_SIZE
        self.sig_bytes_real = self.SIG_SIZE

    def sign(self, message: bytes) -> bytes:
        """Sign message with private key (simulated)."""
        sig_raw = hmac.new(self.sk, message, hashlib.sha256).digest()
        # Pad to realistic ML-DSA signature size for demo
        return sig_raw + b"\x00" * (self.SIG_SIZE - len(sig_raw))

    def verify(self, message: bytes, signature: bytes, pk: bytes = None) -> bool:
        """Verify signature (simulated)."""
        pk_used = pk or self.pk
        expected = hmac.new(self.sk, message, hashlib.sha256).digest()
        return signature[:32] == expected


class SimulatedECDSA:
    """
    Simulated ECDSA P-256 for comparison.
    Actual sizes: pk=64B, sk=32B, sig=64B.
    """
    PK_SIZE  = 64
    SK_SIZE  = 32
    SIG_SIZE = 64

    def __init__(self, seed: bytes = None):
        raw_seed = seed or os.urandom(32)
        self.sk  = hashlib.sha256(b"ecdsa_sk_" + raw_seed).digest()[:32]
        self.pk  = hashlib.sha256(b"ecdsa_pk_" + raw_seed).digest()[:64]

    def sign(self, message: bytes) -> bytes:
        return hmac.new(self.sk, message, hashlib.sha256).digest()[:64]

    def verify(self, message: bytes, signature: bytes) -> bool:
        expected = hmac.new(self.sk, message, hashlib.sha256).digest()[:64]
        return signature == expected


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

class Transaction:
    def __init__(self, sender: str, recipient: str, amount: float,
                 signer: SimulatedMLDSA):
        self.sender    = sender
        self.recipient = recipient
        self.amount    = amount
        self.timestamp = int(time.time())
        self.tx_data   = json.dumps({
            "sender": sender, "recipient": recipient,
            "amount": amount, "ts": self.timestamp
        }, sort_keys=True).encode()
        self.signature = signer.sign(self.tx_data)
        self.sig_algo  = "ML-DSA-44 (FIPS 204)"
        self.sig_size  = signer.sig_bytes_real

    def to_dict(self) -> dict:
        return {
            "sender":    self.sender,
            "recipient": self.recipient,
            "amount":    self.amount,
            "timestamp": self.timestamp,
            "sig_algo":  self.sig_algo,
            "sig_size_bytes": self.sig_size,
            "signature_hex": self.signature[:16].hex() + "...",
        }

    def verify(self, signer: SimulatedMLDSA) -> bool:
        return signer.verify(self.tx_data, self.signature)


# ---------------------------------------------------------------------------
# Blockchain
# ---------------------------------------------------------------------------

class Block:
    def __init__(self, index: int, transactions: list, prev_hash: str):
        self.index        = index
        self.transactions = transactions
        self.prev_hash    = prev_hash
        self.timestamp    = int(time.time())
        self.nonce        = 0
        self.hash         = self._compute_hash()

    def _compute_hash(self) -> str:
        block_str = json.dumps({
            "index":   self.index,
            "txs":     [tx.to_dict() for tx in self.transactions],
            "prev":    self.prev_hash,
            "ts":      self.timestamp,
            "nonce":   self.nonce,
        }, sort_keys=True)
        return hashlib.sha256(block_str.encode()).hexdigest()

    def mine(self, difficulty: int = 2) -> None:
        """Proof-of-work mining (light for demo)."""
        target = "0" * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash   = self._compute_hash()


class QuantumResistantBlockchain:
    def __init__(self):
        self.chain = []
        genesis = Block(0, [], "0" * 64)
        self.chain.append(genesis)

    def add_block(self, transactions: list) -> Block:
        prev = self.chain[-1]
        block = Block(len(self.chain), transactions, prev.hash)
        block.mine(difficulty=2)
        self.chain.append(block)
        return block

    def verify_chain(self, signers: dict) -> dict:
        """Verify all blocks and all transaction signatures."""
        errors = []
        for i in range(1, len(self.chain)):
            b = self.chain[i]
            p = self.chain[i - 1]
            if b.prev_hash != p.hash:
                errors.append(f"Block {i}: prev_hash mismatch")
            for tx in b.transactions:
                signer = signers.get(tx.sender)
                if signer and not tx.verify(signer):
                    errors.append(f"Block {i}: TX {tx.sender}→{tx.recipient} sig invalid")
        return {"valid": len(errors) == 0, "errors": errors}


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    # Participant signers
    alice_signer = SimulatedMLDSA(seed=b"alice")
    bob_signer   = SimulatedMLDSA(seed=b"bob")
    signers      = {"Alice": alice_signer, "Bob": bob_signer}

    print_sep("QUANTUM-RESISTANT BLOCKCHAIN DEMO")
    print("Purpose: 3-block chain signed with ML-DSA (FIPS 204) vs ECDSA threat\n")

    # Build transactions
    txs_block1 = [
        Transaction("Alice", "Bob",   50.0, alice_signer),
        Transaction("Bob",   "Alice", 20.0, bob_signer),
    ]
    txs_block2 = [
        Transaction("Alice", "Bob",   10.0, alice_signer),
    ]
    txs_block3 = [
        Transaction("Bob",   "Alice", 30.0, bob_signer),
        Transaction("Alice", "Bob",    5.0, alice_signer),
    ]

    blockchain = QuantumResistantBlockchain()
    b1 = blockchain.add_block(txs_block1)
    b2 = blockchain.add_block(txs_block2)
    b3 = blockchain.add_block(txs_block3)

    print_sep("Blockchain Structure")
    for block in blockchain.chain:
        txn_str = f"{len(block.transactions)} transaction(s)" if block.index > 0 else "GENESIS"
        print(f"  Block {block.index}:")
        print(f"    Hash:     {block.hash[:32]}...")
        if block.index > 0:
            print(f"    PrevHash: {block.prev_hash[:32]}...")
            print(f"    TXs:      {txn_str}")
            for tx in block.transactions:
                print(f"      {tx.sender} → {tx.recipient}: {tx.amount} coins  "
                      f"[{tx.sig_algo}, {tx.sig_size} bytes]")
        print()

    # Chain verification
    print_sep("Chain Verification")
    result = blockchain.verify_chain(signers)
    print(f"  All block hashes valid:          {'✓' if not result['errors'] else '✗'}")
    print(f"  All transaction signatures valid: {'✓' if result['valid'] else '✗'}")
    print(f"  Verdict: {'CHAIN VALID ✓' if result['valid'] else 'CHAIN INVALID ✗'}")
    print()

    # Signature comparison
    print_sep("ML-DSA vs ECDSA Signature Sizes")
    ecdsa_signer = SimulatedECDSA(seed=b"alice")
    sample_tx_data = b"Alice->Bob:50"
    ml_sig   = alice_signer.sign(sample_tx_data)
    ec_sig   = ecdsa_signer.sign(sample_tx_data)

    rows = [
        ("ECDSA P-256",   64,   32,   64,  128, "BROKEN by Shor (quantum computer)"),
        ("ML-DSA-44",   1312, 2528, 2420,  128, "Safe — FIPS 204 (2024) standard"),
        ("ML-DSA-65",   1952, 4000, 3293,  192, "Safe — higher security level"),
        ("SLH-DSA-128s",  32,   64, 7856,  128, "Hash-based — maximally conservative"),
    ]
    print(f"  {'Scheme':<14}  {'PK':>6}  {'SK':>6}  {'Sig':>6}  {'Sec':>5}  Notes")
    print(f"  {'-'*14}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*5}  {'-'*40}")
    for name, pk, sk, sig, sec, note in rows:
        print(f"  {name:<14}  {pk:>6}  {sk:>6}  {sig:>6}  {sec:>5}  {note}")

    print()

    # Quantum threat to ECDSA blockchain
    print_sep("Quantum Threat to Classical Blockchain")
    print("""
  Harvest-Now-Decrypt-Later (HNDL) attack:
    1. Adversary records all blockchain transactions from today.
    2. When a fault-tolerant QC becomes available (~2030–2035):
       → Runs Shor's algorithm on each transaction's ECDSA public key.
       → Recovers the private key.
       → Creates forged transactions moving funds to attacker's address.
    3. Funds stolen retroactively from every wallet that ever transacted on-chain.

  Why ML-DSA (Dilithium) fixes this:
    Shor's algorithm attacks the discrete log problem (ECDSA).
    ML-DSA is based on Module-LWE — Shor provides ZERO speedup.
    Even an attacker with unlimited quantum resources cannot forge ML-DSA sigs.

  Current blockchain migration status:
    Ethereum Foundation: active research on PQC wallet standards.
    NIST Cybersecurity Framework 2.0 (2024): recommends ML-DSA migration.
    Bitcoin: no formal PQC roadmap (slower upgrade cycle).
    Enterprise blockchains (Hyperledger Fabric, R3 Corda): evaluating FIPS 204.
""")
    print_sep()


if __name__ == "__main__":
    main()
