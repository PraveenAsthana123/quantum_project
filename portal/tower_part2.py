"""
Quantum Architecture Control Tower — Part 2
Sections: Multi-Agent, Quantum Process, QML, Compiler, Error Correction,
          Optimization, QML Testing, QML Simulation
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# ─────────────────────────────────────────────────────────────
# SECTION 6 — Multi-Agent Process
# ─────────────────────────────────────────────────────────────

def render_multiagent_process():
    st.subheader("🤖 Multi-Agent Process")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Agents", "9")
    c2.metric("Tasks Today", "47")
    c3.metric("Avg Duration", "3.2 s")
    c4.metric("Error Rate", "2.1 %")

    t1, t2, t3 = st.tabs(["Agent Topology", "Coordination Protocol", "Execution History"])

    # ── Tab 1: Agent Topology ──
    with t1:
        agents = {
            "OrchestratorAgent": (0, 0),
            "CircuitBuilderAgent": (-2, 1.5),
            "ClassicalSolverAgent": (2, 1.5),
            "QPUDispatchAgent": (-2, -1.5),
            "QMLTrainerAgent": (2, -1.5),
            "ErrorMitigationAgent": (0, 2.5),
            "ResultValidatorAgent": (0, -2.5),
            "SecurityAgent": (-3, 0),
            "MonitoringAgent": (3, 0),
        }
        edges = [
            ("OrchestratorAgent", "CircuitBuilderAgent"),
            ("OrchestratorAgent", "ClassicalSolverAgent"),
            ("OrchestratorAgent", "QPUDispatchAgent"),
            ("OrchestratorAgent", "QMLTrainerAgent"),
            ("OrchestratorAgent", "SecurityAgent"),
            ("OrchestratorAgent", "MonitoringAgent"),
            ("CircuitBuilderAgent", "QPUDispatchAgent"),
            ("QPUDispatchAgent", "ErrorMitigationAgent"),
            ("ErrorMitigationAgent", "ResultValidatorAgent"),
            ("ClassicalSolverAgent", "ResultValidatorAgent"),
            ("QMLTrainerAgent", "ResultValidatorAgent"),
        ]
        fig = go.Figure()
        for a, b in edges:
            ax, ay = agents[a]; bx, by = agents[b]
            fig.add_trace(go.Scatter(
                x=[ax, bx, None], y=[ay, by, None],
                mode="lines", line=dict(color="#4a9eff", width=1.5),
                showlegend=False, hoverinfo="none"
            ))
        colors = ["#ff6b6b" if n == "OrchestratorAgent" else
                  "#ffd93d" if n in ("SecurityAgent", "MonitoringAgent") else "#6bcb77"
                  for n in agents]
        sizes = [28 if n == "OrchestratorAgent" else 18 for n in agents]
        fig.add_trace(go.Scatter(
            x=[v[0] for v in agents.values()],
            y=[v[1] for v in agents.values()],
            mode="markers+text",
            text=list(agents.keys()),
            textposition="top center",
            marker=dict(size=sizes, color=colors, line=dict(color="white", width=1)),
            showlegend=False,
        ))
        fig.update_layout(
            title="Agent Communication Topology",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=420, paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            font=dict(color="white"),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Agent Registry**")
        registry = pd.DataFrame({
            "Agent Name": list(agents.keys()),
            "Role": ["Orchestration","Circuit Building","Classical Solve","QPU Dispatch",
                     "QML Training","Error Mitigation","Result Validation","Security","Monitoring"],
            "Model/Tool": ["GPT-4o","Qiskit","OR-Tools","IBM Runtime","PennyLane",
                           "Mitiq","Pytest","CBOM Scanner","Prometheus"],
            "Status": ["Running","Idle","Running","Idle","Running","Idle","Idle","Running","Running"],
            "Last Active": ["0s ago","12s ago","3s ago","45s ago","8s ago","2m ago","5m ago","1s ago","0s ago"],
            "Messages": [142, 38, 51, 29, 67, 14, 22, 88, 215],
        })
        st.dataframe(registry, use_container_width=True, hide_index=True)

        st.markdown("**Live Task Flow**")
        steps = ["Received", "Agent Selected", "Assigned", "Executing", "Validating", "Done"]
        prog = st.slider("Task progress step", 0, len(steps)-1, 3)
        for i, s in enumerate(steps):
            pct = 100 if i < prog else (50 if i == prog else 0)
            st.progress(pct / 100, text=f"{'✅' if i < prog else ('🔄' if i == prog else '⏳')} {s}")

    # ── Tab 2: Coordination Protocol ──
    with t2:
        fig2 = go.Figure(go.Sankey(
            node=dict(
                label=["Task Received","Agent Selection","Task Assignment",
                       "Execution","Validation","Result Aggregation","Response"],
                color=["#4a9eff","#6bcb77","#ffd93d","#ff6b6b","#a29bfe","#fd79a8","#00cec9"],
                pad=15, thickness=20,
            ),
            link=dict(
                source=[0,1,2,3,3,4,5],
                target=[1,2,3,4,5,5,6],
                value=[100,95,90,85,85,80,78],
                color=["rgba(74,158,255,.4)"]*7,
            ),
        ))
        fig2.update_layout(title="Task Coordination State Machine", height=350,
                           paper_bgcolor="#0e1117", font=dict(color="white"))
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("**Coordination Modes**")
        coord_df = pd.DataFrame({
            "Mode": ["Sequential","Parallel","Hierarchical","Consensus"],
            "Use Case": ["Step-by-step pipeline","Independent sub-tasks","Complex delegation","Critical decisions"],
            "Example": ["circuit→transpile→run","fraud+portfolio in parallel","orchestrator→sub-agents","QPU backend selection"],
            "Overhead": ["Low","Medium","High","Very High"],
        })
        st.dataframe(coord_df, use_container_width=True, hide_index=True)

        st.markdown("**Circuit Breaker Status**")
        cb_df = pd.DataFrame({
            "Agent": list(agents.keys()),
            "Circuit State": ["Closed","Closed","Half-Open","Closed","Closed","Open","Closed","Closed","Closed"],
            "Failure Count": [0, 1, 3, 0, 0, 6, 1, 0, 0],
            "Threshold": [5]*9,
            "Recovery Time": ["—","—","30s","—","—","60s","—","—","—"],
            "Last Trip": ["—","—","2m ago","—","—","8m ago","—","—","—"],
        })
        def highlight_cb(val):
            if val == "Open": return "background-color:#c0392b;color:white"
            if val == "Half-Open": return "background-color:#e67e22;color:white"
            return ""
        st.dataframe(cb_df.style.applymap(highlight_cb, subset=["Circuit State"]),
                     use_container_width=True, hide_index=True)

    # ── Tab 3: Execution History ──
    with t3:
        rng = np.random.default_rng(0)
        task_types = ["Circuit Run","QML Train","VRP Solve","PQC Scan","Portfolio Opt"]
        hist_df = pd.DataFrame({
            "Run ID": [f"RUN-{1000+i}" for i in range(15)],
            "Task Type": rng.choice(task_types, 15),
            "Agents Involved": [rng.integers(2,6) for _ in range(15)],
            "Duration (s)": rng.uniform(0.5, 12, 15).round(2),
            "Status": rng.choice(["Success","Success","Success","Failed","Running"], 15),
            "Tokens Used": rng.integers(500, 8000, 15),
            "Cost ($)": rng.uniform(0.01, 0.5, 15).round(3),
        })
        st.dataframe(hist_df, use_container_width=True, hide_index=True)

        # Gantt
        tasks_g = ["OrchestratorAgent","CircuitBuilderAgent","QPUDispatchAgent",
                   "ErrorMitigationAgent","ResultValidatorAgent"]
        starts = [0, 0.5, 2.1, 5.3, 7.8]
        durs   = [9.0, 1.8, 3.2, 2.0, 1.0]
        fig3 = go.Figure()
        colors3 = ["#4a9eff","#6bcb77","#ffd93d","#fd79a8","#a29bfe"]
        for i, (task, st_, dur) in enumerate(zip(tasks_g, starts, durs)):
            fig3.add_trace(go.Bar(
                name=task, x=[dur], y=[task], base=[st_], orientation="h",
                marker_color=colors3[i], showlegend=True,
            ))
        fig3.update_layout(barmode="overlay", title="Parallel Agent Execution Timeline",
                           xaxis_title="Time (s)", height=300,
                           paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                           font=dict(color="white"))
        st.plotly_chart(fig3, use_container_width=True)

        err_rate = np.cumsum(rng.normal(0, 0.3, 30)).clip(0, 15)
        fig4 = px.line(x=list(range(30)), y=err_rate, labels={"x":"Run","y":"Error Rate (%)"},
                       title="Rolling Error Rate Trend", color_discrete_sequence=["#ff6b6b"])
        fig4.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117", font=dict(color="white"))
        st.plotly_chart(fig4, use_container_width=True)


# ─────────────────────────────────────────────────────────────
# SECTION 7 — Quantum Process
# ─────────────────────────────────────────────────────────────

def render_quantum_process():
    st.subheader("⚛️ Quantum Process")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Jobs", "3")
    c2.metric("Avg Circuit Depth", "24")
    c3.metric("QPU Queue", "7 jobs")
    c4.metric("Fidelity", "94.2 %")

    t1, t2, t3 = st.tabs(["Circuit Lifecycle", "Live Circuit Viewer", "QPU Job Management"])

    with t1:
        stages = ["Problem\nDefinition","QUBO\nFormulation","Gate\nDecomposition",
                  "Circuit\nConstruction","Transpilation","Noise\nModeling",
                  "Simulation","QPU\nDispatch","Measurement","Post-Processing","Result"]
        colors_s = ["#4a9eff","#4a9eff","#6bcb77","#6bcb77","#ffd93d","#ffd93d",
                    "#fd79a8","#ff6b6b","#ff6b6b","#a29bfe","#00cec9"]
        fig = go.Figure()
        for i, (s, c) in enumerate(zip(stages, colors_s)):
            fig.add_shape(type="rect", x0=i*1.1, x1=i*1.1+0.9, y0=0, y1=1,
                          fillcolor=c, opacity=0.8, line=dict(color="white", width=1))
            fig.add_annotation(x=i*1.1+0.45, y=0.5, text=s, showarrow=False,
                               font=dict(color="white", size=9), align="center")
            if i < len(stages)-1:
                fig.add_annotation(x=i*1.1+0.95, y=0.5, text="→", showarrow=False,
                                   font=dict(color="white", size=14))
        fig.update_layout(xaxis=dict(showgrid=False,showticklabels=False,range=[-0.1,12.5]),
                          yaxis=dict(showgrid=False,showticklabels=False,range=[-0.2,1.2]),
                          height=160, title="Quantum Circuit Lifecycle",
                          paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                          font=dict(color="white"), margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(fig, use_container_width=True)

        stage_df = pd.DataFrame({
            "Stage": stages,
            "Tool": ["Domain Model","Qiskit Optimization","Qiskit","Qiskit","Qiskit Transpiler",
                     "Qiskit Aer Noise","Qiskit Aer","IBM Runtime","IBM Runtime","Mitiq","Report"],
            "Output Artifact": ["Problem Spec","QUBO Matrix","Gate List","QuantumCircuit",
                                "ISA Circuit","Noisy Model","Statevector","Job ID","Bitstring Counts",
                                "Mitigated Probs","JSON/HTML"],
            "Error Check": ["Schema valid","Penalty OK","Gate valid","Width limit","Topology OK",
                            "Noise calibrated","Threshold check","Queue accept","Shot count","Fidelity OK","✓"],
        })
        st.dataframe(stage_df, use_container_width=True, hide_index=True)

        st.markdown("**Circuit Metrics (Current Job)**")
        m = pd.DataFrame({"Metric":["Qubits","Depth","Gate Count","2-qubit Gates",
                                     "T-Gates","SWAP Count","Estimated Fidelity"],
                           "Value":["16","42","187","38","12","9","93.1 %"]})
        st.dataframe(m, use_container_width=True, hide_index=True)

    with t2:
        bell_circuit = """\
        ┌───┐      ░ ┌─┐
 q_0: ─┤ H ├──■───░─┤M├───
        └───┘┌─┴─┐ ░ └─┘┌─┐
 q_1: ──────┤ X ├─░────┤M├
             └───┘ ░    └─┘
 c: 2/═══════════════╩══╩═
                         0  1"""
        st.code(bell_circuit, language=None)

        props = pd.DataFrame({"Property":["State Vector Dim","Hilbert Space Size",
                                           "Entanglement Entropy","Schmidt Rank"],
                               "Value":["4 (2²)","4","1.0 ebit","2"]})
        st.dataframe(props, use_container_width=True, hide_index=True)

        # Bloch sphere states
        states_bloch = {"|0⟩":(0,0,1), "|1⟩":(0,0,-1), "|+⟩":(1,0,0), "|−⟩":(-1,0,0)}
        fig_b = go.Figure()
        # sphere
        u, v = np.mgrid[0:2*np.pi:40j, 0:np.pi:20j]
        fig_b.add_trace(go.Surface(x=np.cos(u)*np.sin(v), y=np.sin(u)*np.sin(v), z=np.cos(v),
                                   opacity=0.1, colorscale=[[0,"#4a9eff"],[1,"#4a9eff"]],
                                   showscale=False, name="Sphere"))
        cs = ["#ff6b6b","#6bcb77","#ffd93d","#a29bfe"]
        for (lbl,(x,y,z)), col in zip(states_bloch.items(), cs):
            fig_b.add_trace(go.Scatter3d(x=[0,x], y=[0,y], z=[0,z],
                mode="lines+markers+text", text=["", lbl],
                textposition="top center",
                line=dict(color=col, width=4),
                marker=dict(size=[1,8], color=col),
                name=lbl))
        fig_b.update_layout(title="Bloch Sphere States", height=400,
                            scene=dict(bgcolor="#0e1117",
                                       xaxis=dict(showgrid=False, showticklabels=False),
                                       yaxis=dict(showgrid=False, showticklabels=False),
                                       zaxis=dict(showgrid=False, showticklabels=False)),
                            paper_bgcolor="#0e1117", font=dict(color="white"))
        st.plotly_chart(fig_b, use_container_width=True)

        gate_log = pd.DataFrame({
            "Step":[1,2,3,4],
            "Gate":["H","CNOT","Measure","Measure"],
            "Qubit(s)":["q0","q0→q1","q0","q1"],
            "Parameter":["—","—","—","—"],
            "Matrix":["[[1,1],[1,-1]]/√2","[[1,0,0,0],[0,1,0,0],[0,0,0,1],[0,0,1,0]]",
                      "Proj|0⟩,|1⟩","Proj|0⟩,|1⟩"],
        })
        st.dataframe(gate_log, use_container_width=True, hide_index=True)

    with t3:
        rng2 = np.random.default_rng(7)
        queue_df = pd.DataFrame({
            "Job ID":[f"J{2000+i}" for i in range(8)],
            "Circuit Depth": rng2.integers(10,80,8),
            "Qubits": rng2.integers(4,27,8),
            "Backend": rng2.choice(["ibm_brisbane","ibm_kyoto","AerSim","ibmq_qasm"],8),
            "Queue Pos": list(range(1,9)),
            "ETA": [f"{v}m" for v in rng2.integers(1,30,8)],
            "Priority": rng2.choice(["High","Medium","Low"],8),
        })
        st.dataframe(queue_df, use_container_width=True, hide_index=True)

        st.markdown("**Backend Comparison**")
        backends = pd.DataFrame({
            "Backend":["ibm_brisbane","ibm_kyoto","ibm_sherbrooke","AerSim (CPU)","AerSim (GPU)"],
            "Type":["Superconducting"]*3+["Simulator"]*2,
            "Qubits":[133,127,127,"unlimited","unlimited"],
            "T1 (μs)":[300,280,320,"∞","∞"],
            "T2 (μs)":[200,190,210,"∞","∞"],
            "Gate Error":[0.001,0.0015,0.0012,"0","0"],
            "Readout Error":[0.01,0.012,0.009,"0","0"],
            "Status":["✅ Online","✅ Online","⚠️ Maintenance","✅ Running","✅ Running"],
        })
        st.dataframe(backends, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────
# SECTION 8 — QML Process
# ─────────────────────────────────────────────────────────────

def render_qml_process():
    st.subheader("🧠 QML Process")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Models", "4")
    c2.metric("Best Val Acc", "87.3 %")
    c3.metric("Train Epochs", "50")
    c4.metric("Qubits Used", "8")

    t1, t2, t3 = st.tabs(["QML Pipeline", "Training Dashboard", "Model Registry"])

    with t1:
        nodes = ["Raw Data","Feature Eng.","PCA","Quantum\nFeature Map",
                 "Variational\nCircuit","Param\nOptimization","Model Eval",
                 "Classical\nIntegration","Deployment"]
        fig = go.Figure(go.Sankey(
            node=dict(label=nodes, pad=10, thickness=18,
                      color=["#4a9eff","#6bcb77","#ffd93d","#fd79a8","#a29bfe",
                             "#ff6b6b","#00cec9","#fdcb6e","#55efc4"]),
            link=dict(source=list(range(8)), target=list(range(1,9)),
                      value=[100,95,90,88,85,82,80,78],
                      color=["rgba(74,158,255,.3)"]*8),
        ))
        fig.update_layout(title="QML Training Pipeline", height=320,
                          paper_bgcolor="#0e1117", font=dict(color="white"))
        st.plotly_chart(fig, use_container_width=True)

        algo_df = pd.DataFrame({
            "Algorithm":["QSVM","VQC","QNN","QAOA","VQE","QKernel"],
            "Qubit Req.":[4,4,6,8,6,4],
            "Circuit Depth":["Shallow","Medium","Medium","Deep","Deep","Shallow"],
            "Training Complexity":["O(N log N)","O(N·iter)","O(N·layer·iter)","O(N²)","O(N²)","O(N log N)"],
            "Best Use":["Classification","Classification","Regression","Optimization","Chemistry","Classification"],
        })
        st.dataframe(algo_df, use_container_width=True, hide_index=True)

        fmap_df = pd.DataFrame({
            "Feature Map":["ZZFeatureMap","PauliFeatureMap","AngleEmbedding"],
            "Entanglement":["Full","Linear","None"],
            "Reps":[2,2,1],
            "Data Encoding":["ZZ interaction","Pauli rotations","Rotation angles"],
            "Best For":["Kernel methods","VQC input","Simple encoding"],
        })
        st.dataframe(fmap_df, use_container_width=True, hide_index=True)

    with t2:
        rng3 = np.random.default_rng(3)
        epochs = np.arange(1, 51)
        q_train = 1.2 * np.exp(-0.06*epochs) + 0.15 + rng3.normal(0, 0.02, 50)
        q_val   = 1.3 * np.exp(-0.055*epochs) + 0.18 + rng3.normal(0, 0.025, 50)
        c_train = 1.0 * np.exp(-0.08*epochs) + 0.12 + rng3.normal(0, 0.015, 50)
        c_val   = 1.1 * np.exp(-0.075*epochs) + 0.14 + rng3.normal(0, 0.02, 50)

        fig2 = go.Figure()
        for name, vals, col, dash in [
            ("Q-Train", q_train, "#4a9eff", "solid"),
            ("Q-Val",   q_val,   "#74b9ff", "dash"),
            ("C-Train", c_train, "#ff6b6b", "solid"),
            ("C-Val",   c_val,   "#fd79a8", "dash"),
        ]:
            fig2.add_trace(go.Scatter(x=epochs, y=vals.clip(0), name=name,
                           line=dict(color=col, dash=dash)))
        fig2.update_layout(title="Training vs Validation Loss (Quantum vs Classical)",
                           xaxis_title="Epoch", yaxis_title="Loss",
                           paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                           font=dict(color="white"), height=320)
        st.plotly_chart(fig2, use_container_width=True)

        metrics_df = pd.DataFrame({
            "Epoch":[1,10,20,30,40,50],
            "Q-Loss":[1.18,0.72,0.41,0.28,0.21,0.17],
            "Q-Val Loss":[1.25,0.78,0.46,0.31,0.24,0.20],
            "Q-Acc":[0.51,0.69,0.79,0.84,0.86,0.87],
            "LR":[0.01]*6,
            "Grad Norm":[1.2,0.8,0.5,0.3,0.2,0.15],
        })
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)

        hp_df = pd.DataFrame({"Hyperparameter":["n_qubits","n_layers","entanglement",
                                                  "optimizer","learning_rate","shots","backend"],
                               "Value":["8","4","full","Adam","0.01","1024","default.qubit"]})
        st.dataframe(hp_df, use_container_width=True, hide_index=True)

        # Loss landscape 3D
        g = np.linspace(-np.pi, np.pi, 30)
        b = np.linspace(-np.pi, np.pi, 30)
        G, B = np.meshgrid(g, b)
        Z = 0.5 - 0.4*np.cos(G) * np.cos(B) + 0.1*np.random.default_rng(5).normal(0,1,G.shape)
        fig3 = go.Figure(go.Surface(x=G, y=B, z=Z, colorscale="Viridis", opacity=0.85))
        fig3.update_layout(title="Loss Landscape (gamma × beta)", height=380,
                           scene=dict(xaxis_title="gamma", yaxis_title="beta", zaxis_title="Loss",
                                      bgcolor="#0e1117"),
                           paper_bgcolor="#0e1117", font=dict(color="white"))
        st.plotly_chart(fig3, use_container_width=True)

    with t3:
        models_df = pd.DataFrame({
            "Model ID":["QM-001","QM-002","QM-003","QM-004"],
            "Algorithm":["VQC","QSVM","QNN","QKernel"],
            "Qubits":[8,4,6,4],
            "Layers":[4,1,3,1],
            "Train Acc":[0.891,0.842,0.876,0.831],
            "Val Acc":[0.873,0.821,0.856,0.815],
            "Test Acc":[0.865,0.814,0.848,0.808],
            "Timestamp":["2026-09-21 10:00","2026-09-21 11:30","2026-09-21 13:15","2026-09-21 14:45"],
            "Status":["Champion","Retired","Challenger","Staging"],
        })
        st.dataframe(models_df, use_container_width=True, hide_index=True)

        rng4 = np.random.default_rng(9)
        cm = np.array([[85, 8, 4, 3], [6, 78, 9, 7], [3, 11, 80, 6], [5, 7, 4, 84]])
        fig4 = px.imshow(cm, text_auto=True, color_continuous_scale="Blues",
                         labels=dict(x="Predicted", y="Actual"),
                         title="Confusion Matrix — QM-001")
        fig4.update_layout(paper_bgcolor="#0e1117", font=dict(color="white"), height=300)
        st.plotly_chart(fig4, use_container_width=True)

        fpr = np.linspace(0, 1, 50)
        tpr_q = np.clip(fpr**0.3 + rng4.normal(0, 0.02, 50), 0, 1)
        tpr_c = np.clip(fpr**0.4 + rng4.normal(0, 0.02, 50), 0, 1)
        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(x=fpr, y=tpr_q, name="Quantum VQC (AUC=0.91)", line=dict(color="#4a9eff")))
        fig5.add_trace(go.Scatter(x=fpr, y=tpr_c, name="Classical SVM (AUC=0.88)", line=dict(color="#ff6b6b")))
        fig5.add_trace(go.Scatter(x=[0,1], y=[0,1], name="Random", line=dict(color="gray", dash="dash")))
        fig5.update_layout(title="ROC Curve", xaxis_title="FPR", yaxis_title="TPR",
                           paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                           font=dict(color="white"), height=300)
        st.plotly_chart(fig5, use_container_width=True)


# ─────────────────────────────────────────────────────────────
# SECTION 9 — QML Compiler
# ─────────────────────────────────────────────────────────────

def render_qml_compiler():
    st.subheader("🔧 QML Compiler")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Depth Reduction", "38 %")
    c2.metric("SWAP Inserted", "9")
    c3.metric("Gate Count Before", "187")
    c4.metric("Gate Count After", "124")

    t1, t2, t3 = st.tabs(["Compilation Pipeline", "Hardware Mapping", "IR / Interoperability"])

    with t1:
        passes = ["Source\nCircuit","IR\nGeneration","Gate\nCancellation",
                  "Depth\nReduction","Layout\nMapping","SWAP\nRouting",
                  "Scheduling","Native Gate\nTranslation","Final\nCircuit"]
        cols_p = ["#4a9eff","#6bcb77","#ffd93d","#ffd93d","#fd79a8","#ff6b6b",
                  "#a29bfe","#00cec9","#55efc4"]
        fig = go.Figure()
        for i, (p, c) in enumerate(zip(passes, cols_p)):
            fig.add_shape(type="rect", x0=i*1.2, x1=i*1.2+1.0, y0=0, y1=1,
                          fillcolor=c, opacity=0.8, line=dict(color="white", width=1))
            fig.add_annotation(x=i*1.2+0.5, y=0.5, text=p, showarrow=False,
                               font=dict(color="#0e1117", size=9), align="center")
            if i < len(passes)-1:
                fig.add_annotation(x=i*1.2+1.05, y=0.5, text="→",
                                   showarrow=False, font=dict(color="white", size=14))
        fig.update_layout(xaxis=dict(showgrid=False,showticklabels=False,range=[-0.1,11.0]),
                          yaxis=dict(showgrid=False,showticklabels=False,range=[-0.2,1.2]),
                          height=150, title="Compiler Pass Pipeline",
                          paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                          font=dict(color="white"), margin=dict(l=5,r=5,t=40,b=5))
        st.plotly_chart(fig, use_container_width=True)

        ba_df = pd.DataFrame({
            "Metric":["Circuit Depth","Gate Count","2-qubit Gates","SWAP Count","T-Gates"],
            "Before":[68, 187, 52, 0, 18],
            "After": [42, 124, 41, 9, 12],
        })
        ba_df["Improvement %"] = ((ba_df["Before"]-ba_df["After"])/ba_df["Before"]*100).round(1)
        st.dataframe(ba_df, use_container_width=True, hide_index=True)

        pass_df = pd.DataFrame({
            "Pass":["CommutativeCancellation","Optimize1qGates","CXCancellation",
                    "LayoutSwap","BasisTranslator"],
            "Type":["Algebraic","Algebraic","Algebraic","Routing","Translation"],
            "Gates Removed":[18, 24, 7, 0, 14],
            "Depth Saved":[8, 10, 4, -3, 7],
            "Duration (ms)":[1.2, 0.8, 0.6, 12.4, 2.1],
        })
        st.dataframe(pass_df, use_container_width=True, hide_index=True)

    with t2:
        def draw_topo(name, qubits, edges_t):
            angle = 2*np.pi*np.arange(qubits)/qubits
            xs = np.cos(angle); ys = np.sin(angle)
            fig_t = go.Figure()
            for a, b in edges_t:
                fig_t.add_trace(go.Scatter(x=[xs[a],xs[b]], y=[ys[a],ys[b]],
                    mode="lines", line=dict(color="#4a9eff",width=2), showlegend=False))
            fig_t.add_trace(go.Scatter(x=xs, y=ys, mode="markers+text",
                text=[f"Q{i}" for i in range(qubits)], textposition="top center",
                marker=dict(size=20, color="#6bcb77"), showlegend=False))
            fig_t.update_layout(title=name, height=280,
                xaxis=dict(showgrid=False,showticklabels=False,range=[-1.4,1.4]),
                yaxis=dict(showgrid=False,showticklabels=False,range=[-1.4,1.4]),
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117", font=dict(color="white"),
                margin=dict(l=5,r=5,t=35,b=5))
            return fig_t

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(draw_topo("5-Qubit Linear", 5,
                [(0,1),(1,2),(2,3),(3,4)]), use_container_width=True)
        with col2:
            st.plotly_chart(draw_topo("7-Qubit Heavy-Hex (subset)", 7,
                [(0,1),(1,2),(1,3),(3,4),(3,5),(5,6)]), use_container_width=True)

        coupling_df = pd.DataFrame({
            "Qubit Pair":["Q0-Q1","Q1-Q2","Q2-Q3","Q3-Q4","Q1-Q3"],
            "Gate Fidelity":[0.998,0.997,0.995,0.996,0.993],
            "Last Calibrated":["1h ago","1h ago","2h ago","2h ago","3h ago"],
        })
        st.dataframe(coupling_df, use_container_width=True, hide_index=True)

        routing_df = pd.DataFrame({
            "Method":["BasicSwap","Sabre","Lookahead"],
            "SWAP Count":[18, 9, 7],
            "Depth Overhead":[+22, +9, +6],
            "Runtime (ms)":[0.2, 8.1, 31.4],
            "Recommended For":["Debugging","General use","High-fidelity circuits"],
        })
        st.dataframe(routing_df, use_container_width=True, hide_index=True)

    with t3:
        ir_df = pd.DataFrame({
            "From":["Qiskit","OpenQASM 3","Qiskit","Qiskit","Cirq"],
            "To":["OpenQASM 3","QIR","Cirq","TKET","Qiskit"],
            "Tool":["qasm3.dumps","pyqir","qiskit-cirq","pytket-qiskit","cirq-aqt"],
            "Status":["✅ Stable","✅ Stable","✅ Stable","✅ Stable","⚠️ Beta"],
            "Notes":["Native Qiskit export","LLVM IR via PyQIR","cirq-google adapter",
                     "pytket-qiskit package","Limited gate set"],
        })
        st.dataframe(ir_df, use_container_width=True, hide_index=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Qiskit Python**")
            st.code("""\
from qiskit import QuantumCircuit
qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0,1],[0,1])
""", language="python")
        with col2:
            st.markdown("**OpenQASM 3**")
            st.code("""\
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
bit[2] c;
h q[0];
cx q[0], q[1];
c[0] = measure q[0];
c[1] = measure q[1];
""", language="text")
        with col3:
            st.markdown("**Cirq Python**")
            st.code("""\
import cirq
q = cirq.LineQubit.range(2)
circuit = cirq.Circuit([
  cirq.H(q[0]),
  cirq.CNOT(q[0], q[1]),
  cirq.measure(q[0], q[1]),
])
""", language="python")


# ─────────────────────────────────────────────────────────────
# SECTION 10 — Error Correction
# ─────────────────────────────────────────────────────────────

def render_error_correction():
    st.subheader("🛡️ Error Correction")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Physical Qubits", "1 331")
    c2.metric("Logical Qubits", "13")
    c3.metric("Code Distance", "9")
    c4.metric("Threshold", "1 %")

    t1, t2, t3 = st.tabs(["QEC Overview", "Syndrome Detection", "Live Error Dashboard"])

    with t1:
        err_df = pd.DataFrame({
            "Error Type":["Bit Flip (X)","Phase Flip (Z)","Bit+Phase (Y)",
                          "Decoherence","Leakage","Crosstalk"],
            "Cause":["Environmental","Environmental","Environmental",
                     "T1/T2 decay","Higher levels","Near-by gates"],
            "Rate (typical)":["0.1%","0.1%","0.01%","varies","0.01%","0.05%"],
            "Correction Method":["Repetition code","Phase-flip code","CSS code",
                                 "QEC codes","Leakage reduction","Dynamical decoupling"],
            "Detection":["Parity check","Phase parity","Both","Syndrome","Ancilla","Echo"],
        })
        st.dataframe(err_df, use_container_width=True, hide_index=True)

        code_df = pd.DataFrame({
            "QEC Code":["Surface Code","Steane [[7,1,3]]","Bacon-Shor [[9,1,3]]","Repetition (d=3)"],
            "Physical/Logical":[2*9**2 - 1, 7, 9, 3],
            "Distance":[9, 3, 3, 3],
            "Threshold Error Rate":["1 %","0.7 %","0.6 %","29 %"],
            "Best Use":["Universal FT","Small circuits","Hardware-efficient","Bit flip only"],
        })
        st.dataframe(code_df, use_container_width=True, hide_index=True)

        n_l = st.slider("Logical qubits", 1, 100, 10, key="qec_l")
        p_e = st.slider("Physical error rate (%)", 0.01, 1.0, 0.1, step=0.01, key="qec_p")
        d_vals = np.arange(3, 20, 2)
        phys = (2*d_vals**2 - 1) * n_l
        fig = px.bar(x=[f"d={d}" for d in d_vals], y=phys,
                     labels={"x":"Code Distance","y":"Physical Qubits"},
                     title=f"Physical Qubits Required ({n_l} logical, p={p_e}%)",
                     color_discrete_sequence=["#4a9eff"])
        fig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                          font=dict(color="white"), height=280)
        st.plotly_chart(fig, use_container_width=True)

    with t2:
        fig2 = go.Figure(go.Sankey(
            node=dict(
                label=["Logical State","Error Occurs","Ancilla Prep",
                       "Stabilizer Meas.","Syndrome Extraction","Decoder",
                       "Correction Applied","Corrected State"],
                color=["#4a9eff","#ff6b6b","#ffd93d","#6bcb77",
                       "#a29bfe","#fd79a8","#00cec9","#55efc4"],
                pad=10, thickness=18,
            ),
            link=dict(
                source=[0,1,2,3,4,5,6],
                target=[1,2,3,4,5,6,7],
                value=[100,95,93,91,89,87,85],
                color=["rgba(74,158,255,.3)"]*7,
            ),
        ))
        fig2.update_layout(title="Syndrome Detection Pipeline", height=300,
                           paper_bgcolor="#0e1117", font=dict(color="white"))
        st.plotly_chart(fig2, use_container_width=True)

        distances = [3,5,7,9,11]
        p_phys_vals = [0.001, 0.005, 0.01]
        fig3 = go.Figure()
        colors3 = ["#6bcb77","#ffd93d","#ff6b6b"]
        for p, col in zip(p_phys_vals, colors3):
            p_L = [(p/0.01)**(int((d+1)/2)) * 0.01 for d in distances]
            fig3.add_trace(go.Scatter(x=distances, y=p_L, name=f"p={p}",
                                      mode="lines+markers", line=dict(color=col)))
        fig3.update_layout(title="Logical Error Rate vs Code Distance",
                           xaxis_title="Code Distance", yaxis_title="Logical Error Rate",
                           yaxis_type="log", paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                           font=dict(color="white"), height=300)
        st.plotly_chart(fig3, use_container_width=True)

        decoder_df = pd.DataFrame({
            "Decoder":["MWPM","Union-Find","Neural Decoder"],
            "Accuracy":["Very High","High","Very High"],
            "Speed (μs)":["~100","~1","~50 (after training)"],
            "Online Training":["No","No","Yes"],
            "Scalability":["O(d³)","O(d·α(d))","O(1) inference"],
        })
        st.dataframe(decoder_df, use_container_width=True, hide_index=True)

    with t3:
        err_live = pd.DataFrame({
            "Error Type":["X (Bit Flip)","Z (Phase Flip)","Y (Both)","Leakage","Crosstalk"],
            "Count (100 shots)":[7,5,1,1,3],
            "Rate":[0.07,0.05,0.01,0.01,0.03],
            "Trend":["→","↓","→","↓","↑"],
            "Status":["OK","OK","OK","OK","WARNING"],
        })
        def color_status(val):
            return "background-color:#c0392b;color:white" if val=="CRITICAL" else \
                   "background-color:#e67e22;color:white" if val=="WARNING" else ""
        st.dataframe(err_live.style.applymap(color_status, subset=["Status"]),
                     use_container_width=True, hide_index=True)

        rng5 = np.random.default_rng(11)
        err_ts = np.clip(rng5.normal(0.05, 0.01, 50), 0, 0.15)
        fig4 = px.line(x=list(range(50)), y=err_ts,
                       labels={"x":"Shot Batch","y":"Error Rate"},
                       title="Rolling Error Rate (last 50 batches)",
                       color_discrete_sequence=["#ffd93d"])
        fig4.add_hline(y=0.10, line_color="#ff6b6b", line_dash="dash",
                       annotation_text="Threshold 10%")
        fig4.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                           font=dict(color="white"), height=250)
        st.plotly_chart(fig4, use_container_width=True)

        st.markdown("**QPU Circuit Breaker**")
        cb2 = pd.DataFrame({
            "Service":["IBM Quantum","Aer Simulator","D-Wave Leap","AWS Braket"],
            "State":["Closed","Closed","Open","Closed"],
            "Failures / Window":[2,0,6,1],
            "Threshold":[5,10,5,5],
            "Recovery Timeout":["—","—","120s","—"],
            "Last Trip":["—","—","4m ago","—"],
        })
        st.dataframe(cb2.style.applymap(color_status, subset=[]),
                     use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────
# SECTION 11 — Optimization
# ─────────────────────────────────────────────────────────────

def render_optimization():
    st.subheader("📈 Optimization")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Best Approx. Ratio", "0.87")
    c2.metric("QAOA Layers (p)", "3")
    c3.metric("Iterations", "150")
    c4.metric("Quantum Speedup", "1.4×")

    t1, t2, t3 = st.tabs(["Algorithm Landscape", "QAOA Dashboard", "Benchmarks"])

    with t1:
        tree_df = pd.DataFrame({
            "labels":["Optimization","Combinatorial","Continuous","ML","Hybrid",
                      "QAOA","SA","VRP/TSP","VQE","SPSA","Adam",
                      "Gradient Descent","Natural Gradient","COBYLA","L-BFGS-B"],
            "parents":["","Optimization","Optimization","Optimization","Optimization",
                       "Combinatorial","Combinatorial","Combinatorial","Continuous","Continuous","Continuous",
                       "ML","ML","Hybrid","Hybrid"],
            "values":[0,0,0,0,0,30,25,20,35,15,20,25,20,18,22],
        })
        fig = px.treemap(tree_df, names="labels", parents="parents", values="values",
                         title="Optimization Algorithm Landscape",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(paper_bgcolor="#0e1117", font=dict(color="white"), height=360)
        st.plotly_chart(fig, use_container_width=True)

        rng6 = np.random.default_rng(13)
        iters = np.arange(1, 101)
        fig2 = go.Figure()
        for name, base, decay, col in [
            ("QAOA p=1", 1.8, 0.03, "#4a9eff"),
            ("QAOA p=3", 1.5, 0.045, "#6bcb77"),
            ("Simulated Annealing", 2.0, 0.025, "#ffd93d"),
            ("Classical (Gurobi)", 1.2, 0.06, "#ff6b6b"),
        ]:
            vals = base*np.exp(-decay*iters) + 0.1 + rng6.normal(0,.03,100)
            fig2.add_trace(go.Scatter(x=iters, y=vals.clip(0.05), name=name,
                           line=dict(color=col)))
        fig2.update_layout(title="Convergence Comparison", xaxis_title="Iteration",
                           yaxis_title="Cost / Optimality Gap",
                           paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                           font=dict(color="white"), height=300)
        st.plotly_chart(fig2, use_container_width=True)

        enc_df = pd.DataFrame({
            "Problem Type":["Max-Cut","TSP","Portfolio Opt.","VRP","Job Shop"],
            "Classical Encoding":["Graph adjacency","Distance matrix","Covariance matrix","Distance+capacity","Precedence"],
            "Quantum Encoding":["Ising model","QUBO","QUBO","QUBO","QUBO"],
            "QUBO Form":["Σ w_ij z_i z_j","Σ penalty + dist","Σ risk - return","Σ penalty + route","Σ precedence"],
            "Penalty Strategy":["Soft","Hard","Soft","Hard","Hard"],
        })
        st.dataframe(enc_df, use_container_width=True, hide_index=True)

    with t2:
        g = np.linspace(0, np.pi, 40)
        b = np.linspace(0, np.pi, 40)
        G, B = np.meshgrid(g, b)
        Z_qaoa = -(0.5 + 0.3*np.cos(2*G)*np.cos(2*B) - 0.2*np.sin(G)*np.sin(B))
        fig3 = go.Figure(go.Surface(x=G, y=B, z=Z_qaoa, colorscale="RdBu_r", opacity=0.9))
        fig3.update_layout(title="QAOA Cost Landscape (gamma × beta)", height=380,
                           scene=dict(xaxis_title="gamma", yaxis_title="beta",
                                      zaxis_title="Expected Cost", bgcolor="#0e1117"),
                           paper_bgcolor="#0e1117", font=dict(color="white"))
        st.plotly_chart(fig3, use_container_width=True)

        p_layers = [1,2,3,4,5]
        approx = [0.69, 0.79, 0.87, 0.91, 0.93]
        fig4 = px.bar(x=[f"p={p}" for p in p_layers], y=approx,
                      labels={"x":"QAOA Layers","y":"Approximation Ratio"},
                      title="Approximation Ratio vs p-layers",
                      color_discrete_sequence=["#6bcb77"])
        fig4.add_hline(y=0.878, line_dash="dash", line_color="#ffd93d",
                       annotation_text="Goemans-Williamson bound (0.878)")
        fig4.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                           font=dict(color="white"), height=280)
        st.plotly_chart(fig4, use_container_width=True)

        en_hist = pd.DataFrame({
            "Iteration":[1,25,50,75,100,125,150],
            "Energy":[-12.1,-18.4,-22.7,-25.1,-26.8,-27.4,-27.9],
            "Grad Norm":[1.8,1.1,0.7,0.4,0.25,0.15,0.09],
            "Step Size":[0.1,0.08,0.06,0.04,0.03,0.02,0.01],
        })
        st.dataframe(en_hist, use_container_width=True, hide_index=True)

    with t3:
        bm_df = pd.DataFrame({
            "Problem Size":["N=10","N=20","N=50","N=100","N=200"],
            "Classical (ms)":[1,4,52,380,2900],
            "QAOA (ms)":[320,850,4200,18000,"N/A"],
            "SA (ms)":[12,38,210,820,3200],
            "Classical Quality":[1.0,1.0,0.98,0.96,0.94],
            "Quantum Quality":[0.91,0.87,0.82,0.79,"—"],
        })
        st.dataframe(bm_df, use_container_width=True, hide_index=True)

        ns = [10,20,50,100,200]
        fig5 = go.Figure()
        for name, vals, col in [
            ("Classical", [1,4,52,380,2900], "#ff6b6b"),
            ("QAOA",      [320,850,4200,18000,80000], "#4a9eff"),
            ("SA",        [12,38,210,820,3200], "#ffd93d"),
        ]:
            fig5.add_trace(go.Scatter(x=ns, y=vals, name=name,
                           mode="lines+markers", line=dict(color=col)))
        fig5.update_layout(title="Time Complexity Scaling (log-log)",
                           xaxis_title="Problem Size (N)", yaxis_title="Time (ms)",
                           xaxis_type="log", yaxis_type="log",
                           paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                           font=dict(color="white"), height=300)
        st.plotly_chart(fig5, use_container_width=True)

        res_df = pd.DataFrame({
            "Scenario":["Small (N=10)","Medium (N=20)","Large (N=50)"],
            "Qubits":[10,20,50],
            "Circuit Depth":[24,48,120],
            "Shots":[1024,2048,4096],
            "Total QPU Time (s)":[0.32,0.85,4.2],
            "Estimated Cost ($)":[0.004,0.011,0.055],
        })
        st.dataframe(res_df, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────
# SECTION 12 — QML Testing
# ─────────────────────────────────────────────────────────────

def render_qml_testing():
    st.subheader("🧪 QML Testing")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tests Total", "87")
    c2.metric("Pass Rate", "94.3 %")
    c3.metric("Coverage", "78 %")
    c4.metric("Flaky Tests", "3")

    t1, t2, t3 = st.tabs(["Test Pyramid", "Test Results", "Quantum-Specific Tests"])

    with t1:
        levels = [
            ("E2E", 3, "#ff6b6b", "Full workflow tests: end-to-end pipeline, regression"),
            ("Integration", 12, "#ffd93d", "Pipeline tests, hybrid tests, API contract tests"),
            ("Unit", 72, "#6bcb77", "Circuit tests, gate tests, encoder tests, QUBO tests"),
        ]
        fig = go.Figure()
        for i, (name, count, col, desc) in enumerate(levels):
            width = 0.3 + i*0.35
            fig.add_trace(go.Bar(
                x=[count], y=[name], orientation="h",
                marker_color=col,
                text=[f"{count} tests — {desc}"],
                textposition="inside",
                insidetextanchor="middle",
                name=name, showlegend=False,
            ))
        fig.update_layout(title="Test Pyramid", xaxis_title="Test Count",
                          paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                          font=dict(color="white"), height=250,
                          barmode="overlay")
        st.plotly_chart(fig, use_container_width=True)

        rng7 = np.random.default_rng(17)
        registry = pd.DataFrame({
            "Test ID":[f"T{100+i}" for i in range(12)],
            "Name":["test_bell_state","test_qsvm_accuracy","test_vqc_forward","test_qubo_penalty",
                    "test_transpile","test_noise_model","test_fraud_pipeline","test_portfolio_qaoa",
                    "test_pqc_keygen","test_cbom_scan","test_circuit_depth","test_shot_noise"],
            "Level":["Unit","Integration","Unit","Unit","Integration","Unit","E2E","Integration",
                     "Unit","Unit","Unit","Integration"],
            "Status":["Pass","Pass","Pass","Pass","Pass","Fail","Pass","Pass","Pass","Pass","Pass","Skip"],
            "Duration (ms)":[12,340,28,8,180,55,1240,890,15,22,6,420],
            "Last Run":["1h ago"]*12,
            "Coverage (%)":rng7.integers(70,100,12).tolist(),
        })
        st.dataframe(registry, use_container_width=True, hide_index=True)

        modules = ["core","quantum","qml","compiler","security","api"]
        test_types = ["Unit","Integration","E2E"]
        cov = np.array([[88,72,0],[90,65,50],[85,70,45],[78,60,0],[82,55,30],[91,80,60]])
        fig2 = px.imshow(cov, x=test_types, y=modules,
                         text_auto=True, color_continuous_scale="YlGn",
                         labels=dict(color="Coverage %"),
                         title="Coverage Heatmap (Module × Test Type)")
        fig2.update_layout(paper_bgcolor="#0e1117", font=dict(color="white"), height=280)
        st.plotly_chart(fig2, use_container_width=True)

    with t2:
        rng8 = np.random.default_rng(19)
        statuses = rng8.choice(["Pass","Pass","Pass","Pass","Fail","Skip"], 30)
        tests_df = pd.DataFrame({
            "Test": [f"test_{i:03d}" for i in range(30)],
            "Status": statuses,
            "Duration (ms)": rng8.integers(5, 1500, 30),
            "Error": ["—" if s=="Pass" else "AssertionError" if s=="Fail" else "Skipped"
                      for s in statuses],
            "Circuit Depth Tested": rng8.integers(2, 50, 30),
            "Backend": rng8.choice(["statevector","aer_sim","default.qubit"], 30),
        })
        st.dataframe(tests_df, use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            cnts = pd.Series(statuses).value_counts().reset_index()
            cnts.columns = ["Status","Count"]
            fig3 = px.pie(cnts, names="Status", values="Count",
                          title="Pass / Fail / Skip",
                          color_discrete_map={"Pass":"#6bcb77","Fail":"#ff6b6b","Skip":"#ffd93d"})
            fig3.update_layout(paper_bgcolor="#0e1117", font=dict(color="white"), height=280)
            st.plotly_chart(fig3, use_container_width=True)
        with col2:
            durations = tests_df["Duration (ms)"]
            fig4 = px.histogram(durations, nbins=15, title="Test Duration Distribution",
                                labels={"value":"Duration (ms)"},
                                color_discrete_sequence=["#4a9eff"])
            fig4.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                               font=dict(color="white"), height=280)
            st.plotly_chart(fig4, use_container_width=True)

        st.markdown("**Flakiness Tracker (5 runs)**")
        flaky_df = pd.DataFrame(
            np.where(np.random.default_rng(21).random((6,5)) > 0.85, "F", "P"),
            index=[f"test_{i:03d}" for i in [3,7,14,20,25,29]],
            columns=["Run 1","Run 2","Run 3","Run 4","Run 5"],
        )
        st.dataframe(flaky_df.style.applymap(
            lambda v: "background-color:#c0392b;color:white" if v=="F" else
                      "background-color:#27ae60;color:white"),
            use_container_width=True)

    with t3:
        rng9 = np.random.default_rng(23)
        layers = [1,2,3,4,5,6,7,8]
        variance = 0.5 * np.exp(-0.6*np.array(layers)) + rng9.normal(0,.005,8).clip(0)
        fig5 = px.line(x=layers, y=variance, markers=True,
                       labels={"x":"Circuit Layers","y":"Gradient Variance"},
                       title="Barren Plateau Detector — Gradient Variance vs Depth",
                       color_discrete_sequence=["#fd79a8"])
        fig5.add_hline(y=0.02, line_dash="dash", line_color="#ffd93d",
                       annotation_text="Barren plateau threshold")
        fig5.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                           font=dict(color="white"), height=260)
        st.plotly_chart(fig5, use_container_width=True)

        qubits = [2,3,4,5,6,7,8]
        expressibility = 1 - np.exp(-0.3*np.array(qubits))
        entangle_cap = 1 - 1/np.array(qubits)
        col1, col2 = st.columns(2)
        with col1:
            fig6 = px.bar(x=[f"{q}q" for q in qubits], y=expressibility,
                          labels={"x":"Qubits","y":"KL Divergence (Haar)"},
                          title="Expressibility (KL from Haar random)",
                          color_discrete_sequence=["#6bcb77"])
            fig6.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                               font=dict(color="white"), height=260)
            st.plotly_chart(fig6, use_container_width=True)
        with col2:
            fig7 = px.bar(x=[f"{q}q" for q in qubits], y=entangle_cap,
                          labels={"x":"Qubits","y":"Meyer-Wallach Measure"},
                          title="Entanglement Capability",
                          color_discrete_sequence=["#a29bfe"])
            fig7.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                               font=dict(color="white"), height=260)
            st.plotly_chart(fig7, use_container_width=True)

        shots_vals = [64,128,256,512,1024,2048,4096]
        acc = [0.62,0.71,0.78,0.83,0.87,0.89,0.91]
        fig8 = px.line(x=shots_vals, y=acc, markers=True,
                       labels={"x":"Shots","y":"Accuracy"},
                       title="Shot Noise Analysis — Accuracy vs Shots",
                       color_discrete_sequence=["#00cec9"], log_x=True)
        fig8.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                           font=dict(color="white"), height=260)
        st.plotly_chart(fig8, use_container_width=True)


# ─────────────────────────────────────────────────────────────
# SECTION 13 — QML Simulation
# ─────────────────────────────────────────────────────────────

def render_qml_simulation():
    st.subheader("🌀 QML Simulation")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Backend", "statevector")
    c2.metric("Max Qubits (CPU)", "30")
    c3.metric("Circuits/s", "1 240")
    c4.metric("GPU Acceleration", "✅ GTX 1080 Ti")

    t1, t2, t3 = st.tabs(["Backend Selection", "Simulation Run", "Resource Estimation"])

    with t1:
        be_df = pd.DataFrame({
            "Backend":["statevector","density_matrix","MPS","stabilizer","cuStateVec (GPU)"],
            "Type":["Exact","Exact+Noise","Approx","Stabilizer","GPU-Exact"],
            "Max Qubits":[30,20,50,1000,30],
            "Noise Model":["No","Yes","No","No","No"],
            "Speed (circuits/s)":[1240,280,820,5500,8400],
            "Use Case":["Small circuits","NISQ simulation","Large depth","Clifford circuits","Fast batch"],
        })
        st.dataframe(be_df, use_container_width=True, hide_index=True)

        noise_df = pd.DataFrame({
            "Error Type":["Depolarizing","Thermal Relaxation","Readout Error",
                          "Coherent Error","Two-Qubit Depolarizing"],
            "Probability":["0.1 %","T1/T2 based","1 %","0.05 %","0.5 %"],
            "Qubits Affected":["All","All","Measurement","Single-qubit gates","2-qubit gates"],
            "Mitigation Available":["ZNE, PEC","DD","Matrix inversion","Randomized compile","ZNE"],
        })
        st.dataframe(noise_df, use_container_width=True, hide_index=True)

        n_q = st.selectbox("Problem size (qubits)", [4,8,12,16,20,24,28,30], index=1,
                           key="sim_backend_sel")
        rec = "cuStateVec (GPU)" if n_q >= 20 else "statevector" if n_q <= 12 else "MPS"
        st.info(f"Recommended backend for {n_q} qubits: **{rec}**")

    with t2:
        rng10 = np.random.default_rng(27)
        states = [f"{i:04b}" for i in range(16)]
        probs = rng10.dirichlet(np.ones(16) * 0.5)
        # Simulate Bell-state-like distribution (|0000⟩ and |1111⟩ dominant)
        probs_bell = np.zeros(16); probs_bell[0]=0.48; probs_bell[15]=0.47
        probs_bell += rng10.uniform(0,0.003,16); probs_bell /= probs_bell.sum()
        fig = px.bar(x=states, y=probs_bell,
                     labels={"x":"Measurement Outcome","y":"Probability"},
                     title="Measurement Distribution (4-qubit Bell-like state)",
                     color_discrete_sequence=["#4a9eff"])
        fig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                          font=dict(color="white"), height=280)
        st.plotly_chart(fig, use_container_width=True)

        sv = pd.DataFrame({
            "State":["|0000⟩","|0001⟩","...","|1110⟩","|1111⟩"],
            "Amplitude":["0.707+0j","0.001+0j","...","0.001+0j","0.707+0j"],
            "Probability":[0.4998,0.000001,"...",0.000001,0.4998],
            "Phase (°)":[0,45,"...",135,0],
        })
        st.dataframe(sv, use_container_width=True, hide_index=True)

        depths = [2,5,10,20,30,40,50]
        fidelity_clean = [1.0]*7
        fidelity_noisy = [0.998,0.991,0.975,0.938,0.887,0.821,0.745]
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=depths, y=fidelity_clean, name="No noise",
                                  line=dict(color="#6bcb77"), mode="lines+markers"))
        fig2.add_trace(go.Scatter(x=depths, y=fidelity_noisy, name="With noise (p=0.001)",
                                  line=dict(color="#ff6b6b"), mode="lines+markers"))
        fig2.update_layout(title="Fidelity vs Circuit Depth (noise impact)",
                           xaxis_title="Circuit Depth", yaxis_title="State Fidelity",
                           paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                           font=dict(color="white"), height=270)
        st.plotly_chart(fig2, use_container_width=True)

    with t3:
        res_df = pd.DataFrame({
            "Circuit Depth":[5,10,20,30,50],
            "Qubits":[8,12,16,20,24],
            "Shots":[1024,1024,2048,2048,4096],
            "Sim Time (s)":[0.02,0.08,0.45,2.1,18.4],
            "Memory (GB)":[0.001,0.016,0.256,4.0,64.0],
            "QPU Equiv (s)":[0.5,1.2,3.8,8.2,32.1],
        })
        st.dataframe(res_df, use_container_width=True, hide_index=True)

        qb = np.arange(4, 31)
        mem_gb = 2**(qb-30) * 16  # complex128
        sim_t = (0.001 * 2**(qb/4)).clip(None, 1000)
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=qb, y=mem_gb, name="Memory (GB)",
                                  line=dict(color="#4a9eff")))
        fig3.add_trace(go.Scatter(x=qb, y=sim_t, name="Sim Time (s)",
                                  line=dict(color="#ffd93d")))
        fig3.update_layout(title="Resource Scaling vs Qubit Count (log scale)",
                           xaxis_title="Qubits", yaxis_title="Resource",
                           yaxis_type="log", paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                           font=dict(color="white"), height=280)
        st.plotly_chart(fig3, use_container_width=True)

        cost_df = pd.DataFrame({
            "Scenario":["Quick test (100 shots)","Standard (1k shots)","Production (10k shots)"],
            "Simulator Cost ($)":[0.0,0.0,0.0],
            "IBM QPU Cost ($)":[0.05,0.45,4.50],
            "AWS Braket Cost ($)":[0.075,0.75,7.50],
            "Rec. for Dev?":["Simulator","Simulator","QPU (critical only)"],
        })
        st.dataframe(cost_df, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────
SECTIONS = {
    "🤖 Multi-Agent Process":  render_multiagent_process,
    "⚛️ Quantum Process":      render_quantum_process,
    "🧠 QML Process":          render_qml_process,
    "🔧 QML Compiler":         render_qml_compiler,
    "🛡️ Error Correction":     render_error_correction,
    "📈 Optimization":         render_optimization,
    "🧪 QML Testing":          render_qml_testing,
    "🌀 QML Simulation":       render_qml_simulation,
}
