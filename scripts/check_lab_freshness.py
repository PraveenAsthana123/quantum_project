#!/usr/bin/env python3
"""
check_lab_freshness.py — Check freshness of each quantum lab's results JSON.

Warns if any result is older than STALE_DAYS (default 10).
Prints a table: Lab | Results File | Last Run | Age (days) | Status

Usage:
    python3 /mnt/deepa/quantum/scripts/check_lab_freshness.py

Exit code: 0 if all labs are fresh, 1 if any are stale or missing.
"""

import os
import sys
import time

# ─── Configuration ─────────────────────────────────────────────────────────────
STALE_DAYS = 10
BASE = "/mnt/deepa/quantum"

LABS = [
    # (display_name, results_json_path)
    ("Banking Lab",      f"{BASE}/qc-banking-lab/results/fraud_benchmark_results.json"),
    ("Finance Lab",      f"{BASE}/qc-finance-lab/results/finance_summary.json"),
    ("Healthcare Lab",   f"{BASE}/qc-healthcare-lab/results/healthcare_summary.json"),
    ("Security Lab",     f"{BASE}/qc-security-lab/results/security_summary.json"),
    ("Logistics Lab",    f"{BASE}/qc-logistics-lab/results/supply_chain_results.json"),
    ("Logistics VRP",    f"{BASE}/qc-logistics-lab/results/vrp_benchmark_results.json"),
]

# ─── Colour helpers ─────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def colour(text: str, code: str) -> str:
    return f"{code}{text}{RESET}"

# ─── Main ───────────────────────────────────────────────────────────────────────

def check_lab(name: str, results_path: str) -> dict:
    """Return freshness info for one lab."""
    if not os.path.exists(results_path):
        return {
            "name": name,
            "path": results_path,
            "exists": False,
            "last_run": None,
            "age_days": None,
            "status": "MISSING",
        }

    mtime = os.path.getmtime(results_path)
    now = time.time()
    age_days = (now - mtime) / 86400

    last_run_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))

    if age_days <= STALE_DAYS:
        status = "FRESH"
    else:
        status = "STALE"

    return {
        "name": name,
        "path": results_path,
        "exists": True,
        "last_run": last_run_str,
        "age_days": round(age_days, 1),
        "status": status,
    }


def main() -> int:
    print("\n" + "=" * 82)
    print(f"  Quantum Lab Freshness Report  |  Stale threshold: {STALE_DAYS} days")
    print(f"  Checked: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 82)

    results = [check_lab(name, path) for name, path in LABS]

    print(f"\n  {'Lab':<20} {'Last Run':<18} {'Age (days)':>10}  {'Status':<10}  Results File")
    print("  " + "─" * 79)

    all_fresh = True
    for r in results:
        age_str  = f"{r['age_days']:.1f}" if r["age_days"] is not None else "N/A"
        last_str = r["last_run"] if r["last_run"] else "—"

        if r["status"] == "FRESH":
            status_col = colour("FRESH  ", GREEN)
        elif r["status"] == "STALE":
            status_col = colour("STALE  ", YELLOW)
            all_fresh = False
        else:
            status_col = colour("MISSING", RED)
            all_fresh = False

        # Shorten path for display
        short_path = r["path"].replace(BASE + "/", "").replace("/results/", "/results/\n" + " " * 72)
        short_path = r["path"].replace(BASE + "/", "")

        print(f"  {r['name']:<20} {last_str:<18} {age_str:>10}  {status_col}  {short_path}")

    # Stale + missing summary
    stale  = [r for r in results if r["status"] == "STALE"]
    missing = [r for r in results if r["status"] == "MISSING"]
    fresh  = [r for r in results if r["status"] == "FRESH"]

    print("\n" + "─" * 82)
    print(f"  Summary: {colour(str(len(fresh)), GREEN)} fresh  "
          f"{colour(str(len(stale)), YELLOW)} stale  "
          f"{colour(str(len(missing)), RED)} missing  "
          f"(of {len(results)} labs checked)")

    if stale:
        print(f"\n  {YELLOW}STALE labs (re-run recommended):{RESET}")
        for r in stale:
            print(f"    {r['name']}: last run {r['last_run']} ({r['age_days']} days ago)")

    if missing:
        print(f"\n  {RED}MISSING results (lab never run or wrong path):{RESET}")
        for r in missing:
            print(f"    {r['name']}: {r['path']}")

    if all_fresh:
        print(f"\n  {GREEN}All labs fresh — no action needed.{RESET}")

    # Log directory staleness check
    logs_dir = f"{BASE}/.continuity/logs"
    print(f"\n  Cron log files ({logs_dir}):")
    if os.path.isdir(logs_dir):
        log_files = sorted(f for f in os.listdir(logs_dir) if f.endswith(".log"))
        if log_files:
            for lf in log_files:
                lpath = os.path.join(logs_dir, lf)
                lmtime = os.path.getmtime(lpath)
                lage = (time.time() - lmtime) / 86400
                lmod = time.strftime("%Y-%m-%d %H:%M", time.localtime(lmtime))
                lsize = os.path.getsize(lpath)
                status_col = colour("ok", GREEN) if lage <= STALE_DAYS else colour("stale", YELLOW)
                print(f"    {lf:<20} {lmod}  age={lage:.1f}d  size={lsize}B  [{status_col}]")
        else:
            print(f"    (no .log files yet — will appear after first Sunday cron run)")
    else:
        print(f"    {RED}logs dir missing: {logs_dir}{RESET}")

    print("=" * 82 + "\n")
    return 0 if all_fresh else 1


if __name__ == "__main__":
    sys.exit(main())
