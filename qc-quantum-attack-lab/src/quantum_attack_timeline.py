"""
Quantum Attack Timeline
========================
Timeline of quantum computing threat evolution — from Shor's paper (1994)
to projected CRQC arrival and the end of RSA/ECC era (2030–2035).

Uses ASCII visualization for terminal display.

References:
- NSA CNSA 2.0 (2022) — National Security Systems migration deadlines
- ODNI Annual Threat Assessment (2023) — CRQC risk framing
- IBM Quantum Roadmap (2023) — hardware milestones
- Google Quantum AI (2023) — error correction progress
- NIST FIPS 203/204/205 (2024) — standardization milestones

Educational use only — demonstrates defensive security concepts.
"""

import math
from typing import Optional


CURRENT_YEAR = 2026

# ─────────────────────────────────────────────────────────────────────────────
# Timeline Milestones
# ─────────────────────────────────────────────────────────────────────────────

MILESTONES = [
    # Past milestones (verified)
    {
        "year":     1994,
        "month":    None,
        "event":    "Shor's Algorithm published",
        "detail":   "Peter Shor publishes polynomial-time quantum factoring algorithm at Bell Labs. "
                    "Theoretical proof RSA, DH, ECC are vulnerable to quantum computers.",
        "category": "THEORETICAL",
        "past":     True,
    },
    {
        "year":     1996,
        "month":    None,
        "event":    "Grover's Algorithm published",
        "detail":   "Lov Grover publishes O(√N) quantum search. "
                    "Implies AES-128 security halved to 64-bit on quantum computer.",
        "category": "THEORETICAL",
        "past":     True,
    },
    {
        "year":     2016,
        "month":    "April",
        "event":    "NIST starts PQC standardization process",
        "detail":   "NIST issues call for PQC algorithm proposals (NISTIR 8105). "
                    "69 candidates submitted. Start of 8-year standardization process.",
        "category": "STANDARDS",
        "past":     True,
    },
    {
        "year":     2017,
        "month":    "February",
        "event":    "SHAttered — first practical SHA-1 collision",
        "detail":   "Stevens et al. (CWI + Google) demonstrate first practical SHA-1 collision. "
                    "Demonstrates that cryptographic deprecation timelines can be exceeded.",
        "category": "CLASSICAL BREAK",
        "past":     True,
    },
    {
        "year":     2019,
        "month":    "October",
        "event":    "Google claims quantum supremacy — Sycamore (53 qubits)",
        "detail":   "Google's 53-qubit Sycamore processor performs a specific sampling task "
                    "in 200 seconds vs estimated 10,000 years on classical computer. "
                    "No cryptographic relevance yet — too noisy, too few qubits.",
        "category": "HARDWARE",
        "past":     True,
    },
    {
        "year":     2021,
        "month":    "November",
        "event":    "IBM 127-qubit Eagle processor",
        "detail":   "IBM crosses 100-qubit threshold. Still NISQ era — no fault tolerance. "
                    "Demonstrates scaling pathway. IBM roadmap targets 100,000 qubits by 2033.",
        "category": "HARDWARE",
        "past":     True,
    },
    {
        "year":     2022,
        "month":    "November",
        "event":    "IBM 433-qubit Osprey + NSA CNSA 2.0",
        "detail":   "IBM reaches 433 qubits. Simultaneously: NSA publishes CNSA 2.0 — "
                    "all National Security Systems must complete PQC migration by 2030–2033.",
        "category": "HARDWARE + POLICY",
        "past":     True,
    },
    {
        "year":     2023,
        "month":    "December",
        "event":    "IBM 1121-qubit Condor",
        "detail":   "IBM's 1,121-qubit processor. Still NISQ — error rates prevent fault tolerance. "
                    "Simultaneously IBM releases Heron (133 qubits, lower error rate) — "
                    "quality over quantity trend begins.",
        "category": "HARDWARE",
        "past":     True,
    },
    {
        "year":     2024,
        "month":    "August",
        "event":    "NIST publishes FIPS 203/204/205",
        "detail":   "FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), FIPS 205 (SLH-DSA) finalized. "
                    "First official post-quantum cryptographic standards. "
                    "TLS 1.3 extensions for ML-KEM being finalized (RFC drafts).",
        "category": "STANDARDS",
        "past":     True,
    },
    {
        "year":     2024,
        "month":    "December",
        "event":    "Google Willow — below threshold error correction",
        "detail":   "Google Willow processor demonstrates error rates below fault-tolerance threshold "
                    "as qubit count increases — a historic milestone in QEC. "
                    "105 physical qubits. Path to CRQC now clearer but hardware gap still vast.",
        "category": "HARDWARE",
        "past":     True,
    },
    # Future milestones
    {
        "year":     2025,
        "month":    None,
        "event":    "FIPS 206 (FN-DSA / Falcon) expected",
        "detail":   "NIST expected to publish FIPS 206 for Falcon signature scheme "
                    "(NTRU lattice-based). Completes the initial PQC suite.",
        "category": "STANDARDS",
        "past":     False,
    },
    {
        "year":     2026,
        "month":    None,
        "event":    "TLS 1.3 + ML-KEM hybrid becoming mainstream",
        "detail":   "Major browsers/CDNs (Cloudflare, Google) deploying hybrid X25519+ML-KEM-768 "
                    "in TLS 1.3. IETF RFC for ML-KEM in TLS expected this year.",
        "category": "DEPLOYMENT",
        "past":     False,
    },
    {
        "year":     2027,
        "month":    None,
        "event":    "NSA CNSA 2.0 NSS deadline — Tier 1 systems",
        "detail":   "National Security Systems (NSS) must complete PQC migration for "
                    "software and firmware signing. Key exchange migration required for "
                    "highest-sensitivity networks.",
        "category": "POLICY DEADLINE",
        "past":     False,
    },
    {
        "year":     2029,
        "month":    None,
        "event":    "CRQC possible — optimistic estimate (10% confidence)",
        "detail":   "If hardware progress accelerates dramatically (breakthrough in error correction, "
                    "qubit connectivity, and control electronics): CRQC capable of breaking RSA-2048 "
                    "within 8 hours might be available. "
                    "Probability: 10% (ODNI framing). Not a planning assumption — a planning bound.",
        "category": "CRQC PROJECTION",
        "past":     False,
    },
    {
        "year":     2030,
        "month":    None,
        "event":    "NSA CNSA 2.0 final deadline — all NSS",
        "detail":   "ALL National Security Systems must complete PQC migration. "
                    "RSA/ECDSA/ECDH/DH no longer permitted for any NSS application.",
        "category": "POLICY DEADLINE",
        "past":     False,
    },
    {
        "year":     2033,
        "month":    None,
        "event":    "CRQC likely — moderate estimate (50% confidence)",
        "detail":   "Based on published IBM/Google/IonQ roadmaps, academic resource estimates, "
                    "and sustained investment trajectory: 50% probability of a CRQC capable of "
                    "breaking RSA-2048 in hours by 2033. "
                    "This is the PRIMARY planning assumption for enterprise migration.",
        "category": "CRQC PROJECTION",
        "past":     False,
    },
    {
        "year":     2035,
        "month":    None,
        "event":    "All RSA/ECC systems compromised — if no migration",
        "detail":   "If enterprises have not migrated off RSA/ECC by 2035, a CRQC is considered "
                    "available with high confidence (conservative 90% estimate). "
                    "HNDL data collected since 2020 becomes retroactively decryptable.",
        "category": "RISK HORIZON",
        "past":     False,
    },
    {
        "year":     2038,
        "month":    None,
        "event":    "CRQC near-certain — conservative estimate (90% confidence)",
        "detail":   "Even under conservative assumptions (significant QEC barriers remain), "
                    "90% probability of CRQC by 2038. Any system still using RSA/ECC is "
                    "fully compromised. No mitigation possible without prior migration.",
        "category": "CRQC PROJECTION",
        "past":     False,
    },
]


# ─────────────────────────────────────────────────────────────────────────────

class ThreatTimeline:
    """
    Quantum threat timeline with countdown and urgency calculations.
    """

    def get_current_threat_level(self) -> str:
        """
        Based on today's date vs milestones, classify current threat level.
        Categories: MONITORING / PREPARATION / URGENT / CRITICAL / CRISIS
        """
        if CURRENT_YEAR < 2026:
            return "MONITORING"
        elif CURRENT_YEAR < 2027:
            return "PREPARATION — CNSA 2.0 Tier 1 deadline approaching (2027)"
        elif CURRENT_YEAR < 2029:
            return "URGENT — within optimistic CRQC window; HNDL active"
        elif CURRENT_YEAR < 2033:
            return "CRITICAL — inside moderate CRQC window; migration required now"
        elif CURRENT_YEAR < 2035:
            return "CRISIS — CRQC likely exists; unmigrated systems at immediate risk"
        else:
            return "CRISIS / COMPROMISED — any RSA/ECC system presumed broken"

    def days_until_crqc(self, estimate: str = "moderate") -> int:
        """
        Countdown in days until estimated CRQC.
        estimate: 'optimistic' (2029), 'moderate' (2033), 'conservative' (2038)
        """
        targets = {"optimistic": 2029, "moderate": 2033, "conservative": 2038}
        crqc_year = targets.get(estimate, 2033)
        # Approximate: 365.25 days/year
        return max(0, int((crqc_year - CURRENT_YEAR) * 365.25))

    def migration_deadline(self, data_sensitivity: str, retention_years: int) -> dict:
        """
        Calculate when PQC migration MUST be complete given data sensitivity
        and retention period (Mosca inequality).

        Mosca: if (migration_years + retention_years) > years_until_CRQC → URGENT
        Typical enterprise migration: 3–5 years for full crypto stack.
        """
        years_until_crqc = 2033 - CURRENT_YEAR  # moderate estimate

        sensitivity_migration_overhead = {
            "CLASSIFIED":   1,  # less tolerance — faster required
            "CONFIDENTIAL": 2,
            "INTERNAL":     3,
            "PUBLIC":       5,
        }

        # Assume 3-year baseline migration cycle
        migration_years_needed = 3 + sensitivity_migration_overhead.get(
            data_sensitivity.upper(), 3
        )

        must_start_by   = CURRENT_YEAR + max(0, years_until_crqc - migration_years_needed - retention_years)
        must_complete_by = must_start_by + migration_years_needed

        already_late = must_start_by <= CURRENT_YEAR

        return {
            "data_sensitivity":      data_sensitivity,
            "retention_years":       retention_years,
            "migration_years_needed": migration_years_needed,
            "must_start_by":         must_start_by,
            "must_complete_by":      must_complete_by,
            "already_late":          already_late,
            "status":                "ALREADY LATE — start immediately" if already_late
                                     else f"Must start by {must_start_by}",
        }

    def print_timeline(self) -> None:
        """ASCII timeline visualization of quantum threat evolution."""
        print("\n" + "="*70)
        print("  QUANTUM COMPUTING THREAT TIMELINE  (1994 → 2038)")
        print("="*70)

        # Build year range
        min_year = 1994
        max_year = 2038
        span     = max_year - min_year
        width    = 60

        def year_to_pos(year: int) -> int:
            return int((year - min_year) / span * (width - 1))

        # Print scale
        print(f"\n  1994{'─'*56}2038")
        scale_line = [" "] * width
        for yr in range(1994, 2039, 4):
            pos = year_to_pos(yr)
            label = str(yr)[2:]
            if pos < width - 1:
                scale_line[pos] = "│"
        print("  " + "".join(scale_line))

        # Category symbols
        cat_symbols = {
            "THEORETICAL":      "T",
            "STANDARDS":        "S",
            "HARDWARE":         "H",
            "CLASSICAL BREAK":  "X",
            "DEPLOYMENT":       "D",
            "POLICY DEADLINE":  "P",
            "CRQC PROJECTION":  "Q",
            "RISK HORIZON":     "!",
            "HARDWARE + POLICY": "H",
        }

        # Print milestones on timeline
        print()
        for m in MILESTONES:
            yr  = m["year"]
            pos = year_to_pos(yr)
            sym = cat_symbols.get(m["category"], "•")
            past_str = "✓" if m["past"] else "→"

            line = [" "] * width
            line[pos] = sym

            # Marker for current year
            curr_pos = year_to_pos(CURRENT_YEAR)
            line[curr_pos] = "◆"

            indicator = past_str
            print(f"  {''.join(line)}  {yr} [{indicator}] {m['event'][:44]}")

        print(f"\n  Legend:  T=Theory  H=Hardware  S=Standards  P=Policy  Q=CRQC  ◆=Now ({CURRENT_YEAR})")
        print()

        # Print each milestone with detail
        print("  MILESTONE DETAILS")
        print("  " + "─"*65)
        for m in MILESTONES:
            past_label = "PAST" if m["past"] else "FUTURE"
            print(f"\n  [{past_label}] {m['year']} — {m['event']}")
            print(f"  Category: {m['category']}")
            print(f"  {m['detail']}")

    def print_countdown(self) -> None:
        """Print countdown to CRQC estimates."""
        print("\n" + "="*70)
        print(f"  CRQC COUNTDOWN (current year: {CURRENT_YEAR})")
        print("="*70)

        for estimate in ["optimistic", "moderate", "conservative"]:
            days = self.days_until_crqc(estimate)
            years = days / 365.25
            targets = {"optimistic": "2029 (10%)", "moderate": "2033 (50%)", "conservative": "2038 (90%)"}
            print(f"  {estimate.capitalize():<14}: {days:>7,} days  (~{years:.1f} years)  Target: {targets[estimate]}")

        print(f"\n  Current threat level: {self.get_current_threat_level()}")

    def print_migration_deadlines(self) -> None:
        """Print migration deadlines for different data types."""
        print("\n" + "="*70)
        print("  MIGRATION DEADLINE CALCULATOR (Mosca Inequality)")
        print("="*70)

        cases = [
            ("CLASSIFIED",   30, "30-year state secret"),
            ("CLASSIFIED",   10, "10-year intelligence operation"),
            ("CONFIDENTIAL", 20, "20-year pharma patent"),
            ("CONFIDENTIAL",  7, "7-year financial record"),
            ("INTERNAL",      3, "3-year corporate strategy"),
            ("PUBLIC",        1, "Short-lived public data"),
        ]

        print(f"\n  {'Sensitivity':<14} {'Retention':<10} {'Must Start':<12} {'Complete By':<12} {'Status'}")
        print(f"  {'─'*66}")
        for sens, years, label in cases:
            r = self.migration_deadline(sens, years)
            late_flag = " ←" if r["already_late"] else ""
            print(f"  {sens:<14} {years:<10} {r['must_start_by']:<12} {r['must_complete_by']:<12} "
                  f"{r['status'][:25]}{late_flag}")
        print()


def main():
    timeline = ThreatTimeline()

    print("\n" + "#"*70)
    print("#  QUANTUM COMPUTING ATTACK TIMELINE")
    print("#  Historical milestones → CRQC projection → migration deadlines")
    print("#"*70)

    timeline.print_timeline()
    timeline.print_countdown()
    timeline.print_migration_deadlines()

    print("  KEY TAKEAWAY")
    print("  " + "-"*65)
    print("  The quantum threat is not hypothetical — the timeline is compressed.")
    print("  HNDL is active NOW. Migration cycles take 3–7 years.")
    print("  Any system NOT migrating today may not complete before CRQC arrives.")
    print(f"  Current threat level: {timeline.get_current_threat_level()}")
    print()


if __name__ == "__main__":
    main()
