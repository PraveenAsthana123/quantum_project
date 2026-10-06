# Quantum Algorithm Assessment & Benchmark Platform

## Overview
A comprehensive platform for implementing, visualizing, and benchmarking foundational quantum algorithms against their classical counterparts. Covers QFT, Grover, Shor, QPE, HHL, amplitude estimation, QAOA, and VQE with circuit diagrams, Bloch sphere animations, and performance benchmarks.

## Role Target
Quantum Solutions Scientist / Applied Quantum Consultant

## Tech Stack
- **Core SDKs:** qiskit>=2.0.0, qiskit-aer>=0.17.0, qiskit-algorithms>=0.4.0, pennylane>=0.45.0, cirq>=1.7.0, numpy>=2.0.0
- **UI:** Streamlit + Plotly
- **Data:** mlg-ulb/creditcardfraud
- **GitHub Reference:** https://github.com/Qiskit/qiskit-algorithms

## Project Structure
```
src/           Core quantum implementation
data/          Datasets (Kaggle + generated)
ui/            Streamlit dashboard (app.py)
notebooks/     Jupyter exploration notebooks
tests/         Unit and integration tests
```

## Key Capabilities
- Quantum Fourier Transform (QFT) — circuit construction and verification
- Grover's search algorithm with oracle for structured search problems
- Shor's factoring algorithm (small N) with classical vs quantum comparison
- Quantum Phase Estimation (QPE) for eigenvalue computation
- HHL linear systems solver with condition number analysis
- Amplitude Estimation and Amplitude Amplification implementations
- Algorithm selection guide: problem type → recommended quantum algorithm

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download data (if applicable)
kaggle datasets download -d mlg-ulb/creditcardfraud

# Run UI
qlab run q01-algorithms
# or directly:
streamlit run ui/app.py
```

## CLI Commands
```bash
qlab info  q01-algorithms    # Show project details
qlab setup q01-algorithms    # Install requirements
qlab data  q01-algorithms    # Download Kaggle data
qlab run   q01-algorithms    # Launch Streamlit UI
```
