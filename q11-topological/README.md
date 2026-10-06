# Topological QC Digital Twin: Anyons & Braiding

## Overview
Simulates topological quantum computation using Fibonacci anyon models and Majorana zero modes. Implements fusion rules, braid sequences, and logical gate construction through topological operations. Provides a comparison between topological and conventional gate error rates.

## Role Target
Quantum Research Scientist / FTQC Architecture Lead

## Tech Stack
- **Core SDKs:** qiskit>=2.0.0, stim>=1.16.0, numpy>=2.0.0, scipy>=1.14.0, streamlit>=1.40.0, plotly>=5.0.0
- **UI:** Streamlit + Plotly
- **Data:** No external dataset required
- **GitHub Reference:** https://github.com/Constantine-Quantum-Tech/tqsim

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Fibonacci anyon fusion state space construction
- Braid sequence compiler: logical gate → braid word
- Topological gate fidelity vs conventional gate fidelity comparison
- Majorana zero mode simulation in 1D Kitaev chain
- Braiding protocol animator with step-by-step visualization
- Topological protection factor analysis vs noise level
- Hybrid topological/conventional circuit design

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q11-topological
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q11-topological    # Show project details
qlab setup q11-topological    # Install requirements
qlab data  q11-topological    # Download Kaggle data
qlab run   q11-topological    # Launch Streamlit UI
```
