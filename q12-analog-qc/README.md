# Neutral-Atom Analog Quantum Optimization Lab

## Overview
Implements analog quantum computation using neutral-atom arrays with Rydberg blockade interactions. Programs time-dependent Hamiltonians through laser pulse sequences to solve combinatorial optimization problems. Compares analog Rydberg-blockade approach with digital QAOA.

## Role Target
Quantum Algorithm Developer / Analog Quantum Architect

## Tech Stack
- **Core SDKs:** pennylane>=0.45.0, numpy>=2.0.0, scipy>=1.14.0, networkx>=3.0.0, streamlit>=1.40.0, plotly>=5.0.0
- **UI:** Streamlit + Plotly
- **Data:** gaborfodor/tsplib-benchmark
- **GitHub Reference:** https://github.com/pasqal-io/pulser

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Neutral-atom register layout design for MaxCut / MIS problems
- Rabi drive and detuning pulse sequence construction
- Rydberg blockade constraint encoding for combinatorial problems
- Digital QAOA vs analog Rydberg comparison on same problem instances
- Pulse parameter optimization with gradient-free methods
- Atom array geometry visualizer with interaction graph overlay
- Emulator-based time evolution with QuTiP master equation

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
kaggle datasets download -d gaborfodor/tsplib-benchmark

# Run UI
qlab run q12-analog-qc
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q12-analog-qc    # Show project details
qlab setup q12-analog-qc    # Install requirements
qlab data  q12-analog-qc    # Download Kaggle data
qlab run   q12-analog-qc    # Launch Streamlit UI
```
