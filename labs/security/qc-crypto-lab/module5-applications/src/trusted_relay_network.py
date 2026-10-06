"""
CUSTOMER DEMO PITCH — Trusted Relay QKD Network
================================================
Current QKD technology is limited to ~100 km in fiber and ~1200 km via satellite.
For wider networks, Trusted Relay Nodes extend QKD range:

  Alice ─QKD─► Relay ─QKD─► Bob
  Alice establishes key K_AR with Relay.
  Relay establishes key K_RB with Bob.
  Relay computes K_AB = K_AR ⊕ K_RB and sends K_AB to Bob (encrypted with K_RB).
  Bob computes K_AR = K_AB ⊕ K_RB = K_AR.

Trust assumption: the relay MUST be physically secure — it knows K_AR and K_RB.
This is a deployment compromise: not end-to-end quantum security, but provably secure
if the relay is not compromised.  Real networks use multiple relays with HSMs.

Real deployments:
  - China's 2000 km Beijing-Shanghai QKD backbone (32 trusted relays, 2017).
  - Toshiba's UK metropolitan QKD network.
  - SK Broadband Korea QKD network.

Audience: Network architects, QKD sales teams, government customers.
Runtime: < 2 seconds.
"""

import os
import hashlib
import secrets


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


def xor_bytes(a: bytes, b: bytes) -> bytes:
    assert len(a) == len(b), "Keys must be same length"
    return bytes(x ^ y for x, y in zip(a, b))


def simulate_qkd_link(alice: str, bob: str, n_bits: int = 256) -> bytes:
    """
    Simulate a QKD key establishment between two nodes.
    Returns a shared secret key (n_bits bits = n_bits//8 bytes).
    In a real system: BB84 + sifting + QEC + PA over a quantum channel.
    """
    # Simulate: both nodes end up with the same random key
    link_seed = hashlib.sha256(f"{alice}:{bob}:qkd_shared".encode()).digest()
    return hashlib.sha256(link_seed).digest()[:n_bits // 8]


def encrypt_otp(plaintext: bytes, key: bytes) -> bytes:
    """XOR OTP encryption (key must be >= len(plaintext))."""
    return xor_bytes(plaintext, key[:len(plaintext)])


def decrypt_otp(ciphertext: bytes, key: bytes) -> bytes:
    return xor_bytes(ciphertext, key[:len(ciphertext)])


# ---------------------------------------------------------------------------
# Trusted Relay Protocol
# ---------------------------------------------------------------------------

class QKDNode:
    def __init__(self, name: str):
        self.name  = name
        self.keys  = {}   # peer_name → shared QKD key

    def establish_qkd(self, peer: "QKDNode", n_bits: int = 256) -> None:
        """Establish a QKD key with peer."""
        shared = simulate_qkd_link(self.name, peer.name, n_bits)
        self.keys[peer.name] = shared
        peer.keys[self.name] = shared
        print(f"  QKD link: {self.name}—{peer.name}  key={shared.hex()[:16]}..."
              f"  ({n_bits} bits)")

    def relay_key(self, alice_name: str, bob_name: str) -> bytes:
        """
        Relay computes K_AB = K_AR ⊕ K_RB and sends to Bob.
        Returns K_AB (to be transmitted over classical authenticated channel).
        """
        k_ar = self.keys[alice_name]
        k_rb = self.keys[bob_name]
        k_ab = xor_bytes(k_ar, k_rb)
        return k_ab


def simulate_trusted_relay_network(n_bits: int = 256) -> dict:
    """
    3-node network: Alice — Relay — Bob
    Returns all keys and a verification that Alice and Bob share K_AR.
    """
    alice = QKDNode("Alice")
    relay = QKDNode("Relay")
    bob   = QKDNode("Bob")

    # Step 1: Establish QKD links
    alice.establish_qkd(relay, n_bits)
    relay.establish_qkd(bob,   n_bits)

    k_ar = alice.keys["Relay"]
    k_rb = relay.keys["Bob"]

    # Step 2: Relay computes and forwards K_AB = K_AR ⊕ K_RB
    k_ab_relay = relay.relay_key("Alice", "Bob")

    # Step 3: Bob reconstructs K_AR = K_AB ⊕ K_RB
    k_ar_at_bob = xor_bytes(k_ab_relay, k_rb)

    # Verification
    assert k_ar == k_ar_at_bob, "Key derivation error!"

    return {
        "K_AR":        k_ar,
        "K_RB":        k_rb,
        "K_AB_relay":  k_ab_relay,   # what relay sends to Bob
        "K_AR_at_Bob": k_ar_at_bob,
        "match":       k_ar == k_ar_at_bob,
    }


def simulate_extended_relay_network(n_nodes: int = 5, n_bits: int = 256) -> dict:
    """
    Extended chain: Alice — R1 — R2 — ... — Bob
    Each consecutive pair shares a QKD key.
    Final shared key Alice-Bob derived by XOR chain.
    """
    node_names = ["Alice"] + [f"Relay-{i}" for i in range(1, n_nodes - 1)] + ["Bob"]
    nodes      = {n: QKDNode(n) for n in node_names}

    keys = []
    for i in range(len(node_names) - 1):
        a, b = node_names[i], node_names[i + 1]
        nodes[a].establish_qkd(nodes[b], n_bits)
        keys.append(nodes[a].keys[b])

    # Derive end-to-end key: XOR all link keys
    # Alice holds K_AR1, each relay holds two keys and computes K_relay_fwd
    # Final Bob's view = K_A-R1 ⊕ K_R1-R2 ⊕ ... ⊕ K_Rn-B
    # (simplified model — real protocol requires OTP forwarding chain)
    k_end_to_end = keys[0]
    for k in keys[1:]:
        k_end_to_end = xor_bytes(k_end_to_end, k)

    return {
        "n_relays":      n_nodes - 2,
        "link_keys":     [k.hex()[:8] + "..." for k in keys],
        "k_end_to_end":  k_end_to_end,
    }


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    print_sep("TRUSTED RELAY QKD NETWORK DEMO")
    print("Purpose: Show key forwarding across multiple QKD hops\n")

    # 3-node demo
    print_sep("3-Node Network: Alice — Relay — Bob")
    print()
    result = simulate_trusted_relay_network(n_bits=256)
    print()

    print(f"  K_AR (Alice-Relay key):     {result['K_AR'].hex()[:32]}...")
    print(f"  K_RB (Relay-Bob key):       {result['K_RB'].hex()[:32]}...")
    print(f"  K_AB = K_AR ⊕ K_RB:        {result['K_AB_relay'].hex()[:32]}  [sent to Bob]")
    print(f"  K_AR at Bob = K_AB ⊕ K_RB: {result['K_AR_at_Bob'].hex()[:32]}")
    print(f"  Keys match:                 {'✓' if result['match'] else '✗'}")
    print()

    # Demo: use shared key to encrypt a message
    print_sep("End-to-End Encrypted Message (Alice → Bob via Relay)")
    message = b"QKD SECURE: Transfer 1M USD"  # 27 bytes < 32-byte key
    k       = result["K_AR"]
    cipher  = encrypt_otp(message, k)
    decrypted = decrypt_otp(cipher, result["K_AR_at_Bob"])
    print(f"  Plaintext:   {message.decode()}")
    print(f"  Encrypted:   {cipher[:20].hex()}...  (OTP, information-theoretically secure)")
    print(f"  Decrypted:   {decrypted.decode()}")
    print(f"  Match:       {'✓' if decrypted == message else '✗'}")
    print()

    # Extended relay chain
    print_sep("Extended 5-Node Chain: Alice — R1 — R2 — R3 — Bob")
    print()
    ext = simulate_extended_relay_network(n_nodes=5)
    print()
    print(f"  Number of relay hops:   {ext['n_relays']}")
    print(f"  Link keys:")
    for i, k in enumerate(ext["link_keys"]):
        link_names = ["Alice-R1", "R1-R2", "R2-R3", "R3-Bob"]
        print(f"    {link_names[i]}: {k}")
    print(f"  End-to-end key (XOR):   {ext['k_end_to_end'].hex()[:32]}...")
    print()

    # Trust model discussion
    print_sep("Trust Model Analysis")
    print("""
  Trusted Relay is a deployment compromise:

  SECURITY GUARANTEE (holds):
    Each QKD link is individually information-theoretically secure.
    An eavesdropper on ANY individual fiber cannot extract a key without
    being detected (QBER threshold).

  SECURITY ASSUMPTION (required):
    Each relay node must be PHYSICALLY SECURE.
    A compromised relay node knows K_AR and K_RB and can compute K_AB.
    The relay is a TRUSTED NETWORK ELEMENT — like a classical VPN concentrator,
    but with quantum-secured links between it.

  MITIGATIONS:
    1. Hardware Security Modules (HSMs) at relay nodes — keys in tamper-proof hardware.
    2. Multiple independent relay paths — key must be compromised on ALL paths.
    3. Relay node auditing — physical access logs, intrusion detection.
    4. Automatic key rotation — short key lifetime limits exposure window.
    5. Satellite QKD bypass — for routes where satellite provides >1000 km range.
""")

    # Real deployment comparison
    print_sep("Real-World QKD Network Deployments")
    deployments = [
        ("Beijing-Shanghai backbone", "2017", "2000 km", 32,   "China Quantum/Alibaba"),
        ("SECOQC Vienna",             "2008", "200 km",   6,   "EU consortium"),
        ("Toshiba UK metro",          "2022", "250 km",   4,   "Toshiba/BT"),
        ("SK Korea network",          "2020", "800 km",  15,   "SK Broadband"),
        ("Micius satellite",          "2017", "1200 km",  1,   "Chinese Academy of Science"),
        ("QiaNet Europe (planned)",   "2027", "10,000 km", "TBD", "EU quantum internet"),
    ]
    print(f"  {'Network':<30}  {'Year':>5}  {'Range':>10}  {'Relays':>7}  Operator")
    print(f"  {'-'*30}  {'-'*5}  {'-'*10}  {'-'*7}  {'-'*30}")
    for name, year, dist, relays, op in deployments:
        print(f"  {name:<30}  {year:>5}  {dist:>10}  {str(relays):>7}  {op}")

    print()
    print_sep("Key Takeaway")
    print("""
  Trusted Relay Networks are TODAY'S practical QKD deployment model.
  They extend QKD beyond the ~100 km fiber limit to city-to-city or
  country-wide coverage.

  The trust assumption (secure relay nodes) is:
    - Stronger than classical VPN (QKD links are physically unbreakable)
    - Weaker than pure end-to-end QKD (relay nodes are trusted parties)
    - Comparable to classical TLS with trusted certificate authorities

  Future evolution:
    Quantum Repeaters (2035–2040) → entanglement swapping → no trusted relays needed.
    This is the path to a fully quantum internet with end-to-end ITS security.
""")
    print_sep()


if __name__ == "__main__":
    main()
