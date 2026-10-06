# Multi-Cloud Quantum Workload Router & QPU Control Tower

## Overview
An enterprise-grade quantum workload orchestration layer. Routes circuits to the best available backend (IBM simulators, local Aer, mock AWS/Azure) based on qubit count, topology, fidelity, queue depth, cost, and SLA requirements. Provides a unified job lifecycle dashboard.

## Role Target
Quantum Cloud Architect / Senior Quantum Software Platform Architect

## Tech Stack
- **Core SDKs:** qiskit>=2.0.0, qiskit-aer>=0.17.0, qiskit-ibm-runtime>=0.45.0, numpy>=2.0.0, pandas>=2.0.0, fastapi>=0.100.0
- **UI:** Streamlit + Plotly
- **Data:** No external dataset required
- **GitHub Reference:** https://github.com/Qiskit/qiskit-ibm-runtime

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Backend registry with fidelity, queue, cost, and topology metadata
- Routing policy engine: cheapest / fastest / highest-fidelity / hybrid
- Job lifecycle manager: submit → queue → execute → retrieve → store
- Fallback logic: QPU timeout → degrade to simulator with configurable SLA
- Multi-tenant job isolation with quota management
- Cost estimation per job across backend options
- REST API for programmatic backend selection and job submission

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q07-cloud-qpu
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q07-cloud-qpu    # Show project details
qlab setup q07-cloud-qpu    # Install requirements
qlab data  q07-cloud-qpu    # Download Kaggle data
qlab run   q07-cloud-qpu    # Launch Streamlit UI
```
