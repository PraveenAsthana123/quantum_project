#!/usr/bin/env python3

from pathlib import Path

import pandas as pd
import panel as pn
import plotly.express as px
import networkx as nx

ROOT = Path("/mnt/deepa/quantum")

pn.extension("plotly")

venv_root = ROOT / "venvs"
github_root = ROOT / "github"

envs = sorted([
    p.name for p in venv_root.iterdir()
    if p.is_dir()
]) if venv_root.exists() else []

categories = []

if github_root.exists():
    for category in sorted(github_root.iterdir()):
        if not category.is_dir():
            continue

        repos = sum(
            1 for p in category.iterdir()
            if p.is_dir() and (p / ".git").exists()
        )

        categories.append({
            "category": category.name,
            "repositories": repos,
        })

df = pd.DataFrame(categories)

if df.empty:
    fig = px.bar(
        pd.DataFrame({"category": ["none"], "repositories": [0]}),
        x="category",
        y="repositories",
        title="Quantum GitHub Repository Inventory",
    )
else:
    fig = px.bar(
        df,
        x="category",
        y="repositories",
        title="Quantum GitHub Repository Inventory",
    )

# Small architecture graph.
g = nx.DiGraph()

g.add_edges_from([
    ("Business Workload", "Platform"),
    ("Platform", "Compiler"),
    ("Compiler", "Simulator"),
    ("Compiler", "QPU"),
    ("QPU", "Testing"),
    ("Simulator", "Testing"),
    ("Testing", "Data"),
    ("Data", "Control Tower"),
])

architecture_text = "\n".join(
    f"{a} -> {b}" for a, b in g.edges()
)

template = pn.template.FastListTemplate(
    title="Quantum Engineering Control Tower",
)

template.main.append(
    pn.pane.Markdown(
        f"""
# Quantum Engineering Lab

**Root:** `{ROOT}`

**Virtual environments:** {len(envs)}

**GitHub categories:** {len(categories)}

## Environments

`{", ".join(envs)}`

## Architecture

```text
{architecture_text}
```
"""
    )
)

template.main.append(
    pn.pane.Plotly(fig, sizing_mode="stretch_width")
)

template.servable()
