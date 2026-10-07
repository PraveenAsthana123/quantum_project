# Analog Quantum Computing — User Stories

## Overview
Quantum annealing, QUBO formulation, D-Wave style optimization, adiabatic evolution.

## User Stories

### US-01: optimization engineer — solve max-cut with quantum annealing
**As a** optimization engineer, **I want** solve max-cut with quantum annealing **so that** I get better solutions than classical.

**Acceptance Criteria:**
- [ ] QUBO formulated correctly
- [ ] Annealing schedule applied
- [ ] Result matches or beats classical

## Input / Process / Output

| Stage | Description |
|-------|-------------|
| **Input** | QUBO matrix Q, annealing schedule, num reads |
| **Process** | Adiabatic evolution, energy landscape search, thermal sampling |
| **Output** | Best bitstring solution, energy, success rate |
