"""
Classical Security Lab — CLI Demo Script
==========================================
Demonstrates crypto agility scanning, CBOM generation, maturity assessment,
vulnerability analysis, migration planning, policy checking, and agility scoring.
No Streamlit — pure Python CLI output.

Usage
-----
    cd qc-classical-security-lab
    python src/demo.py

Steps
-----
  1  Crypto inventory scan
  2  CBOM (CycloneDX) generation
  3  Maturity assessment (5 layers)
  4  Vulnerability analysis (top 10 critical findings)
  5  Migration plan — RSA-2048 → ML-DSA-65
  6  Policy check — 5 algorithm/use-case pairs
  7  Agility score for payment-gateway system
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from collections import defaultdict
from typing import Any, Dict, List

# ── path setup ────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)

from generate_data import generate, INVENTORY_JSON, VULN_CSV, MIGRATION_CSV
from sbom_generator import SBOMGenerator
from crypto_agility import CryptoAgilityFramework
from maturity_model import MaturityModel
from vulnerability_analyzer import ALGORITHMS as VULN_ALGOS

# ── helpers ───────────────────────────────────────────────────────────────────
PASS  = "\u2713 PASS"
FAIL  = "\u2717 FAIL"
SEP   = "=" * 72


def _banner(step: int, title: str) -> None:
    print(f"\n{SEP}")
    print(f"  STEP {step}: {title}")
    print(SEP)


def _table(headers: List[str], rows: List[List[Any]], col_width: int = 18) -> None:
    widths = [max(col_width, len(h) + 2) for h in headers]
    hdr    = "  ".join(str(h).ljust(w) for h, w in zip(headers, widths))
    print(hdr)
    print("-" * len(hdr))
    for row in rows:
        print("  ".join(str(c).ljust(w) for c, w in zip(row, widths)))


def _ensure_data() -> None:
    if not os.path.exists(INVENTORY_JSON):
        print("  [INFO] Generating synthetic data …")
        generate()


# ── step implementations ──────────────────────────────────────────────────────

def step1_crypto_inventory() -> Dict[str, Any]:
    _banner(1, "Crypto Inventory Scan")
    t0 = time.perf_counter()
    _ensure_data()

    with open(INVENTORY_JSON) as fh:
        inv = json.load(fh)

    assets     = inv["assets"]
    total      = len(assets)
    vulnerable = sum(1 for a in assets if a["quantum_vulnerable"])
    safe       = total - vulnerable

    by_algo: Dict[str, int] = defaultdict(int)
    for a in assets:
        by_algo[a["algorithm"]] += 1

    print(f"  total_assets       : {total}")
    print(f"  vulnerable_count   : {vulnerable}")
    print(f"  quantum_safe_count : {safe}")
    print(f"  vulnerability_rate : {vulnerable/total*100:.1f}%\n")

    rows_data = [[algo, cnt, f"{cnt/total*100:.1f}%"]
                 for algo, cnt in sorted(by_algo.items(), key=lambda x: -x[1])]
    _table(["algorithm", "count", "share"], rows_data, col_width=16)

    elapsed = time.perf_counter() - t0
    print(f"\n  Scan completed in {elapsed*1000:.1f} ms  {PASS}")
    return {"total": total, "vulnerable": vulnerable, "safe": safe, "by_algo": dict(by_algo)}


def step2_cbom_generation() -> None:
    _banner(2, "CBOM Generation — CycloneDX Summary")
    t0 = time.perf_counter()

    sg   = SBOMGenerator()
    cbom = sg.generate_cbom()

    components = cbom.get("components", [])
    n_comp     = len(components) if isinstance(components, list) else 0
    spec_ver   = cbom.get("specVersion", "1.6")
    serial     = cbom.get("serialNumber", "urn:uuid:demo-cbom")
    bom_format = cbom.get("bomFormat", "CycloneDX")

    # Count vulnerable from built-in scan
    ca        = CryptoAgilityFramework()
    vuln_list = ca.list_quantum_vulnerable()
    vuln_pct  = f"{len(vuln_list)}/{len(ca.list_all())} algorithms quantum-vulnerable"

    rows_data = [
        ["bom_format",       bom_format],
        ["spec_version",     spec_ver],
        ["serial_number",    str(serial)[:32]],
        ["components",       n_comp],
        ["vuln_algorithms",  vuln_pct],
        ["generated_at",     cbom.get("metadata", {}).get("timestamp", "2026-10-06")[:19]
                             if isinstance(cbom.get("metadata"), dict) else "2026-10-06"],
    ]
    _table(["field", "value"], rows_data, col_width=24)

    elapsed = time.perf_counter() - t0
    print(f"\n  CBOM generated in {elapsed*1000:.1f} ms  {PASS}")


def step3_maturity_assessment() -> None:
    _banner(3, "Maturity Assessment — 5 Sample Layers")
    t0 = time.perf_counter()

    mm = MaturityModel()
    sample_layers = ["L01", "L02", "L05", "L10", "L28"]

    rows_data = []
    for layer_id in sample_layers:
        lm = mm.get_layer_maturity(layer_id)
        rows_data.append([
            layer_id,
            lm["layer_name"][:20],
            lm["level_badge"],
            f"{lm['average_score']:.1f}",
            lm["effort_to_next_level"][:20],
        ])

    _table(["layer_id", "layer_name", "maturity", "avg_score", "effort_to_next"],
           rows_data, col_width=20)

    elapsed = time.perf_counter() - t0
    print(f"\n  Maturity assessment in {elapsed*1000:.1f} ms  {PASS}")


def step4_vulnerability_analysis() -> None:
    _banner(4, "Vulnerability Analysis — Top 10 Critical Findings")
    t0 = time.perf_counter()
    _ensure_data()

    findings: List[Dict[str, Any]] = []
    with open(VULN_CSV, newline="") as fh:
        for row in csv.DictReader(fh):
            findings.append(row)

    # Sort by CVSS descending; take top 10
    critical = sorted(
        [f for f in findings if float(f.get("cvss_score", 0)) >= 7.5],
        key=lambda x: float(x.get("cvss_score", 0)),
        reverse=True
    )[:10]

    rows_data = []
    for f in critical:
        rows_data.append([
            f["finding_id"][:14],
            f["algorithm"][:12],
            f["cvss_score"],
            f["priority"][:12],
            f["system_name"][:16],
            f.get("pqc_replacement", "N/A")[:14],
        ])

    _table(["finding_id", "algorithm", "cvss", "priority", "system", "replacement"],
           rows_data, col_width=16)

    elapsed = time.perf_counter() - t0
    print(f"\n  Found {len(critical)} critical findings in {elapsed*1000:.1f} ms  {PASS}")


def step5_migration_plan() -> None:
    _banner(5, "Migration Plan — RSA-2048 → ML-DSA-65")
    t0 = time.perf_counter()

    ca   = CryptoAgilityFramework()
    plan = ca.generate_migration_plan("RSA-2048", "ML-DSA-65", system_count=10)

    print(f"  from_algo       : {plan.from_algo}")
    print(f"  to_algo         : {plan.to_algo}")
    print(f"  system_count    : {plan.system_count}")
    print(f"  estimated_days  : {plan.estimated_days}")
    print(f"  effort_person_days: {plan.effort_person_days}")
    print(f"  risk_level      : {plan.risk_level}\n")

    rows_data = []
    for phase in plan.phases:
        rows_data.append([
            str(phase.get("name", phase.get("phase", "")))[:28],
            phase.get("duration_days", phase.get("days", "N/A")),
            phase.get("effort_fte_weeks", phase.get("tasks", ["N/A"])[0][:20]
                       if isinstance(phase.get("tasks"), list) else "N/A"),
        ])
    _table(["phase", "duration_days", "effort_or_task"],
           rows_data, col_width=28)

    elapsed = time.perf_counter() - t0
    print(f"\n  Migration plan in {elapsed*1000:.1f} ms  {PASS}")


def step6_policy_check() -> None:
    _banner(6, "Policy Check — 5 Algorithm / Use-Case Pairs")
    t0 = time.perf_counter()

    ca = CryptoAgilityFramework()

    # policy_as_code_check uses specific registered use_case keys
    checks = [
        ("RSA-2048",    "pki_ca_signing"),
        ("ML-DSA-65",   "code_signing"),
        ("AES-128",     "bulk_encryption"),
        ("SHA-1",       "integrity_hashing"),
        ("ML-KEM-768",  "tls13_key_exchange"),
    ]

    rows_data = []
    for algo_name, use_case in checks:
        result = ca.policy_as_code_check(algo_name, use_case)
        allowed_val = result.get("allowed")
        if allowed_val is True:
            policy_str = "ALLOWED"
        elif allowed_val is False:
            policy_str = "BLOCKED"
        else:
            # None means use_case not registered → flag as REVIEW
            policy_str = "REVIEW"
        rows_data.append([
            algo_name,
            use_case[:24],
            policy_str,
            str(result.get("reason", ""))[:32],
            result.get("cnsa2_deadline", "N/A"),
        ])

    _table(["algorithm", "use_case", "policy", "reason", "deadline"],
           rows_data, col_width=18)

    elapsed = time.perf_counter() - t0
    print(f"\n  Policy checks in {elapsed*1000:.1f} ms  {PASS}")


def step7_agility_score() -> None:
    _banner(7, "Crypto Agility Score — payment-gateway System")
    t0 = time.perf_counter()

    ca    = CryptoAgilityFramework()
    score = ca.agility_score(
        system_name="payment-gateway",
        algorithms_in_use=["RSA-2048", "AES-128", "SHA-256"],
        abstraction_layers=0,
        hardcoded_count=5,
        crypto_test_coverage_pct=20.0,
        config_driven=False,
        key_rotation_automated=False,
    )

    total      = score.get("score", 0)
    breakdown  = score.get("breakdown", {})
    grade      = score.get("grade", "N/A")
    top_gap    = score.get("gaps", ["N/A"])[0] if score.get("gaps") else "N/A"

    rows_data = [[dim, f"{v:.1f}"] for dim, v in breakdown.items()]
    _table(["dimension", "score"], rows_data, col_width=24)

    print(f"\n  Overall agility_score : {total:.1f} / 100")
    print(f"  Grade                 : {grade}")
    print(f"  Top gap               : {top_gap[:60]}")

    elapsed = time.perf_counter() - t0
    print(f"\n  Agility score in {elapsed*1000:.1f} ms  {PASS}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{'#'*72}")
    print("  Classical Security Lab — Production Demo")
    print(f"{'#'*72}")

    _ensure_data()

    results: Dict[str, bool] = {}
    t_total = time.perf_counter()

    try:
        step1_crypto_inventory()
        results["Step 1 — Crypto inventory scan"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 1 — Crypto inventory scan"] = False

    try:
        step2_cbom_generation()
        results["Step 2 — CBOM generation"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 2 — CBOM generation"] = False

    try:
        step3_maturity_assessment()
        results["Step 3 — Maturity assessment"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 3 — Maturity assessment"] = False

    try:
        step4_vulnerability_analysis()
        results["Step 4 — Vulnerability analysis"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 4 — Vulnerability analysis"] = False

    try:
        step5_migration_plan()
        results["Step 5 — Migration plan"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 5 — Migration plan"] = False

    try:
        step6_policy_check()
        results["Step 6 — Policy check"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 6 — Policy check"] = False

    try:
        step7_agility_score()
        results["Step 7 — Agility score"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 7 — Agility score"] = False

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
