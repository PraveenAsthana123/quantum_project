"""
PQC Migration Planner.
Reads CBOM JSON produced by crypto_inventory.py and generates a
prioritized migration roadmap with effort estimates and replacement recommendations.
Outputs: CSV + HTML report.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"
CBOM_FILE = DATA_DIR / "cbom.json"
ROADMAP_CSV = DATA_DIR / "migration_roadmap.csv"
ROADMAP_HTML = DATA_DIR / "migration_roadmap.html"


# ---------------------------------------------------------------------------
# Replacement map
# ---------------------------------------------------------------------------

REPLACEMENT_MAP: dict[str, dict] = {
    "RSA":   {"kem": "ML-KEM-768",  "sig": "ML-DSA-65",  "effort_days": 10, "complexity": "Medium"},
    "ECDSA": {"kem": "ML-KEM-768",  "sig": "ML-DSA-65",  "effort_days": 7,  "complexity": "Medium"},
    "ECDH":  {"kem": "ML-KEM-768",  "sig": None,          "effort_days": 7,  "complexity": "Medium"},
    "DSA":   {"kem": None,           "sig": "ML-DSA-65",  "effort_days": 5,  "complexity": "Low"},
    "DH":    {"kem": "ML-KEM-768",  "sig": None,          "effort_days": 12, "complexity": "High"},
    "ED25519": {"kem": None,         "sig": "ML-DSA-44",  "effort_days": 5,  "complexity": "Low"},
    "3DES":  {"kem": None,           "sig": None,          "effort_days": 3,  "complexity": "Low"},
    "DES":   {"kem": None,           "sig": None,          "effort_days": 3,  "complexity": "Low"},
    "RC4":   {"kem": None,           "sig": None,          "effort_days": 3,  "complexity": "Low"},
}

PHASE_MAP = {
    "P1": {"phase": 1, "phase_label": "Immediate (0-6 months)",  "description": "Harvest-Now-Decrypt-Later risk; migrate first"},
    "P2": {"phase": 2, "phase_label": "Short-term (6-18 months)", "description": "Quantum-vulnerable but not actively targeted"},
    "P3": {"phase": 3, "phase_label": "Long-term (18+ months)",   "description": "Already quantum-safe or low-risk"},
}

RISK_SCORE_MAP = {"P1": 9, "P2": 5, "P3": 1}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MigrationAction:
    asset_path: str
    asset_type: str
    current_algorithm: str
    recommended_replacement: str
    migration_priority: str
    phase: int
    phase_label: str
    risk_score: int
    effort_days: int
    complexity: str
    migration_steps: str
    harvest_now_risk: bool
    expiry: Optional[str]

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

def _migration_steps(asset_type: str, current_alg: str, replacement: str) -> str:
    steps = [
        f"1. Inventory: confirm all uses of {current_alg} in {asset_type}",
        f"2. Test: stand up {replacement} in non-prod environment",
        "3. Hybrid: deploy hybrid classical+PQC TLS/auth for compatibility",
        f"4. Rotate: generate new {replacement} keys/certificates",
        "5. Update: push new certificates to all consumers",
        "6. Verify: confirm no remaining {current_alg} endpoints",
        "7. Retire: revoke old certificates and archive keys",
        "8. Audit: update CBOM and run next inventory scan",
    ]
    return " → ".join([f"Step {i+1}: {s[3:]}" for i, s in enumerate(steps)])


def plan_migration(assets: list[dict]) -> list[MigrationAction]:
    actions = []
    for asset in assets:
        alg = asset.get("algorithm", "UNKNOWN").upper()
        priority = asset.get("migration_priority", "P2")
        if asset.get("quantum_safe"):
            continue  # no action needed

        rep_info = REPLACEMENT_MAP.get(alg, {"kem": "ML-KEM-768", "sig": "ML-DSA-65",
                                              "effort_days": 10, "complexity": "High"})
        asset_type = asset.get("asset_type", "unknown")
        if asset_type in ("certificate", "code_signing"):
            replacement = rep_info.get("sig") or rep_info.get("kem") or "ML-DSA-65"
        elif asset_type == "ssh_key":
            replacement = rep_info.get("sig") or "ML-DSA-44"
        else:
            replacement = rep_info.get("kem") or rep_info.get("sig") or "ML-KEM-768"

        phase_info = PHASE_MAP.get(priority, PHASE_MAP["P2"])
        actions.append(MigrationAction(
            asset_path=asset.get("path", ""),
            asset_type=asset_type,
            current_algorithm=alg,
            recommended_replacement=replacement,
            migration_priority=priority,
            phase=phase_info["phase"],
            phase_label=phase_info["phase_label"],
            risk_score=RISK_SCORE_MAP.get(priority, 5),
            effort_days=rep_info.get("effort_days", 7),
            complexity=rep_info.get("complexity", "Medium"),
            migration_steps=_migration_steps(asset_type, alg, replacement),
            harvest_now_risk=asset.get("harvest_now_risk", False),
            expiry=asset.get("expiry"),
        ))

    # Sort by risk score desc, then effort asc
    actions.sort(key=lambda a: (-a.risk_score, a.effort_days))
    return actions


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

def save_csv(actions: list[MigrationAction]) -> Path:
    ROADMAP_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(ROADMAP_CSV, "w", newline="") as f:
        if actions:
            writer = csv.DictWriter(f, fieldnames=actions[0].to_dict().keys())
            writer.writeheader()
            for a in actions:
                writer.writerow(a.to_dict())
    print(f"Migration roadmap CSV → {ROADMAP_CSV}")
    return ROADMAP_CSV


def save_html(actions: list[MigrationAction], cbom_meta: dict) -> Path:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total = cbom_meta.get("total_assets", len(actions))
    vuln = cbom_meta.get("quantum_vulnerable", sum(1 for a in actions))
    hndl = cbom_meta.get("harvest_now_risk", sum(1 for a in actions if a.harvest_now_risk))

    rows_html = ""
    for a in actions:
        color = "#ffcccc" if a.migration_priority == "P1" else ("#fff3cd" if a.migration_priority == "P2" else "#d4edda")
        hndl_badge = '<span style="background:#dc3545;color:#fff;padding:2px 6px;border-radius:4px;font-size:11px">HNDL</span>' if a.harvest_now_risk else ""
        rows_html += f"""
        <tr style="background:{color}">
          <td><b>{a.migration_priority}</b></td>
          <td>{a.phase_label}</td>
          <td><code>{a.asset_path}</code></td>
          <td>{a.asset_type}</td>
          <td><b>{a.current_algorithm}</b></td>
          <td><b>{a.recommended_replacement}</b></td>
          <td>{a.effort_days} days</td>
          <td>{a.complexity}</td>
          <td>{hndl_badge}</td>
          <td>{a.expiry or "N/A"}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>PQC Migration Roadmap</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 30px; background: #f8f9fa; }}
  h1 {{ color: #1a237e; }} h2 {{ color: #283593; }}
  .summary {{ display:flex; gap:20px; margin-bottom:20px; }}
  .card {{ background:#fff; border-left:5px solid; padding:15px 20px; border-radius:6px; box-shadow:0 2px 4px rgba(0,0,0,.1); }}
  .card.total {{ border-color:#1a73e8; }}
  .card.vuln {{ border-color:#e53935; }}
  .card.hndl {{ border-color:#f57c00; }}
  table {{ width:100%; border-collapse:collapse; background:#fff; box-shadow:0 2px 4px rgba(0,0,0,.1); border-radius:6px; overflow:hidden; }}
  th {{ background:#1a237e; color:#fff; padding:10px; text-align:left; font-size:13px; }}
  td {{ padding:8px 10px; font-size:12px; border-bottom:1px solid #eee; }}
  footer {{ margin-top:30px; color:#888; font-size:11px; }}
</style>
</head>
<body>
<h1>Enterprise PQC Migration Roadmap</h1>
<p>Generated: {generated} | Cryptographic Bill of Materials Analysis</p>

<div class="summary">
  <div class="card total"><div style="font-size:24px;font-weight:bold">{total}</div><div>Total Assets</div></div>
  <div class="card vuln"><div style="font-size:24px;font-weight:bold;color:#e53935">{vuln}</div><div>Quantum Vulnerable</div></div>
  <div class="card hndl"><div style="font-size:24px;font-weight:bold;color:#f57c00">{hndl}</div><div>Harvest-Now Risk</div></div>
  <div class="card" style="border-color:#2e7d32"><div style="font-size:24px;font-weight:bold;color:#2e7d32">{total-vuln}</div><div>Already Safe</div></div>
</div>

<h2>Migration Actions ({len(actions)} items)</h2>
<table>
  <tr>
    <th>Priority</th><th>Phase</th><th>Asset Path</th><th>Type</th>
    <th>Current Algorithm</th><th>Replace With</th><th>Effort</th>
    <th>Complexity</th><th>HNDL Risk</th><th>Expiry</th>
  </tr>
  {rows_html}
</table>

<h2>Migration Phases</h2>
<ul>
  <li><b>Phase 1 (P1) — Immediate (0-6 months):</b> Harvest-Now-Decrypt-Later exposure — attackers collect ciphertext today, decrypt later with quantum computer. Migrate these first.</li>
  <li><b>Phase 2 (P2) — Short-term (6-18 months):</b> Quantum-vulnerable algorithms that are not yet actively harvested. Migrate before fault-tolerant quantum computers arrive (est. 2030s).</li>
  <li><b>Phase 3 (P3) — Long-term (18+ months):</b> Assets already using quantum-safe algorithms. Monitor for algorithm deprecations.</li>
</ul>

<footer>Enterprise PQC &amp; Crypto-Agility Control Tower | Praveen Asthana Quantum Portfolio</footer>
</body>
</html>"""

    ROADMAP_HTML.parent.mkdir(parents=True, exist_ok=True)
    with open(ROADMAP_HTML, "w") as f:
        f.write(html)
    print(f"Migration roadmap HTML → {ROADMAP_HTML}")
    return ROADMAP_HTML


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not CBOM_FILE.exists():
        print(f"CBOM not found at {CBOM_FILE} — running crypto_inventory first")
        from crypto_inventory import main as run_inventory
        run_inventory()

    with open(CBOM_FILE) as f:
        cbom = json.load(f)

    assets = cbom.get("assets", [])
    print(f"Planning migration for {len(assets)} assets...")
    actions = plan_migration(assets)

    if not actions:
        print("No vulnerable assets found — all assets are quantum-safe!")
        return []

    print(f"\nMigration actions ({len(actions)} items):")
    for a in actions:
        print(f"  [{a.migration_priority}] Phase {a.phase}: {a.current_algorithm:10s} → {a.recommended_replacement:15s} | {a.effort_days}d | {a.asset_path}")

    save_csv(actions)
    save_html(actions, cbom)
    print(f"\nTotal effort estimate: {sum(a.effort_days for a in actions)} engineer-days")
    return actions


if __name__ == "__main__":
    main()
