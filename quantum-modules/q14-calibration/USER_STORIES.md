# Quantum Gate Calibration — User Stories

## Overview
Randomized benchmarking (RB), gate set tomography (GST), drift tracking, recalibration.

## User Stories

### US-01: quantum engineer — run randomized benchmarking
**As a** quantum engineer, **I want** run randomized benchmarking **so that** I know my gate error rate.

**Acceptance Criteria:**
- [ ] RB decay curve fitted
- [ ] Error per Clifford extracted
- [ ] Drift over time tracked

## Input / Process / Output

| Stage | Description |
|-------|-------------|
| **Input** | Random Clifford circuits at multiple depths |
| **Process** | Average fidelity vs depth, exponential decay fit |
| **Output** | Error per Clifford, T1/T2, calibration schedule |
