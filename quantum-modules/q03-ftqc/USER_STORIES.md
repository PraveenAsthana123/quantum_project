# Fault-Tolerant Quantum Computing — User Stories

## Overview
Surface codes, logical qubits, syndrome measurement, error correction thresholds.

## User Stories

### US-01: quantum engineer — implement surface code d=3
**As a** quantum engineer, **I want** implement surface code d=3 **so that** I protect logical qubit from errors.

**Acceptance Criteria:**
- [ ] 9 physical qubits per logical
- [ ] Syndrome measured correctly
- [ ] Error below threshold corrected

## Input / Process / Output

| Stage | Description |
|-------|-------------|
| **Input** | Physical qubit error rates, code distance d |
| **Process** | Surface code encoding, syndrome extraction, correction |
| **Output** | Logical error rate, physical qubit overhead, code cycles |
