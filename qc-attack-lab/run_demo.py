"""
QC Attack Lab — Master Demo Runner
====================================
Runs all simulation modules in sequence with timing.
Educational attack simulation lab for quantum security portfolio.

Defensive Security Educational Lab — /mnt/deepa/quantum/qc-attack-lab/
"""

import sys
import time
import traceback


def _run_module(label: str, module_path: str) -> tuple[bool, float]:
    """Import and run a module's main() function. Returns (success, elapsed_s)."""
    import importlib.util
    import os

    spec = importlib.util.spec_from_file_location(label, module_path)
    if spec is None or spec.loader is None:
        print(f"  [ERROR] Cannot load {module_path}")
        return False, 0.0
    mod = importlib.util.module_from_spec(spec)
    t0 = time.perf_counter()
    try:
        spec.loader.exec_module(mod)  # type: ignore[attr-defined]
        if hasattr(mod, "main"):
            mod.main()
        elapsed = time.perf_counter() - t0
        return True, elapsed
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        print(f"\n  [ERROR] {label} raised: {exc}")
        traceback.print_exc()
        return False, elapsed


def main():
    import os
    lab_root = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(lab_root, "src")
    sys.path.insert(0, src)
    sys.path.insert(0, lab_root)

    print("\n" + "█" * 76)
    print("  QC ATTACK LAB — QUANTUM SECURITY ATTACK SIMULATION SUITE")
    print("  Defensive Security Educational Lab")
    print("  /mnt/deepa/quantum/qc-attack-lab/")
    print("█" * 76)
    print()
    print("  DISCLAIMER: All attacks are theoretical simulations for educational")
    print("  understanding of the threat landscape. No offensive capability is")
    print("  provided. All code uses Python stdlib + numpy only.")
    print()

    modules = [
        ("Classical Attacks",     os.path.join(src, "classical_attacks.py")),
        ("Quantum Attacks",       os.path.join(src, "quantum_attacks.py")),
        ("AI Attacks",            os.path.join(src, "ai_attacks.py")),
        ("Attack Detection",      os.path.join(src, "attack_detection.py")),
        ("Defense Playbook",      os.path.join(src, "defense_playbook.py")),
        ("Interview Prep",        os.path.join(src, "interview_attack_prep.py")),
    ]

    results = []
    total_start = time.perf_counter()

    for label, path in modules:
        print(f"\n{'▼' * 76}")
        print(f"  RUNNING: {label}")
        print(f"{'▼' * 76}")
        success, elapsed = _run_module(label, path)
        results.append((label, success, elapsed))

    total_elapsed = time.perf_counter() - total_start

    # Final summary
    print("\n\n" + "█" * 76)
    print("  DEMO RUN COMPLETE — EXECUTION SUMMARY")
    print("█" * 76)
    print(f"  {'Module':<30} {'Status':<12} {'Time (s)'}")
    print("  " + "-" * 56)
    for label, success, elapsed in results:
        status = "OK" if success else "FAILED"
        print(f"  {label:<30} {status:<12} {elapsed:.2f}s")
    print("  " + "-" * 56)
    print(f"  {'TOTAL':<30} {'':12} {total_elapsed:.2f}s")
    print("█" * 76)

    passed = sum(1 for _, s, _ in results if s)
    failed = len(results) - passed
    print(f"\n  Modules run: {len(results)}  |  Passed: {passed}  |  Failed: {failed}")
    print()
    print("  PORTFOLIO COVERAGE:")
    print("  ✓ Classical cryptographic attacks (RSA, ECDSA, AES, JWT, MITM, timing)")
    print("  ✓ Quantum-era attacks (Shor's RSA/ECC, Grover's AES/SHA, HNDL, AI-assisted)")
    print("  ✓ AI/ML security attacks (FGSM, extraction, poisoning, prompt injection, inversion)")
    print("  ✓ Detection & monitoring (timing, HNDL, JWT, certs, side-channel)")
    print("  ✓ Defense playbook (immediate / 30-day / PQC migration per attack)")
    print("  ✓ Interview preparation (26 Q&As, NIST FIPS 203/204/205/206, cheatsheet)")
    print()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
