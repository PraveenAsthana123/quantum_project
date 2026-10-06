# Hybrid Quantum-Classical Molecular Simulation Platform

## Overview
Simulates molecular electronic structure using hybrid VQE/QPE quantum algorithms. Starts with PySCF classical Hartree-Fock baseline, maps to qubit Hamiltonians via OpenFermion/Qiskit Nature, then runs VQE with various ansätze and validates with resource estimation for fault-tolerant QPE.

## Role Target
Quantum Algorithm Scientist / Quantum Chemistry Researcher

## Tech Stack
- **Core SDKs:** qiskit-nature>=0.8.0, openfermion>=1.8.0, numpy>=2.0.0, scipy>=1.14.0, pandas>=2.0.0, matplotlib>=3.8.0
- **UI:** Streamlit + Plotly
- **Data:** No external dataset required
- **GitHub Reference:** https://github.com/Qiskit/qiskit-nature

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Molecular Hamiltonian construction: HF, CCSD, FCI baselines
- Jordan-Wigner and Bravyi-Kitaev fermion-to-qubit mapping
- Active-space selection with CASSCF-style orbital selection
- VQE with UCCSD, hardware-efficient, and symmetry-preserving ansätze
- QPE resource estimation for fault-tolerant chemistry
- Molecular property calculation: bond lengths, dissociation curves
- Benchmark suite: H2, LiH, BeH2, H2O ground state energy comparison

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q20-chemistry
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q20-chemistry    # Show project details
qlab setup q20-chemistry    # Install requirements
qlab data  q20-chemistry    # Download Kaggle data
qlab run   q20-chemistry    # Launch Streamlit UI
```
