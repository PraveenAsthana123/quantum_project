# Quantum Memory Digital Twin & Fidelity Control Tower

## Overview
Models quantum memory systems for both network quantum memories (photon storage for repeaters) and processor quantum memories (QPU state storage for multi-QPU coordination). Simulates storage fidelity, coherence decay, write/read efficiency, and multi-mode scheduling.

## Role Target
Quantum Hardware Architect / Quantum Network Engineer

## Tech Stack
- **Core SDKs:** qutip>=5.0.0, numpy>=2.0.0, scipy>=1.14.0, pandas>=2.0.0, streamlit>=1.40.0, plotly>=5.0.0
- **UI:** Streamlit + Plotly
- **Data:** No external dataset required
- **GitHub Reference:** See README for references

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Spin-wave quantum memory: AFC protocol simulation
- Coherence decay modeling: T1/T2 for atomic ensemble memories
- Write and read efficiency vs bandwidth tradeoff
- Multi-mode memory capacity: temporal vs spectral modes
- Memory scheduler: FIFO, priority, and deadline-aware allocation
- Fidelity vs storage time curves for different memory types
- Random-access memory protocol simulation with access infidelity tracking

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q23-memory
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q23-memory    # Show project details
qlab setup q23-memory    # Install requirements
qlab data  q23-memory    # Download Kaggle data
qlab run   q23-memory    # Launch Streamlit UI
```
