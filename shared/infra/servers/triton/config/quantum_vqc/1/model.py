"""
Triton Python Backend — Quantum VQC (PennyLane)
================================================
4-qubit variational quantum classifier using:
  - RY angle encoding of 4 input features
  - CNOT ring entanglement
  - 3 variational layers (Rot gates)
  - Pauli-Z expectation values → 2-class softmax probabilities

Weights are loaded from weights.npy saved alongside this file.
"""

import os
import json
import numpy as np
import triton_python_backend_utils as pb_utils

try:
    import pennylane as qml
except ImportError:
    raise RuntimeError("PennyLane is not installed in the Triton Python backend environment. "
                       "Add 'pennylane' to the conda/pip env used by KIND_CPU instances.")


# ---------------------------------------------------------------------------
# Circuit definition
# ---------------------------------------------------------------------------

N_QUBITS = 4
N_LAYERS = 3
WEIGHTS_FILE = os.path.join(os.path.dirname(__file__), "weights.npy")

dev = qml.device("default.qubit", wires=N_QUBITS)


@qml.qnode(dev)
def vqc_circuit(inputs: np.ndarray, weights: np.ndarray) -> list:
    """
    Args:
        inputs:  shape (4,)  — normalised feature vector
        weights: shape (N_LAYERS, N_QUBITS, 3) — Rot gate angles

    Returns:
        List of 4 Pauli-Z expectation values (one per qubit).
    """
    # Angle encoding: map each feature to RY rotation on its qubit
    for i in range(N_QUBITS):
        qml.RY(inputs[i] * np.pi, wires=i)

    # CNOT ring entanglement
    for i in range(N_QUBITS):
        qml.CNOT(wires=[i, (i + 1) % N_QUBITS])

    # Variational layers: Rot(phi, theta, omega) + CNOT ring repeated
    for layer in range(N_LAYERS):
        for qubit in range(N_QUBITS):
            qml.Rot(
                weights[layer, qubit, 0],
                weights[layer, qubit, 1],
                weights[layer, qubit, 2],
                wires=qubit,
            )
        for i in range(N_QUBITS):
            qml.CNOT(wires=[i, (i + 1) % N_QUBITS])

    return [qml.expval(qml.PauliZ(i)) for i in range(N_QUBITS)]


def _expvals_to_probs(expvals: np.ndarray) -> np.ndarray:
    """
    Map 4 Pauli-Z expectation values in [-1, 1] to 2-class probabilities.
    Uses the mean of the first two vs last two qubits as a logit proxy,
    then applies softmax.

    Returns shape (2,) — [P(not_fraud), P(fraud)].
    """
    score_0 = float(np.mean(expvals[:2]))   # qubits 0,1 → not-fraud signal
    score_1 = float(np.mean(expvals[2:]))   # qubits 2,3 → fraud signal

    # Softmax over two logits
    logits = np.array([score_0, score_1], dtype=np.float32)
    logits -= logits.max()                  # numerical stability
    exps = np.exp(logits)
    probs = exps / exps.sum()
    return probs.astype(np.float32)


# ---------------------------------------------------------------------------
# Triton TritonPythonModel class
# ---------------------------------------------------------------------------

class TritonPythonModel:
    """
    Triton Python Backend entry point.
    Triton calls initialize() once, then execute() for every incoming batch.
    """

    def initialize(self, args: dict) -> None:
        """
        Load variational weights from disk.
        args["model_repository"] points to the directory containing this file.
        """
        self.logger = pb_utils.Logger
        model_dir = args.get("model_repository", os.path.dirname(__file__))
        weights_path = os.path.join(model_dir, "weights.npy")

        if not os.path.isfile(weights_path):
            # Fall back to the directory of __file__ (version subfolder)
            weights_path = WEIGHTS_FILE

        if not os.path.isfile(weights_path):
            raise FileNotFoundError(
                f"VQC weights not found at {weights_path}. "
                "Run scripts/load_models.py to train and save weights first."
            )

        self.weights = np.load(weights_path)  # shape: (N_LAYERS, N_QUBITS, 3)

        expected_shape = (N_LAYERS, N_QUBITS, 3)
        if self.weights.shape != expected_shape:
            raise ValueError(
                f"Loaded weights shape {self.weights.shape} != expected {expected_shape}"
            )

        self.logger.log_info(
            f"[quantum_vqc] Loaded weights from {weights_path}, "
            f"shape={self.weights.shape}"
        )

    def execute(self, requests: list) -> list:
        """
        Process a batch of Triton inference requests.

        Each request may contain multiple samples (dynamic batching).
        Input tensor name: "input__0", shape [batch, 4], dtype FP32.
        Output tensor name: "output__0", shape [batch, 2], dtype FP32.
        """
        responses = []

        for request in requests:
            # Retrieve input tensor
            in_tensor = pb_utils.get_input_tensor_by_name(request, "input__0")
            inputs = in_tensor.as_numpy()          # shape: (batch_size, 4)

            batch_size = inputs.shape[0]
            output_probs = np.zeros((batch_size, 2), dtype=np.float32)

            for i in range(batch_size):
                sample = inputs[i].astype(np.float64)  # PennyLane prefers float64
                expvals = np.array(vqc_circuit(sample, self.weights), dtype=np.float64)
                output_probs[i] = _expvals_to_probs(expvals)

            out_tensor = pb_utils.Tensor("output__0", output_probs)
            response = pb_utils.InferenceResponse(output_tensors=[out_tensor])
            responses.append(response)

        return responses

    def finalize(self) -> None:
        """Called when Triton unloads the model. Clean up if needed."""
        self.logger.log_info("[quantum_vqc] Model unloaded.")
