# Quantum Metrology — User Stories

## Overview
Quantum phase estimation, atomic clock precision, optical frequency standards.

## User Stories

### US-01: metrologist — implement quantum phase estimation
**As a** metrologist, **I want** implement quantum phase estimation **so that** I measure phase beyond classical limit.

**Acceptance Criteria:**
- [ ] Phase estimated to 0.001 precision
- [ ] Quantum Fisher information maximized
- [ ] Heisenberg scaling achieved

## Input / Process / Output

| Stage | Description |
|-------|-------------|
| **Input** | Unknown phase φ, N ancilla qubits, probe state |
| **Process** | QPE circuit, inverse QFT, classical post-processing |
| **Output** | Phase estimate, precision, Heisenberg scaling verification |
