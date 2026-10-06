"""
Quantum Lab — Global Portal
Launch: streamlit run /mnt/deepa/quantum/portal/app.py
or:     qlab portal
"""
import subprocess
import sys
import os
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

QUANTUM_ROOT = Path(__file__).parent.parent

st.set_page_config(
    page_title="Quantum Lab — Global Portal",
    layout="wide",
    page_icon="⚛️",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.project-card {
    background: #1e1e2e; border-radius: 10px;
    padding: 14px; margin: 6px 0;
    border-left: 4px solid #00b4d8;
}
.project-card h4 { margin: 0 0 4px 0; color: #cdd6f4; font-size: 0.95em; }
.project-card small { color: #a6adc8; font-size: 0.78em; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.72em; font-weight: bold; }
.badge-ready    { background: #a6e3a1; color: #1e1e2e; }
.badge-partial  { background: #89dceb; color: #1e1e2e; }
.badge-scaffold { background: #f9e2af; color: #1e1e2e; }
</style>
""", unsafe_allow_html=True)

PROJECTS = [
    ("pqc-control-tower",   "Enterprise PQC & Crypto-Agility Control Tower",     "security",      ["cryptography","liboqs","cyclonedx-python-lib"]),
    ("qc-banking-lab",      "Hybrid Quantum-Classical Banking Platform",           "applications",  ["qiskit","qiskit-finance","pennylane"]),
    ("qc-logistics-lab",    "Hybrid CPU/GPU/QPU Logistics Optimization",           "applications",  ["qiskit","dwave-ocean-sdk"]),
    ("q01-algorithms",      "Quantum Algorithm Assessment & Benchmark",            "algorithms",    ["qiskit","pennylane","cirq"]),
    ("q02-error-mitigation","NISQ Error-Mitigation Lab",                           "algorithms",    ["qiskit","mitiq"]),
    ("q03-ftqc",            "Fault-Tolerant QC Resource Platform",                 "hardware",      ["qiskit","stim","cirq"]),
    ("q04-compiler",        "Hardware-Aware Quantum Compiler",                     "platform",      ["qiskit","cirq"]),
    ("q05-ir-interop",      "Quantum IR & Interoperability Gateway",               "platform",      ["qiskit","cirq"]),
    ("q06-transpilation",   "Calibration-Aware Quantum Transpilation",             "platform",      ["qiskit"]),
    ("q07-cloud-qpu",       "Multi-Cloud Quantum Workload Router",                 "platform",      ["qiskit-ibm-runtime"]),
    ("q08-distributed-qc",  "Distributed Multi-QPU Platform",                     "platform",      ["qiskit"]),
    ("q09-circuit-cutting", "Circuit Cutting & Reconstruction Platform",           "platform",      ["qiskit","mitiq"]),
    ("q10-silicon-spin",    "Silicon Spin-Qubit Digital Twin",                     "hardware",      ["scqubits","qutip"]),
    ("q11-topological",     "Topological QC Digital Twin",                         "hardware",      ["qiskit","stim"]),
    ("q12-analog-qc",       "Neutral-Atom Analog Quantum Lab",                    "hardware",      ["pennylane"]),
    ("q13-control",         "Quantum Pulse Control Platform",                      "hardware",      ["qiskit","qutip"]),
    ("q14-calibration",     "Autonomous Quantum Calibration Tower",                "hardware",      ["qiskit","qutip"]),
    ("q15-readout",         "Quantum Readout Engineering Platform",                "hardware",      ["qiskit","qutip"]),
    ("q16-ctrl-electronics","Control Electronics & RFSoC Digital Twin",            "hardware",      ["numpy","qutip"]),
    ("q17-cryogenics",      "Quantum Cryogenics Digital Twin",                     "infrastructure",["scipy","numpy"]),
    ("q18-fabrication",     "Quantum Chip Fabrication Digital Twin",               "infrastructure",["numpy","scipy"]),
    ("q19-packaging",       "Quantum Packaging & Interconnect",                    "infrastructure",["scipy"]),
    ("q20-chemistry",       "Hybrid Quantum Chemistry Platform",                   "science",       ["qiskit-nature","openfermion"]),
    ("q21-many-body",       "Many-Body Quantum Simulation",                        "science",       ["pennylane","netket"]),
    ("q22-repeaters",       "Quantum Repeater Network",                            "networking",    ["numpy","networkx"]),
    ("q23-memory",          "Quantum Memory Digital Twin",                         "networking",    ["qutip","numpy"]),
    ("q24-internet",        "Quantum Internet Architecture",                       "networking",    ["fastapi","numpy"]),
    ("q25-sensing",         "NV-Center Quantum Sensing Tower",                     "science",       ["qutip","numpy"]),
    ("q26-metrology",       "Quantum Metrology Platform",                          "science",       ["pennylane","scipy"]),
    ("q27-clocks",          "Quantum Atomic Clock Digital Twin",                   "science",       ["scipy","numpy"]),
]

CATEGORY_ICON  = {"security":"🔐","applications":"💼","algorithms":"⚡","platform":"🏗️","hardware":"🔬","infrastructure":"🏭","science":"🔭","networking":"🌐"}
CATEGORY_COLOR = {"security":"#cba6f7","applications":"#a6e3a1","algorithms":"#89dceb","platform":"#89b4fa","hardware":"#f9e2af","infrastructure":"#f38ba8","science":"#cdd6f4","networking":"#cba6f7"}

KAGGLE_MAP = {
    "qc-banking-lab":"mlg-ulb/creditcardfraud",
    "qc-logistics-lab":"gaborfodor/tsplib-benchmark",
    "q01-algorithms":"mlg-ulb/creditcardfraud",
    "q02-error-mitigation":"mlg-ulb/creditcardfraud",
    "pqc-control-tower":"mlg-ulb/creditcardfraud",
    "q12-analog-qc":"gaborfodor/tsplib-benchmark",
}

def get_status(pid):
    src = list((QUANTUM_ROOT/pid/"src").glob("*.py")) if (QUANTUM_ROOT/pid/"src").exists() else []
    ui  = list((QUANTUM_ROOT/pid/"ui").glob("*.py"))  if (QUANTUM_ROOT/pid/"ui").exists() else []
    if src and ui: return "ready"
    if ui:         return "partial"
    return "scaffold"

with st.sidebar:
    st.title("⚛️ Quantum Lab")
    st.caption("Praveen Asthana | Enterprise → Quantum")
    st.divider()
    view = st.radio("View", ["Overview","Projects","Status Board","Run Project"])
    st.divider()
    if view == "Projects":
        cats = sorted(set(p[2] for p in PROJECTS))
        cat_filter = st.multiselect("Category", cats, default=cats)
    else:
        cat_filter = [p[2] for p in PROJECTS]
    st.caption(f"{len(PROJECTS)} projects  |  {QUANTUM_ROOT}")

if view == "Overview":
    st.title("⚛️ Quantum Computing Portfolio")
    st.markdown("**Praveen Asthana** — Enterprise AI & Security Architect → Quantum Computing\n\nThis workspace contains **30 quantum computing projects** spanning the full stack: PQC cryptography, quantum algorithms, hardware simulation, compiler engineering, quantum chemistry, quantum networking, and quantum sensing.")
    st.divider()
    statuses = [get_status(p[0]) for p in PROJECTS]
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total",len(PROJECTS))
    c2.metric("Ready",statuses.count("ready"))
    c3.metric("Partial",statuses.count("partial"))
    c4.metric("Scaffold",statuses.count("scaffold"))
    cats_count = {}
    for p in PROJECTS: cats_count[p[2]] = cats_count.get(p[2],0)+1
    fig = px.bar(x=list(cats_count.keys()),y=list(cats_count.values()),color=list(cats_count.keys()),
                 color_discrete_map={k:CATEGORY_COLOR.get(k,"#cdd6f4") for k in cats_count},
                 template="plotly_dark",height=300,labels={"x":"Category","y":"Count"})
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig,use_container_width=True)
    cols = st.columns(3)
    for i,(pid,title,cat,sdks) in enumerate(PROJECTS):
        status = get_status(pid)
        color = CATEGORY_COLOR.get(cat,"#cdd6f4")
        icon = CATEGORY_ICON.get(cat,"⚛️")
        with cols[i%3]:
            st.markdown(f'<div class="project-card" style="border-left-color:{color}"><h4>{icon} {title}</h4><small><code>{pid}</code> | {cat} | <span class="badge badge-{status}">{status}</span></small><br/><small>{", ".join(sdks[:2])}</small></div>',unsafe_allow_html=True)

elif view == "Projects":
    st.title("⚛️ Project Browser")
    filtered = [p for p in PROJECTS if p[2] in cat_filter]
    for cat in sorted(set(p[2] for p in filtered)):
        icon = CATEGORY_ICON.get(cat,"⚛️")
        cat_projs = [p for p in filtered if p[2]==cat]
        st.markdown(f"### {icon} {cat.title()} ({len(cat_projs)})")
        ncols = min(3,len(cat_projs))
        cols = st.columns(ncols)
        for i,(pid,title,_,sdks) in enumerate(cat_projs):
            with cols[i%ncols]:
                with st.expander(f"**{title}**"):
                    st.markdown(f"**ID:** `{pid}`  |  **Status:** `{get_status(pid)}`")
                    st.markdown(f"**SDKs:** {', '.join(sdks)}")
                    readme = QUANTUM_ROOT/pid/"README.md"
                    if readme.exists():
                        txt = readme.read_text()
                        if "## Overview" in txt:
                            ov = txt.split("## Overview")[1].split("##")[0].strip()
                            st.markdown(ov[:400]+"..." if len(ov)>400 else ov)
                    st.code(f"qlab run {pid}")

elif view == "Status Board":
    st.title("📊 Status Board")
    rows = []
    for pid,title,cat,sdks in PROJECTS:
        src_n = len(list((QUANTUM_ROOT/pid/"src").glob("*.py"))) if (QUANTUM_ROOT/pid/"src").exists() else 0
        ui_n  = len(list((QUANTUM_ROOT/pid/"ui").glob("*.py")))  if (QUANTUM_ROOT/pid/"ui").exists() else 0
        rows.append({"ID":pid,"Title":title,"Category":cat,"Status":get_status(pid),"src":src_n,"ui":ui_n,"SDKs":", ".join(sdks[:2])})
    df = pd.DataFrame(rows)
    st.dataframe(df,use_container_width=True,height=700)
    sc = df["Status"].value_counts()
    fig = go.Figure(go.Pie(labels=sc.index,values=sc.values,marker_colors=["#a6e3a1","#89dceb","#f9e2af"],hole=0.4))
    fig.update_layout(title="Status Distribution",template="plotly_dark",height=280)
    st.plotly_chart(fig,use_container_width=True)

elif view == "Run Project":
    st.title("🚀 Run a Project")
    proj_ids = [p[0] for p in PROJECTS]
    selected = st.selectbox("Select project",proj_ids,format_func=lambda x: next(p[1] for p in PROJECTS if p[0]==x))
    info = next(p for p in PROJECTS if p[0]==selected)
    st.markdown(f"**{info[1]}**  |  `{info[2]}`  |  SDKs: {', '.join(info[3])}")
    col1,col2,col3 = st.columns(3)
    with col1:
        if st.button("📦 Install Requirements"):
            req = QUANTUM_ROOT/selected/"requirements.txt"
            with st.spinner("Installing..."):
                r = subprocess.run([sys.executable,"-m","pip","install","-r",str(req)],capture_output=True,text=True)
            st.success("Done") if r.returncode==0 else st.error(r.stderr[-400:])
    with col2:
        if selected in KAGGLE_MAP and st.button("⬇️ Download Kaggle Data"):
            dest = QUANTUM_ROOT/selected/"data"; dest.mkdir(exist_ok=True)
            with st.spinner("Downloading..."):
                r = subprocess.run(["kaggle","datasets","download","-d",KAGGLE_MAP[selected],"-p",str(dest),"--unzip"],capture_output=True,text=True)
            st.success(f"Saved to {dest}") if r.returncode==0 else st.error(r.stderr[-300:])
    with col3:
        if st.button("▶️ Launch Project UI"):
            app_path = QUANTUM_ROOT/selected/"ui"/"app.py"
            if app_path.exists():
                port = 8502+proj_ids.index(selected)
                subprocess.Popen(["streamlit","run",str(app_path),"--server.port",str(port),"--server.headless","true"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                st.success(f"Started on port {port}")
                st.markdown(f"[Open → http://localhost:{port}](http://localhost:{port})")
            else:
                st.error("No UI app.py found")
    readme_path = QUANTUM_ROOT/selected/"README.md"
    if readme_path.exists():
        st.divider()
        st.markdown(readme_path.read_text())
