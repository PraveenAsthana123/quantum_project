"""
CUSTOMER DEMO PITCH — Quantum Internet Protocol Stack
=====================================================
Wehner, Elkouss & Hanson (Science 2018) proposed a 6-layer quantum internet
stack analogous to the classical TCP/IP stack.  Each layer represents a
progressively more powerful quantum network capability.

The 6 layers:
  1. Trusted Repeater Network (QKD + classical links, no entanglement sharing)
  2. Prepare & Measure Network (BB84-style, no entanglement, limited range)
  3. Entanglement Distribution Network (Bell pair distribution, DIQKD possible)
  4. Quantum Memory Network (long-lived entanglement, teleportation)
  5. Fault-Tolerant Few-Qubit Network (error-corrected qubits, distributed computing)
  6. Quantum Computing Network (full quantum computing + communication)

This demo simulates Layers 1-3 (achievable today or near-term) and provides
conceptual descriptions with protocol tables for Layers 4-6.

Reference: Wehner, Elkouss & Hanson, Science 362, 303 (2018).

Audience: Network architects, telecom operators, government planners.
Runtime: < 10 seconds.
"""

import math
import numpy as np

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_sep(title: str = "") -> None:
    w = 70
    if title:
        p = (w - len(title) - 2) // 2
        print("=" * p + f" {title} " + "=" * (w - p - len(title) - 2))
    else:
        print("=" * w)


def xor_bytes(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


# ---------------------------------------------------------------------------
# Layer 1: Trusted Relay Network
# ---------------------------------------------------------------------------

def simulate_layer1_trusted_relay(n_hops: int = 3, key_bits: int = 256) -> dict:
    """
    Layer 1: Simulate QKD key generation + XOR relay forwarding.
    Each hop establishes a fresh QKD key.
    End-to-end key = XOR chain of all hop keys.
    """
    import hashlib
    hop_keys = []
    hop_names = ["Alice-R1", "R1-R2", "R2-Bob"][:n_hops]
    for name in hop_names:
        key = hashlib.sha256(f"hop:{name}".encode()).digest()[:key_bits//8]
        hop_keys.append((name, key))

    # Build end-to-end key
    k_e2e = hop_keys[0][1]
    for _, k in hop_keys[1:]:
        k_e2e = xor_bytes(k_e2e, k)

    return {
        "layer": 1,
        "name":  "Trusted Relay Network",
        "n_hops": n_hops,
        "hop_keys": [(n, k.hex()[:16]+"...") for n, k in hop_keys],
        "end_to_end_key": k_e2e.hex()[:16] + "...",
        "security": "Classical authenticated channel + QKD per hop",
        "trust_assumption": "Each relay node must be physically secure",
        "quantum_requirement": "QKD hardware per hop only",
    }


# ---------------------------------------------------------------------------
# Layer 2: Prepare and Measure (BB84 style)
# ---------------------------------------------------------------------------

def simulate_layer2_bb84(n_qubits: int = 200, rng: np.random.Generator = None) -> dict:
    """
    Layer 2: BB84 prepare-and-measure protocol.
    No entanglement needed. Alice prepares, Bob measures.
    """
    rng = rng or np.random.default_rng(42)
    alice_bits  = rng.integers(0, 2, n_qubits)
    alice_bases = rng.integers(0, 2, n_qubits)
    bob_bases   = rng.integers(0, 2, n_qubits)

    # Sifting
    sifted_mask = (alice_bases == bob_bases)
    n_sifted    = int(np.sum(sifted_mask))
    alice_key   = alice_bits[sifted_mask]

    return {
        "layer": 2,
        "name":  "Prepare & Measure Network",
        "n_raw": n_qubits,
        "n_sifted": n_sifted,
        "sift_rate": n_sifted / n_qubits,
        "protocol": "BB84",
        "key_preview": "".join(str(b) for b in alice_key[:16]) + "...",
        "quantum_requirement": "Single-photon source or WCP + detectors",
        "entanglement_needed": False,
        "range_km": "~100 (fiber) or ~1200 (satellite)",
        "security": "Information-theoretic (No-Cloning)",
    }


# ---------------------------------------------------------------------------
# Layer 3: Entanglement Distribution
# ---------------------------------------------------------------------------

def simulate_layer3_entanglement(shots: int = 1000) -> dict:
    """
    Layer 3: Distribute Bell pairs between Alice and Bob.
    Demonstrate CHSH violation as evidence of genuine entanglement.
    """
    sim = AerSimulator()

    def correlator(alice_angle: float, bob_angle: float) -> float:
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        qc.ry(-2 * math.radians(alice_angle), 0)
        qc.ry(-2 * math.radians(bob_angle), 1)
        qc.measure_all()
        result = sim.run(qc, shots=shots).result()
        counts = result.get_counts()
        E = sum((+1 if int(k[-1]) == int(k[0]) else -1) * v
                for k, v in counts.items()) / shots
        return E

    E11 = correlator(0, 45)
    E13 = correlator(0, 135)
    E31 = correlator(90, 45)
    E33 = correlator(90, 135)
    S   = E11 - E13 + E31 + E33

    return {
        "layer": 3,
        "name":  "Entanglement Distribution Network",
        "chsh_S": S,
        "classical_limit": 2.0,
        "quantum_limit":   2 * math.sqrt(2),
        "entanglement_verified": abs(S) > 2.0,
        "protocols_enabled": ["E91 QKD", "DIQKD", "Quantum Teleportation (prep)"],
        "quantum_requirement": "Entangled photon pair source + quantum channels",
        "entanglement_needed": True,
        "range_km": "~100 (fiber), ~1200 (satellite)",
    }


# ---------------------------------------------------------------------------
# Layers 4-6: Conceptual descriptions
# ---------------------------------------------------------------------------

UPPER_LAYERS = {
    4: {
        "name": "Quantum Memory Network",
        "status": "Research prototype (2025)",
        "capabilities": [
            "Long-lived quantum memory (milliseconds to seconds)",
            "Entanglement swapping across relay nodes → no trusted relay needed",
            "Quantum teleportation of unknown states",
            "Blind quantum computation (server computes without seeing data)",
        ],
        "protocols": [
            "Entanglement swapping (Bell state measurement at relay)",
            "Quantum teleportation (Bennett et al. 1993)",
            "Quantum error correction (surface codes, 50+ qubits)",
        ],
        "hardware": "Trapped ions, NV centers in diamond, rare-earth-doped crystals",
        "timeline": "2028–2035 for metropolitan-scale deployment",
    },
    5: {
        "name": "Fault-Tolerant Few-Qubit Network",
        "status": "Theoretical (2030+)",
        "capabilities": [
            "Error-corrected logical qubits distributed across nodes",
            "Distributed quantum algorithms (HHL, VQE, QAOA over network)",
            "Verifiable quantum computation",
            "Distributed quantum secret sharing",
        ],
        "protocols": [
            "Distributed surface code error correction",
            "Quantum key agreement (Shor distance ~1000 km)",
            "Distributed Shor algorithm",
        ],
        "hardware": "Modular quantum processors with photonic links",
        "timeline": "2035–2040",
    },
    6: {
        "name": "Quantum Computing Network (Full Quantum Internet)",
        "status": "Long-term vision",
        "capabilities": [
            "Full quantum cryptography (device-independent, ITS)",
            "Distributed quantum computing across continents",
            "Quantum position verification",
            "Perfect quantum coin flipping",
        ],
        "protocols": [
            "Universal quantum network coding",
            "Quantum internet protocol (qIP)",
            "Quantum DNS, quantum routing",
        ],
        "hardware": "Fault-tolerant universal quantum computers + quantum links",
        "timeline": "2045–2060 (speculative)",
    },
}


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    rng = np.random.default_rng(42)

    print_sep("QUANTUM INTERNET PROTOCOL STACK DEMO")
    print("Purpose: Simulate Layers 1-3, describe Layers 4-6 (Wehner et al. 2018)\n")

    # Layer 1
    print_sep("Layer 1: Trusted Relay Network — Simulation")
    l1 = simulate_layer1_trusted_relay(n_hops=3)
    print(f"  Hops:    {l1['n_hops']}")
    for name, key_hex in l1["hop_keys"]:
        print(f"    Link {name}: key = {key_hex}")
    print(f"  End-to-end key: {l1['end_to_end_key']}")
    print(f"  Security: {l1['security']}")
    print(f"  Trust:    {l1['trust_assumption']}")
    print()

    # Layer 2
    print_sep("Layer 2: Prepare & Measure Network (BB84) — Simulation")
    l2 = simulate_layer2_bb84(n_qubits=400, rng=rng)
    print(f"  Protocol:     {l2['protocol']}")
    print(f"  Raw qubits:   {l2['n_raw']}")
    print(f"  Sifted bits:  {l2['n_sifted']}  ({l2['sift_rate']*100:.1f}% sifting rate)")
    print(f"  Key (16b):    {l2['key_preview']}")
    print(f"  Range:        {l2['range_km']}")
    print(f"  Entanglement: {'Required' if l2['entanglement_needed'] else 'Not required'}")
    print()

    # Layer 3
    print_sep("Layer 3: Entanglement Distribution — Simulation")
    l3 = simulate_layer3_entanglement(shots=1000)
    print(f"  Protocol:     Bell pair distribution + CHSH test")
    print(f"  CHSH S value: {l3['chsh_S']:.4f}  "
          f"(classical ≤ {l3['classical_limit']:.1f}, quantum ≤ {l3['quantum_limit']:.3f})")
    verdict = "QUANTUM ENTANGLEMENT VERIFIED ✓" if l3['entanglement_verified'] else \
              "ENTANGLEMENT NOT VERIFIED ✗"
    print(f"  Verdict:      {verdict}")
    print(f"  Enables:      {', '.join(l3['protocols_enabled'])}")
    print(f"  Range:        {l3['range_km']}")
    print()

    # Upper layers
    for layer_num in [4, 5, 6]:
        L = UPPER_LAYERS[layer_num]
        print_sep(f"Layer {layer_num}: {L['name']} — Conceptual")
        print(f"  Status:    {L['status']}")
        print(f"  Timeline:  {L['timeline']}")
        print(f"  Hardware:  {L['hardware']}")
        print(f"  Capabilities:")
        for cap in L["capabilities"]:
            print(f"    - {cap}")
        print(f"  Key Protocols:")
        for proto in L["protocols"]:
            print(f"    - {proto}")
        print()

    # Full stack summary table
    print_sep("Quantum Internet Stack — Summary Table")
    print(f"  {'Layer':>5}  {'Name':<38}  {'Status':<18}  {'Entanglement':>12}  {'Timeline'}")
    print(f"  {'-'*5}  {'-'*38}  {'-'*18}  {'-'*12}  {'-'*20}")
    stack_rows = [
        (1, "Trusted Relay Network",         "Deployed today",  "No",       "2017 (CN backbone)"),
        (2, "Prepare & Measure Network",     "Deployed today",  "No",       "2020s metropolitan"),
        (3, "Entanglement Distribution",     "Lab demonstrated","Yes",      "2025–2030"),
        (4, "Quantum Memory Network",        "Research proto",  "Yes+memory","2028–2035"),
        (5, "Fault-Tolerant Few-Qubit",      "Theoretical",     "Yes+QEC",  "2035–2040"),
        (6, "Quantum Computing Network",     "Long-term vision","Full QC",  "2045–2060"),
    ]
    for num, name, status, ent, timeline in stack_rows:
        print(f"  {num:>5}  {name:<38}  {status:<18}  {ent:>12}  {timeline}")

    print()
    print_sep("Classical vs Quantum Internet Stack Analogy")
    analogy = [
        ("Physical",     "Fiber/RF/optical",    "Photon channels (780/1550 nm)"),
        ("Data link",    "Ethernet frames",     "QKD sifting + error detection"),
        ("Network",      "IP routing",          "Entanglement routing + swapping"),
        ("Transport",    "TCP reliability",     "Quantum error correction"),
        ("Session",      "TLS handshake",       "Quantum key agreement"),
        ("Application",  "HTTP/SMTP/etc.",      "Quantum-secure distributed computing"),
    ]
    print(f"  {'OSI Layer':<15}  {'Classical':<28}  Quantum Analogy")
    print(f"  {'-'*15}  {'-'*28}  {'-'*40}")
    for layer, classical, quantum in analogy:
        print(f"  {layer:<15}  {classical:<28}  {quantum}")

    print()
    print_sep("Key Takeaway")
    print("""
  The quantum internet is a layered architecture — just like the classical internet.
  Layers 1-2 are OPERATIONAL TODAY (China, UK, Korea, USA test networks).
  Layer 3 was demonstrated by Micius satellite (2017) and university labs.
  Layers 4-6 require quantum memory and error correction — active research.

  The path to a quantum internet:
    2024: Metropolitan QKD networks in major cities.
    2027: Cross-city entanglement distribution (EU QCI, US NQIA).
    2030: National quantum backbones with satellite augmentation.
    2035: Quantum repeaters → true end-to-end quantum security.
    2040+: Distributed quantum computing over global network.

  Security significance:
    Each layer adds capabilities beyond what classical crypto can achieve.
    Layer 3+ provides DEVICE-INDEPENDENT security — even your own hardware
    can be untrusted, certified only by quantum correlations.
""")
    print_sep()


if __name__ == "__main__":
    main()
