"""
Blockchain PQC: Stateful Hash-Based Signatures — W-OTS+ and LMS
================================================================
Purpose   : W-OTS+ (Winternitz One-Time Signature+) and Leighton-Micali Signatures
             (LMS) for quantum-safe blockchain key management and cold storage.
Reference  : Hülsing, "W-OTS+ — Shorter Signatures for Hash-Based Signature Schemes"
             AFRICACRYPT 2013; RFC 8554 (LMS/LM-OTS); NIST SP 800-208
Standard  : NIST SP 800-208 (2020); RFC 8554; FIPS 205 (SLH-DSA subsystem)
Security  : EUF-CMA under preimage/collision resistance of SHA-256; 2^(h/2) forgery
             cost under Grover; stateful — leaf reuse breaks security
Quantum Adv: Hash functions are Grover-safe at double parameter size;
             W-OTS+ + Merkle tree → one-time sigs aggregated into many-time key
"""

from __future__ import annotations

import hashlib
import os
import struct
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# W-OTS+ constants (RFC 8554 §3, NIST SP 800-208 §5)
# ─────────────────────────────────────────────────────────────────────────────
n  = 32    # hash output length in bytes (SHA-256 → 32 B)
w  = 16    # Winternitz parameter (base-w digits)

# l1 = ceil(8n / log2(w)) = ceil(256 / 4) = 64
# l2 = floor(log2(l1 * (w-1)) / log2(w)) + 1 = floor(log2(64*15)/4) + 1 = 3
# l  = l1 + l2 = 67
_log2_w = 4          # log2(16) = 4
l1 = (8 * n + _log2_w - 1) // _log2_w   # = 64
l2 = int(np.log2(l1 * (w - 1)) / _log2_w) + 1  # = 3
l  = l1 + l2                              # = 67  (total chain count)


# ─────────────────────────────────────────────────────────────────────────────
# Shared hash primitives (NIST SP 800-208 §4)
# ─────────────────────────────────────────────────────────────────────────────

def _H(x: bytes) -> bytes:
    """Randomized tree hash H(x): SHA-256(x), output n bytes."""
    return hashlib.sha256(x).digest()


def _F(key: bytes, x: bytes) -> bytes:
    """
    W-OTS+ pseudorandom function F: SHA-256(key || x).
    key and x are each n bytes.
    """
    assert len(key) == n and len(x) == n, (
        f"F: expected n={n}-byte inputs, got key={len(key)}, x={len(x)}"
    )
    return hashlib.sha256(key + x).digest()


def _PRF(seed: bytes, addr: bytes) -> bytes:
    """PRF(seed, ADRS): SHA-256(seed || addr), output n bytes."""
    return hashlib.sha256(seed + addr).digest()


def _msg_hash(message: bytes) -> bytes:
    """SHA-256(message) → n bytes."""
    return hashlib.sha256(message).digest()


def _addr_bytes(layer: int = 0, tree: int = 0, ots_idx: int = 0,
                chain_idx: int = 0, hash_idx: int = 0) -> bytes:
    """Pack ADRS (address) structure as 32 bytes per NIST SP 800-208."""
    return struct.pack(">IIIII", layer, tree, ots_idx, chain_idx, hash_idx) + b"\x00" * 12


# ─────────────────────────────────────────────────────────────────────────────
# Base-w message representation
# ─────────────────────────────────────────────────────────────────────────────

def _base_w(msg_bytes: bytes, out_len: int) -> List[int]:
    """
    Convert bytes to base-w representation (RFC 8554 §2.6).

    Parameters
    ----------
    msg_bytes : bytes
        Input bytes (n bytes for message hash, or n+2 for full checksum input).
    out_len : int
        Number of base-w digits to output.

    Returns
    -------
    list of int, each in [0, w-1].
    """
    total_bits = out_len * _log2_w
    # Pad msg_bytes if needed
    needed_bytes = (total_bits + 7) // 8
    data = msg_bytes + b"\x00" * max(0, needed_bytes - len(msg_bytes))

    digits = []
    consumed_bits = 0
    for byte in data:
        for shift in range(8 - _log2_w, -1, -_log2_w):
            if consumed_bits >= total_bits:
                break
            digits.append((byte >> shift) & (w - 1))
            consumed_bits += _log2_w
        if consumed_bits >= total_bits:
            break
    return digits[:out_len]


def _checksum(b: List[int]) -> List[int]:
    """
    Compute Winternitz checksum over base-w message digest (RFC 8554 §3.1).

    C = sum_{i=0}^{l1-1} (w - 1 - b[i])
    Then represent C in base-w with l2 digits (left-padded).
    """
    C = sum(w - 1 - bi for bi in b)
    # Encode C as l2 base-w digits, big-endian
    digits = []
    for _ in range(l2):
        digits.append(C % w)
        C //= w
    return list(reversed(digits))


# ─────────────────────────────────────────────────────────────────────────────
# W-OTS+ class
# ─────────────────────────────────────────────────────────────────────────────

class WOTSPlus:
    """
    W-OTS+ (Winternitz One-Time Signature Plus) implementation.

    Parameters
    ----------
    seed : bytes or None
        32-byte seed for key derivation. Random if None.

    Security note
    -------------
    W-OTS+ is a ONE-TIME signature scheme. Signing two messages with the same
    key completely compromises the secret key. Use LMSSignature (below) to
    aggregate W-OTS+ keys into a stateful many-time scheme.

    Reference
    ---------
    Hülsing, "W-OTS+ — Shorter Signatures for Hash-Based Signature Schemes,"
    AFRICACRYPT 2013; RFC 8554 §3.
    """

    def __init__(self, seed: Optional[bytes] = None):
        self.seed = seed if seed is not None else os.urandom(n)
        assert len(self.seed) == n, f"Seed must be {n} bytes"

    # ── Core chain function ────────────────────────────────────────────────

    def _chain(self, x: bytes, i: int, steps: int, seed: bytes) -> bytes:
        """
        Iterated hash chain: apply F 'steps' times starting at position i.

        chain(x, i, s, SEED) = F(PRF(SEED, ADRS_i+s-1),
                                  chain(x, i, s-1, SEED))

        Parameters
        ----------
        x : bytes
            n-byte input value.
        i : int
            Starting index in the chain (0 ≤ i < w).
        steps : int
            Number of chain steps to apply (i + steps ≤ w).
        seed : bytes
            n-byte randomization seed.

        Returns
        -------
        bytes : n-byte chain output after 'steps' applications.
        """
        if len(x) != n:
            raise ValueError(f"chain: x must be {n} bytes, got {len(x)}")
        if steps == 0:
            return x
        # Apply F iteratively: F(key_j, val_{j-1}) for j = i+1 .. i+steps
        val = x
        for j in range(i, i + steps):
            addr = _addr_bytes(chain_idx=j)
            key  = _PRF(seed, addr)                 # n-byte randomization key
            val  = _F(key, val)                     # n-byte output
        return val

    # ── Key generation ────────────────────────────────────────────────────

    def keygen(self, seed: Optional[bytes] = None) -> Tuple[List[bytes], List[bytes]]:
        """
        Generate W-OTS+ keypair.

        Algorithm (RFC 8554 §3.1.3):
          For i = 0 .. l-1:
            sk[i] = PRF(SEED, ADRS_ots_i)       [n-byte secret chain start]
            pk[i] = chain(sk[i], 0, w-1, SEED)  [end of chain = public key]

        Parameters
        ----------
        seed : bytes or None
            Override instance seed (useful for LMS tree generation).

        Returns
        -------
        (secret_key_list, public_key_list) : each a list of l n-byte values.
        """
        s = seed if seed is not None else self.seed
        secret_key: List[bytes] = []
        public_key: List[bytes] = []

        for i in range(l):
            addr = _addr_bytes(ots_idx=i)
            sk_i = _PRF(s, addr)                     # n-byte secret value
            pk_i = self._chain(sk_i, 0, w - 1, s)   # apply w-1 times
            secret_key.append(sk_i)
            public_key.append(pk_i)

        return secret_key, public_key

    # ── Signing ───────────────────────────────────────────────────────────

    def sign(self, message: bytes,
             secret_key: List[bytes]) -> bytes:
        """
        Sign a message using W-OTS+ (RFC 8554 §3.1.5).

        Algorithm:
          M_hash = SHA-256(message)         [n bytes]
          b      = base_w(M_hash, l1)       [l1 digits in [0, w-1]]
          b     += checksum(b)              [append l2 digits → l digits total]
          sig[i] = chain(sk[i], 0, b[i], SEED)

        Parameters
        ----------
        message : bytes
            Arbitrary-length message.
        secret_key : list of l bytes (each n bytes)
            Secret key from keygen().

        Returns
        -------
        bytes : l × n bytes (67 × 32 = 2144 bytes) signature.
        """
        if len(secret_key) != l:
            raise ValueError(f"secret_key must have {l} elements, got {len(secret_key)}")

        msg_hash_bytes = _msg_hash(message)
        b = _base_w(msg_hash_bytes, l1)           # l1 base-w digits
        b_full = b + _checksum(b)                  # l = l1 + l2 digits

        sig_chains: List[bytes] = []
        for i in range(l):
            # Sign: advance chain by b[i] steps from start
            sig_i = self._chain(secret_key[i], 0, b_full[i], self.seed)
            sig_chains.append(sig_i)

        return b"".join(sig_chains)   # l × n = 2144 bytes

    # ── Verification ──────────────────────────────────────────────────────

    def verify(self, message: bytes,
               signature: bytes,
               public_key: List[bytes]) -> bool:
        """
        Verify a W-OTS+ signature (RFC 8554 §3.1.6).

        Algorithm:
          M_hash = SHA-256(message)
          b      = base_w(M_hash, l1) + checksum(...)
          tmp[i] = chain(sig[i], b[i], w-1-b[i], SEED)
          Accept if tmp[i] == pk[i] for all i

        Parameters
        ----------
        message : bytes
        signature : bytes
            l × n bytes from sign().
        public_key : list of l bytes

        Returns
        -------
        bool : True if valid.
        """
        if len(signature) != l * n:
            return False
        if len(public_key) != l:
            return False

        msg_hash_bytes = _msg_hash(message)
        b = _base_w(msg_hash_bytes, l1)
        b_full = b + _checksum(b)

        # Extract l chains from signature bytes
        sig_chains = [signature[i * n:(i + 1) * n] for i in range(l)]

        for i in range(l):
            # Advance from position b[i] to position w-1 (remaining steps)
            remaining = w - 1 - b_full[i]
            tmp_i = self._chain(sig_chains[i], b_full[i], remaining, self.seed)
            if tmp_i != public_key[i]:
                return False
        return True

    def signature_size(self) -> int:
        """Return signature size in bytes."""
        return l * n   # 67 × 32 = 2144


# ─────────────────────────────────────────────────────────────────────────────
# LMS (Leighton-Micali Signature) class
# ─────────────────────────────────────────────────────────────────────────────

class LMSSignature:
    """
    LMS (Leighton-Micali Signature Scheme) — RFC 8554.

    Aggregates 2^height W-OTS+ keypairs into a Merkle tree. The root hash
    is the public key. Each leaf is the hash of one W-OTS+ public key.
    State: leaf_idx tracks the next unused OTS key (MUST NOT reuse).

    Parameters
    ----------
    height : int
        Merkle tree height. Total signing capacity = 2^height messages.
        height=10 → 1024 signatures. height=20 → ~1M signatures.

    Security
    --------
    Forgery requires breaking SHA-256 preimage. Grover halves bit-security:
    at n=32 bytes SHA-256, quantum security ≈ 128 bits (Grover on SHA-256).

    Reference
    ---------
    McGrew & Curcio, RFC 8554 "Leighton-Micali Hash-Based Signatures" (2019).
    NIST SP 800-208 §5.
    """

    def __init__(self, height: int = 10):
        self.height  = height
        self.n_leaves = 1 << height   # 2^height OTS keys
        self._wots   = WOTSPlus()     # shared W-OTS+ instance
        self._leaves: List[bytes] = []        # leaf hashes (built during keygen)
        self._sk_list: List[List[bytes]] = [] # W-OTS+ secret keys per leaf
        self._pk_list: List[List[bytes]] = [] # W-OTS+ public keys per leaf
        self._tree:   List[List[bytes]] = []  # internal nodes per level
        self._root:   Optional[bytes]   = None
        self._leaf_idx: int = 0

    # ── Key generation ────────────────────────────────────────────────────

    def keygen(self, master_seed: Optional[bytes] = None) -> Tuple[bytes, Dict]:
        """
        Generate LMS keypair (RFC 8554 §5.3).

        Algorithm:
          For each leaf i = 0 .. 2^h - 1:
            seed_i = PRF(master_seed, i || "leaf")
            (sk_i, pk_i) = WOTS+.keygen(seed_i)
            leaf_hash[i] = H("OTS" || pk_i[0] || ... || pk_i[l-1])
          Build Merkle tree bottom-up; root = T[height][0]

        Parameters
        ----------
        master_seed : bytes or None
            32-byte master seed. Random if None.

        Returns
        -------
        (root_hash, state_dict)
            root_hash : 32-byte Merkle root (= LMS public key)
            state_dict : mutable state (leaf_idx, sk_list, pk_list, tree)
        """
        master_seed = master_seed or os.urandom(n)

        sk_all:   List[List[bytes]] = []
        pk_all:   List[List[bytes]] = []
        seed_all: List[bytes]       = []
        leaves:   List[bytes]       = []

        for i in range(self.n_leaves):
            # Derive per-leaf seed (deterministic; stored in state for sign/verify)
            leaf_seed = _PRF(master_seed, struct.pack(">I", i) + b"leaf" + b"\x00" * 24)
            wots_i = WOTSPlus(seed=leaf_seed)
            sk_i, pk_i = wots_i.keygen()

            # Leaf hash = H("LMS_LEAF" || i || pk_i concatenated)
            pk_bytes_i = b"".join(pk_i)
            leaf_hash  = _H(b"LMS_LEAF" + struct.pack(">I", i) + pk_bytes_i)

            sk_all.append(sk_i)
            pk_all.append(pk_i)
            seed_all.append(leaf_seed)
            leaves.append(leaf_hash)

        # Build Merkle tree: tree[0] = leaves, tree[h] = [root]
        tree: List[List[bytes]] = [leaves[:]]
        current = leaves[:]
        for lvl in range(1, self.height + 1):
            parent = []
            for j in range(0, len(current), 2):
                left  = current[j]
                right = current[j + 1] if j + 1 < len(current) else current[j]
                node  = _H(b"LMS_NODE" + struct.pack(">II", lvl, j // 2) + left + right)
                parent.append(node)
            tree.append(parent)
            current = parent

        root_hash = current[0]

        # Store state
        self._sk_list  = sk_all
        self._pk_list  = pk_all
        self._leaves   = leaves
        self._tree     = tree
        self._root     = root_hash
        self._leaf_idx = 0

        self._seed_list = seed_all

        state_dict = {
            "leaf_idx":   self._leaf_idx,
            "sk_list":    self._sk_list,
            "pk_list":    self._pk_list,
            "seed_list":  seed_all,      # per-leaf W-OTS+ seeds for sign/verify
            "tree":       self._tree,
            "height":     self.height,
            "n_leaves":   self.n_leaves,
            "capacity":   self.n_leaves - self._leaf_idx,
        }
        return root_hash, state_dict

    # ── Signing ───────────────────────────────────────────────────────────

    def sign(self, message: bytes,
             state: Dict) -> Tuple[int, bytes, List[bytes]]:
        """
        Sign a message using the next unused OTS leaf (RFC 8554 §5.4).

        Algorithm:
          q = state["leaf_idx"]   (current leaf index)
          sig_wots = WOTS+.sign(message, sk[q])
          auth_path = Merkle authentication path from leaf q to root
          state["leaf_idx"] += 1
          return (q, sig_wots, auth_path)

        Parameters
        ----------
        message : bytes
        state : dict
            Mutable state from keygen() — leaf_idx is incremented in-place.

        Returns
        -------
        (leaf_idx, wots_sig, auth_path)
            leaf_idx  : int, index of the leaf used
            wots_sig  : bytes, W-OTS+ signature (l × n = 2144 bytes)
            auth_path : list of h n-byte sibling hashes (Merkle proof)

        Raises
        ------
        RuntimeError if all OTS keys have been used (key exhausted).
        """
        q = state["leaf_idx"]
        if q >= self.n_leaves:
            raise RuntimeError(
                f"LMS key exhausted: all {self.n_leaves} OTS leaves used. "
                "Generate a new LMS keypair."
            )

        # Get per-leaf secret key and the leaf-specific W-OTS+ seed from state
        sk_q      = state["sk_list"][q]
        leaf_seed = state["seed_list"][q]   # exact seed used during keygen

        wots_signer = WOTSPlus(seed=leaf_seed)
        wots_sig = wots_signer.sign(message, sk_q)

        # Build Merkle authentication path
        auth_path: List[bytes] = []
        tree = state["tree"]
        node_idx = q
        for lvl in range(self.height):
            # Sibling node at level lvl
            sibling_idx = node_idx ^ 1   # XOR with 1 flips last bit
            level_nodes = tree[lvl]
            if sibling_idx < len(level_nodes):
                auth_path.append(level_nodes[sibling_idx])
            else:
                # Odd number of nodes — duplicate last
                auth_path.append(level_nodes[-1])
            node_idx //= 2   # go up one level

        state["leaf_idx"] = q + 1
        state["capacity"] = self.n_leaves - state["leaf_idx"]

        # Include leaf_seed in signature tuple so verifier can reconstruct chains
        return q, wots_sig, auth_path, leaf_seed

    # ── Verification ──────────────────────────────────────────────────────

    def verify(self, message: bytes,
               signature: Tuple,
               root_hash: bytes) -> bool:
        """
        Verify an LMS signature (RFC 8554 §5.5).

        Algorithm:
          (q, sig_wots, auth_path, leaf_seed) = signature
          Recompute W-OTS+ public key pk_candidate from sig_wots using leaf_seed
          leaf_hash = H("LMS_LEAF" || q || pk_candidate)
          Reconstruct root from leaf_hash + auth_path
          Accept if reconstructed_root == root_hash

        Parameters
        ----------
        message : bytes
        signature : (leaf_idx, wots_sig, auth_path, leaf_seed)
            leaf_seed is the per-leaf W-OTS+ seed (included in sig for verifier).
        root_hash : bytes (n bytes)

        Returns
        -------
        bool
        """
        if len(signature) not in (3, 4):
            return False

        if len(signature) == 4:
            q, wots_sig, auth_path, leaf_seed = signature
        else:
            q, wots_sig, auth_path = signature
            leaf_seed = None

        if len(auth_path) != self.height:
            return False
        if len(wots_sig) != l * n:
            return False

        # Reconstruct W-OTS+ public key from signature using the correct leaf seed
        msg_hash_bytes = _msg_hash(message)
        b = _base_w(msg_hash_bytes, l1)
        b_full = b + _checksum(b)

        sig_chains = [wots_sig[i * n:(i + 1) * n] for i in range(l)]

        # Use the leaf-specific seed from the signature tuple (same as used in sign)
        if leaf_seed is None:
            leaf_seed = sig_chains[0][:n]   # fallback proxy (less accurate)

        wots_ver = WOTSPlus(seed=leaf_seed)

        pk_candidate: List[bytes] = []
        for i in range(l):
            remaining = w - 1 - b_full[i]
            pk_i = wots_ver._chain(sig_chains[i], b_full[i], remaining, leaf_seed)
            pk_candidate.append(pk_i)

        # Compute candidate leaf hash
        pk_bytes = b"".join(pk_candidate)
        candidate_leaf = _H(b"LMS_LEAF" + struct.pack(">I", q) + pk_bytes)

        # Walk Merkle path from leaf to root.
        # Must use same level index convention as keygen (lvl 1-based from leaf).
        node = candidate_leaf
        node_idx = q
        for step, sibling in enumerate(auth_path):
            tree_level = step + 1       # keygen stores level as 1..height
            lvl_idx    = node_idx // 2
            if node_idx % 2 == 0:      # current node is left child
                parent = _H(b"LMS_NODE"
                            + struct.pack(">II", tree_level, lvl_idx)
                            + node + sibling)
            else:                      # current node is right child
                parent = _H(b"LMS_NODE"
                            + struct.pack(">II", tree_level, lvl_idx)
                            + sibling + node)
            node = parent
            node_idx //= 2

        return node == root_hash

    # ── State management ──────────────────────────────────────────────────

    def remaining_capacity(self, state: Dict) -> int:
        """Return number of remaining signing operations."""
        return self.n_leaves - state["leaf_idx"]

    def is_exhausted(self, state: Dict) -> bool:
        """True if all OTS keys have been consumed."""
        return state["leaf_idx"] >= self.n_leaves

    def signature_size(self) -> int:
        """Return total signature size in bytes."""
        # leaf_idx (4) + wots_sig (l×n) + auth_path (h × n)
        return 4 + l * n + self.height * n


# ─────────────────────────────────────────────────────────────────────────────
# Standalone demo
# ─────────────────────────────────────────────────────────────────────────────

def run_demo() -> Dict[str, Any]:
    results: Dict[str, Any] = {}

    # ── W-OTS+ demo ─────────────────────────────────────────────────────
    seed_bytes = hashlib.sha256(b"wots-demo-seed-0000001").digest()
    wots = WOTSPlus(seed=seed_bytes)

    t0 = time.perf_counter()
    sk, pk = wots.keygen()
    keygen_ms = (time.perf_counter() - t0) * 1000

    msg = b"Quantum-safe transaction: Alice to Bob 0.5 BTC at block 900000"

    t1 = time.perf_counter()
    sig = wots.sign(msg, sk)
    sign_ms = (time.perf_counter() - t1) * 1000

    t2 = time.perf_counter()
    valid = wots.verify(msg, sig, pk)
    verify_ms = (time.perf_counter() - t2) * 1000

    tampered = wots.verify(b"tampered_message", sig, pk)

    results["wots_plus"] = {
        "l_chains":           l,
        "n_bytes":            n,
        "w_parameter":        w,
        "sig_size_bytes":     len(sig),
        "keygen_ms":          round(keygen_ms, 2),
        "sign_ms":            round(sign_ms, 2),
        "verify_ms":          round(verify_ms, 2),
        "valid":              valid,
        "tampered_rejected":  not tampered,
    }

    # ── LMS demo (height=4 for speed; production uses height=10-20) ──────
    lms = LMSSignature(height=4)   # 2^4 = 16 leaves

    t3 = time.perf_counter()
    root, state = lms.keygen(
        master_seed=hashlib.sha256(b"lms-master-seed-001").digest()
    )
    lms_keygen_ms = (time.perf_counter() - t3) * 1000

    t4 = time.perf_counter()
    sig_lms = lms.sign(msg, state)
    lms_sign_ms = (time.perf_counter() - t4) * 1000

    t5 = time.perf_counter()
    lms_valid = lms.verify(msg, sig_lms, root)
    lms_verify_ms = (time.perf_counter() - t5) * 1000

    # Second signature (different leaf)
    msg2 = b"Second quantum-safe transaction: Bob to Carol 0.1 ETH"
    sig_lms2 = lms.sign(msg2, state)
    lms_valid2 = lms.verify(msg2, sig_lms2, root)

    results["lms"] = {
        "height":             lms.height,
        "n_leaves":           lms.n_leaves,
        "sig_size_bytes":     lms.signature_size(),
        "keygen_ms":          round(lms_keygen_ms, 2),
        "sign_ms":            round(lms_sign_ms, 2),
        "verify_ms":          round(lms_verify_ms, 2),
        "valid_msg1":         lms_valid,
        "valid_msg2":         lms_valid2,
        "remaining_capacity": lms.remaining_capacity(state),
        "leaf_idx_after_2":   state["leaf_idx"],
    }

    results["security_properties"] = {
        "hash_function":    "SHA-256 (n=32 bytes)",
        "classical_bits":   256,   # SHA-256 preimage
        "quantum_bits":     128,   # Grover halves to 128-bit
        "one_time_only":    True,
        "stateful":         True,
        "nist_standard":    "SP 800-208 / RFC 8554",
        "quantum_safe":     True,
    }

    results["status"] = "PASS" if (valid and lms_valid and lms_valid2) else "PARTIAL"
    return results


if __name__ == "__main__":
    out = run_demo()
    print("\n" + "=" * 70)
    print("Hash-Chain Signature Demo — W-OTS+ and LMS")
    print("=" * 70)
    for section, data in out.items():
        if isinstance(data, dict):
            print(f"\n  [{section}]")
            for k, v in data.items():
                print(f"    {k:<40} {v}")
        else:
            print(f"  {section:<44} {data}")
    print()
    print(f"  W-OTS+ sig size:  {l * n} bytes ({l} chains × {n} bytes each)")
    print(f"  LMS sig size:     4 + {l * n} + height × {n} bytes")
    print("=" * 70)
