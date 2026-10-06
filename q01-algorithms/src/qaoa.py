"""
Q01 — QAOA for Max-Cut on a random 6-node graph.

Uses PennyLane to build and optimize a QAOA circuit with p=2 layers.
Saves results to data/qaoa_results.json.

Reference: /mnt/deepa/quantum/github/qiskit-tutorials/tutorials/algorithms/05_qaoa.ipynb
"""

import json
import time
import random
from pathlib import Path

import numpy as np
import networkx as nx
import pennylane as qml
from scipy.optimize import minimize

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RESULTS_PATH = Path(__file__).parent.parent / "data" / "qaoa_results.json"


def build_random_graph(n_nodes: int = 6, seed: int = 42) -> nx.Graph:
    """Generate a random connected graph with fixed seed."""
    rng = np.random.default_rng(seed)
    G = nx.erdos_renyi_graph(n_nodes, p=0.5, seed=seed)
    # Ensure connectivity
    while not nx.is_connected(G):
        G = nx.erdos_renyi_graph(n_nodes, p=0.6, seed=rng.integers(1000))
    return G


def max_cut_brute_force(G: nx.Graph) -> tuple[int, list[int]]:
    """Brute-force Max-Cut for small graphs. Returns (max_cut_value, best_partition)."""
    n = G.number_of_nodes()
    best_val = 0
    best_x = []
    for mask in range(1, 2**n):
        cut = sum(
            1
            for u, v in G.edges()
            if ((mask >> u) & 1) != ((mask >> v) & 1)
        )
        if cut > best_val:
            best_val = cut
            best_x = [(mask >> i) & 1 for i in range(n)]
    return best_val, best_x


# ---------------------------------------------------------------------------
# QAOA circuit (PennyLane)
# ---------------------------------------------------------------------------

def build_qaoa_circuit(G: nx.Graph, p: int = 2):
    """Return a PennyLane QNode implementing QAOA for Max-Cut."""
    n_qubits = G.number_of_nodes()
    dev = qml.device("default.qubit", wires=n_qubits)

    # Cost Hamiltonian: H_C = -0.5 * sum_{(i,j) in E} (1 - Z_i Z_j)
    coeffs = []
    observables = []
    for u, v in G.edges():
        coeffs.append(-0.5)
        obs_z = qml.Identity(0)
        # Build ZZ term
        obs_list = [qml.PauliZ(i) for i in range(n_qubits)]
        # ZiZj => product; PennyLane uses Hamiltonian with per-term approach
        coeffs[-1] = 0.5  # flip sign for maximization later
        observables.append(qml.PauliZ(u) @ qml.PauliZ(v))

    # H_C = sum_{(u,v)} 0.5 * (I - Z_u Z_v)  — maximizing cuts
    # Expectation: <H_C> = 0.5 * |E| - 0.5 * sum <Z_u Z_v>
    # We minimize -<H_C>
    cost_h = qml.Hamiltonian(
        [0.5 * len(G.edges())] + [-0.5] * len(list(G.edges())),
        [qml.Identity(0)] + [qml.PauliZ(u) @ qml.PauliZ(v) for u, v in G.edges()],
    )

    @qml.qnode(dev)
    def circuit(params):
        gammas = params[:p]
        betas = params[p:]
        # Hadamard layer — equal superposition
        for i in range(n_qubits):
            qml.Hadamard(wires=i)
        # p QAOA layers
        for layer in range(p):
            # Cost unitary
            for u, v in G.edges():
                qml.CNOT(wires=[u, v])
                qml.RZ(2 * gammas[layer], wires=v)
                qml.CNOT(wires=[u, v])
            # Mixer unitary
            for i in range(n_qubits):
                qml.RX(2 * betas[layer], wires=i)
        return qml.expval(cost_h)

    return circuit, cost_h


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Q01 — QAOA for Max-Cut (6-node random graph, p=2)")
    print("=" * 60)

    # Build graph
    G = build_random_graph(n_nodes=6, seed=42)
    print(f"\nGraph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print(f"Edges: {list(G.edges())}")

    # Classical optimal via brute force
    print("\nRunning brute-force Max-Cut...")
    t0 = time.time()
    classical_optimal, best_partition = max_cut_brute_force(G)
    classical_time_ms = (time.time() - t0) * 1000
    print(f"Classical optimal cut = {classical_optimal}  (partition: {best_partition})")

    # Build QAOA circuit
    p = 2
    circuit, cost_h = build_qaoa_circuit(G, p=p)

    # Random initial parameters: [gamma_0, gamma_1, beta_0, beta_1]
    np.random.seed(123)
    init_params = np.random.uniform(0, np.pi, size=2 * p)

    def neg_expval(params):
        return -float(circuit(params))

    print(f"\nOptimizing QAOA parameters (p={p})...")
    result = minimize(
        neg_expval,
        init_params,
        method="COBYLA",
        options={"maxiter": 500, "rhobeg": 0.5},
    )
    opt_params = result.x
    qaoa_energy = -result.fun  # flip sign back (we minimized negative)
    print(f"QAOA energy (approx cut value) = {qaoa_energy:.4f}")
    print(f"Optimization success: {result.success}, message: {result.message}")

    # Approximation ratio
    approx_ratio = qaoa_energy / classical_optimal if classical_optimal > 0 else 0.0
    print(f"Approximation ratio = {approx_ratio:.4f}")

    # Circuit depth estimate: 1 Hadamard layer + p*(edges + n) layers
    circuit_depth = 1 + p * (G.number_of_edges() + G.number_of_nodes())

    # Persist results
    data = {
        "graph_nodes": G.number_of_nodes(),
        "graph_edges": list(G.edges()),
        "n_edges": G.number_of_edges(),
        "qaoa_energy": round(float(qaoa_energy), 6),
        "classical_optimal": int(classical_optimal),
        "best_partition": best_partition,
        "approximation_ratio": round(float(approx_ratio), 6),
        "circuit_depth": circuit_depth,
        "p_layers": p,
        "opt_gammas": opt_params[:p].tolist(),
        "opt_betas": opt_params[p:].tolist(),
        "optimizer_iterations": int(result.nfev),
        "classical_time_ms": round(classical_time_ms, 3),
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved → {RESULTS_PATH}")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
