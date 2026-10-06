# Classical Security Lab — User Stories

Version: 1.0 | Date: 2026-10-06 | Lab: qc-classical-security-lab

---

## US-01 — CISO: Full Cryptographic Inventory Scan

**As a** CISO responsible for enterprise quantum readiness,
**I want to** scan the organization's full cryptographic asset inventory and get a count of quantum-vulnerable vs quantum-safe algorithms,
**So that** I can brief the board on the blast radius if cryptographically-relevant quantum computers arrive by 2030.

**Acceptance Criteria:**
- Inventory loaded from crypto_inventory.json (100 assets across 29 layers)
- Output includes: total_assets, vulnerable_count, quantum_safe_count, vulnerability_rate
- Per-algorithm breakdown table printed
- Scan completes in under 2 seconds

---

## US-02 — Security Architect: CBOM Generation

**As a** security architect building a quantum-risk supply chain management process,
**I want to** generate a CycloneDX-format Cryptographic Bill of Materials (CBOM) from the inventory,
**So that** software procurement and vendor management teams can flag products using quantum-vulnerable cryptography.

**Acceptance Criteria:**
- SBOMGenerator.generate_cbom_summary() returns a CycloneDX-compatible dict
- Output includes: format (CycloneDX 1.6), component count, vulnerable_pct, cnsa2_compliant_pct
- Serial number and generation timestamp included
- CBOM generation under 500 ms

---

## US-03 — GRC Analyst: Quantum Security Maturity Assessment

**As a** GRC analyst running a quarterly security maturity review,
**I want to** score each of the 29 security layers against the Quantum Security Maturity Model (L0–L5),
**So that** the security roadmap prioritizes the lowest-maturity, highest-risk layers.

**Acceptance Criteria:**
- MaturityModelAssessor.assess_layer() returns level_badge, average_score, effort_to_next_level
- 5 representative layers assessed and printed in a table
- Maturity levels range L0 (Unaware) through L5 (Optimized)
- Gaps and next-steps available on LayerMaturity object

---

## US-04 — DevSecOps Engineer: Critical Vulnerability Triage

**As a** DevSecOps engineer responding to a quantum security alert,
**I want to** see the top 10 highest-CVSS quantum vulnerability findings sorted by severity,
**So that** I can assign remediation tickets to the right engineering teams before the next sprint.

**Acceptance Criteria:**
- vulnerability_scan.csv loaded (200 findings)
- Top 10 findings with CVSS ≥ 7.5 displayed
- Columns: finding_id, algorithm, cvss_score, priority, system_name, pqc_replacement
- Output printable as plain text for JIRA/ServiceNow ticket descriptions

---

## US-05 — Security Architect: RSA-to-PQC Migration Planning

**As a** security architect tasked with migrating all RSA-2048 assets to ML-DSA-65,
**I want to** see a phased migration plan with effort estimates and deadlines,
**So that** I can allocate engineer time and communicate a credible timeline to the CISO.

**Acceptance Criteria:**
- Migration plan covers 6 phases: Discovery, Risk Assessment, Test, Hybrid, Cutover, Monitoring
- Each phase shows effort_days and engineer count
- Total calendar days and CNSA 2.0 deadline (2027-12-31) displayed
- HNDL risk of delay explicitly noted

---

## US-06 — Security Architect: Algorithm Policy Enforcement

**As a** security architect enforcing cryptographic policy across engineering teams,
**I want to** check whether a given algorithm is allowed for a specific use case (e.g. RSA-2048 for JWT signing),
**So that** developers receive an automated ALLOWED/BLOCKED decision with a reason and deadline before they merge code.

**Acceptance Criteria:**
- CryptoAgilityFramework.check_policy() returns allowed, reason, and deadline
- Policy covers: RSA-2048, ML-DSA-65, AES-128, SHA-1, ML-KEM-768
- BLOCKED decisions include a human-readable reason (e.g. "quantum_vulnerable; migrate by 2027")
- Policy check latency under 10 ms

---

## US-07 — GRC Analyst: Migration Progress Tracking

**As a** GRC analyst tracking PQC migration across 10 systems and 29 layers,
**I want to** see per-layer, per-system migration progress as a percentage,
**So that** the quarterly compliance report reflects real engineering progress rather than estimates.

**Acceptance Criteria:**
- migration_progress.csv contains 290 rows (29 layers × 10 systems)
- Columns: layer_id, system, current_algo, target_algo, completion_pct, deadline, status
- Status values: NOT_STARTED, STARTED, IN_PROGRESS, COMPLETED
- Data generated deterministically for audit reproducibility

---

## US-08 — DevSecOps Engineer: Crypto Agility Scoring

**As a** DevSecOps engineer evaluating whether a service is ready for PQC adoption,
**I want to** compute a quantitative crypto agility score (0–10) for a given system,
**So that** I can prioritize systems with low agility scores for architectural refactoring before the migration window closes.

**Acceptance Criteria:**
- CryptoAgilityFramework.compute_agility_score() returns agility_score, breakdown, rating, top_recommendation
- Score breakdown covers multiple dimensions (CBOM status, PQC readiness, migration plan, audit recency)
- Rating categories: Low / Medium / High / Excellent
- Top recommendation is a concrete next action, not a generic suggestion
