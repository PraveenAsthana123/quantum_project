# Quantum Transpilation — User Stories

## Overview
Mapping logical qubits to hardware topology, SWAP insertion, basis gate decomposition.

## User Stories

### US-01: hardware engineer — transpile circuit to linear chain topology
**As a** hardware engineer, **I want** transpile circuit to linear chain topology **so that** I can run on real hardware.

**Acceptance Criteria:**
- [ ] SWAP count minimized
- [ ] Basis gates respected
- [ ] Fidelity loss estimated

## Input / Process / Output

| Stage | Description |
|-------|-------------|
| **Input** | Logical circuit, hardware topology graph, native gate set |
| **Process** | Qubit routing (SABRE), SWAP insertion, basis decomposition |
| **Output** | Physical circuit, SWAP count, estimated fidelity |
