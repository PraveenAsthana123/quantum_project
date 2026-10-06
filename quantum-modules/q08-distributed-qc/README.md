# Distributed Multi-QPU Quantum Computing Platform

## Overview
Implements circuit knitting to partition a large quantum circuit across multiple smaller QPUs. Uses Qiskit's circuit-cutting addon for wire and gate cuts, executes subcircuits independently, and reconstructs the full result classically. Demonstrates distributed quantum computing architecture.

## Role Target
Distributed Quantum Computing Architect

## Tech Stack
- **Core SDKs:** qiskit>=2.0.0, qiskit-aer>=0.17.0, numpy>=2.0.0, pandas>=2.0.0, streamlit>=1.40.0, plotly>=5.0.0
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
- Circuit partitioning: automatic and manual cut placement
- Wire cut and gate cut implementation with quasiprobability decomposition
- Subcircuit execution on independent simulators (simulating separate QPUs)
- Classical reconstruction of full circuit expectation values
- Sampling overhead vs cut count analysis
- Shot budget allocation across subcircuits
- Distributed execution timeline visualization

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q08-distributed-qc
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q08-distributed-qc    # Show project details
qlab setup q08-distributed-qc    # Install requirements
qlab data  q08-distributed-qc    # Download Kaggle data
qlab run   q08-distributed-qc    # Launch Streamlit UI
```
