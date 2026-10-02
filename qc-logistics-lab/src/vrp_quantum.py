"""
Quantum VRP solver via QUBO → QAOA, with simulated-annealing (D-Wave dimod) baseline.
Compares: Classical greedy | Simulated Annealing | QAOA
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np

DATA_DIR = Path(__file__).parent.parent / "data"
RESULTS_FILE = DATA_DIR / "vrp_quantum_results.json"


# ---------------------------------------------------------------------------
# Small TSP → QUBO (tractable for simulation)
# ---------------------------------------------------------------------------

def tsp_qubo(n: int, dist_matrix: np.ndarray, penalty: float = 100.0) -> np.ndarray:
    """Convert n-city TSP to QUBO. Variables: x_{i,t} = 1 if city i at position t."""
    size = n * n
    Q = np.zeros((size, size))

    def idx(i, t):
        return i * n + t

    # Constraint: each city visited exactly once
    for i in range(n):
        for t in range(n):
            Q[idx(i, t), idx(i, t)] += -penalty
            for s in range(t + 1, n):
                Q[idx(i, t), idx(i, s)] += 2 * penalty
        for j in range(i + 1, n):
            for t in range(n):
                Q[idx(i, t), idx(j, t)] += 2 * penalty

    # Objective: distance
    for u in range(n):
        for v in range(n):
            if u == v:
                continue
            d = dist_matrix[u, v]
            for t in range(n):
                Q[idx(u, t), idx(v, (t + 1) % n)] += d

    return Q


def qubo_to_ising(Q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert QUBO to Ising (h, J) via x = (1 - s) / 2."""
    n = Q.shape[0]
    J = Q / 4.0
    h = np.zeros(n)
    for i in range(n):
        h[i] = np.sum(Q[i, :]) / 4.0 + np.sum(Q[:, i]) / 4.0 - Q[i, i] / 4.0
    return h, J


# ---------------------------------------------------------------------------
# Simulated Annealing baseline (D-Wave dimod or pure numpy)
# ---------------------------------------------------------------------------

def simulated_annealing(Q: np.ndarray, num_reads: int = 100) -> dict:
    try:
        import dimod
        bqm = dimod.BinaryQuadraticModel.from_qubo(
            {(i, j): float(Q[i, j]) for i in range(len(Q)) for j in range(i, len(Q)) if Q[i, j] != 0}
        )
        sampler = dimod.SimulatedAnnealingSampler()
        t0 = time.perf_counter()
        response = sampler.sample(bqm, num_reads=num_reads)
        elapsed = time.perf_counter() - t0
        best = response.first
        return {"energy": float(best.energy), "sample": dict(best.sample), "elapsed_s": round(elapsed, 4), "backend": "dimod-SA"}
    except ImportError:
        pass

    # Pure numpy SA fallback
    n = Q.shape[0]
    rng = np.random.default_rng(42)
    x = rng.integers(0, 2, n).astype(float)
    energy = float(x @ Q @ x)
    T = 10.0
    t0 = time.perf_counter()
    for step in range(5000):
        i = rng.integers(0, n)
        x_new = x.copy()
        x_new[i] = 1 - x_new[i]
        e_new = float(x_new @ Q @ x_new)
        dE = e_new - energy
        if dE < 0 or rng.random() < np.exp(-dE / T):
            x, energy = x_new, e_new
        T = max(T * 0.995, 0.01)
    elapsed = time.perf_counter() - t0
    return {"energy": energy, "sample": {i: int(x[i]) for i in range(n)}, "elapsed_s": round(elapsed, 4), "backend": "numpy-SA"}


# ---------------------------------------------------------------------------
# QAOA on small TSP
# ---------------------------------------------------------------------------

def qaoa_tsp(n_cities: int, Q: np.ndarray, n_layers: int = 1) -> dict:
    n_qubits = n_cities * n_cities
    if n_qubits > 16:
        return {"method": "QAOA-skipped", "reason": f"n_qubits={n_qubits} > 16; use SA for larger instances"}

    try:
        import pennylane as qml
        from pennylane import numpy as pnp
    except ImportError:
        return {"method": "QAOA-unavailable", "error": "pennylane not installed"}

    dev = qml.device("default.qubit", wires=n_qubits)

    def cost_unitary(gamma: float):
        for i in range(n_qubits):
            for j in range(i + 1, n_qubits):  # skip i==j (same wire)
                if Q[i, j] != 0:
                    qml.IsingZZ(-gamma * Q[i, j], wires=[i, j])
            # diagonal terms as RZ
            if Q[i, i] != 0:
                qml.RZ(-gamma * Q[i, i], wires=i)

    def mixer_unitary(beta: float):
        for i in range(n_qubits):
            qml.RX(-2 * beta, wires=i)

    @qml.qnode(dev)
    def qaoa_circuit(gammas, betas):
        for i in range(n_qubits):
            qml.Hadamard(wires=i)
        for layer in range(n_layers):
            cost_unitary(gammas[layer])
            mixer_unitary(betas[layer])
        return qml.probs(wires=range(n_qubits))

    rng = np.random.default_rng(42)
    gammas = pnp.array(rng.uniform(0, np.pi, n_layers), requires_grad=True)
    betas = pnp.array(rng.uniform(0, np.pi, n_layers), requires_grad=True)

    opt = qml.AdamOptimizer(stepsize=0.1)

    def obj(params):
        g, b = params
        probs = qaoa_circuit(g, b)
        energies = pnp.zeros(2 ** n_qubits)
        for state_idx in range(2 ** n_qubits):
            bits = np.array([(state_idx >> i) & 1 for i in range(n_qubits)], dtype=float)
            energies = pnp.array(energies.numpy() if hasattr(energies, 'numpy') else np.array(energies))
            e = float(bits @ Q @ bits)
            energies_np = np.array(energies)
            energies_np[state_idx] = e
            energies = pnp.array(energies_np)
        return pnp.dot(probs, energies)

    losses = []
    t0 = time.perf_counter()
    try:
        for step in range(20):
            (gammas, betas), loss = opt.step_and_cost(obj, (gammas, betas))
            losses.append(float(loss))
    except Exception as e:
        return {"method": "QAOA-error", "error": str(e), "elapsed_s": round(time.perf_counter() - t0, 4)}

    elapsed = time.perf_counter() - t0
    final_probs = qaoa_circuit(gammas, betas)
    best_state = int(np.argmax(np.array(final_probs)))
    best_bits = np.array([(best_state >> i) & 1 for i in range(n_qubits)], dtype=float)
    best_energy = float(best_bits @ Q @ best_bits)

    circuit_info = {
        "n_qubits": n_qubits, "n_layers": n_layers,
        "depth": 2 * n_layers + 1,
    }
    return {
        "method": "QAOA-PennyLane",
        "n_qubits": n_qubits,
        "n_layers": n_layers,
        "best_energy": best_energy,
        "final_gammas": gammas.tolist() if hasattr(gammas, 'tolist') else list(gammas),
        "final_betas": betas.tolist() if hasattr(betas, 'tolist') else list(betas),
        "loss_history": losses,
        "elapsed_s": round(elapsed, 4),
        "circuit": circuit_info,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(n_cities: int = 4) -> dict:
    import math

    # Generate small instance (TSP, tractable for simulation)
    rng = np.random.default_rng(42)
    coords = rng.uniform(0, 100, (n_cities, 2))
    dist_matrix = np.array([[math.hypot(*(coords[i] - coords[j])) for j in range(n_cities)] for i in range(n_cities)])

    print(f"\nBuilding QUBO for {n_cities}-city TSP ({n_cities**2} binary variables)...")
    Q = tsp_qubo(n_cities, dist_matrix)

    print("Solving with Simulated Annealing...")
    sa_result = simulated_annealing(Q)
    print(f"  SA energy={sa_result['energy']:.2f}  elapsed={sa_result['elapsed_s']}s  backend={sa_result['backend']}")

    print("Solving with QAOA...")
    qaoa_result = qaoa_tsp(n_cities, Q)
    if "error" not in qaoa_result and "reason" not in qaoa_result:
        print(f"  QAOA energy={qaoa_result.get('best_energy', '?'):.2f}  elapsed={qaoa_result.get('elapsed_s', '?')}s")
    else:
        print(f"  QAOA: {qaoa_result}")

    import importlib.util, sys as _sys
    _spec = importlib.util.spec_from_file_location("vrp_classical", Path(__file__).parent / "vrp_classical.py")
    _mod = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_mod)
    nearest_neighbor_vrp = _mod.nearest_neighbor_vrp; generate_vrp = _mod.generate_vrp
    instance = generate_vrp(n_cities=max(n_cities, 6), n_vehicles=2)
    classical_sol = nearest_neighbor_vrp(instance)

    result: dict[str, Any] = {
        "n_cities": n_cities,
        "instance": {"coords": coords.tolist(), "dist_matrix": dist_matrix.tolist()},
        "simulated_annealing": sa_result,
        "qaoa": qaoa_result,
        "classical_greedy": {
            "total_distance": classical_sol["total_distance"],
            "routes": classical_sol["routes"],
        },
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"Results saved → {RESULTS_FILE}")
    return result


if __name__ == "__main__":
    main(n_cities=4)
