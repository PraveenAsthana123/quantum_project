# Quantum Control Electronics & RFSoC Digital Twin

## Overview
Digital twin of quantum control electronics including AWG/RFSoC-based qubit control, DAC/ADC signal chains, I/Q mixer modeling, clock synchronization, and FPGA real-time feedback. Based on open QICK architecture for open-source RFSoC quantum control.

## Role Target
Quantum Control Electronics Engineer / Hardware Architect

## Tech Stack
- **Core SDKs:** numpy>=2.0.0, scipy>=1.14.0, qutip>=5.0.0, matplotlib>=3.8.0, streamlit>=1.40.0, plotly>=5.0.0
- **UI:** Streamlit + Plotly
- **Data:** No external dataset required
- **GitHub Reference:** https://github.com/openquantumhardware/qick

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- DAC waveform generator: pulse envelope, frequency, phase
- I/Q mixer model with LO leakage and sideband suppression
- ADC signal capture and digital downconversion simulation
- FPGA real-time feedback loop: measure → decision → pulse
- Clock synchronization and multi-channel phase coherence
- Signal integrity analysis: SNR, noise floor, dynamic range
- Full qubit control chain: program → waveform → qubit → readout

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
# No Kaggle data required

# Run UI
qlab run q16-ctrl-electronics
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q16-ctrl-electronics    # Show project details
qlab setup q16-ctrl-electronics    # Install requirements
qlab data  q16-ctrl-electronics    # Download Kaggle data
qlab run   q16-ctrl-electronics    # Launch Streamlit UI
```
