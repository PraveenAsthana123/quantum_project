# Qubit Fabrication — User Stories

## User Stories

### US-01: Fabrication Engineer — Design Josephson Junction Parameters
**As a** fabrication engineer, **I want** to compute Josephson junction parameters from physical dimensions **so that** I can target a specific qubit frequency and anharmonicity.
**Acceptance Criteria:**
- EJ and EC are computed from junction area and capacitance
- EJ/EC ratio is verified to be in the transmon regime (> 20)
- Qubit frequency and anharmonicity are derived

### US-02: Process Engineer — Optimize Junction Fabrication Yield
**As a** process engineer, **I want** to track fabrication yield across wafers **so that** I can identify process drift and improve yield over time.
**Acceptance Criteria:**
- Yield percentage is computed per wafer
- Failing junction types are categorized
- Trend across batches is visible

### US-03: Device Physicist — Characterize Transmon Parameters
**As a** device physicist, **I want** to characterize transmon qubit parameters from fabricated junctions **so that** I can verify they meet design specifications.
**Acceptance Criteria:**
- EJ, EC, qubit frequency, and anharmonicity are computed
- Comparison to target values is shown
- Out-of-spec devices are flagged

### US-04: Materials Engineer — Evaluate Substrate Options
**As a** materials engineer, **I want** to compare substrate materials (silicon, sapphire) for qubit fabrication **so that** I can select the one with lowest dielectric loss.
**Acceptance Criteria:**
- Loss tangent for each substrate is listed
- Impact on T1 coherence time is estimated
- Recommended substrate is identified

### US-05: Yield Engineer — Analyze Wafer-Level Statistics
**As a** yield engineer, **I want** to compute wafer-level statistics for junction parameters **so that** I can assess uniformity and set process control limits.
**Acceptance Criteria:**
- Mean, std dev, and CV for EJ and EC are computed
- Control chart limits are set at ±3σ
- Out-of-control wafers are flagged

### US-06: Student — Understand Transmon Qubit Physics
**As a** student, **I want** to run a demo that computes transmon parameters from EJ and EC **so that** I can understand how fabrication choices determine qubit behavior.
**Acceptance Criteria:**
- Demo computes EJ, EC, ratio, frequency, and anharmonicity
- Physical interpretation of each parameter is printed
- All checks PASS with N/N PASS summary

### US-07: Quality Engineer — Validate Fabrication Data Pipeline
**As a** quality engineer, **I want** to validate that fabrication data is correctly parsed and stored **so that** downstream analysis is based on accurate measurements.
**Acceptance Criteria:**
- Data schema is validated against expected columns
- Out-of-range values are flagged
- Data completeness is checked

### US-08: Research Scientist — Explore EJ/EC Design Space
**As a** research scientist, **I want** to explore the EJ/EC design space **so that** I can understand the trade-off between anharmonicity and charge noise sensitivity.
**Acceptance Criteria:**
- EJ/EC ratio is swept over a range
- Qubit frequency and anharmonicity are plotted vs ratio
- Optimal design point is identified for gate fidelity

## Input / Process / Output

| Stage | Description |
|-------|-------------|
| Input | Junction area (µm²), critical current (nA), normal resistance (Ω), shunt capacitance (fF) |
| Process | Compute EJ from Ic; compute EC from capacitance; compute ratio; derive qubit frequency and anharmonicity |
| Output | EJ_GHz, EC_GHz, EJ/EC ratio, qubit frequency (GHz), anharmonicity (GHz), T1 estimate |
