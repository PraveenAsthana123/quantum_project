# Fault-Tolerant QC Resource & Architecture Platform

## Overview
Models fault-tolerant quantum computing requirements for practical algorithms. Covers logical circuit representation, QEC code selection (surface, color, Steane), physical qubit overhead estimation, Clifford+T decomposition, magic state distillation, and lattice surgery operations.

## Role Target
Fault-Tolerant QC Architect / QEC Lead

## Tech Stack
- **Core SDKs:** qiskit>=2.0.0, stim>=1.16.0, cirq>=1.7.0, numpy>=2.0.0, scipy>=1.14.0, streamlit>=1.40.0
- **UI:** Streamlit + Plotly
- **Data:** No external dataset required
- **GitHub Reference:** https://github.com/google/Qualtran

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Logical circuit construction and T-gate count analysis
- Surface code and color code threshold simulation with Stim
- Physical-to-logical qubit ratio estimation for target algorithms
- Clifford+T decomposition and T-depth optimization
- Magic state distillation overhead calculator
- Resource estimation dashboard: qubits vs error rate vs algorithm
- QEC comparison: surface code vs Steane vs color code tradeoffs

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q03-ftqc
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q03-ftqc    # Show project details
qlab setup q03-ftqc    # Install requirements
qlab data  q03-ftqc    # Download Kaggle data
qlab run   q03-ftqc    # Launch Streamlit UI
```
