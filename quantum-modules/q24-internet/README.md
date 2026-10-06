# Quantum Internet Architecture & Entanglement Service Mesh

## Overview
Implements a layered quantum internet architecture following IRTF RFC 9340 principles. Separates Quantum Data Plane (QDP) from Quantum Control Plane (QCP), models entanglement as a network service, and integrates with classical network for hybrid quantum-classical communication.

## Role Target
Principal Architect Network R&D / Quantum Internet Architect

## Tech Stack
- **Core SDKs:** numpy>=2.0.0, scipy>=1.14.0, networkx>=3.0.0, pandas>=2.0.0, fastapi>=0.100.0, streamlit>=1.40.0
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
- Quantum Data Plane (QDP) and Quantum Control Plane (QCP) separation
- Entanglement service API: request → allocate → distribute → consume
- QKD link simulation with BB84 and E91 protocols
- Quantum-classical hybrid network: entanglement + classical side-channel
- Network topology: star, mesh, and hierarchical repeater architectures
- Service mesh metrics: entanglement rate, fidelity SLA, latency, availability
- RFC 9340 protocol stack visualization and compliance mapping

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q24-internet
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q24-internet    # Show project details
qlab setup q24-internet    # Install requirements
qlab data  q24-internet    # Download Kaggle data
qlab run   q24-internet    # Launch Streamlit UI
```
