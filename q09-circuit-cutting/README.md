# Automated Circuit Cutting & Reconstruction Platform

## Overview
Deep-focus project on automated quantum circuit cutting. Implements automatic cut finder, quasiprobability decomposition, subexperiment generation, shot allocation, and classical reconstruction with variance and error analysis. Includes a cost-effectiveness calculator for deciding when cutting is worthwhile.

## Role Target
Quantum Software Engineer / Circuit Architect

## Tech Stack
- **Core SDKs:** qiskit>=2.0.0, qiskit-aer>=0.17.0, mitiq>=0.0.0, numpy>=2.0.0, scipy>=1.14.0, streamlit>=1.40.0
- **UI:** Streamlit + Plotly
- **Data:** No external dataset required
- **GitHub Reference:** https://github.com/Qiskit/qiskit-addon-cutting

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Automatic cut placement optimizer minimizing sampling overhead
- Wire cut implementation: quasiprobability decomposition and reconstruction
- Gate cut implementation: LOCC decomposition
- Subexperiment generator with shot allocation strategy
- Reconstruction error vs shot count tradeoff analysis
- Cut economics calculator: is cutting cheaper than a larger QPU?
- Circuit topology visualizer showing cut locations

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q09-circuit-cutting
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q09-circuit-cutting    # Show project details
qlab setup q09-circuit-cutting    # Install requirements
qlab data  q09-circuit-cutting    # Download Kaggle data
qlab run   q09-circuit-cutting    # Launch Streamlit UI
```
