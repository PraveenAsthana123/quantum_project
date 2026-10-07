# Qubit Control Systems — User Stories

## Overview
Pulse-level programming, Rabi oscillations, AWG waveforms, IQ mixer calibration.

## User Stories

### US-01: control engineer — program qubit at pulse level
**As a** control engineer, **I want** program qubit at pulse level **so that** I can implement custom gates.

**Acceptance Criteria:**
- [ ] Gaussian pulse generated
- [ ] π-pulse time found from Rabi
- [ ] Gate fidelity > 99.9%

## Input / Process / Output

| Stage | Description |
|-------|-------------|
| **Input** | Drive frequency, pulse amplitude, duration |
| **Process** | Rabi oscillation simulation, pulse optimization, IQ waveform generation |
| **Output** | π-pulse time, gate fidelity, AWG sequence |
