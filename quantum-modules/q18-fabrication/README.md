# Quantum Chip Fabrication Digital Twin & Yield Control Tower

## Overview
Simulates quantum chip design and fabrication process for superconducting qubits. Covers GDSFactory-based device layout, DRC/LVS verification, process variation Monte Carlo, Josephson junction parameter spread, and wafer-level yield analytics.

## Role Target
Quantum Device Architect / Silicon Technology Architect

## Tech Stack
- **Core SDKs:** numpy>=2.0.0, scipy>=1.14.0, pandas>=2.0.0, matplotlib>=3.8.0, streamlit>=1.40.0, plotly>=5.0.0
- **UI:** Streamlit + Plotly
- **Data:** No external dataset required
- **GitHub Reference:** https://github.com/gdsfactory/gdsfactory

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Transmon qubit geometry design: island, junction, resonator coupling
- GDSII layout generation and DRC rule checking simulation
- Josephson junction parameter (EJ, EC) process variation modeling
- Monte Carlo yield analysis: qubit frequency distribution across wafer
- Defect density and critical area analysis
- Fabrication process step tracker: deposit → pattern → etch → clean
- Yield optimization: parameter sensitivity and design-for-manufacturing rules

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q18-fabrication
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q18-fabrication    # Show project details
qlab setup q18-fabrication    # Install requirements
qlab data  q18-fabrication    # Download Kaggle data
qlab run   q18-fabrication    # Launch Streamlit UI
```
