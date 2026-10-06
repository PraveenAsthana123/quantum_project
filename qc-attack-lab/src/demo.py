"""
Attack Lab — CLI Demo Script
===============================
Demonstrates quantum and classical cryptographic attack simulations and
corresponding defense effectiveness analysis.
No Streamlit — pure Python CLI output.

Usage
-----
    cd qc-attack-lab
    python src/demo.py

Steps
-----
  1  Load attack scenarios and print threat summary
  2  Shor's algorithm on RSA — resource estimates from module
  3  Grover's algorithm on AES — security bit reduction
  4  Harvest-Now Decrypt-Later (HNDL) threat
  5  Attack matrix — all types, feasibility, defense
  6  Defense effectiveness from generated defense log
"""
from __future__ import annotations

import csv
import math
import os
import sys
import time
from collections import defaultdict
from typing import Any, Dict, List

# ── path setup ────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)

from generate_data import (generate, ATTACK_CSV, DEFENSE_CSV)
from quantum_attacks import (ShorsRSAAttack, GroversAESAttack,
                              HarvestNowDecryptLater)
from defense_playbook import PLAYBOOK

# ── helpers ───────────────────────────────────────────────────────────────────
PASS  = "\u2713 PASS"
FAIL  = "\u2717 FAIL"
SEP   = "=" * 72


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
    if not os.path.exists(ATTACK_CSV):
        print("  [INFO] Generating synthetic data …")
        generate()


def _fmt_sci(v: float) -> str:
    if v == 0:
        return "0"
    if v >= 1e9:
        exp = int(math.log10(v))
        return f"~1e{exp}"
    return f"{v:,.0f}"


# ── step implementations ──────────────────────────────────────────────────────

def step1_load_scenarios() -> List[Dict[str, Any]]:
    _banner(1, "Load Attack Scenarios — Threat Summary")
    t0 = time.perf_counter()
    _ensure_data()

    scenarios: List[Dict[str, Any]] = []
    with open(ATTACK_CSV, newline="") as fh:
        for row in csv.DictReader(fh):
            scenarios.append(row)

    by_severity: Dict[str, int] = defaultdict(int)
    by_type:     Dict[str, int] = defaultdict(int)

    for s in scenarios:
        by_severity[s["severity"]] += 1
        by_type[s["attack_type"]]  += 1

    print(f"  Total scenarios: {len(scenarios)}\n")
    print("  By severity:")
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        cnt = by_severity.get(sev, 0)
        bar = "#" * min(40, cnt // 2)
        print(f"    {sev:<12} {cnt:>4}  {bar}")

    print("\n  By attack type:")
    for atype, cnt in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"    {atype:<24} {cnt:>4}")

    elapsed = time.perf_counter() - t0
    print(f"\n  Loaded in {elapsed*1000:.1f} ms  {PASS}")
    return scenarios


def step2_shors_rsa() -> None:
    _banner(2, "Shor's Algorithm — RSA Threat Analysis")
    t0 = time.perf_counter()

    threats = ShorsRSAAttack().run()

    # Display each threat
    rows_data = []
    for t in threats:
        rows_data.append([
            t.name[:24],
            t.target[:12],
            f"{t.qubits_logical:,}" if t.qubits_logical else "N/A",
            f"~{t.qubits_physical_est:,}" if t.qubits_physical_est else "N/A",
            t.crqc_year_est,
            t.urgency,
        ])

    _table(["threat_name", "target", "logical_q", "physical_q",
            "crqc_year", "urgency"],
           rows_data, col_width=18)

    # Closed-form estimates for RSA-2048
    logical_q   = 2 * 2048 + 3         # 4099
    d           = 27
    physical_q  = logical_q * d * d    # ~2.99M
    t_gates     = 40 * (2048 ** 3) * 7

    print(f"\n  [RSA-2048 closed-form — Beauregard 2003]")
    print(f"    logical_qubits  : {logical_q:,}")
    print(f"    code_distance_d : {d}")
    print(f"    physical_qubits : ~{physical_q:,}")
    print(f"    T_gates         : {_fmt_sci(float(t_gates))}")
    print(f"    defense         : Migrate to ML-DSA-65 (FIPS 204)")

    elapsed = time.perf_counter() - t0
    print(f"\n  Shor analysis in {elapsed*1000:.1f} ms  {PASS}")


def step3_grovers_aes() -> None:
    _banner(3, "Grover's Algorithm — AES Security Bit Reduction")
    t0 = time.perf_counter()

    threats = GroversAESAttack().run()

    rows_data = []
    for t in threats:
        rows_data.append([
            t.name[:20],
            t.target[:12],
            t.classical_security[:12],
            t.quantum_security[:16],
            t.urgency,
            t.crqc_year_est,
        ])

    _table(["threat", "target", "classical_sec", "pq_security",
            "urgency", "crqc_year"],
           rows_data, col_width=18)

    # Quantify oracle calls
    print("\n  Oracle call estimates (Grover quadratic speedup):")
    for key_bits, label in [(128, "AES-128"), (256, "AES-256")]:
        oracle_calls = math.pi / 4 * math.sqrt(2 ** key_bits)
        eff_bits     = key_bits // 2
        print(f"    {label}: oracle_calls={_fmt_sci(oracle_calls)} | "
              f"effective_security={eff_bits} bits post-quantum")

    elapsed = time.perf_counter() - t0
    print(f"\n  Grover analysis in {elapsed*1000:.1f} ms  {PASS}")


def step4_hndl_attack() -> None:
    _banner(4, "Harvest-Now Decrypt-Later (HNDL) Attack")
    t0 = time.perf_counter()

    hndl   = HarvestNowDecryptLater()
    threat = hndl.run()   # returns a single QuantumThreat

    print(f"  CRQC estimated year : {hndl.CRQC_YEAR}")
    print(f"  Current year        : {hndl.CURRENT_YEAR}")
    print(f"  Exposure window     : {hndl.CRQC_YEAR - hndl.CURRENT_YEAR} years")
    print(f"  Urgency             : {threat.urgency}")
    print(f"  Logical qubits req  : {threat.qubits_logical:,}\n")

    # Print simulation results as table
    rows_data = []
    for scenario, detail in threat.simulation_result.items():
        rows_data.append([scenario[:32], str(detail)[:38]])
    _table(["harvest_scenario", "detail"], rows_data, col_width=32)

    print("\n  Key insight: data recorded from RSA/ECDSA sessions NOW")
    print("  can be decrypted retroactively once a CRQC is available.")
    print("  PQ-safe protocols (ML-KEM-768) are immune to HNDL attacks.")

    elapsed = time.perf_counter() - t0
    print(f"\n  HNDL analysis in {elapsed*1000:.1f} ms  {PASS}")


def step5_attack_matrix() -> None:
    _banner(5, "Attack Matrix — All Types, Feasibility, Defense")
    t0 = time.perf_counter()

    matrix_rows = [
        ("shor_rsa",         "RSA-2048",    2032, "ML-DSA-65 (FIPS 204)"),
        ("shor_ecdsa",       "ECDSA-P256",  2030, "ML-DSA-65 (FIPS 204)"),
        ("grover_aes",       "AES-128",     2035, "AES-256 (CNSA 2.0)"),
        ("harvest_decrypt",  "RSA-2048",    2025, "Deploy PQC now; enable PFS"),
        ("intercept_resend", "QKD-BB84",    2024, "Decoy-state BB84; auth QKD"),
        ("side_channel",     "ML-DSA-65",   2024, "Constant-time impl; HSM"),
        ("grover_hash",      "SHA-256",     2060, "SHA3-256 or SHA-512"),
    ]

    rows_data = []
    for attack, target, year, defense in matrix_rows:
        rows_data.append([attack[:20], target[:16], year, defense[:32]])

    _table(["attack", "target", "feasibility_year", "defense_recommendation"],
           rows_data, col_width=20)

    elapsed = time.perf_counter() - t0
    print(f"\n  Attack matrix in {elapsed*1000:.1f} ms  {PASS}")


def step6_defense_effectiveness() -> None:
    _banner(6, "Defense Effectiveness — Cost / Coverage Analysis")
    t0 = time.perf_counter()
    _ensure_data()

    by_defense: Dict[str, List[float]]  = defaultdict(list)
    by_cost:    Dict[str, List[float]]  = defaultdict(list)
    by_days:    Dict[str, List[int]]    = defaultdict(list)

    with open(DEFENSE_CSV, newline="") as fh:
        for row in csv.DictReader(fh):
            d = row["defense_applied"]
            by_defense[d].append(float(row["defense_effectiveness_pct"]))
            by_cost[d].append(float(row["cost_usd"]))
            by_days[d].append(int(row["implementation_days"]))

    rows_data = []
    for defense, effs in sorted(by_defense.items(),
                                 key=lambda x: -sum(x[1])/max(1, len(x[1]))):
        avg_eff  = sum(effs) / len(effs)
        avg_cost = sum(by_cost[defense]) / len(by_cost[defense])
        avg_days = sum(by_days[defense]) / len(by_days[defense])
        rows_data.append([
            defense[:32],
            f"{avg_eff:.1f}%",
            f"${avg_cost:,.0f}",
            f"{avg_days:.0f}",
        ])

    _table(["defense", "avg_coverage_pct", "avg_cost_usd", "avg_impl_days"],
           rows_data, col_width=28)

    # Also show playbook entry count
    print(f"\n  Defense playbook entries available: {len(PLAYBOOK)}")

    elapsed = time.perf_counter() - t0
    print(f"\n  Defense effectiveness in {elapsed*1000:.1f} ms  {PASS}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{'#'*72}")
    print("  Attack Lab — Quantum Cryptographic Attack Simulation Demo")
    print(f"{'#'*72}")
    print("  [EDUCATIONAL USE ONLY — All attacks are theoretical simulations]")

    _ensure_data()

    results: Dict[str, bool] = {}
    t_total = time.perf_counter()

    try:
        step1_load_scenarios()
        results["Step 1 — Load attack scenarios"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 1 — Load attack scenarios"] = False

    try:
        step2_shors_rsa()
        results["Step 2 — Shor's RSA"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 2 — Shor's RSA"] = False

    try:
        step3_grovers_aes()
        results["Step 3 — Grover's AES"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 3 — Grover's AES"] = False

    try:
        step4_hndl_attack()
        results["Step 4 — HNDL attack"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 4 — HNDL attack"] = False

    try:
        step5_attack_matrix()
        results["Step 5 — Attack matrix"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 5 — Attack matrix"] = False

    try:
        step6_defense_effectiveness()
        results["Step 6 — Defense effectiveness"] = True
    except Exception as e:
        print(f"  {FAIL}: {e}"); results["Step 6 — Defense effectiveness"] = False

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
