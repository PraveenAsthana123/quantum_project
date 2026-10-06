"""
PQC Migration Lab — Master Demo Runner
Runs all demos in sequence with timing and section headers.
"""

import time
import sys
import traceback
from pathlib import Path

# Ensure src/ is on path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def _run_module(label: str, module_name: str) -> bool:
    print("\n" + "#" * 75)
    print(f"#  {label}")
    print("#" * 75)
    t0 = time.perf_counter()
    try:
        mod = __import__(module_name)
        mod.main()
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"\n[OK] {label} completed in {elapsed:.0f} ms")
        return True
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"\n[ERROR] {label} failed after {elapsed:.0f} ms: {exc}")
        traceback.print_exc()
        return False


DEMOS = [
    ("1. PQC PKI — ML-DSA-65 Certificates",          "pqc_pki"),
    ("2. Hybrid TLS 1.3 — X25519 + ML-KEM-768",      "pqc_tls"),
    ("3. PQC JWT — RS256 → ML-DSA-65",               "pqc_jwt"),
    ("4. Post-Quantum SSH",                           "pqc_ssh"),
    ("5. 7-Stage Migration Pipeline",                 "migration_pipeline"),
    ("6. Monitoring Dashboard (29 layers)",           "monitoring_dashboard"),
    ("7. Benchmarking — Classical vs PQC",            "benchmarking"),
    ("8. Interview Prep Q&A",                         "interview_prep"),
]


def main():
    print("=" * 75)
    print("  PQC MIGRATION LAB — MASTER DEMO RUNNER")
    print("  Post-Quantum Cryptography: Complete Enterprise Migration Suite")
    print("=" * 75)
    print(f"  Running {len(DEMOS)} modules...")

    total_start = time.perf_counter()
    results = {}
    for label, module in DEMOS:
        ok = _run_module(label, module)
        results[label] = ok

    total_ms = (time.perf_counter() - total_start) * 1000

    print("\n" + "=" * 75)
    print("  DEMO SUMMARY")
    print("=" * 75)
    passed = sum(1 for ok in results.values() if ok)
    for label, ok in results.items():
        icon = "✓" if ok else "✗"
        print(f"  [{icon}] {label}")

    print(f"\n  {passed}/{len(DEMOS)} demos passed  |  Total time: {total_ms:.0f} ms")
    if passed == len(DEMOS):
        print("  All demos completed successfully.")
    else:
        print("  Some demos failed — see output above for details.")
    print("=" * 75)


if __name__ == "__main__":
    main()
