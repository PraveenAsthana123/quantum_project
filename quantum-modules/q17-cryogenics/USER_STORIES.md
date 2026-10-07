# Cryogenics — User Stories

## User Stories

### US-01: Systems Engineer — Compute Qubit Thermal Budget
**As a** systems engineer, **I want** to compute the total heat load for a multi-qubit system **so that** I can confirm the dilution refrigerator cooling power is sufficient.
**Acceptance Criteria:**
- Heat load per qubit is estimated
- Total heat load is compared to fridge cooling power at 20 mK
- Safety margin is reported in µW

### US-02: Cryogenics Engineer — Design Wiring Heat Intercepts
**As a** cryogenics engineer, **I want** to design heat intercept stages for qubit control wiring **so that** I can prevent excess heat from reaching the mixing chamber.
**Acceptance Criteria:**
- Heat load per coaxial line at each temperature stage is computed
- Attenuator and filter placement is recommended
- Total wiring heat load is within budget

### US-03: Hardware Engineer — Size the Dilution Refrigerator
**As a** hardware engineer, **I want** to select a dilution refrigerator with appropriate cooling power **so that** it can support a 50-qubit processor with margin.
**Acceptance Criteria:**
- Required cooling power is computed from qubit count and wiring
- Suitable commercial fridge models are identified
- Power margin at 20 mK is at least 2×

### US-04: Platform Architect — Plan Cryogenic Infrastructure Scale-Up
**As a** platform architect, **I want** to model how cooling requirements scale with qubit count **so that** I can plan infrastructure for 100+ qubit systems.
**Acceptance Criteria:**
- Cooling power vs qubit count curve is generated
- Crossover point where standard fridges are insufficient is identified
- Alternative architectures (modular cooling) are noted

### US-05: Safety Engineer — Verify Safe Operating Margins
**As a** safety engineer, **I want** to verify that all thermal stages operate within safe margins **so that** I can prevent quench events and hardware damage.
**Acceptance Criteria:**
- Each stage temperature is checked against operating limits
- Margin is computed for each stage
- Warning thresholds are defined

### US-06: Student — Understand Dilution Refrigerator Stages
**As a** student, **I want** to run a demo that walks through each fridge stage **so that** I can understand how millikelvin temperatures are achieved.
**Acceptance Criteria:**
- Demo shows all 5 temperature stages (300K, 50K, 4K, Still, MXC)
- Cooling power and heat load per stage are printed
- All checks PASS with N/N PASS summary

### US-07: Procurement Engineer — Compare Fridge Vendors
**As a** procurement engineer, **I want** to compare dilution refrigerator specifications from multiple vendors **so that** I can make an informed purchasing decision.
**Acceptance Criteria:**
- Specs table includes cooling power, base temperature, hold time, and cost
- At least 3 vendors are compared
- Recommended system is identified for 50-qubit use case

### US-08: Operations Engineer — Monitor Fridge Health Metrics
**As an** operations engineer, **I want** to monitor key fridge health metrics in real time **so that** I can detect drift before it causes qubit decoherence.
**Acceptance Criteria:**
- Key metrics (base temp, flow rate, still pressure) are defined
- Alert thresholds are set
- Log format for metrics is specified

## Input / Process / Output

| Stage | Description |
|-------|-------------|
| Input | Number of qubits, heat load per qubit (µW), fridge cooling power at 20 mK (µW) |
| Process | Compute total heat load; compare to cooling power; compute margin; check feasibility for each stage |
| Output | Thermal budget table, feasibility verdict, margin in µW, operating temperature |
