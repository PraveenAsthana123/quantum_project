# Quantum Cryogenic Infrastructure & Thermal Digital Twin

## Overview
Thermal simulation of a dilution refrigerator for superconducting quantum systems. Models heat loads at 50K, 4K, still, cold-plate, and mixing-chamber stages. Simulates PID thermal control, cable heat loads, and cooldown/warmup cycles.

## Role Target
Quantum Systems Engineer / Cryogenics Architect

## Tech Stack
- **Core SDKs:** numpy>=2.0.0, scipy>=1.14.0, matplotlib>=3.8.0, pandas>=2.0.0, streamlit>=1.40.0, plotly>=5.0.0
- **UI:** Streamlit + Plotly
- **Data:** No external dataset required
- **GitHub Reference:** https://github.com/Luigy-Lemon/quantum-computing-research

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Multi-stage dilution refrigerator thermal model (RT → 50K → 4K → still → MXC)
- Heat load calculator: cables, connectors, radiation, black-body
- PID temperature controller simulation for mixing chamber stage
- Cooldown curve simulation: time-to-base-temperature estimation
- Attenuation and filtering chain thermal contribution analysis
- Cryogenic cable heat load comparison: NbTi vs stainless vs Cu
- Thermal dashboard: stage temperatures, heat loads, cooling power margins

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q17-cryogenics
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q17-cryogenics    # Show project details
qlab setup q17-cryogenics    # Install requirements
qlab data  q17-cryogenics    # Download Kaggle data
qlab run   q17-cryogenics    # Launch Streamlit UI
```
