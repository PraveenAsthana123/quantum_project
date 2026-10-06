# Calibration-Aware Quantum Transpilation Control Tower

## Overview
Advanced quantum transpilation focused on noise-aware layout and routing. Uses real calibration data to assign qubits with lowest error rates, minimize SWAP count, and optimize scheduling for hardware fidelity. Benchmarks using MQT Bench standardized circuits.

## Role Target
Quantum Systems Architect / Transpilation Engineer

## Tech Stack
- **Core SDKs:** qiskit>=2.0.0, qiskit-aer>=0.17.0, numpy>=2.0.0, pandas>=2.0.0, networkx>=3.0.0, streamlit>=1.40.0
- **UI:** Streamlit + Plotly
- **Data:** gaborfodor/tsplib-benchmark
- **GitHub Reference:** https://github.com/cda-tum/mqt-bench

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Calibration-aware qubit layout: assign qubits by T1/T2/gate-error map
- SABRE routing with configurable heuristic weights
- SWAP count vs fidelity trade-off analysis across hardware topologies
- Noise-aware scheduling with pulse-level timing constraints
- Transpilation time vs circuit complexity scaling analysis
- Side-by-side logical vs physical circuit comparison dashboard

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
kaggle datasets download -d gaborfodor/tsplib-benchmark

# Run UI
qlab run q06-transpilation
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q06-transpilation    # Show project details
qlab setup q06-transpilation    # Install requirements
qlab data  q06-transpilation    # Download Kaggle data
qlab run   q06-transpilation    # Launch Streamlit UI
```
