# Quantum Machine Learning — User Stories

## Overview
Variational quantum classifiers (VQC), quantum kernel methods (QSVM), quantum neural networks.

## User Stories

### US-01: ML engineer — train a VQC on XOR dataset
**As a** ML engineer, **I want** train a VQC on XOR dataset **so that** I understand quantum advantage for ML.

**Acceptance Criteria:**
- [ ] VQC accuracy > 85%
- [ ] Training converges in 50 epochs
- [ ] Quantum vs classical comparison shown

## Input / Process / Output

| Stage | Description |
|-------|-------------|
| **Input** | Classical dataset (features), VQC ansatz, optimizer (Adam) |
| **Process** | Angle embedding, parameterized rotations, measurement, gradient descent |
| **Output** | Trained model, accuracy, loss curve, classical comparison |
