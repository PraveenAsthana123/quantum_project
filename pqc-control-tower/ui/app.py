"""
Enterprise PQC & Crypto-Agility Control Tower — Streamlit UI
Tabs: Crypto Inventory | Algorithm Benchmark | Quantum Risk | Migration Roadmap
Run: streamlit run ui/app.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

st.set_page_config(
    page_title="Enterprise PQC & Crypto-Agility Control Tower",
    layout="wide",
    page_icon="🔐",
)


def load_json(path: Path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------

def demo_cbom() -> dict:
    assets = [
        {"path": "web/server.crt",     "asset_type": "certificate",  "algorithm": "RSA",      "key_size": 2048, "quantum_safe": False, "harvest_now_risk": True,  "migration_priority": "P1", "expiry": "2025-03-15"},
        {"path": "web/api.crt",        "asset_type": "certificate",  "algorithm": "ECDSA",    "key_size": 256,  "quantum_safe": False, "harvest_now_risk": True,  "migration_priority": "P1", "expiry": "2026-01-10"},
        {"path": "ssh/id_rsa",         "asset_type": "ssh_key",      "algorithm": "RSA",      "key_size": 4096, "quantum_safe": False, "harvest_now_risk": True,  "migration_priority": "P1", "expiry": None},
        {"path": "ssh/id_ed25519",     "asset_type": "ssh_key",      "algorithm": "ED25519",  "key_size": 256,  "quantum_safe": False, "harvest_now_risk": False, "migration_priority": "P2", "expiry": None},
        {"path": "code_sign/rel.crt",  "asset_type": "code_signing", "algorithm": "ECDSA",    "key_size": 384,  "quantum_safe": False, "harvest_now_risk": True,  "migration_priority": "P1", "expiry": "2027-06-01"},
        {"path": "vault/config.crt",   "asset_type": "certificate",  "algorithm": "RSA",      "key_size": 2048, "quantum_safe": False, "harvest_now_risk": True,  "migration_priority": "P1", "expiry": "2025-09-01"},
        {"path": "pqc/kyber.cer",      "asset_type": "certificate",  "algorithm": "ML-KEM",   "key_size": 768,  "quantum_safe": True,  "harvest_now_risk": False, "migration_priority": "P3", "expiry": "2030-01-01"},
        {"path": "pqc/dilithium.cer",  "asset_type": "certificate",  "algorithm": "ML-DSA",   "key_size": None, "quantum_safe": True,  "harvest_now_risk": False, "migration_priority": "P3", "expiry": "2030-01-01"},
    ]
    return {
        "cbom_version": "1.4", "total_assets": len(assets),
        "quantum_vulnerable": sum(1 for a in assets if not a["quantum_safe"]),
        "quantum_safe": sum(1 for a in assets if a["quantum_safe"]),
        "harvest_now_risk": sum(1 for a in assets if a["harvest_now_risk"]),
        "assets": assets,
    }


def demo_benchmark() -> list[dict]:
    return [
        {"name": "RSA-2048",          "category": "classical_asymmetric", "quantum_safe": False, "keygen_ms": 45.2,  "operation_ms": 0.4,   "verify_ms": 12.1,  "public_key_bytes": 294,  "ciphertext_or_sig_bytes": 256,  "nist_level": None},
        {"name": "RSA-4096",          "category": "classical_asymmetric", "quantum_safe": False, "keygen_ms": 280.5, "operation_ms": 1.2,   "verify_ms": 84.3,  "public_key_bytes": 550,  "ciphertext_or_sig_bytes": 512,  "nist_level": None},
        {"name": "ECDSA-P-256",       "category": "classical_asymmetric", "quantum_safe": False, "keygen_ms": 0.18,  "operation_ms": 0.22,  "verify_ms": 0.48,  "public_key_bytes": 91,   "ciphertext_or_sig_bytes": 72,   "nist_level": None},
        {"name": "AES-256-GCM",       "category": "classical_symmetric",  "quantum_safe": True,  "keygen_ms": 0.002, "operation_ms": 0.002, "verify_ms": 0.002, "public_key_bytes": 32,   "ciphertext_or_sig_bytes": 1040, "nist_level": 3},
        {"name": "ML-KEM-512",        "category": "pqc_kem",              "quantum_safe": True,  "keygen_ms": 0.04,  "operation_ms": 0.05,  "verify_ms": 0.04,  "public_key_bytes": 800,  "ciphertext_or_sig_bytes": 768,  "nist_level": 1},
        {"name": "ML-KEM-768",        "category": "pqc_kem",              "quantum_safe": True,  "keygen_ms": 0.07,  "operation_ms": 0.08,  "verify_ms": 0.07,  "public_key_bytes": 1184, "ciphertext_or_sig_bytes": 1088, "nist_level": 3},
        {"name": "ML-KEM-1024",       "category": "pqc_kem",              "quantum_safe": True,  "keygen_ms": 0.09,  "operation_ms": 0.10,  "verify_ms": 0.09,  "public_key_bytes": 1568, "ciphertext_or_sig_bytes": 1568, "nist_level": 5},
        {"name": "ML-DSA-44",         "category": "pqc_sig",              "quantum_safe": True,  "keygen_ms": 0.07,  "operation_ms": 0.18,  "verify_ms": 0.09,  "public_key_bytes": 1312, "ciphertext_or_sig_bytes": 2420, "nist_level": 2},
        {"name": "ML-DSA-65",         "category": "pqc_sig",              "quantum_safe": True,  "keygen_ms": 0.12,  "operation_ms": 0.26,  "verify_ms": 0.13,  "public_key_bytes": 1952, "ciphertext_or_sig_bytes": 3293, "nist_level": 3},
        {"name": "ML-DSA-87",         "category": "pqc_sig",              "quantum_safe": True,  "keygen_ms": 0.17,  "operation_ms": 0.35,  "verify_ms": 0.20,  "public_key_bytes": 2592, "ciphertext_or_sig_bytes": 4595, "nist_level": 5},
        {"name": "SLH-DSA-SHAKE-128s","category": "pqc_sig",              "quantum_safe": True,  "keygen_ms": 1.50,  "operation_ms": 350.0, "verify_ms": 0.90,  "public_key_bytes": 32,   "ciphertext_or_sig_bytes": 7856, "nist_level": 1},
    ]


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🔐 Enterprise PQC & Crypto-Agility Control Tower")
st.caption("PQC Architect Portfolio Project | liboqs + cryptography + CycloneDX CBOM")

tab1, tab2, tab3, tab4 = st.tabs([
    "🗂️ Crypto Inventory",
    "📊 Algorithm Benchmark",
    "☢️ Quantum Risk Assessment",
    "🗺️ Migration Roadmap",
])

# ---------------------------------------------------------------------------
# Tab 1: Crypto Inventory (CBOM)
# ---------------------------------------------------------------------------

with tab1:
    st.header("Cryptographic Bill of Materials (CBOM)")

    with st.sidebar:
        st.subheader("⚙️ Scanner Controls")
        scan_path = st.text_input("Scan directory path (optional)", placeholder="/etc/ssl or leave blank for demo")
        if st.button("🔍 Run Inventory Scan"):
            with st.spinner("Scanning..."):
                try:
                    sys.path.insert(0, str(SRC_DIR))
                    from crypto_inventory import main as run_inv
                    run_inv(scan_path if scan_path.strip() else None)
                    st.success("Scan complete!")
                except Exception as e:
                    st.error(f"Scan error: {e}")

    raw_cbom = load_json(DATA_DIR / "cbom.json")
    cbom = raw_cbom if raw_cbom else demo_cbom()
    assets = cbom.get("assets", [])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Assets", cbom.get("total_assets", len(assets)))
    col2.metric("Quantum Vulnerable", cbom.get("quantum_vulnerable", 0), delta_color="inverse")
    col3.metric("Quantum Safe", cbom.get("quantum_safe", 0))
    col4.metric("Harvest-Now Risk", cbom.get("harvest_now_risk", 0), delta_color="inverse")

    df_assets = pd.DataFrame(assets)
    if not df_assets.empty:
        # Color code
        def row_color(row):
            if not row.get("quantum_safe"):
                return ["background-color: #ffe5e5"] * len(row)
            return ["background-color: #e5ffe5"] * len(row)

        priority_filter = st.selectbox("Filter by Priority", ["All", "P1", "P2", "P3"])
        if priority_filter != "All":
            df_show = df_assets[df_assets["migration_priority"] == priority_filter]
        else:
            df_show = df_assets

        st.dataframe(df_show[["path", "asset_type", "algorithm", "key_size", "quantum_safe", "harvest_now_risk", "migration_priority", "expiry"]],
                     use_container_width=True, hide_index=True)

        # Algorithm distribution
        alg_counts = df_assets["algorithm"].value_counts().reset_index()
        alg_counts.columns = ["algorithm", "count"]
        fig_alg = px.pie(alg_counts, names="algorithm", values="count",
                         title="Algorithm Distribution", height=300)
        st.plotly_chart(fig_alg, use_container_width=True)

    if not raw_cbom:
        st.info("Demo CBOM shown. Run inventory scan above or: `python src/crypto_inventory.py /path/to/scan`")

# ---------------------------------------------------------------------------
# Tab 2: Algorithm Benchmark
# ---------------------------------------------------------------------------

with tab2:
    st.header("Classical vs PQC Algorithm Performance Benchmark")

    raw_bench = load_json(DATA_DIR / "pqc_benchmark.json")
    bench_data = raw_bench if raw_bench else demo_benchmark()
    df_bench = pd.DataFrame(bench_data)

    if st.button("▶ Run Benchmark (takes ~30s)"):
        with st.spinner("Running benchmark..."):
            try:
                from pqc_benchmark import main as run_bench
                run_bench()
                st.success("Benchmark complete! Refresh to see real results.")
            except Exception as e:
                st.error(f"Benchmark error: {e}")

    col1, col2 = st.columns(2)

    with col1:
        fig_pk = px.bar(df_bench.sort_values("public_key_bytes"), x="name", y="public_key_bytes",
                        color="quantum_safe", title="Public Key Size (bytes)",
                        color_discrete_map={True: "#4CAF50", False: "#F44336"}, height=340)
        fig_pk.update_xaxes(tickangle=45)
        st.plotly_chart(fig_pk, use_container_width=True)

    with col2:
        fig_sig = px.bar(df_bench.sort_values("ciphertext_or_sig_bytes"), x="name", y="ciphertext_or_sig_bytes",
                         color="quantum_safe", title="Ciphertext/Signature Size (bytes)",
                         color_discrete_map={True: "#4CAF50", False: "#F44336"}, height=340)
        fig_sig.update_xaxes(tickangle=45)
        st.plotly_chart(fig_sig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        fig_kg = px.bar(df_bench, x="name", y="keygen_ms", color="category",
                        title="Key Generation Time (ms)", height=320, log_y=True)
        fig_kg.update_xaxes(tickangle=45)
        st.plotly_chart(fig_kg, use_container_width=True)
    with col4:
        fig_op = px.bar(df_bench, x="name", y="operation_ms", color="category",
                        title="Encrypt/Sign Time (ms)", height=320, log_y=True)
        fig_op.update_xaxes(tickangle=45)
        st.plotly_chart(fig_op, use_container_width=True)

    st.subheader("Full Benchmark Table")
    st.dataframe(df_bench[["name", "category", "quantum_safe", "nist_level", "keygen_ms",
                            "operation_ms", "verify_ms", "public_key_bytes",
                            "ciphertext_or_sig_bytes"]],
                 use_container_width=True, hide_index=True)

    if not raw_bench:
        st.info("NIST reference values shown. Run benchmark above for real measurements.")

# ---------------------------------------------------------------------------
# Tab 3: Quantum Risk Assessment
# ---------------------------------------------------------------------------

with tab3:
    st.header("Quantum Risk Assessment — Harvest-Now-Decrypt-Later (HNDL)")

    cbom3 = load_json(DATA_DIR / "cbom.json") or demo_cbom()
    assets3 = cbom3.get("assets", [])
    df3 = pd.DataFrame(assets3) if assets3 else pd.DataFrame()

    if not df3.empty:
        col1, col2 = st.columns(2)
        with col1:
            safe_count = int(df3["quantum_safe"].sum())
            vuln_count = len(df3) - safe_count
            fig_pie = px.pie(
                values=[safe_count, vuln_count],
                names=["Quantum Safe", "Quantum Vulnerable"],
                color_discrete_sequence=["#4CAF50", "#F44336"],
                title="Quantum Safety Status", height=320,
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            p1 = int((df3["migration_priority"] == "P1").sum())
            p2 = int((df3["migration_priority"] == "P2").sum())
            p3 = int((df3["migration_priority"] == "P3").sum())
            fig_prio = px.bar(
                x=["P1 — Immediate", "P2 — Short-term", "P3 — Long-term"],
                y=[p1, p2, p3],
                color=["P1", "P2", "P3"],
                color_discrete_map={"P1": "#F44336", "P2": "#FF9800", "P3": "#4CAF50"},
                title="Migration Priority Distribution", height=320,
            )
            st.plotly_chart(fig_prio, use_container_width=True)

        hndl_assets = df3[df3["harvest_now_risk"] == True]
        if not hndl_assets.empty:
            st.error(f"⚠️ {len(hndl_assets)} assets at Harvest-Now-Decrypt-Later risk!")
            st.dataframe(hndl_assets[["path", "algorithm", "asset_type", "expiry"]],
                         use_container_width=True, hide_index=True)

    st.markdown("""
    ### HNDL Risk Explanation
    **Harvest-Now-Decrypt-Later (HNDL):** Adversaries collect encrypted traffic today using RSA/ECDSA.
    When a cryptographically relevant quantum computer (CRQC) arrives (~2030s), Shor's algorithm
    breaks RSA and ECC, exposing all previously harvested traffic.

    **Affected algorithms:** RSA, ECDSA, ECDH, DSA, DH — any asymmetric scheme based on factoring or discrete log.

    **Migration target:** ML-KEM (key exchange) + ML-DSA (signatures) — NIST-standardized PQC algorithms (FIPS 203/204).
    """)

# ---------------------------------------------------------------------------
# Tab 4: Migration Roadmap
# ---------------------------------------------------------------------------

with tab4:
    st.header("PQC Migration Roadmap")

    if st.button("📋 Generate Migration Plan"):
        with st.spinner("Planning..."):
            try:
                from migration_planner import main as run_plan
                run_plan()
                st.success("Migration plan generated!")
            except Exception as e:
                st.error(f"Error: {e}")

    cbom4 = load_json(DATA_DIR / "cbom.json") or demo_cbom()
    assets4 = cbom4.get("assets", [])

    if assets4:
        # Simulate migration actions from cbom
        REPLACEMENTS = {
            "RSA": ("ML-DSA-65", 10), "ECDSA": ("ML-DSA-65", 7), "ECDH": ("ML-KEM-768", 7),
            "DSA": ("ML-DSA-65", 5), "ED25519": ("ML-DSA-44", 5),
        }
        actions = []
        for a in assets4:
            if a.get("quantum_safe"):
                continue
            alg = a.get("algorithm", "RSA").upper()
            rep, days = REPLACEMENTS.get(alg, ("ML-DSA-65", 10))
            actions.append({"Asset": a["path"], "Type": a["asset_type"],
                            "Current": alg, "Replace With": rep,
                            "Priority": a["migration_priority"],
                            "Effort (days)": days,
                            "HNDL": "⚠️ Yes" if a.get("harvest_now_risk") else "No",
                            "Expiry": a.get("expiry") or "N/A"})

        if actions:
            df_actions = pd.DataFrame(actions).sort_values("Priority")
            st.dataframe(df_actions, use_container_width=True, hide_index=True)

            total_effort = sum(a["Effort (days)"] for a in actions)
            col1, col2, col3 = st.columns(3)
            col1.metric("Items to Migrate", len(actions))
            col2.metric("Estimated Effort", f"{total_effort} days")
            col3.metric("P1 (Critical)", sum(1 for a in actions if a["Priority"] == "P1"))

            # Gantt-style
            phases = {"P1": 0, "P2": 6, "P3": 18}
            gantt_data = []
            for a in actions:
                start = phases.get(a["Priority"], 6)
                gantt_data.append({
                    "Task": a["Asset"][-30:],
                    "Start": start, "Finish": start + a["Effort (days)"] / 20,
                    "Priority": a["Priority"],
                })
            df_gantt = pd.DataFrame(gantt_data)
            fig_gantt = px.timeline(
                df_gantt.assign(Start=pd.to_datetime("2025-01") + pd.to_timedelta(df_gantt["Start"] * 30, unit="D"),
                                Finish=pd.to_datetime("2025-01") + pd.to_timedelta(df_gantt["Finish"] * 30, unit="D")),
                x_start="Start", x_end="Finish", y="Task", color="Priority",
                color_discrete_map={"P1": "#F44336", "P2": "#FF9800", "P3": "#4CAF50"},
                title="PQC Migration Timeline", height=400,
            )
            st.plotly_chart(fig_gantt, use_container_width=True)

    roadmap_html = DATA_DIR / "migration_roadmap.html"
    if roadmap_html.exists():
        with open(roadmap_html) as f:
            html_content = f.read()
        st.download_button("⬇ Download Full HTML Report", html_content,
                           "migration_roadmap.html", "text/html")
