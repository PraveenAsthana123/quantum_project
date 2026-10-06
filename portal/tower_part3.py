"""
Quantum Architecture Control Tower — Part 3
Sections: XAI, Responsible AI, Accountable AI, AI Governance,
          Performance AI, SBOM/CBOM/Security, Hybrid Classical-Quantum
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

RNG = np.random.default_rng(42)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 14 — Explainable AI (XAI)
# ─────────────────────────────────────────────────────────────────────────────

def render_xai() -> None:
    st.subheader("🔍 Explainable AI (XAI)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Features Explained", "29")
    c2.metric("Top Feature", "V17")
    c3.metric("Model Fidelity", "94.2%")
    c4.metric("XAI Method", "SHAP + Circuit Grad")

    t1, t2, t3 = st.tabs(["Feature Importance", "Circuit Explainability", "Model Transparency"])

    # ── Tab 1 ─────────────────────────────────────────────────────────────────
    with t1:
        st.markdown("#### SHAP-style Feature Importance — Quantum Fraud Detection")
        features = [f"V{i}" for i in range(1, 29)] + ["Amount"]
        importance = np.abs(RNG.normal(0, 1, 29))
        importance[[16, 11, 13, 3, 6]] *= 3  # V17, V12, V14, V4, V7 most important
        importance = importance / importance.sum()
        fi_df = pd.DataFrame({"Feature": features, "Importance": importance}).sort_values(
            "Importance", ascending=True
        )
        fig = px.bar(fi_df, x="Importance", y="Feature", orientation="h",
                     color="Importance", color_continuous_scale="blues",
                     title="Feature Importance (SHAP magnitude)")
        fig.update_layout(height=600, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Feature Correlation Heatmap (Top 10 Features)")
        top10 = fi_df.nlargest(10, "Importance")["Feature"].tolist()
        corr = RNG.uniform(-1, 1, (10, 10))
        np.fill_diagonal(corr, 1.0)
        corr = (corr + corr.T) / 2
        fig2 = px.imshow(corr, x=top10, y=top10, color_continuous_scale="RdBu_r",
                         zmin=-1, zmax=1, title="Feature Correlation Matrix")
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("#### PCA Explained Variance")
        var = np.sort(RNG.uniform(0.5, 8, 28))[::-1]
        var = var / var.sum() * 100
        cumvar = np.cumsum(var)
        fig3 = go.Figure()
        fig3.add_bar(x=[f"PC{i+1}" for i in range(28)], y=var, name="Explained %", marker_color="#4C8BF5")
        fig3.add_scatter(x=[f"PC{i+1}" for i in range(28)], y=cumvar, name="Cumulative %",
                         line=dict(color="orange", width=2), yaxis="y2")
        fig3.update_layout(
            title="PCA Explained Variance",
            yaxis=dict(title="Explained Variance (%)"),
            yaxis2=dict(title="Cumulative (%)", overlaying="y", side="right"),
            legend=dict(x=0.7, y=0.3),
        )
        st.plotly_chart(fig3, use_container_width=True)

        st.markdown("#### Quantum Feature Map — ZZFeatureMap Qubit Assignment")
        qf_df = pd.DataFrame({
            "Qubit": [f"q{i}" for i in range(4)],
            "Mapped Features": ["V17, V12", "V14, V4", "V7, Amount", "V3, V10"],
            "Encoding": ["ZZFeatureMap", "ZZFeatureMap", "ZZFeatureMap", "ZZFeatureMap"],
            "Entangled With": ["q1", "q0, q2", "q3", "q2"],
            "Rationale": [
                "Highest SHAP — primary fraud signal",
                "Second tier fraud indicators",
                "Transaction amount + timing",
                "Contextual transaction features",
            ],
        })
        st.dataframe(qf_df, use_container_width=True)

    # ── Tab 2 ─────────────────────────────────────────────────────────────────
    with t2:
        st.markdown("#### Why This Circuit? — Design Decision Table")
        dec_df = pd.DataFrame({
            "Problem Type": ["Binary Classification", "Feature Encoding", "Optimization", "Kernel Estimation"],
            "Encoding Strategy": ["Amplitude Encoding", "ZZFeatureMap", "QAOA Ansatz", "Quantum Kernel"],
            "Reason": [
                "Compact representation, exponential state space",
                "Captures feature correlations via entanglement",
                "Variational landscape suited for QUBO",
                "Non-linear separation in Hilbert space",
            ],
            "Alternatives Rejected": [
                "Basis encoding (too many qubits), angle encoding (no entanglement)",
                "PauliFeatureMap (slower), custom map (no convergence)",
                "HEA (barren plateaus at depth>6), UCCSD (too deep)",
                "Classical RBF (lower accuracy), swap test (ancilla overhead)",
            ],
        })
        st.dataframe(dec_df, use_container_width=True)

        st.markdown("#### Parameter Sensitivity — Gradient Magnitude Heatmap")
        params = [f"θ_{i}" for i in range(12)]
        layers = [f"Layer {j}" for j in range(1, 5)]
        grad = np.abs(RNG.normal(0, 0.4, (4, 12)))
        grad[0, 2] = 1.2; grad[1, 5] = 0.9; grad[2, 8] = 0.7
        fig4 = px.imshow(grad, x=params, y=layers, color_continuous_scale="hot",
                         title="Gradient Magnitude per Parameter per Layer")
        st.plotly_chart(fig4, use_container_width=True)

        st.markdown("#### Entanglement Role Explanation")
        ent_df = pd.DataFrame({
            "Qubit Pair": ["q0–q1", "q1–q2", "q2–q3", "q0–q3"],
            "Entanglement Gate": ["CX (CNOT)", "CZ", "CX (CNOT)", "CZ"],
            "Role in Fraud Detection": [
                "Correlates V17 with V12 — amount-velocity pattern",
                "Links V14 and V4 — geographic + category signal",
                "Connects Amount with V3 — size-context relationship",
                "Long-range: V17 with V10 — cross-feature interaction",
            ],
            "Removed Accuracy Δ": ["-4.3%", "-2.1%", "-1.8%", "-0.9%"],
        })
        st.dataframe(ent_df, use_container_width=True)

        st.markdown("#### Prediction Explanations (Sample Cases)")
        pred_df = pd.DataFrame({
            "Sample ID": [f"TX-{1000+i}" for i in range(5)],
            "Prediction": ["Fraud", "Legitimate", "Fraud", "Legitimate", "Fraud"],
            "Confidence": ["97.3%", "89.1%", "84.7%", "92.4%", "76.5%"],
            "Top Feature": ["V17 (high)", "V17 (low)", "Amount (outlier)", "V12 (normal)", "V14 + V17"],
            "Classical Agrees": ["✅ Yes", "✅ Yes", "⚠️ No (classical: legit)", "✅ Yes", "✅ Yes"],
        })
        st.dataframe(pred_df, use_container_width=True)

    # ── Tab 3 ─────────────────────────────────────────────────────────────────
    with t3:
        st.markdown("#### Model Card")
        model_card = {
            "Model Name": "QuantumFraudDetector-VQC-v2.1",
            "Version": "2.1.0",
            "Task": "Binary classification — credit card fraud detection",
            "Dataset": "Kaggle mlg-ulb/creditcardfraud (284,807 transactions, 492 fraud)",
            "Metrics": {"Accuracy": "99.95%", "F1": "0.865", "ROC-AUC": "0.967", "Quantum AUC": "0.912"},
            "Architecture": "4-qubit VQC with ZZFeatureMap + RealAmplitudes ansatz (2 reps)",
            "Training": "Adam optimizer, 50 epochs, 1024 shots",
            "Limitations": [
                "Trained on European cardholders only",
                "Quantum advantage only apparent for >10K samples",
                "Requires PCA to 4 features — information loss",
            ],
            "Intended Use": "Demo portfolio — fraud detection in banking with quantum-classical hybrid approach",
            "Out-of-scope": "Production deployment without retraining; non-financial fraud; real-time <50ms SLA",
        }
        st.json(model_card)

        st.markdown("#### Counterfactual Explanations")
        cf_df = pd.DataFrame({
            "Sample": [f"TX-{1000+i}" for i in range(5)],
            "Original Prediction": ["Fraud"]*5,
            "Change Required": [
                "V17: 2.3 → 0.1",
                "Amount: $4,500 → $250",
                "V14: -3.1 → -0.5 AND V4: 1.8 → 0.3",
                "V17: 1.9 → 0.2 AND V12: 2.1 → 0.5",
                "Amount: $9,800 → $1,200",
            ],
            "New Prediction": ["Legitimate"]*5,
            "Confidence Change": ["97%→12%", "91%→8%", "85%→23%", "80%→15%", "77%→19%"],
        })
        st.dataframe(cf_df, use_container_width=True)

        st.markdown("#### Quantum vs Classical Accuracy by Problem Size")
        sizes = [100, 500, 1000, 5000, 10000, 50000, 100000]
        classical_acc = [0.91, 0.935, 0.947, 0.961, 0.970, 0.978, 0.982]
        quantum_acc   = [0.88, 0.905, 0.921, 0.942, 0.958, 0.969, 0.974]
        fig5 = go.Figure()
        fig5.add_scatter(x=sizes, y=classical_acc, name="Classical (XGBoost)", mode="lines+markers",
                         line=dict(color="#EF553B", width=2))
        fig5.add_scatter(x=sizes, y=quantum_acc, name="Quantum (VQC)", mode="lines+markers",
                         line=dict(color="#636EFA", width=2))
        fig5.update_layout(title="Accuracy vs Training Size", xaxis_title="Training Samples",
                           yaxis_title="Accuracy", xaxis_type="log")
        st.plotly_chart(fig5, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 15 — Responsible AI (ResAI)
# ─────────────────────────────────────────────────────────────────────────────

def render_responsible_ai() -> None:
    st.subheader("⚖️ Responsible AI (ResAI)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fairness Score", "87/100")
    c2.metric("Bias Alerts", "1")
    c3.metric("Policies Compliant", "5/6")
    c4.metric("Last Audit", "2026-09-18")

    t1, t2, t3 = st.tabs(["Fairness Metrics", "Responsible Use Policy", "Impact Assessment"])

    with t1:
        st.markdown("#### Fairness Dashboard")
        fair_df = pd.DataFrame({
            "Metric": ["Statistical Parity Difference", "Equal Opportunity Difference",
                        "Predictive Parity", "Individual Fairness", "Disparate Impact Ratio"],
            "Value": [0.03, 0.05, 0.92, 0.89, 0.96],
            "Threshold": [0.05, 0.05, 0.90, 0.85, 0.80],
            "Status": ["✅ Pass", "✅ Pass", "✅ Pass", "✅ Pass", "✅ Pass"],
            "Notes": [
                "Difference in positive prediction rates across groups",
                "TPR difference across groups",
                "PPV consistency across groups",
                "Similar individuals get similar predictions",
                "Ratio of positive rates (≥0.8 required)",
            ],
        })
        st.dataframe(fair_df, use_container_width=True)

        st.markdown("#### Group Performance Comparison")
        groups = ["Group A", "Group B", "Group C", "Group D"]
        metrics_vals = {
            "Accuracy": [0.994, 0.993, 0.995, 0.991],
            "Precision": [0.862, 0.841, 0.878, 0.855],
            "Recall": [0.801, 0.788, 0.812, 0.795],
        }
        fig = go.Figure()
        colors = ["#636EFA", "#EF553B", "#00CC96"]
        for (m, vals), col in zip(metrics_vals.items(), colors):
            fig.add_bar(name=m, x=groups, y=vals, marker_color=col)
        fig.update_layout(barmode="group", title="Performance Metrics by Group", yaxis_range=[0.75, 1.0])
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Bias Detection Timeline (across model versions)")
        versions = [f"v{i}.0" for i in range(1, 7)]
        spd = [0.08, 0.07, 0.05, 0.04, 0.03, 0.03]
        eod = [0.09, 0.08, 0.06, 0.06, 0.05, 0.05]
        fig2 = go.Figure()
        fig2.add_scatter(x=versions, y=spd, name="Statistical Parity Diff", mode="lines+markers")
        fig2.add_scatter(x=versions, y=eod, name="Equal Opportunity Diff", mode="lines+markers")
        fig2.add_hline(y=0.05, line_dash="dash", line_color="red", annotation_text="Threshold=0.05")
        fig2.update_layout(title="Bias Metrics Over Model Versions", yaxis_title="Bias Score")
        st.plotly_chart(fig2, use_container_width=True)

    with t2:
        st.markdown("#### Policy Compliance")
        pol_df = pd.DataFrame({
            "Principle": ["Transparency", "Non-discrimination", "Privacy", "Security",
                           "Human Oversight", "Environmental Impact"],
            "Description": [
                "Model decisions are explainable via SHAP and circuit gradients",
                "Fairness metrics monitored across demographic groups",
                "No PII in training data; anonymised transaction features",
                "PQC-ready cryptography; access controls enforced",
                "Human review required for predictions <80% confidence",
                "GPU/QPU energy budgets tracked; prefer simulation over QPU",
            ],
            "Status": ["✅ Compliant", "✅ Compliant", "✅ Compliant",
                        "✅ Compliant", "⚠️ Partial", "✅ Compliant"],
            "Evidence": ["XAI dashboard", "Fairness tab", "CBOM/PII scan", "CBOM tab",
                          "Override log (2 cases)", "Energy table below"],
            "Last Audited": ["2026-09-18"]*6,
        })
        st.dataframe(pol_df, use_container_width=True)

        st.markdown("#### Data Governance")
        dg_df = pd.DataFrame({
            "Data Source": ["Kaggle creditcardfraud", "NIFTY-50 Stocks", "VRPTW Benchmarks", "Demo Sensor Data"],
            "Sensitivity": ["Low (anonymised)", "Public", "Public", "Synthetic"],
            "Retention Policy": ["90 days", "365 days", "Indefinite", "30 days"],
            "Access Control": ["Read-only, local", "Read-only, local", "Read-only, local", "Internal"],
            "Consent": ["CC0 / Public Domain", "CC0", "CC BY 4.0", "Synthetic — N/A"],
        })
        st.dataframe(dg_df, use_container_width=True)

        st.markdown("#### Quantum-Specific Risks")
        qr_df = pd.DataFrame({
            "Risk": ["Quantum advantage gap", "QPU vendor lock-in", "Algorithm bias amplification",
                      "NISQ noise introducing errors", "Harvest-Now-Decrypt-Later threat"],
            "Probability": ["High", "Medium", "Low", "High", "Medium"],
            "Impact": ["Medium", "High", "High", "Medium", "Critical"],
            "Mitigation": [
                "Always maintain classical baseline; only deploy quantum if AUC gain >2%",
                "Multi-provider SDK abstraction (Qiskit+Braket+Azure); OpenQASM 3 standard",
                "Fairness audits on quantum predictions; compare with classical fairness scores",
                "Error mitigation (ZNE, PEC); always validate against noiseless simulation",
                "CBOM; begin PQC migration; inventory all RSA/EC assets",
            ],
        })
        st.dataframe(qr_df, use_container_width=True)

    with t3:
        st.markdown("#### Benefit / Risk Matrix")
        use_cases = ["Fraud Detection", "Portfolio Opt.", "Drug Discovery", "Logistics VRP",
                      "Quantum Sensing", "QKD Network", "Cryptography Audit"]
        risks = [2, 3, 4, 2, 3, 2, 1]
        benefits = [4, 3, 5, 4, 4, 5, 5]
        colors_uc = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3", "#FF6692"]
        fig3 = go.Figure()
        for uc, r, b, col in zip(use_cases, risks, benefits, colors_uc):
            fig3.add_scatter(x=[r], y=[b], mode="markers+text", name=uc,
                             marker=dict(size=22, color=col), text=[uc], textposition="top center")
        fig3.add_vline(x=2.5, line_dash="dash", line_color="gray")
        fig3.add_hline(y=3.5, line_dash="dash", line_color="gray")
        fig3.update_layout(title="Use Case Benefit vs Risk Matrix",
                           xaxis_title="Risk (1=Low, 5=Critical)", yaxis_title="Benefit (1=Low, 5=High)",
                           xaxis=dict(range=[0, 6]), yaxis=dict(range=[0, 6]), showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

        st.markdown("#### Environmental Impact Comparison")
        env_df = pd.DataFrame({
            "Compute Mode": ["Classical CPU (sklearn)", "Classical GPU (XGBoost)",
                              "Quantum Simulation (Aer)", "Real QPU (IBMQ)", "Hybrid (GPU+Sim)"],
            "Energy per Run (kWh)": [0.001, 0.008, 0.12, 0.05, 0.09],
            "CO₂ Equivalent (g)": [0.4, 3.2, 48, 20, 36],
            "Runs per Day": [500, 200, 10, 5, 50],
            "Daily CO₂ (kg)": [0.2, 0.64, 0.48, 0.10, 1.8],
        })
        st.dataframe(env_df, use_container_width=True)

        st.markdown("#### Human-in-Loop Decision Points")
        hilp = [
            ("Model deployment approval", True),
            ("High-stakes fraud override (>$10K transactions)", True),
            ("Confidence <80% prediction review", False),
            ("Fairness audit sign-off", True),
            ("Quantum circuit change review", False),
            ("PQC migration gate approval", True),
        ]
        for label, checked in hilp:
            st.checkbox(label, value=checked, key=f"hilp_{label}")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 16 — Accountable AI
# ─────────────────────────────────────────────────────────────────────────────

def render_accountable_ai() -> None:
    st.subheader("🏛️ Accountable AI")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Audit Log Entries", "1,247")
    c2.metric("Human Overrides Today", "2")
    c3.metric("Review Queue", "3")
    c4.metric("Chain Integrity", "✅ Valid")

    t1, t2, t3 = st.tabs(["Decision Audit Trail", "Human Oversight", "Accountability Matrix"])

    with t1:
        st.markdown("#### Audit Log (Last 15 Entries)")
        base = datetime(2026, 9, 21, 16, 0)
        actors = ["Model", "Agent", "Human", "Model", "Agent", "Human", "Model",
                  "Agent", "Human", "Model", "Agent", "Human", "Model", "Agent", "Human"]
        actions = ["Predict:Fraud", "Compile:Circuit", "Review:Override",
                   "Predict:Legit", "Dispatch:QPU", "Approve:Deploy",
                   "Predict:Fraud", "Mitigate:ZNE", "Override:Reject",
                   "Predict:Legit", "Compile:Circuit", "Audit:Fairness",
                   "Predict:Fraud", "Dispatch:Sim", "Review:Approve"]
        rows = []
        prev_hash = "0" * 16
        for i in range(15):
            ts = (base + timedelta(minutes=i*4)).strftime("%H:%M:%S")
            in_h = hashlib.sha256(f"input_{i}".encode()).hexdigest()[:12]
            out_h = hashlib.sha256(f"output_{i}".encode()).hexdigest()[:12]
            this_hash = hashlib.sha256(f"{prev_hash}{ts}{actors[i]}".encode()).hexdigest()[:16]
            rows.append({
                "Timestamp": ts, "Actor": actors[i], "Action": actions[i],
                "Input Hash": in_h, "Output Hash": out_h,
                "Decision": "Fraud" if "Fraud" in actions[i] else "Non-Fraud/System",
                "Signature": this_hash,
            })
            prev_hash = this_hash
        audit_df = pd.DataFrame(rows)
        st.dataframe(audit_df, use_container_width=True)

        st.markdown("#### Decision Lineage (Data → Final Decision)")
        fig = go.Figure(go.Sankey(
            node=dict(
                label=["Raw Data", "Preprocessing", "PCA (4D)", "ZZFeatureMap", "VQC Circuit",
                        "Measurement", "Prediction", "Confidence Check", "Auto-Approve", "Human Review", "Final Decision"],
                color=["#4C8BF5", "#4C8BF5", "#4C8BF5", "#AB63FA", "#AB63FA",
                        "#00CC96", "#FFA15A", "#FFA15A", "#00CC96", "#EF553B", "#636EFA"],
                pad=15, thickness=20,
            ),
            link=dict(
                source=[0, 1, 2, 3, 4, 5, 6, 7, 7, 8, 9],
                target=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10],
                value=[100, 100, 100, 100, 100, 100, 100, 80, 20, 80, 20],
                label=["284K rows", "Normalised", "4 features", "Encoded", "Run", "Sampled",
                        "0.9997 prob", "High conf", "Low conf", "Approved", "Reviewed"],
            ),
        ))
        fig.update_layout(title="Decision Lineage — Fraud Detection Pipeline", height=400)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Hash Chain Integrity")
        hc_df = audit_df[["Timestamp", "Signature"]].copy()
        hc_df["Valid"] = "✅"
        st.dataframe(hc_df, use_container_width=True)
        st.success("✅ All 15 log entries cryptographically chained — tamper detection active.")

    with t2:
        st.markdown("#### Human-in-Loop Process")
        fig2 = go.Figure(go.Sankey(
            node=dict(
                label=["Model Prediction", "Confidence Check", "High Confidence",
                        "Low Confidence", "Auto-Approve", "Review Queue", "Human Decision",
                        "Override", "Accept", "Override Log", "Final Output"],
                color=["#4C8BF5"]*4 + ["#00CC96", "#FFA15A", "#EF553B", "#EF553B", "#00CC96", "#AB63FA", "#636EFA"],
                pad=15, thickness=20,
            ),
            link=dict(
                source=[0, 1, 1, 2, 3, 5, 6, 6, 7, 8],
                target=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                value=[100, 80, 20, 80, 20, 20, 8, 12, 8, 12],
            ),
        ))
        fig2.update_layout(title="Human-in-Loop Flow", height=380)
        st.plotly_chart(fig2, use_container_width=True)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Pending Review", "3")
        col2.metric("Approved Today", "12")
        col3.metric("Overridden Today", "2")
        col4.metric("Avg Review Time", "4.2 min")

        st.markdown("#### Override Log")
        or_df = pd.DataFrame({
            "Case ID": ["TX-20481", "TX-20499"],
            "Original Prediction": ["Fraud (78%)", "Fraud (81%)"],
            "Human Override": ["Legitimate", "Legitimate"],
            "Reason": ["Known test transaction", "Customer verified — travel notification"],
            "Reviewer": ["analyst_01", "analyst_02"],
            "Timestamp": ["16:12:04", "16:34:51"],
        })
        st.dataframe(or_df, use_container_width=True)

    with t3:
        st.markdown("#### RASCI Matrix")
        activities = ["Model Training", "Model Deployment", "Fraud Decision",
                       "Fairness Audit", "PQC Migration", "Data Governance",
                       "Incident Response", "Model Retirement"]
        stakeholders = ["Quantum Eng.", "Data Sci.", "Security Arch.", "TPM", "Compliance"]
        rasci_data = [
            ["R", "A", "C", "I", "I"],
            ["C", "C", "I", "A", "R"],
            ["I", "R", "C", "I", "A"],
            ["C", "R", "C", "I", "A"],
            ["C", "I", "R", "A", "C"],
            ["I", "C", "C", "A", "R"],
            ["C", "C", "R", "A", "I"],
            ["R", "C", "I", "A", "C"],
        ]
        rasci_df = pd.DataFrame(rasci_data, index=activities, columns=stakeholders)
        st.dataframe(rasci_df, use_container_width=True)

        st.markdown("#### Compliance Registry")
        comp_df = pd.DataFrame({
            "Regulation": ["GDPR", "PIPEDA", "HIPAA (if healthcare)", "EU AI Act", "NIST AI RMF"],
            "Requirement": [
                "Right to explanation, data minimisation",
                "Consent, accountability, openness",
                "PHI protection, audit controls",
                "High-risk AI: transparency, human oversight, robustness",
                "Govern, Map, Measure, Manage",
            ],
            "Status": ["✅ Compliant", "✅ Compliant", "⚠️ N/A (no PHI)", "🔄 In Progress", "✅ Compliant"],
            "Evidence": ["XAI + audit log", "Data governance policy", "No PHI in dataset",
                          "Governance framework", "Risk register + model cards"],
            "Next Review": ["2026-12-01", "2026-12-01", "N/A", "2026-11-01", "2026-12-15"],
        })
        st.dataframe(comp_df, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 17 — AI Governance
# ─────────────────────────────────────────────────────────────────────────────

def render_ai_governance() -> None:
    st.subheader("🏛️ AI Governance")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Policies Active", "10")
    c2.metric("Open Risks", "4")
    c3.metric("Models in Prod", "3")
    c4.metric("Framework Coverage", "82%")

    t1, t2, t3 = st.tabs(["Governance Framework", "Risk Register", "Model Lifecycle"])

    with t1:
        st.markdown("#### Governance Tier Structure")
        fig = px.treemap(
            names=["Enterprise AI Governance",
                   "Board / C-Suite", "AI Ethics Committee", "Model Risk Mgmt",
                   "MLOps Team", "Dev Team",
                   "CEO/CTO", "Chief AI Officer", "Chief Risk Officer",
                   "Model Validation", "Risk Analytics",
                   "Pipeline Automation", "Monitoring", "Deployment",
                   "Quantum Engineers", "Data Scientists", "Security Architects"],
            parents=["", "Enterprise AI Governance", "Enterprise AI Governance",
                     "Enterprise AI Governance", "Enterprise AI Governance", "Enterprise AI Governance",
                     "Board / C-Suite", "Board / C-Suite", "Board / C-Suite",
                     "Model Risk Mgmt", "Model Risk Mgmt",
                     "MLOps Team", "MLOps Team", "MLOps Team",
                     "Dev Team", "Dev Team", "Dev Team"],
            title="AI Governance Hierarchy",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Policy Registry")
        pol_df = pd.DataFrame({
            "Policy ID": [f"POL-{i:03d}" for i in range(1, 11)],
            "Name": ["AI Model Risk Policy", "Data Quality Standard", "Quantum Circuit Review Policy",
                      "PQC Migration Policy", "Fairness & Bias Policy", "Model Change Management",
                      "AI Transparency Policy", "Incident Response Policy",
                      "Third-Party AI Vendor Policy", "AI Environmental Policy"],
            "Version": ["2.1", "1.3", "1.0", "1.0", "1.2", "2.0", "1.1", "3.0", "1.0", "1.0"],
            "Scope": ["All AI/ML models", "Training datasets", "Quantum circuits",
                       "Cryptographic assets", "All models", "Production models",
                       "Customer-facing AI", "All systems", "External AI APIs", "Compute resources"],
            "Status": ["Active"]*10,
            "Owner": ["Chief Risk Officer", "Data Science Lead", "Quantum Eng. Lead",
                       "Security Arch.", "AI Ethics Committee", "MLOps Lead",
                       "Chief AI Officer", "CISO", "Procurement", "Sustainability Lead"],
        })
        st.dataframe(pol_df, use_container_width=True)

        st.markdown("#### Control Framework Coverage")
        frameworks = ["NIST AI RMF", "ISO/IEC 42001", "EU AI Act", "OECD AI Principles"]
        controls = ["Govern", "Map", "Measure", "Manage", "Transparency", "Accountability",
                     "Human Oversight", "Robustness", "Fairness", "Privacy"]
        coverage = RNG.choice([0, 50, 100], (4, 10), p=[0.1, 0.3, 0.6])
        fig2 = px.imshow(coverage, x=controls, y=frameworks,
                         color_continuous_scale=["red", "yellow", "green"],
                         zmin=0, zmax=100, title="Framework Control Coverage (%)")
        st.plotly_chart(fig2, use_container_width=True)

    with t2:
        st.markdown("#### Risk Register")
        risks = [
            ("RSK-001", "Bias", "Model bias against minority groups", 3, 4, "Data Sci.", "Active"),
            ("RSK-002", "Data", "Training data quality degradation over time", 3, 3, "Data Eng.", "Active"),
            ("RSK-003", "Infra", "QPU hardware unavailability (>4hr)", 3, 3, "Quantum Eng.", "Monitored"),
            ("RSK-004", "Security", "PQC migration delay — harvest-now-decrypt-later", 2, 5, "Security Arch.", "Active"),
            ("RSK-005", "Vendor", "QPU provider API breaking changes", 3, 3, "MLOps", "Monitored"),
            ("RSK-006", "Security", "Adversarial attacks on QML model", 2, 4, "Security Arch.", "Active"),
            ("RSK-007", "Model", "Barren plateau — training stagnation", 4, 3, "Quantum Eng.", "Mitigated"),
            ("RSK-008", "Compliance", "EU AI Act high-risk classification", 2, 4, "Compliance", "Active"),
            ("RSK-009", "Ops", "Circuit transpilation failure on hardware change", 3, 3, "MLOps", "Monitored"),
            ("RSK-010", "Data", "Dataset shift — fraud pattern changes", 3, 4, "Data Sci.", "Active"),
            ("RSK-011", "Infra", "GPU memory exhaustion during simulation", 2, 3, "Infra", "Mitigated"),
            ("RSK-012", "Model", "Quantum noise exceeding error budget", 3, 4, "Quantum Eng.", "Monitored"),
            ("RSK-013", "Compliance", "GDPR breach via model inversion attack", 1, 5, "Security", "Active"),
            ("RSK-014", "Vendor", "Cloud cost overrun — QPU shots", 3, 2, "Finance", "Monitored"),
            ("RSK-015", "Model", "Concept drift in anomaly detection", 4, 3, "Data Sci.", "Active"),
        ]
        risk_df = pd.DataFrame(
            risks,
            columns=["Risk ID", "Category", "Description", "Likelihood", "Impact", "Owner", "Status"]
        )
        risk_df["Risk Score"] = risk_df["Likelihood"] * risk_df["Impact"]
        st.dataframe(risk_df[["Risk ID", "Category", "Description", "Likelihood", "Impact",
                               "Risk Score", "Owner", "Status"]], use_container_width=True)

        fig3 = px.scatter(risk_df, x="Likelihood", y="Impact", size="Risk Score",
                          color="Category", text="Risk ID",
                          title="Risk Matrix (size = Risk Score)",
                          range_x=[0.5, 5.5], range_y=[0.5, 5.5])
        fig3.add_shape(type="rect", x0=3, y0=3, x1=5.5, y1=5.5,
                        fillcolor="red", opacity=0.1, line_width=0)
        fig3.add_shape(type="rect", x0=0.5, y0=0.5, x1=3, y1=3,
                        fillcolor="green", opacity=0.1, line_width=0)
        st.plotly_chart(fig3, use_container_width=True)

        st.markdown("#### Risk Score Trend (Last 6 Months)")
        months = ["Apr", "May", "Jun", "Jul", "Aug", "Sep"]
        avg_scores = [12.4, 11.8, 10.9, 9.7, 9.2, 8.8]
        fig4 = px.line(x=months, y=avg_scores, markers=True, title="Average Risk Score Over Time",
                       labels={"x": "Month", "y": "Avg Risk Score"})
        fig4.add_hline(y=10, line_dash="dash", line_color="orange", annotation_text="Target <10")
        st.plotly_chart(fig4, use_container_width=True)

    with t3:
        st.markdown("#### Model Lifecycle Stages")
        stages = ["Research", "Development", "Validation", "Staging", "Production", "Monitoring", "Retirement"]
        stage_counts = [2, 3, 1, 1, 3, 3, 1]
        fig5 = go.Figure(go.Bar(x=stages, y=stage_counts, marker_color=[
            "#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3", "#aaa"
        ]))
        fig5.update_layout(title="Models per Lifecycle Stage", yaxis_title="# Models")
        st.plotly_chart(fig5, use_container_width=True)

        st.markdown("#### Model Registry")
        mr_df = pd.DataFrame({
            "Model ID": ["MDL-001", "MDL-002", "MDL-003", "MDL-004", "MDL-005"],
            "Name": ["QuantumFraudDetector-VQC", "PortfolioOptimizer-QAOA",
                      "VRPSolver-SA", "PQCBenchmarker", "SentinelAnomalyDetector"],
            "Version": ["2.1", "1.3", "1.0", "1.1", "0.9"],
            "Stage": ["Production", "Production", "Staging", "Production", "Development"],
            "Risk Level": ["Medium", "Medium", "Low", "Low", "High"],
            "Validation": ["✅ Passed", "✅ Passed", "🔄 In Review", "✅ Passed", "⏳ Pending"],
            "Deployed": ["2026-09-15", "2026-09-10", "—", "2026-09-12", "—"],
        })
        st.dataframe(mr_df, use_container_width=True)

        st.markdown("#### Stage Gate Criteria")
        gate_df = pd.DataFrame({
            "Transition": ["Research → Dev", "Dev → Validation", "Validation → Staging",
                            "Staging → Production", "Production → Monitoring", "Monitoring → Retirement"],
            "Required Approvals": ["Tech Lead", "Tech Lead + QA", "Risk + Compliance",
                                    "CTO + Risk", "Auto (monitoring configured)", "CTO + Business Owner"],
            "Key Criteria": [
                "Proof-of-concept accuracy >baseline; no IP conflicts",
                "Unit tests >80%; circuit fidelity >90%; no CRITICAL vulnerabilities",
                "Integration tests pass; fairness metrics within threshold; SBOM complete",
                "Load test passed; disaster recovery tested; regulatory sign-off",
                "Monitoring dashboards live; alerting configured; SLOs defined",
                "Successor model deployed; audit trail archived; decommission plan",
            ],
        })
        st.dataframe(gate_df, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 18 — Performance AI
# ─────────────────────────────────────────────────────────────────────────────

def render_performance_ai() -> None:
    st.subheader("🧫 Performance AI")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avg Latency", "245 ms")
    c2.metric("P99 Latency", "890 ms")
    c3.metric("Throughput", "42 req/s")
    c4.metric("Error Rate", "0.3%")

    t1, t2, t3 = st.tabs(["Latency & Throughput", "Quantum Performance", "Benchmarks"])

    with t1:
        st.markdown("#### Latency Distribution")
        latencies = RNG.lognormal(5.5, 0.5, 1000)
        latencies = np.clip(latencies, 50, 3000)
        fig = px.histogram(x=latencies, nbins=60, title="Request Latency Distribution (ms)",
                           labels={"x": "Latency (ms)", "y": "Count"},
                           color_discrete_sequence=["#4C8BF5"])
        fig.add_vline(x=245, line_dash="dash", annotation_text="Avg 245ms")
        fig.add_vline(x=890, line_dash="dot", line_color="red", annotation_text="P99 890ms")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Throughput — Last 24 Hours")
        hours = list(range(24))
        tput = 30 + 20 * np.sin(np.array(hours) * np.pi / 12) + RNG.normal(0, 3, 24)
        tput = np.clip(tput, 5, 70)
        fig2 = px.line(x=hours, y=tput, markers=True, title="Throughput (req/s) Last 24h",
                       labels={"x": "Hour", "y": "req/s"})
        fig2.add_hline(y=42, line_dash="dash", annotation_text="Avg 42 req/s")
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("#### API Endpoint Performance")
        ep_df = pd.DataFrame({
            "Endpoint": ["/submit-circuit", "/job-status", "/get-results",
                          "/compile-circuit", "/benchmark", "/cbom-scan"],
            "Avg (ms)": [312, 45, 892, 180, 2400, 1100],
            "P50 (ms)": [290, 42, 750, 165, 2200, 980],
            "P95 (ms)": [680, 89, 1800, 350, 5100, 2300],
            "P99 (ms)": [1200, 145, 3200, 620, 8900, 4100],
            "Error Rate": ["0.1%", "0.0%", "0.4%", "0.2%", "0.8%", "0.3%"],
            "Calls/hr": [840, 4200, 840, 320, 12, 8],
        })
        st.dataframe(ep_df, use_container_width=True)

    with t2:
        st.markdown("#### QPU Utilization by Backend")
        backends = ["ibmq_sim", "ibmq_falcon", "braket_sv1", "braket_tn1", "local_aer"]
        slots = ["00–06", "06–12", "12–18", "18–24"]
        util = RNG.integers(10, 95, (4, 5))
        fig3 = px.imshow(util, x=backends, y=slots, color_continuous_scale="Reds",
                         title="QPU Utilization % by Backend and Time Slot", text_auto=True)
        st.plotly_chart(fig3, use_container_width=True)

        st.markdown("#### Circuit Fidelity Trend (Last 14 Days)")
        days = pd.date_range("2026-09-07", periods=14)
        fidelity = 0.88 + 0.08 * RNG.random(14)
        fig4 = px.line(x=days, y=fidelity, markers=True, title="Average Circuit Fidelity per Day",
                       labels={"x": "Date", "y": "Fidelity"})
        fig4.add_hline(y=0.90, line_dash="dash", annotation_text="Target ≥0.90")
        st.plotly_chart(fig4, use_container_width=True)

        st.markdown("#### Quantum vs Classical Performance")
        qa_df = pd.DataFrame({
            "Task": ["Fraud (4 features)", "Portfolio (5 assets)", "VRP (4 cities)", "Clustering (8D)"],
            "Classical (ms)": [12, 45, 8, 22],
            "QPU Queue+Run (ms)": [15000, 12000, 125000, 9000],
            "Simulation (ms)": [180, 320, 124800, 520],
            "Quantum Advantage": ["❌ No (sim only)", "❌ No (sim only)", "❌ No (NISQ era)", "❌ No (sim only)"],
            "Notes": ["Sim overhead dominates", "QAOA not yet competitive", "QUBO proof-of-concept", "QKernel research"],
        })
        st.dataframe(qa_df, use_container_width=True)

        st.markdown("#### Shot Efficiency — Accuracy vs Shots")
        shots_list = [32, 64, 128, 256, 512, 1024, 2048, 4096]
        acc_qaoa = [0.71, 0.76, 0.82, 0.87, 0.90, 0.93, 0.95, 0.96]
        acc_vqc  = [0.68, 0.74, 0.81, 0.86, 0.89, 0.91, 0.93, 0.94]
        fig5 = go.Figure()
        fig5.add_scatter(x=shots_list, y=acc_qaoa, name="QAOA", mode="lines+markers")
        fig5.add_scatter(x=shots_list, y=acc_vqc, name="VQC", mode="lines+markers")
        fig5.update_layout(title="Accuracy vs Number of Shots", xaxis_type="log",
                           xaxis_title="Shots", yaxis_title="Accuracy")
        st.plotly_chart(fig5, use_container_width=True)

    with t3:
        st.markdown("#### MLPerf-style Benchmark")
        bench_df = pd.DataFrame({
            "Model/Task": ["Fraud Detection (binary)", "Portfolio Opt.", "VRP (4 cities)",
                            "Quantum Chemistry (H₂)", "Quantum Sensing"],
            "Dataset": ["creditcardfraud", "NIFTY-50", "VRPTW", "H₂ molecule", "Synthetic"],
            "Metric": ["ROC-AUC", "Sharpe Ratio", "Tour Length", "Ground Energy Error", "SNR (dB)"],
            "Classical": [0.967, 1.82, 438, 0.012, 28.4],
            "Quantum (Sim)": [0.912, 1.74, 461, 0.008, 31.2],
            "Hybrid": [0.971, 1.89, 440, 0.006, 32.1],
            "Hardware": ["CPU+Sim", "CPU+Sim", "CPU+Sim", "CPU+Sim", "CPU+Sim"],
        })
        st.dataframe(bench_df, use_container_width=True)

        st.markdown("#### Resource Utilization by Workload")
        workloads = ["Training (VQC)", "QAOA Run", "Simulation", "PQC Benchmark", "API Serving"]
        cpu_util = [45, 30, 92, 65, 20]
        gpu_util = [78, 15, 88, 10, 5]
        mem_util = [60, 45, 95, 40, 25]
        qpu_time = [0, 85, 0, 0, 0]
        fig6 = go.Figure()
        for name, vals, col in zip(
            ["CPU%", "GPU%", "Memory%", "QPU Queue%"],
            [cpu_util, gpu_util, mem_util, qpu_time],
            ["#636EFA", "#EF553B", "#00CC96", "#AB63FA"]
        ):
            fig6.add_bar(name=name, x=workloads, y=vals, marker_color=col)
        fig6.update_layout(barmode="group", title="Resource Utilization per Workload Type")
        st.plotly_chart(fig6, use_container_width=True)

        st.markdown("#### Cost Analysis")
        cost_df = pd.DataFrame({
            "Provider": ["Local (GPU)", "AWS Braket SV1", "IBM Quantum (free tier)",
                          "AWS Braket IonQ", "Azure Quantum IonQ"],
            "Compute Type": ["GPU Simulation", "Managed Simulator", "QPU (5 qubits free)",
                              "Trapped-Ion QPU", "Trapped-Ion QPU"],
            "Rate": ["~$0.002/hr electricity", "$0.00035/task + $0.00145/shot",
                      "Free (10 min/month)", "$0.01/shot", "$0.0097/shot"],
            "Monthly Estimate (1K jobs)": ["$2", "$180", "$0", "$10,000", "$9,700"],
        })
        st.dataframe(cost_df, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 19 — SBOM / CBOM / Security Layers
# ─────────────────────────────────────────────────────────────────────────────

def render_security_layers() -> None:
    st.subheader("🔐 SBOM / CBOM / Security Layers")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("SBOM Components", "27")
    c2.metric("CBOM Assets", "14")
    c3.metric("Active SIEM Alerts", "3")
    c4.metric("Threat Score", "28/100")

    t1, t2, t3, t4 = st.tabs(["SBOM", "CBOM", "SIEM / EDR / XDR", "SOAR / IR"])

    # ── SBOM ─────────────────────────────────────────────────────────────────
    with t1:
        sbom_rows = [
            ("qiskit", "2.3.0", "Apache-2.0", "IBM", "a1b2c3d4e5f6", 0, "pkg:pypi/qiskit@2.3.0"),
            ("qiskit-aer", "0.17.2", "Apache-2.0", "IBM", "b2c3d4e5f6a1", 0, "pkg:pypi/qiskit-aer@0.17.2"),
            ("qiskit-algorithms", "0.4.0", "Apache-2.0", "IBM", "c3d4e5f6a1b2", 0, "pkg:pypi/qiskit-algorithms@0.4.0"),
            ("qiskit-finance", "0.4.1", "Apache-2.0", "IBM", "d4e5f6a1b2c3", 0, "pkg:pypi/qiskit-finance@0.4.1"),
            ("qiskit-nature", "0.8.0", "Apache-2.0", "IBM", "e5f6a1b2c3d4", 0, "pkg:pypi/qiskit-nature@0.8.0"),
            ("qiskit-optimization", "0.7.0", "Apache-2.0", "IBM", "f6a1b2c3d4e5", 0, "pkg:pypi/qiskit-optimization@0.7.0"),
            ("pennylane", "0.45.1", "Apache-2.0", "Xanadu", "1a2b3c4d5e6f", 0, "pkg:pypi/pennylane@0.45.1"),
            ("mitiq", "0.0.0-dev", "GPL-3.0", "Unitary Fund", "2b3c4d5e6f1a", 1, "pkg:pypi/mitiq@0.0.0"),
            ("stim", "1.16.0", "Apache-2.0", "Google", "3c4d5e6f1a2b", 0, "pkg:pypi/stim@1.16.0"),
            ("openfermion", "1.8.1", "Apache-2.0", "Google", "4d5e6f1a2b3c", 0, "pkg:pypi/openfermion@1.8.1"),
            ("qutip", "5.3.1", "BSD-3-Clause", "Community", "5e6f1a2b3c4d", 0, "pkg:pypi/qutip@5.3.1"),
            ("scqubits", "4.3.1", "BSD-3-Clause", "Community", "6f1a2b3c4d5e", 0, "pkg:pypi/scqubits@4.3.1"),
            ("cirq", "1.7.0", "Apache-2.0", "Google", "a1b2c3d4e5f7", 0, "pkg:pypi/cirq@1.7.0"),
            ("dwave-ocean-sdk", "9.5.0", "Apache-2.0", "D-Wave", "b2c3d4e5f6a2", 0, "pkg:pypi/dwave-ocean-sdk@9.5.0"),
            ("perceval-quandela", "1.3.0", "MIT", "Quandela", "c3d4e5f6a1b3", 0, "pkg:pypi/perceval-quandela@1.3.0"),
            ("netket", "3.22.4", "Apache-2.0", "EPFL", "d4e5f6a1b2c4", 0, "pkg:pypi/netket@3.22.4"),
            ("streamlit", "1.48.0", "Apache-2.0", "Snowflake", "e5f6a1b2c3d5", 0, "pkg:pypi/streamlit@1.48.0"),
            ("plotly", "5.x", "MIT", "Plotly", "f6a1b2c3d4e6", 0, "pkg:pypi/plotly@5"),
            ("numpy", "2.4.6", "BSD-3-Clause", "NumPy Project", "a1b2c3d4e5f8", 0, "pkg:pypi/numpy@2.4.6"),
            ("scipy", "1.16.2", "BSD-3-Clause", "SciPy Project", "b2c3d4e5f6a3", 0, "pkg:pypi/scipy@1.16.2"),
            ("pandas", "2.3.1", "BSD-3-Clause", "Pandas Project", "c3d4e5f6a1b4", 0, "pkg:pypi/pandas@2.3.1"),
            ("scikit-learn", "1.x", "BSD-3-Clause", "scikit-learn", "d4e5f6a1b2c5", 1, "pkg:pypi/scikit-learn@1"),
            ("fastapi", "0.136.3", "MIT", "Tiangolo", "e5f6a1b2c3d6", 0, "pkg:pypi/fastapi@0.136.3"),
            ("ortools", "9.15.6755", "Apache-2.0", "Google", "f6a1b2c3d4e7", 0, "pkg:pypi/ortools@9.15.6755"),
            ("cryptography", "latest", "Apache-2.0/BSD", "PyCA", "a1b2c3d4e5f9", 0, "pkg:pypi/cryptography"),
            ("jupyter", "1.1.1", "BSD-3-Clause", "Jupyter", "b2c3d4e5f6a4", 0, "pkg:pypi/jupyter@1.1.1"),
            ("kaggle", "1.7.4.5", "Apache-2.0", "Kaggle/Google", "c3d4e5f6a1b5", 0, "pkg:pypi/kaggle@1.7.4.5"),
        ]
        sbom_df = pd.DataFrame(sbom_rows, columns=[
            "Component", "Version", "License", "Supplier", "Hash (SHA256 prefix)", "Vuln Count", "PURL"
        ])
        st.markdown("#### Software Bill of Materials (SBOM)")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Critical CVEs", "0", delta="0 new")
        col2.metric("High CVEs", "2", delta="+1", delta_color="inverse")
        col3.metric("Medium CVEs", "5")
        col4.metric("Low CVEs", "12")
        st.dataframe(sbom_df, use_container_width=True)

        lic_counts = sbom_df["License"].value_counts()
        fig = px.bar(x=lic_counts.index, y=lic_counts.values, title="License Distribution",
                     labels={"x": "License", "y": "Count"}, color=lic_counts.index)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Qiskit Dependency Network (simplified)")
        nodes = ["qiskit", "qiskit-aer", "qiskit-algorithms", "qiskit-finance",
                 "rustworkx", "numpy", "scipy", "sympy", "stevedore"]
        node_x = [0.5, 0.2, 0.8, 0.5, 0.1, 0.3, 0.7, 0.9, 0.0]
        node_y = [0.9, 0.6, 0.6, 0.4, 0.3, 0.1, 0.1, 0.3, 0.6]
        edges = [(0,1),(0,2),(0,3),(0,4),(1,5),(2,5),(2,6),(3,6),(0,7),(4,8)]
        fig2 = go.Figure()
        for s, t in edges:
            fig2.add_scatter(x=[node_x[s], node_x[t]], y=[node_y[s], node_y[t]],
                             mode="lines", line=dict(color="#aaa", width=1), showlegend=False)
        fig2.add_scatter(x=node_x, y=node_y, mode="markers+text", text=nodes,
                         textposition="top center",
                         marker=dict(size=18, color=["#636EFA"]*4 + ["#EF553B"]*5))
        fig2.update_layout(title="Qiskit Dependency Graph", xaxis=dict(visible=False), yaxis=dict(visible=False))
        st.plotly_chart(fig2, use_container_width=True)

        cyclonedx_json = json.dumps({
            "bomFormat": "CycloneDX", "specVersion": "1.5",
            "version": 1, "serialNumber": "urn:uuid:quantum-lab-sbom-001",
            "components": [{"type": "library", "name": r[0], "version": r[1],
                             "licenses": [{"license": {"id": r[2]}}], "supplier": {"name": r[3]},
                             "purl": r[6]} for r in sbom_rows[:5]]
        }, indent=2)
        st.download_button("⬇ Download SBOM (CycloneDX JSON)", cyclonedx_json,
                           file_name="sbom_quantum_lab.cdx.json", mime="application/json")

    # ── CBOM ─────────────────────────────────────────────────────────────────
    with t2:
        cbom_rows = [
            ("TLS Cert (portal)", "RSA-2048", "2048-bit", "X.509 / TLS 1.3", "⚠️ Vulnerable", "High", "P1"),
            ("TLS Cert (API GW)", "ECDSA-P256", "256-bit", "X.509 / TLS 1.3", "⚠️ Vulnerable", "High", "P1"),
            ("SSH Host Key", "RSA-4096", "4096-bit", "RFC4253", "⚠️ Vulnerable", "High", "P1"),
            ("JWT Signing", "HMAC-SHA256", "256-bit", "RFC7519", "✅ Safe", "None", "P3"),
            ("DB Encryption", "AES-256-GCM", "256-bit", "FIPS 197", "✅ Safe", "None", "P3"),
            ("API Auth Token", "HMAC-SHA256", "256-bit", "Internal", "✅ Safe", "None", "P3"),
            ("Config Signing", "ECDSA-P384", "384-bit", "NIST", "⚠️ Vulnerable", "Medium", "P2"),
            ("File Integrity", "SHA-256", "256-bit", "FIPS 180", "✅ Safe", "None", "P3"),
            ("PQC Demo: KEM", "ML-KEM-768", "1184-bit pk", "NIST FIPS 203", "✅ PQC Safe", "None", "—"),
            ("PQC Demo: Sig", "ML-DSA-65", "1952-bit pk", "NIST FIPS 204", "✅ PQC Safe", "None", "—"),
            ("PQC Demo: Hash-Sig","SLH-DSA-128s","32-bit pk",  "NIST FIPS 205", "✅ PQC Safe", "None", "—"),
            ("Code Signing", "RSA-4096", "4096-bit", "X.509", "⚠️ Vulnerable", "Medium", "P2"),
            ("Backup Encryption","AES-256-CBC","256-bit", "FIPS 197", "✅ Safe", "None", "P3"),
            ("QPU Auth", "ECDSA-P256", "256-bit", "IBM/AWS API", "⚠️ Vulnerable", "Medium", "P2"),
        ]
        cbom_df = pd.DataFrame(cbom_rows, columns=[
            "Asset", "Algorithm", "Key Size", "Standard", "Quantum-Safe", "Harvest Risk", "Migration Priority"
        ])
        st.markdown("#### Cryptographic Bill of Materials (CBOM)")
        st.dataframe(cbom_df, use_container_width=True)

        vuln_counts = cbom_df["Harvest Risk"].value_counts()
        fig3 = px.pie(values=vuln_counts.values, names=vuln_counts.index,
                      title="Harvest-Now-Decrypt-Later Risk by Asset",
                      color_discrete_map={"High": "#EF553B", "Medium": "#FFA15A", "None": "#00CC96"})
        st.plotly_chart(fig3, use_container_width=True)

        st.markdown("#### PQC Migration Roadmap (Gantt)")
        now = datetime(2026, 9, 21)
        gantt_data = pd.DataFrame([
            dict(Task="Phase 1: Discovery & CBOM", Start=now, Finish=now+timedelta(days=30), Phase="Discovery"),
            dict(Task="Phase 2: Pilot Hybrid TLS", Start=now+timedelta(days=25), Finish=now+timedelta(days=90), Phase="Hybrid"),
            dict(Task="Phase 2: Hybrid JWT/Signing", Start=now+timedelta(days=30), Finish=now+timedelta(days=100), Phase="Hybrid"),
            dict(Task="Phase 3: Full ML-KEM Migration", Start=now+timedelta(days=85), Finish=now+timedelta(days=180), Phase="PQC"),
            dict(Task="Phase 3: Full ML-DSA Signing", Start=now+timedelta(days=90), Finish=now+timedelta(days=190), Phase="PQC"),
            dict(Task="Phase 3: Retire RSA/ECDSA", Start=now+timedelta(days=180), Finish=now+timedelta(days=210), Phase="PQC"),
        ])
        fig4 = px.timeline(gantt_data, x_start="Start", x_end="Finish", y="Task", color="Phase",
                           title="PQC Migration Timeline",
                           color_discrete_map={"Discovery": "#636EFA", "Hybrid": "#FFA15A", "PQC": "#00CC96"})
        fig4.update_yaxes(autorange="reversed")
        st.plotly_chart(fig4, use_container_width=True)

        st.markdown("#### Algorithm Size Comparison (Classical vs PQC)")
        algos = ["RSA-2048", "RSA-4096", "ECDSA-P256", "ML-KEM-768", "ML-DSA-65", "SLH-DSA-128s"]
        pk_sizes = [294, 550, 91, 1184, 1952, 32]
        sig_sizes = [256, 512, 71, 1088, 3293, 7856]
        fig5 = go.Figure()
        fig5.add_bar(name="Public Key (bytes)", x=algos, y=pk_sizes, marker_color="#636EFA")
        fig5.add_bar(name="Sig/Ciphertext (bytes)", x=algos, y=sig_sizes, marker_color="#EF553B")
        fig5.update_layout(barmode="group", title="Key/Ciphertext Size: Classical vs PQC")
        st.plotly_chart(fig5, use_container_width=True)

    # ── SIEM / EDR / XDR ─────────────────────────────────────────────────────
    with t3:
        st.markdown("#### Security Event Dashboard")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Active SIEM Alerts", "3")
        col2.metric("Critical Events (24h)", "0")
        col3.metric("Threat Score", "28/100")
        col4.metric("Uptime", "99.7%")

        base = datetime(2026, 9, 21, 10, 0)
        siem_rows = []
        for i in range(15):
            ts = (base + timedelta(minutes=i*25)).strftime("%H:%M")
            sev = RNG.choice(["INFO", "LOW", "MEDIUM", "HIGH"], p=[0.5, 0.3, 0.15, 0.05])
            siem_rows.append({
                "Timestamp": ts,
                "Source": RNG.choice(["portal-host", "api-gateway", "qpu-worker", "data-pipeline", "auth-service"]),
                "Event Type": RNG.choice(["Login Success", "API Rate Limit", "Anomalous Request", "Port Scan", "Config Change", "Job Submitted", "Error Spike"]),
                "Severity": sev,
                "Description": f"Event #{i+1} — automated SIEM detection",
                "Status": RNG.choice(["Closed", "Open", "Closed", "Closed"]),
            })
        siem_df = pd.DataFrame(siem_rows)
        st.markdown("#### SIEM Event Log")
        st.dataframe(siem_df, use_container_width=True)

        st.markdown("#### EDR Host Status")
        edr_df = pd.DataFrame({
            "Host": ["quantum-workstation", "portal-server", "api-gateway", "qpu-worker-01", "data-pipeline"],
            "OS": ["Ubuntu 22.04", "Ubuntu 22.04", "Debian 12", "Ubuntu 22.04", "Ubuntu 20.04"],
            "Agent Version": ["3.12.1", "3.12.1", "3.11.8", "3.12.1", "3.10.5"],
            "Last Seen": ["Now", "Now", "Now", "2 min ago", "5 min ago"],
            "Threat Level": ["🟢 Clean", "🟢 Clean", "🟡 Low", "🟢 Clean", "🟢 Clean"],
            "Quarantined Files": [0, 0, 1, 0, 0],
            "Status": ["Active"]*5,
        })
        st.dataframe(edr_df, use_container_width=True)

        st.markdown("#### XDR Correlated Incidents")
        xdr_df = pd.DataFrame({
            "Incident ID": ["XDR-2026-0014", "XDR-2026-0013", "XDR-2026-0012"],
            "Sources Correlated": ["SIEM + EDR", "SIEM + Network", "EDR + Firewall"],
            "MITRE ATT&CK Tactic": ["Initial Access", "Discovery", "Defense Evasion"],
            "MITRE Technique": ["T1190 (Exploit Public App)", "T1046 (Network Scan)", "T1562 (Impair Defenses)"],
            "Confidence": ["72%", "85%", "61%"],
            "Status": ["Open", "Closed", "Investigating"],
        })
        st.dataframe(xdr_df, use_container_width=True)

        st.markdown("#### Threat Event Timeline (Last 24h)")
        hours24 = list(range(24))
        events = RNG.poisson(2, 24)
        events[14] = 8; events[15] = 12; events[16] = 6  # spike
        fig6 = px.line(x=hours24, y=events, markers=True, title="Security Events per Hour",
                       labels={"x": "Hour (UTC)", "y": "Event Count"})
        fig6.add_hline(y=5, line_dash="dash", line_color="orange", annotation_text="Alert Threshold=5")
        st.plotly_chart(fig6, use_container_width=True)

    # ── SOAR ──────────────────────────────────────────────────────────────────
    with t4:
        st.markdown("#### SOAR Playbook Registry")
        soar_df = pd.DataFrame({
            "Playbook": ["Brute Force Response", "Malware Containment", "Anomalous API Traffic",
                          "QPU Job Anomaly", "PQC Alert — Expired Cert", "Insider Threat"],
            "Trigger": ["5+ failed logins/5min", "EDR malware detection",
                         "API rate >3× baseline", "Circuit error rate >20%",
                         "RSA cert expiry <30 days", "Unusual data access pattern"],
            "Actions": ["Block IP, notify SOC", "Isolate host, snapshot, notify",
                         "Rate-limit, alert, review", "Pause QPU job, notify eng",
                         "Auto-generate CSR, notify sec arch", "Alert, freeze account, review"],
            "Avg Runtime (s)": [12, 45, 8, 6, 30, 120],
            "Success Rate": ["99%", "94%", "97%", "100%", "92%", "88%"],
            "Last Run": ["1h ago", "3d ago", "2h ago", "4h ago", "2d ago", "5d ago"],
        })
        st.dataframe(soar_df, use_container_width=True)

        st.markdown("#### Active Incidents")
        inc_df = pd.DataFrame({
            "Incident ID": ["INC-2026-0041", "INC-2026-0038", "INC-2026-0035"],
            "Severity": ["🟡 Medium", "🟡 Medium", "🔴 High"],
            "Title": ["Anomalous API traffic (rate 4×)", "EDR quarantine — api-gateway",
                       "XDR: Correlated network scan detected"],
            "Assigned To": ["analyst_01", "analyst_02", "sec_lead"],
            "Status": ["In Progress", "Investigating", "Escalated"],
            "SLA Remaining (min)": [45, 80, 12],
        })
        st.dataframe(inc_df, use_container_width=True)

        st.markdown("#### Incident Response Flow")
        fig7 = go.Figure(go.Sankey(
            node=dict(
                label=["Alert Triggered", "SOAR Playbook", "Auto-Remediate",
                        "Escalate to Human", "Human Action", "Resolution", "Post-Mortem"],
                color=["#EF553B", "#AB63FA", "#00CC96", "#FFA15A", "#636EFA", "#00CC96", "#19D3F3"],
                pad=15, thickness=20,
            ),
            link=dict(
                source=[0, 1, 2, 3, 4, 4, 5, 6],
                target=[1, 2, 5, 4, 5, 6, 6, 6],
                value=[100, 100, 70, 30, 30, 30, 70, 30],
                label=["100 alerts", "playbook run", "auto-closed", "escalated",
                        "resolved", "post-mortem", "closed", "documented"],
            ),
        ))
        fig7.update_layout(title="SOAR Incident Response Flow", height=380)
        st.plotly_chart(fig7, use_container_width=True)

        st.markdown("#### MITRE ATT&CK Coverage")
        tactics = ["Initial Access", "Execution", "Persistence", "Privilege Esc.",
                    "Defense Evasion", "Credential Access", "Discovery", "Lateral Movement",
                    "Collection", "Exfiltration", "Impact"]
        techniques = ["T1190", "T1059", "T1098", "T1068", "T1562", "T1110", "T1046",
                       "T1021", "T1005", "T1041", "T1499"]
        coverage = RNG.choice([0, 1, 2], (len(tactics), len(techniques)),
                               p=[0.3, 0.4, 0.3])
        fig8 = px.imshow(coverage, x=techniques, y=tactics,
                         color_continuous_scale=["#eee", "#FFA15A", "#00CC96"],
                         zmin=0, zmax=2,
                         title="MITRE ATT&CK Coverage (0=Not Covered, 1=Partial, 2=Full)")
        fig8.update_layout(height=500)
        st.plotly_chart(fig8, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 20 — Hybrid Classical-Quantum
# ─────────────────────────────────────────────────────────────────────────────

def render_hybrid_classical_quantum() -> None:
    st.subheader("⚡ Hybrid Classical-Quantum Architecture")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Classical Jobs (24h)", "847")
    c2.metric("Simulator Jobs (24h)", "123")
    c3.metric("QPU Jobs (24h)", "12")
    c4.metric("Hybrid Jobs (24h)", "45")

    t1, t2, t3, t4 = st.tabs(["Architecture Layers", "Workload Router", "API & Database", "Observability"])

    # ── Tab 1 ─────────────────────────────────────────────────────────────────
    with t1:
        st.markdown("#### Full Hybrid Stack — 7 Layers")
        layers = [
            (7, "Application / Business Logic",
             "React/Streamlit UI, REST API, business workflows, job orchestration",
             "Streamlit, FastAPI, React", "N/A", "HTTP/JSON"),
            (6, "AI/ML Orchestration",
             "Classical ML + QML training, inference, model registry, A/B testing",
             "scikit-learn, PennyLane, Qiskit", "~50ms", "gRPC/REST"),
            (5, "Quantum Middleware",
             "QPU abstraction, circuit compilation, transpilation, backend routing",
             "Qiskit, Cirq, TKET, OpenQASM3", "~200ms", "Vendor SDK"),
            (4, "Classical HPC",
             "CPU/GPU acceleration, data preprocessing, classical solvers, simulation",
             "NumPy, OR-Tools, Qiskit Aer GPU", "~10ms", "CUDA/MPI"),
            (3, "Quantum Processing",
             "Gate-model QPU, quantum annealing, photonic QC, hybrid VQE/QAOA",
             "IBM QPU, D-Wave, Perceval, PennyLane", "100μs–1ms gate", "Vendor API"),
            (2, "Control Electronics",
             "Microwave pulses, RF control, AWG/RFSoC, timing, feedback",
             "QICK, Qibolab, Zurich Instruments", "~100ns", "FPGA/RF"),
            (1, "Physical Qubit Layer",
             "Superconducting transmons, spin qubits, trapped-ion, neutral atom",
             "Dilution fridge, laser, RF cavity", "~50μs T1", "Physical"),
        ]
        for layer_num, name, description, tools, latency, protocol in layers:
            colors = {7: "#4C8BF5", 6: "#AB63FA", 5: "#00CC96", 4: "#FFA15A",
                      3: "#EF553B", 2: "#FF6692", 1: "#B6E880"}
            with st.expander(f"**Layer {layer_num}: {name}**", expanded=(layer_num >= 5)):
                col1, col2, col3, col4 = st.columns([3, 3, 1, 1])
                col1.markdown(f"**Description:** {description}")
                col2.markdown(f"**Tools:** {tools}")
                col3.metric("Latency", latency)
                col4.metric("Protocol", protocol)

        st.markdown("#### Layer Stack Visualization")
        layer_names = [f"L{l[0]}: {l[1]}" for l in reversed(layers)]
        layer_colors = ["#B6E880", "#FF6692", "#EF553B", "#FFA15A", "#00CC96", "#AB63FA", "#4C8BF5"]
        fig = go.Figure()
        for i, (name, color) in enumerate(zip(layer_names, layer_colors)):
            fig.add_bar(y=[name], x=[100], orientation="h", marker_color=color,
                        name=name, showlegend=False,
                        text=[name], textposition="inside")
        fig.update_layout(barmode="stack", title="Hybrid Quantum-Classical Stack",
                          xaxis=dict(visible=False), height=400)
        st.plotly_chart(fig, use_container_width=True)

    # ── Tab 2 ─────────────────────────────────────────────────────────────────
    with t2:
        st.markdown("#### Workload Routing Decision Logic")
        fig2 = go.Figure(go.Sankey(
            node=dict(
                label=["New Workload", "Quantum-Suitable?", "Problem Size OK?", "QPU Available?",
                        "Classical GPU", "Quantum Simulator", "Real QPU", "Hybrid (GPU+Sim)"],
                color=["#636EFA", "#FFA15A", "#FFA15A", "#FFA15A",
                        "#EF553B", "#00CC96", "#AB63FA", "#19D3F3"],
                pad=15, thickness=20,
            ),
            link=dict(
                source=[0, 1, 1, 2, 2, 3, 3],
                target=[1, 2, 4, 3, 5, 6, 7],
                value=[100, 60, 40, 30, 30, 15, 15],
                label=["route", "yes", "no → classical", "yes/small", "large → sim",
                        "available", "busy → hybrid"],
            ),
        ))
        fig2.update_layout(title="Workload Routing Decision Flow", height=380)
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("#### Routing Policy Table")
        rp_df = pd.DataFrame({
            "Condition": [
                "Problem not QUBO-encodable",
                "Qubits required > 25",
                "QPU queue > 30 min",
                "Qubits ≤ 25 AND queue < 30 min",
                "Simulation + classical post-processing",
                "Circuit depth > 100",
            ],
            "Route To": ["Classical GPU", "Quantum Simulator", "Hybrid (GPU+Sim)",
                          "Real QPU", "Hybrid", "Simulator only"],
            "Rationale": [
                "Not quantum-suitable — no advantage possible",
                "NISQ devices limited; simulation more reliable",
                "Long queue — simulator gives results faster",
                "Quantum hardware gives real fidelity data",
                "Use best of both worlds for large problems",
                "Deep circuits suffer too much noise on NISQ hardware",
            ],
            "Fallback": ["—", "Classical", "Classical", "Simulator", "Classical", "Classical"],
        })
        st.dataframe(rp_df, use_container_width=True)

        st.markdown("#### Live Routing Metrics (24h)")
        job_types = ["Classical GPU", "Quantum Simulator", "Real QPU", "Hybrid"]
        job_counts = [847, 123, 12, 45]
        fig3 = px.bar(x=job_types, y=job_counts, color=job_types, title="Jobs Routed by Type (24h)",
                      labels={"x": "Route", "y": "Job Count"})
        st.plotly_chart(fig3, use_container_width=True)

        st.markdown("#### Cost per Problem Size")
        sizes2 = [4, 8, 12, 16, 20, 25, 30]
        cost_classical = [0.001, 0.002, 0.004, 0.008, 0.016, 0.032, 0.064]
        cost_sim = [0.05, 0.1, 0.2, 0.5, 1.5, 5.0, 20.0]
        cost_qpu = [0.2, 0.4, 0.8, 2.0, 5.0, 12.0, 30.0]
        fig4 = go.Figure()
        fig4.add_scatter(x=sizes2, y=cost_classical, name="Classical GPU", mode="lines+markers")
        fig4.add_scatter(x=sizes2, y=cost_sim, name="Quantum Simulator", mode="lines+markers")
        fig4.add_scatter(x=sizes2, y=cost_qpu, name="Real QPU", mode="lines+markers")
        fig4.update_layout(title="Estimated Cost ($) per Problem Size (qubits)",
                           xaxis_title="Problem Size (qubits)", yaxis_title="Cost ($)", yaxis_type="log")
        st.plotly_chart(fig4, use_container_width=True)

    # ── Tab 3 ─────────────────────────────────────────────────────────────────
    with t3:
        st.markdown("#### API Layer")
        api_df = pd.DataFrame({
            "API Name": ["Submit Circuit", "Job Status", "Get Results", "Compile Circuit",
                          "Run Benchmark", "CBOM Scan", "List Backends", "Cancel Job"],
            "Endpoint": ["/v1/circuits/submit", "/v1/jobs/{id}/status", "/v1/jobs/{id}/results",
                          "/v1/circuits/compile", "/v1/benchmark/run", "/v1/cbom/scan",
                          "/v1/backends", "/v1/jobs/{id}/cancel"],
            "Method": ["POST", "GET", "GET", "POST", "POST", "POST", "GET", "DELETE"],
            "Auth": ["JWT"]*8,
            "Rate Limit": ["100/min", "1000/min", "500/min", "200/min", "10/min", "5/min", "500/min", "100/min"],
            "Backend": ["QPU Router", "Job DB", "Results DB", "Compiler", "Benchmark Engine",
                         "CBOM Scanner", "Backend Registry", "QPU Router"],
        })
        st.dataframe(api_df, use_container_width=True)

        st.markdown("#### Circuit Breaker Status per API")
        cb_apis = ["Submit Circuit", "Job Status", "Get Results", "Compile Circuit", "Run Benchmark"]
        cb_states = ["Closed", "Closed", "Closed", "Half-Open", "Closed"]
        cb_colors = {"Closed": "green", "Half-Open": "yellow", "Open": "red"}
        cb_cols = st.columns(len(cb_apis))
        for col, api, state in zip(cb_cols, cb_apis, cb_states):
            color = cb_colors[state]
            col.markdown(f"""
<div style='text-align:center; padding:8px; border-radius:8px; background-color:{color}22; border:2px solid {color}'>
<b>{api}</b><br/><span style='color:{color}; font-size:18px'>⬤</span><br/>{state}
</div>""", unsafe_allow_html=True)

        st.markdown("#### Database Schema")
        schema_fig = go.Figure()
        tables = {
            "QuantumJob": (0.1, 0.8, ["id PK", "circuit_id FK", "status", "backend", "created_at"]),
            "Circuit": (0.4, 0.8, ["id PK", "qasm_src", "depth", "qubits", "created_at"]),
            "Result": (0.7, 0.8, ["id PK", "job_id FK", "counts", "fidelity", "created_at"]),
            "Benchmark": (0.1, 0.4, ["id PK", "algorithm", "metrics JSON", "hardware"]),
            "Experiment": (0.4, 0.4, ["id PK", "name", "params JSON", "status"]),
            "AuditLog": (0.7, 0.4, ["id PK", "actor", "action", "hash", "ts"]),
            "UserModel": (0.25, 0.1, ["id PK", "username", "role", "created_at"]),
        }
        for tname, (tx, ty, fields) in tables.items():
            label = f"<b>{tname}</b><br>" + "<br>".join(fields)
            schema_fig.add_annotation(x=tx, y=ty, text=label, showarrow=False,
                                      bgcolor="#f0f4ff", bordercolor="#4C8BF5", borderwidth=2,
                                      font=dict(size=10), xanchor="center")
        fk_edges = [("QuantumJob", "Circuit", 0.1, 0.8, 0.4, 0.8),
                    ("QuantumJob", "Result", 0.1, 0.8, 0.7, 0.8),
                    ("QuantumJob", "AuditLog", 0.1, 0.75, 0.7, 0.45)]
        for _, _, x0, y0, x1, y1 in fk_edges:
            schema_fig.add_shape(type="line", x0=x0, y0=y0, x1=x1, y1=y1,
                                  line=dict(color="#888", width=1, dash="dot"))
        schema_fig.update_layout(
            title="Database Entity Relationships",
            xaxis=dict(visible=False, range=[0, 1]),
            yaxis=dict(visible=False, range=[0, 1]),
            height=500,
        )
        st.plotly_chart(schema_fig, use_container_width=True)

        st.markdown("#### Query Performance")
        qp_df = pd.DataFrame({
            "Query": ["SELECT job by id", "INSERT circuit", "SELECT results by job",
                       "SELECT audit log", "UPDATE job status", "SELECT backends"],
            "Avg Time (ms)": [2.1, 4.5, 8.3, 12.1, 1.8, 0.9],
            "Calls/hr": [4200, 840, 840, 120, 1200, 500],
            "Index Used": ["PRIMARY", "—", "FK(job_id)", "idx_actor", "PRIMARY", "idx_status"],
        })
        st.dataframe(qp_df, use_container_width=True)

    # ── Tab 4 ─────────────────────────────────────────────────────────────────
    with t4:
        st.markdown("#### Full Observability Stack")
        log_col, metric_col, trace_col = st.columns(3)

        with log_col:
            st.markdown("**📋 Logs (Last 10)**")
            log_df = pd.DataFrame({
                "Time": [(datetime(2026, 9, 21, 17, 0) + timedelta(minutes=i*3)).strftime("%H:%M:%S")
                          for i in range(10)],
                "Level": ["INFO", "INFO", "WARN", "INFO", "ERROR", "INFO", "INFO", "WARN", "INFO", "INFO"],
                "Service": ["api-gw", "qpu-worker", "compiler", "api-gw", "qpu-worker",
                             "api-gw", "compiler", "auth", "api-gw", "portal"],
                "Message": ["Job submitted", "Circuit compiled", "QPU queue >15min",
                             "Results returned", "QPU timeout — retry", "Auth OK",
                             "Transpile done", "JWT expiry <1hr", "CBOM scan started", "UI load OK"],
            })
            st.dataframe(log_df, use_container_width=True)

        with metric_col:
            st.markdown("**📊 Metrics (Last 60 min)**")
            mins = list(range(60))
            cpu_vals = 30 + 20 * np.sin(np.array(mins) * 0.2) + RNG.normal(0, 3, 60)
            gpu_vals = 50 + 30 * np.sin(np.array(mins) * 0.15) + RNG.normal(0, 5, 60)
            qpu_q = np.clip(RNG.poisson(3, 60).astype(float), 0, 15)
            fig5 = go.Figure()
            fig5.add_scatter(x=mins, y=cpu_vals, name="CPU%", line=dict(width=1.5))
            fig5.add_scatter(x=mins, y=gpu_vals, name="GPU%", line=dict(width=1.5))
            fig5.add_scatter(x=mins, y=qpu_q * 6, name="QPU Queue×6", line=dict(width=1.5, dash="dot"))
            fig5.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0),
                                title="System Metrics", legend=dict(x=0, y=1))
            st.plotly_chart(fig5, use_container_width=True)

        with trace_col:
            st.markdown("**🔍 Distributed Traces**")
            trace_df = pd.DataFrame({
                "Trace ID": [f"tr-{i:04d}" for i in range(5)],
                "Spans": [4, 3, 6, 3, 5],
                "Duration (ms)": [312, 45, 1840, 180, 920],
                "Services": ["api→compiler→qpu→result",
                              "api→job_db→result",
                              "api→compiler→qpu(queued)→result→audit",
                              "api→cbom→result",
                              "api→compiler→sim→result→audit"],
                "Status": ["✅", "✅", "⚠️ slow", "✅", "✅"],
            })
            st.dataframe(trace_df, use_container_width=True)

        st.markdown("#### SLO Dashboard")
        slo_df = pd.DataFrame({
            "SLO": ["API P99 Latency <1s", "Job Success Rate >99%", "QPU Job Start <5min",
                     "CBOM Scan Complete <2min", "Portal Load <3s", "Auth Latency <200ms"],
            "Target": ["<1000ms", ">99.0%", "<5min", "<120s", "<3s", "<200ms"],
            "Current": ["890ms", "99.7%", "3.2min", "68s", "1.8s", "145ms"],
            "Status": ["✅ OK", "✅ OK", "✅ OK", "✅ OK", "✅ OK", "✅ OK"],
            "Error Budget Remaining": ["82%", "70%", "90%", "95%", "88%", "75%"],
        })
        st.dataframe(slo_df, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Export
# ─────────────────────────────────────────────────────────────────────────────

SECTIONS: dict = {
    "🔍 Explainable AI": render_xai,
    "⚖️ Responsible AI": render_responsible_ai,
    "🏛️ Accountable AI": render_accountable_ai,
    "🏛️ AI Governance": render_ai_governance,
    "🧫 Performance AI": render_performance_ai,
    "🔐 SBOM/CBOM/Security": render_security_layers,
    "⚡ Hybrid Classical-Quantum": render_hybrid_classical_quantum,
}
