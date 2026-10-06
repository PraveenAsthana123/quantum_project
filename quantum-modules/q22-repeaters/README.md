# Quantum Repeater Network & Entanglement Routing Tower

## Overview
Simulates quantum repeater networks for long-distance entanglement distribution. Models elementary entanglement generation, entanglement swapping, purification protocols, and multi-hop routing. Uses SeQUeNCe-inspired architecture with configurable repeater chains.

## Role Target
Quantum Network Architect / Quantum Internet Engineer

## Tech Stack
- **Core SDKs:** numpy>=2.0.0, scipy>=1.14.0, networkx>=3.0.0, pandas>=2.0.0, matplotlib>=3.8.0, streamlit>=1.40.0
- **UI:** Streamlit + Plotly
- **Data:** No external dataset required
- **GitHub Reference:** https://github.com/sequence-toolbox/SeQUeNCe

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Elementary entanglement link simulation with loss and fidelity models
- Entanglement swapping protocol with Bell-state measurement
- Entanglement purification (DEJMPS, BB84-based) with round analysis
- Multi-hop repeater chain: rate and fidelity vs distance
- Routing protocol: shortest path vs highest-fidelity path
- Quantum memory model: coherence time, efficiency, multimode capacity
- Network dashboard: link fidelity map, entanglement rate, latency

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q22-repeaters
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q22-repeaters    # Show project details
qlab setup q22-repeaters    # Install requirements
qlab data  q22-repeaters    # Download Kaggle data
qlab run   q22-repeaters    # Launch Streamlit UI
```
