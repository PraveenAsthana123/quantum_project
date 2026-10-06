#!/usr/bin/env python3
"""
run_all.py — Run all 10 QC security lab scripts and print a summary table.

Usage:
    cd /mnt/deepa/quantum/qc-security-lab
    python3 run_all.py

Exit code: 0 if all scripts pass (no exception), 1 if any throw an exception.
"""

import sys
import time
import subprocess
import traceback

# ---------------------------------------------------------------------------
# Script registry
# ---------------------------------------------------------------------------

SCRIPTS = [
    # id,    script_path,               display_name
    ("SEC-01", "src/pqc_benchmark.py",       "PQC Benchmark (liboqs)"),
    ("SEC-02", "src/qkd_bb84.py",            "BB84 QKD"),
    ("SEC-03", "src/e91_qkd.py",             "E91 Entanglement QKD"),
    ("SEC-04", "src/mdi_qkd_simulation.py",  "MDI-QKD Simulation"),
    ("SEC-05", "src/ml_kem_kyber.py",        "ML-KEM (Kyber-512)"),
    ("SEC-06", "src/ml_dsa_dilithium.py",    "ML-DSA (Dilithium2)"),
    ("SEC-07", "src/slh_dsa_sphincs.py",     "SLH-DSA (SPHINCS+)"),
    ("SEC-08", "src/qrng.py",                "QRNG"),
    ("SEC-09", "src/quantum_ids.py",         "Quantum IDS (VQC)"),
    ("SEC-10", "src/classical_baseline.py",  "Classical IDS Baseline"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

WIDTH = 78


def run_script(script_path: str, timeout_s: int = 300) -> tuple[str, float, str]:
    """
    Run script_path as a subprocess.
    Returns (status, elapsed_s, error_snippet).
    """
    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        elapsed = time.perf_counter() - t0
        if result.returncode == 0:
            return "PASS", elapsed, ""
        else:
            # Script exited non-zero — still counts as "ran"
            snippet = (result.stderr or result.stdout or "")[-200:].strip().replace("\n", " | ")
            return "FAIL", elapsed, snippet[:80]
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - t0
        return "TIMEOUT", elapsed, f"Exceeded {timeout_s}s"
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return "ERROR", elapsed, str(exc)[:80]


def colour(status: str) -> str:
    if status == "PASS":
        return f"{GREEN}{status}{RESET}"
    if status == "FAIL":
        return f"{YELLOW}{status}{RESET}"
    return f"{RED}{status}{RESET}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("\n" + "=" * WIDTH)
    print(f"  QC Security Lab — All Scripts Runner")
    print(f"  {len(SCRIPTS)} scripts  |  cwd: /mnt/deepa/quantum/qc-security-lab")
    print("=" * WIDTH)

    rows = []
    all_ok = True

    for sid, script, name in SCRIPTS:
        print(f"  Running {sid}: {name} ...", end="", flush=True)
        status, elapsed, err = run_script(script)
        tag = colour(status)
        rows.append((sid, name, status, elapsed, err))
        elapsed_str = f"{elapsed:.1f}s"
        print(f"\r  {sid}  {elapsed_str:>6}  {tag}  {name:<36}")
        if status not in ("PASS",):
            all_ok = False
            if err:
                print(f"           {YELLOW}note: {err}{RESET}")

    # Summary table
    print("\n" + "─" * WIDTH)
    print(f"  {'ID':<8} {'Script':<38} {'Status':>6}  {'Time':>6}")
    print("─" * WIDTH)

    for sid, name, status, elapsed, err in rows:
        tag = colour(status)
        elapsed_str = f"{elapsed:.1f}s"
        print(f"  {sid:<8} {name:<38} {tag:>6}  {elapsed_str:>6}")

    print("─" * WIDTH)
    pass_count = sum(1 for _, _, s, _, _ in rows if s == "PASS")
    total_time = sum(e for _, _, _, e, _ in rows)
    summary_colour = GREEN if all_ok else RED
    print(f"\n  Result: {summary_colour}{pass_count}/{len(SCRIPTS)} PASSED{RESET}   Total time: {total_time:.1f}s")

    # Data files created
    import os
    data_dir = "data"
    if os.path.isdir(data_dir):
        json_files = sorted(f for f in os.listdir(data_dir) if f.endswith(".json"))
        print(f"\n  Data files in {data_dir}/ ({len(json_files)} JSON):")
        for f in json_files:
            fpath = os.path.join(data_dir, f)
            size_kb = os.path.getsize(fpath) / 1024
            mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(fpath)))
            print(f"    {mtime}  {size_kb:5.1f} KB  {f}")

    print("=" * WIDTH + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
