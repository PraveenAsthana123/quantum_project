"""
Harvest Now Decrypt Later (HNDL) Attack Simulation
====================================================
Models the "Store Now, Decrypt Later" / "Harvest Now, Decrypt Later" threat
where nation-state adversaries collect encrypted traffic today for decryption
once a Cryptographically Relevant Quantum Computer (CRQC) becomes available.

HNDL is NOT a future threat — it is ACTIVE TODAY.

References:
- NSA Cybersecurity Advisory (2022): "Quantum Computing and Post-Quantum Cryptography"
- CISA/NSA/ODNI (2022): "Quantum-Computing and Post-Quantum Cryptography FAQs"
- BSI (2021): "Quantum Computing — impact and potential threats to IT security"
- Mosca, M. (2018): "Cybersecurity in an Era with Quantum Computers"
- Internet2 / NIST IR 8413.

Educational use only — demonstrates defensive security concepts.
"""

import math
from typing import NamedTuple


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

CURRENT_YEAR = 2026

DATA_SENSITIVITY = {
    "CLASSIFIED":   {"level": 4, "description": "National security, intelligence operations"},
    "CONFIDENTIAL": {"level": 3, "description": "Trade secrets, financial records, health data"},
    "INTERNAL":     {"level": 2, "description": "Internal corporate communications"},
    "PUBLIC":       {"level": 1, "description": "Publicly available information"},
}

ALGORITHM_VULNERABILITY = {
    "RSA-2048":     {"vulnerable": True,  "pq_bits": 0,   "shor_target": True},
    "RSA-4096":     {"vulnerable": True,  "pq_bits": 0,   "shor_target": True},
    "ECDHE-P256":   {"vulnerable": True,  "pq_bits": 0,   "shor_target": True},
    "ECDH-P384":    {"vulnerable": True,  "pq_bits": 0,   "shor_target": True},
    "DH-2048":      {"vulnerable": True,  "pq_bits": 0,   "shor_target": True},
    "AES-128":      {"vulnerable": False, "pq_bits": 64,  "shor_target": False},
    "AES-256":      {"vulnerable": False, "pq_bits": 128, "shor_target": False},
    "ChaCha20-256": {"vulnerable": False, "pq_bits": 128, "shor_target": False},
    "ML-KEM-768":   {"vulnerable": False, "pq_bits": 184, "shor_target": False},
    "ML-DSA-65":    {"vulnerable": False, "pq_bits": 138, "shor_target": False},
}

RISK_LEVELS = {
    (True,  "HIGH"):    "CRITICAL",
    (True,  "MEDIUM"):  "HIGH",
    (True,  "LOW"):     "MEDIUM",
    (False, "HIGH"):    "LOW",
    (False, "MEDIUM"):  "LOW",
    (False, "LOW"):     "NONE",
}


class RiskResult(NamedTuple):
    data_sensitivity:  str
    retention_years:   int
    algorithm:         str
    crqc_year:         int
    years_until_crqc:  int
    exposed_after_crqc: int
    algorithm_vulnerable: bool
    risk_score:        str
    recommendation:    str


class HNDLThreatModel:
    """
    Models HNDL risk as a function of:
      - Data sensitivity (classification level)
      - Data retention requirement (how long must data be protected?)
      - Algorithm in use (vulnerable to Shor's or not?)
      - CRQC arrival estimate (optimistic/moderate/conservative)

    Mosca Inequality: if X = years to migration, Y = years data must be secure,
    Z = years until CRQC then: if X + Y > Z → URGENT ACTION REQUIRED NOW.
    """

    # ── 1. Calculate risk ─────────────────────────────────────────────────────

    def calculate_risk(
        self,
        data_sensitivity: str,
        retention_years:  int,
        algorithm:        str,
        crqc_year:        int = 2033,
    ) -> RiskResult:
        """
        Calculate HNDL risk for a given data/algorithm/timeline combination.

        Risk is HIGH when:
          - Algorithm is quantum-vulnerable (Shor's target), AND
          - retention_years > (crqc_year - current_year)
        """
        years_until_crqc    = crqc_year - CURRENT_YEAR
        end_of_protection   = CURRENT_YEAR + retention_years
        exposed_after_crqc  = max(0, end_of_protection - crqc_year)

        alg_data    = ALGORITHM_VULNERABILITY.get(algorithm, {"vulnerable": True, "pq_bits": 0})
        vulnerable  = alg_data["vulnerable"]
        sens_level  = DATA_SENSITIVITY.get(data_sensitivity, {"level": 2})["level"]

        # Determine urgency of the retention overlap
        if retention_years > years_until_crqc:
            retention_urgency = "HIGH"
        elif retention_years > (years_until_crqc // 2):
            retention_urgency = "MEDIUM"
        else:
            retention_urgency = "LOW"

        # Overall risk
        risk_score = RISK_LEVELS.get((vulnerable, retention_urgency), "UNKNOWN")

        # Upgrade risk for sensitive data
        if sens_level >= 4 and risk_score == "HIGH":
            risk_score = "CRITICAL"
        elif sens_level >= 3 and risk_score == "MEDIUM":
            risk_score = "HIGH"

        # Recommendation
        if risk_score == "CRITICAL":
            recommendation = (
                "IMMEDIATE ACTION: Begin PQC migration today. "
                "This data is already being harvested. "
                "Deploy ML-KEM hybrid mode in TLS NOW."
            )
        elif risk_score == "HIGH":
            recommendation = (
                "URGENT: Plan PQC migration within 6 months. "
                "Prioritize this system in your CBOM (Crypto Bill of Materials). "
                "Apply for NIST FIPS 203/204 early deployment."
            )
        elif risk_score == "MEDIUM":
            recommendation = (
                "PLAN: Include in 2-year migration roadmap. "
                "Evaluate hybrid classical/PQC scheme as interim measure."
            )
        elif risk_score == "LOW":
            recommendation = (
                "MONITOR: Data retention within CRQC window. "
                "Standard PQC migration timeline acceptable."
            )
        else:
            recommendation = "No quantum threat — algorithm is post-quantum safe."

        return RiskResult(
            data_sensitivity=data_sensitivity,
            retention_years=retention_years,
            algorithm=algorithm,
            crqc_year=crqc_year,
            years_until_crqc=years_until_crqc,
            exposed_after_crqc=exposed_after_crqc,
            algorithm_vulnerable=vulnerable,
            risk_score=risk_score,
            recommendation=recommendation,
        )

    # ── 2. Estimate intercepted traffic ──────────────────────────────────────

    def estimate_intercepted_traffic(self) -> None:
        """
        Estimate scale of HNDL-relevant traffic a nation-state adversary
        could realistically collect and store for later decryption.
        """
        print("\n" + "="*70)
        print("  HNDL SCALE ESTIMATE — NATION-STATE ADVERSARY")
        print("="*70)
        print(f"""
GLOBAL INTERNET TRAFFIC (2026 estimates)
─────────────────────────────────────────
  Total internet backbone traffic:         ~463 EB/month  (Cisco VNI projection)
  Estimated encrypted fraction (TLS/HTTPS): ~95% of web, ~40% of all traffic
  Encrypted traffic volume:                ~185 EB/month

NATION-STATE COLLECTION CAPACITY
──────────────────────────────────
  Assumption: sophisticated adversary (Tier-1 signals intelligence)
  Capture rate:  0.01% of backbone (targeted interception points)
  Monthly HNDL storage:  ~185 PB/month = ~2.2 EB/year

  Known HNDL programs (publicly disclosed):
  • MUSCULAR (NSA/GCHQ): intercepted Google/Yahoo datacenter traffic
  • BULLRUN (NSA): worked to undermine encryption standards
  • UPSTREAM collection: fiber tap on transatlantic cables
  • PRISM: direct server access at major tech companies

TARGET PRIORITY TIERS
──────────────────────
  Tier 1 (IMMEDIATE collection priority):
    • Government agency TLS (ECDHE-RSA, ECDHE-ECDSA)
    • Military communications (even if separately encrypted at application layer)
    • Financial SWIFT/FIX protocol messages
    • Pharmaceutical/defense contractor email and VPN
    • Intelligence service endpoint communications

  Tier 2 (Bulk collection, decryption opportunistic):
    • Healthcare record systems (HIPAA-regulated)
    • Legal/attorney-client privileged communications
    • Journalist sources and whistleblower channels

  Tier 3 (Archival, low priority):
    • General enterprise email
    • Consumer HTTPS (banking, e-commerce)

STORAGE ECONOMICS FOR ADVERSARY
────────────────────────────────
  At $0.01/GB (cold storage, 2026), storing 2.2 EB/year costs:
    $2.2 million/year — trivial for a nation-state intelligence budget.
  Over 7 years (now → 2033 CRQC): ~15 EB stored at ~$15 million total.
  A single CRQC then decrypts all of it.
""")

    # ── 3. HNDL scenarios ─────────────────────────────────────────────────────

    def hndl_scenarios(self) -> None:
        """5 concrete HNDL scenarios showing real-world impact."""
        print("\n" + "="*70)
        print("  HNDL CONCRETE SCENARIOS")
        print("="*70)

        scenarios = [
            {
                "id":          1,
                "title":       "Government Agency TLS (ECDHE-P256)",
                "description": "A federal agency uses TLS 1.3 with ECDHE-P256 key exchange.\n"
                               "    Nation-state adversary intercepts TLS handshakes on fiber backbone today.\n"
                               "    In 2033: Shor's Algorithm recovers ephemeral ECDH private keys.\n"
                               "    Result: All intercepted session keys decryptable → plaintext comms exposed.",
                "algorithm":   "ECDHE-P256",
                "sensitivity": "CLASSIFIED",
                "retention":   25,
                "risk":        "CRITICAL",
                "notes":       "Even TLS with PFS (Perfect Forward Secrecy) is NOT quantum-safe.\n"
                               "    PFS protects against classical key compromise, not quantum ECDLP attack.",
            },
            {
                "id":          2,
                "title":       "30-Year Government Bond Settlement",
                "description": "Treasury bond issuance encrypted with RSA-2048, settlement record\n"
                               "    retained for full bond lifecycle (30 years, maturing 2056).\n"
                               "    CRQC arrives ~2033: RSA private key recovered from public key.\n"
                               "    Result: Settlement amounts, counterparties, terms exposed; fraud possible.",
                "algorithm":   "RSA-2048",
                "sensitivity": "CONFIDENTIAL",
                "retention":   30,
                "risk":        "CRITICAL",
                "notes":       "Financial regulators require migration plan; SEC proposed rules in 2024.",
            },
            {
                "id":          3,
                "title":       "Medical Record Transfer (HIPAA)",
                "description": "Hospital EHR system transfers patient records with RSA-2048 encryption.\n"
                               "    HIPAA requires 6-year record retention minimum.\n"
                               "    Records created in 2026 must be protected until 2032.\n"
                               "    Moderate CRQC estimate: 2033. Risk window: 2032–2033+ overlap.",
                "algorithm":   "RSA-2048",
                "sensitivity": "CONFIDENTIAL",
                "retention":   6,
                "risk":        "MEDIUM",
                "notes":       "Mental health, HIV, substance abuse records may have longer retention.\n"
                               "    HHS HC3 issued quantum threat advisory in 2023.",
            },
            {
                "id":          4,
                "title":       "Military Communications (Classification: TOP SECRET)",
                "description": "Battlefield comms encrypted with ECDH-P384.\n"
                               "    Military operational security requires decades of protection.\n"
                               "    Adversary collecting today to decrypt in 2033.\n"
                               "    Result: Past operations, sources, methods, capabilities exposed.",
                "algorithm":   "ECDH-P384",
                "sensitivity": "CLASSIFIED",
                "retention":   30,
                "risk":        "CRITICAL",
                "notes":       "DoD mandates CNSA 2.0 compliance by 2030 for NSS.\n"
                               "    DISA STIGs being updated for PQC algorithms.",
            },
            {
                "id":          5,
                "title":       "Pharmaceutical IP — Drug Patent",
                "description": "Pharmaceutical firm transmits clinical trial data via TLS (ECDHE-P256).\n"
                               "    Drug patent protection: 20 years from filing (2026–2046).\n"
                               "    CRQC in 2033: formulations, dosages, synthesis routes exposed.\n"
                               "    Result: Competitor nations manufacture generic before patent expiry.",
                "algorithm":   "ECDHE-P256",
                "sensitivity": "CONFIDENTIAL",
                "retention":   20,
                "risk":        "CRITICAL",
                "notes":       "Estimated $20–50B in pharma IP at risk from nation-state HNDL programs.",
            },
        ]

        for s in scenarios:
            result = self.calculate_risk(
                s["sensitivity"], s["retention"], s["algorithm"]
            )
            print(f"\n  Scenario {s['id']}: {s['title']}")
            print(f"  {'─'*62}")
            print(f"    {s['description']}")
            print(f"    Algorithm:          {s['algorithm']}")
            print(f"    Data sensitivity:   {s['sensitivity']}")
            print(f"    Retention required: {s['retention']} years (until {CURRENT_YEAR + s['retention']})")
            print(f"    Years until CRQC:   {result.years_until_crqc} (moderate estimate: 2033)")
            print(f"    Exposed after CRQC: {result.exposed_after_crqc} years of data at risk")
            print(f"    RISK LEVEL:         {result.risk_score}")
            print(f"    Recommendation:     {result.recommendation}")
            print(f"    Note: {s['notes']}")

    # ── 4. Migration urgency matrix ───────────────────────────────────────────

    def migration_urgency_matrix(self) -> None:
        """
        2D matrix: urgency = f(data_sensitivity, retention_period).
        Using moderate CRQC estimate of 2033.
        """
        print("\n" + "="*70)
        print("  HNDL MIGRATION URGENCY MATRIX")
        print("  (Moderate CRQC estimate: 2033, current year: 2026)")
        print("="*70)

        sensitivities = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "CLASSIFIED"]
        retention_ranges = [
            ("1-3 years", 2),
            ("4-7 years", 5),
            ("8-15 years", 10),
            ("16-30 years", 20),
            ("30+ years", 35),
        ]

        algorithm = "ECDHE-P256"  # representative TLS standard

        print(f"\n  Algorithm: {algorithm}")
        print(f"  {'Retention':<16}", end="")
        for sens in sensitivities:
            print(f"  {sens:<15}", end="")
        print()
        print("  " + "─"*76)

        for label, years in retention_ranges:
            print(f"  {label:<16}", end="")
            for sens in sensitivities:
                r = self.calculate_risk(sens, years, algorithm)
                risk = r.risk_score
                print(f"  {risk:<15}", end="")
            print()

        print(f"""
  READING THE MATRIX
  ──────────────────
  CRITICAL: Intercept today → decrypt before protection period ends.
            Start PQC migration immediately. Every month of delay increases exposure.
  HIGH:     Likely to be exposed. Begin migration planning today.
  MEDIUM:   Possible exposure. Include in 2-year migration roadmap.
  LOW:      Unlikely to be exposed before CRQC. Standard migration timeline acceptable.
  NONE:     Algorithm already post-quantum safe. No action required.

  MOSCA INEQUALITY
  ────────────────
  If  (migration_years + retention_years) > years_until_CRQC:
      YOU ARE ALREADY LATE.

  Example: migration takes 3 years (X=3), data must be safe 10 years (Y=10),
           CRQC in 7 years (Z=7).  X + Y = 13 > Z = 7 → URGENT.
""")


def main():
    model = HNDLThreatModel()

    print("\n" + "#"*70)
    print("#  HARVEST NOW DECRYPT LATER (HNDL) THREAT MODEL")
    print("#  The quantum threat that is ACTIVE today, not a future problem")
    print("#"*70)

    model.estimate_intercepted_traffic()
    model.hndl_scenarios()
    model.migration_urgency_matrix()

    # Spot calculations
    print("\n  SPOT RISK CALCULATIONS")
    print("  " + "-"*65)
    test_cases = [
        ("CLASSIFIED",   25, "ECDHE-P256", 2033),
        ("CONFIDENTIAL", 10, "RSA-2048",   2033),
        ("INTERNAL",     3,  "AES-256",    2033),
        ("CLASSIFIED",   30, "ML-KEM-768", 2033),
        ("CONFIDENTIAL", 7,  "RSA-2048",   2029),  # optimistic CRQC
    ]
    print(f"  {'Sensitivity':<14} {'Retention':<10} {'Algorithm':<14} {'CRQC':<6} {'Risk':<10} {'Exposed (yrs)'}")
    print(f"  {'─'*72}")
    for sens, years, alg, crqc in test_cases:
        r = model.calculate_risk(sens, years, alg, crqc)
        print(f"  {sens:<14} {years:<10} {alg:<14} {crqc:<6} {r.risk_score:<10} {r.exposed_after_crqc}")
    print()

    print("  IMMEDIATE ACTIONS CHECKLIST")
    print("  " + "-"*65)
    actions = [
        "1. Build a Cryptographic Bill of Materials (CBOM) — inventory all algorithms in use",
        "2. Classify all data by sensitivity + retention period",
        "3. Identify all RSA/ECDH/ECDSA usage (TLS, code signing, VPN, SSH)",
        "4. Deploy hybrid TLS (classical + ML-KEM) immediately for CLASSIFIED data",
        "5. Plan certificate rotation to ML-DSA (FIPS 204) for authentication",
        "6. Brief leadership: HNDL means quantum threat risk starts NOW, not 2033",
        "7. Establish CRQC trigger criteria — know when to declare crypto emergency",
    ]
    for action in actions:
        print(f"  {action}")
    print()


if __name__ == "__main__":
    main()
