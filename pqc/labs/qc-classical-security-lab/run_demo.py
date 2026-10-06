#!/usr/bin/env python3
"""
Classical Security Lab — Master Demo Runner
Maps scenario names to source files. Supports --list and --all flags.

Usage:
  python3 run_demo.py --list
  python3 run_demo.py --all
  python3 run_demo.py pki
  python3 run_demo.py tls jwt
  python3 run_demo.py vuln layers
"""

import sys
import os
import time
import importlib
import importlib.util
import argparse
import traceback

# ---------------------------------------------------------------------------
# Scenario registry
# ---------------------------------------------------------------------------

LAB_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(LAB_DIR, "src")

SCENARIOS = {
    "pki": {
        "file":        "classical_pki.py",
        "title":       "Classical PKI — RSA-2048, ECDSA P-256, X.509 Certificates",
        "description": "Key generation, signing, verification, and certificate chain demo. "
                       "Shows RSA-2048 and ECDSA P-256 timing. Quantum threat: Shor's algorithm "
                       "breaks both (~4096 and ~2330 logical qubits respectively).",
        "tags":        ["asymmetric", "certificates", "shor"],
    },
    "tls": {
        "file":        "classical_tls.py",
        "title":       "Classical TLS 1.3 Handshake Simulation",
        "description": "Step-by-step TLS 1.3: ClientHello, ECDHE key exchange, ECDSA "
                       "authentication, HKDF key schedule, AES-256-GCM record layer. "
                       "Quantum threat: ECDHE and ECDSA both broken by Shor's.",
        "tags":        ["transport", "ecdhe", "aes-gcm", "shor"],
    },
    "jwt": {
        "file":        "classical_jwt.py",
        "title":       "Classical JWT — HS256, RS256, ES256 + Replay Attack Demo",
        "description": "JWT token generation and verification for all three algorithms. "
                       "Includes replay attack, alg:none vulnerability, and jti bypass demo. "
                       "Quantum threat: RS256 (RSA) and ES256 (ECDSA) broken by Shor's.",
        "tags":        ["api", "authentication", "shor", "attacks"],
    },
    "ssh": {
        "file":        "classical_ssh.py",
        "title":       "Classical SSH Protocol Simulation",
        "description": "SSH-2 handshake: version exchange, algorithm negotiation, ECDH key "
                       "exchange, host key authentication (ECDSA), key derivation, "
                       "AES-256-CTR bulk cipher, HMAC-SHA256 MAC. "
                       "Quantum threat: ECDH and ECDSA both broken by Shor's.",
        "tags":        ["ssh", "remote-access", "ecdh", "shor"],
    },
    "vpn": {
        "file":        "classical_vpn.py",
        "title":       "Classical IPsec/IKEv2 VPN Simulation",
        "description": "IKEv2 SA negotiation, DH Group 14 (2048-bit MODP) key exchange, "
                       "PRF-HMAC-SHA256 SKEYSEED derivation, Child SA, IPsec ESP "
                       "AES-256-CBC + HMAC-SHA256 ICV. "
                       "Quantum threat: DH Group 14 broken by Shor's.",
        "tags":        ["vpn", "ipsec", "dh", "shor"],
    },
    "vuln": {
        "file":        "vulnerability_analyzer.py",
        "title":       "Quantum Vulnerability Analyzer — Full Threat Matrix",
        "description": "Assesses 20 classical algorithms (RSA, ECDSA, ECDH, DH, AES, SHA, "
                       "Ed25519, secp256k1, HMAC, PBKDF2) against Shor's and Grover's. "
                       "Provides severity, logical qubits needed, timeline, and PQC replacement.",
        "tags":        ["analysis", "shor", "grover", "matrix"],
    },
    "layers": {
        "file":        "layer_security_map.py",
        "title":       "29-Layer Security Map — Classical Crypto per OSI/Security Layer",
        "description": "Maps L1 Physical through L29 AI/ML Security to their classical "
                       "cryptographic algorithms, quantum vulnerability level, breaking "
                       "quantum algorithm, and PQC migration path. Includes urgency tiers.",
        "tags":        ["architecture", "layers", "shor", "grover", "migration"],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_and_run(scenario_name: str) -> bool:
    """Load a scenario module and call its main() function."""
    scenario = SCENARIOS[scenario_name]
    filepath = os.path.join(SRC_DIR, scenario["file"])

    if not os.path.exists(filepath):
        print(f"  [ERROR] File not found: {filepath}")
        return False

    spec   = importlib.util.spec_from_file_location(scenario_name, filepath)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        module.main()
        return True
    except Exception as exc:
        print(f"\n  [ERROR] Scenario '{scenario_name}' raised an exception:")
        traceback.print_exc()
        return False


def print_scenario_list():
    """Print all available scenarios with descriptions."""
    print()
    print("=" * 70)
    print("  CLASSICAL SECURITY LAB — AVAILABLE SCENARIOS")
    print("=" * 70)
    for name, meta in SCENARIOS.items():
        tags_str = ", ".join(meta["tags"])
        print(f"\n  [{name}]")
        print(f"    {meta['title']}")
        print(f"    {meta['description']}")
        print(f"    Tags: {tags_str}")
    print()
    print("  Usage:")
    print("    python3 run_demo.py --list")
    print("    python3 run_demo.py --all")
    print("    python3 run_demo.py pki")
    print("    python3 run_demo.py tls jwt ssh vpn")
    print("    python3 run_demo.py vuln layers")
    print()


def print_banner():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║     CLASSICAL SECURITY LAB — Quantum Portfolio          ║")
    print("║     OLD / PRE-PQC Security System Demonstration         ║")
    print("║     Shows why classical crypto must be migrated         ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()


def print_run_header(scenario_name: str):
    meta = SCENARIOS[scenario_name]
    width = 70
    print()
    print("┌" + "─" * (width - 2) + "┐")
    print(f"│  RUNNING: {scenario_name.upper():<{width-12}}│")
    title_short = meta["title"][:width-6]
    print(f"│  {title_short:<{width-4}}│")
    print("└" + "─" * (width - 2) + "┘")


def print_run_summary(results: dict, total_ms: float):
    print()
    print("=" * 60)
    print("  RUN SUMMARY")
    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    failed = len(results) - passed
    for name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"    {name:<12} : {status}")
    print()
    print(f"  Scenarios run : {len(results)}")
    print(f"  Passed        : {passed}")
    print(f"  Failed        : {failed}")
    print(f"  Total time    : {total_ms:.2f} ms")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="run_demo.py",
        description="Classical Security Lab — Master Demo Runner",
    )
    parser.add_argument(
        "scenarios",
        nargs="*",
        metavar="SCENARIO",
        help="One or more scenario names to run (pki, tls, jwt, ssh, vpn, vuln, layers)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available scenarios and exit",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all scenarios in order",
    )

    args = parser.parse_args()

    print_banner()

    if args.list:
        print_scenario_list()
        return

    if args.all:
        targets = list(SCENARIOS.keys())
    elif args.scenarios:
        targets = []
        for name in args.scenarios:
            if name not in SCENARIOS:
                print(f"  [ERROR] Unknown scenario: '{name}'")
                print(f"  Available: {', '.join(SCENARIOS.keys())}")
                sys.exit(1)
            targets.append(name)
    else:
        print("  No scenario specified. Use --list to see options, or --all to run everything.")
        print()
        print_scenario_list()
        return

    results = {}
    t_total = time.perf_counter()

    for name in targets:
        print_run_header(name)
        t0   = time.perf_counter()
        ok   = load_and_run(name)
        took = (time.perf_counter() - t0) * 1000
        results[name] = ok
        print(f"\n  [{'OK' if ok else 'FAIL'}] '{name}' completed in {took:.2f} ms")

    total_ms = (time.perf_counter() - t_total) * 1000
    print_run_summary(results, total_ms)


if __name__ == "__main__":
    main()
