# Hybrid Optical Atomic Clock Digital Twin & Timescale Tower

## Overview
Simulates optical atomic clock performance including clock noise, Allan deviation, holdover prediction, timescale steering, and time transfer. Models both chip-scale atomic clocks and optical lattice clocks for PNT applications. Based on Kshana and allantools open-source foundations.

## Role Target
Quantum Technologies Specialist / Quantum PNT Architect

## Tech Stack
- **Core SDKs:** numpy>=2.0.0, scipy>=1.14.0, pandas>=2.0.0, matplotlib>=3.8.0, streamlit>=1.40.0, plotly>=5.0.0
- **UI:** Streamlit + Plotly
- **Data:** No external dataset required
- **GitHub Reference:** https://github.com/ashfordeOU/kshana

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Clock noise model: white phase, flicker phase, white frequency, flicker frequency, random walk
- Allan deviation (ADEV), overlapping ADEV, modified ADEV computation
- Clock holdover prediction: stability vs holdover duration
- Optical lattice clock vs CSAC comparison: frequency stability and accuracy
- Time transfer simulation: two-way satellite time and frequency transfer (TWSTFT)
- Timescale steering: weighted average from ensemble of clocks
- PNT application: position error vs clock stability for GPS-denied scenarios

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q27-clocks
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q27-clocks    # Show project details
qlab setup q27-clocks    # Install requirements
qlab data  q27-clocks    # Download Kaggle data
qlab run   q27-clocks    # Launch Streamlit UI
```
