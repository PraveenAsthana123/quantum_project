# Quantum Many-Body Physics — User Stories

## Overview
Transverse-field Ising model, Hubbard model, quantum phase transitions, entanglement entropy.

## User Stories

### US-01: physicist — simulate Ising model ground state
**As a** physicist, **I want** simulate Ising model ground state **so that** I study quantum phase transitions.

**Acceptance Criteria:**
- [ ] Ground energy computed
- [ ] Phase transition at h/J=1 found
- [ ] Entanglement entropy peaks at transition

## Input / Process / Output

| Stage | Description |
|-------|-------------|
| **Input** | Hamiltonian parameters J, h, system size L |
| **Process** | Exact diagonalization (ED), DMRG for larger systems |
| **Output** | Ground state energy, phase diagram, entanglement entropy |
