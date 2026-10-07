"""
Quantum Attack System Lab — Master Runner
==========================================
Runs all 7 lab modules in sequence with section headers.
Each module can also be run independently.

Usage:
  python3 run_demo.py                    # Run all modules
  python3 run_demo.py --module shors_rsa # Run single module
  python3 run_demo.py --list             # List available modules

No external dependencies — Python 3.8+ stdlib only.
"""

import sys
import os
import time
import importlib
import argparse

LAB_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(LAB_DIR, "src")

MODULES = [
    {
        "key":         "shors_rsa",
        "filename":    "shors_rsa_attack",
        "title":       "Shor's Algorithm — RSA Attack",
        "description": "Factor small RSA moduli step-by-step, resource estimates for RSA-512 to RSA-4096, "
                       "CRQC timeline projection, and full RSA-15 attack narrative.",
        "estimated_s": 2,
    },
    {
        "key":         "shors_ecc",
        "filename":    "shors_ecc_attack",
        "title":       "Shor's Algorithm — ECC Attack",
        "description": "ECDLP explanation, resource estimates for P-256/P-384/P-521/secp256k1 (Bitcoin), "
                       "$1.75 trillion in crypto assets at risk, full attack narrative.",
        "estimated_s": 2,
    },
    {
        "key":         "grovers",
        "filename":    "grovers_attack",
        "title":       "Grover's Algorithm — Symmetric Crypto Attack",
        "description": "AES-128/192/256 quantum analysis, SHA family threat table, "
                       "password hashing (bcrypt/PBKDF2/Argon2id) quantum resistance.",
        "estimated_s": 2,
    },
    {
        "key":         "hndl",
        "filename":    "hndl_attack",
        "title":       "Harvest Now Decrypt Later (HNDL)",
        "description": "Nation-state collection estimates (185 PB/month), 5 concrete HNDL scenarios, "
                       "migration urgency matrix, Mosca inequality calculations.",
        "estimated_s": 2,
    },
    {
        "key":         "crypto_analysis",
        "filename":    "quantum_crypto_analysis",
        "title":       "Complete Quantum Crypto Threat Matrix",
        "description": "Full threat matrix (RSA → ML-KEM), system risk analyzer for enterprise configs, "
                       "migration priority ordering, explanation of quantum advantage.",
        "estimated_s": 2,
    },
    {
        "key":         "timeline",
        "filename":    "quantum_attack_timeline",
        "title":       "Quantum Attack Timeline",
        "description": "1994–2038 ASCII timeline, CRQC countdown (optimistic/moderate/conservative), "
                       "migration deadline calculator using Mosca inequality.",
        "estimated_s": 2,
    },
    {
        "key":         "interview",
        "filename":    "interview_quantum_attacks",
        "title":       "Interview Preparation — Quantum Attacks",
        "description": "10 expert Q&As: Shor's, Grover's, HNDL, migration priorities, NIST standards, "
                       "crypto agility. Interview-ready 150–200 word answers.",
        "estimated_s": 2,
    },
]


def banner() -> None:
    print("\n" + "█"*70)
    print("█  QUANTUM ATTACK SYSTEM LAB")
    print("█  Defensive Security Education — How Quantum Breaks Classical Crypto")
    print("█  github.com/PraveenAsthana123/quantum  |  Python stdlib only")
    print("█"*70)
    print("""
  This lab simulates quantum computing attacks on classical cryptography for:
  • Defensive security understanding
  • Enterprise migration planning
  • Principal Architect / Security Engineer interview preparation

  Algorithms covered:
    Shor's Algorithm  →  Breaks RSA, ECC, DH (0 bits of quantum security)
    Grover's Algorithm → Weakens AES-128, SHA-1/MD5 (halves effective bits)
    HNDL               → Active nation-state threat operating today

  NIST Standards:  FIPS 203 ML-KEM  |  FIPS 204 ML-DSA  |  FIPS 205 SLH-DSA
""")


def separator(module: dict) -> None:
    print("\n" + "▓"*70)
    print(f"▓  MODULE: {module['title']}")
    print(f"▓  {module['description']}")
    print("▓"*70)


def run_module(filename: str) -> bool:
    """Dynamically import and run main() from src/<filename>.py."""
    sys.path.insert(0, SRC_DIR)
    try:
        mod = importlib.import_module(filename)
        if hasattr(mod, "main"):
            mod.main()
            return True
        else:
            print(f"  [WARNING] {filename}.py has no main() function — skipping.")
            return False
    except ImportError as e:
        print(f"  [ERROR] Could not import {filename}: {e}")
        return False
    except Exception as e:
        print(f"  [ERROR] {filename}.main() raised an exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if SRC_DIR in sys.path:
            sys.path.remove(SRC_DIR)


def list_modules() -> None:
    print("\n  Available modules (use --module <key> to run individually):")
    print(f"  {'Key':<16} {'Module':<40} {'Est. Time'}")
    print(f"  {'─'*62}")
    for m in MODULES:
        print(f"  {m['key']:<16} {m['title']:<40} ~{m['estimated_s']}s")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Quantum Attack System Lab — Master Runner",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--module", "-m",
        type=str,
        default=None,
        help="Run a single module by key (see --list for available keys)",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available modules and exit",
    )
    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="Suppress the intro banner",
    )
    args = parser.parse_args()

    if args.list:
        list_modules()
        return

    if not args.no_banner:
        banner()

    if args.module:
        # Find matching module
        match = next((m for m in MODULES if m["key"] == args.module.lower()), None)
        if match is None:
            print(f"  [ERROR] Unknown module key: '{args.module}'")
            list_modules()
            sys.exit(1)
        separator(match)
        success = run_module(match["filename"])
        sys.exit(0 if success else 1)

    # Run all modules
    total   = len(MODULES)
    passed  = 0
    failed  = []
    t_start = time.time()

    print(f"  Running {total} modules ...\n")

    for i, mod in enumerate(MODULES, 1):
        print(f"\n  [{i}/{total}] Starting: {mod['title']}")
        separator(mod)
        t0 = time.time()
        ok = run_module(mod["filename"])
        elapsed = time.time() - t0
        status  = "OK" if ok else "FAILED"
        print(f"\n  [{i}/{total}] {status} in {elapsed:.1f}s — {mod['title']}")
        if ok:
            passed += 1
        else:
            failed.append(mod["title"])

    elapsed_total = time.time() - t_start

    print("\n" + "▓"*70)
    print("▓  QUANTUM ATTACK LAB — RUN COMPLETE")
    print("▓"*70)
    print(f"\n  Modules run:    {total}")
    print(f"  Passed:         {passed}")
    print(f"  Failed:         {total - passed}")
    print(f"  Total time:     {elapsed_total:.1f}s")

    if failed:
        print(f"\n  Failed modules:")
        for name in failed:
            print(f"    • {name}")
        sys.exit(1)
    else:
        print(f"\n  All modules completed successfully.")
        print(f"\n  KEY FINDINGS SUMMARY:")
        print(f"  • RSA-2048 / ECDSA P-256: BROKEN by Shor's (0 bits quantum security)")
        print(f"  • AES-128: WEAKENED by Grover's (64 bits quantum security — upgrade)")
        print(f"  • AES-256 / SHA-256: SAFE (128 bits quantum security)")
        print(f"  • HNDL: Active threat TODAY — adversaries harvesting encrypted traffic")
        print(f"  • CRQC arrival: 2029 (10%) / 2033 (50%) / 2038 (90%)")
        print(f"  • Migrate to: FIPS 203 ML-KEM + FIPS 204 ML-DSA + FIPS 205 SLH-DSA")
    print()


if __name__ == "__main__":
    main()
