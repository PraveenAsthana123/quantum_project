# Control Tower — User Stories

## Overview
Quantum security observability and HNDL risk monitoring.

## User Stories
### US-01: CISO — view all 29 crypto layer statuses
**As a** CISO, **I want** view all 29 crypto layer statuses **so that** I can track PQC migration progress.

**Acceptance Criteria:**
- [ ] Dashboard shows all 29 layers
- [ ] Each layer shows current+target algo
- [ ] Progress % per layer

### US-02: Security ops — get HNDL risk score per system
**As a** Security ops, **I want** get HNDL risk score per system **so that** I can prioritize migrations.

**Acceptance Criteria:**
- [ ] Risk = sensitivity × months_to_migrate
- [ ] CRITICAL/HIGH/MEDIUM/LOW classification
- [ ] Top 5 risks shown

### US-03: Compliance officer — see CNSA 2.0 readiness
**As a** Compliance officer, **I want** see CNSA 2.0 readiness **so that** I can report to regulators.

**Acceptance Criteria:**
- [ ] Per-protocol deadline status
- [ ] Overall readiness % shown
- [ ] Gap analysis available

## Input / Process / Output

| Stage | Description |
|-------|-------------|
| **Input** | 29 crypto layer definitions, system sensitivity scores |
| **Process** | HNDL formula, status aggregation, vendor scoring |
| **Output** | Health score 0-100, risk register, CISO report |
