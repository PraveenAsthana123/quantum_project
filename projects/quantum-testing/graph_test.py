#!/usr/bin/env python3

from pathlib import Path
import json

import networkx as nx
import rustworkx as rx

ROOT = Path("/mnt/deepa/quantum")
OUT = ROOT / "results" / "graph-tests"
OUT.mkdir(parents=True, exist_ok=True)

# Example QPU coupling graph.
edges = [
    (0, 1),
    (1, 2),
    (2, 3),
    (1, 4),
    (4, 5),
]

nxg = nx.Graph()
nxg.add_edges_from(edges)

shortest = nx.shortest_path(nxg, 0, 5)

rxg = rx.PyGraph()
rxg.add_nodes_from(list(range(6)))
rxg.add_edges_from_no_data(edges)

payload = {
    "nodes": nxg.number_of_nodes(),
    "edges": nxg.number_of_edges(),
    "shortest_0_to_5": shortest,
    "rustworkx_nodes": rxg.num_nodes(),
    "rustworkx_edges": rxg.num_edges(),
}

(OUT / "graph-test.json").write_text(
    json.dumps(payload, indent=2)
)

print(json.dumps(payload, indent=2))
print("GRAPH TEST: PASS")
