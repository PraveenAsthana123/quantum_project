# Quantum IR Interoperability — User Stories

## Overview
OpenQASM 3.0, QIR, Quil format conversion and circuit equivalence checking.

## User Stories

### US-01: platform engineer — convert circuits between IR formats
**As a** platform engineer, **I want** convert circuits between IR formats **so that** I can run on any hardware.

**Acceptance Criteria:**
- [ ] OpenQASM→QIR conversion works
- [ ] Equivalence verified
- [ ] No information lost

## Input / Process / Output

| Stage | Description |
|-------|-------------|
| **Input** | Quantum circuit in source IR format |
| **Process** | AST parsing, gate mapping, format emission |
| **Output** | Circuit in target format, equivalence report |
