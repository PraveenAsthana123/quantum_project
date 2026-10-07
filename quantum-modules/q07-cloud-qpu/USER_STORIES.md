# Cloud QPU Access — User Stories

## Overview
IBM Quantum, AWS Braket, Azure Quantum job submission, queue management, cost tracking.

## User Stories

### US-01: researcher — submit jobs to cloud QPUs
**As a** researcher, **I want** submit jobs to cloud QPUs **so that** I can run real quantum experiments.

**Acceptance Criteria:**
- [ ] Job submitted successfully
- [ ] Queue time estimated
- [ ] Results retrieved and parsed

## Input / Process / Output

| Stage | Description |
|-------|-------------|
| **Input** | Quantum circuit, shots, provider selection |
| **Process** | Circuit serialization, job submission, queue wait, result fetch |
| **Output** | Measurement counts, fidelity, cost, queue time |
