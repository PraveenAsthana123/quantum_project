# Silicon Spin-Qubit Digital Twin & Auto-Tuning Platform

## Overview
Simulates silicon spin-qubit devices including quantum dot charge stability diagrams, spin state initialization, single-qubit rotation gates, exchange-coupled two-qubit gates, and charge noise. Includes an ML-based auto-tuning layer and real-time calibration dashboard.

## Role Target
Quantum System Architecture / Silicon-Spin Technology Architect

## Tech Stack
- **Core SDKs:** qiskit>=2.0.0, scqubits>=4.0.0, qutip>=5.0.0, numpy>=2.0.0, scipy>=1.14.0, scikit-learn>=1.3.0
- **UI:** Streamlit + Plotly
- **Data:** No external dataset required
- **GitHub Reference:** https://github.com/microsoft/qdarts

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Quantum dot charge stability diagram simulation with realistic noise
- Spin qubit initialization: thermal equilibration and spin-selective readout
- Single-qubit Rabi oscillation and EDSR gate simulation
- Exchange-coupled two-qubit gate (CZ/CPHASE) implementation
- Charge noise spectrum and dephasing time estimation
- ML-based auto-tuner for gate-voltage optimization
- Real-time calibration dashboard with drift alerts

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q10-silicon-spin
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q10-silicon-spin    # Show project details
qlab setup q10-silicon-spin    # Install requirements
qlab data  q10-silicon-spin    # Download Kaggle data
qlab run   q10-silicon-spin    # Launch Streamlit UI
```
