# NV-Center Quantum Magnetometry & Sensing Control Tower

## Overview
Implements NV-center quantum sensing for DC and AC magnetometry. Simulates ODMR spectroscopy, Ramsey and Hahn echo sequences, photon count statistics, and sensitivity estimation. Includes a noise spectroscopy module and spatial magnetic field imaging.

## Role Target
Quantum Sensing Scientist / Quantum Technologies Specialist

## Tech Stack
- **Core SDKs:** qutip>=5.0.0, numpy>=2.0.0, scipy>=1.14.0, pandas>=2.0.0, matplotlib>=3.8.0, streamlit>=1.40.0
- **UI:** Streamlit + Plotly
- **Data:** No external dataset required
- **GitHub Reference:** https://github.com/Ulm-IQO/qudi-core

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- NV center spin Hamiltonian: zero-field splitting, Zeeman, strain
- CW and pulsed ODMR simulation with fluorescence contrast
- Ramsey magnetometry: sensitivity vs coherence time analysis
- Hahn echo and CPMG dynamical decoupling for AC sensing
- Photon count statistics with shot noise and photon-number distribution
- Noise spectroscopy: filter function framework
- Spatial magnetic field imaging: 2D NV scan with field map reconstruction

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q25-sensing
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q25-sensing    # Show project details
qlab setup q25-sensing    # Install requirements
qlab data  q25-sensing    # Download Kaggle data
qlab run   q25-sensing    # Launch Streamlit UI
```
