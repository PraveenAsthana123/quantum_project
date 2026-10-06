# Hardware-Aware Quantum Compiler & Validation Platform

## Overview
A full quantum compiler pipeline: logical circuit → layout mapping → SWAP routing → basis translation → optimization → hardware-native circuit. Validates correctness with unitary simulation and benchmarks compilation quality across noise levels, hardware topologies, and optimization levels.

## Role Target
Quantum Compiler Engineer / Quantum Software Platform Architect

## Tech Stack
- **Core SDKs:** qiskit>=2.0.0, qiskit-aer>=0.17.0, cirq>=1.7.0, numpy>=2.0.0, pandas>=2.0.0, streamlit>=1.40.0
- **UI:** Streamlit + Plotly
- **Data:** gaborfodor/tsplib-benchmark
- **GitHub Reference:** https://github.com/Qiskit/qiskit

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Qiskit PassManager pipeline: init → layout → routing → translation → optimization
- SWAP insertion comparison: BasicSwap vs SabreSwap vs StochasticSwap
- Hardware topology modeling: linear, grid, heavy-hex, custom
- Compilation quality metrics: CNOT count, depth, fidelity estimate
- Circuit equivalence verification via unitary simulation
- Optimization level comparison (O0 → O3) with trade-off analysis
- MQT Bench integration for standardized benchmark circuits

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
kaggle datasets download -d gaborfodor/tsplib-benchmark

# Run UI
qlab run q04-compiler
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q04-compiler    # Show project details
qlab setup q04-compiler    # Install requirements
qlab data  q04-compiler    # Download Kaggle data
qlab run   q04-compiler    # Launch Streamlit UI
```
