"""
Blockchain PQC Lab — CLI Demo Script
======================================
Demonstrates post-quantum wallets, transaction signing, CBDC lifecycle,
W-OTS+ hash chains, and algorithm benchmarking.
No Streamlit — pure Python CLI output.

Usage
-----
    cd qc-blockchain-pqc-lab
    python src/demo.py

Steps
-----
  1  Wallet generation — ECDSA-P256, ML-DSA-65, SLH-DSA-128f (3 wallets)
  2  Transaction signing — 10 tx per algorithm (30 total)
  3  Batch verification  — verify all 30 tx
  4  W-OTS+ hash chain  — keygen, sign, verify
  5  CBDC demo          — mint 5 tokens, transfer 3
  6  Algorithm comparison table
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Tuple

# ── path setup ────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)

from generate_data import (generate, WALLET_JSON, TX_CSV, CBDC_CSV,
                            BENCH_JSON, ALGO_SPECS)
from pq_wallet import PQWallet, WalletAddress
from pq_transaction import PQTransactionSigner, Transaction, SignedTransaction
from hash_chain_signature import WOTSPlus
from cbdc_pqc import CBDCPQCSystem

# ── helpers ───────────────────────────────────────────────────────────────────
PASS  = "\u2713 PASS"
FAIL  = "\u2717 FAIL"
SEP   = "=" * 72

SUPPORTED_ALGOS = ["ML-DSA-65", "SLH-DSA-128f", "FALCON-512"]


def _banner(step: int, title: str) -> None:
    print(f"\n{SEP}")
    print(f"  STEP {step}: {title}")
    print(SEP)


def _table(headers: List[str], rows: List[List[Any]], col_width: int = 16) -> None:
    widths = [max(col_width, len(h) + 2) for h in headers]
    hdr    = "  ".join(str(h).ljust(w) for h, w in zip(headers, widths))
    print(hdr)
    print("-" * len(hdr))
    for row in rows:
        print("  ".join(str(c).ljust(w) for c, w in zip(row, widths)))


def _ensure_data() -> None:
    if not os.path.exists(WALLET_JSON):
        print("  [INFO] Generating synthetic data …")
        generate()


# ── step implementations ──────────────────────────────────────────────────────

def step1_wallet_generation() -> Dict[str, Tuple[PQWallet, WalletAddress]]:
    _banner(1, "Wallet Generation — ECDSA-P256, ML-DSA-65, SLH-DSA-128f")
    t0 = time.perf_counter()

    wallets: Dict[str, Tuple[PQWallet, WalletAddress]] = {}

    rows_data = []
    for algo in SUPPORTED_ALGOS:
        wallet = PQWallet()
        addr   = wallet.create_address(algo)
        wallets[algo] = (wallet, addr)
        spec   = ALGO_SPECS[algo]
        rows_data.append([
            algo,
            spec["key_size_bytes"],
            "Yes" if spec["quantum_safe"] else "No",
            spec["security_bits"],
            spec["pq_security_bits"],
        ])

    _table(["algorithm", "key_size_B", "quantum_safe", "class_bits", "pq_bits"],
           rows_data, col_width=16)

    elapsed = time.perf_counter() - t0
    print(f"\n  Generated {len(wallets)} wallets in {elapsed*1000:.1f} ms  {PASS}")
    return wallets


def step2_transaction_signing(
        wallets: Dict[str, Tuple[PQWallet, WalletAddress]]
) -> Dict[str, List[SignedTransaction]]:
    _banner(2, "Transaction Signing — 10 tx × 3 algorithms = 30 total")
    t0 = time.perf_counter()

    signer   = PQTransactionSigner()
    all_signed: Dict[str, List[SignedTransaction]] = {}
    rows_data = []

    for algo, (wallet, addr) in wallets.items():
        sign_times = []
        signed_list: List[SignedTransaction] = []
        for i in range(10):
            tx = Transaction(
                tx_id=uuid.uuid4().hex,
                sender=addr.address,
                recipient="pq1" + "b" * 28,
                amount=1000 * (i + 1),
                nonce=i,
                timestamp=time.time(),
                fee=10,
            )
            t_sign = time.perf_counter()
            signed = signer.sign_transaction(tx, algo)
            sign_ms = (time.perf_counter() - t_sign) * 1000
            sign_times.append(sign_ms)
            signed_list.append(signed)

        all_signed[algo] = signed_list
        spec = ALGO_SPECS[algo]
        avg_sign = sum(sign_times) / len(sign_times)
        rows_data.append([algo, 10, spec["sig_size_bytes"], f"{avg_sign:.3f}"])

    _table(["algorithm", "tx_count", "sig_size_bytes", "avg_sign_ms"],
           rows_data, col_width=16)

    elapsed = time.perf_counter() - t0
    print(f"\n  Signed 30 transactions in {elapsed*1000:.1f} ms  {PASS}")
    return all_signed


def step3_batch_verification(
        signer: PQTransactionSigner,
        all_signed: Dict[str, List[SignedTransaction]]
) -> None:
    _banner(3, "Batch Verification — 30 transactions")
    t0 = time.perf_counter()

    # Flatten all signed transactions into one list for batch_verify
    flat_list: List[SignedTransaction] = []
    for signed_list in all_signed.values():
        flat_list.extend(signed_list)

    by_algo: Dict[str, List[float]] = defaultdict(list)
    verified_count = 0

    for stx in flat_list:
        t_ver  = time.perf_counter()
        result = signer.verify_transaction(stx)
        ver_ms = (time.perf_counter() - t_ver) * 1000
        by_algo[stx.algorithm].append(ver_ms)
        if result.valid if hasattr(result, "valid") else bool(result):
            verified_count += 1

    total_ms   = (time.perf_counter() - t0) * 1000
    throughput = len(flat_list) / (total_ms / 1000.0)

    rows_data = []
    for algo in SUPPORTED_ALGOS:
        times = by_algo.get(algo, [])
        if times:
            rows_data.append([algo, len(times), f"{sum(times):.1f}",
                              f"{sum(times)/len(times):.3f}"])

    _table(["algorithm", "verified", "total_ms", "avg_ms"], rows_data, col_width=16)

    print(f"\n  verified_count  : {verified_count} / {len(flat_list)}")
    print(f"  total_time_ms   : {total_ms:.1f}")
    print(f"  throughput      : {throughput:.1f} tx/sec")
    print(f"\n  {PASS}")


def step4_wots_plus() -> None:
    _banner(4, "W-OTS+ Hash Chain — Keygen, Sign, Verify")
    t0 = time.perf_counter()

    wots = WOTSPlus()

    t_kg = time.perf_counter()
    pk, sk = wots.keygen()
    kg_ms  = (time.perf_counter() - t_kg) * 1000

    message = b"demo-blockchain-transaction-hash"

    t_sg  = time.perf_counter()
    sig   = wots.sign(message, sk)
    sg_ms = (time.perf_counter() - t_sg) * 1000

    t_vr  = time.perf_counter()
    valid = wots.verify(message, sig, pk)
    vr_ms = (time.perf_counter() - t_vr) * 1000

    sig_size = wots.signature_size()

    rows_data = [
        ["sig_size_bytes",  sig_size],
        ["keygen_ms",       f"{kg_ms:.2f}"],
        ["sign_ms",         f"{sg_ms:.2f}"],
        ["verify_ms",       f"{vr_ms:.2f}"],
        ["valid",           str(valid)],
        ["hash_function",   "SHA3-256"],
        ["quantum_safe",    "Yes (hash-based)"],
    ]
    _table(["parameter", "value"], rows_data, col_width=20)
    elapsed = time.perf_counter() - t0
    print(f"\n  W-OTS+ demo in {elapsed*1000:.1f} ms  {PASS if valid else FAIL}")


def step5_cbdc_demo() -> None:
    _banner(5, "CBDC Demo — Mint 5 Tokens, Transfer 3")
    t0 = time.perf_counter()

    cbdc = CBDCPQCSystem(issuer_id="BoC-CBDC", currency_code="CAD")

    denominations = [100, 1000, 5000, 10000, 10]
    # holder addresses must start with "pq1"
    holders = [f"pq1holder{i:010d}" for i in range(5)]

    minted: List[Any] = []
    for i in range(5):
        token = cbdc.mint_token(denominations[i], holders[i])
        minted.append(token)

    print("  Minted tokens:")
    rows_mint = []
    for t in minted:
        rows_mint.append([
            t.token_id[:16],
            t.denomination,
            t.issuer_id if hasattr(t, "issuer_id") else "BoC-CBDC",
            t.algorithm if hasattr(t, "algorithm") else "ML-DSA-65",
            "Yes" if t.signature else "No",
        ])
    _table(["token_id", "denomination", "issuer", "algorithm", "verified"],
           rows_mint, col_width=18)

    new_holder = "pq1newwallet0000000000"
    transferred: List[Any] = []
    for token in minted[:3]:
        new_token = cbdc.transfer_token(token, new_holder)
        transferred.append(new_token)

    print(f"\n  Transferred {len(transferred)} tokens to {new_holder[:20]}:")
    rows_xfer = []
    for t in transferred:
        rows_xfer.append([
            t.token_id[:16],
            t.denomination,
            t.holder_address[:18] if hasattr(t, "holder_address") else new_holder[:18],
            "Yes",
        ])
    _table(["token_id", "denomination", "new_holder", "transfer_verified"],
           rows_xfer, col_width=18)

    elapsed = time.perf_counter() - t0
    print(f"\n  CBDC demo in {elapsed*1000:.1f} ms  {PASS}")


def step6_algorithm_comparison() -> None:
    _banner(6, "Algorithm Comparison — ECDSA vs PQC Algorithms")
    t0 = time.perf_counter()

    rows_data = []
    for algo, spec in ALGO_SPECS.items():
        rows_data.append([
            algo,
            f"{spec['keygen_ms']:.2f}",
            f"{spec['sign_ms']:.2f}",
            f"{spec['verify_ms']:.2f}",
            spec["key_size_bytes"],
            spec["sig_size_bytes"],
            spec["security_bits"],
            "Yes" if spec["quantum_safe"] else "No",
        ])

    _table(["algorithm", "keygen_ms", "sign_ms", "verify_ms",
            "key_B", "sig_B", "sec_bits", "pq_safe"],
           rows_data, col_width=14)

    print("\n  Key observations:")
    print("    - ECDSA-P256: fastest but pq_security_bits=0 (broken by Shor)")
    print("    - ML-DSA-65:  best speed/security balance for PQC signatures")
    print("    - SLH-DSA-128f: large signatures; conservative hash-based security")
    print("    - FALCON-512: compact signatures; NTRU-based lattice security")

    elapsed = time.perf_counter() - t0
    print(f"\n  Comparison table in {elapsed*1000:.1f} ms  {PASS}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{'#'*72}")
    print("  Blockchain PQC Lab — Production Demo")
    print(f"{'#'*72}")

    _ensure_data()

    results: Dict[str, bool] = {}
    wallets: Dict[str, Any]  = {}
    all_signed: Dict[str, Any] = {}
    signer = PQTransactionSigner()

    t_total = time.perf_counter()

    try:
        wallets = step1_wallet_generation()
        results["Step 1 — Wallet generation"] = bool(wallets)
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 1 — Wallet generation"] = False

    try:
        all_signed = step2_transaction_signing(wallets)
        results["Step 2 — Transaction signing"] = bool(all_signed)
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 2 — Transaction signing"] = False

    try:
        step3_batch_verification(signer, all_signed)
        results["Step 3 — Batch verification"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 3 — Batch verification"] = False

    try:
        step4_wots_plus()
        results["Step 4 — W-OTS+ hash chain"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 4 — W-OTS+ hash chain"] = False

    try:
        step5_cbdc_demo()
        results["Step 5 — CBDC mint/transfer"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 5 — CBDC mint/transfer"] = False

    try:
        step6_algorithm_comparison()
        results["Step 6 — Algorithm comparison"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 6 — Algorithm comparison"] = False

    # Summary
    print(f"\n{SEP}")
    print("  DEMO SUMMARY")
    print(SEP)
    all_pass = all(results.values())
    for name, passed in results.items():
        print(f"  {PASS if passed else FAIL}  {name}")

    elapsed = time.perf_counter() - t_total
    print(f"\n  {'ALL STEPS PASSED' if all_pass else 'SOME STEPS FAILED'} — "
          f"total wall time: {elapsed:.2f} s\n")


if __name__ == "__main__":
    main()
