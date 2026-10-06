# NISQ Error-Mitigation Lab

## Overview
Implements and compares zero-noise extrapolation (ZNE), probabilistic error cancellation (PEC), readout error mitigation, symmetry verification, and dynamical decoupling on realistic noisy QAOA circuits. Uses Mitiq and Qiskit Aer noise models with real financial datasets to show mitigation impact.

## Role Target
Quantum Software Engineer / NISQ Algorithm Developer

## Tech Stack
- **Core SDKs:** qiskit>=2.0.0, qiskit-aer>=0.17.0, mitiq>=0.0.0, pennylane>=0.45.0, numpy>=2.0.0, pandas>=2.0.0
- **UI:** Streamlit + Plotly
- **Data:** mlg-ulb/creditcardfraud
- **GitHub Reference:** https://github.com/unitaryfund/mitiq

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Zero-Noise Extrapolation (ZNE) with Richardson and polynomial extrapolation
- Probabilistic Error Cancellation (PEC) with quasi-probability decomposition
- Readout error mitigation with assignment matrix calibration
- Dynamical decoupling (DD) sequence insertion and comparison
- Symmetry verification for detecting circuit errors
- Noise model builder: depolarizing, thermal relaxation, readout errors
- Mitigation effectiveness dashboard: raw vs mitigated expectation values

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
kaggle datasets download -d mlg-ulb/creditcardfraud

# Run UI
qlab run q02-error-mitigation
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q02-error-mitigation    # Show project details
qlab setup q02-error-mitigation    # Install requirements
qlab data  q02-error-mitigation    # Download Kaggle data
qlab run   q02-error-mitigation    # Launch Streamlit UI
```
