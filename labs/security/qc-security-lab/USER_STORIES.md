# Quantum Security Lab — User Stories

## Overview
Quantum cryptography protocols and attack simulations.

## User Stories
### US-01: cryptographer — simulate BB84 QKD
**As a** cryptographer, **I want** simulate BB84 QKD **so that** I understand photon-based key exchange.

**Acceptance Criteria:**
- [ ] BB84 runs end-to-end
- [ ] QBER computed
- [ ] Eavesdrop detection shown

### US-02: security researcher — run Grover's on AES-128
**As a** security researcher, **I want** run Grover's on AES-128 **so that** I understand quantum impact.

**Acceptance Criteria:**
- [ ] Grover reduces 128-bit to 64-bit
- [ ] Classical vs quantum steps compared
- [ ] Results visualized

### US-03: architect — get quantum threat assessment
**As a** architect, **I want** get quantum threat assessment **so that** I can plan PQC migration.

**Acceptance Criteria:**
- [ ] All vulnerable algorithms listed
- [ ] Risk levels assigned
- [ ] Migration recommendations provided

## Input / Process / Output

| Stage | Description |
|-------|-------------|
| **Input** | Quantum circuit parameters, key sizes, qubit counts |
| **Process** | BB84 simulation, Grover oracle, Shor factoring |
| **Output** | Key rate, QBER, attack complexity, migration recommendations |
