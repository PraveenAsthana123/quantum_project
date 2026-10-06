"""
Attack Lab — Synthetic Data Generator
========================================
Purpose  : Generate two synthetic datasets for quantum cryptographic attack
           analysis and defense effectiveness evaluation.

Outputs (all written to ../data/)
---------------------------------
  attack_scenarios.csv  — 200 quantum attack scenarios
  defense_log.csv       — 300 defense evaluation records

Usage
-----
    python generate_data.py
"""
from __future__ import annotations

import csv
import math
import os
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

# ── Reproducible seed ─────────────────────────────────────────────────────────
random.seed(99)

# ── Paths ─────────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(_SCRIPT_DIR, "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

ATTACK_CSV  = os.path.join(DATA_DIR, "attack_scenarios.csv")
DEFENSE_CSV = os.path.join(DATA_DIR, "defense_log.csv")

# ── Attack type definitions ───────────────────────────────────────────────────
# Each entry: (attack_type, target_algorithm, qubits_required, success_prob_range,
#              classical_time_years_range, quantum_time_hours_range, severity, year_feasible)
ATTACK_DEFS: List[Dict[str, Any]] = [
    {
        "attack_type":          "shor_rsa",
        "target_algorithm":     "RSA-2048",
        "n_qubits_required":    4099,
        "success_prob":         (0.85, 0.99),
        "classical_years":      (1e12, 1e15),
        "quantum_hours":        (8, 72),
        "severity":             "CRITICAL",
        "year_feasible":        2032,
        "description":          "Shor factoring RSA-2048 modulus",
    },
    {
        "attack_type":          "shor_rsa",
        "target_algorithm":     "RSA-4096",
        "n_qubits_required":    8195,
        "success_prob":         (0.80, 0.95),
        "classical_years":      (1e15, 1e18),
        "quantum_hours":        (200, 2000),
        "severity":             "HIGH",
        "year_feasible":        2037,
        "description":          "Shor factoring RSA-4096 modulus",
    },
    {
        "attack_type":          "shor_ecdsa",
        "target_algorithm":     "ECDSA-P256",
        "n_qubits_required":    2330,
        "success_prob":         (0.90, 0.99),
        "classical_years":      (1e10, 1e12),
        "quantum_hours":        (1, 24),
        "severity":             "CRITICAL",
        "year_feasible":        2030,
        "description":          "Shor solving ECDLP on P-256",
    },
    {
        "attack_type":          "grover_aes",
        "target_algorithm":     "AES-128",
        "n_qubits_required":    3000,
        "success_prob":         (0.50, 0.75),
        "classical_years":      (1e18, 1e22),
        "quantum_hours":        (1000, 10000),
        "severity":             "HIGH",
        "year_feasible":        2035,
        "description":          "Grover's search on AES-128 keyspace",
    },
    {
        "attack_type":          "grover_aes",
        "target_algorithm":     "AES-256",
        "n_qubits_required":    6000,
        "success_prob":         (0.10, 0.30),
        "classical_years":      (1e38, 1e42),
        "quantum_hours":        (1e9, 1e12),
        "severity":             "MEDIUM",
        "year_feasible":        2050,
        "description":          "Grover's search on AES-256 keyspace",
    },
    {
        "attack_type":          "harvest_decrypt",
        "target_algorithm":     "RSA-2048",
        "n_qubits_required":    4099,
        "success_prob":         (0.95, 0.99),
        "classical_years":      (1e12, 1e15),
        "quantum_hours":        (8, 72),
        "severity":             "CRITICAL",
        "year_feasible":        2025,   # Harvesting can start NOW
        "description":          "Harvest-Now Decrypt-Later on TLS sessions",
    },
    {
        "attack_type":          "harvest_decrypt",
        "target_algorithm":     "DH-2048",
        "n_qubits_required":    4099,
        "success_prob":         (0.88, 0.97),
        "classical_years":      (1e12, 1e14),
        "quantum_hours":        (12, 96),
        "severity":             "CRITICAL",
        "year_feasible":        2025,
        "description":          "Harvest-Now Decrypt-Later on Diffie-Hellman",
    },
    {
        "attack_type":          "intercept_resend",
        "target_algorithm":     "QKD-BB84",
        "n_qubits_required":    50,
        "success_prob":         (0.05, 0.20),
        "classical_years":      (0, 0),
        "quantum_hours":        (0.001, 0.1),
        "severity":             "MEDIUM",
        "year_feasible":        2024,
        "description":          "Intercept-resend attack on BB84 QKD",
    },
    {
        "attack_type":          "side_channel",
        "target_algorithm":     "ML-DSA-65",
        "n_qubits_required":    0,
        "success_prob":         (0.01, 0.15),
        "classical_years":      (0.5, 5),
        "quantum_hours":        (0, 0),
        "severity":             "MEDIUM",
        "year_feasible":        2024,
        "description":          "Power/timing side-channel on PQC implementation",
    },
    {
        "attack_type":          "grover_hash",
        "target_algorithm":     "SHA-256",
        "n_qubits_required":    1500,
        "success_prob":         (0.20, 0.50),
        "classical_years":      (1e32, 1e38),
        "quantum_hours":        (1e10, 1e14),
        "severity":             "LOW",
        "year_feasible":        2060,
        "description":          "Grover's second-preimage attack on SHA-256",
    },
]

DEFENSES = [
    "deploy_ml_dsa_65",
    "deploy_ml_kem_768",
    "enable_pfs",
    "migrate_to_aes_256",
    "deploy_qkd_bb84",
    "implement_timing_countermeasures",
    "rotate_keys_daily",
    "enable_hsm_pqc",
    "network_segmentation",
    "quantum_random_number_generator",
]

# Effectiveness by defense type (0–100%)
DEFENSE_EFFECTIVENESS = {
    "deploy_ml_dsa_65":                  95,
    "deploy_ml_kem_768":                 97,
    "enable_pfs":                        80,
    "migrate_to_aes_256":                72,
    "deploy_qkd_bb84":                   85,
    "implement_timing_countermeasures":  60,
    "rotate_keys_daily":                 55,
    "enable_hsm_pqc":                    90,
    "network_segmentation":              50,
    "quantum_random_number_generator":   70,
}

DEFENSE_COST = {
    "deploy_ml_dsa_65":                  15000,
    "deploy_ml_kem_768":                 18000,
    "enable_pfs":                         5000,
    "migrate_to_aes_256":                 8000,
    "deploy_qkd_bb84":                  250000,
    "implement_timing_countermeasures":  12000,
    "rotate_keys_daily":                  2000,
    "enable_hsm_pqc":                    35000,
    "network_segmentation":              20000,
    "quantum_random_number_generator":   45000,
}

BASE_TIME = datetime(2026, 1, 1)


def _ts(offset_days: float) -> str:
    dt = BASE_TIME + timedelta(days=offset_days)
    return dt.strftime("%Y-%m-%d")


# ── Attack scenarios ──────────────────────────────────────────────────────────

def generate_attack_scenarios(n: int = 200) -> List[str]:
    """Generate n attack scenario rows, cycling through attack types."""
    fieldnames = [
        "attack_id", "attack_type", "target_algorithm",
        "n_qubits_required", "success_probability",
        "classical_time_years", "quantum_time_hours",
        "severity", "year_feasible", "description",
    ]
    scenario_ids: List[str] = []

    with open(ATTACK_CSV, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(n):
            defn = ATTACK_DEFS[i % len(ATTACK_DEFS)]
            attack_id = f"ATK-{uuid.uuid4().hex[:10].upper()}"
            scenario_ids.append(attack_id)
            jitter = random.uniform(0.90, 1.10)
            writer.writerow({
                "attack_id":             attack_id,
                "attack_type":           defn["attack_type"],
                "target_algorithm":      defn["target_algorithm"],
                "n_qubits_required":     defn["n_qubits_required"],
                "success_probability":   round(
                    random.uniform(*defn["success_prob"]), 4),
                "classical_time_years":  round(
                    defn["classical_years"][0] * jitter, 2),
                "quantum_time_hours":    round(
                    defn["quantum_hours"][0] * jitter, 2),
                "severity":              defn["severity"],
                "year_feasible":         defn["year_feasible"],
                "description":           defn["description"],
            })
    print(f"[generate_data] Wrote {n} attack scenarios → {ATTACK_CSV}")
    return scenario_ids


# ── Defense log ───────────────────────────────────────────────────────────────

def generate_defense_log(scenario_ids: List[str], n: int = 300) -> None:
    fieldnames = [
        "log_id", "scenario_id", "defense_applied",
        "defense_effectiveness_pct", "cost_usd",
        "implementation_days", "status",
    ]
    statuses = ["DEPLOYED", "DEPLOYED", "DEPLOYED", "TESTING", "PLANNED"]

    with open(DEFENSE_CSV, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(n):
            defense = random.choice(DEFENSES)
            base_eff = DEFENSE_EFFECTIVENESS[defense]
            eff      = min(100, round(base_eff * random.uniform(0.85, 1.05), 1))
            cost     = DEFENSE_COST[defense] * random.uniform(0.8, 1.2)
            writer.writerow({
                "log_id":                    f"DEF-{uuid.uuid4().hex[:10].upper()}",
                "scenario_id":               random.choice(scenario_ids),
                "defense_applied":           defense,
                "defense_effectiveness_pct": eff,
                "cost_usd":                  round(cost, 2),
                "implementation_days":        random.randint(1, 180),
                "status":                    random.choice(statuses),
            })
    print(f"[generate_data] Wrote {n} defense records → {DEFENSE_CSV}")


# ── Entry point ───────────────────────────────────────────────────────────────

def generate() -> None:
    scenario_ids = generate_attack_scenarios(200)
    generate_defense_log(scenario_ids, 300)


if __name__ == "__main__":
    generate()
