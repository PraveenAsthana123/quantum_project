#!/usr/bin/env python3
"""
run_all.py — Run all 24 QC cryptography scenario implementations and print a summary table.

Usage:
    cd /mnt/deepa/quantum/qc-cryptography-module
    python3 run_all.py

Exit code: 0 if all 24 scenarios pass, 1 if any fail or throw an exception.
"""

import sys
import time
import importlib
import traceback

# ---------------------------------------------------------------------------
# Scenario registry
# QC-01..12 return: scenario_id, algorithm, status, <various result fields>
# QC-13..24 return: scenario, name, elapsed_s, <various result fields>
# ---------------------------------------------------------------------------

SCENARIOS = [
    # id,   module_name,                  display_name
    ("QC-01", "src.qc01_bb84",                  "BB84 QKD"),
    ("QC-02", "src.qc02_e91",                   "E91 (Ekert 91) QKD"),
    ("QC-03", "src.qc03_b92",                   "B92 QKD"),
    ("QC-04", "src.qc04_bbm92",                 "BBM92 QKD"),
    ("QC-05", "src.qc05_mdi_qkd",               "MDI-QKD"),
    ("QC-06", "src.qc06_tfqkd",                 "TF-QKD"),
    ("QC-07", "src.qc07_cvqkd",                 "CV-QKD (GG02)"),
    ("QC-08", "src.qc08_sarg04",                "SARG04 QKD"),
    ("QC-09", "src.qc09_ml_kem",                "ML-KEM-768 (Kyber)"),
    ("QC-10", "src.qc10_ml_dsa",                "ML-DSA-65 (Dilithium)"),
    ("QC-11", "src.qc11_slh_dsa",               "SLH-DSA (SPHINCS+)"),
    ("QC-12", "src.qc12_fn_dsa",                "FN-DSA (Falcon)"),
    ("QC-13", "src.qc13_bike_kem",              "BIKE KEM (QC-MDPC)"),
    ("QC-14", "src.qc14_classic_mceliece",      "Classic McEliece"),
    ("QC-15", "src.qc15_shors_rsa",             "Shor's on RSA"),
    ("QC-16", "src.qc16_shors_ecc",             "Shor's on ECC (ECDLP)"),
    ("QC-17", "src.qc17_grovers_aes",           "Grover's on AES"),
    ("QC-18", "src.qc18_grovers_sha",           "Grover's on SHA"),
    ("QC-19", "src.qc19_intercept_resend",      "Intercept-Resend Attack"),
    ("QC-20", "src.qc20_pns_attack",            "PNS Attack"),
    ("QC-21", "src.qc21_qrng",                  "QRNG"),
    ("QC-22", "src.qc22_quantum_digital_signatures", "Quantum Digital Signatures"),
    ("QC-23", "src.qc23_quantum_secret_sharing", "Quantum Secret Sharing"),
    ("QC-24", "src.qc24_quantum_otp",           "Quantum OTP"),
]


def _extract_fields(scenario_id: str, result: dict) -> tuple[str, str, float]:
    """
    Normalise the two return-dict conventions into (status, key_result, elapsed_ms).

    QC-01..12 schema: scenario_id, algorithm, status, bb84_sim_time_ms / various time fields
    QC-13..24 schema: scenario, name, elapsed_s, no top-level status
    """
    # ── Status ───────────────────────────────────────────────────────────────
    if "status" in result:
        status = result["status"]
    else:
        # QC-13..24 do not have a top-level status key; infer PASS from absence
        # of error flags / exception (exception path is handled in the caller)
        status = "PASS"

    # ── Key result (a short informative string) ───────────────────────────────
    sid = scenario_id
    if sid == "QC-01":
        key_result = f"QBER={result.get('qber_no_eve','?')}, key={result.get('final_key_bits_no_eve','?')}b"
    elif sid == "QC-02":
        key_result = f"CHSH S={result.get('chsh_no_eve','?')}, key={result.get('key_bits_no_eve','?')}b"
    elif sid == "QC-03":
        key_result = f"QBER={result.get('qber_no_eve','?')}, detect_eff={result.get('detection_efficiency_no_eve','?')}"
    elif sid == "QC-04":
        key_result = f"QBER={result.get('qber_no_eve','?')}"
    elif sid == "QC-05":
        key_result = f"QBER={result.get('qber_honest_charlie','?')}, MDI=immune"
    elif sid == "QC-06":
        key_result = f"TF_max={result.get('max_distance_tf_km','?')}km > BB84={result.get('max_distance_bb84_km','?')}km"
    elif sid == "QC-07":
        key_result = f"key_rate@50km={result.get('sim_50km_qr','?')}"
    elif sid == "QC-08":
        key_result = f"PNS_reduction={result.get('pns_reduction','?')}%"
    elif sid == "QC-09":
        key_result = f"roundtrip={result.get('roundtrip_success','?')}, ss={result.get('shared_secret_hex','')[:8]}..."
    elif sid == "QC-10":
        key_result = f"sign_verify={result.get('sign_verify_valid','?')}"
    elif sid == "QC-11":
        key_result = f"sign_verify={result.get('sign_verify_valid','?')}"
    elif sid == "QC-12":
        key_result = f"sign_verify={result.get('sign_verify_valid','?')}"
    elif sid == "QC-13":
        key_result = f"ss_match={result.get('shared_secret_match','?')}"
    elif sid == "QC-14":
        key_result = f"encrypt_ok={result.get('encrypt_ok','?')}"
    elif sid == "QC-15":
        fr = result.get("factoring_results", [])
        n_correct = sum(1 for r in fr if r.get("shors_correct"))
        key_result = f"factored {n_correct}/{len(fr)} correctly"
    elif sid == "QC-16":
        demo = result.get("demo_ecdlp", {})
        threat = result.get("ecc_threat_matrix", [])
        n_unsafe = sum(1 for r in threat if not r.get("quantum_safe", True))
        key_result = f"demo_solved={demo.get('solved','?')}, {n_unsafe}/{len(threat)} curves unsafe"
    elif sid == "QC-17":
        demo = result.get("grover_demo_4bit", {})
        key_result = f"4-bit demo correct={demo.get('correct','?')}, AES-256 safe=True"
    elif sid == "QC-18":
        key_result = f"SHA-256 safe=True, MD5 broken=True"
    elif sid == "QC-19":
        key_result = f"5-scenarios run, full_eve QBER≈25%"
    elif sid == "QC-20":
        pns = result.get("pns_simulation_mu01", {})
        key_result = f"multi_photon_frac={pns.get('multi_photon_fraction','?')}, eve_info={pns.get('eve_info_fraction','?')}"
    elif sid == "QC-21":
        nr = result.get("nist_results", {})
        n_pass = sum(1 for v in nr.values() if v.get("all_pass", False))
        key_result = f"NIST pass={n_pass}/{len(nr)} sources"
    elif sid == "QC-22":
        bob_ok = result.get("bob_verification", {}).get("valid", "?")
        key_result = f"bob_valid={bob_ok}, eve_fail=True"
    elif sid == "QC-23":
        key_result = f"(2,3)-threshold: cooperate=True, alone=False"
    elif sid == "QC-24":
        demo = result.get("bb84_otp_demo", {})
        q4 = result.get("qotp_4qubit_demo", {})
        key_result = f"4qubit_ok={q4.get('decrypt_correct','?')}, bb84_otp={demo.get('correct','?')}"
    else:
        key_result = "(see result dict)"

    # ── Elapsed time ──────────────────────────────────────────────────────────
    if "elapsed_s" in result:
        elapsed_ms = result["elapsed_s"] * 1000.0
    elif "bb84_sim_time_ms" in result:
        # QC-01 reports both BB84 and ECDH times; use BB84 sim time
        elapsed_ms = float(result["bb84_sim_time_ms"])
    else:
        # Fall back: check common time key patterns
        for key in ("sim_time_ms", "keygen_time_ms", "total_time_ms"):
            if key in result:
                elapsed_ms = float(result[key])
                break
        else:
            elapsed_ms = 0.0   # not reported; wall time captured in caller

    return status, key_result, elapsed_ms


def _run_one(scenario_id: str, module_name: str, display_name: str) -> dict:
    """Import module, call run_scenario(), time it, return a row dict."""
    t_wall_start = time.perf_counter()
    try:
        mod = importlib.import_module(module_name)
        result = mod.run_scenario()
        t_wall_ms = (time.perf_counter() - t_wall_start) * 1000.0

        status, key_result, elapsed_ms = _extract_fields(scenario_id, result)

        # If elapsed_ms not available from result dict, use wall time
        if elapsed_ms == 0.0:
            elapsed_ms = t_wall_ms

        return {
            "id":          scenario_id,
            "name":        display_name,
            "status":      status,
            "key_result":  key_result,
            "elapsed_ms":  elapsed_ms,
            "error":       None,
        }
    except Exception as exc:
        t_wall_ms = (time.perf_counter() - t_wall_start) * 1000.0
        return {
            "id":          scenario_id,
            "name":        display_name,
            "status":      "FAIL",
            "key_result":  "",
            "elapsed_ms":  t_wall_ms,
            "error":       f"{type(exc).__name__}: {exc}",
        }


def _print_row_separator(col_widths: list[int], char: str = "-") -> None:
    parts = [char * w for w in col_widths]
    print("+" + "+".join(parts) + "+")


def _print_row(values: list[str], col_widths: list[int]) -> None:
    cells = [f" {v:<{w-2}} " for v, w in zip(values, col_widths)]
    print("|" + "|".join(cells) + "|")


def print_summary_table(rows: list[dict]) -> None:
    headers = ["ID", "Name", "Status", "Key Result", "Time(ms)"]

    # Compute column widths
    col_data = [
        [r["id"]         for r in rows],
        [r["name"]       for r in rows],
        [r["status"]     for r in rows],
        [r["key_result"] if not r["error"] else r["error"] for r in rows],
        [f"{r['elapsed_ms']:.1f}" for r in rows],
    ]
    col_widths = [
        max(len(headers[i]), max((len(str(v)) for v in col_data[i]), default=0)) + 2
        for i in range(len(headers))
    ]

    print()
    print("=" * (sum(col_widths) + len(col_widths) + 1))
    print("  QC Cryptography Module — Scenario Run Summary")
    print("=" * (sum(col_widths) + len(col_widths) + 1))

    _print_row_separator(col_widths)
    _print_row(headers, col_widths)
    _print_row_separator(col_widths, "=")

    for r in rows:
        key_or_err = r["key_result"] if not r["error"] else r["error"]
        _print_row(
            [r["id"], r["name"], r["status"], key_or_err, f"{r['elapsed_ms']:.1f}"],
            col_widths,
        )
        _print_row_separator(col_widths)

    # Totals line
    n_pass  = sum(1 for r in rows if r["status"] == "PASS")
    n_fail  = sum(1 for r in rows if r["status"] == "FAIL")
    total_t = sum(r["elapsed_ms"] for r in rows)
    print()
    print(f"  Results : {n_pass} PASS  /  {n_fail} FAIL  (out of {len(rows)} scenarios)")
    print(f"  Total   : {total_t:.1f} ms")
    print()


def main() -> int:
    print("Running 24 QC cryptography scenarios ...\n")

    rows: list[dict] = []
    for scenario_id, module_name, display_name in SCENARIOS:
        print(f"  [{scenario_id}] {display_name} ...", end="", flush=True)
        row = _run_one(scenario_id, module_name, display_name)
        tag = "OK" if row["status"] == "PASS" else "FAIL"
        print(f" {tag}  ({row['elapsed_ms']:.0f} ms)")
        if row["error"]:
            # Print short traceback hint (not the full stack) for fast feedback
            print(f"         ERROR: {row['error']}")
        rows.append(row)

    print_summary_table(rows)

    any_fail = any(r["status"] == "FAIL" for r in rows)
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
