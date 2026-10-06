"""
Quantum Architecture Control Tower — Main Assembler v2
Unifies all 20 sections from tower_part1/2/3 under a single Streamlit nav.
Run:  streamlit run /mnt/deepa/quantum/portal/quantum_tower.py --server.port 8766
"""
import sys
import traceback
from pathlib import Path

import streamlit as st

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Quantum Architecture Control Tower",
    page_icon="⚛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Dark theme CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
  html, body, [data-testid="stAppViewContainer"] { background:#0e1117 !important; }
  [data-testid="stSidebar"] { background:#0d1117 !important; border-right:1px solid #21262d; }
  [data-testid="stSidebar"] * { color:#e6edf3; }
  .block-container { padding:1.5rem 2rem 2rem 2rem; }
  h1,h2,h3,h4 { color:#e6edf3 !important; }
  p,li,td,th { color:#c9d1d9; }
  .stMetric [data-testid="metric-container"] {
      background:#161b22 !important; border-radius:8px;
      padding:.5rem .9rem; border:1px solid #30363d;
  }
  .stMetric label { color:#8b949e !important; font-size:.8rem; }
  .stMetric [data-testid="stMetricValue"] { color:#58a6ff !important; font-weight:700; }
  div[data-baseweb="tab-list"] { background:#161b22; border-radius:8px; gap:4px; }
  div[data-baseweb="tab"] { background:transparent; color:#8b949e; border-radius:6px; }
  div[aria-selected="true"][data-baseweb="tab"] { background:#1f6feb !important; color:#fff !important; }
  .stDataFrame { border:1px solid #30363d; border-radius:6px; }
  .stAlert { border-radius:6px; }
  hr { border-color:#21262d !important; }
  /* Sidebar button overrides */
  [data-testid="stSidebar"] button[kind="secondary"] {
      background:#161b22 !important; color:#c9d1d9 !important;
      border:1px solid #30363d !important; border-radius:6px;
      font-size:.82rem; text-align:left;
  }
  [data-testid="stSidebar"] button[kind="primary"] {
      background:#1f6feb !important; color:#fff !important;
      border:none !important; border-radius:6px; font-size:.82rem;
  }
  /* Section badge */
  .sec-badge {
      display:inline-block; padding:3px 10px; border-radius:12px; font-size:.78rem;
      background:#1f6feb22; color:#58a6ff; border:1px solid #1f6feb44;
  }
</style>
""", unsafe_allow_html=True)

# ── Load sections ─────────────────────────────────────────────────────────────
PORTAL_DIR = Path(__file__).parent
if str(PORTAL_DIR) not in sys.path:
    sys.path.insert(0, str(PORTAL_DIR))


@st.cache_resource(show_spinner="Loading tower sections…")
def load_sections():
    try:
        from tower_part1 import SECTIONS as S1
        from tower_part2 import SECTIONS as S2
        from tower_part3 import SECTIONS as S3
        return {**S1, **S2, **S3}
    except ImportError as exc:
        return {"⚠️ Import Error": lambda: st.error(str(exc))}


ALL_SECTIONS = load_sections()

# ── Navigation groups ─────────────────────────────────────────────────────────
PART_LABELS = {
    "📐 Architecture & Design": [
        "🏗️ Architecture",
        "🛠️ Tech Stack",
        "📖 User Stories",
        "⚙️ Manual Process",
        "🔁 Pipeline Process",
    ],
    "⚛️ Quantum Core": [
        "🤖 Multi-Agent Process",
        "⚛️ Quantum Process",
        "🧠 QML Process",
        "🔧 QML Compiler",
        "🛡️ Error Correction",
        "📈 Optimization",
        "🧪 QML Testing",
        "🌀 QML Simulation",
    ],
    "🤖 AI Intelligence": [
        "🔍 Explainable AI",
        "⚖️ Responsible AI",
        "🏛️ Accountable AI",
        "🏛️ AI Governance",
        "🧫 Performance AI",
    ],
    "🔐 Security & Hybrid": [
        "🔐 SBOM/CBOM/Security",
        "⚡ Hybrid Classical-Quantum",
    ],
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
section_names_flat = list(ALL_SECTIONS.keys())

with st.sidebar:
    st.markdown("""
<div style='text-align:center;padding:10px 0 6px;'>
  <span style='font-size:2rem;'>⚛️</span><br>
  <strong style='color:#e6edf3;font-size:.95rem;'>Quantum Tower</strong><br>
  <span style='color:#8b949e;font-size:.72rem;'>Architecture Control Tower v2.0</span>
</div>
<hr style='margin:6px 0;'/>
""", unsafe_allow_html=True)

    for group_label, section_list in PART_LABELS.items():
        present = [s for s in section_list if s in ALL_SECTIONS]
        if not present:
            continue
        active_now = st.session_state.get("active_section", "")
        with st.expander(group_label, expanded=(active_now in present)):
            for sec in present:
                is_active = (sec == active_now)
                if st.button(sec, key=f"nav_{sec}", use_container_width=True,
                             type="primary" if is_active else "secondary"):
                    st.session_state["active_section"] = sec
                    st.rerun()

    st.markdown("<hr/>", unsafe_allow_html=True)

    # System health panel
    st.markdown("**System Health**")
    health = [
        ("QPU Backend",  "IBM Brisbane 🟢"),
        ("Simulator",    "AerSim GPU 🟢"),
        ("ML Pipeline",  "PennyLane 🟢"),
        ("Security",     "CBOM Live 🟢"),
        ("Agent Bus",    "9 active 🟢"),
        ("Portal",       "8766 online 🟢"),
    ]
    for lbl, val in health:
        c1, c2 = st.columns([3, 4])
        c1.caption(lbl)
        c2.caption(val)

    st.markdown("<hr/>", unsafe_allow_html=True)
    st.caption("`qportal` or `qlab portal`")
    st.caption("`streamlit run quantum_tower.py --server.port 8766`")

# ── Default active section ────────────────────────────────────────────────────
if "active_section" not in st.session_state:
    st.session_state["active_section"] = section_names_flat[0] if section_names_flat else None

active = st.session_state.get("active_section")

# ── Header ────────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5, c6 = st.columns([4, 1, 1, 1, 1, 1])
with c1:
    st.markdown("## ⚛️ Quantum Architecture Control Tower")
    breadcrumb = ""
    for grp, items in PART_LABELS.items():
        if active in items:
            breadcrumb = f"<small style='color:#8b949e;'>🏠 &rsaquo; {grp} &rsaquo; </small><span class='sec-badge'>{active}</span>"
            break
    if breadcrumb:
        st.markdown(breadcrumb, unsafe_allow_html=True)
    else:
        st.caption("Post-Quantum Cryptography · QML · Error Correction · Multi-Agent · Hybrid Classical-Quantum")
c2.metric("Sections", len(ALL_SECTIONS))
c3.metric("Projects", "30")
c4.metric("SDKs", "11")
c5.metric("Agents", "9")
c6.metric("Port", "8766")
st.divider()

# ── Render active section ─────────────────────────────────────────────────────
if active and active in ALL_SECTIONS:
    try:
        ALL_SECTIONS[active]()
    except Exception as exc:
        st.error(f"Error rendering **{active}**: {exc}")
        st.code(traceback.format_exc(), language="python")
else:
    # Landing page
    st.markdown("### Select a section from the left sidebar to begin.")
    for group, sections in PART_LABELS.items():
        st.markdown(f"#### {group}")
        cols = st.columns(min(len([s for s in sections if s in ALL_SECTIONS]), 4))
        present = [s for s in sections if s in ALL_SECTIONS]
        for i, sec in enumerate(present):
            with cols[i % len(cols)]:
                if st.button(sec, use_container_width=True):
                    st.session_state["active_section"] = sec
                    st.rerun()
