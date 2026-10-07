# Qubit Readout — User Stories

## User Stories

### US-01: Hardware Engineer — Calibrate Readout Fidelity
**As a** hardware engineer, **I want** to measure and calibrate qubit readout fidelity **so that** I can ensure state discrimination meets threshold for fault-tolerant operation.
**Acceptance Criteria:**
- System reports raw readout fidelity as a percentage
- Confusion matrix is computed from repeated measurement shots
- Fidelity improvement after mitigation is quantified

### US-02: Quantum Researcher — Classify IQ Plane Data
**As a** quantum researcher, **I want** to classify qubit states from IQ plane signals **so that** I can distinguish |0⟩ from |1⟩ with high accuracy.
**Acceptance Criteria:**
- IQ data for |0⟩ and |1⟩ is generated with realistic Gaussian noise
- Classification boundary is computed and visualized
- Misclassification rate is reported

### US-03: Systems Engineer — Apply Readout Error Mitigation
**As a** systems engineer, **I want** to apply confusion-matrix-based readout error mitigation **so that** corrected output probabilities are closer to ideal values.
**Acceptance Criteria:**
- Confusion matrix is measured or loaded from calibration data
- Matrix inversion is applied to raw measurement counts
- Mitigated fidelity exceeds raw fidelity by measurable margin

### US-04: Quantum Engineer — Optimize Readout Pulse Parameters
**As a** quantum engineer, **I want** to optimize readout resonator drive amplitude and duration **so that** I achieve maximum signal-to-noise ratio without inducing state transitions.
**Acceptance Criteria:**
- Pulse parameter sweep is simulated
- SNR is computed as a function of drive power
- Optimal parameters are identified and reported

### US-05: Algorithm Developer — Validate Circuit Output Distributions
**As an** algorithm developer, **I want** to verify that readout errors do not distort algorithm output distributions **so that** I can trust benchmark results.
**Acceptance Criteria:**
- Raw and mitigated distributions are compared for a reference circuit
- Total variation distance between distributions is computed
- Mitigation reduces TVD by at least 50%

### US-06: Platform Engineer — Generate Readout Calibration Data
**As a** platform engineer, **I want** to generate synthetic IQ calibration datasets **so that** I can test mitigation pipelines without access to real hardware.
**Acceptance Criteria:**
- 200-row IQ dataset with shot_id, signals, and state labels is produced
- Confusion matrix JSON is generated with realistic fidelity values
- Data is saved to the module data directory

### US-07: QA Engineer — Benchmark Readout Across Qubit Configurations
**As a** QA engineer, **I want** to benchmark readout performance across multiple qubit configurations **so that** I can identify underperforming qubits that require recalibration.
**Acceptance Criteria:**
- Readout fidelity is computed per qubit
- Qubits below threshold are flagged
- Summary report is exported to results directory

### US-08: Student — Understand IQ Plane and Readout Mechanics
**As a** student, **I want** to run a demo that simulates IQ plane readout **so that** I can understand how qubit state measurement works at the hardware level.
**Acceptance Criteria:**
- Demo runs with only numpy, no specialized quantum frameworks
- Output explains raw vs mitigated fidelity
- All tests PASS with final N/N PASS summary

## Input / Process / Output

| Stage | Description |
|-------|-------------|
| Input | Qubit prepared in |0⟩ or |1⟩ state; IQ signal corrupted by Gaussian noise; confusion matrix from calibration |
| Process | Simulate IQ plane measurements; classify states; compute confusion matrix; apply matrix-inversion mitigation |
| Output | Raw readout fidelity, mitigated fidelity, IQ separation metric, improvement delta |
