# Quantum Pulse Control & Optimal Control Platform

## Overview
Implements pulse-level quantum control using QuTiP-QOC with GRAPE, CRAB, and GOAT optimal control algorithms. Models qubit Hamiltonians, drive fields, and dissipation. Optimizes pulses for maximum gate fidelity under realistic hardware constraints.

## Role Target
Quantum Control Engineer / Quantum Hardware Architect

## Tech Stack
- **Core SDKs:** qiskit>=2.0.0, qutip>=5.0.0, numpy>=2.0.0, scipy>=1.14.0, matplotlib>=3.8.0, streamlit>=1.40.0
- **UI:** Streamlit + Plotly
- **Data:** No external dataset required
- **GitHub Reference:** https://github.com/qutip/qutip-qoc

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Transmon qubit Hamiltonian modeling with drive and coupling terms
- GRAPE optimal control for single and two-qubit gates
- CRAB pulse parameterization with frequency optimization
- Gate fidelity vs pulse duration tradeoff analysis
- Dissipation and decoherence (T1/T2) integration in control design
- Robust control: pulse optimization under parameter uncertainty
- Pulse visualization: amplitude, phase, and IQ quadrature display

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q13-control
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q13-control    # Show project details
qlab setup q13-control    # Install requirements
qlab data  q13-control    # Download Kaggle data
qlab run   q13-control    # Launch Streamlit UI
```
