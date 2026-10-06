"""
Quantum Architecture Control Tower — Part 1
Sections: Architecture, Tech Stack, User Stories, Manual Process, Pipeline Process
"""
from __future__ import annotations

import subprocess
import importlib.metadata
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pkg_version(name: str) -> tuple[str, str]:
    """Return (version, status_emoji). Normalise common import aliases."""
    aliases = {
        "sklearn": "scikit-learn",
        "dwave-ocean-sdk": "dwave-ocean-sdk",
        "perceval-quandela": "perceval-quandela",
    }
    canonical = aliases.get(name, name)
    try:
        v = importlib.metadata.version(canonical)
        return v, "✅"
    except importlib.metadata.PackageNotFoundError:
        return "—", "❌"


# ─────────────────────────────────────────────────────────────────────────────
# Section 1 — Architecture
# ─────────────────────────────────────────────────────────────────────────────

def render_architecture():
    st.subheader("🏗️ Architecture", divider="blue")
    tab_ov, tab_hld, tab_lld = st.tabs(["Architect Overview", "HLD", "LLD"])

    # ── Overview ──────────────────────────────────────────────────────────────
    with tab_ov:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Components", "12", help="Logical subsystems")
        c2.metric("Integration Points", "8", help="External + internal interfaces")
        c3.metric("API Endpoints", "15", help="REST + gRPC contracts")
        c4.metric("Data Flows", "6", help="ETL / streaming pipelines")

        st.markdown("#### Architecture Decision Records (ADR)")
        adrs = pd.DataFrame([
            {"ID": "ADR-001", "Decision": "Hybrid Classical-Quantum Orchestration",        "Status": "Accepted", "Date": "2026-01-10", "Rationale": "NISQ era requires classical pre/post-processing; pure quantum infeasible at scale"},
            {"ID": "ADR-002", "Decision": "PennyLane as primary QML framework",             "Status": "Accepted", "Date": "2026-01-18", "Rationale": "Device-agnostic, autodiff support, Qiskit interop via plugin"},
            {"ID": "ADR-003", "Decision": "Qiskit for circuit compilation + hardware runs", "Status": "Accepted", "Date": "2026-02-03", "Rationale": "IBM Runtime provides error suppression, Sampler/Estimator primitives"},
            {"ID": "ADR-004", "Decision": "REST over gRPC for external API",                "Status": "Accepted", "Date": "2026-02-14", "Rationale": "Broader client compatibility; gRPC used internally for low-latency service mesh"},
            {"ID": "ADR-005", "Decision": "Mitiq for error mitigation (ZNE/PEC)",           "Status": "Proposed", "Date": "2026-03-01", "Rationale": "Framework-agnostic; zero-cost integration with Qiskit + Cirq"},
            {"ID": "ADR-006", "Decision": "ML-KEM + ML-DSA for all new cryptographic ops",  "Status": "Accepted", "Date": "2026-03-20", "Rationale": "NIST FIPS 203/204 finalized; harvest-now-decrypt-later threat active"},
            {"ID": "ADR-007", "Decision": "Stateless job orchestration via FastAPI + Redis", "Status": "Accepted", "Date": "2026-04-05", "Rationale": "Horizontal scaling of job queue; QPU jobs are long-lived, async by nature"},
        ])
        st.dataframe(adrs, use_container_width=True, hide_index=True)

        st.markdown("#### System Context Diagram")
        nodes = ["Actor", "Frontend", "API Gateway", "Orchestrator", "QPU Simulator",
                 "Classical Solver", "ML Engine", "Results Store", "Monitoring"]
        node_colors = ["#4CAF50","#2196F3","#FF9800","#9C27B0",
                       "#00BCD4","#FF5722","#E91E63","#607D8B","#795548"]
        link_src  = [0, 1, 2, 3, 3, 3, 4, 5, 6, 3]
        link_tgt  = [1, 2, 3, 4, 5, 6, 7, 7, 7, 8]
        link_val  = [5, 5, 5, 3, 3, 3, 2, 2, 2, 1]
        fig_sankey = go.Figure(go.Sankey(
            node=dict(label=nodes, color=node_colors, pad=20, thickness=20),
            link=dict(source=link_src, target=link_tgt, value=link_val,
                      color=["rgba(99,110,250,0.3)"]*len(link_src)),
        ))
        fig_sankey.update_layout(title="Quantum Lab — System Context", height=380,
                                 margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_sankey, use_container_width=True)

        st.markdown("#### Architecture Principles")
        principles = {
            "🔀 Hybrid-First": "Every algorithm has a classical fallback. Classical and quantum paths are benchmarked side-by-side. No quantum-only production path without proven advantage.",
            "☁️ Cloud-Native": "Stateless services, container-packaged workloads, QPU backends abstracted behind a provider interface. Local simulators used for dev/test.",
            "🔐 Quantum-Safe": "All new cryptographic operations use ML-KEM / ML-DSA. CBOM maintained. Harvest-now-decrypt-later risk tracked per asset.",
            "🔭 Observable": "Every quantum job emits structured logs, metrics (circuit depth, shots, fidelity, cost) and traces. Dashboards cover both classical and quantum dimensions.",
            "💪 Resilient": "QPU unavailability falls back to Aer simulator transparently. Job retries with exponential backoff. Result validation gates before publishing.",
        }
        for title, body in principles.items():
            with st.expander(title):
                st.write(body)

    # ── HLD ───────────────────────────────────────────────────────────────────
    with tab_hld:
        st.markdown("#### High-Level Design — Block Diagram")
        # Draw blocks as shapes; arrows as annotations
        fig_hld = go.Figure()
        fig_hld.update_xaxes(range=[0, 10], showgrid=False, zeroline=False, visible=False)
        fig_hld.update_yaxes(range=[0, 10], showgrid=False, zeroline=False, visible=False)
        fig_hld.update_layout(height=500, margin=dict(l=10, r=10, t=30, b=10),
                               plot_bgcolor="rgba(0,0,0,0)")

        blocks = [
            # (x0, y0, x1, y1, label, color)
            (0.3, 8.5, 2.2, 9.5, "User Layer",        "#E3F2FD"),
            (3.5, 8.5, 6.5, 9.5, "API Gateway",        "#FFF9C4"),
            (3.5, 6.5, 6.5, 7.5, "Orchestration",      "#FCE4EC"),
            (0.3, 4.3, 2.8, 5.3, "Quantum Processing", "#E8F5E9"),
            (3.8, 4.3, 6.2, 5.3, "Classical ML",       "#FFF3E0"),
            (7.2, 4.3, 9.7, 5.3, "Data Pipeline",      "#EDE7F6"),
            (3.5, 2.0, 6.5, 3.0, "Storage Layer",      "#E0F7FA"),
            (7.2, 6.5, 9.7, 7.5, "Monitoring",         "#EFEBE9"),
        ]
        colors_border = ["#1565C0","#F9A825","#C62828","#2E7D32","#E65100","#4527A0","#00838F","#4E342E"]
        for (x0,y0,x1,y1,label,fill), border in zip(blocks, colors_border):
            fig_hld.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
                              fillcolor=fill, line=dict(color=border, width=2))
            fig_hld.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=f"<b>{label}</b>",
                                   showarrow=False, font=dict(size=11, color=border))

        arrows = [
            (1.25,8.5,5.0,9.5,""), (5.0,8.5,5.0,7.5,"REST"),
            (5.0,6.5,1.55,5.3,"gRPC"), (5.0,6.5,5.0,5.3,""),
            (5.0,6.5,8.45,5.3,""), (1.55,4.3,5.0,3.0,""),
            (5.0,4.3,5.0,3.0,""), (8.45,4.3,5.0,3.0,""),
            (8.45,6.5,8.45,5.3,"logs"),
        ]
        for (ax,ay,bx,by,lbl) in arrows:
            fig_hld.add_annotation(x=bx, y=by, ax=ax, ay=ay, axref="x", ayref="y",
                                   xref="x", yref="y", arrowhead=2, arrowsize=1.2,
                                   arrowcolor="#555", text=lbl, font=dict(size=9, color="#555"))
        st.plotly_chart(fig_hld, use_container_width=True)

        st.markdown("#### HLD Component Inventory")
        hld_comps = pd.DataFrame([
            {"Component":"API Gateway",       "Responsibility":"Auth, routing, rate-limit",      "Technology":"FastAPI + Nginx",    "Owner":"Platform",  "Status":"Built"},
            {"Component":"Job Orchestrator",  "Responsibility":"Quantum job lifecycle mgmt",      "Technology":"Python + Redis",     "Owner":"Core",      "Status":"Built"},
            {"Component":"Circuit Builder",   "Responsibility":"Compose, validate, transpile",   "Technology":"Qiskit + PennyLane", "Owner":"Quantum",   "Status":"Built"},
            {"Component":"QPU Adapter",       "Responsibility":"Backend abstraction (sim/cloud)", "Technology":"Qiskit Runtime",     "Owner":"Quantum",   "Status":"In Progress"},
            {"Component":"Classical ML",      "Responsibility":"Baseline models, feature eng",   "Technology":"sklearn + XGBoost",  "Owner":"Data",      "Status":"Built"},
            {"Component":"Error Mitigator",   "Responsibility":"ZNE, PEC, readout correction",   "Technology":"Mitiq",              "Owner":"Quantum",   "Status":"In Progress"},
            {"Component":"PQC Module",        "Responsibility":"Crypto inventory, migration",     "Technology":"cryptography+liboqs","Owner":"Security",  "Status":"Built"},
            {"Component":"Results Store",     "Responsibility":"Persist circuits+results",        "Technology":"SQLite → Postgres",  "Owner":"Data",      "Status":"Built"},
            {"Component":"Monitoring",        "Responsibility":"Metrics, logs, traces",           "Technology":"Prometheus+Grafana", "Owner":"Ops",       "Status":"Planned"},
        ])
        st.dataframe(hld_comps, use_container_width=True, hide_index=True)

        st.markdown("#### Integration Map")
        integ = pd.DataFrame([
            {"Source":"Frontend",       "Target":"API Gateway",  "Protocol":"HTTPS/REST","Auth":"JWT",        "SLA":"<200ms"},
            {"Source":"API Gateway",    "Target":"Orchestrator", "Protocol":"gRPC",      "Auth":"mTLS",       "SLA":"<50ms"},
            {"Source":"Orchestrator",   "Target":"Qiskit Aer",   "Protocol":"Python SDK","Auth":"N/A",        "SLA":"<60s"},
            {"Source":"Orchestrator",   "Target":"IBM Runtime",  "Protocol":"REST+SDK",  "Auth":"API Key",    "SLA":"<300s"},
            {"Source":"Orchestrator",   "Target":"D-Wave Leap",  "Protocol":"REST",      "Auth":"API Token",  "SLA":"<120s"},
            {"Source":"Error Mitigator","Target":"QPU Adapter",  "Protocol":"Python SDK","Auth":"N/A",        "SLA":"<5s overhead"},
            {"Source":"PQC Module",     "Target":"Results Store","Protocol":"SQLAlchemy","Auth":"DB Role",    "SLA":"<100ms"},
            {"Source":"All Services",   "Target":"Monitoring",   "Protocol":"OTLP",      "Auth":"Bearer",     "SLA":"async"},
        ])
        st.dataframe(integ, use_container_width=True, hide_index=True)

    # ── LLD ───────────────────────────────────────────────────────────────────
    with tab_lld:
        st.markdown("#### Module Hierarchy")
        treemap_data = dict(
            ids=["QuantumLab","core","api","quantum","classical","ui","data","monitoring",
                 "core/config","core/auth","core/exceptions",
                 "api/jobs","api/circuits","api/results","api/cbom",
                 "quantum/circuit_builder","quantum/transpiler","quantum/error_mitigation","quantum/qml","quantum/optimizer",
                 "classical/baseline","classical/feature_eng","classical/benchmark",
                 "ui/portal","ui/banking","ui/logistics","ui/pqc",
                 "data/loaders","data/schema","data/migrations",
                 "monitoring/metrics","monitoring/traces"],
            labels=["QuantumLab","core","api","quantum","classical","ui","data","monitoring",
                    "config","auth","exceptions",
                    "jobs","circuits","results","cbom",
                    "circuit_builder","transpiler","error_mitigation","qml","optimizer",
                    "baseline","feature_eng","benchmark",
                    "portal","banking","logistics","pqc",
                    "loaders","schema","migrations",
                    "metrics","traces"],
            parents=["","QuantumLab","QuantumLab","QuantumLab","QuantumLab","QuantumLab","QuantumLab","QuantumLab",
                     "core","core","core",
                     "api","api","api","api",
                     "quantum","quantum","quantum","quantum","quantum",
                     "classical","classical","classical",
                     "ui","ui","ui","ui",
                     "data","data","data",
                     "monitoring","monitoring"],
        )
        fig_tree = px.treemap(
            names=treemap_data["labels"],
            ids=treemap_data["ids"],
            parents=treemap_data["parents"],
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        fig_tree.update_traces(root_color="lightgrey")
        fig_tree.update_layout(height=380, margin=dict(l=5, r=5, t=30, b=5))
        st.plotly_chart(fig_tree, use_container_width=True)

        st.markdown("#### API Contracts")
        api_contracts = pd.DataFrame([
            {"Endpoint":"/api/v1/jobs",           "Method":"POST",  "Input":"CircuitSpec JSON",     "Output":"JobID + status",           "Auth":"JWT","Rate Limit":"60/min"},
            {"Endpoint":"/api/v1/jobs/{id}",      "Method":"GET",   "Input":"job_id",               "Output":"JobStatus + progress",      "Auth":"JWT","Rate Limit":"120/min"},
            {"Endpoint":"/api/v1/jobs/{id}/result","Method":"GET",  "Input":"job_id",               "Output":"Counts/Statevector JSON",   "Auth":"JWT","Rate Limit":"60/min"},
            {"Endpoint":"/api/v1/circuits",       "Method":"POST",  "Input":"OpenQASM3 string",     "Output":"circuit_id + validation",   "Auth":"JWT","Rate Limit":"30/min"},
            {"Endpoint":"/api/v1/circuits/transpile","Method":"POST","Input":"circuit_id+backend",  "Output":"transpiled_qasm+metrics",   "Auth":"JWT","Rate Limit":"20/min"},
            {"Endpoint":"/api/v1/backends",       "Method":"GET",   "Input":"—",                    "Output":"Backend list+availability", "Auth":"JWT","Rate Limit":"60/min"},
            {"Endpoint":"/api/v1/pqc/cbom",       "Method":"POST",  "Input":"Directory path",       "Output":"CBOM JSON (CycloneDX)",     "Auth":"JWT","Rate Limit":"10/min"},
            {"Endpoint":"/api/v1/pqc/benchmark",  "Method":"GET",   "Input":"algorithms[] query",   "Output":"Benchmark results JSON",    "Auth":"JWT","Rate Limit":"5/min"},
            {"Endpoint":"/api/v1/experiments",    "Method":"GET",   "Input":"filters query",        "Output":"Experiment list + metrics", "Auth":"JWT","Rate Limit":"60/min"},
        ])
        st.dataframe(api_contracts, use_container_width=True, hide_index=True)

        st.markdown("#### Database Schema")
        db_schema = pd.DataFrame([
            {"Entity":"QuantumJob",  "Key Attributes":"id, status, backend, shots, created_at, completed_at, error",         "Relationships":"has Circuit, has Result, belongs to Experiment"},
            {"Entity":"Circuit",     "Key Attributes":"id, qasm, n_qubits, depth, gate_count, backend_target, transpiled",   "Relationships":"used by QuantumJob, has ResourceEstimate"},
            {"Entity":"Result",      "Key Attributes":"id, counts, statevector, fidelity, error_rate, mitigation_method",     "Relationships":"belongs to QuantumJob, has Benchmark"},
            {"Entity":"Benchmark",   "Key Attributes":"id, algorithm, latency_ms, key_size_bytes, sig_size_bytes, quantum_safe","Relationships":"belongs to Experiment"},
            {"Entity":"Experiment",  "Key Attributes":"id, name, description, tags, classical_baseline, quantum_result",      "Relationships":"has many QuantumJobs, has Benchmark"},
            {"Entity":"User",        "Key Attributes":"id, email, role, api_key_hash, created_at, last_login",                "Relationships":"owns Experiments, owns Jobs"},
        ])
        st.dataframe(db_schema, use_container_width=True, hide_index=True)

        st.markdown("#### Quantum Job Lifecycle — Sequence")
        base = datetime(2026, 9, 21, 10, 0, 0)
        seq_data = pd.DataFrame([
            dict(Task="Submit Job",         Start=base+timedelta(seconds=0),  Finish=base+timedelta(seconds=1),   Actor="Client"),
            dict(Task="Auth & Validate",    Start=base+timedelta(seconds=1),  Finish=base+timedelta(seconds=2),   Actor="API Gateway"),
            dict(Task="Enqueue",            Start=base+timedelta(seconds=2),  Finish=base+timedelta(seconds=3),   Actor="Orchestrator"),
            dict(Task="Transpile Circuit",  Start=base+timedelta(seconds=3),  Finish=base+timedelta(seconds=8),   Actor="Quantum Engine"),
            dict(Task="Classical Baseline", Start=base+timedelta(seconds=8),  Finish=base+timedelta(seconds=20),  Actor="Classical ML"),
            dict(Task="QPU Execution",      Start=base+timedelta(seconds=20), Finish=base+timedelta(seconds=90),  Actor="QPU Adapter"),
            dict(Task="Error Mitigation",   Start=base+timedelta(seconds=90), Finish=base+timedelta(seconds=95),  Actor="Mitiq"),
            dict(Task="Result Validation",  Start=base+timedelta(seconds=95), Finish=base+timedelta(seconds=98),  Actor="Orchestrator"),
            dict(Task="Persist Result",     Start=base+timedelta(seconds=98), Finish=base+timedelta(seconds=100), Actor="Results Store"),
            dict(Task="Notify Client",      Start=base+timedelta(seconds=100),Finish=base+timedelta(seconds=101), Actor="API Gateway"),
        ])
        fig_seq = px.timeline(seq_data, x_start="Start", x_end="Finish", y="Task",
                              color="Actor", title="Quantum Job Lifecycle",
                              color_discrete_sequence=px.colors.qualitative.Bold)
        fig_seq.update_yaxes(autorange="reversed")
        fig_seq.update_layout(height=360, margin=dict(l=5, r=5, t=40, b=5))
        st.plotly_chart(fig_seq, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Section 2 — Tech Stack
# ─────────────────────────────────────────────────────────────────────────────

def render_tech_stack():
    st.subheader("🛠️ Tech Stack", divider="orange")
    tab_matrix, tab_deps = st.tabs(["Stack Matrix", "Dependencies"])

    PACKAGES = [
        ("qiskit",            "Quantum SDK",   "Gate-model circuits, transpilation, IBM Runtime"),
        ("qiskit-aer",        "Quantum SDK",   "Local statevector / noise simulation"),
        ("qiskit-algorithms", "Quantum SDK",   "VQE, QAOA, QPE reference implementations"),
        ("qiskit-optimization","Quantum SDK",  "QUBO, MinimumEigenOptimizer, QAOA optimization"),
        ("qiskit-finance",    "Quantum SDK",   "Portfolio optimization, option pricing"),
        ("qiskit-nature",     "Quantum SDK",   "Molecular Hamiltonians, VQE chemistry"),
        ("pennylane",         "Quantum SDK",   "QML, variational circuits, autodiff"),
        ("mitiq",             "Quantum SDK",   "Error mitigation — ZNE, PEC, CDR"),
        ("stim",              "Quantum SDK",   "Stabilizer / QEC simulation"),
        ("openfermion",       "Quantum SDK",   "Fermionic Hamiltonians for chemistry"),
        ("qutip",             "Quantum SDK",   "Open quantum systems, master equations"),
        ("scqubits",          "Quantum SDK",   "Superconducting qubit physics"),
        ("cirq",              "Quantum SDK",   "Hardware-native circuits, Cirq devices"),
        ("perceval-quandela", "Quantum SDK",   "Photonic quantum computing"),
        ("netket",            "Quantum SDK",   "Neural quantum states, variational Monte Carlo"),
        ("dwave-ocean-sdk",   "Quantum SDK",   "Quantum annealing, QUBO, D-Wave samplers"),
        ("ortools",           "Optimization",  "Vehicle routing, scheduling, CP-SAT"),
        ("numpy",             "Scientific",    "Numerical computing"),
        ("scipy",             "Scientific",    "Linear algebra, optimization, signal processing"),
        ("pandas",            "Data",          "DataFrames, tabular data"),
        ("sklearn",           "Classical ML",  "Baselines: LR, RF, SVM, PCA"),
        ("xgboost",           "Classical ML",  "Gradient boosting for classical baselines"),
        ("plotly",            "UI",            "Interactive charts"),
        ("streamlit",         "UI",            "Rapid ML/data apps"),
        ("fastapi",           "Infrastructure","REST API framework"),
        ("cryptography",      "Security",      "Classical crypto primitives"),
        ("kaggle",            "Data",          "Dataset downloads"),
    ]

    with tab_matrix:
        rows = []
        for pkg, cat, purpose in PACKAGES:
            ver, status = _pkg_version(pkg)
            rows.append({"SDK / Library": pkg, "Category": cat, "Version": ver,
                         "Status": status, "Purpose": purpose})
        df_stack = pd.DataFrame(rows)
        st.dataframe(df_stack, use_container_width=True, hide_index=True,
                     column_config={"Status": st.column_config.TextColumn(width="small")})

        st.markdown("#### Package Categories")
        cat_counts = df_stack.groupby("Category").size().reset_index(name="Count")
        fig_cat = px.bar(cat_counts, x="Category", y="Count",
                         color="Category", text="Count",
                         color_discrete_sequence=px.colors.qualitative.Bold)
        fig_cat.update_layout(showlegend=False, height=300,
                               margin=dict(l=5, r=5, t=20, b=5))
        st.plotly_chart(fig_cat, use_container_width=True)

        installed = df_stack[df_stack["Status"] == "✅"].shape[0]
        missing   = df_stack[df_stack["Status"] == "❌"].shape[0]
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Packages", len(df_stack))
        col2.metric("Installed ✅", installed)
        col3.metric("Missing ❌", missing)

        st.markdown("#### Hardware Profile")
        hw = pd.DataFrame([
            {"Component":"CPU",  "Detail":"Intel / AMD x86-64 multi-core",        "Notes":"Quantum simulation is CPU-bound for <20 qubits"},
            {"Component":"GPU",  "Detail":"NVIDIA GTX 1080 Ti — 11 GB VRAM",      "Notes":"Qiskit-Aer GPU / CUDA-Q / PennyLane Lightning-GPU"},
            {"Component":"RAM",  "Detail":"32–64 GB DDR4",                        "Notes":"Full statevector for 28 qubits ≈ 4 GB; 30 qubits ≈ 16 GB"},
            {"Component":"Storage","Detail":"NVMe SSD /mnt/deepa",               "Notes":"Dataset + model checkpoint storage"},
            {"Component":"OS",   "Detail":"Linux (Ubuntu) — kernel 7.x",          "Notes":"Required for Qiskit-Aer GPU package"},
        ])
        st.dataframe(hw, use_container_width=True, hide_index=True)

    with tab_deps:
        st.markdown("#### Dependency Hierarchy")
        sun_ids     = ["root","qiskit-family","pennylane-family","classical-ml","infrastructure",
                       "qiskit","qiskit-aer","qiskit-algorithms","qiskit-optimization","qiskit-finance","qiskit-nature",
                       "pennylane","mitiq","cirq","stim","openfermion",
                       "sklearn","xgboost","scipy","numpy","pandas",
                       "fastapi","streamlit","plotly","cryptography"]
        sun_parents = ["","root","root","root","root",
                       "qiskit-family","qiskit-family","qiskit-family","qiskit-family","qiskit-family","qiskit-family",
                       "pennylane-family","pennylane-family","pennylane-family","pennylane-family","pennylane-family",
                       "classical-ml","classical-ml","classical-ml","classical-ml","classical-ml",
                       "infrastructure","infrastructure","infrastructure","infrastructure"]
        sun_vals    = [0,0,0,0,0,
                       5,4,3,3,3,3,
                       5,4,3,3,3,
                       5,4,4,4,4,
                       5,5,4,4]
        fig_sun = go.Figure(go.Sunburst(
            ids=sun_ids, labels=sun_ids, parents=sun_parents, values=sun_vals,
            branchvalues="total",
            marker=dict(colors=px.colors.qualitative.Pastel * 2),
        ))
        fig_sun.update_layout(height=420, margin=dict(l=5, r=5, t=20, b=5))
        st.plotly_chart(fig_sun, use_container_width=True)

        st.markdown("#### Install Command Generator")
        all_pkgs = [p[0] for p in PACKAGES]
        selected = st.multiselect("Select packages to install:", all_pkgs,
                                  default=["qiskit","pennylane","mitiq"])
        if selected:
            cmd = "pip install " + " ".join(selected)
            st.code(cmd, language="bash")

        st.markdown("#### Dependency Check")
        if st.button("Run `pip check`"):
            with st.spinner("Checking…"):
                result = subprocess.run(["pip", "check"], capture_output=True, text=True, timeout=30)
                out = result.stdout.strip() or "No conflicts detected."
                st.code(out, language="text")


# ─────────────────────────────────────────────────────────────────────────────
# Section 3 — User Stories
# ─────────────────────────────────────────────────────────────────────────────

def render_user_stories():
    st.subheader("📖 User Stories", divider="green")
    tab_map, tab_backlog = st.tabs(["Story Map", "Backlog"])

    EPICS = [
        "Quantum Circuit Engineering",
        "PQC Security",
        "Portfolio Optimization",
        "Error Mitigation",
        "Quantum Sensing",
    ]
    USER_TYPES = ["Data Scientist", "Security Architect", "Quantum Engineer", "Business Analyst"]

    STORY_COUNTS = [
        [4, 1, 5, 2],
        [2, 5, 3, 4],
        [5, 2, 3, 4],
        [3, 1, 5, 2],
        [3, 1, 4, 2],
    ]

    EPIC_STORIES = {
        "Quantum Circuit Engineering": [
            ("Quantum Engineer",    "build parameterized circuits",           "I can sweep parameters for variational algorithms"),
            ("Data Scientist",      "submit a circuit and get shot counts",   "I can compare quantum vs classical distributions"),
            ("Quantum Engineer",    "transpile to hardware topology",         "circuit depth is minimized for target QPU"),
            ("Quantum Engineer",    "inspect circuit depth and gate counts",  "I can estimate resource requirements before submitting"),
            ("Data Scientist",      "visualize Bloch sphere state",           "I understand single-qubit evolution"),
        ],
        "PQC Security": [
            ("Security Architect",  "scan a directory for crypto artifacts",  "I get a CBOM showing vulnerable algorithms"),
            ("Security Architect",  "benchmark ML-KEM vs RSA key sizes",      "I can justify PQC migration to stakeholders"),
            ("Business Analyst",    "see a migration roadmap Gantt chart",    "I can plan PQC adoption timeline"),
            ("Security Architect",  "set harvest-now-decrypt-later risk",     "I prioritize which data to protect first"),
        ],
        "Portfolio Optimization": [
            ("Data Scientist",      "run Markowitz baseline",                 "I have a classical comparison for QAOA"),
            ("Quantum Engineer",    "formulate portfolio as QUBO",            "QAOA can optimize the asset selection"),
            ("Business Analyst",    "see efficient frontier chart",           "I understand risk-return tradeoffs"),
            ("Data Scientist",      "benchmark QAOA vs classical on AUC",    "I can report quantum advantage (or lack thereof)"),
        ],
        "Error Mitigation": [
            ("Quantum Engineer",    "apply ZNE to any circuit",               "readout errors are reduced automatically"),
            ("Quantum Engineer",    "compare mitigated vs raw counts",        "I quantify error mitigation benefit"),
            ("Data Scientist",      "choose mitigation method from dropdown", "I experiment without writing boilerplate"),
        ],
        "Quantum Sensing": [
            ("Quantum Engineer",    "simulate NV-center Hamiltonian",         "I model magnetometry without real hardware"),
            ("Data Scientist",      "extract Fisher information",             "I compare quantum vs classical sensing precision"),
            ("Quantum Engineer",    "run Ramsey sequence simulation",         "I prototype sensing protocols"),
        ],
    }

    with tab_map:
        st.markdown("#### Story Map — Epics × User Types")
        heat_df = pd.DataFrame(STORY_COUNTS, index=EPICS, columns=USER_TYPES)
        fig_heat = px.imshow(heat_df, text_auto=True, color_continuous_scale="Blues",
                             labels=dict(x="User Type", y="Epic", color="Stories"),
                             aspect="auto")
        fig_heat.update_layout(height=320, margin=dict(l=5, r=5, t=20, b=5))
        st.plotly_chart(fig_heat, use_container_width=True)

        for epic, stories in EPIC_STORIES.items():
            with st.expander(f"📌 {epic}  ({len(stories)} stories)"):
                for role, action, outcome in stories:
                    st.markdown(f"- *As a* **{role}**, *I want to* **{action}**, *so that* {outcome}.")

    with tab_backlog:
        st.markdown("#### Sprint Backlog")
        backlog_raw = [
            ("US-001","Parameterized circuit builder","Quantum Circuit Engineering","P0","Done",8,"circuit,qiskit"),
            ("US-002","Circuit transpilation to hardware","Quantum Circuit Engineering","P0","Done",5,"transpile,qiskit"),
            ("US-003","Statevector + Bloch sphere viz","Quantum Circuit Engineering","P1","Done",3,"visualization"),
            ("US-004","Circuit depth / resource estimator","Quantum Circuit Engineering","P1","In Progress",5,"resource"),
            ("US-005","Multi-backend circuit submission","Quantum Circuit Engineering","P2","Todo",8,"cloud,ibm"),
            ("US-006","CBOM scanner (directory scan)","PQC Security","P0","Done",8,"pqc,cbom"),
            ("US-007","ML-KEM/ML-DSA benchmarking","PQC Security","P0","Done",5,"pqc,benchmark"),
            ("US-008","Migration roadmap generator","PQC Security","P1","Done",5,"pqc,migration"),
            ("US-009","Harvest-now-decrypt-later risk score","PQC Security","P1","In Progress",3,"pqc,risk"),
            ("US-010","CBOM CycloneDX export","PQC Security","P2","Todo",3,"pqc,export"),
            ("US-011","Markowitz portfolio baseline","Portfolio Optimization","P0","Done",5,"portfolio,classical"),
            ("US-012","QUBO portfolio formulation","Portfolio Optimization","P0","Done",8,"qaoa,qubo"),
            ("US-013","Efficient frontier visualization","Portfolio Optimization","P1","Done",3,"visualization"),
            ("US-014","QAOA convergence chart","Portfolio Optimization","P1","In Progress",5,"qaoa"),
            ("US-015","VRP classical OR-Tools solver","Portfolio Optimization","P1","Done",5,"vrp,logistics"),
            ("US-016","ZNE error mitigation","Error Mitigation","P0","In Progress",8,"mitiq,zne"),
            ("US-017","PEC error mitigation","Error Mitigation","P1","Todo",8,"mitiq,pec"),
            ("US-018","Readout correction matrix","Error Mitigation","P1","Todo",5,"readout"),
            ("US-019","Mitigated vs raw count comparison","Error Mitigation","P1","Todo",3,"visualization"),
            ("US-020","NV-center Hamiltonian simulator","Quantum Sensing","P2","Todo",8,"sensing,qutip"),
            ("US-021","Ramsey sequence simulation","Quantum Sensing","P2","Todo",5,"sensing"),
            ("US-022","Fisher information calculator","Quantum Sensing","P2","Todo",5,"metrology"),
        ]
        bl_df = pd.DataFrame(backlog_raw, columns=["ID","Title","Epic","Priority","Status","Points","Tags"])

        c1, c2, c3 = st.columns(3)
        epic_filter = c1.selectbox("Epic", ["All"] + EPICS)
        prio_filter = c2.selectbox("Priority", ["All","P0","P1","P2"])
        stat_filter = c3.selectbox("Status", ["All","Todo","In Progress","Done"])

        filtered = bl_df.copy()
        if epic_filter != "All": filtered = filtered[filtered["Epic"] == epic_filter]
        if prio_filter != "All": filtered = filtered[filtered["Priority"] == prio_filter]
        if stat_filter != "All": filtered = filtered[filtered["Status"] == stat_filter]
        st.dataframe(filtered, use_container_width=True, hide_index=True)

        st.markdown("#### Velocity (Story Points per Sprint)")
        sprints = [f"S{i}" for i in range(1, 7)]
        planned   = [21, 24, 18, 20, 22, 16]
        completed = [18, 20, 15, 22, 19, 14]
        fig_vel = go.Figure([
            go.Bar(name="Planned",   x=sprints, y=planned,   marker_color="#2196F3"),
            go.Bar(name="Completed", x=sprints, y=completed, marker_color="#4CAF50"),
        ])
        fig_vel.update_layout(barmode="group", height=280,
                               margin=dict(l=5, r=5, t=20, b=5))
        st.plotly_chart(fig_vel, use_container_width=True)

        st.markdown("#### Cumulative Flow")
        dates = pd.date_range("2026-03-01", periods=30, freq="2D")
        todo_      = [22 - int(i*0.5) for i in range(30)]
        in_prog    = [2 + int(i*0.3) - int(i*0.2) for i in range(30)]
        done_      = [0 + int(i*0.5) for i in range(30)]
        cfd = pd.DataFrame({"Date": dates, "Todo": todo_, "In Progress": in_prog, "Done": done_})
        fig_cfd = px.area(cfd, x="Date", y=["Todo","In Progress","Done"],
                          color_discrete_map={"Todo":"#FF7043","In Progress":"#FFA726","Done":"#66BB6A"})
        fig_cfd.update_layout(height=280, margin=dict(l=5, r=5, t=20, b=5))
        st.plotly_chart(fig_cfd, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Section 4 — Manual Process
# ─────────────────────────────────────────────────────────────────────────────

def render_manual_process():
    st.subheader("⚙️ Manual Process", divider="violet")
    tab_wf, tab_raci = st.tabs(["Workflow Steps", "RACI Matrix"])

    STEPS = [
        "Problem\nDefinition",
        "Literature\nReview",
        "Algorithm\nSelection",
        "Classical\nBaseline",
        "QUBO\nFormulation",
        "Circuit\nDesign",
        "Simulation",
        "Hardware\nRun",
        "Results\nAnalysis",
        "Documentation",
    ]
    STEP_DETAILS = [
        ("Define business problem, KPIs, constraints, quantum suitability criteria",
         "Business requirement", "Problem statement + feasibility note", "Whiteboard / Confluence", "1–2d", "Sponsor sign-off"),
        ("Survey quantum algorithms, review NISQ limitations, cite key papers",
         "Problem statement", "Literature summary + algorithm candidates", "Google Scholar / arXiv", "2–5d", "Algorithm shortlist"),
        ("Select best-fit algorithm (QAOA/VQE/Grover/QML) + classical fallback",
         "Algorithm candidates", "Decision record (ADR)", "ADR template", "1d", "Architecture review"),
        ("Implement and evaluate classical solver (OR-Tools, XGBoost, SVM)",
         "Dataset", "Baseline metrics (accuracy, AUC, runtime)", "Python + sklearn", "2–3d", "Baseline benchmark"),
        ("Encode problem as QUBO/Ising; verify penalty weights; check energy landscape",
         "Problem definition", "QUBO matrix Q, penalty tuning notes", "D-Wave dimod / numpy", "1–3d", "QUBO validation"),
        ("Build parameterized quantum circuit; validate gates; compute depth",
         "QUBO matrix", "Circuit QASM + resource estimate", "Qiskit / PennyLane", "2–5d", "Circuit review"),
        ("Run on noise-free + noisy simulators; apply error mitigation; benchmark",
         "Circuit", "Simulation results + noise analysis", "Qiskit Aer + Mitiq", "2–4d", "Sim pass/fail gate"),
        ("Submit to real QPU; monitor queue; collect raw counts",
         "Transpiled circuit", "Raw hardware counts", "IBM Runtime / D-Wave Leap", "0.5–2d", "Hardware quota check"),
        ("Compare quantum vs classical; statistical significance; resource usage",
         "Counts + baseline", "Results report + comparison table", "pandas + plotly", "1–2d", "Stakeholder review"),
        ("Write ADR, update README, notebook, architecture doc, publish results",
         "All artifacts", "Published report + docs", "Confluence / GitHub", "1d", "Doc review"),
    ]

    with tab_wf:
        st.markdown("#### End-to-End Quantum Workflow")
        n = len(STEPS)
        fig_flow = go.Figure()
        fig_flow.update_layout(
            xaxis=dict(range=[-0.5, n-0.5], showgrid=False, zeroline=False, visible=False),
            yaxis=dict(range=[0, 3], showgrid=False, zeroline=False, visible=False),
            height=200, margin=dict(l=5, r=5, t=20, b=5),
            plot_bgcolor="rgba(0,0,0,0)",
        )
        colors_flow = ["#EF9A9A","#FFCC80","#FFF59D","#A5D6A7","#80DEEA",
                       "#80CBC4","#90CAF9","#CE93D8","#F48FB1","#BCAAA4"]
        for i, (step, col) in enumerate(zip(STEPS, colors_flow)):
            x = i
            fig_flow.add_shape(type="rect", x0=x-0.42, y0=0.5, x1=x+0.42, y1=2.5,
                               fillcolor=col, line=dict(color="#888", width=1))
            fig_flow.add_annotation(x=x, y=1.5, text=step.replace("\n","<br>"),
                                    showarrow=False, font=dict(size=9))
            if i < n - 1:
                fig_flow.add_annotation(x=x+0.5, y=1.5, text="→",
                                        showarrow=False, font=dict(size=14, color="#555"))
        st.plotly_chart(fig_flow, use_container_width=True)

        steps_df = pd.DataFrame(
            [(STEPS[i].replace("\n"," "), det[0], det[1], det[2], det[3], det[4], det[5])
             for i, det in enumerate(STEP_DETAILS)],
            columns=["Step","Description","Input","Output","Tool","Duration","Gate"],
        )
        st.dataframe(steps_df, use_container_width=True, hide_index=True)

        st.markdown("#### Step Checklist")
        cols = st.columns(2)
        for i, step in enumerate(STEPS):
            col = cols[i % 2]
            col.checkbox(step.replace("\n"," "), value=(i < 6), key=f"step_chk_{i}")

    with tab_raci:
        ROLES = ["Quantum Engineer", "Data Scientist", "Security Architect", "TPM", "Biz Analyst"]
        RACI_DATA = {
            "Problem Definition":  ["C","C","C","A","R"],
            "Literature Review":   ["R","C","I","I","I"],
            "Algorithm Selection": ["R","C","I","A","I"],
            "Classical Baseline":  ["C","R","I","I","I"],
            "QUBO Formulation":    ["R","C","I","I","I"],
            "Circuit Design":      ["R","C","I","I","I"],
            "Simulation":          ["R","R","I","I","I"],
            "Hardware Run":        ["R","C","I","A","I"],
            "Results Analysis":    ["C","R","I","A","C"],
            "Documentation":       ["C","C","I","A","I"],
        }
        raci_df = pd.DataFrame(RACI_DATA, index=ROLES).T
        st.markdown("#### RACI Matrix")
        st.dataframe(raci_df, use_container_width=True)
        st.caption("R=Responsible · A=Accountable · C=Consulted · I=Informed")

        # Workload by role
        role_counts = {role: {"R":0,"A":0,"C":0,"I":0} for role in ROLES}
        for step, assignments in RACI_DATA.items():
            for role, val in zip(ROLES, assignments):
                role_counts[role][val] += 1
        workload = pd.DataFrame(role_counts).T.reset_index()
        workload.columns = ["Role","R","A","C","I"]
        fig_raci = px.bar(workload.melt(id_vars="Role", value_vars=["R","A","C","I"]),
                          x="Role", y="value", color="variable", barmode="stack",
                          color_discrete_map={"R":"#EF5350","A":"#FF7043","C":"#42A5F5","I":"#B0BEC5"},
                          labels={"value":"Count","variable":"Type"})
        fig_raci.update_layout(height=320, margin=dict(l=5, r=5, t=20, b=5))
        st.plotly_chart(fig_raci, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Section 5 — Pipeline Process
# ─────────────────────────────────────────────────────────────────────────────

def render_pipeline_process():
    st.subheader("🔁 Pipeline Process", divider="red")
    tab_dag, tab_hist = st.tabs(["Pipeline DAG", "Job History"])

    PIPELINE_STAGES = [
        ("Code Commit",       "git",                    2,  99.9, "Dev"),
        ("Lint / Format",     "ruff + black",           1,  98.5, "Dev"),
        ("Unit Tests",        "pytest",                 5,  97.0, "Dev"),
        ("Classical Baseline","sklearn + XGBoost",     10,  99.0, "Data"),
        ("Circuit Validation","Qiskit transpiler",      3,  95.0, "Quantum"),
        ("Simulation Tests",  "Qiskit Aer",            20,  93.0, "Quantum"),
        ("Noise Analysis",    "Qiskit Aer noise model", 5,  90.0, "Quantum"),
        ("Resource Estimate", "QDK Resource Estimator", 2,  98.0, "Quantum"),
        ("QPU Queue",         "IBM Runtime / D-Wave",  60,  85.0, "Quantum"),
        ("Hardware Run",      "Real QPU",             120,  80.0, "Quantum"),
        ("Result Validation", "Custom validator",       5,  96.0, "QA"),
        ("Deploy / Publish",  "Git + Streamlit",        3,  99.0, "Ops"),
    ]

    with tab_dag:
        st.markdown("#### CI/CD Pipeline — Stage Flow (Sankey)")
        stage_names = [s[0] for s in PIPELINE_STAGES]
        n = len(stage_names)
        src = list(range(n - 1))
        tgt = list(range(1, n))
        vals = [10] * (n - 1)
        node_colors_p = (
            ["#4CAF50"] * 3 +        # code / test
            ["#2196F3"] * 1 +        # classical
            ["#9C27B0"] * 5 +        # quantum
            ["#FF9800"] * 1 +        # QA
            ["#607D8B"] * 1          # ops
        )
        fig_pipe = go.Figure(go.Sankey(
            node=dict(label=stage_names, color=node_colors_p, pad=15, thickness=18),
            link=dict(source=src, target=tgt, value=vals,
                      color=["rgba(120,120,120,0.25)"]*(n-1)),
        ))
        fig_pipe.update_layout(height=380, margin=dict(l=5, r=5, t=30, b=5),
                               title="Quantum CI/CD Pipeline")
        st.plotly_chart(fig_pipe, use_container_width=True)

        stage_df = pd.DataFrame(PIPELINE_STAGES,
                                columns=["Stage","Tool","SLA (min)","Success Rate %","Owner"])
        st.dataframe(stage_df, use_container_width=True, hide_index=True)

        st.markdown("#### Stage Detail")
        STAGE_DETAIL = {
            "Simulation Tests": {
                "Input": "Validated QASM circuit",
                "Output": "Counts, statevector, fidelity metrics",
                "Failure Modes": "Timeout (>20 min), memory overflow for >28 qubits, unexpected NaN in statevector",
            },
            "QPU Queue": {
                "Input": "Transpiled circuit + shots",
                "Output": "Job ID, queue position, estimated wait",
                "Failure Modes": "Backend offline, insufficient credits, circuit too large for device",
            },
            "Hardware Run": {
                "Input": "Queued job ID",
                "Output": "Raw shot counts, backend metadata",
                "Failure Modes": "Hardware error, decoherence during run, unexpected gate error rate spike",
            },
        }
        sel_stage = st.selectbox("Stage details:", list(STAGE_DETAIL.keys()))
        d = STAGE_DETAIL[sel_stage]
        st.write(f"**Input:** {d['Input']}")
        st.write(f"**Output:** {d['Output']}")
        st.warning(f"**Failure Modes:** {d['Failure Modes']}")

    with tab_hist:
        import random
        random.seed(42)
        base_t = datetime(2026, 9, 20, 8, 0)
        job_rows = []
        statuses = ["success","success","success","failed","running"]
        backends = ["Qiskit Aer","Qiskit Aer","IBM Runtime","D-Wave Leap","Qiskit Aer"]
        for j in range(20):
            dur = random.randint(5, 180)
            start = base_t + timedelta(minutes=j * 40)
            end   = start + timedelta(seconds=dur)
            stage = PIPELINE_STAGES[j % len(PIPELINE_STAGES)][0]
            job_rows.append({
                "Job ID": f"JOB-{1000+j}",
                "Stage": stage,
                "Status": random.choice(statuses),
                "Duration (s)": dur,
                "Start": start,
                "End": end,
                "Circuit Depth": random.randint(10, 200),
                "Qubits": random.choice([4,6,8,10,12,16]),
                "Backend": random.choice(backends),
                "Error Rate": round(random.uniform(0.001, 0.05), 4),
            })
        jh_df = pd.DataFrame(job_rows)

        st.dataframe(jh_df.drop(columns=["Start","End"]), use_container_width=True, hide_index=True)

        st.markdown("#### Job Timeline")
        color_map = {"success":"#4CAF50","failed":"#F44336","running":"#FFC107"}
        fig_tl = px.timeline(jh_df, x_start="Start", x_end="End", y="Job ID",
                             color="Status",
                             color_discrete_map=color_map,
                             hover_data=["Stage","Circuit Depth","Qubits","Backend"])
        fig_tl.update_yaxes(autorange="reversed")
        fig_tl.update_layout(height=420, margin=dict(l=5, r=5, t=30, b=5))
        st.plotly_chart(fig_tl, use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            fig_pie = px.pie(jh_df, names="Status", title="Job Status Distribution",
                             color="Status", color_discrete_map=color_map)
            fig_pie.update_layout(height=280, margin=dict(l=5, r=5, t=40, b=5))
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_b:
            fig_hist = px.histogram(jh_df, x="Duration (s)", nbins=10,
                                    title="Duration Distribution",
                                    color_discrete_sequence=["#2196F3"])
            fig_hist.update_layout(height=280, margin=dict(l=5, r=5, t=40, b=5))
            st.plotly_chart(fig_hist, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar helper
# ─────────────────────────────────────────────────────────────────────────────

def render_sidebar_top():
    st.sidebar.markdown("## 🔬 Quantum Control Tower")
    st.sidebar.caption("Praveen Asthana · Senior Enterprise Architect → Quantum")
    st.sidebar.divider()


# ─────────────────────────────────────────────────────────────────────────────
# Section registry
# ─────────────────────────────────────────────────────────────────────────────

SECTIONS = {
    "🏗️ Architecture":    render_architecture,
    "🛠️ Tech Stack":      render_tech_stack,
    "📖 User Stories":    render_user_stories,
    "⚙️ Manual Process":  render_manual_process,
    "🔁 Pipeline Process": render_pipeline_process,
}
