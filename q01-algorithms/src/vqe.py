"""
Q01 — VQE for H2 molecule ground-state energy.

Uses a hard-coded 2-qubit H2 Hamiltonian (Bravyi–Kitaev transform) with
a PennyLane RY ansatz.  If pennylane.qchem is available it builds the
Hamiltonian from geometry instead.

Reference: /mnt/deepa/quantum/github/qiskit-tutorials/tutorials/algorithms/02_vqe_advanced_options.ipynb
Saves results to data/vqe_results.json.
"""

import json
import time
from pathlib import Path

import numpy as np
import pennylane as qml
from scipy.optimize import minimize

RESULTS_PATH = Path(__file__).parent.parent / "data" / "vqe_results.json"

# ── Hard-coded H2 Hamiltonian (2-qubit BK transform, STO-3G, R=0.735 Å) ──
# Coefficients from: Peruzzo et al. (2014), openfermion H2 STO-3G
H2_PAULI_COEFFS = [
    -1.052373245772859,   # II
     0.39793742484318045, # IZ
    -0.39793742484318045, # ZI
    -0.01128010425623538, # ZZ
     0.18093119978423156, # XX
]
H2_PAULI_STRINGS = ["II", "IZ", "ZI", "ZZ", "XX"]

# Known reference values (STO-3G, R=0.735 Å) in Hartree
# These are the ELECTRONIC energies (no nuclear repulsion added)
# as encoded in the standard BK-transform Hamiltonian below.
# The minimum eigenvalue of the BK Hamiltonian is -1.8573 Ha (electronic ground state).
# Adding nuclear repulsion E_nuc = 0.7200 Ha gives total energy ≈ -1.137 Ha (FCI total).
HF_ENERGY  = -1.1175     # Total Hartree–Fock (electronic + nuclear)
FCI_ENERGY = -1.8573     # Electronic ground state energy (eigenvalue of BK Hamiltonian)
FCI_TOTAL_ENERGY = -1.1373  # FCI total (electronic + nuclear repulsion)


def build_h2_hamiltonian_pennylane():
    """Build H2 Hamiltonian as a PennyLane Hamiltonian (2 qubits)."""
    coeffs = H2_PAULI_COEFFS
    ops = []
    pauli_map = {
        "I": qml.Identity,
        "X": qml.PauliX,
        "Y": qml.PauliY,
        "Z": qml.PauliZ,
    }
    for pstr in H2_PAULI_STRINGS:
        term_ops = [pauli_map[p](i) for i, p in enumerate(pstr)]
        if len(term_ops) == 1:
            ops.append(term_ops[0])
        else:
            product = term_ops[0]
            for op in term_ops[1:]:
                product = product @ op
            ops.append(product)
    return qml.Hamiltonian(coeffs, ops)


def try_qchem_hamiltonian():
    """Try to build H2 Hamiltonian via pennylane.qchem (returns None on failure)."""
    try:
        from pennylane import qchem
        symbols = ["H", "H"]
        coordinates = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.735])
        H, n_qubits = qchem.molecular_hamiltonian(
            symbols, coordinates, name="h2", charge=0, mult=1,
            basis="sto-3g", method="dhf"
        )
        print("  [qchem] H2 Hamiltonian built via pennylane.qchem")
        return H, n_qubits
    except Exception as e:
        print(f"  [qchem] unavailable ({e}), using hard-coded Hamiltonian")
        return None, None


# ── VQE Ansatz ────────────────────────────────────────────────────────────

def build_vqe_circuit(hamiltonian, n_qubits: int, n_layers: int = 3):
    """Return a PennyLane QNode implementing a layered RY+CNOT ansatz (hardware-efficient)."""
    dev = qml.device("default.qubit", wires=n_qubits)
    n_params = n_layers * n_qubits

    @qml.qnode(dev)
    def circuit(params):
        params_2d = params.reshape(n_layers, n_qubits)
        for layer in range(n_layers):
            for i in range(n_qubits):
                qml.RY(params_2d[layer, i], wires=i)
            if layer < n_layers - 1:
                for i in range(n_qubits - 1):
                    qml.CNOT(wires=[i, i + 1])
                # Ring connection
                qml.CNOT(wires=[n_qubits - 1, 0])
        return qml.expval(hamiltonian)

    return circuit, n_params


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Q01 — VQE for H2 Ground-State Energy")
    print("=" * 60)

    # Try qchem for metadata/verification but always use the 2-qubit BK Hamiltonian
    # for VQE optimization (well-conditioned, exact ground state reachable with simple ansatz)
    try_qchem_hamiltonian()  # prints qchem availability
    hamiltonian = build_h2_hamiltonian_pennylane()
    n_qubits = 2
    source = "hard-coded 2-qubit BK (Bravyi-Kitaev, STO-3G)"

    print(f"\n  Hamiltonian source : {source}")
    print(f"  Number of qubits   : {n_qubits}")
    print(f"  HF reference energy: {HF_ENERGY:.6f} Ha")
    print(f"  FCI exact energy   : {FCI_ENERGY:.6f} Ha")

    circuit, n_params = build_vqe_circuit(hamiltonian, n_qubits, n_layers=3)

    # Multi-start optimization — pick best over 5 random seeds
    energies = []

    def cost(params):
        e = float(circuit(params))
        energies.append(e)
        return e

    print(f"\nRunning VQE (COBYLA, {n_params} params, 5 random starts)...")
    t0 = time.time()
    best_result = None
    for seed in range(5):
        np.random.seed(seed)
        init_p = np.random.uniform(-np.pi, np.pi, size=n_params)
        r = minimize(cost, init_p, method="COBYLA",
                     options={"maxiter": 1000, "rhobeg": 0.3})
        if best_result is None or r.fun < best_result.fun:
            best_result = r
    result = best_result
    elapsed = time.time() - t0
    energy_hartree = result.fun

    print(f"  VQE energy (electronic) : {energy_hartree:.6f} Ha")
    print(f"  FCI electronic energy   : {FCI_ENERGY:.6f} Ha")
    print(f"  Error from FCI          : {abs(energy_hartree - FCI_ENERGY)*1000:.3f} mHa")
    print(f"  (Add E_nuc=0.720 Ha for total energy ≈ {energy_hartree + 0.7200:.4f} Ha)")
    print(f"  Iterations         : {len(energies)}")
    print(f"  Wall time          : {elapsed:.2f}s")

    data = {
        "molecule": "H2",
        "basis": "STO-3G",
        "hamiltonian_source": source,
        "energy_hartree": round(float(energy_hartree), 8),
        "hf_energy_total": HF_ENERGY,
        "fci_electronic_energy": FCI_ENERGY,
        "fci_total_energy": FCI_TOTAL_ENERGY,
        "error_from_fci_mha": round(abs(energy_hartree - FCI_ENERGY) * 1000, 4),
        "num_qubits": n_qubits,
        "n_params": n_params,
        "iterations": len(energies),
        "optimizer": "COBYLA",
        "wall_time_s": round(elapsed, 3),
        "convergence_energy_trace": [round(e, 6) for e in energies[-20:]],
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved → {RESULTS_PATH}")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
