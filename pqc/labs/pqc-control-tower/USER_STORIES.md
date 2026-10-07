# PQC Control Tower — User Stories

**Version:** 1.0  
**Date:** 2026-10-06  
**Lab:** pqc-control-tower  

---

## Overview

The PQC Control Tower is a centralized monitoring and reporting platform for enterprise Post-Quantum Cryptography (PQC) migration.
It aggregates status across all 29 cryptographic layers, provides HNDL risk scoring, tracks CNSA 2.0 compliance, and generates executive-level reports.

These user stories reflect real CISO, security operations, and compliance needs aligned with CNSA 2.0 and NIST SP 800-208 migration guidance.

---

## US-01: Unified PQC Status Dashboard

**As a** Chief Information Security Officer (CISO),  
**I want** a single dashboard showing all 29 cryptographic layers' PQC migration status  
**so that** I have a single source of truth for board reporting and can identify at a glance where the organization is blocked.

### Acceptance Criteria
- [ ] The dashboard displays all 29 layers with: layer name, owner, current algorithm, target PQC algorithm, migration status, and progress percentage
- [ ] Layers are colour-coded by status: not-started (red), planning (orange), in-progress (yellow), testing (blue), done (green)
- [ ] A headline metric shows overall PQC health score as a percentage of layers at `testing` or `done`
- [ ] Dashboard data refreshes from `data/layer_status.csv` without a code change
- [ ] Layer status can be queried via API endpoint `GET /api/layers`
- [ ] The dashboard loads in under 3 seconds

---

## US-02: Real-Time HNDL Risk Scoring

**As a** Security Operations Engineer,  
**I want** real-time HNDL (Harvest Now, Decrypt Later) risk scores per system  
**so that** I can triage and escalate the systems most likely to be targeted by nation-state adversaries collecting encrypted traffic today.

### Acceptance Criteria
- [ ] Each system in `data/hndl_risk.csv` has a computed `hndl_risk_score = sensitivity_score × time_to_migration_months`
- [ ] Systems are classified as CRITICAL (score ≥ 60), HIGH (40–59), MEDIUM (20–39), LOW (< 20)
- [ ] The top 5 highest-risk systems are surfaced in every executive report
- [ ] Risk scores update automatically when migration timelines or sensitivity classifications change
- [ ] HNDL risk can be queried via API endpoint `GET /api/hndl-risk`
- [ ] The system flags any CRITICAL asset that has migration status `not-started`

---

## US-03: CNSA 2.0 Readiness by Protocol

**As a** Compliance Officer,  
**I want** CNSA 2.0 readiness percentages broken down per protocol (TLS, PKI, SSH, JWT, Code Signing)  
**so that** I can accurately report migration readiness to NSA, external auditors, and the board.

### Acceptance Criteria
- [ ] Per-protocol readiness is computed as `(layers_at_pqc_primary / total_protocol_layers) × 100`
- [ ] A `cnsa_2030_on_track` boolean flag is derived per protocol based on current pace vs. 2030 deadline
- [ ] The control tower generates a compliance report in JSON at `results/control_tower_report.json`
- [ ] A trend chart shows monthly readiness improvement if historical snapshots are available
- [ ] Compliance percentage is queryable via `GET /api/compliance/{protocol}`
- [ ] Any protocol falling below 20% readiness with < 24 months to deadline triggers an alert

---

## US-04: Threat Intelligence on HNDL Collection Activity

**As a** Security Architect,  
**I want** threat intelligence on which advanced persistent threat (APT) groups are known to collect encrypted traffic for future quantum decryption  
**so that** I can prioritize PQC migration for the protocols and data types they are most likely targeting.

### Acceptance Criteria
- [ ] The control tower maintains a structured threat intelligence feed with at least 5 threat actor entries
- [ ] Each entry includes: actor name, attributed nation-state, target protocols, HNDL-relevant data types, and confidence level
- [ ] Threat intel is linked to the systems in the CBOM that handle the targeted data types
- [ ] Intel entries are timestamped and marked with the source (e.g., CISA advisory, NSA guidance)
- [ ] The threat intel feed is queryable via `GET /api/threat-intel`
- [ ] New intel items can be added without redeploying the control tower

---

## US-05: Vendor Quantum Readiness Scoring

**As a** Vendor Manager,  
**I want** quantum readiness scores for all 10 major cryptographic vendors and library providers  
**so that** I can pressure vendors lagging behind CNSA 2.0 timelines and make informed decisions about library upgrades.

### Acceptance Criteria
- [ ] The control tower tracks quantum readiness for at least 10 vendors: OpenSSL, BouncyCastle, AWS KMS, Azure Key Vault, HSM vendors (Thales, Entrust, Utimaco), GnuTLS, liboqs, NSS
- [ ] Each vendor entry includes: readiness score (0-100), supported PQC algorithms, FIPS 140-3 status, and next release timeline
- [ ] Vendors are ranked by readiness score with a traffic-light RAG status
- [ ] Vendor data is stored in JSON and queryable via `GET /api/vendors`
- [ ] The system flags vendors blocking a CRITICAL-risk migration path
- [ ] Vendor scores update monthly (manual input workflow acceptable at this stage)

---

## US-06: HNDL Risk Formula and Scoring Engine

**As a** Risk Manager,  
**I want** the HNDL risk formula `hndl_risk_score = sensitivity_score × time_to_migration_months` to produce an auditable, traceable score for each system  
**so that** I can defend migration prioritization decisions to auditors and leadership using quantified, reproducible risk calculations.

### Acceptance Criteria
- [ ] `sensitivity_score` is an integer 1–10 derived from data classification (PUBLIC=1, INTERNAL=4, CONFIDENTIAL=7, TOP_SECRET=10)
- [ ] `time_to_migration_months` is derived from the current phase and estimated completion date in the CBOM
- [ ] The resulting score is stored alongside the formula inputs in `data/hndl_risk.csv`
- [ ] Risk level thresholds (CRITICAL/HIGH/MEDIUM/LOW) are configuration-driven and auditable
- [ ] The scoring engine can re-run in under 5 seconds across all 20 systems
- [ ] An audit log records each score recalculation with timestamp and input values

---

## US-07: CISO Executive Summary Report

**As an** Executive (CISO / CTO / Board Member),  
**I want** a one-page CISO executive summary with an overall PQC health score, top risks, and current phase status  
**so that** I can communicate quantum migration progress to the board without reading technical documentation.

### Acceptance Criteria
- [ ] The report contains: overall PQC health score (0-100), layers done/in-progress/not-started counts, critical HNDL systems count, CNSA 2030 on-track boolean, and top 3 risks
- [ ] Report is generated in JSON at `results/control_tower_report.json` and is human-readable
- [ ] The report includes a one-line executive recommendation based on current state
- [ ] Report generation completes in under 10 seconds
- [ ] The report is queryable via `GET /api/executive-summary`
- [ ] All metrics in the report link back to the underlying data source for traceability

---

## US-08: Layer Status and HNDL Risk API

**As a** Developer or Security Automation Engineer,  
**I want** clean API endpoints to query layer PQC status and HNDL risk scores programmatically  
**so that** I can integrate control tower data into SIEM dashboards, CI/CD pipelines, and automated compliance workflows.

### Acceptance Criteria
- [ ] `GET /api/layers` returns all 29 layers with full status fields as JSON
- [ ] `GET /api/layers/{id}` returns a single layer by ID
- [ ] `GET /api/hndl-risk` returns all systems with risk scores, sorted by `hndl_risk_score` descending
- [ ] `GET /api/executive-summary` returns the current CISO report JSON
- [ ] All endpoints return HTTP 200 with valid JSON; 404 for unknown IDs; 500 with error detail on failure
- [ ] API responses include a `last_updated` timestamp field
- [ ] The API is documented in the project README with example curl commands

---

*End of User Stories — pqc-control-tower v1.0*
