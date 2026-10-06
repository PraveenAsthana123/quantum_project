# Quantum Packaging & Interconnect Digital Twin

## Overview
Models the quantum chip packaging stack from die to QPU module. Simulates flip-chip bonding, wirebond parasitics, interposer signal integrity, microwave transition design, and cryogenic thermal contraction. Covers scaling to 500+ qubit interconnect architectures.

## Role Target
Quantum Packaging Engineer / Systems Integration Architect

## Tech Stack
- **Core SDKs:** numpy>=2.0.0, scipy>=1.14.0, pandas>=2.0.0, matplotlib>=3.8.0, streamlit>=1.40.0, plotly>=5.0.0
- **UI:** Streamlit + Plotly
- **Data:** No external dataset required
- **GitHub Reference:** https://github.com/iqm-finland/KQCircuits

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Wirebond parasitic inductance and capacitance modeling
- Flip-chip bump bond RF performance simulation
- Microwave launch and transmission line design for cryogenic operation
- Package resonance mode identification and mitigation strategies
- Thermal contraction stress analysis for cryogenic packaging materials
- Signal integrity: crosstalk, insertion loss, return loss across frequency
- Interconnect scaling analysis: 50 → 500 → 1000+ qubit packaging

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q19-packaging
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q19-packaging    # Show project details
qlab setup q19-packaging    # Install requirements
qlab data  q19-packaging    # Download Kaggle data
qlab run   q19-packaging    # Launch Streamlit UI
```
