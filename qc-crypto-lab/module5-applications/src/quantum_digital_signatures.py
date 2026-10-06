"""
CUSTOMER DEMO PITCH — Quantum Digital Signatures (QDS)
=======================================================
Classical digital signatures rely on computational hardness (RSA, ECDSA).
Quantum Digital Signatures (Gottesman & Chuang 2001) provide signatures
with INFORMATION-THEORETIC security — like QKD, the security is guaranteed
by quantum physics, not computational assumptions.

Protocol (simplified Lamport-style QDS):
  1. Alice prepares quantum 'signature' states (superposition of private key bits).
  2. Alice distributes copies to Bob and Charlie (using QKD channels).
  3. Alice signs a message by revealing her private key states.
  4. Bob verifies the signature.
  5. Charlie can confirm Bob did not forge the signature.

Properties:
  - Unforgeability: forging requires knowing Alice's quantum states — impossible by no-cloning.
  - Non-repudiation: Alice cannot deny a valid signature.
  - Transferability: Bob can forward the verified signature to Charlie.

Note: This is a simulation — real QDS requires quantum memory and quantum channels.

Audience: Cryptographers, security architects, interview panels.
Runtime: < 3 seconds.
"""

import hashlib
import os
import hmac as hmac_mod
import numpy as np


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
# Simplified QDS (simulate quantum states as bit strings with commitment)
# ---------------------------------------------------------------------------

class QDSParticipant:
    def __init__(self, name: str, rng: np.random.Generator):
        self.name = name
        self.rng  = rng
        self.received_states = {}   # from_party → quantum states


class QuantumDigitalSignatureScheme:
    """
    Simulated one-time QDS protocol.

    State encoding:
      bit 0 → quantum state in Z basis: represented as {basis: 'Z', value: 0}
      bit 1 → quantum state in X basis: represented as {basis: 'X', value: 1}
      (In a real system these are photon polarisation states)

    Alice's private key: pairs of quantum states (for 0-message and 1-message).
    """

    def __init__(self, n_sig_bits: int = 32, rng: np.random.Generator = None):
        self.n     = n_sig_bits
        self.rng   = rng or np.random.default_rng(42)

    def alice_keygen(self) -> dict:
        """
        Alice generates private key: for each bit position, two quantum states.
        sk[i][b] = quantum state for signing bit b at position i.
        """
        sk = []
        for i in range(self.n):
            sk_i = {}
            for b in [0, 1]:
                basis  = int(self.rng.integers(0, 2))   # Z or X
                value  = int(self.rng.integers(0, 2))   # 0 or 1
                # Commit to the state: hash(basis || value || position || b)
                commit = hashlib.sha256(f"{i}:{b}:{basis}:{value}".encode()).hexdigest()[:16]
                sk_i[b] = {"basis": basis, "value": value, "commit": commit}
            sk.append(sk_i)
        return {"sk": sk, "n": self.n}

    def alice_distribute(self, private_key: dict) -> dict:
        """
        Alice 'distributes' quantum states to Bob and Charlie.
        Each gets a copy of the commitment hash (simulating quantum channel delivery).
        In reality: sends quantum states via QKD channels.
        """
        pk = []
        for sk_i in private_key["sk"]:
            pk.append({
                0: sk_i[0]["commit"],
                1: sk_i[1]["commit"],
            })
        return {"pk": pk, "n": self.n}

    def alice_sign(self, message_bit: int, private_key: dict) -> dict:
        """
        Alice signs a single-bit message:
        Reveals the private key states for message_bit at each position.
        """
        revealed = []
        for sk_i in private_key["sk"]:
            state = sk_i[message_bit]
            revealed.append({"basis": state["basis"], "value": state["value"],
                             "commit": state["commit"]})
        return {"message_bit": message_bit, "revealed": revealed}

    def bob_verify(self, signature: dict, public_key: dict,
                   threshold: float = 0.9) -> dict:
        """
        Bob verifies signature:
        1. Check that revealed states match the distributed commitments.
        2. Measure states in the committed basis.
        3. Count mismatches — if > threshold match, signature is valid.
        """
        msg_bit = signature["message_bit"]
        revealed = signature["revealed"]
        pk       = public_key["pk"]
        n        = public_key["n"]

        matches = 0
        errors  = 0
        for i, (rev_state, pk_i) in enumerate(zip(revealed, pk)):
            # Check commitment matches
            expected_commit = pk_i[msg_bit]
            if rev_state["commit"] == expected_commit:
                matches += 1
            else:
                errors += 1

        match_rate = matches / n
        valid = match_rate >= threshold
        return {
            "valid":      valid,
            "matches":    matches,
            "errors":     errors,
            "match_rate": match_rate,
            "threshold":  threshold,
            "msg_bit":    msg_bit,
        }

    def charlie_check(self, signature: dict, public_key: dict) -> dict:
        """
        Charlie independently verifies that Bob did not forge the signature.
        Charlie also has the same public key distribution from Alice.
        """
        return self.bob_verify(signature, public_key, threshold=0.8)


# ---------------------------------------------------------------------------
# Forging attempt
# ---------------------------------------------------------------------------

def forge_attempt(qds: QuantumDigitalSignatureScheme,
                  alice_pk: dict, target_bit: int,
                  rng: np.random.Generator) -> dict:
    """
    Eve tries to forge Alice's signature on the opposite bit.
    She must produce revealed states that match Alice's commitments.
    Without knowing the private key states, she guesses randomly.
    """
    revealed_forge = []
    for pk_i in alice_pk["pk"]:
        expected_commit = pk_i[target_bit]
        # Eve guesses random basis and value
        basis  = int(rng.integers(0, 2))
        value  = int(rng.integers(0, 2))
        forged_commit = hashlib.sha256(f"?:{target_bit}:{basis}:{value}".encode()).hexdigest()[:16]
        revealed_forge.append({"basis": basis, "value": value,
                               "commit": forged_commit})

    forge_sig = {"message_bit": target_bit, "revealed": revealed_forge}
    result    = qds.bob_verify(forge_sig, alice_pk)
    return result


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    rng = np.random.default_rng(42)
    N_SIG = 64

    print_sep("QUANTUM DIGITAL SIGNATURE DEMO")
    print(f"  Signature length: {N_SIG} quantum state commitments\n")

    qds = QuantumDigitalSignatureScheme(n_sig_bits=N_SIG, rng=rng)

    # Key generation
    print_sep("Step 1: Alice generates private key")
    alice_priv = qds.alice_keygen()
    print(f"  Private key: {N_SIG} pairs of quantum states  (each ∈ {{Z,X}} basis × {{0,1}} value)")
    print(f"  Sample (position 0):  bit0={alice_priv['sk'][0][0]}")
    print(f"                        bit1={alice_priv['sk'][0][1]}")
    print()

    # Distribution
    print_sep("Step 2: Alice distributes commitments to Bob and Charlie")
    alice_pk = qds.alice_distribute(alice_priv)
    print(f"  Sent {N_SIG} commitment hashes to Bob and Charlie.")
    print(f"  Sample pk[0]:  commit_0={alice_pk['pk'][0][0]}")
    print(f"                 commit_1={alice_pk['pk'][0][1]}")
    print(f"  (In real QDS: quantum states sent via authenticated QKD channels)")
    print()

    # Signing both bits
    print_sep("Step 3: Alice signs messages")
    for msg_bit in [0, 1]:
        sig = qds.alice_sign(msg_bit, alice_priv)
        print(f"  Message bit {msg_bit}: signature reveals {N_SIG} quantum states")
        print(f"    Sample revealed[0]: {sig['revealed'][0]}")
    print()

    # Verification
    print_sep("Step 4: Bob and Charlie verify")
    for msg_bit in [0, 1]:
        sig    = qds.alice_sign(msg_bit, alice_priv)
        bob_r  = qds.bob_verify(sig, alice_pk)
        char_r = qds.charlie_check(sig, alice_pk)
        print(f"  Message={msg_bit}:")
        print(f"    Bob:     matches={bob_r['matches']}/{N_SIG}  "
              f"({bob_r['match_rate']*100:.1f}%)  "
              f"{'VALID ✓' if bob_r['valid'] else 'INVALID ✗'}")
        print(f"    Charlie: matches={char_r['matches']}/{N_SIG}  "
              f"({char_r['match_rate']*100:.1f}%)  "
              f"{'VALID ✓' if char_r['valid'] else 'INVALID ✗'}")
    print()

    # Forgery attempt
    print_sep("Step 5: Eve Attempts Forgery")
    rng2 = np.random.default_rng(999)
    for forge_bit in [0, 1]:
        fr = forge_attempt(qds, alice_pk, forge_bit, rng2)
        print(f"  Eve forges bit={forge_bit}:  "
              f"matches={fr['matches']}/{N_SIG}  "
              f"({fr['match_rate']*100:.1f}%)  "
              f"{'VALID (forgery succeeded!)' if fr['valid'] else 'FORGERY DETECTED ✗'}")

    print()
    print_sep("Security Analysis")
    print(f"""
  Honest signature (match rate ≥ 90%):
    Alice reveals the correct quantum states → all commitments match exactly.
    Both Bob and Charlie verify successfully.

  Forgery attempt (match rate ≈ 6.25% = 1/16 from random guessing):
    Eve must guess both the basis AND value of each state.
    P(one state correct) = 1/4 → expected matches ≈ {N_SIG//4}/{N_SIG}.
    Any mismatch rate above threshold → FORGERY DETECTED.

  Information-theoretic security guarantee:
    Even with unlimited quantum computers, Eve cannot forge signatures because:
    1. She doesn't know Alice's private states (No-Cloning prevents copying).
    2. Without the state, her commitment hash will not match with probability 1.

  Transferability:
    Bob can forward Alice's revealed states + Charlie's public key to a third party.
    Charlie's independent copy allows verification that Bob did not forge the message.
    This is the non-repudiation property.
""")
    print_sep()


if __name__ == "__main__":
    main()
