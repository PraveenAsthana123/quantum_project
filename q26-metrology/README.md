# Quantum Metrology & Fisher-Information Precision Platform

## Overview
Implements quantum-enhanced parameter estimation using quantum Fisher information, Cramér-Rao bounds, and entangled probe states. Compares standard quantum limit (SQL) with Heisenberg limit (HL) scaling. Includes adaptive measurement protocols and quantum-classical precision comparison.

## Role Target
Quantum Metrology Scientist / Quantum Sensing Architect

## Tech Stack
- **Core SDKs:** pennylane>=0.45.0, numpy>=2.0.0, scipy>=1.14.0, pandas>=2.0.0, matplotlib>=3.8.0, streamlit>=1.40.0
- **UI:** Streamlit + Plotly
- **Data:** No external dataset required
- **GitHub Reference:** https://github.com/qucontrol/quanestimation

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Classical and Quantum Fisher Information computation
- Cramér-Rao and Quantum Cramér-Rao bound analysis
- Standard Quantum Limit vs Heisenberg Limit scaling comparison
- Entangled (NOON, GHZ, squeezed) probe state preparation
- Adaptive measurement: Bayesian updating and optimal measurement selection
- Phase estimation precision: separable vs entangled strategies
- Precision vs resource (N) scaling visualization with fit to SQL/HL

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q26-metrology
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q26-metrology    # Show project details
qlab setup q26-metrology    # Install requirements
qlab data  q26-metrology    # Download Kaggle data
qlab run   q26-metrology    # Launch Streamlit UI
```
