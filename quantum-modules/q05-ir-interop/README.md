# Quantum IR & Interoperability Gateway

## Overview
A multi-SDK quantum circuit conversion gateway supporting Qiskit → OpenQASM 3 → Cirq → QIR round-trips. Validates circuit equivalence after conversion and provides a unified API to submit circuits to different backends regardless of native SDK.

## Role Target
Principal Developer Platform Architect / Quantum Platform Architect

## Tech Stack
- **Core SDKs:** qiskit>=2.0.0, cirq>=1.7.0, numpy>=2.0.0, streamlit>=1.40.0, plotly>=5.0.0
- **UI:** Streamlit + Plotly
- **Data:** No external dataset required
- **GitHub Reference:** https://github.com/openqasm/openqasm

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Qiskit ↔ OpenQASM 3.x circuit serialization and parsing
- Qiskit ↔ Cirq conversion with gate-set reconciliation
- Circuit equivalence verification after round-trip conversion
- Unified backend API: submit same circuit to Qiskit Aer or Cirq simulators
- IR format comparison dashboard: gate count, depth, fidelity across formats
- OpenQASM 3 advanced features: classical control, pulse grammar stubs

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q05-ir-interop
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q05-ir-interop    # Show project details
qlab setup q05-ir-interop    # Install requirements
qlab data  q05-ir-interop    # Download Kaggle data
qlab run   q05-ir-interop    # Launch Streamlit UI
```
