# Circuit Cutting & Knitting — User Stories

## Overview
Quasi-probability decomposition, gate teleportation, sampling overhead reduction.

## User Stories

### US-01: researcher — cut a large circuit into smaller subcircuits
**As a** researcher, **I want** cut a large circuit into smaller subcircuits **so that** I can run on smaller QPUs.

**Acceptance Criteria:**
- [ ] Circuit cut at specified gates
- [ ] Sampling overhead computed
- [ ] Results knitted back correctly

## Input / Process / Output

| Stage | Description |
|-------|-------------|
| **Input** | Circuit with designated cut gates |
| **Process** | Quasi-probability decomposition, independent sampling, classical post-processing |
| **Output** | Reconstructed output, sampling overhead, fidelity |
