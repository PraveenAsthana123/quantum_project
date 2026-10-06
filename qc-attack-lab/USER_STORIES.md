# Attack Lab — User Stories

Version: 1.0 | Date: 2026-10-06 | Lab: qc-attack-lab

---

## US-01 — Red Team: Quantum Threat Scenario Modeling

**As a** red team engineer modeling future adversarial capabilities,
**I want to** generate a catalog of 200 quantum attack scenarios with severity, qubit requirements, and feasibility year,
**So that** I can brief defensive teams on the full threat surface before CRQC hardware is publicly available.

**Acceptance Criteria:**
- attack_scenarios.csv contains 200 rows covering shor_rsa, shor_ecdsa, grover_aes, harvest_decrypt, intercept_resend, side_channel, grover_hash
- Each row includes: attack_id, attack_type, target_algorithm, n_qubits_required, success_probability, severity, year_feasible
- Severity distribution spans CRITICAL, HIGH, MEDIUM, LOW
- Data generation is reproducible (seeded)

---

## US-02 — Threat Intelligence Analyst: Shor's Algorithm Threat Assessment

**As a** threat intelligence analyst tracking quantum hardware advances,
**I want to** see closed-form resource estimates for Shor's algorithm breaking RSA-2048 (logical qubits, physical qubits, T-gates, runtime),
**So that** I can publish a credible timeline report with specific hardware thresholds that trigger mandatory migration.

**Acceptance Criteria:**
- Logical qubits for RSA-2048 reported as 4099 (Beauregard 2003 model: 2n+3)
- Physical qubits estimated with surface code overhead (code distance d=27, physical ~2.99M)
- T-gate count displayed in scientific notation
- Estimated runtime in days under CRQC model (0.001 physical error rate)
- Feasibility year range cited (2032–2037)

---

## US-03 — CISO: Grover's Attack Urgency Triage

**As a** CISO deciding whether to mandate AES-256 across the enterprise,
**I want to** see the effective post-quantum security bits of AES-128 and AES-256 under Grover's attack,
**So that** I can communicate why AES-128 must be replaced before 2027 while AES-256 remains safe.

**Acceptance Criteria:**
- AES-128: 64 effective post-quantum bits (severity: HIGH, feasibility: 2035)
- AES-256: 128 effective post-quantum bits (severity: LOW, feasibility: 2060+)
- Oracle call count displayed for each key size
- Migration recommendation printed: AES-128 → AES-256 by 2027

---

## US-04 — Threat Intelligence Analyst: HNDL Risk Quantification

**As a** threat intelligence analyst advising a financial institution,
**I want to** see which protocols are currently being harvested and when the decryption window opens,
**So that** the CISO can justify emergency deployment of PQC-enabled TLS before the CRQC feasibility window.

**Acceptance Criteria:**
- HNDL table covers TLS 1.3 (RSA), TLS 1.3 (ECDSA), VPN (DH-2048), S/MIME (RSA-4096), PQ-TLS
- Columns: harvest_year, decrypt_year, exposure_years, risk_level
- PQ-TLS (ML-KEM-768) shows "Never" decrypt year and NONE risk
- Key insight text printed: data harvested today is at risk from 2030

---

## US-05 — CISO: Full Attack Matrix Overview

**As a** CISO preparing a board-level quantum risk briefing,
**I want to** see a single table covering all attack types, their targets, feasibility year, and recommended defense,
**So that** the board can approve the security roadmap with concrete defensive actions mapped to each threat.

**Acceptance Criteria:**
- Attack matrix covers: shor_rsa, shor_ecdsa, grover_aes, harvest_decrypt, intercept_resend, side_channel, grover_hash
- Each row includes: attack, target, feasibility_year, defense_recommendation
- Defense recommendations reference specific NIST standards (FIPS 204, CNSA 2.0)
- Table printable as plain text for board presentation

---

## US-06 — Red Team: Defense Effectiveness Benchmarking

**As a** red team engineer evaluating defensive controls,
**I want to** see the average effectiveness, cost, and implementation time for each defense measure across 300 defense log records,
**So that** I can recommend the highest-ROI defenses for the quarterly security budget.

**Acceptance Criteria:**
- defense_log.csv contains 300 rows linking scenarios to applied defenses
- Columns: defense_applied, defense_effectiveness_pct, cost_usd, implementation_days, status
- Demo Step 6 prints defenses sorted by avg_coverage_pct descending
- Cost and implementation days averaged across all records for each defense

---

## US-07 — Vulnerability Researcher: Side-Channel Attack on PQC

**As a** vulnerability researcher studying PQC implementation weaknesses,
**I want to** understand that side-channel attacks on ML-DSA-65 implementations remain viable even though the algorithm itself is quantum-safe,
**So that** I can publish a research note distinguishing algorithm-level security from implementation-level security.

**Acceptance Criteria:**
- side_channel attack type included in attack scenarios with target_algorithm=ML-DSA-65
- n_qubits_required=0 (no quantum hardware needed)
- Success probability range 1–15% (difficult but feasible with physical access)
- Defense recommendation: constant-time implementation; hardware security module

---

## US-08 — Vulnerability Researcher: Attack Dataset for ML-Based Threat Detection

**As a** vulnerability researcher training a machine learning threat detection model,
**I want to** use the 200-row attack scenarios dataset with realistic feature distributions (severity, qubit counts, time estimates, success probabilities),
**So that** the trained model can classify new threat intelligence reports by quantum attack type and severity.

**Acceptance Criteria:**
- attack_scenarios.csv has well-distributed values across all attack types
- success_probability follows realistic ranges per attack type (shor_rsa: 0.85–0.99)
- n_qubits_required spans 0 (side_channel) to 8195 (shor_rsa RSA-4096)
- year_feasible spans 2024 (intercept_resend) to 2060 (grover_hash)
- Dataset seeded for reproducible ML experiments
