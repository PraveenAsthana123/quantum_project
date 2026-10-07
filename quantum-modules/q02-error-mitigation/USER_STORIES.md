# Quantum Error Mitigation — User Stories

## Overview
Zero-noise extrapolation (ZNE), clifford data regression (CDR), probabilistic error cancellation (PEC).

## User Stories

### US-01: quantum engineer — apply ZNE to reduce noise
**As a** quantum engineer, **I want** apply ZNE to reduce noise **so that** I get more accurate results.

**Acceptance Criteria:**
- [ ] 3 noise levels measured
- [ ] Extrapolated to 0-noise
- [ ] Error reduced by 40%+

### US-02: researcher — compare CDR vs ZNE
**As a** researcher, **I want** compare CDR vs ZNE **so that** I choose the right mitigation.

**Acceptance Criteria:**
- [ ] Both methods benchmarked
- [ ] Trade-offs documented
- [ ] Best method identified

## Input / Process / Output

| Stage | Description |
|-------|-------------|
| **Input** | Noisy circuit output at multiple noise levels |
| **Process** | Richardson extrapolation, Clifford training circuits, quasi-probability |
| **Output** | Mitigated expectation values, error reduction % |
