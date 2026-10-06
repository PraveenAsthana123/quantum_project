# Many-Body Quantum Simulation & Tensor-Network Platform

## Overview
Simulates strongly correlated quantum systems using exact diagonalization, tensor networks (DMRG), and neural quantum states. Studies Ising, Heisenberg, and Hubbard models on 1D/2D lattices. Includes a QPU-vs-classical solver router based on system size and entanglement.

## Role Target
Quantum Research Scientist / Many-Body Physics Specialist

## Tech Stack
- **Core SDKs:** pennylane>=0.45.0, netket>=3.20.0, numpy>=2.0.0, scipy>=1.14.0, matplotlib>=3.8.0, streamlit>=1.40.0
- **UI:** Streamlit + Plotly
- **Data:** No external dataset required
- **GitHub Reference:** https://github.com/tenpy/tenpy

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Ising and Heisenberg spin chain simulation with exact diagonalization
- Hubbard model ground state via DMRG with entanglement entropy
- Neural Quantum States (NQS) with NetKet for variational optimization
- Quantum phase transition detection: order parameter and correlation functions
- Entanglement entropy scaling and area vs volume law classification
- Solver router: ED (n<20) → DMRG (1D) → NQS (2D) → QPU (NISQ)
- Phase diagram generator for parameter-space scans

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q21-many-body
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q21-many-body    # Show project details
qlab setup q21-many-body    # Install requirements
qlab data  q21-many-body    # Download Kaggle data
qlab run   q21-many-body    # Launch Streamlit UI
```
