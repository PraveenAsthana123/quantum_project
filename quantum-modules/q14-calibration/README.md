# Autonomous Quantum Calibration & Drift Detection Tower

## Overview
Implements a full quantum calibration workflow: spectroscopy → Rabi → Ramsey → T1/T2 → gate calibration → validation. Detects parameter drift over time and triggers recalibration automatically. Stores calibration history and trends in a database.

## Role Target
Quantum Calibration Engineer / Quantum Systems Architect

## Tech Stack
- **Core SDKs:** qiskit>=2.0.0, qutip>=5.0.0, numpy>=2.0.0, scipy>=1.14.0, pandas>=2.0.0, streamlit>=1.40.0
- **UI:** Streamlit + Plotly
- **Data:** No external dataset required
- **GitHub Reference:** https://github.com/qiboteam/qibocal

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Qubit spectroscopy simulation: resonance frequency determination
- Rabi oscillation calibration: π-pulse amplitude and duration
- Ramsey interferometry: frequency detuning and T2* measurement
- T1 relaxation and T2 dephasing time characterization
- Gate error rate (RB-style) calibration sequence
- Drift detector: time-series monitoring with alert thresholds
- Calibration registry with history, trends, and recalibration triggers

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q14-calibration
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q14-calibration    # Show project details
qlab setup q14-calibration    # Install requirements
qlab data  q14-calibration    # Download Kaggle data
qlab run   q14-calibration    # Launch Streamlit UI
```
