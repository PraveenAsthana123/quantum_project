"""
Q24 — Quantum Internet
quantum_network_stack.py

4-layer quantum network protocol stack simulation.
  L1: Physical — photon transmission, fiber loss
  L2: Link — entanglement generation, purification
  L3: Network — routing, entanglement swapping
  L4: Application — QKD, distributed quantum computing

Simulates a 3-node quantum network.

Outputs: data/network_stack_results.json
"""

import json
import math
import os
import random
import time


# ---------------------------------------------------------------------------
# L1: Physical Layer
# ---------------------------------------------------------------------------

class PhysicalLayer:
    """Photon transmission over optical fibre."""

    FIBER_LOSS_DB_PER_KM = 0.2
    SPEED_OF_LIGHT_KM_S = 2.0e5    # in fibre (c/n, n≈1.5)

    def __init__(self, wavelength_nm: float = 1550.0,
                 eta_detector: float = 0.85,
                 dark_count_rate_Hz: float = 100.0):
        self.wavelength_nm = wavelength_nm
        self.eta_detector = eta_detector
        self.dark_count_rate = dark_count_rate_Hz

    def transmission(self, distance_km: float) -> float:
        return 10 ** (-self.FIBER_LOSS_DB_PER_KM * distance_km / 10.0)

    def photon_arrival_probability(self, distance_km: float,
                                    eta_source: float = 0.9) -> float:
        return eta_source * self.transmission(distance_km) * self.eta_detector

    def propagation_delay_ms(self, distance_km: float) -> float:
        return distance_km / self.SPEED_OF_LIGHT_KM_S * 1000.0  # ms


# ---------------------------------------------------------------------------
# L2: Link Layer
# ---------------------------------------------------------------------------

class LinkLayer:
    """Heralded entanglement generation and purification."""

    def __init__(self, physical: PhysicalLayer,
                 rep_rate_hz: float = 1e6,
                 photon_pair_prob: float = 0.1,
                 purification: bool = True):
        self.physical = physical
        self.rep_rate = rep_rate_hz
        self.p_pair = photon_pair_prob
        self.purification = purification

    def link_generation_rate(self, distance_km: float) -> float:
        """Heralded Bell pair rate [Hz]."""
        eta = self.physical.photon_arrival_probability(distance_km / 2.0)
        p_link = self.p_pair * eta ** 2
        return self.rep_rate * p_link

    def link_fidelity(self, distance_km: float) -> float:
        """Initial link fidelity (multi-photon + fibre depolarisation)."""
        alpha = 5e-4
        return max(0.5, 1.0 - self.p_pair / 2.0 - alpha * distance_km)

    def purified_fidelity(self, f: float) -> float:
        """One DEJMPS purification round."""
        p_succ = (f ** 2 + (5.0 / 9.0) * (1.0 - f) ** 2
                  + (4.0 / 9.0) * 2.0 * f * (1.0 - f))
        if p_succ < 1e-12:
            return f
        return (f ** 2 + (1.0 / 9.0) * (1.0 - f) ** 2) / p_succ


# ---------------------------------------------------------------------------
# L3: Network Layer
# ---------------------------------------------------------------------------

class NetworkLayer:
    """Routing and entanglement swapping."""

    def __init__(self, link: LinkLayer):
        self.link = link

    def entanglement_swap(self, f1: float, f2: float,
                           p_bsm: float = 0.45) -> tuple:
        """
        Swap two adjacent links.
        Returns (f_out, p_success).
        """
        f_out = f1 * f2 + (1.0 - f1) * (1.0 - f2) / 3.0
        return f_out, p_bsm

    def route(self, topology: dict, src: str, dst: str) -> list:
        """
        Simple shortest-path routing (BFS) over the topology graph.
        topology: {node: [neighbour, ...]}
        """
        from collections import deque
        visited = {src}
        queue = deque([[src]])
        while queue:
            path = queue.popleft()
            node = path[-1]
            if node == dst:
                return path
            for nbr in topology.get(node, []):
                if nbr not in visited:
                    visited.add(nbr)
                    queue.append(path + [nbr])
        return []


# ---------------------------------------------------------------------------
# L4: Application Layer
# ---------------------------------------------------------------------------

class ApplicationLayer:
    """QKD and distributed quantum computing over end-to-end entanglement."""

    def __init__(self):
        pass

    def qkd_key_rate(self, entanglement_rate_hz: float,
                      qber: float = 0.02) -> float:
        """
        Secret key rate from continuous entanglement-based QKD.
        r = R_ent * (1 - h(QBER) - h(QBER))  [Devetak-Winter bound]
        """
        def h2(p):
            if p <= 0 or p >= 1:
                return 0.0
            return -p * math.log2(p) - (1 - p) * math.log2(1 - p)
        return max(0.0, entanglement_rate_hz * (1.0 - 2.0 * h2(qber)))

    def teleportation_fidelity(self, shared_fidelity: float) -> float:
        """
        Fidelity of teleported qubit using shared Werner state.
        F_tel = (2*F_epr + 1) / 3
        """
        return (2.0 * shared_fidelity + 1.0) / 3.0


# ---------------------------------------------------------------------------
# 3-node network simulation
# ---------------------------------------------------------------------------

def simulate_quantum_network(
        nodes: list = None,
        link_distances_km: dict = None,
        rep_rate_hz: float = 1e6,
        memory_t2_us: float = 500.0,
        qber: float = 0.02,
        seed: int = 42) -> dict:
    """
    Simulate a 3-node quantum network: Alice — Bob — Charlie.
    Compute end-to-end entanglement rate, QKD key rate, latency.
    """
    if nodes is None:
        nodes = ["Alice", "Bob", "Charlie"]
    if link_distances_km is None:
        link_distances_km = {("Alice", "Bob"): 100.0,
                              ("Bob", "Charlie"): 100.0}

    random.seed(seed)

    phys = PhysicalLayer()
    link = LinkLayer(phys, rep_rate_hz=rep_rate_hz)
    net = NetworkLayer(link)
    app = ApplicationLayer()

    # Compute per-link stats
    link_stats = {}
    for (n1, n2), dist in link_distances_km.items():
        rate = link.link_generation_rate(dist)
        fid = link.link_fidelity(dist)
        if link.purification:
            fid = link.purified_fidelity(fid)
        delay = phys.propagation_delay_ms(dist)
        link_stats[(n1, n2)] = {
            "distance_km": dist,
            "generation_rate_Hz": round(rate, 4),
            "fidelity": round(fid, 4),
            "propagation_delay_ms": round(delay, 4),
        }

    # Alice-Charlie end-to-end via Bob (entanglement swapping)
    l1 = link_stats[("Alice", "Bob")]
    l2 = link_stats[("Bob", "Charlie")]

    f_ac, p_swap = net.entanglement_swap(l1["fidelity"], l2["fidelity"])
    r_ac = min(l1["generation_rate_Hz"],
               l2["generation_rate_Hz"]) * p_swap
    latency_ms = l1["propagation_delay_ms"] + l2["propagation_delay_ms"]

    key_rate = app.qkd_key_rate(r_ac, qber=qber)
    teleport_fid = app.teleportation_fidelity(f_ac)

    # Protocol overhead: classical signalling + CC latency
    classical_latency_ms = latency_ms * 2.0  # round-trip for heralding
    overhead_frac = classical_latency_ms / (1000.0 / rep_rate_hz * 1000.0)

    topology = {"Alice": ["Bob"], "Bob": ["Alice", "Charlie"],
                "Charlie": ["Bob"]}
    route_ac = net.route(topology, "Alice", "Charlie")

    result = {
        "nodes": nodes,
        "links": [
            {"nodes": list(k), **v}
            for k, v in link_stats.items()
        ],
        "end_to_end": {
            "path": route_ac,
            "fidelity": round(f_ac, 4),
            "entanglement_rate_Hz": round(r_ac, 4),
        },
        "entanglement_rate_Hz": round(r_ac, 4),
        "key_rate_bps": round(key_rate, 4),
        "latency_ms": round(latency_ms, 3),
        "protocol_overhead": round(overhead_frac, 4),
        "teleportation_fidelity": round(teleport_fid, 4),
        "qber": qber,
    }
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Quantum Internet Network Stack Simulation ===\n")

    result = simulate_quantum_network(
        nodes=["Alice", "Bob", "Charlie"],
        link_distances_km={("Alice", "Bob"): 100.0,
                            ("Bob", "Charlie"): 100.0},
        rep_rate_hz=1e6,
        memory_t2_us=500.0,
        qber=0.02,
    )

    print("Nodes:", " — ".join(result["nodes"]))
    print("\nPer-link statistics:")
    for link in result["links"]:
        print(f"  {link['nodes'][0]}-{link['nodes'][1]}: "
              f"{link['distance_km']} km  "
              f"rate={link['generation_rate_Hz']:.4f} Hz  "
              f"fidelity={link['fidelity']:.4f}  "
              f"delay={link['propagation_delay_ms']:.2f} ms")

    print(f"\nEnd-to-end (Alice→Charlie):")
    e2e = result["end_to_end"]
    print(f"  Path              : {' → '.join(e2e['path'])}")
    print(f"  Entanglement rate : {e2e['entanglement_rate_Hz']:.4f} Hz")
    print(f"  Fidelity          : {e2e['fidelity']:.4f}")
    print(f"  QKD key rate      : {result['key_rate_bps']:.4f} bps")
    print(f"  Latency           : {result['latency_ms']:.2f} ms")
    print(f"  Teleport fidelity : {result['teleportation_fidelity']:.4f}")

    os.makedirs("data", exist_ok=True)
    out_path = "data/network_stack_results.json"
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=2)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
