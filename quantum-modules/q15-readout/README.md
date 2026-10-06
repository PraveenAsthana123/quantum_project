# Quantum Readout & Measurement Fidelity Platform

## Overview
Models the complete qubit readout chain from resonator response to state discrimination. Implements IQ-plane classification, assignment matrix calibration, readout error mitigation, and integration window optimization. Analyzes SNR, assignment fidelity, and measurement-induced transitions.

## Role Target
Quantum Hardware Engineer / Quantum Systems Architect

## Tech Stack
- **Core SDKs:** qiskit>=2.0.0, qutip>=5.0.0, numpy>=2.0.0, scipy>=1.14.0, scikit-learn>=1.3.0, streamlit>=1.40.0
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
- IQ-plane scatterplot simulation for |0⟩ and |1⟩ state distributions
- State discriminator: threshold, linear, and ML-based classifiers
- Assignment matrix calibration and readout error mitigation
- Integration window optimization for maximum SNR
- Single-shot readout fidelity vs photon number analysis
- Measurement-induced state transition (T1 during measurement) modeling
- Readout drift detection and recalibration triggers

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q15-readout
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q15-readout    # Show project details
qlab setup q15-readout    # Install requirements
qlab data  q15-readout    # Download Kaggle data
qlab run   q15-readout    # Launch Streamlit UI
```
